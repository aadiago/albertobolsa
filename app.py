import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Test 3 Años - Sector Rotator")

st.title("🧪 Test de Estabilidad (3 años)")
st.info("Estamos forzando la descarga de solo los últimos 3 años para descartar bloqueos por volumen.")

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

# --- 2. MOTOR DE DATOS ULTRA-LIGERO ---
@st.cache_data(ttl=3600)
def test_descarga_3_años():
    fin = datetime.now()
    inicio = fin - timedelta(days=3 * 365)
    
    # Descargamos uno a uno con una pausa para que el servidor no se sature
    master_data = {}
    progreso = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(ALL_TICKERS):
        status_text.text(f"Descargando ({i+1}/{len(ALL_TICKERS)}): {ticker}...")
        try:
            # Usamos period="3y" que es la forma más rápida en Yahoo
            data = yf.download(ticker, start=inicio, end=fin, progress=False, threads=False)
            if not data.empty:
                # Extraemos la columna 'Close' de forma segura
                if isinstance(data.columns, pd.MultiIndex):
                    master_data[ticker] = data['Close'][ticker]
                else:
                    master_data[ticker] = data['Close']
            time.sleep(0.5) # Pausa de seguridad
        except Exception as e:
            st.warning(f"Error en {ticker}: {e}")
        
        progreso.progress((i + 1) / len(ALL_TICKERS))
    
    status_text.text("✅ Descarga finalizada.")
    return pd.DataFrame(master_data).ffill()

# --- 3. EJECUCIÓN ---
if st.button("🚀 Iniciar Test de 3 Años"):
    df = test_descarga_3_años()
    
    if not df.empty:
        st.success(f"¡Éxito! Se han descargado {len(df)} días de datos.")
        
        # Lógica rápida de Ratio para verificar
        ratio = df["HG=F"] / df["GC=F"]
        ma = ratio.rolling(window=50).mean()
        
        # Gráfico rápido
        st.subheader("Ratio Cobre/Oro (Últimos 3 años)")
        df_plot = pd.DataFrame({"Ratio": ratio, "Media 50d": ma})
        st.line_chart(df_plot)
        
        # Mostrar tabla de sectores para confirmar
        st.subheader("Precios de Cierre (Muestra)")
        st.dataframe(df.tail())
    else:
        st.error("La descarga devolvió un DataFrame vacío.")

with st.sidebar:
    if st.button("🗑️ Limpiar Caché"):
        st.cache_data.clear()
        st.rerun()
