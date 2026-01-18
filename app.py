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

# --- 1. CONFIGURAÇÃO VISUAL ---
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

# --- 2. BANCO DE DADOS (CORRIGIDO) ---
def init_db():
    conn = sqlite3.connect('chess_data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    # Adicionada a coluna 'date' para evitar o erro de consulta
    c.execute('''CREATE TABLE IF NOT EXISTS games 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, 
                  pgn TEXT, result TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. MOTOR E LÓGICA DE ANÁLISE ---
def get_stockfish():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return path if os.path.exists(path) else None

STOCKFISH_PATH = get_stockfish()

def get_move_category(loss):
    if loss <= 5: return "Melhor", "#96bc4b", "⭐"
    if loss < 25: return "Excelente", "#60a33e", "!"
    if loss < 60: return "Bom", "#9cbf34", "✓"
    if loss < 150: return "Imprecisão", "#f0c15c", "?!"
    if loss < 300: return "Erro", "#e58f2a", "?"
    return "Capivarada", "#ca3431", "??"

# --- 4. SISTEMA DE LOGIN ---
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
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
            else: st.error("Usuário ou senha incorretos")
    with t2:
        nu = st.text_input("Novo Usuário")
        np = st.text_input("Nova Senha", type="password")
        if st.button("Registrar"):
            try:
                conn = sqlite3.connect('chess_data.db')
                conn.execute('INSERT INTO users VALUES (?,?,800)', (nu, hash_p(np)))
                conn.commit()
                conn.close()
                st.success("Conta criada com 800 de Rating!")
            except: st.error("Usuário já existe")
    st.stop()

# --- 5. INTERFACE PRINCIPAL ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.radio("Navegação", ["Jogar Partida", "Histórico de Jogos", "Analisador Profissional"])

def render_board(board):
    board_svg = chess.svg.board(board=board, size=400).encode("utf-8")
    b64 = base64.b64encode(board_svg).decode("utf-8")
    return f'<div style="display: flex; justify-content: center;"><img src="data:image/svg+xml;base64,{b64}" style="width:100%; max-width:450px; border: 5px solid #312e2b; border-radius: 5px;"/></div>'

if menu == "Jogar Partida":
    st.header("🎮 Nova Partida Local")
    if 'board' not in st.session_state: st.session_state.board = chess.Board()
    
    col_b, col_i = st.columns([2, 1])
    with col_b:
        st.markdown(render_board(st.session_state.board), unsafe_allow_html=True)
    
    with col_i:
        move = st.text_input("Digite seu lance (ex: e4, Nf3, O-O)")
        if st.button("Executar Lance"):
            try:
                m = st.session_state.board.parse_san(move)
                st.session_state.board.push(m)
                st.rerun()
            except: st.error("Lance inválido ou ilegal")
        
        st.divider()
        op = st.text_input("Nome do Oponente")
        if st.button("Finalizar e Salvar Jogo"):
            game_pgn = str(chess.pgn.Game.from_board(st.session_state.board))
            conn = sqlite3.connect('chess_data.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user, op, game_pgn, "1-0"))
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username = ?', (st.session_state.user,))
            conn.commit()
            conn.close()
            st.session_state.rating += 15
            del st.session_state.board
            st.success("Jogo salvo! Você ganhou +15 de Rating.")

elif menu == "Histórico de Jogos":
    st.header("📚 Suas Partidas")
    conn = sqlite3.connect('chess_data.db')
    # Consulta corrigida incluindo a coluna 'date'
    df = pd.read_sql(f"SELECT id, white, black, result, date FROM games WHERE white='{st.session_state.user}' OR black='{st.session_state.user}'", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        game_id = st.number_input("Digite o ID do jogo para analisar", min_value=int(df['id'].min()), max_value=int(df['id'].max()))
        if st.button("🔍 Carregar no Analisador"):
            conn = sqlite3.connect('chess_data.db')
            st.session_state.to_analyze = conn.execute(f"SELECT pgn FROM games WHERE id={game_id}").fetchone()[0]
            conn.close()
            st.success("Partida carregada! Clique em 'Analisador Profissional' no menu lateral.")
    else:
        st.info("Você ainda não salvou nenhuma partida.")

elif menu == "Analisador Profissional":
    st.header("⭐ Revisão da Partida")
    pgn_data = st.session_state.get('to_analyze', None)
    
    if pgn_data and STOCKFISH_PATH:
        game = chess.pgn.read_game(StringIO(pgn_data))
        board = game.board()
        counts = {"Melhor": 0, "Excelente": 0, "Bom": 0, "Imprecisão": 0, "Erro": 0, "Capivarada": 0}
        
        with st.status("Stockfish analisando lances...") as status:
            with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
                for move in game.mainline_moves():
                    info_pre = engine.analyse(board, chess.engine.Limit(time=0.1))
                    score_pre = info_pre["score"].relative.score(mate_score=10000)
                    board.push(move)
                    info_post = engine.analyse(board, chess.engine.Limit(time=0.1))
                    score_post = info_post["score"].relative.score(mate_score=10000)
                    
                    loss = (score_pre * -1) - score_post
                    cat, color, icon = get_move_category(loss)
                    counts[cat] += 1
            status.update(label="Análise concluída!", state="complete")

        # Exibição dos Cards Coloridos
        cols = st.columns(len(counts))
        for i, (cat, count) in enumerate(counts.items()):
            _, color, icon = get_move_category(0 if cat == "Melhor" else (100 if cat == "Imprecisão" else 400))
            cols[i].markdown(f"""
                <div style="background-color:{color}; padding:10px; border-radius:5px; text-align:center;">
                    <h3 style="margin:0;">{count}</h3>
                    <small>{cat}</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Selecione um jogo no seu Histórico primeiro.")

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()
