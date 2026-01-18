import streamlit as st
import chess
import chess.engine
import chess.pgn
import pandas as pd
import altair as alt
import shutil
import os
from io import StringIO

# --- 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS ---
st.set_page_config(page_title="Chess Review Pro", layout="wide")

# CSS para replicar a interface escura e os ícones do Chess.com
st.markdown("""
    <style>
    .main { background-color: #262421; color: white; }
    .stMetric { background-color: #312e2b; padding: 15px; border-radius: 8px; border: 1px solid #403d39; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'Segoe UI', sans-serif; }
    .classification-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 6px 12px; margin-bottom: 3px; background-color: #2b2926; border-radius: 4px;
    }
    .icon-circle {
        width: 26px; height: 26px; border-radius: 50%; display: flex;
        align-items: center; justify-content: center; font-weight: bold; font-size: 13px; color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOCALIZAÇÃO DO MOTOR ---
def get_stockfish_path():
    # Busca o executável instalado via packages.txt
    path = shutil.which("stockfish") or "/usr/games/stockfish"
    return path if os.path.exists(path) else None

STOCKFISH_PATH = get_stockfish_path()

# --- 3. LÓGICA DE CLASSIFICAÇÃO E RATING ---
def get_move_category(loss):
    if loss
