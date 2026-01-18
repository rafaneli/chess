import streamlit as st
import chess
import chess.engine
import chess.pgn
import os
import shutil
from io import StringIO

# --- 1. DEFINIÇÃO DO CAMINHO (RESOLVE O NAMEERROR) ---
def localizar_stockfish():
    # Busca no PATH do sistema (onde o packages.txt instala no Streamlit Cloud)
    path = shutil.which("stockfish")
    if path:
        return path
    
    # Caminhos comuns no Linux/Streamlit
    caminhos_linux = ["/usr/games/stockfish", "/usr/bin/stockfish"]
    for p in caminhos_linux:
        if os.path.exists(p):
            return p
            
    # Fallback para Windows local (se o arquivo estiver na raiz)
    if os.path.exists("stockfish.exe"):
        return "stockfish.exe"
        
    return None

# Definimos a variável global ANTES de qualquer classe ou uso
STOCKFISH_PATH = localizar_stockfish()

# --- 2. LÓGICA DE CLASSIFICAÇÃO ---
def classificar_lance(perda):
    # Baseado na lógica visual do Chess.com
    if perda <= 5: return "Melhor ⭐", "#96bc4b"
    if perda < 25: return "Excelente !", "#96bc4b"
    if perda < 60: return "Bom ✓", "#96bc4b"
    if perda < 150: return "Imprecisão ?!", "#f0c15c"
    if perda < 300: return "Erro ?", "#e58f2a"
    return "Capivarada ??", "#ca3431"

# --- 3. INTERFACE E ANÁLISE ---
st.set_page_config(page_title="Analisador de PGN Profissional", layout="wide")

st.title("♟️ Revisão de Partida Estilo Chess.com")

uploaded_file = st.file_uploader("Envie seu arquivo PGN", type="pgn")

if uploaded_file is not None:
    pgn_text = uploaded_file.getvalue().decode("utf-8")
    partida = chess.pgn.read_game(StringIO(pgn_text))
    
    if partida and STOCKFISH_PATH:
        resumo = {
            "Melhor ⭐": 0, "Excelente !": 0, "Bom ✓": 0,
            "Imprecisão ?!": 0, "Erro ?": 0, "Capivarada ??": 0
        }
        
        lances_detalhados = []
        board = partida.board()
        
        with st.status("Analisando lances com Stockfish...") as status:
            with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
                for move in partida.mainline_moves():
                    # Avaliação antes do lance
                    info_antes = engine.analyse(board, chess.engine.Limit(time=0.1))
                    score_antes = info_antes["score"].relative.score(mate_score=10000)

                    board.push(move)

                    # Avaliação depois do lance
                    info_depois = engine.analyse(board, chess.engine.Limit(time=0.1))
                    score_depois = info_depois["score"].relative.score(mate_score=10000)

                    # Perda de centipawns (ajustando para a vez do jogador)
                    perda = (score_antes * -1) - score_depois
                    label, cor = classificar_lance(perda)
                    
                    resumo[label] += 1
                    lances_detalhados.append({"san": move.uci(), "label": label, "color": cor})
            status.update(label="Análise finalizada!", state="complete")

        # --- EXIBIÇÃO DO RESUMO (CATEGORIAS) ---
        st.write("### Revisão da Partida")
        cols = st.columns(len(resumo))
        for i, (label, count) in enumerate(resumo.items()):
            # Busca a cor da categoria para o fundo do card
            _, bg_color = classificar_lance(0 if "Melhor" in label else (200 if "Erro" in label else 400))
            if "Imprecisão" in label: bg_color = "#f0c15c"
            
            cols[i].markdown(
                f"""<div style="background-color:{bg_color}; padding:15px; border-radius:10px; text-align:center; color:white;">
                    <h2 style="margin:0;">{count}</h2>
                    <small>{label}</small>
                </div>""", 
                unsafe_allow_html=True
            )

        # --- LISTA DE LANCES ---
        with st.expander("Ver análise detalhada lance a lance"):
            for i, item in enumerate(lances_detalhados):
                st.markdown(f"**{i+1}. {item['san']}** — <span style='color:{item['color']}'>{item['label']}</span>", unsafe_allow_html=True)
    
    elif not STOCKFISH_PATH:
        st.error("Motor Stockfish não configurado corretamente no servidor.")
