import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(layout="wide", page_title="MSCI Sector Rotator")

st.markdown("""
    <style>
    .main-title { font-size: 1.6rem; font-weight: bold; color: #1E1E1E; margin-top: -1rem; }
    .subtitle { font-style: italic; font-size: 0.9rem; color: #4A4A4A; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🌍 ESTRATEGIA COPPER/GOLD</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Rotación Mensual de Sectores MSCI World</p>', unsafe_allow_html=True)

# --- 2. DEFINICIÓN DE ACTIVOS ---
SECTORES = {
    "Tecnología": "TELW.PA", "Energía": "WELJ.DE", "Salud": "WELW.DE",
    "Consumo Básico": "XDW0.DE", "Financiero": "WF1E.DE", "Consumo Discrecional": "WELS.DE",
    "Industriales": "XDWI.DE", "Materiales": "XDWM.DE", "Utilities": "SPY2.DE",
    "Comunicación": "WELU.DE", "Real Estate": "WELD.DE"
}
CICLICOS = ["Tecnología", "Energía", "Financiero", "Consumo Discrecional", "Industriales", "Materiales"]
DEFENSIVOS = ["Salud", "Consumo Básico", "Utilities", "Comunicación", "Real Estate"]
BENCHMARK = "EUNL.DE"
COMMODITIES = ["HG=F", "GC=F"]
ALL_TICKERS = list(SECTORES.values()) + [BENCHMARK] + COMMODITIES

# --- 3. MOTOR DE DATOS (OPTIMIZADO PARA STREAMLIT CLOUD) ---
@st.cache_data(ttl=86400)
def cargar_datos_seguro():
    # Limitamos a 20 años para evitar que el servidor se cuelgue procesando "max"
    fin = datetime.now()
    inicio = fin - timedelta(days=20 * 365)
    
    try:
        # Una sola petición masiva es más estable que 15 peticiones individuales
        # threads=False es CRÍTICO para evitar el RuntimeError en Streamlit Cloud
        data = yf.download(ALL_TICKERS, start=inicio, end=fin, progress=False, threads=False)
        
        if data.empty or 'Close' not in data:
            return pd.DataFrame()
            
        df = data['Close'].ffill()
        # Buscamos el denominador común: el primer día que todos tienen datos
        primer_dia_valido = df.dropna().index.min()
        return df[df.index >= primer_dia_valido]
    except Exception as e:
        st.error(f"Error de conexión con Yahoo Finance: {e}")
        return pd.DataFrame()

# --- 4. PARÁMETROS EN SIDEBAR ---
with st.sidebar:
    st.header("Configuración")
    ma_ratio = st.number_input("Media Móvil Ratio (Días)", value=50, min_value=10)
    st.divider()
    if st.button("🔄 Forzar Recarga de Datos"):
        st.cache_data.clear()
        st.rerun()

# --- 5. EJECUCIÓN ---
with st.spinner("Sincronizando mercados..."):
    df_precios = cargar_datos_seguro()

if not df_precios.empty:
    # A. Cálculo de Señales
    ratio = df_precios["HG=F"] / df_precios["GC=F"]
    ratio_ma = ratio.rolling(window=ma_ratio).mean()
    
    # B. Remuestreo Mensual
    # Usamos 'ME' para el final de mes y calculamos retornos del mes siguiente
    df_m = df_precios.resample('ME').last()
    ratio_m = ratio.resample('ME').last()
    ma_m = ratio_ma.resample('ME').last()
    
    returns_next_m = df_m.pct_change().shift(-1)
    returns_past_m = df_m.pct_change() # Para momentum
    
    # C. Simulación
    history = []
    for i in range(len(df_m) - 1):
        if pd.isna(ma_m.iloc[i]): continue
        
        # 1. Determinar Régimen
        es_ciclico = ratio_m.iloc[i] > ma_m.iloc[i]
        pool = CICLICOS if es_ciclico else DEFENSIVOS
        
        # 2. Selección Top 3 por Momentum (retorno del mes que acaba de cerrar)
        past_rets = returns_past_m.iloc[i]
        pool_tickers = {k: v for k, v in SECTORES.items() if k in pool}
        # Ordenamos los sectores del pool por su rentabilidad el mes pasado
        top_3 = sorted(pool_tickers.items(), key=lambda x: past_rets.get(x[1], -999), reverse=True)[:3]
        
        nombres_top = [x[0] for x in top_3]
        tickers_top = [x[1] for x in top_3]
        
        # 3. Rentabilidad obtenida en el mes siguiente
        ret_est = returns_next_m[tickers_top].iloc[i].mean()
        ret_msci = returns_next_m[BENCHMARK].iloc[i]
        
        history.append({
            "Mes": df_m.index[i+1].strftime('%Y-%m'),
            "Régimen": "🔥 Cíclico" if es_ciclico else "🛡️ Defensivo",
            "Sectores": ", ".join(nombres_top),
            "Estrategia %": ret_est,
            "MSCI World %": ret_msci,
            "Alpha %": ret_est - ret_msci
        })

    if history:
        df_res = pd.DataFrame(history)
        
        # --- VISUALIZACIÓN ---
        c1, c2, c3 = st.columns(3)
        cum_e = (1 + df_res["Estrategia %"]).prod() - 1
        cum_m = (1 + df_res["MSCI World %"]).prod() - 1
        
        c1.metric("Rango", f"{df_res['Mes'].iloc[0]} a {df_res['Mes'].iloc[-1]}")
        c2.metric("Estrategia (Total)", f"{cum_e:.1%}")
        c3.metric("MSCI World (Total)", f"{cum_m:.1%}", delta=f"{(cum_e - cum_m):.1%} Alpha")
        
        # Gráfico de Equity
        df_res["Idx_E"] = (1 + df_res["Estrategia %"]).cumprod() * 100
        df_res["Idx_M"] = (1 + df_res["MSCI World %"]).cumprod() * 100
        st.line_chart(df_res.set_index("Mes")[["Idx_E", "Idx_M"]])
        
        # Tabla detallada
        st.dataframe(
            df_res.style.format({"Estrategia %": "{:.2%}", "MSCI World %": "{:.2%}", "Alpha %": "{:.2%}"})
            .background_gradient(subset=["Alpha %"], cmap="RdYlGn"),
            use_container_width=True
        )
    else:
        st.warning("No hay datos suficientes para el periodo común de los ETFs seleccionados.")
else:
    st.error("No se pudo cargar la base de datos. Pulsa el botón de 'Forzar Recarga' en el lateral.")
