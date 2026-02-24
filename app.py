import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(layout="wide", page_title="COPPER/GOLD SECTOR ROTATOR", page_icon="📈")

st.markdown("""
    <style>
    .main-title { font-size: 1.6rem; font-weight: bold; color: #1E1E1E; margin-top: -2rem; }
    .subtitle { font-style: italic; font-size: 0.9rem; color: #4A4A4A; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">COPPER/GOLD RATIO: ESTRATEGIA SECTORIAL</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Backtesting de Rotación Mensual vs MSCI World - Sofía y Alberto 2026</p>', unsafe_allow_html=True)
st.divider()

# --- 2. PARAMETRIZACIÓN ---
with st.sidebar:
    st.header("Configuración")
    years = st.slider("Años de Backtesting", 1, 15, 5)
    ma_ratio = st.number_input("Media Móvil Ratio (Días)", value=50)
    st.info("La estrategia selecciona los 3 mejores sectores cíclicos si el Ratio > Media, o los 3 mejores defensivos si el Ratio < Media.")

# Definición de Tickers
SECTORES = {
    "Tecnología": "TELW.PA",
    "Energía": "WELJ.DE",
    "Salud": "WELW.DE",
    "Consumo Básico": "XDW0.DE",
    "Financiero": "WF1E.DE",
    "Consumo Discrecional": "WELS.DE",
    "Industriales": "XDWI.DE",
    "Materiales": "XDWM.DE",
    "Utilities": "SPY2.DE",
    "Comunicación": "WELU.DE",
    "Real Estate": "WELD.DE"
}

CICLICOS = ["Tecnología", "Energía", "Financiero", "Consumo Discrecional", "Industriales", "Materiales"]
DEFENSIVOS = ["Salud", "Consumo Básico", "Utilities", "Comunicación", "Real Estate"]
BENCHMARK = "EUNL.DE" # MSCI World

# --- 3. MOTOR DE DATOS ---
@st.cache_data
def get_backtest_data(years_back):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365)
    
    # Descargar Cobre y Oro para el Ratio
    commodities = yf.download(["HG=F", "GC=F"], start=start_date, end=end_date)['Close']
    ratio = commodities["HG=F"] / commodities["GC=F"]
    
    # Descargar Sectores y Benchmark
    all_tickers = list(SECTORES.values()) + [BENCHMARK]
    prices = yf.download(all_tickers, start=start_date, end=end_date)['Close']
    
    return ratio, prices

# --- 4. LÓGICA DE BACKTESTING ---
ratio_ser, prices_df = get_backtest_data(years)

if not prices_df.empty:
    # Preparar datos mensuales
    prices_m = prices_df.resample('MS').first()
    ratio_m = ratio_ser.resample('MS').first()
    ratio_ma = ratio_ser.rolling(window=ma_ratio).mean().resample('MS').first()
    
    returns_m = prices_m.pct_change().shift(-1) # Rentabilidad del mes siguiente
    
    bt_results = []
    
    for i in range(len(prices_m) - 1):
        fecha = prices_m.index[i]
        
        # 1. Determinar Régimen
        regime = "Risk-On (Cíclico)" if ratio_m.iloc[i] > ratio_ma.iloc[i] else "Risk-Off (Defensivo)"
        pool = CICLICOS if "Risk-On" in regime else DEFENSIVOS
        
        # 2. Seleccionar Top 3 por Momentum (retorno del último mes)
        momentum = prices_m.pct_change().iloc[i]
        top_3_tickers = []
        
        # Filtrar tickers del pool actual y ordenar
        pool_tickers = {k: v for k, v in SECTORES.items() if k in pool}
        sorted_pool = sorted(pool_tickers.items(), key=lambda x: momentum[x[1]], reverse=True)
        top_3_names = [x[0] for x in sorted_pool[:3]]
        top_3_tickers = [x[1] for x in sorted_pool[:3]]
        
        # 3. Calcular Retorno
        ret_estrategia = returns_m[top_3_tickers].iloc[i].mean()
        ret_msci = returns_m[BENCHMARK].iloc[i]
        
        bt_results.append({
            "Fecha": fecha,
            "Régimen": regime,
            "Sectores": ", ".join(top_3_names),
            "Ret. Estrategia": ret_estrategia,
            "Ret. MSCI World": ret_msci,
            "Alpha": ret_estrategia - ret_msci
        })

    df_bt = pd.DataFrame(bt_results).dropna()

    # --- 5. VISUALIZACIÓN ---
    col1, col2, col3 = st.columns(3)
    
    cum_est = (1 + df_bt["Ret. Estrategia"]).prod() - 1
    cum_msci = (1 + df_bt["Ret. MSCI World"]).prod() - 1
    
    col1.metric("Retorno Acum. Estrategia", f"{cum_est*100:.2f}%")
    col2.metric("Retorno Acum. MSCI World", f"{cum_msci*100:.2f}%")
    col3.metric("Alpha Generado", f"{(cum_est - cum_msci)*100:.2f}%", delta=f"{(cum_est - cum_msci)*100:.2f}%")

    # Gráfico de evolución
    df_bt["Estrategia_Idx"] = (1 + df_bt["Ret. Estrategia"]).cumprod() * 100
    df_bt["MSCI_Idx"] = (1 + df_bt["Ret. MSCI World"]).cumprod() * 100
    
    st.subheader("Evolución de 100€ invertidos")
    st.line_chart(df_bt.set_index("Fecha")[["Estrategia_Idx", "MSCI_Idx"]])

    st.subheader("Detalle Mensual")
    st.dataframe(df_bt.style.format({
        "Ret. Estrategia": "{:.2%}",
        "Ret. MSCI World": "{:.2%}",
        "Alpha": "{:.2%}"
    }), use_container_width=True)
else:
    st.error("No se pudieron descargar los datos. Verifica la conexión o los tickers.")

