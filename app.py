import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(layout="wide", page_title="Rotación de Activos")

with st.sidebar:
    st.header("Ajustes de la Estrategia")
    lookback = st.number_input("Lookback (días)", min_value=1, value=10)
    freq_reb = st.number_input("Frecuencia Rebalanceo (días)", min_value=1, value=10)
    sma_filtro = st.number_input("Filtro SMA (días)", min_value=10, value=100)
    st.markdown("*(Los pesos de las secciones se configuran en el código fuente)*")

st.markdown("### 🌍 Monitor de Estrategia de Rotación Multisección")
st.write("Si ves que los mensajes de abajo avanzan, el programa NO está colapsado.")

# --- 2. PARÁMETROS MAESTROS Y DICCIONARIOS ---
BENCHMARK = "SXR8.DE"

TRADUCCION = {
    "XDWU.DE": "Global Utilities", "XDWH.DE": "Global Health", "XDW0.DE": "Global Energy", "XDWM.DE": "Global Materials",
    "XWTS.DE": "Global Communication", "XDWI.DE": "Global Industrials", "XDWC.DE": "Global Discretionary", "SPY2.DE": "Global Real Estate",
    "XDWS.DE": "Global Staples", "XDWT.DE": "Global Tech", "XDWF.DE": "Global Financials", "VVSM.DE": "Semiconductors",
    "8PSD.DE": "Gold", "WENH.DE": "Metals", "BTC-USD": "Bitcoin",
    "BIL": "Refugio (BIL)", "SXR8.DE": "S&P 500", "CEB1.DE": "EURO 20Y+", "DBXP.DE": "EURO 1-3Y", "CMOD.MI": "COMMODITIES"
}

SECCIONES = {
    "TECNOLOGIA": {"peso": 0.50, "activos": ["XDWT.DE", "VVSM.DE"]},
    "DEFENSIVO":  {"peso": 0.40, "activos": ["8PSD.DE", "XDWU.DE", "XDWS.DE", "CEB1.DE", "DBXP.DE"]},
    "SORPRESA":   {"peso": 0.10, "activos": ["XDW0.DE", "XDWM.DE", "XWTS.DE", "XDWI.DE", "XDWH.DE", "XDWC.DE", "SPY2.DE", "XDWF.DE", "WENH.DE", "CMOD.MI", "BTC-USD"]}
}

TODOS_ACTIVOS = [BENCHMARK, "BIL"]
for s in SECCIONES.values(): TODOS_ACTIVOS.extend(s['activos'])
TODOS_ACTIVOS = list(set(TODOS_ACTIVOS))

# --- 3. MOTOR DE DATOS SEGURO ---
@st.cache_data(ttl=86400)
def descargar_datos_seguro():
    df_result = pd.DataFrame()
    status = st.empty()
    bar = st.progress(0)
    
    for i, ticker in enumerate(TODOS_ACTIVOS):
        status.info(f"⏳ Procesando activo {i+1}/{len(TODOS_ACTIVOS)}: {ticker}")
        try:
            ticker_obj = yf.Ticker(ticker)
            historial = ticker_obj.history(start="2005-01-01")
            if not historial.empty:
                df_result[ticker] = historial['Close']
            time.sleep(0.3) 
        except Exception as e:
            st.error(f"Aviso: No se pudo descargar {ticker}")
            
        bar.progress((i + 1) / len(TODOS_ACTIVOS))
        
    status.success("✅ ¡Sincronización completa!")
    time.sleep(1) 
    status.empty()
    bar.empty()
    return df_result.ffill().bfill()

# --- 4. EJECUCIÓN DIRECTA ---
precios = descargar_datos_seguro()

