import streamlit as st
import chess
import chess.engine
import chess.pgn
import pandas as pd
import altair as alt
import shutil
import os
from io import StringIO

# --- 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS ---
st.set_page_config(page_title="Chess Review Pro", layout="wide")

# CSS para replicar a interface escura e os ícones do Chess.com
st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stMetric { background-color: #312e2b; padding: 15px; border-radius: 8px; border: 1px solid #403d39; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'Segoe UI', sans-serif; }
    .classification-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 6px 12px; margin-bottom: 3px; background-color: #2b2926; border-radius: 4px;
    }
    .icon-circle {
        width: 26px; height: 26px; border-radius: 50%; display: flex;
        align-items: center; justify-content: center; font-weight: bold; font-size: 13px; color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOCALIZAÇÃO DO MOTOR ---
def get_stockfish_path():
    # Busca o executável instalado via packages.txt
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return path if os.path.exists(path) else None

STOCKFISH_PATH = get_stockfish_path()

# --- 3. LÓGICA DE CLASSIFICAÇÃO E RATING ---
def get_move_category(loss):
    if loss <= 5: return "Melhor", "#96bc4b", "⭐"
    if loss < 25: return "Excelente", "#60a33e", "!"
    if loss < 60: return "Bom", "#9cbf34", "✓"
    if loss < 150: return "Imprecisão", "#f0c15c", "?!"
    if loss < 300: return "Erro", "#e58f2a", "?"
    return "Capivarada", "#ca3431", "??"

def estimate_rating(accuracy):
    if accuracy >= 90: return 1800 + (accuracy - 90) * 40
    if accuracy >= 70: return 1200 + (accuracy - 70) * 30
    return 400 + accuracy * 10

# --- 4. INTERFACE PRINCIPAL ---
st.title("♟️ Revisão da Partida Profissional")

with st.sidebar:
    st.subheader("Configurações de Análise")
    uploaded_file = st.file_uploader("Carregue seu arquivo PGN", type="pgn")
    depth = st.slider("Profundidade (Stockfish)", 10, 20, 12)

if uploaded_file and STOCKFISH_PATH:
    pgn_text = uploaded_file.getvalue().decode("utf-8")
    game = chess.pgn.read_game(StringIO(pgn_text))
    
    if game:
        results = []
        evals = []
        counts = {"Melhor": 0, "Excelente": 0, "Bom": 0, "Imprecisão": 0, "Erro": 0, "Capivarada": 0}
        
        # --- PROCESSAMENTO DA PARTIDA ---
        with st.status("O Professor está analisando os lances...", expanded=True) as status:
            board = game.board()
            try:
                with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
                    for move in game.mainline_moves():
                        # A CORREÇÃO: Gerar a notação SAN ANTES do push
                        move_san = board.san(move)
                        
                        # Avaliação da posição atual (antes do lance)
                        info_pre = engine.analyse(board, chess.engine.Limit(depth=depth))
                        score_pre = info_pre["score"].relative.score(mate_score=10000)
                        
                        # Executa o movimento no tabuleiro
                        board.push(move)
                        
                        # Avaliação da nova posição (pós-lance)
                        info_post = engine.analyse(board, chess.engine.Limit(depth=depth))
                        score_post = info_post["score"].relative.score(mate_score=10000)
                        
                        # Cálculo de perda e classificação
                        loss = (score_pre * -1) - score_post
                        cat, color, icon = get_move_category(loss)
                        
                        counts[cat] += 1
                        evals.append(score_post / 100)
                        results.append({
                            "move": move_san, 
                            "cat": cat, 
                            "color": color, 
                            "icon": icon,
                            "score": score_post / 100
                        })
                        st.write(f"Analisado: {move_san} ({cat})")
                status.update(label="Análise finalizada!", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Erro no motor: {e}")

        # --- EXIBIÇÃO DA INTERFACE (LADO A LADO) ---
        col_viz, col_stats = st.columns([2, 1])

        with col_viz:
            # Gráfico de Vantagem (Topo)
            df_chart = pd.DataFrame({"Lance": range(len(evals)), "Vantagem": evals})
            chart = alt.Chart(df_chart).mark_area(
                line={'color': 'white'}, 
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#ffffff', offset=1),
                           alt.GradientStop(color='#4d4d4d', offset=0)],
                    x1=1, y1=1, x2=1, y2=0
                )
            ).encode(
                x='Lance', 
                y=alt.Y('Vantagem', scale=alt.Scale(domain=[-10, 10]))
            ).properties(height=200)
            st.altair_chart(chart, use_container_width=True)
            
            # Placeholder do Tabuleiro (Imagem estática ou componente)
            st.image("https://images.chesscomfiles.com/chess-themes/boards/green/100.png", use_container_width=True)

        with col_stats:
            st.markdown("<h3 style='text-align: center; color: white;'>Revisão da Partida</h3>", unsafe_allow_html=True)
            
            # Cálculos Finais
            total = len(results)
            acc = max(0, 100 - (counts["Erro"]*8 + counts["Capivarada"]*15 + counts["Imprecisão"]*3)) if total > 0 else 0
            
            # Cards de Precisão
            c1, c2 = st.columns(2)
            c1.metric("Você", f"{acc:.1f}")
            c2.metric("Oponente", "---")

            st.markdown("<br>", unsafe_allow_html=True)

            # Tabela de Categorias com Ícones
            for cat, color, icon in [
                ("Melhor", "#96bc4b", "⭐"), 
                ("Excelente", "#60a33e", "!"), 
                ("Imprecisão", "#f0c15c", "?!"), 
                ("Erro", "#e58f2a", "?"), 
                ("Capivarada", "#ca3431", "??")
            ]:
                st.markdown(f"""
                <div class="classification-row">
                    <span style="color: #bababa; font-size: 14px;">{cat}</span>
                    <div style="display: flex; align-items: center;">
                        <span style="color: {color}; font-weight: bold; margin-right: 12px;">{counts[cat]}</span>
                        <div class="icon-circle" style="background-color: {color};">{icon}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()
            
            # Card de Rating Estimado
            r_val = estimate_rating(acc)
            st.markdown(f"""
            <div style="display: flex; justify-content: center; gap: 10px;">
                <div style="background: white; color: black; padding: 5px 25px; border-radius: 4px; font-weight: bold; font-size: 18px;">{int(r_val)}</div>
                <div style="background: #312e2b; color: white; padding: 5px 25px; border-radius: 4px; font-weight: bold; font-size: 18px;">---</div>
            </div>
            <p style="text-align: center; color: #8b8987; font-size: 12px; margin-top: 8px;">Rating da Partida (Performance)</p>
            """, unsafe_allow_html=True)

            with st.expander("Ver histórico detalhado"):
                for r in results:
                    st.markdown(f"**{r['move']}** - <span style='color:{r['color']}'>{r['cat']}</span>", unsafe_allow_html=True)

elif not STOCKFISH_PATH:
    st.error("ERRO: Motor Stockfish não encontrado. Verifique se 'stockfish' está no seu arquivo packages.txt.")
else:
    st.info("Aguardando upload do arquivo PGN para iniciar a revisão.")
