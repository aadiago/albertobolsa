import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(layout="wide", page_title="Copper/Gold Tracker")

st.markdown("### 🌍 Monitor de Rotación: Cobre/Oro")
st.write("Si ves que los mensajes de abajo avanzan, el programa NO está colapsado.")

# --- 2. DEFINICIÓN DE TICKERS ---
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

# --- 3. MOTOR DE DATOS SEGURO (SIN HILOS) ---
@st.cache_data(ttl=86400)
def descargar_datos_seguro(anios):
    fin = datetime.now()
    inicio = fin - timedelta(days=anios * 365 + 100)
    
    df_result = pd.DataFrame()
    
    # Usamos un contenedor de texto para dar feedback en tiempo real
    status = st.empty()
    bar = st.progress(0)
    
    for i, ticker in enumerate(ALL_TICKERS):
        status.info(f"⏳ Procesando activo {i+1}/{len(ALL_TICKERS)}: {ticker}")
        try:
            # Petición individual: la única forma 100% estable en Python 3.13
            ticker_obj = yf.Ticker(ticker)
            historial = ticker_obj.history(start=inicio, end=fin)
            if not historial.empty:
                df_result[ticker] = historial['Close']
            # Pausa táctica para que el servidor no nos bloquee
            time.sleep(0.3)
        except Exception as e:
            st.error(f"Error en {ticker}: {e}")
            
        bar.progress((i + 1) / len(ALL_TICKERS))
    
    status.success("✅ ¡Sincronización completa!")
    return df_result.ffill()

# --- 4. INTERFAZ Y EJECUCIÓN ---
with st.sidebar:
    st.header("Ajustes")
    años_selec = st.slider("Años de análisis", 1, 10, 3)
    media_movil = st.number_input("Media Móvil (días)", value=50)

# Botón para iniciar
if st.button("🚀 Ejecutar Estrategia"):
    precios = descargar_datos_seguro(años_selec)
    
    if not precios.empty:
        # A. Cálculo del Ratio
        ratio = precios["HG=F"] / precios["GC=F"]
        ma_ratio = ratio.rolling(window=media_movil).mean()
        
        # B. Datos Mensuales
        precios_m = precios.resample('ME').last()
        ratio_m = ratio.resample('ME').last()
        ma_m = ma_ratio.resample('ME').last()
        
        # Momentum y Retornos
        ret_pasados = precios_m.pct_change()
        ret_futuros = precios_m.pct_change().shift(-1)
        
        backtest = []
        for i in range(len(precios_m) - 1):
            if pd.isna(ma_m.iloc[i]): continue
            
            # Selección de bando
            es_on = ratio_m.iloc[i] > ma_m.iloc[i]
            universo = CICLICOS if es_on else DEFENSIVOS
            
            # Top 3 Sectores por Momentum
            datos_pool = {k: v for k, v in SECTORES.items() if k in universo}
            top_3 = sorted(datos_pool.items(), key=lambda x: ret_pasados.iloc[i].get(x[1], -999), reverse=True)[:3]
            
            nombres = [x[0] for x in top_3]
            tickers = [x[1] for x in top_3]
            
            backtest.append({
                "Fecha": precios_m.index[i+1].strftime('%Y-%m'),
                "Régimen": "Cíclico" if es_on else "Defensivo",
                "Sectores": ", ".join(nombres),
                "Rent. Estrategia": ret_futuros[tickers].iloc[i].mean(),
                "Rent. MSCI World": ret_futuros[BENCHMARK].iloc[i]
            })

        # --- 5. RESULTADOS ---
        df_res = pd.DataFrame(backtest)
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c_est = (1 + df_res["Rent. Estrategia"]).prod() - 1
        c_msci = (1 + df_res["Rent. MSCI World"]).prod() - 1
        c1.metric("Estrategia", f"{c_est:.1%}")
        c2.metric("MSCI World", f"{c_msci:.1%}")
        c3.metric("Alpha", f"{(c_est - c_msci):.1%}", delta=f"{(c_est - c_msci):.1%}")

        # Gráfico
        df_res["Idx_E"] = (1 + df_res["Rent. Estrategia"]).cumprod() * 100
        df_res["Idx_M"] = (1 + df_res["Rent. MSCI World"]).cumprod() * 100
        st.line_chart(df_res.set_index("Fecha")[["Idx_E", "Idx_M"]])
        
        st.subheader("Bitácora Mensual")
        st.dataframe(df_res, use_container_width=True)
    else:
        st.error("No se pudieron obtener datos. Inténtalo de nuevo.")
