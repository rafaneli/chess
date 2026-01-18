import streamlit as st
import chess
import chess.engine
import chess.pgn
import os
import shutil
from io import StringIO
import pandas as pd
import altair as alt

# --- 1. CONFIGURAÇÃO E LOCALIZAÇÃO DO MOTOR STOCKFISH ---
# Esta função é robusta para encontrar o Stockfish no Streamlit Cloud (Linux)
# e também funciona em ambientes locais (Windows/Linux).
def localizar_stockfish():
    # Tenta encontrar no PATH do sistema (método preferencial após apt-get)
    path = shutil.which("stockfish")
    if path:
        return path
    
    # Caminhos comuns para instalação em sistemas Linux (Debian/Ubuntu)
    caminhos_linux = [
        "/usr/games/stockfish",
        "/usr/bin/stockfish",
        "/usr/local/bin/stockfish"
    ]
    for p in caminhos_linux:
        if os.path.exists(p) and os.access(p, os.X_OK): # Verifica existência e permissão de execução
            return p
            
    # Fallback para Windows local (se o arquivo .exe estiver na mesma pasta)
    # ATENÇÃO: Se estiver usando Streamlit Cloud, este caminho será ignorado.
    if os.path.exists("stockfish.exe") and os.access("stockfish.exe", os.X_OK):
        return "stockfish.exe"
        
    return None

# A variável global STOCKFISH_PATH é definida UMA VEZ ao iniciar o app.
STOCKFISH_PATH = localizar_stockfish()

# --- 2. FUNÇÕES DE ANÁLISE E CLASSIFICAÇÃO ---

# Classifica um lance com base na perda de centipawns (CP)
def classificar_lance(perda_cp):
    # As thresholds e cores são baseadas no estilo do Chess.com
    if perda_cp <= 5: return "Melhor ⭐", "#96bc4b" # Verde escuro
    if perda_cp < 25: return "Excelente !", "#60a33e" # Verde
    if perda_cp < 60: return "Bom ✓", "#9cbf34"    # Verde claro
    if perda_cp < 150: return "Imprecisão ?!", "#f0c15c" # Amarelo
    if perda_cp < 300: return "Erro ?", "#e58f2a"     # Laranja
    return "Capivarada ??", "#ca3431" # Vermelho

# Estima o Rating (ELO) baseado na precisão média da partida
def estimar_rating(precisao_media):
    # Esta é uma função heurística, não um cálculo exato de ELO.
    # Correlação entre precisão e rating, ajustada para dar um feedback útil.
    if precisao_media >= 95: return int(2200 + (precisao_media - 95) * 50)
    if precisao_media >= 90: return int(1900 + (precisao_media - 90) * 60)
    if precisao_media >= 80: return int(1400 + (precisao_media - 80) * 50)
    if precisao_media >= 70: return int(1000 + (precisao_media - 70) * 40)
    if precisao_media >= 50: return int(600 + (precisao_media - 50) * 20)
    return int(400 + precisao_media * 2)

# --- 3. INTERFACE STREAMLIT PRINCIPAL ---
st.set_page_config(page_title="Professor de Xadrez IA", layout="wide", icon="♟️")

st.title("♟️ Professor de Xadrez IA: Análise de Partidas PGN")
st.markdown("Carregue seu arquivo PGN e receba uma análise detalhada dos seus lances, como um verdadeiro mestre!")

# Informação sobre o Stockfish na barra lateral para debug
st.sidebar.header("Status do Motor")
if STOCKFISH_PATH:
    st.sidebar.success(f"Stockfish encontrado: {STOCKFISH_PATH}")
else:
    st.sidebar.error("Stockfish não encontrado! Verifique `packages.txt` ou o caminho.")

uploaded_file = st.file_uploader("Selecione seu arquivo .PGN", type="pgn")

