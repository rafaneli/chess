import streamlit as st
import chess
import chess.engine
import chess.pgn
import pandas as pd
import sqlite3
import hashlib
import shutil
import os
from io import StringIO
from streamlit_chess import st_chess # Componente para movimentos Drag & Drop

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Chess Master Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stButton>button { background-color: #81b64c; color: white; border-radius: 5px; font-weight: bold; width: 100%; }
    .stMetric { background-color: #312e2b; padding: 10px; border-radius: 4px; border: 1px solid #403d39; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('chess_master.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('''CREATE TABLE IF NOT EXISTS games 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, 
                  pgn TEXT, result TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. MOTOR STOCKFISH ---
def get_engine():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    if os.path.exists(path):
        return chess.engine.SimpleEngine.popen_uci(path)
    return None

# --- 4. SISTEMA DE ACESSO ---
if 'user' not in st.session_state:
    st.title("♟️ Bem-vindo ao Chess Pro")
    tab_login, tab_cadastro = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
    
    with tab_login:
        u = st.text_input("Usuário", key="login_u")
        p = st.text_input("Senha", type="password", key="login_p")
        if st.button("Entrar"):
            conn = sqlite3.connect('chess_master.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', 
                               (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            conn.close()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
            else: st.error("Erro no login.")

    with tab_cadastro:
        nu = st.text_input("Novo Usuário", key="reg_u")
        np = st.text_input("Nova Senha", type="password", key="reg_p")
        if st.button("Cadastrar"):
            try:
                conn = sqlite3.connect('chess_master.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hashlib.sha256(np.encode()).hexdigest()))
                conn.commit()
                conn.close()
                st.success("Conta criada! Entre na aba ao lado.")
            except: st.error("Usuário já existe.")
    st.stop()

# --- 5. INTERFACE DO USUÁRIO ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Navegação", ["Jogar Partida", "Aprendizado", "Histórico"])

# --- ABA: JOGAR ---
if menu == "Jogar Partida":
    st.header("🎮 Partida Interativa")
    
    if 'board_fen' not in st.session_state:
        st.session_state.board_fen = chess.STARTING_FEN

    col_board, col_side = st.columns([2, 1])

    with col_side:
        st.write("### Configuração")
        cor_player = st.radio("Cor das peças:", ["Brancas", "Pretas"])
        op_nome = st.text_input("Oponente", value="Computador")
        
        if st.button("Reiniciar Tabuleiro"):
            st.session_state.board_fen = chess.STARTING_FEN
            st.rerun()

        st.divider()
        if st.button("Finalizar e Ganhar Rating"):
            game = chess.pgn.Game()
            game.setup(st.session_state.board_fen)
            pgn_str = str(game)
            conn = sqlite3.connect('chess_master.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user if cor_player == "Brancas" else op_nome,
                          op_nome if cor_player == "Brancas" else st.session_state.user,
                          pgn_str, "Finalizado"))
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username=?', (st.session_state.user,))
            conn.commit()
            conn.close()
            st.session_state.rating += 15
            st.success("Partida Salva! +15 de ELO.")

    with col_board:
        # Tabuleiro Jogável: Clique e arraste ou clique na peça e destino
        # O componente atualiza st.session_state.board_fen automaticamente
        new_fen = st_chess(
            fen=st.session_state.board_fen,
            orientation="white" if cor_player == "Brancas" else "black",
            key="chess_game"
        )
        
        if new_fen != st.session_state.board_fen:
            st.session_state.board_fen = new_fen
            st.rerun()

# --- ABA: APRENDIZADO ---
elif menu == "Aprendizado":
    st.header("🎓 Centro de Treinamento")
    desafios = {
        "Aberturas": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "Táticas": "6k1/5ppp/8/8/8/8/5PPP/6K1 w - - 0 1"
    }
    tema = st.selectbox("Escolha o Tema", list(desafios.keys()))
    
    col_t, col_s = st.columns([2, 1])
    
    with col_t:
        # Tabuleiro jogável também no aprendizado para testar lances
        edu_fen = st_chess(fen=desafios[tema], key="edu_board")
        
    with col_s:
        st.info("Mova as peças para testar ou peça uma dica.")
        if st.button("Dica do Stockfish"):
            engine = get_engine()
            if engine:
                board = chess.Board(edu_fen)
                res = engine.analyse(board, chess.engine.Limit(time=1.0))
                st.success(f"Melhor lance: **{board.san(res['pv'][0])}**")
                engine.quit()

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
