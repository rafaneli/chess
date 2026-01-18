import streamlit as st
import chess
import chess.svg
import chess.engine
import pandas as pd
import sqlite3
import hashlib
import shutil
import os
import random
import base64
from io import StringIO

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="Chess Master Pro", layout="wide")

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

# --- 2. SISTEMA DE LOGIN / CADASTRO ---
if 'user' not in st.session_state:
    st.title("♟️ Chess Master Platform")
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
                st.success("Cadastrado com sucesso!")
            except: st.error("Usuário já existe.")
    st.stop()

# --- 3. GERADOR DE EXERCÍCIOS "INFINITOS" ---
# Base de dados de sementes (FENs iniciais) para o gerador
FEN_SEEDS = {
    "Aberturas": [
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1",
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
    ],
    "Táticas": [
        "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
        "r1bqkbnr/p1pp1ppp/1pn5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4",
        "3r2k1/1p3ppp/8/8/8/8/1P3PPP/3R2K1 w - - 0 1"
    ],
    "Finais": [
        "8/8/8/8/8/4k3/8/R3K3 w - - 0 1",
        "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1",
        "8/8/k7/8/8/8/1R6/1K6 w - - 0 1"
    ],
    "Aproveite o Erro": [
        "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 1 4"
    ]
}

def carregar_novo_desafio(tema):
    # Seleciona uma semente aleatória e define como o desafio atual
    st.session_state.fen_desafio = random.choice(FEN_SEEDS[tema])
    st.session_state.solucao_desafio = None

# --- 4. INTERFACE ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Menu", ["Jogar Partida", "Aprendizado IA", "Histórico"])

if menu == "Aprendizado IA":
    st.header("🎓 Centro de Treinamento Infinito")
    
    tema = st.radio("Escolha o Tema:", list(FEN_SEEDS.keys()), horizontal=True)
    
    # Inicializa o desafio se não existir ou se o tema mudou
    if 'fen_desafio' not in st.session_state or st.sidebar.button("🔄 Resetar Sessão"):
        carregar_novo_desafio(tema)

    col_board, col_info = st.columns([2, 1])

    with col_board:
        board = chess.Board(st.session_state.fen_desafio)
        board_svg = chess.svg.board(board=board, size=450).encode("utf-8")
        st.image(f"data:image/svg+xml;base64,{base64.b64encode(board_svg).decode('utf-8')}", use_column_width=False)
        
        if st.button("Próximo Exercício ➡️"):
            carregar_novo_desafio(tema)
            st.rerun()

    with col_info:
        st.markdown(f"### Desafio: {tema}")
        st.write("Analise a posição no tabuleiro. O que você faria?")
        
        if st.button("🔍 Revelar Solução da IA"):
            engine = get_engine()
            if engine:
                with st.spinner("O Professor está calculando..."):
                    result = engine.analyse(board, chess.engine.Limit(time=1.0))
                    best_move = board.san(result["pv"][0])
                    st.session_state.solucao_desafio = best_move
                    st.success(f"O melhor lance nesta posição é: **{best_move}**")
                engine.quit()
            else:
                st.error("Motor Stockfish indisponível.")

elif menu == "Jogar Partida":
    st.header("🎮 Jogo Local")
    if 'game_fen' not in st.session_state: st.session_state.game_fen = chess.STARTING_FEN
    
    board = chess.Board(st.session_state.game_fen)
    col_b, col_c = st.columns([2, 1])
    
    with col_b:
        board_svg = chess.svg.board(board=board, size=500).encode("utf-8")
        st.image(f"data:image/svg+xml;base64,{base64.b64encode(board_svg).decode('utf-8')}")
    
    with col_c:
        move = st.text_input("Seu Lance (ex: e4, Nf3):")
        if st.button("Confirmar"):
            try:
                board.push_san(move)
                st.session_state.game_fen = board.fen()
                st.rerun()
            except: st.error("Lance ilegal.")
        
        if st.button("Finalizar Partida"):
            conn = sqlite3.connect('chess_master.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user, "Oponente", board.fen(), "1-0"))
            conn.execute('UPDATE users SET rating = rating + 10 WHERE username=?', (st.session_state.user,))
            conn.commit()
            st.session_state.rating += 10
            st.success("Rating Atualizado!")

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
