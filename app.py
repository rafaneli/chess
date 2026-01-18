import streamlit as st
import chess
import chess.engine
import os
import shutil

# --- CONFIGURAÇÕES DO MOTOR (REVISADO PARA CLOUD) ---
def buscar_estoque_peixe():
    # 1. Tenta localizar no PATH do sistema (onde o packages.txt instala)
    path = shutil.which("stockfish")
    if path:
        return path
    
    # 2. Caminhos padrão do Linux (Debian/Ubuntu no Streamlit)
    caminhos_linux = [
        "/usr/games/stockfish",
        "/usr/bin/stockfish",
        "/usr/local/bin/stockfish"
    ]
    for p in caminhos_linux:
        if os.path.exists(p):
            return p
            
    # 3. Fallback para Windows Local
    if os.path.exists("stockfish.exe"):
        return "stockfish.exe"
        
    return None

STOCKFISH_PATH = buscar_estoque_peixe()

class ChessTutor:
    def __init__(self):
        self.engine = None
        if not STOCKFISH_PATH:
            st.error("Erro crítico: O executável do Stockfish não foi encontrado no servidor.")
            return

        try:
            # No Linux, popen_uci precisa do caminho absoluto ou nome correto
            self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception as e:
            st.error(f"Erro ao iniciar o motor: {e}")

    def get_analysis(self, board):
        if not self.engine: 
            return None
        try:
            # Limitamos o tempo para não travar o servidor gratuito
            info = self.engine.analyse(board, chess.engine.Limit(time=0.1))
            return info["score"].relative.score(mate_score=10000)
        except:
            return None
        # Analisa a melhor jogada
        info = self.engine.analyse(board, chess.engine.Limit(time=0.1))
        return info["score"].relative.score(mate_score=10000)

    def classify_move(self, score_diff):
        # Lógica baseada nas categorias que discutimos
        diff = abs(score_diff)
        if diff == 0: return "Melhor ⭐", "#96bc4b"
        if diff < 20: return "Excelente !", "#96bc4b"
        if diff < 50: return "Bom ✓", "#96bc4b"
        if diff < 150: return "Imprecisão ?!", "#f0c15c"
        if diff < 300: return "Erro ?", "#e58f2a"
        return "Capivarada ??", "#ca3431"

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Professor de Xadrez IA", layout="wide")

# Inicializar estado da sessão
if 'board' not in st.session_state:
    st.session_state.board = chess.Board()
if 'history' not in st.session_state:
    st.session_state.history = []
if 'pgn_game' not in st.session_state:
    st.session_state.pgn_game = None
if 'current_move' not in st.session_state:
    st.session_state.current_move = 0

tutor = ChessTutor()

st.title("♟️ Professor de Xadrez IA")
st.markdown("Jogue e analise partidas com a precisão do **Stockfish**.")

# Abas para diferentes modos
tab1, tab2 = st.tabs(["Jogar", "Analisar PGN"])

with tab1:
    st.header("Modo de Jogo")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Tabuleiro")
        # Exibir tabuleiro visual
        board_svg = st.session_state.board._repr_svg_()
        st.markdown(board_svg, unsafe_allow_html=True)
        
        st.subheader("Fazer Lance")
        move_input = st.text_input("Digite seu lance (ex: e2e4)", key="move_input")
        if st.button("Fazer Lance"):
            if move_input:
                try:
                    move = chess.Move.from_uci(move_input)
                    if move in st.session_state.board.legal_moves:
                        st.session_state.board.push(move)
                        st.session_state.history.append(move)
                        st.rerun()
                    else:
                        st.error("Lance ilegal!")
                except:
                    st.error("Lance inválido!")
        
        # Opção para desfazer lance
        if st.button("Desfazer Lance") and st.session_state.history:
            st.session_state.board.pop()
            st.session_state.history.pop()
            st.rerun()

    with col2:
        st.subheader("Análise")
        score = tutor.get_analysis(st.session_state.board)
        if score is not None:
            precision = max(0, min(100, 100 - (abs(score) / 20)))
            st.metric("Avaliação do Stockfish", f"{score/100:.2f}")
            st.metric("Precisão Estimada", f"{precision:.1f}%")
            
            label, color = tutor.classify_move(score)
            st.markdown(f"**Classificação:** <span style='color:{color}'>{label}</span>", unsafe_allow_html=True)
        else:
            st.warning("Stockfish não disponível.")

        st.subheader("Lances Legais")
        legal_moves = list(st.session_state.board.legal_moves)
        if legal_moves:
            selected_move = st.selectbox("Escolha um lance legal:", [str(move) for move in legal_moves])
            if st.button("Fazer Lance Selecionado"):
                move = chess.Move.from_uci(selected_move)
                st.session_state.board.push(move)
                st.session_state.history.append(move)
                st.rerun()

with tab2:
    st.header("Análise de PGN")
    uploaded_file = st.file_uploader("Faça upload de um arquivo PGN", type="pgn")
    
    if uploaded_file is not None:
        pgn_content = StringIO(uploaded_file.getvalue().decode("utf-8"))
        game = chess.pgn.read_game(pgn_content)
        
        if game is not None:
            st.session_state.pgn_game = game
            st.session_state.current_move = 0
            st.session_state.board = game.board()
            
            st.subheader("Informações da Partida")
            st.write(f"**Brancas:** {game.headers.get('White', 'Desconhecido')}")
            st.write(f"**Pretas:** {game.headers.get('Black', 'Desconhecido')}")
            st.write(f"**Resultado:** {game.headers.get('Result', 'Desconhecido')}")
            
            # Navegação pela partida
            moves = list(game.mainline_moves())
            st.session_state.current_move = st.slider("Mover na partida", 0, len(moves), st.session_state.current_move)
            
            # Aplicar moves até o ponto atual
            board = game.board()
            for i, move in enumerate(moves[:st.session_state.current_move]):
                board.push(move)
            
            st.session_state.board = board
            
            # Exibir tabuleiro
            board_svg = board._repr_svg_()
            st.markdown(board_svg, unsafe_allow_html=True)
            
            # Análise da posição atual
            score = tutor.get_analysis(board)
            if score is not None:
                st.metric("Avaliação", f"{score/100:.2f}")
                label, color = tutor.classify_move(score)
                st.markdown(f"**Posição:** <span style='color:{color}'>{label}</span>", unsafe_allow_html=True)
            
            # Mostrar próximos lances
            if st.session_state.current_move < len(moves):
                next_move = moves[st.session_state.current_move]
                st.write(f"Próximo lance: {next_move}")
        else:
            st.error("Erro ao ler o arquivo PGN.")

# Rodapé
st.sidebar.header("Configurações")
if st.sidebar.button("Reiniciar Partida"):
    st.session_state.board = chess.Board()
    st.session_state.history = []
    st.session_state.pgn_game = None
    st.session_state.current_move = 0
    st.rerun()
