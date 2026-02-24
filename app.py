import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Safe Rotator")

st.markdown("""
    <style>
    .main-title { font-size: 1.5rem; font-weight: bold; color: #1E1E1E; }
    .stProgress > div > div > div > div { background-color: #00ACEE; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🌍 Estrategia Sectorial Cobre/Oro</p>', unsafe_allow_html=True)

# Tickers estrictos
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
CSV_FILE = "db_precios.csv"

# --- 2. MOTOR DE DATOS (SISTEMA DE SEGURIDAD) ---
def sincronizar_activos():
    df_final = pd.DataFrame()
    
    # Si existe el archivo, lo leemos para no pedir datos antiguos
    if os.path.exists(CSV_FILE):
        df_final = pd.read_csv(CSV_FILE, index_col=0, parse_dates=True)
        start_date = df_final.index.max() + timedelta(days=1)
    else:
        # Si no existe, bajamos los últimos 5 años (evitamos 'max' para no saturar)
        start_date = datetime.now() - timedelta(days=5 * 365)

    # Si necesitamos actualizar (ha pasado más de un día)
    if (datetime.now() - start_date.replace(tzinfo=None) if start_date.tzinfo else datetime.now() - start_date).days >= 1:
        with st.status("🚀 Sincronizando datos paso a paso...", expanded=True) as status:
            nuevos_datos = {}
            for ticker in ALL_TICKERS:
                status.write(f"Actualizando {ticker}...")
                try:
                    # history() es mucho más estable que download() en Python 3.13
                    h = yf.Ticker(ticker).history(start=start_date, end=datetime.now())
                    if not h.empty:
                        nuevos_datos[ticker] = h['Close']
                    time.sleep(0.2) # Pausa mínima para no colapsar la conexión
                except:
                    continue
            
            if nuevos_datos:
                df_new = pd.DataFrame(nuevos_datos)
                df_final = pd.concat([df_final, df_new]).sort_index()
                df_final = df_final[~df_final.index.duplicated(keep='last')]
                df_final.to_csv(CSV_FILE)
            status.update(label="✅ Datos al día", state="complete")
    
    return df_final.ffill()

# --- 3. LÓGICA DE CONTROL ---
with st.sidebar:
    st.header("Configuración")
    ma_val = st.number_input("Media Móvil Ratio (Días)", value=50)
    if st.button("Limpiar y Recargar Todo"):
        if os.path.exists(CSV_FILE): os.remove(CSV_FILE)
        st.cache_data.clear()
        st.rerun()

# --- 4. EJECUCIÓN ---
df = sincronizar_activos()

if not df.empty and all(c in df.columns for c in COMMODITIES):
    # Ratio
    ratio = (df["HG=F"] / df["GC=F"]).dropna()
    ma = ratio.rolling(window=ma_val).mean()
    
    # Análisis Mensual
    df_m = df.resample('ME').last()
    ratio_m = ratio.resample('ME').last()
    ma_m = ma.resample('ME').last()
    
    ret_futuros = df_m.pct_change().shift(-1)
    ret_pasados = df_m.pct_change()
    
    bt = []
    for i in range(len(df_m) - 1):
        if pd.isna(ma_m.iloc[i]): continue
        
        # Régimen
        pool = CICLICOS if ratio_m.iloc[i] > ma_m.iloc[i] else DEFENSIVOS
        
        # Momentum (Top 3 del bando elegido)
        past = ret_pasados.iloc[i]
        t_pool = {k: v for k, v in SECTORES.items() if k in pool}
        top_3 = sorted(t_pool.items(), key=lambda x: past.get(x[1], -999), reverse=True)[:3]
        
        t_tickers = [x[1] for x in top_3]
        
        bt.append({
            "Mes": df_m.index[i+1].strftime('%Y-%m'),
            "Régimen": "Cíclico" if ratio_m.iloc[i] > ma_m.iloc[i] else "Defensivo",
            "Sectores": ", ".join([x[0] for x in top_3]),
            "Estrategia %": ret_futuros[t_tickers].iloc[i].mean() * 100,
            "MSCI World %": ret_futuros[BENCHMARK].iloc[i] * 100
        })

    if bt:
        df_bt = pd.DataFrame(bt)
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c_est = (1 + df_bt["Estrategia %"]/100).prod() - 1
        c_msci = (1 + df_bt["MSCI World %"]/100).prod() - 1
        c1.metric("Estrategia", f"{c_est:.1%}")
        c2.metric("MSCI World", f"{c_msci:.1%}")
        c3.metric("Alpha", f"{(c_est - c_msci):.1%}", delta=f"{(c_est - c_msci):.1%}")

        # Gráfico
        df_bt["Idx_E"] = (1 + df_bt["Estrategia %"]/100).cumprod() * 100
        df_bt["Idx_M"] = (1 + df_bt["MSCI World %"]/100).cumprod() * 100
        st.line_chart(df_bt.set_index("Mes")[["Idx_E", "Idx_M"]])
        
        # Tabla
        st.dataframe(df_bt.style.format({"Estrategia %": "{:.2f}%", "MSCI World %": "{:.2f}%"}), use_container_width=True)
else:
    st.info("Esperando sincronización de datos...")
