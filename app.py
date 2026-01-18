import streamlit as st
import chess
import chess.engine
import chess.pgn
import pandas as pd
import sqlite3
import hashlib
import shutil
import os
from io import StringIO
from st_chess_board import st_chess_board # Novo componente estável

# --- CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Chess Master Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #81b64c; color: white; font-weight: bold; }
    .challenge-card { background-color: #312e2b; padding: 20px; border-radius: 10px; border-left: 5px solid #81b64c; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('chess_pro.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, rating INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, white TEXT, black TEXT, pgn TEXT, result TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

init_db()

# --- MOTOR ---
def get_engine():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    if os.path.exists(path):
        return chess.engine.SimpleEngine.popen_uci(path)
    return None

# --- SISTEMA DE LOGIN ---
if 'user' not in st.session_state:
    st.title("♟️ Chess Master Platform")
    t1, t2 = st.tabs(["Entrar", "Cadastrar"])
    with t1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Acessar"):
            conn = sqlite3.connect('chess_pro.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
    st.stop()

# --- MENU ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Navegação", ["Jogar Partida", "Aprendizado", "Histórico", "Análise"])

# --- ABA DE APRENDIZADO (NOVA) ---
if menu == "Aprendizado":
    st.header("🎓 Centro de Treinamento")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        categoria = st.radio("Escolha o Tema:", ["Aberturas", "Táticas (Mates)", "Fins de Jogo", "Aproveite o Erro"])
        dificuldade = st.select_slider("Dificuldade", options=["Iniciante", "Intermediário", "Mestre"])

    # Base de dados de desafios (Exemplos de FENs famosas para cada categoria)
    desafios = {
        "Aberturas": {"fen": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3", "msg": "Ruy Lopez: Qual o lance mais sólido para as brancas?"},
        "Táticas (Mates)": {"fen": "6k1/5ppp/8/8/8/8/5PPP/6K1 w - - 0 1", "msg": "Mate de Corredor: Encontre a sequência."},
        "Fins de Jogo": {"fen": "8/8/8/8/8/4k3/8/4K2R w K - 0 1", "msg": "Mate de Torre e Rei: Encurrale o rei preto."},
        "Aproveite o Erro": {"fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3", "msg": "As brancas jogaram Bispo C4. Como as pretas podem punir se houver erro?"}
    }

    with col2:
        st.subheader(f"Desafio: {categoria}")
        st.info(desafios[categoria]["msg"])
        
        # Tabuleiro Jogável no Aprendizado
        st_chess_board(fen=desafios[categoria]["fen"], key="edu_board")
        
        if st.button("Ver Dica do Stockfish"):
            engine = get_engine()
            if engine:
                board = chess.Board(desafios[categoria]["fen"])
                analysis = engine.analyse(board, chess.engine.Limit(time=0.5))
                best_move = board.san(analysis["pv"][0])
                st.success(f"O Stockfish sugere: **{best_move}**")
                engine.quit()

# --- ABA DE JOGO (TABULEIRO INTERATIVO) ---
elif menu == "Jogar Partida":
    st.header("🎮 Partida Real")
    
    if 'game_board' not in st.session_state:
        st.session_state.game_board = chess.Board()

    col_board, col_info = st.columns([2, 1])

    with col_board:
        # Tabuleiro totalmente jogável (Drag & Drop)
        move_made = st_chess_board(fen=st.session_state.game_board.fen(), key="play_board")
        
        # Se o jogador arrastar uma peça, atualizamos o estado interno
        if move_made and move_made != st.session_state.game_board.fen():
            st.session_state.game_board = chess.Board(move_made)
            st.rerun()

    with col_info:
        st.write("### Status da Partida")
        st.write(f"Vez das: **{'Brancas' if st.session_state.game_board.turn else 'Pretas'}**")
        
        if st.button("Reiniciar Tabuleiro"):
            st.session_state.game_board = chess.Board()
            st.rerun()

        st.divider()
        oponente = st.text_input("Oponente", value="Computador")
        if st.button("Finalizar e Registrar"):
            pgn = str(chess.pgn.Game.from_board(st.session_state.game_board))
            conn = sqlite3.connect('chess_pro.db')
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (st.session_state.user, oponente, pgn, "Concluído"))
            conn.execute('UPDATE users SET rating = rating + 10 WHERE username=?', (st.session_state.user,))
            conn.commit()
            st.session_state.rating += 10
            st.success("Partida salva! +10 de Rating.")

# --- HISTÓRICO E ANÁLISE ---
elif menu == "Histórico":
    st.header("🕒 Suas Partidas")
    conn = sqlite3.connect('chess_pro.db')
    df = pd.read_sql(f"SELECT id, white, black, result, date FROM games WHERE white='{st.session_state.user}'", conn)
    st.dataframe(df, use_container_width=True)
