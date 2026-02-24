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
    st.info("Estrategia: Ratio > Media = Cíclicos | Ratio < Media = Defensivos")

# Definición de Tickers (ETFs de Xtrackers/iShares en EU)
SECTORES = {
    "Tecnología": "TELW.PA", "Energía": "WELJ.DE", "Salud": "WELW.DE",
    "Consumo Básico": "XDW0.DE", "Financiero": "WF1E.DE", "Consumo Discrecional": "WELS.DE",
    "Industriales": "XDWI.DE", "Materiales": "XDWM.DE", "Utilities": "SPY2.DE",
    "Comunicación": "WELU.DE", "Real Estate": "WELD.DE"
}

CICLICOS = ["Tecnología", "Energía", "Financiero", "Consumo Discrecional", "Industriales", "Materiales"]
DEFENSIVOS = ["Salud", "Consumo Básico", "Utilities", "Comunicación", "Real Estate"]
BENCHMARK = "EUNL.DE"

# --- 3. MOTOR DE DATOS (CORREGIDO) ---
@st.cache_data(ttl=3600)
def get_backtest_data(years_back):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365 + 100) # Días extra para la media móvil
    
    try:
        # Descarga de Commodities para el Ratio
        # Usamos threads=False para mayor estabilidad en Streamlit Cloud
        raw_comm = yf.download(["HG=F", "GC=F"], start=start_date, end=end_date, progress=False, threads=False)
        
        # Manejo de MultiIndex en columnas
        if isinstance(raw_comm.columns, pd.MultiIndex):
            commodities = raw_comm['Close']
        else:
            commodities = raw_comm[['Close']]
            
        ratio = (commodities["HG=F"] / commodities["GC=F"]).dropna()
        
        # Descarga de Sectores y Benchmark
        all_tickers = list(SECTORES.values()) + [BENCHMARK]
        raw_prices = yf.download(all_tickers, start=start_date, end=end_date, progress=False, threads=False)
        
        if isinstance(raw_prices.columns, pd.MultiIndex):
            prices = raw_prices['Close']
        else:
            prices = raw_prices[['Close']]
            
        return ratio, prices.ffill()
    
    except Exception as e:
        st.error(f"Error en la descarga: {e}")
        return pd.Series(), pd.DataFrame()

# --- 4. EJECUCIÓN Y LÓGICA ---
ratio_ser, prices_df = get_backtest_data(years)

if not prices_df.empty and not ratio_ser.empty:
    # Cálculo de medias y remuestreo mensual
    ratio_ma_ser = ratio_ser.rolling(window=ma_ratio).mean()
    
    # Alineamos datos: tomamos el último día de cada mes para decidir el siguiente
    prices_m = prices_df.resample('ME').last()
    ratio_m = ratio_ser.resample('ME').last()
    ratio_ma_m = ratio_ma_ser.resample('ME').last()
    
    returns_m = prices_m.pct_change().shift(-1) # La rentabilidad que obtendremos el mes siguiente
    
    bt_results = []
    
    # Iteramos por los meses disponibles (excepto el último)
    for i in range(len(prices_m) - 1):
        fecha_decision = prices_m.index[i]
        
        # 1. Régimen
        current_ratio = ratio_m.iloc[i]
        current_ma = ratio_ma_m.iloc[i]
        
        if pd.isna(current_ma): continue
            
        is_cyclical = current_ratio > current_ma
        regime = "Risk-On (Cíclico)" if is_cyclical else "Risk-Off (Defensivo)"
        pool = CICLICOS if is_cyclical else DEFENSIVOS
        
        # 2. Momentum (Mejor retorno el mes previo a la decisión)
        if i > 0:
            past_return = (prices_m.iloc[i] / prices_m.iloc[i-1]) - 1
            pool_tickers = {k: v for k, v in SECTORES.items() if k in pool}
            # Ordenar sectores del pool por su retorno pasado
            sorted_pool = sorted(pool_tickers.items(), key=lambda x: past_return.get(x[1], -999), reverse=True)
            top_3_names = [x[0] for x in sorted_pool[:3]]
            top_3_tickers = [x[1] for x in sorted_pool[:3]]
        else:
            # Si es el primer mes, elegimos los 3 primeros del pool por defecto
            top_3_names = pool[:3]
            top_3_tickers = [SECTORES[n] for n in top_3_names]
        
        # 3. Rentabilidad del mes siguiente
        ret_estrategia = returns_m[top_3_tickers].iloc[i].mean()
        ret_msci = returns_m[BENCHMARK].iloc[i]
        
        bt_results.append({
            "Mes Inversión": prices_m.index[i+1].strftime('%Y-%m'),
            "Régimen": regime,
            "Sectores Elegidos": ", ".join(top_3_names),
            "Ret. Estrategia": ret_estrategia,
            "Ret. MSCI World": ret_msci,
            "Alpha": ret_estrategia - ret_msci
        })

    if bt_results:
        df_bt = pd.DataFrame(bt_results)
        
        # Métricas principales
        cum_est = (1 + df_bt["Ret. Estrategia"]).prod() - 1
        cum_msci = (1 + df_bt["Ret. MSCI World"]).prod() - 1
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Acumulado Estrategia", f"{cum_est*100:.2f}%")
        c2.metric("Acumulado MSCI World", f"{cum_msci*100:.2f}%")
        c3.metric("Alpha Total", f"{(cum_est - cum_msci)*100:.2f}%", 
                  delta=f"{(cum_est - cum_msci)*100:.2f}%")

        # Gráfico
        chart_data = pd.DataFrame({
            "Estrategia": (1 + df_bt["Ret. Estrategia"]).cumprod() * 100,
            "MSCI World": (1 + df_bt["Ret. MSCI World"]).cumprod() * 100
        }, index=df_bt["Mes Inversión"])
        st.line_chart(chart_data)

        st.subheader("Bitácora Mensual de Rotación")
        st.dataframe(df_bt.style.background_gradient(subset=['Alpha'], cmap='RdYlGn'), use_container_width=True)
    else:
        st.warning("No hay suficientes datos para el periodo y media móvil seleccionados.")
else:
    st.error("Error al obtener datos de Yahoo Finance. Intenta reducir los años de backtesting.")
