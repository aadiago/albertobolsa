import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
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

# --- 2. MOTOR DE DATOS (VERSION SIN THREADING PARA EVITAR RUNTIME ERROR) ---
@st.cache_data(ttl=3600)
def sincronizar_base_datos():
    hoy = datetime.now()
    
    if os.path.exists(CSV_FILE):
        df_local = pd.read_csv(CSV_FILE, index_col=0, parse_dates=True)
        ultima_fecha = df_local.index.max()
        
        if (hoy - ultima_fecha).days >= 1:
            try:
                start_dl = ultima_fecha + timedelta(days=1)
                # IMPORTANTE: threads=False evita el error de la imagen
                nuevos = yf.download(ALL_TICKERS, start=start_dl, end=hoy, progress=False, threads=False)['Close']
                if not nuevos.empty:
                    df_final = pd.concat([df_local, nuevos]).sort_index()
                    df_final = df_final[~df_final.index.duplicated(keep='last')]
                    df_final.to_csv(CSV_FILE)
                    return df_final.ffill()
            except Exception as e:
                st.warning(f"Nota: No se pudieron bajar nuevos datos hoy ({e}). Usando histórico local.")
        return df_local.ffill()
    
    else:
        with st.status("Construyendo base de datos maestra...", expanded=True) as status:
            try:
                # Descarga inicial completa sin hilos para estabilidad
                raw = yf.download(ALL_TICKERS, period="max", progress=False, threads=False)['Close']
                fecha_inicio_comun = raw.dropna().index.min()
                df_final = raw[raw.index >= fecha_inicio_comun].ffill()
                df_final.to_csv(CSV_FILE)
                status.update(label="✅ Base de datos creada", state="complete")
                return df_final
            except Exception as e:
                st.error(f"Error crítico en la descarga inicial: {e}")
                return pd.DataFrame()

# --- 3. LÓGICA DE BACKTESTING ---
def ejecutar_estrategia(df, ma_period):
    ratio = (df["HG=F"] / df["GC=F"]).dropna()
    ratio_ma = ratio.rolling(window=ma_period).mean()
    
    prices_m = df.resample('ME').last()
    ratio_m = ratio.resample('ME').last()
    ratio_ma_m = ratio_ma.resample('ME').last()
    
    returns_m = prices_m.pct_change().shift(-1)
    
    resultados = []
    for i in range(len(prices_m) - 1):
        if pd.isna(ratio_ma_m.iloc[i]): continue
        
        es_ciclico = ratio_m.iloc[i] > ratio_ma_m.iloc[i]
        regimen = "🔥 Cíclico" if es_ciclico else "🛡️ Defensivo"
        pool = CICLICOS if es_ciclico else DEFENSIVOS
        
        ret_pasado = (prices_m.iloc[i] / prices_m.iloc[i-1]) - 1 if i > 0 else pd.Series(0, index=prices_m.columns)
        pool_t = {k: v for k, v in SECTORES_DICT.items() if k in pool}
        sorted_pool = sorted(pool_t.items(), key=lambda x: ret_pasado.get(x[1], -999), reverse=True)
        
        top_3_names = [x[0] for x in sorted_pool[:3]]
        top_3_tickers = [x[1] for x in sorted_pool[:3]]
        
        resultados.append({
            "Mes": prices_m.index[i+1].strftime('%Y-%m'),
            "Régimen": regimen,
            "Sectores": ", ".join(top_3_names),
            "Ret. Estrategia": returns_m[top_3_tickers].iloc[i].mean(),
            "Ret. MSCI World": returns_m[BENCHMARK].iloc[i]
        })
    return pd.DataFrame(resultados)

# --- 4. INTERFAZ ---
st.title("🌍 MSCI World Sector Rotator")

ma_val = st.sidebar.number_input("Media Móvil (Días)", value=50, step=1)
años_slider = st.sidebar.slider("Ver últimos X años", 1, 20, 10)

df_master = sincronizar_base_datos()

if not df_master.empty:
    # Filtrar por los años seleccionados en el slider
    fecha_corte = datetime.now() - timedelta(days=años_slider * 365)
    df_filtrado = df_master[df_master.index >= fecha_corte]
    
    df_bt = ejecutar_estrategia(df_filtrado, ma_val)
    
    if not df_bt.empty:
        cum_est = (1 + df_bt["Ret. Estrategia"]).prod() - 1
        cum_msci = (1 + df_bt["Ret. MSCI World"]).prod() - 1
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventana de Análisis", f"{años_slider} Años")
        c2.metric("Estrategia (Acum)", f"{cum_est:.1%}")
        c3.metric("MSCI World (Acum)", f"{cum_msci:.1%}", delta=f"{(cum_est - cum_msci):.1%} Alpha")
        
        df_bt["Idx_E"] = (1 + df_bt["Ret. Estrategia"]).cumprod() * 100
        df_bt["Idx_M"] = (1 + df_bt["Ret. MSCI World"]).cumprod() * 100
        st.line_chart(df_bt.set_index("Mes")[["Idx_E", "Idx_M"]])
        
        st.subheader("Histórico de Decisiones Mensuales")
        st.dataframe(df_bt.style.format({
            "Ret. Estrategia": "{:.2%}",
            "Ret. MSCI World": "{:.2%}"
        }).background_gradient(subset=["Ret. Estrategia"], cmap="RdYlGn"), use_container_width=True)
