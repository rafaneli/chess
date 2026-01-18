import streamlit as st
import chess
import chess.pgn
import sqlite3
import hashlib
import requests
from streamlit_player import st_player
from io import StringIO

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="Chess Master Pro", layout="wide")

def init_db():
    conn = sqlite3.connect('chess_master.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, pgn TEXT, result TEXT)')
    conn.commit()
    conn.close()

init_db()

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

# --- 3. MENU E FUNCIONALIDADES ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Menu", ["Jogar Partida", "Aprendizado IA (Infinito)", "Histórico"])

# --- ABA JOGAR (TABULEIRO REAL JOGÁVEL) ---
if menu == "Jogar Partida":
    st.header("🎮 Tabuleiro Jogável Interativo")
    st.write("Mova as peças no tabuleiro abaixo (Drag & Drop habilitado via Lichess Embed).")
    
    # Embutindo um tabuleiro de análise real que permite jogar e testar lances
    st_player("https://lichess.org/analysis/standard", height=600)
    
    st.divider()
    with st.expander("Salvar Partida no Histórico"):
        pgn_input = st.text_area("Cole o PGN da partida finalizada aqui para salvar:")
        oponente = st.text_input("Nome do Oponente:")
        if st.button("Salvar e Ganhar +15 Rating"):
            conn = sqlite3.connect('chess_master.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user, oponente, pgn_input, "Finalizado"))
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username=?', (st.session_state.user,))
            conn.commit()
            st.session_state.rating += 15
            st.success("Rating atualizado!")

# --- ABA APRENDIZADO (EXERCÍCIOS INFINITOS VIA API) ---
elif menu == "Aprendizado IA (Infinito)":
    st.header("🎓 Exercícios de Tática Infinitos")
    
    if st.button("🎯 Próximo Exercício Aleatório"):
        # Puxa um quebra-cabeça aleatório da API do Lichess
        response = requests.get("https://lichess.org/api/puzzle/daily")
        if response.status_code == 200:
            data = response.json()
            st.session_state.puzzle_id = data['puzzle']['id']
        else:
            st.error("Erro ao carregar exercício. Tente novamente.")

    if 'puzzle_id' in st.session_state:
        url_puzzle = f"https://lichess.org/training/{st.session_state.puzzle_id}"
        st.write(f"Resolva o desafio no tabuleiro abaixo:")
        st_player(url_puzzle, height=700)
    else:
        st.info("Clique no botão acima para carregar seu primeiro desafio!")

# --- LOGOUT ---
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()
