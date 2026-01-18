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

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stMetric { background-color: #312e2b; padding: 15px; border-radius: 8px; border: 1px solid #403d39; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
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
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return path if os.path.exists(path) else None

STOCKFISH_PATH = get_stockfish_path()

# --- 3. LÓGICA DE CLASSIFICAÇÃO ---
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
    st.subheader("Configurações")
    uploaded_file = st.file_uploader("Carregue seu PGN", type="pgn")
    depth = st.slider("Profundidade da Análise", 10, 20, 12)

if uploaded_file and STOCKFISH_PATH:
    pgn_text = uploaded_file.getvalue().decode("utf-8")
    game = chess.pgn.read_game(StringIO(pgn_text))
    
    if game:
        results = []
        evals = []
        counts = {"Melhor": 0, "Excelente": 0, "Bom": 0, "Imprecisão": 0, "Erro": 0, "Capivarada": 0}
        
        # Processamento
        with st.status("Analisando lances com Stockfish...") as status:
            board = game.board()
            with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
                for move in game.mainline_moves():
                    # Avaliação pré-move
                    info_pre = engine.analyse(board, chess.engine.Limit(depth=depth))
                    score_pre = info_pre["score"].relative.score(mate_score=10000)
                    
                    board.push(move)
                    
                    # Avaliação pós-move
                    info_post = engine.analyse(board, chess.engine.Limit(depth=depth))
                    score_post = info_post["score"].relative.score(mate_score=10000)
                    
                    loss = (score_pre * -1) - score_post
                    cat, color, icon = get_move_category(loss)
                    
                    counts[cat] += 1
                    evals.append(score_post / 100)
                    results.append({"move": board.san(move), "cat": cat, "color": color, "icon": icon})
            status.update(label="Análise finalizada!", state="complete")

        # --- RENDERIZAÇÃO IDÊNTICA ---
        col_viz, col_stats = st.columns([2, 1])

        with col_viz:
            # Gráfico de Vantagem
            df_chart = pd.DataFrame({"Lance": range(len(evals)), "Vantagem": evals})
            chart = alt.Chart(df_chart).mark_area(line={'color': 'white'}, color='#4d4d4d').encode(
                x='Lance', y=alt.Y('Vantagem', scale=alt.Scale(domain=[-10, 10]))
            ).properties(height=200)
            st.altair_chart(chart, use_container_width=True)
            
            st.image("https://images.chesscomfiles.com/chess-themes/boards/green/100.png", use_container_width=True)

        with col_stats:
            st.markdown("<h3 style='text-align: center;'>Resumo da Revisão</h3>", unsafe_allow_html=True)
            
            # Precisão
            acc = max(0, 100 - (counts["Erro"]*10 + counts["Capivarada"]*20))
            c1, c2 = st.columns(2)
            c1.metric("Jogador", f"{acc:.1f}")
            c2.metric("Oponente", "---")

            st.markdown("<br>", unsafe_allow_html=True)

            # Tabela de lances
            for cat, color, icon in [("Melhor", "#96bc4b", "⭐"), ("Excelente", "#60a33e", "!"), 
                                     ("Imprecisão", "#f0c15c", "?!"), ("Erro", "#e58f2a", "?"), 
                                     ("Capivarada", "#ca3431", "??")]:
                st.markdown(f"""
                <div class="classification-row">
                    <span style="color: #bababa;">{cat}</span>
                    <div style="display: flex; align-items: center;">
                        <span style="color: {color}; font-weight: bold; margin-right: 12px;">{counts[cat]}</span>
                        <div class="icon-circle" style="background-color: {color};">{icon}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()
            
            # Rating Card
            r_val = estimate_rating(acc)
            st.markdown(f"""
            <div style="display: flex; justify-content: center; gap: 10px;">
                <div style="background: white; color: black; padding: 5px 20px; border-radius: 4px; font-weight: bold;">{int(r_val)}</div>
                <div style="background: #312e2b; color: white; padding: 5px 20px; border-radius: 4px; font-weight: bold;">---</div>
            </div>
            <p style="text-align: center; color: #8b8987; font-size: 12px; margin-top: 5px;">Rating da Partida</p>
            """, unsafe_allow_html=True)

elif not STOCKFISH_PATH:
    st.error("Motor Stockfish não detectado. Verifique o arquivo packages.txt.")
else:
    st.info("Aguardando carregamento do PGN para iniciar a revisão...")
