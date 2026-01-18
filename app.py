import streamlit as st
import chess
import chess.engine
import pandas as pd
import sqlite3
import hashlib
import shutil
import os
from io import StringIO
import streamlit.components.v1 as components

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="Chess Pro Platform", layout="wide")

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

# --- 2. SISTEMA DE LOGIN/CADASTRO ---
if 'user' not in st.session_state:
    st.title("♟️ Chess Master Pro")
    t1, t2 = st.tabs(["Login", "Cadastro"])
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
        if st.button("Cadastrar"):
            try:
                conn = sqlite3.connect('chess_master.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hashlib.sha256(np.encode()).hexdigest()))
                conn.commit()
                st.success("Cadastrado! Use a aba Login.")
            except: st.error("Erro no cadastro.")
    st.stop()

# --- 3. COMPONENTE DE TABULEIRO INTERATIVO (JS) ---
def jogavel_board(fen, key):
    # Tabuleiro interativo que retorna o lance para o Streamlit
    board = chess.Board(fen)
    legal_moves = [move.uci() for move in board.legal_moves]
    
    # HTML/JS para o tabuleiro interativo
    board_html = f"""
    <div id="board_{key}" style="width: 400px; height: 400px; background: #312e2b; border: 2px solid #555;">
        <p style="color: white; text-align: center; padding-top: 150px;">
            Clique para interagir (Simulação de Tabuleiro Ativa)<br>
            FEN: {fen}
        </p>
    </div>
    <script>
        // Aqui o componente se comunica com o Python enviando o lance escolhido
        const move = window.prompt("Digite o lance (ex: e2e4, e7e5):");
        if (move) window.parent.postMessage({{type: 'streamlit:setComponentValue', value: move}}, '*');
    </script>
    """
    # Para manter o tabuleiro real e jogável sem quebrar o Streamlit:
    st.write(f"Vez de: **{'Brancas' if board.turn else 'Pretas'}**")
    import chess.svg
    board_svg = chess.svg.board(board=board, size=400)
    st.image(f"data:image/svg+xml;base64,{hashlib.md5(board_svg.encode()).hexdigest()}") # Representação visual
    
    res = st.text_input("Mova sua peça (Notação UCI, ex: e2e4):", key=f"input_{key}")
    return res

# --- 4. MENU E FUNCIONALIDADES ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Menu", ["Jogar", "Aprendizado", "Análise"])

# --- ABA JOGAR ---
if menu == "Jogar":
    st.header("🎮 Partida Local")
    if 'fen' not in st.session_state: st.session_state.fen = chess.STARTING_FEN
    
    col_ev, col_bd, col_ctrl = st.columns([0.2, 2, 1])
    
    with col_bd:
        move = st.text_input("Seu Lance (ex: e2e4, Nf3):", key="play_move")
        if st.button("Confirmar Lance"):
            board = chess.Board(st.session_state.fen)
            try:
                board.push_san(move)
                st.session_state.fen = board.fen()
                st.rerun()
            except: st.error("Lance ilegal.")
        
        import chess.svg
        st.image(chess.svg.board(board=chess.Board(st.session_state.fen), size=450), use_column_width=False)

# --- ABA APRENDIZADO (COM TROCA DE EXERCÍCIOS) ---
elif menu == "Aprendizado":
    st.header("🎓 Centro de Treinamento")
    
    temas = {
        "Aberturas": ["r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3", "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1"],
        "Táticas": ["6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", "r1bqkbnr/p1pp1ppp/1pn5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"],
        "Finais": ["8/8/8/8/8/4k3/8/R3K3 w - - 0 1", "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"]
    }
    
    tema_escolhido = st.radio("Escolha o Tema:", list(temas.keys()), horizontal=True)
    
    # Sistema para trocar exercícios dentro do tema
    if f"idx_{tema_escolhido}" not in st.session_state:
        st.session_state[f"idx_{tema_escolhido}"] = 0
    
    idx = st.session_state[f"idx_{tema_escolhido}"]
    fen_atual = temas[tema_escolhido][idx]
    
    col_board, col_info = st.columns([2, 1])
    
    with col_board:
        import chess.svg
        st.image(chess.svg.board(board=chess.Board(fen_atual), size=400))
        
        if st.button("Próximo Exercício ➡️"):
            st.session_state[f"idx_{tema_escolhido}"] = (idx + 1) % len(temas[tema_escolhido])
            st.rerun()

    with col_info:
        st.info("Resolva a posição ou use a IA.")
        if st.button("Dica do Stockfish"):
            engine = get_engine()
            if engine:
                board = chess.Board(fen_atual)
                res = engine.analyse(board, chess.engine.Limit(time=1.0))
                st.success(f"Melhor lance: **{board.san(res['pv'][0])}**")
                engine.quit()

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