if uploaded_file is not None:
    pgn_text = uploaded_file.getvalue().decode("utf-8")
    partida = chess.pgn.read_game(StringIO(pgn_text))
    
    if partida is None:
        st.error("Erro: Não foi possível ler a partida PGN. Verifique o formato do arquivo.")
    elif not STOCKFISH_PATH:
        st.error("Não é possível analisar: O motor Stockfish não foi encontrado no servidor.")
    else:
        # Inicializa contadores e listas para análise
        resumo_categorias = {
            "Melhor ⭐": 0, "Excelente !": 0, "Bom ✓": 0,
            "Imprecisão ?!": 0, "Erro ?", "Capivarada ??": 0
        }
        lances_detalhados = []
        avaliacoes_grafico = [] # Para o gráfico de vantagem

        board = partida.board()
        
        # --- Barra de Status para a Análise ---
        with st.status("O Professor está analisando os lances com Stockfish...", expanded=True) as status:
            st.write("Iniciando motor de xadrez...")
            try:
                with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
                    st.write("Analisando cada lance da partida...")
                    for i, move in enumerate(partida.mainline_moves()):
                        # Avalia a posição ANTES do lance ser feito
                        info_antes = engine.analyse(board, chess.engine.Limit(time=0.1))
                        score_antes = info_antes["score"].relative.score(mate_score=10000)
                        
                        board.push(move) # Faz o lance
                        
                        # Avalia a posição DEPOIS do lance ser feito
                        info_depois = engine.analyse(board, chess.engine.Limit(time=0.1))
                        score_depois = info_depois["score"].relative.score(mate_score=10000)

                        # Calcula a perda de centipawns (CP)
                        # A pontuação do Stockfish é relativa ao jogador que está jogando.
                        # Para comparar, precisamos "normalizar" para a perspectiva do jogador que acabou de jogar.
                        # Se o jogador jogou e perdeu 50 CP, a pontuação do Stockfish (do ponto de vista do próximo jogador) vai subir 50.
                        # Então, (score_antes * -1) inverte a pontuação para a perspectiva do jogador atual.
                        # Depois, subtraímos score_depois (que é a avaliação para o próximo jogador, mas precisamos ver o impacto do lance do jogador atual)
                        # A perda é o quanto a avaliação caiu para o jogador que fez o lance.
                        perda_cp = (score_antes * -1) - score_depois
                        label, cor = classificar_lance(perda_cp)
                        
                        resumo_categorias[label] += 1
                        lances_detalhados.append({
                            "move_num": i + 1,
                            "san": board.san(move), # Notação padrão de xadrez (ex: Nf3)
                            "uci": move.uci(),
                            "label": label,
                            "color": cor,
                            "perda_cp": perda_cp
                        })
                        avaliacoes_grafico.append({"Lance": i + 1, "Vantagem": score_depois / 100}) # Converte para Paws
                        st.write(f"Analisado lance {i+1}: {board.san(move)}")

                    engine.quit() # Garante que o motor seja desligado
                status.update(label="Análise da partida concluída!", state="complete", expanded=False)

            except Exception as e:
                status.update(label="Erro durante a análise!", state="error")
                st.error(f"Não foi possível analisar a partida. Erro: {e}")
                st.info("Isso pode acontecer se o Stockfish demorar muito ou se o arquivo PGN estiver muito grande/complexo para o servidor gratuito.")
                st.stop() # Para a execução do script para não gerar mais erros


        # --- 4. EXIBIÇÃO DOS RESULTADOS ---
        st.header("Resultados da Análise")
        
        # --- Cálculo de Métricas Finais (Precisão e Rating) ---
        total_lances = len(lances_detalhados)
        # Definindo uma pontuação para cada tipo de lance para calcular a precisão
        pontos_precisao = sum([
            100 if "Melhor" in i["label"] or "Excelente" in i["label"] else
            80 if "Bom" in i["label"] else
            40 if "Imprecisão" in i["label"] else
            10 if "Erro" in i["label"] else 0
            for i in lances_detalhados
        ])
        
        # A precisão é uma porcentagem, normalizada pela pontuação máxima possível
        precisao_final = (pontos_precisao / (total_lances * 100)) * 100 if total_lances > 0 else 0
        rating_partida = estimar_rating(precisao_final)

        st.subheader("Performance Geral")
        col_precisao, col_rating = st.columns(2)
        
        with col_precisao:
            st.metric("Precisão da Partida", f"{precisao_final:.1f}%")
        
        with col_rating:
            # Exemplo de delta para mostrar uma comparação simples
            st.metric("Rating Estimado (Performance)", f"{rating_partida}", delta="Estimativa de ELO")

        st.divider()

        # --- Gráfico de Vantagem ao longo da partida ---
        st.subheader("Gráfico de Vantagem")
        if avaliacoes_grafico:
            df_avaliacoes = pd.DataFrame(avaliacoes_grafico)
            
            chart = alt.Chart(df_avaliacoes).mark_area(
                line={'color':'darkgreen'}, 
                color=alt.Gradient(
                    gradient='linear',
                    stops=[
                        alt.GradientStop(color='rgba(0,128,0,0.8)', offset=0), # Verde
                        alt.GradientStop(color='rgba(0,0,0,0)', offset=0.5),   # Transparente no centro
                        alt.GradientStop(color='rgba(128,0,0,0.8)', offset=1)  # Vermelho
                    ],
                    x1=1, y1=1, x2=1, y2=0 # Direção do gradiente
                )
            ).encode(
                x=alt.X('Lance:Q', axis=alt.Axis(title='Número do Lance')),
                y=alt.Y('Vantagem:Q', axis=alt.Axis(title='Vantagem (Peões)', format='.1f')),
                tooltip=['Lance', 'Vantagem']
            ).properties(
                height=300
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Nenhuma avaliação gerada para o gráfico.")
        
        st.divider()

        # --- Cards de Resumo de Categorias ---
        st.subheader("Detalhe dos Lances")
        # Definindo a ordem das categorias para a exibição
        cat_order_display = ["Melhor ⭐", "Excelente !", "Bom ✓", "Imprecisão ?!", "Erro ?", "Capivarada ??"]
        
        cols_summary = st.columns(len(cat_order_display))
        for idx, cat_label in enumerate(cat_order_display):
            count = resumo_categorias.get(cat_label, 0)
            # Para pegar a cor correta para o background do card
            _, bg_color = classificar_lance(
                0 if "Melhor" in cat_label else
                15 if "Excelente" in cat_label else
                40 if "Bom" in cat_label else
                100 if "Imprecisão" in cat_label else
                250 if "Erro" in cat_label else 500
            )
            
            cols_summary[idx].markdown(
                f"""<div style="background-color:{bg_color}; padding:12px; border-radius:10px; text-align:center; color:white; border: 1px solid rgba(255,255,255,0.2);">
                    <h3 style="margin:0; font-size:24px;">{count}</h3>
                    <small>{cat_label.split(' ')[0]}</small>
                </div>""", 
                unsafe_allow_html=True
            )

        st.divider()

        # --- Lista de Lances Detalhados (Expansível) ---
        st.subheader("Histórico de Lances")
        with st.expander("Clique para ver a análise de cada lance"):
            for item in lances_detalhados:
                st.markdown(
                    f"**{item['move_num']}.** {item['san']} ({item['uci']}) "
                    f"— <span style='color:{item['color']}; font-weight:bold;'>{item['label']}</span> "
                    f"(Perda: {item['perda_cp']} CP)", 
                    unsafe_allow_html=True
                )

# Rodapé ou informações extras
st.markdown("---")
st.markdown("Desenvolvido com Streamlit e Stockfish.")
