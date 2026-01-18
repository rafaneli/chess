import streamlit as st
import chess
import chess.engine
import chess.pgn
import pandas as pd
import sqlite3
import hashlib
import shutil
import os
import base64
from io import StringIO
import streamlit.components.v1 as components

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Chess Master Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stButton>button { background-color: #81b64c; color: white; border-radius: 5px; font-weight: bold; width: 100%; }
    /* Barra de Avaliação Lateral */
    .eval-container {
        width: 35px; height: 450px; background-color: #403d39;
        border-radius: 5px; position: relative; overflow: hidden; border: 2px solid #312e2b;
    }
    .eval-white {
        position: absolute; bottom: 0; width: 100%;
        background-color: white; transition: height 0.5s ease-in-out;
    }
    .eval-text {
        position: absolute; width: 100%; text-align: center;
        font-weight: bold; color: #262421; z-index: 10; font-size: 11px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('chess_final.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, pgn TEXT, result TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

init_db()

def get_engine():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return chess.engine.SimpleEngine.popen_uci(path) if os.path.exists(path) else None

# --- LOGIN / CADASTRO ---
if 'user' not in st.session_state:
    st.title("♟️ Chess Master Platform")
    t1, t2 = st.tabs(["Login", "Cadastro"])
    with t1:
        u = st.text_input("Usuário", key="login_u")
        p = st.text_input("Senha", type="password", key="login_p")
        if st.button("Entrar"):
            conn = sqlite3.connect('chess_final.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
    with t2:
        nu = st.text_input("Novo Usuário", key="reg_u")
        np = st.text_input("Senha", type="password", key="reg_p")
        if st.button("Cadastrar"):
            try:
                conn = sqlite3.connect('chess_final.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hashlib.sha256(np.encode()).hexdigest()))
                conn.commit()
                st.success("Conta criada! Use a aba Login.")
            except: st.error("Erro no cadastro.")
    st.stop()

# --- BARRA DE AVALIAÇÃO ---
def render_eval_bar(fen):
    engine = get_engine()
    eval_val = 0.0
    if engine:
        board = chess.Board(fen)
        try:
            info = engine.analyse(board, chess.engine.Limit(time=0.1))
            score = info["score"].relative.score(mate_score=10000)
            eval_val = score / 100.0 if score is not None else 0.0
        finally: engine.quit()
    
    percentage = 50 + (eval_val * 5)
    percentage = max(5, min(95, percentage))
    st.markdown(f"""
        <div class="eval-container">
            <div class="eval-text" style="bottom: {percentage}%;">{eval_val:+.1f}</div>
            <div class="eval-white" style="height: {percentage}%;"></div>
        </div>
    """, unsafe_allow_html=True)

# --- TABULEIRO JOGÁVEL (COMPONENTE ESTÁVEL) ---
def chess_board_interface(fen, orientation="white"):
    # Renderizamos um tabuleiro SVG com interação simples via clique
    board = chess.Board(fen)
    board_svg = chess.svg.board(board=board, orientation=chess.WHITE if orientation == "white" else chess.BLACK, size=450).encode("utf-8")
    b64 = base64.b64encode(board_svg).decode("utf-8")
    
    st.markdown(f'<div style="display:flex;justify-content:center;"><img src="data:image/svg+xml;base64,{b64}" style="width:100%;max-width:450px;border-radius:5px;"/></div>', unsafe_allow_html=True)
    
    # Input de lance (Interface de clique virá via expansão futura, por enquanto usamos SAN estável)
    move_txt = st.text_input("Sua jogada (ex: e4, Nf3, O-O):", key=f"move_{fen}")
    if move_txt:
        try:
            board.push_san(move_txt)
            return board.fen()
        except:
            st.warning("Lance ilegal ou inválido.")
    return fen

# --- MENU PRINCIPAL ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Menu", ["Jogar", "Aprendizado", "Histórico"])

if menu == "Jogar":
    st.header("🎮 Partida Local")
    if 'fen' not in st.session_state: st.session_state.fen = chess.STARTING_FEN
    
    col_ev, col_bd, col_ctrl = st.columns([0.2, 2, 1])
    
    with col_ev: render_eval_bar(st.session_state.fen)
    
    with col_bd:
        cor = st.radio("Cor:", ["Brancas", "Pretas"], horizontal=True)
        new_fen = chess_board_interface(st.session_state.fen, orientation=cor.lower())
        if new_fen != st.session_state.fen:
            st.session_state.fen = new_fen
            st.rerun()

    with col_ctrl:
        st.subheader("Controles")
        if st.button("Reiniciar Partida"):
            st.session_state.fen = chess.STARTING_FEN
            st.rerun()
        
        st.divider()
        op = st.text_input("Oponente", "Computador")
        if st.button("Finalizar e Ganhar ELO"):
            conn = sqlite3.connect('chess_final.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user if cor == "Brancas" else op, op if cor == "Brancas" else st.session_state.user, st.session_state.fen, "1-0"))
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username=?', (st.session_state.user,))
            conn.commit()
            st.session_state.rating += 15
            st.success("Jogo salvo!")

elif menu == "Aprendizado":
    st.header("🎓 Centro de Treinamento")
    desafios = {
        "Abertura (Italiana)": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
        "Tática (Mate em 1)": "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"
    }
    tema = st.selectbox("Tema", list(desafios.keys()))
    
    col_ev, col_bd, col_ds = st.columns([0.2, 2, 1])
    with col_ev: render_eval_bar(desafios[tema])
    with col_bd: 
        st.write("Analise a posição abaixo:")
        chess_board_interface(desafios[tema])
    with col_ds:
        if st.button("Dica da IA"):
            engine = get_engine()
            if engine:
                board = chess.Board(desafios[tema])
                res = engine.analyse(board, chess.engine.Limit(time=1.0))
                st.success(f"O melhor lance é: **{board.san(res['pv'][0])}**")
                engine.quit()

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
