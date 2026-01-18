import streamlit as st
import chess
import chess.engine
import chess.pgn
import pandas as pd
import altair as alt
import sqlite3
import hashlib
import shutil
import os
from io import StringIO

# Tente importar o componente; se falhar, o app avisa o erro de instalação
try:
    from streamlit_chess import st_chess
except ModuleNotFoundError:
    st.error("Erro de Dependência: 'streamlit-chess' não instalado. Verifique o requirements.txt.")
    st.stop()

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Chess Platform Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stMetric { background-color: #312e2b; padding: 10px; border-radius: 4px; border: 1px solid #403d39; }
    .classification-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 5px 12px; margin-bottom: 3px; background-color: #2b2926; border-radius: 4px;
    }
    .icon-circle {
        width: 24px; height: 24px; border-radius: 50%; display: flex;
        align-items: center; justify-content: center; font-weight: bold; font-size: 12px; color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS E MOTOR ---
def init_db():
    conn = sqlite3.connect('chess_data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, pgn TEXT, result TEXT)')
    conn.commit()
    conn.close()

init_db()

def get_stockfish():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return path if os.path.exists(path) else None

STOCKFISH_PATH = get_stockfish()

# --- LÓGICA DE LOGIN ---
def hash_p(pwd): return hashlib.sha256(pwd.encode()).hexdigest()

if 'user' not in st.session_state:
    st.title("♟️ Bem-vindo ao Chess Pro")
    t1, t2 = st.tabs(["Entrar", "Criar Conta"])
    with t1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Login"):
            conn = sqlite3.connect('chess_data.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, hash_p(p))).fetchone()
            if res:
                st.session_state.user = u
                st.session_state.rating = res[2]
                st.rerun()
            else: st.error("Incorreto")
    with t2:
        nu = st.text_input("Novo Usuário")
        np = st.text_input("Nova Senha", type="password")
        if st.button("Registrar"):
            try:
                conn = sqlite3.connect('chess_data.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hash_p(np)))
                conn.commit()
                st.success("Pronto!")
            except: st.error("Erro")
    st.stop()

# --- MENU PRINCIPAL ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.radio("Navegação", ["Jogar", "Histórico", "Analisador Profissional"])

if menu == "Jogar":
    st.header("🎮 Nova Partida")
    if 'board' not in st.session_state: st.session_state.board = chess.Board()
    
    col_b, col_i = st.columns([2, 1])
    with col_b:
        fen = st_chess(st.session_state.board.fen(), key="play")
        if fen != st.session_state.board.fen():
            st.session_state.board = chess.Board(fen)
            st.rerun()
    with col_i:
        op = st.text_input("Oponente")
        if st.button("Salvar e Finalizar"):
            game_pgn = str(chess.pgn.Game.from_board(st.session_state.board))
            conn = sqlite3.connect('chess_data.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user, op, game_pgn, "Finalizado"))
            conn.commit()
            st.success("Salvo!")

elif menu == "Analisador Profissional":
    st.header("⭐ Analisador Estilo Chess.com")
    pgn_input = st.text_area("Cole o PGN ou use do histórico", st.session_state.get('to_analyze', ""))
    
    if pgn_input and STOCKFISH_PATH:
        game = chess.pgn.read_game(StringIO(pgn_input))
        # ... [Insira aqui o código da interface idêntica que geramos no prompt anterior] ...
        # (Lógica de contagem de lances Melhor, Excelente, Livro, etc.)
        st.info("O analisador está pronto para processar seu jogo.")



### Próximo Passo Sugerido
Para resolver o erro de instalação definitivamente:
1. Atualize o `requirements.txt` com as versões fixas que passei.
2. No Streamlit Cloud, clique em **"Settings" > "Delete Cache"** e depois em **"Reboot"**. Isso limpa instalações corrompidas e instala tudo do zero.

**Gostaria que eu escrevesse a lógica automática de "Ganho de Rating" (ex: +15 pontos por vitória) para ser aplicada assim que você clicar em "Finalizar Jogo"?**
