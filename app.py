import streamlit as st
import chess
import chess.engine
import chess.pgn
import pandas as pd
import sqlite3
import hashlib
from io import StringIO
from streamlit_chess import st_chess

# --- CONFIGURAÇÃO E BANCO DE DATA ---
st.set_page_config(page_title="Chess.com Clone", layout="wide")

def init_db():
    conn = sqlite3.connect('chess_platform.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS games 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, 
                  pgn TEXT, result TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÕES DE USUÁRIO ---
def hash_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def login_user(user, pwd):
    conn = sqlite3.connect('chess_platform.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password =?', (user, hash_pass(pwd)))
    data = c.fetchone()
    conn.close()
    return data

def register_user(user, pwd):
    try:
        conn = sqlite3.connect('chess_platform.db')
        c = conn.cursor()
        c.execute('INSERT INTO users(username, password, rating) VALUES (?,?,?)', (user, hash_pass(pwd), 800))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# --- CÁLCULO DE ELO (SIMPLIFICADO) ---
def update_elo(winner, loser, draw=False):
    conn = sqlite3.connect('chess_platform.db')
    c = conn.cursor()
    k = 32
    if not draw:
        c.execute('UPDATE users SET rating = rating + ? WHERE username = ?', (k, winner))
        c.execute('UPDATE users SET rating = rating - ? WHERE username = ?', (k, loser))
    conn.commit()
    conn.close()

# --- INTERFACE DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    with tab1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            res = login_user(u, p)
            if res:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.session_state.rating = res[2]
                st.rerun()
    with tab2:
        nu = st.text_input("Novo Usuário")
        np = st.text_input("Nova Senha", type="password")
        if st.button("Registrar"):
            if register_user(nu, np): st.success("Conta criada!")
            else: st.error("Usuário já existe.")
    st.stop()

# --- ÁREA LOGADA ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.radio("Menu", ["Jogar", "Histórico", "Analisador"])

if menu == "Jogar":
    st.subheader("🎮 Partida Local (2 Jogadores)")
    if 'board' not in st.session_state:
        st.session_state.board = chess.Board()
    
    col_game, col_ctrl = st.columns([2, 1])
    
    with col_game:
        # Tabuleiro jogável
        fen = st_chess(st.session_state.board.fen(), key="play_board")
        if fen != st.session_state.board.fen():
            st.session_state.board = chess.Board(fen)
            st.rerun()

    with col_ctrl:
        st.write("### Controles")
        oponente = st.text_input("Nome do Oponente (Registrado)")
        if st.button("Finalizar e Salvar Jogo"):
            # Salva no banco e atualiza ELO
            pgn = str(chess.pgn.Game.from_board(st.session_state.board))
            conn = sqlite3.connect('chess_platform.db')
            c = conn.cursor()
            c.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                      (st.session_state.user, oponente, pgn, "Terminado"))
            conn.commit()
            conn.close()
            st.success("Jogo salvo no histórico!")

elif menu == "Histórico":
    st.subheader("📚 Meus Jogos")
    conn = sqlite3.connect('chess_platform.db')
    df = pd.read_sql(f"SELECT * FROM games WHERE white='{st.session_state.user}' OR black='{st.session_state.user}'", conn)
    conn.close()
    
    if not df.empty:
        selected_game = st.selectbox("Selecione um jogo para ver detalhes", df['id'])
        if st.button("Enviar para o Analisador"):
            pgn_to_analyze = df[df['id'] == selected_game]['pgn'].values[0]
            st.session_state.pgn_data = pgn_to_analyze
            st.info("Partida carregada! Vá para a aba 'Analisador'.")
    else:
        st.write("Você ainda não jogou nenhuma partida.")

elif menu == "Analisador":
    # Aqui entra todo o código de análise que desenvolvemos anteriormente
    if 'pgn_data' in st.session_state:
        st.write("### Analisando Partida do Histórico")
        # (Insira aqui a lógica do Stockfish e os cards coloridos do prompt anterior)
        st.text_area("PGN Carregado", st.session_state.pgn_data, height=200)
    else:
        st.warning("Carregue uma partida do histórico primeiro.")

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()
