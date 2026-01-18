import streamlit as st
import chess
import chess.engine
import sqlite3
import hashlib
import requests
import pandas as pd
import shutil
import os
from st_chess import chess_board # Componente estável para tabuleiro jogável

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Chess Master Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stButton>button { background-color: #81b64c; color: white; border-radius: 5px; font-weight: bold; width: 100%; }
    /* Estilo da Barra de Avaliação Lateral */
    .eval-container {
        width: 30px; height: 400px; background-color: #403d39;
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

# --- 2. BANCO DE DADOS E MOTOR ---
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
    if os.path.exists(path):
        return chess.engine.SimpleEngine.popen_uci(path)
    return None

# --- 3. SISTEMA DE ACESSO ---
if 'user' not in st.session_state:
    st.title("♟️ Chess Master Platform")
    t1, t2 = st.tabs(["🔐 Login", "📝 Cadastro"])
    with t1:
        u = st.text_input("Usuário", key="l_u")
        p = st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar"):
            conn = sqlite3.connect('chess_master.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
    with t2:
        nu = st.text_input("Novo Usuário", key="r_u")
        np = st.text_input("Nova Senha", type="password", key="r_p")
        if st.button("Criar Conta"):
            try:
                conn = sqlite3.connect('chess_master.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hashlib.sha256(np.encode()).hexdigest()))
                conn.commit()
                st.success("Cadastro realizado!")
            except: st.error("Erro no cadastro.")
    st.stop()

# --- 4. FUNÇÃO DA BARRA DE AVALIAÇÃO ---
def render_eval_bar(fen):
    eval_val = 0.0
    engine = get_engine()
    if engine:
        board = chess.Board(fen)
        try:
            info = engine.analyse(board, chess.engine.Limit(time=0.1))
            score = info["score"].relative.score(mate_score=10000)
            eval_val = score / 100.0 if score is not None else 0.0
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

# --- 5. MENU PRINCIPAL ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Navegação", ["Jogar", "Aprendizado IA", "Leaderboard"])

if menu == "Jogar":
    st.header("🎮 Partida Local Interativa")
    if 'fen' not in st.session_state: st.session_state.fen = chess.STARTING_FEN
    
    col_ev, col_bd, col_side = st.columns([0.2, 2, 1])
    
    with col_ev:
        render_eval_bar(st.session_state.fen)
    
    with col_bd:
        # Tabuleiro Jogável (clicar e arrastar)
        # Este componente retorna o novo FEN após o movimento
        new_fen = chess_board(fen=st.session_state.fen, key="main_game")
        if new_fen != st.session_state.fen:
            st.session_state.fen = new_fen
            st.rerun()

    with col_side:
        if st.button("🔄 Reiniciar Jogo"):
            st.session_state.fen = chess.STARTING_FEN
            st.rerun()
        
        st.divider()
        op = st.text_input("Oponente", "Computador")
        if st.button("🏆 Finalizar e Ganhar Rating"):
            conn = sqlite3.connect('chess_master.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', (st.session_state.user, op, st.session_state.fen, "1-0"))
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username=?', (st.session_state.user,))
            conn.commit()
            st.session_state.rating += 15
            st.success("Rating Atualizado!")

elif menu == "Aprendizado IA":
    st.header("🎓 Treinamento de Tática")
    # Busca um puzzle aleatório (FEN) da nossa base interna ou API externa
    if 'puzzle_fen' not in st.session_state:
        st.session_state.puzzle_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"
    
    col_ev2, col_bd2, col_side2 = st.columns([0.2, 2, 1])
    
    with col_ev2:
        render_eval_bar(st.session_state.puzzle_fen)
        
    with col_bd2:
        new_edu_fen = chess_board(fen=st.session_state.puzzle_fen, key="edu_game")
        if new_edu_fen != st.session_state.puzzle_fen:
            st.session_state.puzzle_fen = new_edu_fen
            st.rerun()
            
    with col_side2:
        if st.button("🎯 Próximo Exercício"):
            # Aqui você pode adicionar lógica para trocar o FEN
            st.session_state.puzzle_fen = "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"
            st.rerun()
        
        if st.button("💡 Dica da IA"):
            engine = get_engine()
            if engine:
                board = chess.Board(st.session_state.puzzle_fen)
                res = engine.analyse(board, chess.engine.Limit(time=0.5))
                st.info(f"O Professor sugere: {board.san(res['pv'][0])}")
                engine.quit()

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
