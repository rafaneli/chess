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
st.set_page_config(page_title="Chess Pro: Play & Learn", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stButton>button { background-color: #81b64c; color: white; border-radius: 5px; font-weight: bold; }
    .stMetric { background-color: #312e2b; padding: 10px; border-radius: 4px; border: 1px solid #403d39; }
    .player-card { background-color: #312e2b; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
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

# --- MOTOR ---
def get_engine():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return chess.engine.SimpleEngine.popen_uci(path) if os.path.exists(path) else None

# --- LOGIN ---
if 'user' not in st.session_state:
    st.title("♟️ Chess Pro Platform")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    with t1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect('chess_master.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
    st.stop()

# --- MENU ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Navegação", ["Jogar Partida", "Aprendizado", "Histórico & Análise"])

def render_board_svg(board):
    board_svg = chess.svg.board(board=board, size=450).encode("utf-8")
    b64 = base64.b64encode(board_svg).decode("utf-8")
    return f'<div style="display:flex;justify-content:center;"><img src="data:image/svg+xml;base64,{b64}" style="width:100%;max-width:450px;border-radius:5px;"/></div>'

# --- ABA: JOGAR ---
if menu == "Jogar Partida":
    st.header("🎮 Partida Local Interativa")
    if 'game_board' not in st.session_state: st.session_state.game_board = chess.Board()
    
    col_b, col_c = st.columns([2, 1])
    with col_b:
        st.markdown(render_board_svg(st.session_state.game_board), unsafe_allow_html=True)
    
    with col_c:
        st.write("### Suas Jogadas")
        move = st.text_input("Digite o lance (ex: e4, Nf3)", key="play_move")
        if st.button("Executar Lance"):
            try:
                st.session_state.game_board.push_san(move)
                st.rerun()
            except: st.error("Lance inválido")
        
        if st.button("Reiniciar Jogo"):
            st.session_state.game_board = chess.Board()
            st.rerun()

        st.divider()
        op = st.text_input("Oponente")
        if st.button("Salvar e Pontuar"):
            pgn = str(chess.pgn.Game.from_board(st.session_state.game_board))
            conn = sqlite3.connect('chess_master.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', (st.session_state.user, op, pgn, "Finalizado"))
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username=?', (st.session_state.user,))
            conn.commit()
            st.session_state.rating += 15
            st.success("Vitória! +15 de Rating")

# --- ABA: APRENDIZADO ---
elif menu == "Aprendizado":
    st.header("🎓 Centro de Treinamento IA")
    
    # Desafios pré-definidos (FENs)
    desafios = {
        "Aberturas": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "Táticas (Mates)": "6k1/5ppp/8/8/8/8/5PPP/6K1 w - - 0 1",
        "Fins de Jogo": "8/8/8/8/8/4k3/8/4K2R w K - 0 1"
    }
    
    tema = st.radio("Escolha o Tema", list(desafios.keys()), horizontal=True)
    
    col_t, col_s = st.columns([2, 1])
    with col_t:
        board_edu = chess.Board(desafios[tema])
        st.markdown(render_board_svg(board_edu), unsafe_allow_html=True)
    
    with col_s:
        st.info("Utilize o Stockfish para encontrar a solução mestre desta posição.")
        if st.button("Analisar com Stockfish"):
            engine = get_engine()
            if engine:
                with st.spinner("IA calculando..."):
                    res = engine.analyse(board_edu, chess.engine.Limit(time=1.0))
                    best = board_edu.san(res["pv"][0])
                    st.success(f"O melhor lance é: **{best}**")
                    engine.quit()
            else: st.error("Motor indisponível")

# --- HISTÓRICO ---
elif menu == "Histórico & Análise":
    st.header("🕒 Histórico Profissional")
    conn = sqlite3.connect('chess_master.db')
    df = pd.read_sql(f"SELECT id, white, black, result, date FROM games WHERE white='{st.session_state.user}'", conn)
    st.table(df)
    
    game_id = st.number_input("ID para Análise", step=1)
    if st.button("Abrir Analisador"):
        st.info("Carregando motor para revisão completa...")
