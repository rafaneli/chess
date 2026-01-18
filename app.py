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

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Chess Pro: Play & Learn", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stButton>button { background-color: #81b64c; color: white; border-radius: 5px; font-weight: bold; width: 100%; }
    .stMetric { background-color: #312e2b; padding: 10px; border-radius: 4px; border: 1px solid #403d39; }
    .player-box { background-color: #312e2b; padding: 15px; border-radius: 8px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
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

# --- 3. MOTOR STOCKFISH ---
def get_engine():
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    if os.path.exists(path):
        return chess.engine.SimpleEngine.popen_uci(path)
    return None

# --- 4. SISTEMA DE ACESSO (LOGIN E CADASTRO) ---
if 'user' not in st.session_state:
    st.title("♟️ Bem-vindo ao Chess Pro")
    
    # Abas para garantir que o cadastro esteja sempre visível
    tab_login, tab_cadastro = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
    
    with tab_login:
        u = st.text_input("Usuário", key="login_user")
        p = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Acessar Plataforma"):
            conn = sqlite3.connect('chess_master.db')
            res = conn.execute('SELECT * FROM users WHERE username=? AND password=?', 
                               (u, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            conn.close()
            if res:
                st.session_state.user, st.session_state.rating = res[0], res[2]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    with tab_cadastro:
        nu = st.text_input("Escolha um Usuário", key="reg_user")
        np = st.text_input("Escolha uma Senha", type="password", key="reg_pass")
        if st.button("Finalizar Cadastro"):
            if nu and np:
                try:
                    conn = sqlite3.connect('chess_master.db')
                    conn.execute('INSERT INTO users VALUES (?,?,800)', 
                                 (nu, hashlib.sha256(np.encode()).hexdigest()))
                    conn.commit()
                    conn.close()
                    st.success("Conta criada! Agora faça o login na aba 'Entrar'.")
                except:
                    st.error("Este nome de usuário já está em uso.")
            else:
                st.warning("Preencha todos os campos.")
    st.stop()

# --- 5. INTERFACE DO USUÁRIO LOGADO ---
st.sidebar.title(f"👤 {st.session_state.user} ({st.session_state.rating})")
menu = st.sidebar.selectbox("Navegação", ["Jogar Partida", "Aprendizado", "Histórico & Análise"])

def render_board(board, flipped=False):
    # flipped=True inverte o tabuleiro para jogar de pretas
    board_svg = chess.svg.board(board=board, size=450, orientation=chess.BLACK if flipped else chess.WHITE).encode("utf-8")
    b64 = base64.b64encode(board_svg).decode("utf-8")
    return f'<div style="display:flex;justify-content:center;"><img src="data:image/svg+xml;base64,{b64}" style="width:100%;max-width:450px;border-radius:5px;"/></div>'

# --- ABA: JOGAR ---
if menu == "Jogar Partida":
    st.header("🎮 Partida Local Interativa")
    
    # Configurações de Cor e Oponente
    if 'game_board' not in st.session_state: 
        st.session_state.game_board = chess.Board()
    
    col_b, col_c = st.columns([2, 1])
    
    with col_c:
        st.write("### ⚙️ Configurações")
        cor_escolhida = st.radio("Jogar de:", ["Brancas", "Pretas"], horizontal=True)
        op_nome = st.text_input("Nome do Oponente", value="Computador")
        
        st.divider()
        st.write("### ♟️ Suas Jogadas")
        move = st.text_input("Digite o lance (ex: e4, Nf3, O-O)", key="play_move")
        if st.button("Executar Lance"):
            try:
                st.session_state.game_board.push_san(move)
                st.rerun()
            except:
                st.error("Lance inválido ou ilegal.")
        
        if st.button("Reiniciar Tabuleiro"):
            st.session_state.game_board = chess.Board()
            st.rerun()

        st.divider()
        if st.button("Salvar Partida e Ganhar Rating"):
            pgn = str(chess.pgn.Game.from_board(st.session_state.game_board))
            conn = sqlite3.connect('chess_master.db')
            
            # Define quem jogou de quê com base na escolha da cor
            branco = st.session_state.user if cor_escolhida == "Brancas" else op_nome
            preto = op_nome if cor_escolhida == "Brancas" else st.session_state.user
            
            conn.execute('INSERT INTO games (white, black, pgn, result) VALUES (?,?,?,?)', 
                         (branco, preto, pgn, "Finalizado"))
            conn.execute('UPDATE users SET rating = rating + 15 WHERE username=?', (st.session_state.user,))
            conn.commit()
            conn.close()
            st.session_state.rating += 15
            st.success("Vitória registrada! +15 de Rating.")

    with col_b:
        # Renderiza o tabuleiro invertido se o jogador escolher Pretas
        is_flipped = True if cor_escolhida == "Pretas" else False
        st.markdown(render_board(st.session_state.game_board, flipped=is_flipped), unsafe_allow_html=True)
        st.write(f"Vez das: **{'Brancas' if st.session_state.game_board.turn else 'Pretas'}**")

# --- ABA: APRENDIZADO ---
elif menu == "Aprendizado":
    st.header("🎓 Centro de Treinamento IA")
    desafios = {
        "Aberturas": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "Táticas (Mates)": "6k1/5ppp/8/8/8/8/5PPP/6K1 w - - 0 1",
        "Fins de Jogo": "8/8/8/8/8/4k3/8/4K2R w K - 0 1"
    }
    tema = st.radio("Escolha o Tema", list(desafios.keys()), horizontal=True)
    
    col_t, col_s = st.columns([2, 1])
    with col_t:
        board_edu = chess.Board(desafios[tema])
        st.markdown(render_board(board_edu), unsafe_allow_html=True)
    
    with col_s:
        st.info("Utilize o Stockfish para aprender a solução desta posição.")
        if st.button("Analisar com Stockfish"):
            engine = get_engine()
            if engine:
                with st.spinner("IA calculando..."):
                    res = engine.analyse(board_edu, chess.engine.Limit(time=1.0))
                    best = board_edu.san(res["pv"][0])
                    st.success(f"O melhor lance é: **{best}**")
                    engine.quit()
            else:
                st.error("Motor Stockfish indisponível.")

# --- LOGOUT ---
if st.sidebar.button("Sair da Conta"):
    st.session_state.clear()
    st.rerun()
