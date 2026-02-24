import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="PRO Copper/Gold Rotator")

# Tickers consolidados para una sola descarga
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

# --- 2. SIDEBAR OPTIMIZADA ---
with st.sidebar:
    st.title("⚙️ Parámetros")
    # Reducimos el default a 3 años para que la primera carga sea más ágil
    years = st.slider("Años de Backtesting", 1, 15, 3)
    ma_ratio = st.number_input("Media Móvil Ratio (Días)", value=50)
    st.divider()
    st.caption("Nota: Los datos se guardan en caché por 24h para mayor velocidad.")

# --- 3. MOTOR DE DATOS ULTRA-RÁPIDO ---
@st.cache_data(ttl=86400) # Caché de 24 horas
def download_all_data(years_back):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365 + 150)
    
    all_tickers = list(SECTORES_DICT.values()) + [BENCHMARK] + COMMODITIES
    
    # Descarga masiva en una sola petición
    data = yf.download(all_tickers, start=start_date, end=end_date, interval="1d", progress=False, threads=True)
    
    if data.empty or 'Close' not in data:
        return pd.DataFrame()
    
    return data['Close'].ffill()

# --- 4. LÓGICA DE EJECUCIÓN ---
with st.status("🚀 Sincronizando con mercados financieros...", expanded=True) as status:
    st.write("Descargando historial de precios...")
    prices_all = download_all_data(years)
    
    if not prices_all.empty:
        st.write("Calculando señales del Ratio Cobre/Oro...")
        # Extraer ratio
        ratio = (prices_all["HG=F"] / prices_all["GC=F"]).dropna()
        ratio_ma = ratio.rolling(window=ma_ratio).mean()
        
        st.write("Ejecutando simulación mensual...")
        # Remuestreo mensual (ME = Month End)
        prices_m = prices_all.resample('ME').last()
        ratio_m = ratio.resample('ME').last()
        ratio_ma_m = ratio_ma.resample('ME').last()
        
        returns_m = prices_m.pct_change().shift(-1)
        
        bt_results = []
        for i in range(len(prices_m) - 1):
            if pd.isna(ratio_ma_m.iloc[i]): continue
            
            # Decisión de régimen
            is_cyclical = ratio_m.iloc[i] > ratio_ma_m.iloc[i]
            pool = CICLICOS if is_cyclical else DEFENSIVOS
            
            # Momentum (sector que más subió el mes pasado)
            past_return = (prices_m.iloc[i] / prices_m.iloc[i-1]) - 1 if i > 0 else pd.Series(0, index=prices_m.columns)
            pool_tickers = {k: v for k, v in SECTORES_DICT.items() if k in pool}
            sorted_pool = sorted(pool_tickers.items(), key=lambda x: past_return.get(x[1], -999), reverse=True)
            
            top_3_names = [x[0] for x in sorted_pool[:3]]
            top_3_tickers = [x[1] for x in sorted_pool[:3]]
            
            bt_results.append({
                "Fecha": prices_m.index[i+1].strftime('%b %Y'),
                "Régimen": "🔥 Cíclico" if is_cyclical else "🛡️ Defensivo",
                "Top 3 Sectores": ", ".join(top_3_names),
                "Estrategia %": returns_m[top_3_tickers].iloc[i].mean(),
                "MSCI World %": returns_m[BENCHMARK].iloc[i]
            })
            
        df_bt = pd.DataFrame(bt_results)
        status.update(label="✅ Backtesting completado", state="complete", expanded=False)

# --- 5. RESULTADOS VISUALES ---
if not df_bt.empty:
    st.title("📊 Resultados del Análisis")
    
    # Métricas Alpha
    c1, c2, c3 = st.columns(3)
    cum_est = (1 + df_bt["Estrategia %"]).prod() - 1
    cum_msci = (1 + df_bt["MSCI World %"]).prod() - 1
    
    c1.metric("Estrategia (Acum)", f"{cum_est:.1%}")
    c2.metric("MSCI World (Acum)", f"{cum_msci:.1%}")
    c3.metric("Alpha Extra", f"{(cum_est - cum_msci):.1%}", delta=f"{(cum_est - cum_msci):.1%}")

    # Gráfico de Equidad
    df_bt["Idx_Estrat"] = (1 + df_bt["Estrategia %"]).cumprod() * 100
    df_bt["Idx_MSCI"] = (1 + df_bt["MSCI World %"]).cumprod() * 100
    st.line_chart(df_bt.set_index("Fecha")[["Idx_Estrat", "Idx_MSCI"]])

    st.subheader("Detalle de la Rotación")
    st.dataframe(df_bt.style.format({
        "Estrategia %": "{:.2%}",
        "MSCI World %": "{:.2%}"
    }), use_container_width=True)
else:
    st.info("Aumenta los años de backtesting o ajusta la media móvil para ver resultados.")
