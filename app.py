import streamlit as st
import chess
import chess.engine
import chess.pgn
import pandas as pd
import altair as alt
import shutil
import os
from io import StringIO
from streamlit_chess import st_chess # Componente para o tabuleiro interativo

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Chess Review Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stMetric { background-color: #312e2b; padding: 10px; border-radius: 4px; border: 1px solid #403d39; }
    .classification-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 4px 10px; margin-bottom: 2px; background-color: #2b2926; border-radius: 3px;
    }
    .icon-circle {
        width: 22px; height: 22px; border-radius: 50%; display: flex;
        align-items: center; justify-content: center; font-weight: bold; font-size: 11px; color: white;
    }
    .player-box { background-color: #312e2b; padding: 5px 15px; border-radius: 4px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA DO MOTOR E CLASSIFICAÇÃO ---
def get_stockfish_path():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return path if os.path.exists(path) else None

STOCKFISH_PATH = get_stockfish_path()

def get_detailed_category(loss, move_idx, total_moves):
    # Lógica de "Livro" para os primeiros movimentos
    if move_idx < 8: return "Livro", "#a88865", "📖"
    if loss <= -50: return "Brilhante", "#26ceaa", "!!"
    if loss <= 5: return "Melhor", "#96bc4b", "⭐"
    if loss < 20: return "Excelente", "#60a33e", "!"
    if loss < 40: return "Ótimo", "#96bc4b", "👍"
    if loss < 70: return "Bom", "#9cbf34", "✓"
    if loss < 150: return "Imprecisão", "#f0c15c", "?!"
    if loss < 300: return "Erro", "#e58f2a", "?"
    return "Capivarada", "#ca3431", "??"

# --- 3. INTERFACE E PROCESSAMENTO ---
st.title("♟️ Revisão da Partida Profissional")

with st.sidebar:
    uploaded_file = st.file_uploader("Upload PGN", type="pgn")
    depth = st.slider("Profundidade Stockfish", 10, 16, 12)

if 'current_move_idx' not in st.session_state:
    st.session_state.current_move_idx = 0

if uploaded_file and STOCKFISH_PATH:
    pgn_text = uploaded_file.getvalue().decode("utf-8")
    game = chess.pgn.read_game(StringIO(pgn_text))
    
    if game:
        all_moves = list(game.mainline_moves())
        evals = []
        history = []
        counts = {cat: 0 for cat in ["Brilhante", "Excelente", "Livro", "Melhor", "Ótimo", "Bom", "Imprecisão", "Erro", "Capivarada"]}
        
        # --- ANÁLISE ---
        with st.status("Analisando partida...") as status:
            board_eval = game.board()
            with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
                for i, move in enumerate(all_moves):
                    move_san = board_eval.san(move)
                    info_pre = engine.analyse(board_eval, chess.engine.Limit(depth=depth))
                    score_pre = info_pre["score"].relative.score(mate_score=10000)
                    
                    board_eval.push(move)
                    
                    info_post = engine.analyse(board_eval, chess.engine.Limit(depth=depth))
                    score_post = info_post["score"].relative.score(mate_score=10000)
                    
                    loss = (score_pre * -1) - score_post
                    cat, color, icon = get_detailed_category(loss, i, len(all_moves))
                    counts[cat] += 1
                    
                    eval_val = score_post / 100
                    evals.append(eval_val)
                    history.append({"fen": board_eval.fen(), "san": move_san, "cat": cat, "color": color, "icon": icon})
            status.update(label="Análise completa!", state="complete")

        # --- EXIBIÇÃO ---
        col_board, col_side = st.columns([2, 1])

        with col_board:
            # Tabuleiro Interativo
            current_fen = history[st.session_state.current_move_idx]["fen"] if history else chess.STARTING_FEN
            st_chess(current_fen, key="board_viewer")
            
            # Controles de Navegação
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("⏪ Início"): st.session_state.current_move_idx = 0
            if c2.button("⬅️ Anterior"): st.session_state.current_move_idx = max(0, st.session_state.current_move_idx - 1)
            if c3.button("Próximo ➡️"): st.session_state.current_move_idx = min(len(history)-1, st.session_state.current_move_idx + 1)
            if c4.button("Fim ⏩"): st.session_state.current_move_idx = len(history)-1

        with col_side:
            # Gráfico de Vantagem
            df_chart = pd.DataFrame({"Lance": range(len(evals)), "Vantagem": evals})
            st.altair_chart(alt.Chart(df_chart).mark_area(line={'color': 'white'}, color='#4d4d4d').encode(
                x='Lance', y=alt.Y('Vantagem', scale=alt.Scale(domain=[-10, 10]))
            ).properties(height=100), use_container_width=True)

            # Cabeçalho Jogadores
            p1, p2 = st.columns(2)
            p1.markdown(f"<div class='player-box'><b>{game.headers.get('White', 'Brancas')}</b><br>65.1</div>", unsafe_allow_html=True)
            p2.markdown(f"<div class='player-box'><b>{game.headers.get('Black', 'Pretas')}</b><br>93.1</div>", unsafe_allow_html=True)

            # Tabela de Classificação
            st.markdown("<br>", unsafe_allow_html=True)
            for cat, color, icon in [("Brilhante", "#26ceaa", "!!"), ("Excelente", "#60a33e", "!"), ("Livro", "#a88865", "📖"), 
                                     ("Melhor", "#96bc4b", "⭐"), ("Imprecisão", "#f0c15c", "?!"), ("Erro", "#e58f2a", "?"), 
                                     ("Capivarada", "#ca3431", "??")]:
                st.markdown(f"""
                <div class="classification-row">
                    <span style="color: #bababa; font-size: 13px;">{cat}</span>
                    <div style="display: flex; align-items: center;">
                        <span style="color: {color}; font-weight: bold; margin-right: 10px;">{counts[cat]}</span>
                        <div class="icon-circle" style="background-color: {color};">{icon}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Fases e Rating
            st.divider()
            r1, r2 = st.columns(2)
            r1.markdown("<div style='background:white; color:black; text-align:center; font-weight:bold; border-radius:3px;'>800</div>", unsafe_allow_html=True)
            r2.markdown("<div style='background:#312e2b; color:white; text-align:center; font-weight:bold; border-radius:3px;'>1650</div>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; font-size:12px;'>Rating da Partida</p>", unsafe_allow_html=True)
            
            st.write(f"**Lance Atual:** {history[st.session_state.current_move_idx]['san']} ({history[st.session_state.current_move_idx]['cat']})")
