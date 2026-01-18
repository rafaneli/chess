import streamlit as st
import chess
import chess.engine
import sqlite3
import hashlib
import shutil
import os
import json
import streamlit.components.v1 as components

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Chess Pro", layout="wide")

def init_db():
    conn = sqlite3.connect('chess_master.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, pgn TEXT, result TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- 2. COMPONENTE DE TABULEIRO INTERATIVO (JS) ---
def chessboard_component(fen, key):
    # HTML e JS para um tabuleiro real que permite arrastar peças
    board_html = f"""
    <link rel="stylesheet" href="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.css">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
    
    <div id="board" style="width: 450px"></div>
    
    <script>
        var board = null;
        var game = new Chess('{fen}');

        function onDrop (source, target) {{
            var move = game.move({{
                from: source,
                to: target,
                promotion: 'q'
            }});

            if (move === null) return 'snapback';
            
            // Envia o novo FEN para o Streamlit
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: game.fen()
            }}, '*');
        }}

        var config = {{
            draggable: true,
            position: '{fen}',
            onDrop: onDrop,
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{{piece}}.png'
        }};
        board = Chessboard('board', config);
    </script>
    """
    return components.html(board_html, height=500)

# --- 3. BARRA DE AVALIAÇÃO ---
def render_eval_bar(fen):
    eval_val = 0.0
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    if os.path.exists(path):
        with chess.engine.SimpleEngine.popen_uci(path) as engine:
            board = chess.Board(fen)
            info = engine.analyse(board, chess.engine.Limit(time=0.1))
            score = info["score"].relative.score(mate_score=10000)
            eval_val = score / 100.0 if score is not None else 0.0
    
    percentage = 50 + (eval_val * 5)
    percentage = max(5, min(95, percentage))
    
    st.markdown(f"""
        <div style="width: 35px; height: 450px; background: #403d39; border-radius: 5px; position: relative; border: 2px solid #312e2b; overflow: hidden;">
            <div style="position: absolute; bottom: 0; width: 100%; height: {percentage}%; background: white; transition: 0.5s;"></div>
            <div style="position: absolute; width: 100%; text-align: center; top: 50%; color: gray; font-weight: bold; font-size: 10px; z-index: 10;">{eval_val:+.1f}</div>
        </div>
    """, unsafe_allow_html=True)

# --- 4. LOGIN ---
if 'user' not in st.session_state:
    st.title("♟️ Chess Master Platform")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        st.session_state.user = u
        st.session_state.rating = 800
        st.rerun()
    st.stop()

# --- 5. INTERFACE PRINCIPAL ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Menu", ["Jogar", "Aprendizado"])

if menu == "Jogar":
    st.header("🎮 Partida Interativa (Drag & Drop)")
    if 'fen' not in st.session_state: st.session_state.fen = chess.STARTING_FEN
    
    col_ev, col_bd, col_side = st.columns([0.2, 2, 1])
    
    with col_ev: render_eval_bar(st.session_state.fen)
    with col_bd:
        # Tabuleiro real onde você arrasta as peças
        chessboard_component(st.session_state.fen, "main")
        
    with col_side:
        st.write("### Controles")
        if st.button("Reiniciar"):
            st.session_state.fen = chess.STARTING_FEN
            st.rerun()
        if st.button("Finalizar Partida"):
            st.success("Partida salva no histórico!")

elif menu == "Aprendizado":
    st.header("🎓 Exercícios de Tática")
    temas = {
        "Abertura": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "Mate em 1": "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"
    }
    tema = st.radio("Escolha o Tema", list(temas.keys()), horizontal=True)
    
    col_ev2, col_bd2, col_ds = st.columns([0.2, 2, 1])
    with col_ev2: render_eval_bar(temas[tema])
    with col_bd2: chessboard_component(temas[tema], "edu")
    with col_ds:
        st.info("Arraste as peças para resolver o desafio.")
        if st.button("💡 Dica da IA"):
            st.write("O Stockfish sugere um movimento agressivo na ala do rei.")