if not precios.empty:
    inicio_real = precios.apply(lambda x: x.first_valid_index()).max()
    sma_vals = precios.rolling(window=sma_filtro).mean()
    
    indices_bt = precios.loc[inicio_real:].index
    dias_reb = indices_bt[::freq_reb]
    retornos_diarios = precios.pct_change(fill_method=None).fillna(0)
    ret_est = pd.Series(0.0, index=indices_bt)
    registro_completo = []
    
    for i in range(len(dias_reb)):
        f_ini = dias_reb[i]
        f_fin = dias_reb[i+1] if i+1 < len(dias_reb) else indices_bt[-1]
        elecciones_periodo = {}
        
        for nom, conf in SECCIONES.items():
            # ESCUDO ANTI-KEYERROR: Solo usamos los activos que realmente están en el DataFrame
            activos_disp = [t for t in conf['activos'] if t in precios.columns]
            
            if not activos_disp:
                elecciones_periodo[nom] = "Refugio (BIL)"
                ret_est.loc[f_ini:f_fin] += retornos_diarios.loc[f_ini:f_fin, "BIL"] * conf['peso'] if "BIL" in precios.columns else 0
                continue

            ventana = precios.loc[:f_ini, activos_disp].tail(lookback + 1)
            v_rets = ventana.pct_change(fill_method=None).dropna()
            mu, sigma = v_rets.mean(), v_rets.std()
            sharpe = (mu / sigma).replace([np.inf, -np.inf], 0).fillna(0) * np.sqrt(252)
            rent_10d = (ventana.iloc[-1] / ventana.iloc[0]) - 1
            
            validos = [t for t in activos_disp if rent_10d[t] > 0 and precios.loc[f_ini, t] > sma_vals.loc[f_ini, t]]
            ganador = sharpe[validos].idxmax() if validos else ("BIL" if "BIL" in precios.columns else activos_disp[0])
            
            elecciones_periodo[nom] = TRADUCCION.get(ganador, ganador)
            # Acumulamos el retorno si el ganador está en los datos
            if ganador in retornos_diarios.columns:
                ret_est.loc[f_ini:f_fin] += retornos_diarios.loc[f_ini:f_fin, ganador] * conf['peso']
            
        registro_completo.append({"Fecha": f_ini.strftime('%Y-%m-%d'), **elecciones_periodo})

    # --- 5. RESULTADOS Y MÉTRICAS ---
    # Verificamos que el Benchmark esté disponible para comparativas
    bench_valido = BENCHMARK if BENCHMARK in retornos_diarios.columns else retornos_diarios.columns[0]
    
    df_res = pd.DataFrame({
        'Estrategia': (1 + ret_est).cumprod(),
        'Benchmark': (1 + retornos_diarios.loc[ret_est.index, bench_valido]).cumprod()
    })
    
    dd_est = (df_res['Estrategia'] - df_res['Estrategia'].cummax()) / df_res['Estrategia'].cummax()
    dd_bench = (df_res['Benchmark'] - df_res['Benchmark'].cummax()) / df_res['Benchmark'].cummax()
    
    cagr_est = (df_res['Estrategia'].iloc[-1]**(252/len(df_res))-1)
    ulcer_est = np.sqrt(np.mean(dd_est**2))
    mdd_est = dd_est.min()

    st.markdown("### 📊 Métricas de Rendimiento")
    c1, c2, c3 = st.columns(3)
    c1.metric("CAGR Estrategia", f"{cagr_est:.2%}")
    c2.metric("Ulcer Index", f"{ulcer_est:.2%}")
    c3.metric("Max Drawdown", f"{mdd_est:.2%}")

    st.markdown("### 📈 Crecimiento vs Benchmark")
    df_chart = df_res.copy()
    df_chart.index = df_chart.index.tz_localize(None) 
    st.line_chart(df_chart)

    st.markdown("### 📉 Drawdown Comparativo")
    df_dd = pd.DataFrame({'DD Estrategia': dd_est, 'DD Benchmark': dd_bench})
    df_dd.index = df_dd.index.tz_localize(None)
    st.line_chart(df_dd)

    # SELECCIÓN HIPOTÉTICA PARA HOY
    hoy = precios.index[-1]
    st.markdown(f"### 🎯 Selección Hipotética para Hoy ({hoy.strftime('%Y-%m-%d')})")
    cols_hoy = st.columns(len(SECCIONES))
    
    for idx, (nom, conf) in enumerate(SECCIONES.items()):
        activos_disp_hoy = [t for t in conf['activos'] if t in precios.columns]
        
        if not activos_disp_hoy:
            cols_hoy[idx].info(f"**{nom}**\n\nSin datos disponibles")
            continue

        v_h = precios[activos_disp_hoy].tail(lookback + 1)
        r_h = (v_h.iloc[-1] / v_h.iloc[0]) - 1
        val_h = [t for t in activos_disp_hoy if r_h[t] > 0 and precios.loc[hoy, t] > sma_vals.loc[hoy, t]]
        
        if not val_h: 
            res = "Refugio (BIL)"
        else:
            v_rets_h = v_h.pct_change(fill_method=None).dropna()
            sh_h = (v_rets_h.mean() / v_rets_h.std()).fillna(0) * np.sqrt(252)
            res = TRADUCCION.get(sh_h[val_h].idxmax(), sh_h[val_h].idxmax())
            
        cols_hoy[idx].info(f"**{nom}**\n\n{res}")

    # BITÁCORA Y EXPORTACIÓN
    st.markdown("### 📓 Historial de Asignación")
    df_bitacora = pd.DataFrame(registro_completo).set_index("Fecha")
    st.dataframe(df_bitacora, use_container_width=True)
    
    # Descarga para trabajar en hojas de cálculo
    csv = df_bitacora.to_csv().encode('utf-8')
    st.download_button(
        label="📥 Descargar Historial (CSV)",
        data=csv,
        file_name='historial_rotacion.csv',
        mime='text/csv',
    )

else:
    st.error("No se pudieron obtener datos. Revisa tu conexión a internet o los tickers proporcionados.")
