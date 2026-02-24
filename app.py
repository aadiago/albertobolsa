import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Safe Mode - Sector Rotator")

st.title("🛡️ Modo Seguro (Python 3.13 Stable)")
st.info("Esta versión utiliza peticiones directas para evitar el RuntimeError de hilos.")

# Activos
SECTORES = {
    "Tecnología": "TELW.PA", "Energía": "WELJ.DE", "Salud": "WELW.DE",
    "Consumo Básico": "XDW0.DE", "Financiero": "WF1E.DE", "Consumo Discrecional": "WELS.DE",
    "Industriales": "XDWI.DE", "Materiales": "XDWM.DE", "Utilities": "SPY2.DE",
    "Comunicación": "WELU.DE", "Real Estate": "WELD.DE"
}
BENCHMARK = "EUNL.DE"
COMMODITIES = ["HG=F", "GC=F"]
ALL_TICKERS = list(SECTORES.values()) + [BENCHMARK] + COMMODITIES

# --- 2. MOTOR DE DATOS (SIN CACHÉ PARA DIAGNÓSTICO) ---
# Si esto funciona, luego activaremos la caché.
def descargar_datos_directos():
    master_data = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(ALL_TICKERS):
        try:
            status_text.text(f"Conectando con: {ticker}...")
            # Usamos Ticker() + history() que es más estable que download()
            t = yf.Ticker(ticker)
            # Pedimos solo 3 años como pediste para la prueba
            df_hist = t.history(period="3y")
            
            if not df_hist.empty:
                # Forzamos que la serie sea limpia
                master_data[ticker] = df_hist['Close']
            
            # Pequeña pausa para no saturar la conexión
            time.sleep(0.2)
        except Exception as e:
            st.error(f"Error en {ticker}: {str(e)}")
            
        progress_bar.progress((i + 1) / len(ALL_TICKERS))
    
    status_text.text("✅ Sincronización finalizada.")
    return pd.DataFrame(master_data)

# --- 3. EJECUCIÓN ---
if st.button("🚀 Ejecutar Diagnóstico de 3 Años"):
    try:
        df = descargar_datos_directos()
        
        if not df.empty:
            st.success(f"¡Conseguido! Datos obtenidos para {len(df.columns)} activos.")
            
            # Lógica de la estrategia resumida
            ratio = (df["HG=F"] / df["GC=F"]).ffill()
            ma = ratio.rolling(window=50).mean()
            
            # Resultados visuales
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Ratio Cobre/Oro")
                st.line_chart(ratio)
            with col2:
                st.subheader("Tabla de Datos (Cierres)")
                st.dataframe(df.tail())
                
            # Identificación de Régimen Actual
            if ratio.iloc[-1] > ma.iloc[-1]:
                st.warning("🔥 Régimen Actual: RISK-ON (Cíclico)")
            else:
                st.info("🛡️ Régimen Actual: RISK-OFF (Defensivo)")
                
        else:
            st.error("El DataFrame está vacío. Yahoo Finance no devolvió datos.")
            
    except Exception as global_e:
        st.exception(global_e)

with st.sidebar:
    st.write("Configuración de Prueba")
    st.write("- Periodo: 3 años")
    st.write("- Método: yf.Ticker.history")
    st.write("- Hilos: Desactivados")
