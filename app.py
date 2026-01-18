import streamlit as st
import sqlite3
import hashlib
import requests
import pandas as pd
import streamlit.components.v1 as components

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
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, result TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

init_db()

# --- 3. SISTEMA DE LOGIN / CADASTRO ---
if 'user' not in st.session_state:
    st.title("♟️ Bem-vindo ao Chess Master")
    t1, t2 = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
    with t1:
        u = st.text_input("Usuário", key="login_u")
        p = st.text_input("Senha", type="password", key="login_p")
        if st.button("Acessar"):
            conn = sqlite3.connect('chess_master.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
            else: st.error("Incorreto")
    with t2:
        nu = st.text_input("Novo Usuário", key="reg_u")
        np = st.text_input("Nova Senha", type="password", key="reg_p")
        if st.button("Cadastrar"):
            try:
                conn = sqlite3.connect('chess_master.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hashlib.sha256(np.encode()).hexdigest()))
                conn.commit()
                st.success("Cadastrado! Faça o login.")
            except: st.error("Usuário já existe")
    st.stop()

# --- 4. INTERFACE ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Menu", ["Jogar Partida", "Aprendizado IA (Infinito)", "Leaderboard"])

# --- ABA JOGAR (TABULEIRO INTERATIVO REAL) ---
if menu == "Jogar Partida":
    st.header("🎮 Tabuleiro Jogável Profissional")
    st.info("Utilize o tabuleiro abaixo para jogar. Ele inclui Barra de Avaliação e Stockfish integrados.")
    
    # Iframe nativo do Lichess - 100% jogável e evita virar player de vídeo
    components.html(
        '<iframe src="https://lichess.org/analysis/standard?theme=green&bg=dark" width="100%" height="600" frameborder="0"></iframe>',
        height=600
    )
    
    if st.button("🏆 Finalizei e Ganhei ( +15 Rating )"):
        conn = sqlite3.connect('chess_master.db')
        conn.execute('UPDATE users SET rating = rating + 15 WHERE username=?', (st.session_state.user,))
        conn.commit()
        st.session_state.rating += 15
        st.success("Pontuação atualizada no banco de dados!")

# --- ABA APRENDIZADO (EXERCÍCIOS INFINITOS) ---
elif menu == "Aprendizado IA (Infinito)":
    st.header("🎓 Exercícios de Tática Infinitos")
    
    if st.button("🎯 Próximo Exercício Aleatório"):
        # API do Lichess para pegar um puzzle novo
        res = requests.get("https://lichess.org/api/puzzle/daily")
        if res.status_code == 200:
            st.session_state.puzzle_id = res.json()['puzzle']['id']

    if 'puzzle_id' in st.session_state:
        puzzle_url = f"https://lichess.org/training/embed/{st.session_state.puzzle_id}?theme=brown&bg=dark"
        components.html(
            f'<iframe src="{puzzle_url}" width="100%" height="700" frameborder="0"></iframe>',
            height=700
        )
    else:
        st.info("Clique no botão para carregar o primeiro desafio.")

# --- ABA LEADERBOARD ---
elif menu == "Leaderboard":
    st.header("🏆 Top Jogadores")
    conn = sqlite3.connect('chess_master.db')
    df = pd.read_sql("SELECT username, rating FROM users ORDER BY rating DESC", conn)
    st.table(df)

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
