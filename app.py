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
from streamlit_chess import st_chess

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Chess Pro Platform", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    /* Estilo da Barra de Avaliação */
    .eval-container {
        width: 30px; height: 450px; background-color: #403d39;
        border-radius: 5px; position: relative; overflow: hidden; border: 2px solid #312e2b;
    }
    .eval-white {
        position: absolute; bottom: 0; width: 100%;
        background-color: white; transition: height 0.5s ease-in-out;
    }
    .eval-text {
        position: absolute; width: 100%; text-align: center;
        font-weight: bold; color: #262421; z-index: 10; font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS E MOTOR ---
def init_db():
    conn = sqlite3.connect('chess_pro.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, pgn TEXT, result TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

init_db()

def get_engine():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return chess.engine.SimpleEngine.popen_uci(path) if os.path.exists(path) else None

# --- 3. LOGLOGICA DE ACESSO ---
if 'user' not in st.session_state:
    st.title("♟️ Chess Master Pro")
    t1, t2 = st.tabs(["Login", "Registo"])
    with t1:
        u = st.text_input("Utilizador", key="l_u")
        p = st.text_input("Palavra-passe", type="password", key="l_p")
        if st.button("Entrar"):
            conn = sqlite3.connect('chess_pro.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
    with t2:
        nu = st.text_input("Novo Utilizador", key="r_u")
        np = st.text_input("Nova Palavra-passe", type="password", key="r_p")
        if st.button("Criar Conta"):
            try:
                conn = sqlite3.connect('chess_pro.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hashlib.sha256(np.encode()).hexdigest()))
                conn.commit()
                st.success("Conta criada!")
            except: st.error("Erro no registo.")
    st.stop()

# --- 4. INTERFACE PRINCIPAL ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Menu", ["Jogar", "Aprendizado", "Histórico"])

# Função para a Barra de Avaliação
def render_eval_bar(fen):
    engine = get_engine()
    eval_val = 0.0
    display_text = "0.0"
    if engine:
        board = chess.Board(fen)
        info = engine.analyse(board, chess.engine.Limit(time=0.1))
        score = info["score"].relative.score(mate_score=10000)
        eval_val = score / 100.0 if score is not None else 0.0
        display_text = f"{eval_val:+.1f}" if abs(eval_val) < 10 else ("M" if eval_val > 0 else "-M")
        engine.quit()
    
    # Converter eval para percentagem (0% a 100%)
    percentage = 50 + (eval_val * 5) # 1 ponto = 5% de deslocamento
    percentage = max(5, min(95, percentage)) # Limites
    
    st.markdown(f"""
        <div class="eval-container">
            <div class="eval-text" style="bottom: {percentage}%;">{display_text}</div>
            <div class="eval-white" style="height: {percentage}%;"></div>
        </div>
    """, unsafe_allow_html=True)

# --- ABA JOGAR ---
if menu == "Jogar":
    st.header("🎮 Partida Interativa")
    if 'fen' not in st.session_state: st.session_state.fen = chess.STARTING_FEN
    
    col_eval, col_board, col_tools = st.columns([0.2, 2, 1])
    
    with col_eval:
        render_eval_bar(st.session_state.fen)
    
    with col_board:
        cor = st.radio("Cor:", ["Brancas", "Pretas"], horizontal=True)
        # Tabuleiro Jogável Drag & Drop
        new_fen = st_chess(
            fen=st.session_state.fen,
            orientation="white" if cor == "Brancas" else "black",
            key="game_board"
        )
        if new_fen != st.session_state.fen:
            st.session_state.fen = new_fen
            st.rerun()

    with col_tools:
        st.subheader("Ferramentas")
        if st.button("Reiniciar"):
            st.session_state.fen = chess.STARTING_FEN
            st.rerun()
        
        st.divider()
        op = st.text_input("Oponente", "Computador")
        if st.button("Finalizar e Pontuar"):
            conn = sqlite3.connect('chess_pro.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user if cor == "Brancas" else op, op if cor == "Brancas" else st.session_state.user, st.session_state.fen, "1-0"))
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username=?', (st.session_state.user,))
            conn.commit()
            st.session_state.rating += 15
            st.success("ELO Atualizado!")

# --- ABA APRENDIZADO ---
elif menu == "Aprendizado":
    st.header("🎓 Desafios de IA")
    desafios = {
        "Aberturas (Italiana)": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
        "Tática (Mate em 1)": "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
        "Final de Torres": "8/8/8/8/8/4k3/8/R3K3 w - - 0 1"
    }
    tema = st.selectbox("Escolha o Tema", list(desafios.keys()))
    
    col_ev, col_bd, col_ds = st.columns([0.2, 2, 1])
    
    with col_ev:
        render_eval_bar(st.session_state.get('edu_fen', desafios[tema]))
    
    with col_bd:
        edu_fen = st_chess(fen=desafios[tema], key="edu_board")
        st.session_state.edu_fen = edu_fen
        
    with col_ds:
        st.info("Mova as peças para resolver. A barra ao lado mostra a vantagem em tempo real.")
        if st.button("Dica Mestre"):
            engine = get_engine()
            if engine:
                board = chess.Board(edu_fen)
                res = engine.analyse(board, chess.engine.Limit(time=1.0))
                st.success(f"Sugestão: **{board.san(res['pv'][0])}**")
                engine.quit()

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
