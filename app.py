import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="MSCI Sector Rotator Pro")

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

# --- 2. MOTOR DE DATOS (LÓGICA DE INTERSECCIÓN MÁXIMA) ---
@st.cache_data(ttl=3600)
def sincronizar_base_datos():
    hoy = datetime.now()
    
    if os.path.exists(CSV_FILE):
        # CARGA INCREMENTAL
        df_local = pd.read_csv(CSV_FILE, index_col=0, parse_dates=True)
        ultima_fecha = df_local.index.max()
        
        if (hoy - ultima_fecha).days >= 1:
            # Solo descargamos lo nuevo
            start_dl = ultima_fecha + timedelta(days=1)
            nuevos = yf.download(ALL_TICKERS, start=start_dl, end=hoy, progress=False)['Close']
            if not nuevos.empty:
                df_final = pd.concat([df_local, nuevos]).sort_index()
                df_final = df_final[~df_final.index.duplicated(keep='last')]
                df_final.to_csv(CSV_FILE)
                return df_final.ffill()
        return df_local.ffill()
    
    else:
        # CARGA INICIAL (Búsqueda del ETF con menor historial)
        with st.spinner("Construyendo base de datos histórica por primera vez..."):
            raw = yf.download(ALL_TICKERS, period="max", progress=False)['Close']
            
            # Buscamos la primera fecha donde TODOS los activos tienen datos
            # Esto evita que el backtest falle por falta de un solo ETF
            fecha_inicio_comun = raw.dropna().index.min()
            df_final = raw[raw.index >= fecha_inicio_comun].ffill()
            
            df_final.to_csv(CSV_FILE)
            return df_final

# --- 3. LÓGICA DE BACKTESTING ---
def ejecutar_estrategia(df, ma_period):
    # Ratio y Señal
    ratio = (df["HG=F"] / df["GC=F"]).dropna()
    ratio_ma = ratio.rolling(window=ma_period).mean()
    
    # Resample mensual para rotación
    prices_m = df.resample('ME').last()
    ratio_m = ratio.resample('ME').last()
    ratio_ma_m = ratio_ma.resample('ME').last()
    
    returns_m = prices_m.pct_change().shift(-1)
    
    resultados = []
    for i in range(len(prices_m) - 1):
        if pd.isna(ratio_ma_m.iloc[i]): continue
        
        # Régimen según Ratio Cobre/Oro
        es_ciclico = ratio_m.iloc[i] > ratio_ma_m.iloc[i]
        regimen = "🔥 Cíclico" if es_ciclico else "🛡️ Defensivo"
        pool = CICLICOS if es_ciclico else DEFENSIVOS
        
        # Momentum (Mejor retorno el mes anterior)
        ret_pasado = (prices_m.iloc[i] / prices_m.iloc[i-1]) - 1 if i > 0 else pd.Series(0, index=prices_m.columns)
        pool_t = {k: v for k, v in SECTORES_DICT.items() if k in pool}
        sorted_pool = sorted(pool_t.items(), key=lambda x: ret_pasado.get(x[1], -999), reverse=True)
        
        top_3_names = [x[0] for x in sorted_pool[:3]]
        top_3_tickers = [x[1] for x in sorted_pool[:3]]
        
        resultados.append({
            "Mes": prices_m.index[i+1].strftime('%Y-%m'),
            "Régimen": regimen,
            "Top 3 Sectores": ", ".join(top_3_names),
            "Ret. Estrategia": returns_m[top_3_tickers].iloc[i].mean(),
            "Ret. MSCI World": returns_m[BENCHMARK].iloc[i]
        })
    return pd.DataFrame(resultados)

# --- 4. INTERFAZ Y RENDERIZADO ---
st.title("🌍 MSCI World Sector Rotator")
st.caption("Estrategia basada en el Ratio Cobre/Oro con selección por Momentum")

# Parámetro de la Media Móvil
ma_val = st.sidebar.number_input("Media Móvil (Días)", value=50, step=1)

df_master = sincronizar_base_datos()

if not df_master.empty:
    df_bt = ejecutar_estrategia(df_master, ma_val)
    
    if not df_bt.empty:
        # Métricas
        cum_est = (1 + df_bt["Ret. Estrategia"]).prod() - 1
        cum_msci = (1 + df_bt["Ret. MSCI World"]).prod() - 1
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Historial Común", f"{df_master.index.min().year} - {df_master.index.max().year}")
        c2.metric("Estrategia (Acum)", f"{cum_est:.1%}")
        c3.metric("MSCI World (Acum)", f"{cum_msci:.1%}", delta=f"{(cum_est - cum_msci):.1%} Alpha")
        
        # Evolución
        df_bt["Idx_E"] = (1 + df_bt["Ret. Estrategia"]).cumprod() * 100
        df_bt["Idx_M"] = (1 + df_bt["Ret. MSCI World"]).cumprod() * 100
        st.line_chart(df_bt.set_index("Mes")[["Idx_E", "Idx_M"]])
        
        # Tabla
        st.subheader("Bitácora de Inversión")
        st.dataframe(df_bt.style.format({
            "Ret. Estrategia": "{:.2%}",
            "Ret. MSCI World": "{:.2%}"
        }).background_gradient(subset=["Ret. Estrategia"], cmap="RdYlGn"), use_container_width=True)
    else:
        st.info("Ajusta la media móvil para ver resultados.")
