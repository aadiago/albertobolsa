import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="MSCI World Sector Rotator")

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

# --- 2. MOTOR DE DATOS (SIN HILOS - ULTRA ROBUSTO) ---
@st.cache_data(ttl=3600)
def sincronizar_base_datos():
    hoy = datetime.now()
    
    # Intento de carga desde archivo local para ahorrar tiempo
    if os.path.exists(CSV_FILE):
        try:
            df_local = pd.read_csv(CSV_FILE, index_col=0, parse_dates=True)
            ultima_fecha = df_local.index.max()
            
            # Si faltan datos nuevos (más de 1 día)
            if (hoy - ultima_fecha).days >= 1:
                with st.status("Actualizando con datos recientes...", expanded=False) as s:
                    nuevos_datos = {}
                    for ticker in ALL_TICKERS:
                        t = yf.Ticker(ticker)
                        # Descarga individual simple
                        h = t.history(start=ultima_fecha + timedelta(days=1), end=hoy)
                        if not h.empty:
                            nuevos_datos[ticker] = h['Close']
                    
                    if nuevos_datos:
                        df_nuevos = pd.DataFrame(nuevos_datos)
                        df_local = pd.concat([df_local, df_nuevos]).sort_index()
                        df_local = df_local[~df_local.index.duplicated(keep='last')]
                        df_local.to_csv(CSV_FILE)
            return df_local.ffill()
        except Exception:
            pass # Si el CSV está corrupto, re-descargamos todo

    # DESCARGA INICIAL DESDE CERO
    with st.status("Sincronizando historial completo (Solo una vez)...", expanded=True) as status:
        master_dict = {}
        for i, ticker in enumerate(ALL_TICKERS):
            status.write(f"Descargando {ticker}...")
            try:
                # Obtenemos el máximo historial de cada uno
                t = yf.Ticker(ticker)
                h = t.history(period="max")
                if not h.empty:
                    master_dict[ticker] = h['Close']
                time.sleep(0.1) # Pausa para evitar bloqueos de Yahoo
            except Exception as e:
                status.write(f"⚠️ Error en {ticker}: {e}")
        
        if master_dict:
            raw = pd.DataFrame(master_dict)
            # BUSCAR EL DENOMINADOR COMÚN (ETF más joven)
            # Filtramos para que todos tengan datos desde el mismo día
            fecha_inicio_comun = raw.dropna().index.min()
            df_final = raw[raw.index >= fecha_inicio_comun].ffill()
            df_final.to_csv(CSV_FILE)
            status.update(label="✅ Datos sincronizados", state="complete")
            return df_final
        return pd.DataFrame()

# --- 3. LÓGICA DE LA ESTRATEGIA ---
def analizar_estrategia(df, ma_period):
    # Ratio Cobre/Oro
    ratio = (df["HG=F"] / df["GC=F"]).dropna()
    ratio_ma = ratio.rolling(window=ma_period).mean()
    
    # Resample mensual
    prices_m = df.resample('ME').last()
    ratio_m = ratio.resample('ME').last()
    ratio_ma_m = ratio_ma.resample('ME').last()
    
    returns_m = prices_m.pct_change().shift(-1)
    
    resultados = []
    for i in range(len(prices_m) - 1):
        if pd.isna(ratio_ma_m.iloc[i]): continue
        
        # Régimen según el ratio
        es_ciclico = ratio_m.iloc[i] > ratio_ma_m.iloc[i]
        regimen = "🔥 Cíclico" if es_ciclico else "🛡️ Defensivo"
        pool = CICLICOS if es_ciclico else DEFENSIVOS
        
        # Selección por Momentum (mejor rendimiento mes anterior)
        ret_pasado = (prices_m.iloc[i] / prices_m.iloc[i-1]) - 1 if i > 0 else pd.Series(0, index=prices_m.columns)
        activos_universo = {k: v for k, v in SECTORES_DICT.items() if k in pool}
        sorted_pool = sorted(activos_universo.items(), key=lambda x: ret_pasado.get(x[1], -999), reverse=True)
        
        top_3_names = [x[0] for x in sorted_pool[:3]]
        top_3_tickers = [x[1] for x in sorted_pool[:3]]
        
        resultados.append({
            "Mes": prices_m.index[i+1].strftime('%Y-%m'),
            "Régimen": regimen,
            "Top 3 Sectores": ", ".join(top_3_names),
            "Estrategia %": returns_m[top_3_tickers].iloc[i].mean(),
            "MSCI World %": returns_m[BENCHMARK].iloc[i]
        })
    return pd.DataFrame(resultados)

# --- 4. INTERFAZ ---
st.title("🌍 MSCI World Sector Rotator")

ma_val = st.sidebar.number_input("Media Móvil Ratio (Días)", value=50, step=1)
años_slider = st.sidebar.slider("Años en gráfico", 1, 20, 5)

# Ejecución del motor
df_master = sincronizar_base_datos()

if not df_master.empty:
    # Filtro de tiempo para el análisis
    fecha_corte = datetime.now() - timedelta(days=años_slider * 365)
    df_filtrado = df_master[df_master.index >= fecha_corte]
    
    df_bt = analizar_estrategia(df_filtrado, ma_val)
    
    if not df_bt.empty:
        # Métricas principales
        cum_est = (1 + df_bt["Estrategia %"]).prod() - 1
        cum_msci = (1 + df_bt["MSCI World %"]).prod() - 1
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Inicio Historial", df_master.index.min().strftime('%d/%m/%Y'))
        c2.metric("Estrategia (Total)", f"{cum_est:.1%}")
        c3.metric("MSCI World (Total)", f"{cum_msci:.1%}", delta=f"{(cum_est - cum_msci):.1%} Alpha")
        
        # Gráfico
        df_bt["Idx_E"] = (1 + df_bt["Estrategia %"]).cumprod() * 100
        df_bt["Idx_M"] = (1 + df_bt["Rentabilidad MSCI World" if "Rentabilidad MSCI World" in df_bt else "MSCI World %"]).cumprod() * 100
        st.line_chart(df_bt.set_index("Mes")[["Idx_E", "Idx_M"]])
        
        # Tabla detallada
        st.subheader("Bitácora Mensual")
        st.dataframe(df_bt.style.format({
            "Estrategia %": "{:.2%}",
            "MSCI World %": "{:.2%}"
        }).background_gradient(subset=["Estrategia %"], cmap="RdYlGn"), use_container_width=True)
else:
    st.error("No se han podido cargar los datos. Comprueba tu conexión o los tickers.")
