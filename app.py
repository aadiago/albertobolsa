import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(layout="wide", page_title="PRO Copper/Gold Rotator", page_icon="📈")

st.markdown("""
    <style>
    .main-title { font-size: 1.6rem; font-weight: bold; color: #1E1E1E; margin-top: -2rem; }
    .subtitle { font-style: italic; font-size: 0.9rem; color: #4A4A4A; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">COPPER/GOLD RATIO: ESTRATEGIA SECTORIAL</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Backtesting de Rotación Mensual vs MSCI World</p>', unsafe_allow_html=True)
st.divider()

# --- 2. DEFINICIÓN DE ACTIVOS ---
SECTORES_DICT = {
    "Tecnología": "TELW.PA", "Energía": "WELJ.DE", "Salud": "WELW.DE",
    "Consumo Básico": "XDW0.DE", "Financiero": "WF1E.DE", "Consumo Discrecional": "WELS.DE",
    "Industriales": "XDWI.DE", "Materiales": "XDWM.DE", "Utilities": "SPY2.DE",
    "Comunicación": "WELU.DE", "Real Estate": "WELD.DE"
}
CICLICOS = ["Tecnología", "Energía", "Financiero", "Consumo Discrecional", "Industriales", "Materiales"]
DEFENSIVOS = ["Salud", "Consumo Básico", "Utilities", "Comunicación", "Real Estate"]
BENCHMARK = "EUNL.DE"
COMMODITIES = ["HG=F", "GC=F"]
ALL_TICKERS = list(SECTORES_DICT.values()) + [BENCHMARK] + COMMODITIES

# --- 3. MOTOR DE DATOS OPTIMIZADO (CARGA INCREMENTAL) ---
@st.cache_data(ttl=3600)
def obtener_datos_históricos(years_back):
    file_path = "data_cache.csv"
    hoy = datetime.now()
    
    # Si existe el archivo, cargamos y actualizamos
    if os.path.exists(file_path):
        df_local = pd.read_csv(file_path, index_col=0, parse_dates=True)
        ultima_fecha = df_local.index.max()
        
        # Si la última fecha es de ayer o antes, descargamos el hueco
        if (hoy - ultima_fecha).days >= 1:
            inicio_descarga = ultima_fecha + timedelta(days=1)
            nuevos_datos = yf.download(ALL_TICKERS, start=inicio_descarga, end=hoy, progress=False)['Close']
            if not nuevos_datos.empty:
                df_final = pd.concat([df_local, nuevos_datos]).sort_index()
                df_final = df_final[~df_final.index.duplicated(keep='last')]
                df_final.to_csv(file_path)
                return df_final.ffill()
        return df_local.ffill()
    
    # Si no existe, descarga completa inicial
    else:
        inicio_inicial = hoy - timedelta(days=years_back * 365 + 150)
        df_inicial = yf.download(ALL_TICKERS, start=inicio_inicial, end=hoy, progress=False)['Close']
        df_inicial.to_csv(file_path)
        return df_inicial.ffill()

# --- 4. PARÁMETROS Y LÓGICA ---
with st.sidebar:
    st.header("Configuración")
    años_bt = st.slider("Años de Backtesting", 1, 15, 5)
    ma_periodo = st.number_input("Media Móvil Ratio (Días)", value=50)

with st.status("Actualizando base de datos y ejecutando estrategia...", expanded=False) as status:
    prices_all = obtener_datos_históricos(años_bt)
    
    if not prices_all.empty:
        # 1. Preparación del Ratio Cobre/Oro
        ratio = (prices_all["HG=F"] / prices_all["GC=F"]).dropna()
        ratio_ma = ratio.rolling(window=ma_periodo).mean()
        
        # 2. Muestreo Mensual (Cierre de mes)
        prices_m = prices_all.resample('ME').last()
        ratio_m = ratio.resample('ME').last()
        ratio_ma_m = ratio_ma.resample('ME').last()
        
        # Rentabilidad del mes siguiente (objetivo)
        returns_m = prices_m.pct_change().shift(-1)
        
        # 3. Simulación de Backtesting
        bt_results = []
        for i in range(len(prices_m) - 1):
            if pd.isna(ratio_ma_m.iloc[i]): continue
            
            # Decisión de Régimen
            es_ciclico = ratio_m.iloc[i] > ratio_ma_m.iloc[i]
            regimen = "🔥 Risk-On" if es_ciclico else "🛡️ Risk-Off"
            pool = CICLICOS if es_ciclico else DEFENSIVOS
            
            # Momentum: Sectores del pool que mejor lo hicieron el mes pasado
            retorno_pasado = (prices_m.iloc[i] / prices_m.iloc[i-1]) - 1 if i > 0 else pd.Series(0, index=prices_m.columns)
            pool_tickers = {k: v for k, v in SECTORES_DICT.items() if k in pool}
            sorted_pool = sorted(pool_tickers.items(), key=lambda x: retorno_pasado.get(x[1], -999), reverse=True)
            
            top_3_names = [x[0] for x in sorted_pool[:3]]
            top_3_tickers = [x[1] for x in sorted_pool[:3]]
            
            bt_results.append({
                "Mes": prices_m.index[i+1].strftime('%Y-%m'),
                "Régimen": regimen,
                "Sectores": ", ".join(top_3_names),
                "Rent. Estrategia": returns_m[top_3_tickers].iloc[i].mean(),
                "Rent. MSCI World": returns_m[BENCHMARK].iloc[i]
            })
            
        df_bt = pd.DataFrame(bt_results)
        status.update(label="✅ Análisis finalizado", state="complete")

# --- 5. VISUALIZACIÓN DE RESULTADOS ---
if not df_bt.empty:
    # Métricas de Alpha
    cum_est = (1 + df_bt["Rent. Estrategia"]).prod() - 1
    cum_msci = (1 + df_bt["Rent. MSCI World"]).prod() - 1
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Estrategia (Acumulado)", f"{cum_est:.1%}")
    col2.metric("MSCI World (Acumulado)", f"{cum_msci:.1%}")
    col3.metric("Alpha Generado", f"{(cum_est - cum_msci):.1%}", delta=f"{(cum_est - cum_msci):.1%}")

    # Gráfico de Evolución
    df_bt["Idx_Estrat"] = (1 + df_bt["Rent. Estrategia"]).cumprod() * 100
    df_bt["Idx_MSCI"] = (1 + df_bt["Rent. MSCI World"]).cumprod() * 100
    
    st.subheader("Evolución de la Inversión (Base 100)")
    st.line_chart(df_bt.set_index("Mes")[["Idx_Estrat", "Idx_MSCI"]])

    # Tabla Detallada
    st.subheader("Histórico de Rotación y Rentabilidad")
    st.dataframe(df_bt.style.format({
        "Rent. Estrategia": "{:.2%}",
        "Rent. MSCI World": "{:.2%}"
    }).background_gradient(subset=["Rent. Estrategia"], cmap="RdYlGn"), use_container_width=True)
else:
    st.warning("No hay datos suficientes para el periodo seleccionado.")
