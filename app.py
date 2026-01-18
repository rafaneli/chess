import streamlit as st
import chess
import chess.engine
import os
import shutil

# --- CONFIGURAÇÕES DO MOTOR ---
# Certifique-se de que o binário do Stockfish esteja na mesma pasta ou forneça o caminho
STOCKFISH_PATH = shutil.which("stockfish")  # Verifica se está no PATH (cloud)
if not STOCKFISH_PATH:
    # Fallback para caminhos locais
    STOCKFISH_PATHS = [
        os.path.join("stockfish", "stockfish"),  # Para local
        os.path.join("stockfish", "stockfish.exe"),  # Para Windows local
    ]
    for path in STOCKFISH_PATHS:
        if os.path.exists(path):
            STOCKFISH_PATH = path
            break

class ChessTutor:
    def __init__(self):
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception:
            st.error("Erro: Executável do Stockfish não encontrado.")
            self.engine = None

    def get_analysis(self, board):
        if not self.engine: return None
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

if 'board' not in st.session_state:
    st.session_state.board = chess.Board()
if 'history' not in st.session_state:
    st.session_state.history = []

tutor = ChessTutor()

st.title("♟️ Professor de Xadrez Robotizado")
st.markdown("Analise seus lances com a precisão do **Stockfish**.")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Tabuleiro Atual")
    st.code(str(st.session_state.board))
    
    move_input = st.text_input("Digite seu lance (ex: e2e4)", key="move_input")
    if st.button("Fazer Lance"):
        if move_input:
            try:
                move = chess.Move.from_uci(move_input)
                if move in st.session_state.board.legal_moves:
                    st.session_state.board.push(move)
                    st.rerun()
                else:
                    st.error("Lance ilegal!")
            except:
                st.error("Lance inválido!")
    
    # Se o jogador fizer um lance no tabuleiro (neste caso, via botão)
    # Lógica de análise aqui, mas por enquanto, apenas atualizar

with col2:
    st.subheader("📊 Revisão da Partida")
    
    # Simulação de Precisão (Exemplo didático)
    score = tutor.get_analysis(st.session_state.board)
    
    if score is not None:
        precision = max(0, min(100, 100 - (abs(score) / 20))) # Fórmula simplificada
        st.metric("Precisão Geral", f"{precision:.1f}%")
        
        # Classificação do lance atual
        label, color = tutor.classify_move(score)
        st.markdown(f"### Avaliação: <span style='color:{color}'>{label}</span>", unsafe_allow_html=True)
        
        st.divider()
        st.write("**Dica do Professor:**")
        if abs(score) > 100:
            st.info("Você está perdendo material ou posição. Tente controlar o centro!")
        else:
            st.success("Sua posição é sólida. Continue pressionando!")

# Rodapé técnico
st.sidebar.header("Configurações")
if st.sidebar.button("Reiniciar Partida"):
    st.session
