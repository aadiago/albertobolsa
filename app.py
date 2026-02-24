import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(layout="wide", page_title="MSCI Sector Rotator Pro")

# Definición de activos y sectores
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
CSV_FILE = "msci_master_data.csv"

# --- 2. MOTOR DE DATOS (DESCARGA SECUENCIAL ROBUSTA) ---
@st.cache_data(ttl=3600)
def sincronizar_datos():
    hoy = datetime.now()
    
    # Caso A: El archivo ya existe, solo actualizamos los días faltantes
    if os.path.exists(CSV_FILE):
        df_local = pd.read_csv(CSV_FILE, index_col=0, parse_dates=True)
        ultima_fecha = df_local.index.max()
        
        if (hoy - ultima_fecha).days >= 1:
            with st.status("Buscando actualizaciones de mercado...", expanded=False):
                start_dl = ultima_fecha + timedelta(days=1)
                nuevos_datos = {}
                for ticker in ALL_TICKERS:
                    try:
                        # Descarga individual para evitar errores de hilos
                        data = yf.Ticker(ticker).history(start=start_dl, end=hoy)
                        if not data.empty:
                            nuevos_datos[ticker] = data['Close']
                    except Exception:
                        continue
                
                if nuevos_datos:
                    df_nuevos = pd.DataFrame(nuevos_datos)
                    df_final = pd.concat([df_local, df_nuevos]).sort_index()
                    df_final = df_final[~df_final.index.duplicated(keep='last')]
                    df_final.to_csv(CSV_FILE)
                    return df_final.ffill()
        return df_local.ffill()
    
    # Caso B: Carga inicial (descarga uno a uno para evitar el RuntimeError)
    else:
        with st.status("Creando base de datos maestra (esto solo ocurre una vez)...", expanded=True) as status:
            master_dict = {}
            progreso = st.progress(0)
            for i, ticker in enumerate(ALL_TICKERS):
                status.write(f"Sincronizando: {ticker}")
                try:
                    # Obtenemos el máximo historial posible para cada uno
                    hist = yf.Ticker(ticker).history(period="max")
                    if not hist.empty:
                        master_dict[ticker] = hist['Close']
                    time.sleep(0.2) # Pausa técnica para evitar bloqueos
                except Exception as e:
                    status.write(f"⚠️ Error en {ticker}: {e}")
                progreso.progress((i + 1) / len(ALL_TICKERS))
            
            if master_dict:
                raw = pd.DataFrame(master_dict)
                # Buscamos la fecha común más antigua para todos los activos
                fecha_inicio = raw.dropna().index.min()
                df_final = raw[raw.index >= fecha_inicio].ffill()
                df_final.to_csv(CSV_FILE)
                status.update(label="✅ Base de datos completada", state="complete")
                return df_final
            return pd.DataFrame()

# --- 3. LÓGICA DE LA ESTRATEGIA ---
def analizar_estrategia(df, periodo_ma):
    # Cálculo del Ratio y su Media Móvil
    ratio = (df["HG=F"] / df["GC=F"]).dropna()
    ratio_ma = ratio.rolling(window=periodo_ma).mean()
    
    # Muestreo mensual (último día de cada mes)
    precios_m = df.resample('ME').last()
    ratio_m = ratio.resample('ME').last()
    ratio_ma_m = ratio_ma.resample('ME').last()
    
    # Rentabilidad que se obtendrá el mes siguiente
    retornos_futuros = precios_m.pct_change().shift(-1)
    
    logs = []
    for i in range(len(precios_m) - 1):
        if pd.isna(ratio_ma_m.iloc[i]): continue
        
        # Clasificación del régimen
        es_ciclico = ratio_m.iloc[i] > ratio_ma_m.iloc[i]
        regimen_txt = "🔥 Cíclico" if es_ciclico else "🛡️ Defensivo"
        universo = CICLICOS if es_ciclico else DEFENSIVOS
        
        # Selección por Momentum (mejor rendimiento el mes previo a la decisión)
        rend_pasado = (precios_m.iloc[i] / precios_m.iloc[i-1]) - 1 if i > 0 else pd.Series(0, index=precios_m.columns)
        activos_universo = {k: v for k, v in SECTORES_DICT.items() if k in universo}
        top_3 = sorted(activos_universo.items(), key=lambda x: rend_pasado.get(x[1], -999), reverse=True)[:3]
        
        nombres_top = [x[0] for x in top_3]
        tickers_top = [x[1] for x in top_3]
        
        logs.append({
            "Mes": precios_m.index[i+1].strftime('%Y-%m'),
            "Régimen": regimen_txt,
            "Sectores": ", ".join(nombres_top),
            "Estrategia %": retornos_futuros[tickers_top].iloc[i].mean(),
            "MSCI World %": retornos_futuros[BENCHMARK].iloc[i]
        })
    return pd.DataFrame(logs)

# --- 4. RENDERIZADO PRINCIPAL ---
st.title("🌍 Estrategia de Rotación Sectorial")

# Controles en el lateral
ma_input = st.sidebar.number_input("Media Móvil del Ratio (Días)", value=50, min_value=10)
ventana_años = st.sidebar.slider("Años de visualización", 1, 25, 10)

# Ejecución
datos_maestros = sincronizar_datos()

if not datos_maestros.empty:
    # Filtro temporal según el slider
    fecha_limite = datetime.now() - timedelta(days=ventana_años * 365)
    df_ver = datos_maestros[datos_maestros.index >= fecha_limite]
    
    resultados = analizar_estrategia(df_ver, ma_input)
    
    if not resultados.empty:
        # Métricas Resumen
        c1, c2, c3 = st.columns(3)
        ret_est = (1 + resultados["Estrategia %"]).prod() - 1
        ret_msci = (1 + resultados["MSCI World %"]).prod() - 1
        
        c1.metric("Rango del Backtest", f"{df_ver.index.min().year} - {df_ver.index.max().year}")
        c2.metric("Estrategia (Total)", f"{ret_est:.1%}")
        c3.metric("MSCI World (Total)", f"{ret_msci:.1%}", delta=f"{(ret_est - ret_msci):.1%} Alpha")
        
        # Gráfico Comparativo
        resultados["Curva Estrategia"] = (1 + resultados["Estrategia %"]).cumprod() * 100
        resultados["Curva MSCI World"] = (1 + resultados["MSCI World %"]).cumprod() * 100
        st.line_chart(resultados.set_index("Mes")[["Curva Estrategia", "Curva MSCI World"]])
        
        # Tabla de Log
        st.subheader("Bitácora de Decisiones")
        st.dataframe(resultados.style.format({
            "Estrategia %": "{:.2%}",
            "MSCI World %": "{:.2%}"
        }).background_gradient(subset=["Estrategia %"], cmap="RdYlGn"), use_container_width=True)
    else:
        st.info("No hay datos suficientes para calcular la estrategia con esa configuración.")
else:
    st.error("No se pudo inicializar la base de datos. Por favor, reinicia la aplicación.")
