import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Copper/Gold Sector Rotator")

st.title("🌍 Rotación Sectorial: Cobre/Oro vs MSCI World")
st.markdown("Estrategia: Cobre/Oro > Media (Cíclicos) | Cobre/Oro < Media (Defensivos)")

# --- 2. TICKERS ---
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

# --- 3. MOTOR DE DESCARGA (SECUENCIAL PARA EVITAR ERRORES) ---
@st.cache_data(ttl=86400)
def descargar_datos(años):
    fin = datetime.now()
    inicio = fin - timedelta(days=años * 365 + 100)
    
    master_df = pd.DataFrame()
    progreso = st.progress(0)
    status = st.empty()
    
    for i, ticker in enumerate(ALL_TICKERS):
        status.text(f"Descargando {ticker}...")
        try:
            # Descarga individual: la más lenta pero la única que no falla en 3.13
            data = yf.Ticker(ticker).history(start=inicio, end=fin)
            if not data.empty:
                master_df[ticker] = data['Close']
            time.sleep(0.2) 
        except Exception as e:
            st.error(f"Fallo en {ticker}: {e}")
        progreso.progress((i + 1) / len(ALL_TICKERS))
    
    status.empty()
    progreso.empty()
    return master_df.ffill()

# --- 4. INTERFAZ DE USUARIO ---
with st.sidebar:
    st.header("Configuración")
    años_bt = st.slider("Años de Backtesting", 1, 15, 5)
    ma_ratio = st.number_input("Media Móvil Ratio (Días)", value=50)
    if st.button("Recargar Datos"):
        st.cache_data.clear()
        st.rerun()

# --- 5. LÓGICA DE LA ESTRATEGIA ---
df_precios = descargar_datos(años_bt)

if not df_precios.empty:
    # A. Señal
    ratio = (df_precios["HG=F"] / df_precios["GC=F"]).dropna()
    ma = ratio.rolling(window=ma_ratio).mean()
    
    # B. Datos Mensuales
    # Usamos el cierre de mes para decidir y el mes siguiente para medir rentabilidad
    df_m = df_precios.resample('ME').last()
    ratio_m = ratio.resample('ME').last()
    ma_m = ma.resample('ME').last()
    
    returns_m = df_m.pct_change() # Retorno pasado (para momentum)
    future_returns_m = df_m.pct_change().shift(-1) # Retorno futuro (el que ganamos)
    
    bt_log = []
    
    for i in range(len(df_m) - 1):
        if pd.isna(ma_m.iloc[i]): continue
        
        # 1. Régimen
        regimen_on = ratio_m.iloc[i] > ma_m.iloc[i]
        pool = CICLICOS if regimen_on else DEFENSIVOS
        
        # 2. Selección Top 3 por Momentum (mejor retorno el mes anterior)
        past_rets = returns_m.iloc[i]
        pool_tickers = {k: v for k, v in SECTORES.items() if k in pool}
        # Ordenamos y cogemos los 3 mejores
        top_3 = sorted(pool_tickers.items(), key=lambda x: past_rets.get(x[1], -999), reverse=True)[:3]
        
        nombres_selec = [x[0] for x in top_3]
        tickers_selec = [x[1] for x in top_3]
        
        # 3. Resultado
        ret_estrategia = future_returns_m[tickers_selec].iloc[i].mean()
        ret_msci = future_returns_m[BENCHMARK].iloc[i]
        
        bt_log.append({
            "Fecha": df_m.index[i+1].strftime('%Y-%m'),
            "Régimen": "Cíclico" if regimen_on else "Defensivo",
            "Sectores": ", ".join(nombres_selec),
            "Estrategia %": ret_est := (ret_estrategia * 100),
            "MSCI World %": ret_m := (ret_msci * 100),
            "Alpha": ret_est - ret_m
        })

    if bt_log:
        df_bt = pd.DataFrame(bt_log)
        
        # --- 6. RESULTADOS ---
        c1, c2, c3 = st.columns(3)
        cum_e = (1 + df_bt["Estrategia %"]/100).prod() - 1
        cum_m = (1 + df_bt["MSCI World %"]/100).prod() - 1
        
        c1.metric("Retorno Estrategia", f"{cum_e:.1%}")
        c2.metric("Retorno MSCI World", f"{cum_m:.1%}")
        c3.metric("Alpha Generado", f"{(cum_e - cum_m):.1%}", delta=f"{(cum_e - cum_m):.1%}")
        
        # Gráfico
        df_bt["Idx_E"] = (1 + df_bt["Estrategia %"]/100).cumprod() * 100
        df_bt["Idx_M"] = (1 + df_bt["MSCI World %"]/100).cumprod() * 100
        st.line_chart(df_bt.set_index("Fecha")[["Idx_E", "Idx_M"]])
        
        # Tabla
        st.dataframe(df_bt.style.format({
            "Estrategia %": "{:.2f}%",
            "MSCI World %": "{:.2f}%",
            "Alpha": "{:.2f}%"
        }).background_gradient(subset=["Alpha"], cmap="RdYlGn"), use_container_width=True)
    else:
        st.warning("No hay suficientes datos comunes para el periodo seleccionado.")
else:
    st.error("No se han podido descargar los datos. Inténtalo de nuevo en unos minutos.")
