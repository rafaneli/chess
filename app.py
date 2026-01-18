import streamlit as st
import chess
import chess.svg
import chess.engine
import chess.pgn
import pandas as pd
import sqlite3
import hashlib
import shutil
import os
import base64
from io import StringIO

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Chess Pro Platform", layout="wide")

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

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('chess_data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, pgn TEXT, result TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- MOTOR ---
def get_stockfish():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return path if os.path.exists(path) else None

STOCKFISH_PATH = get_stockfish()

# --- SISTEMA DE LOGIN ---
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
            conn.close()
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
                conn.close()
                st.success("Conta criada!")
            except: st.error("Usuário já existe")
    st.stop()

# --- MENU ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.radio("Navegação", ["Jogar Partida", "Histórico de Jogos", "Analisador Profissional"])

# --- FUNÇÃO PARA RENDERIZAR TABULEIRO ---
def render_board(board):
    board_svg = chess.svg.board(board=board).encode("utf-8")
    b64 = base64.b64encode(board_svg).decode("utf-8")
    return f'<img src="data:image/svg+xml;base64,{b64}" style="width:100%; max-width:500px;"/>'

if menu == "Jogar Partida":
    st.header("🎮 Nova Partida Local")
    if 'board' not in st.session_state: st.session_state.board = chess.Board()
    
    col_b, col_i = st.columns([2, 1])
    with col_b:
        st.markdown(render_board(st.session_state.board), unsafe_allow_html=True)
    
    with col_i:
        move = st.text_input("Digite seu lance (ex: e2e4)")
        if st.button("Fazer Lance"):
            try:
                m = st.session_state.board.parse_san(move)
                st.session_state.board.push(m)
                st.rerun()
            except: st.error("Lance inválido")
        
        op = st.text_input("Oponente (Registrado)")
        if st.button("Finalizar e Ganhar Rating"):
            # Salva jogo
            game_pgn = str(chess.pgn.Game.from_board(st.session_state.board))
            conn = sqlite3.connect('chess_data.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user, op, game_pgn, "1-0"))
            # Atualiza Rating (+15)
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username = ?', (st.session_state.user,))
            conn.commit()
            conn.close()
            st.session_state.rating += 15
            st.success("Vitória registrada! +15 de Rating.")
            del st.session_state.board

elif menu == "Histórico de Jogos":
    st.header("📚 Suas Partidas")
    conn = sqlite3.connect('chess_data.db')
    df = pd.read_sql(f"SELECT id, white, black, result, date FROM games WHERE white='{st.session_state.user}' OR black='{st.session_state.user}'", conn)
    conn.close()
    if not df.empty:
        st.table(df)
        game_id = st.number_input("ID do jogo para analisar", min_value=int(df['id'].min()), max_value=int(df['id'].max()))
        if st.button("Enviar para o Analisador"):
            conn = sqlite3.connect('chess_data.db')
            st.session_state.to_analyze = conn.execute(f"SELECT pgn FROM games WHERE id={game_id}").fetchone()[0]
            conn.close()
            st.info("Carregado! Mude para a aba Analisador.")
    else: st.write("Nenhum jogo encontrado.")

elif menu == "Analisador Profissional":
    st.header("⭐ Revisão da Partida")
    pgn_data = st.session_state.get('to_analyze', None)
    if pgn_data and STOCKFISH_PATH:
        st.success("Análise disponível para o PGN carregado.")
        # [AQUI VAI A LÓGICA DE CARDS COLORIDOS E STOCKFISH QUE CRIAMOS]
        st.text_area("Dados PGN", pgn_data, height=150)
    else:
        st.warning("Carregue uma partida do histórico primeiro.")

if st.sidebar.button("Sair"):
    del st.session_state.user
    st.rerun()
