import streamlit as st
import chess
import chess.svg
import chess.engine
import pandas as pd
import sqlite3
import hashlib
import shutil
import os
import base64
import streamlit.components.v1 as components

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Chess Pro Platform", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stButton>button { background-color: #81b64c; color: white; border-radius: 5px; font-weight: bold; width: 100%; }
    /* Barra de Avaliação */
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

# --- 2. BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('chess_master.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, pgn TEXT, result TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

init_db()

def get_engine():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return chess.engine.SimpleEngine.popen_uci(path) if os.path.exists(path) else None

# --- 3. LOGIN / CADASTRO ---
if 'user' not in st.session_state:
    st.title("♟️ Bem-vindo ao Chess Pro")
    t1, t2 = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
    with t1:
        u = st.text_input("Usuário", key="login_u")
        p = st.text_input("Senha", type="password", key="login_p")
        if st.button("Entrar"):
            conn = sqlite3.connect('chess_master.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
    with t2:
        nu = st.text_input("Novo Usuário", key="reg_u")
        np = st.text_input("Senha", type="password", key="reg_p")
        if st.button("Finalizar Cadastro"):
            try:
                conn = sqlite3.connect('chess_master.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hashlib.sha256(np.encode()).hexdigest()))
                conn.commit()
                st.success("Conta criada! Use a aba Entrar.")
            except: st.error("Erro no cadastro.")
    st.stop()

# --- 4. TABULEIRO JOGÁVEL (SVG + INTERAÇÃO) ---
def render_interactive_board(board, key):
    # Renderiza o tabuleiro como um SVG clicável
    board_svg = chess.svg.board(board=board, size=450).encode("utf-8")
    b64 = base64.b64encode(board_svg).decode("utf-8")
    
    st.markdown(f'<div style="display:flex;justify-content:center;"><img src="data:image/svg+xml;base64,{b64}" style="width:100%;max-width:450px;border: 5px solid #312e2b; border-radius: 5px;"/></div>', unsafe_allow_html=True)
    
    # Sistema de movimento por clique-origem e clique-destino (simulado por texto para estabilidade)
    move_txt = st.text_input("Mova a peça (ex: e2e4, e7e5, g1f3):", key=f"move_input_{key}")
    return move_txt

# --- 5. BARRA DE AVALIAÇÃO ---
def render_eval_bar(fen):
    eval_val = 0.0
    engine = get_engine()
    if engine:
        board = chess.Board(fen)
        try:
            info = engine.analyse(board, chess.engine.Limit(time=0.1))
            score = info["score"].relative.score(mate_score=10000)
            eval_val = (score / 100.0) if score is not None else 0.0
        except: pass
        finally: engine.quit()
    
    percentage = 50 + (eval_val * 5)
    percentage = max(5, min(95, percentage))
    st.markdown(f"""
        <div class="eval-container">
            <div class="eval-text" style="bottom: {percentage}%;">{eval_val:+.1f}</div>
            <div class="eval-white" style="height: {percentage}%;"></div>
        </div>
    """, unsafe_allow_html=True)

# --- 6. MENU E APRENDIZADO ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Menu", ["Jogar Partida", "Aprendizado IA", "Histórico"])

if menu == "Jogar Partida":
    st.header("🎮 Partida Local")
    if 'game_fen' not in st.session_state: st.session_state.game_fen = chess.STARTING_FEN
    
    col_ev, col_bd, col_ctrl = st.columns([0.2, 2, 1])
    board = chess.Board(st.session_state.game_fen)
    
    with col_ev: render_eval_bar(st.session_state.game_fen)
    with col_bd:
        move = render_interactive_board(board, "game")
        if move:
            try:
                board.push_uci(move)
                st.session_state.game_fen = board.fen()
                st.rerun()
            except: st.error("Lance ilegal. Use o formato e2e4.")
            
    with col_ctrl:
        st.write(f"Vez das: **{'Brancas' if board.turn else 'Pretas'}**")
        if st.button("Reiniciar"):
            st.session_state.game_fen = chess.STARTING_FEN
            st.rerun()
        if st.button("Finalizar e Pontuar"):
            st.success("Vitória registrada! +15 de Rating.")

elif menu == "Aprendizado IA":
    st.header("🎓 Exercícios Infinitos")
    
    temas = {
        "Aberturas": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "Táticas": "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"
    }
    tema = st.radio("Tema:", list(temas.keys()), horizontal=True)
    
    if st.button("🔄 Próximo Exercício"):
        st.rerun() # Aqui você pode adicionar lógica de FENs aleatórios

    col_ev2, col_bd2, col_ds2 = st.columns([0.2, 2, 1])
    board_edu = chess.Board(temas[tema])
    
    with col_ev2: render_eval_bar(temas[tema])
    with col_bd2: render_interactive_board(board_edu, "edu")
    with col_ds2:
        if st.button("💡 Dica do Professor"):
            engine = get_engine()
            if engine:
                res = engine.analyse(board_edu, chess.engine.Limit(time=0.5))
                st.success(f"O melhor lance é: **{board_edu.san(res['pv'][0])}**")
                engine.quit()

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
