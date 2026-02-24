import streamlit as st
import yfinance as yf
import pandas as pd
import traceback
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PARÁMETROS (TUS VALORES POR DEFECTO) ---
DEFAULT_ULCER = 3.0 #
DEFAULT_VELOCITY = 30.0 #
REG_PERIODS = 63 #
R2_MIN = 60 #

st.set_page_config(layout="wide", page_title="Safe Debug Mode")
st.title("🛠️ Modo de Diagnóstico Final")

# Lista reducida para asegurar que el motor arranca
SECTORES = {
    "Tecnología": "TELW.PA", "Energía": "WELJ.DE", "Salud": "WELW.DE",
    "Consumo Básico": "XDW0.DE", "Financiero": "WF1E.DE",
    "MSCI World": "EUNL.DE", "Cobre": "HG=F", "Oro": "GC=F"
}

# --- MOTOR DE DESCARGA ATÓMICO ---
def descargar_seguro(tickers_dict):
    datos = {}
    for nombre, ticker in tickers_dict.items():
        try:
            st.write(f"⏳ Descargando {nombre} ({ticker})...")
            # Usamos Ticker individual para evitar hilos de yfinance
            t = yf.Ticker(ticker)
            # Limitamos a 2 años para máxima velocidad en la prueba
            df_hist = t.history(period="2y")
            if not df_hist.empty:
                datos[ticker] = df_hist['Close']
                st.write(f"✅ {nombre} completado.")
            else:
                st.error(f"❌ {nombre} devolvió datos vacíos.")
        except Exception as e:
            st.error(f"❌ Error crítico en {nombre}: {str(e)}")
    return pd.DataFrame(datos)

# --- EJECUCIÓN ---
if st.button("🚀 INICIAR DESCARGA Y ANÁLISIS"):
    try:
        df = descargar_seguro(SECTORES)
        
        if not df.empty:
            st.success("¡DATOS RECUPERADOS EXITOSAMENTE!")
            
            # Cálculo del Ratio
            df['Ratio'] = df['HG=F'] / df['GC=F']
            df['MA50'] = df['Ratio'].rolling(window=50).mean()
            
            # Muestra de resultados con tus parámetros
            st.subheader("Resultados del Análisis")
            col1, col2, col3 = st.columns(3)
            col1.metric("Regresión Periodos", REG_PERIODS) #
            col2.metric("Velocity Default", f"{DEFAULT_VELOCITY}%") #
            col3.metric("Max Ulcer Index", DEFAULT_ULCER) #
            
            # Gráfico simple
            st.line_chart(df[['Ratio', 'MA50']].dropna())
            
            st.write("Últimos datos de cierre:")
            st.dataframe(df.tail())
            
        else:
            st.error("No se pudo crear el DataFrame. Revisa los mensajes de arriba.")
            
    except Exception:
        st.error("SE HA PRODUCIDO UN ERROR DE SISTEMA:")
        st.code(traceback.format_exc())

st.sidebar.info(f"Configuración cargada:\n- R² Mín: {R2_MIN}%\n- Periodos: {REG_PERIODS}") #
