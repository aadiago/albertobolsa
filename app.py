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
        status.info(f"⏳ Descargando base de datos ({i+1}/{len(TODOS_ACTIVOS)}): {ticker}")
        try:
            ticker_obj = yf.Ticker(ticker)
            historial = ticker_obj.history(start="2005-01-01")
            if not historial.empty:
                df_result[ticker] = historial['Close']
            time.sleep(0.1) 
        except Exception:
            pass # Ignoramos errores silenciosamente para no saturar la UI
            
        bar.progress((i + 1) / len(TODOS_ACTIVOS))
        
    status.empty()
    bar.empty()
    return df_result.ffill().bfill()

# --- 4. MOTOR MATEMÁTICO CACHEADO (EVITA LENTITUD) ---
@st.cache_data
def ejecutar_backtest(df_precios, lb, freq, sma_f):
    inicio_real = df_precios.apply(lambda x: x.first_valid_index()).max()
    sma_vals = df_precios.rolling(window=sma_f).mean()
    
    indices_bt = df_precios.loc[inicio_real:].index
    dias_reb = indices_bt[::freq]
    retornos_diarios = df_precios.pct_change(fill_method=None).fillna(0)
    ret_est = pd.Series(0.0, index=indices_bt)
    registro_completo = []
    
    for i in range(len(dias_reb)):
        f_ini = dias_reb[i]
        f_fin = dias_reb[i+1] if i+1 < len(dias_reb) else indices_bt[-1]
        elecciones_periodo = {}
        
        for nom, conf in SECCIONES.items():
            activos_disp = [t for t in conf['activos'] if t in df_precios.columns]
            
            if not activos_disp:
                elecciones_periodo[nom] = "Refugio (BIL)"
                if "BIL" in df_precios.columns:
                    ret_est.loc[f_ini:f_fin] += retornos_diarios.loc[f_ini:f_fin, "BIL"] * conf['peso']
                continue

            ventana = df_precios.loc[:f_ini, activos_disp].tail(lb + 1)
            v_rets = ventana.pct_change(fill_method=None).dropna()
            
            mu = v_rets.mean()
            sigma = v_rets.std()
            # Evitar divisiones por cero
            sharpe = (mu / sigma).replace([np.inf, -np.inf], 0).fillna(0) * np.sqrt(252)
            rent_10d = (ventana.iloc[-1] / ventana.iloc[0]) - 1
            
            validos = [t for t in activos_disp if rent_10d[t] > 0 and df_precios.loc[f_ini, t] > sma_vals.loc[f_ini, t]]
            ganador = sharpe[validos].idxmax() if validos else ("BIL" if "BIL" in df_precios.columns else activos_disp[0])
            
            elecciones_periodo[nom] = TRADUCCION.get(ganador, ganador)
            if ganador in retornos_diarios.columns:
                ret_est.loc[f_ini:f_fin] += retornos_diarios.loc[f_ini:f_fin, ganador] * conf['peso']
            
        registro_completo.append({"Fecha": f_ini.strftime('%Y-%m-%d'), **elecciones_periodo})

    # CÁLCULO DE MÉTRICAS ALINEADAS (BASE 100)
    bench_valido = BENCHMARK if BENCHMARK in retornos_diarios.columns else retornos_diarios.columns[0]
    
    df_res = pd.DataFrame({
        'Estrategia': (1 + ret_est).cumprod(),
        'Benchmark': (1 + retornos_diarios.loc[ret_est.index, bench_valido]).cumprod()
    })
    
    # FORZAR A QUE AMBOS EMPIECEN EXACTAMENTE EN 100 EN EL DÍA 1
    df_res = (df_res / df_res.iloc[0]) * 100
    
    dd_est = (df_res['Estrategia'] - df_res['Estrategia'].cummax()) / df_res['Estrategia'].cummax()
    dd_bench = (df_res['Benchmark'] - df_res['Benchmark'].cummax()) / df_res['Benchmark'].cummax()
    
    cagr_est = ((df_res['Estrategia'].iloc[-1] / 100) ** (252/len(df_res)) - 1)
    ulcer_est = np.sqrt(np.mean(dd_est**2))
    mdd_est = dd_est.min()
    
    df_bitacora = pd.DataFrame(registro_completo).set_index("Fecha")
    
    # DATOS DE HOY
    hoy = df_precios.index[-1]
    res_hoy = {}
    for nom, conf in SECCIONES.items():
        activos_disp_hoy = [t for t in conf['activos'] if t in df_precios.columns]
        if not activos_disp_hoy:
            res_hoy[nom] = "Sin datos"
            continue
        v_h = df_precios[activos_disp_hoy].tail(lb + 1)
        r_h = (v_h.iloc[-1] / v_h.iloc[0]) - 1
        val_h = [t for t in activos_disp_hoy if r_h[t] > 0 and df_precios.loc[hoy, t] > sma_vals.loc[hoy, t]]
        if not val_h: 
            res_hoy[nom] = "Refugio (BIL)"
        else:
            v_rets_h = v_h.pct_change(fill_method=None).dropna()
            sh_h = (v_rets_h.mean() / v_rets_h.std()).fillna(0) * np.sqrt(252)
            res_hoy[nom] = TRADUCCION.get(sh_h[val_h].idxmax(), sh_h[val_h].idxmax())

    return df_res, df_bitacora, dd_est, dd_bench, cagr_est, ulcer_est, mdd_est, res_hoy, hoy

# --- 5. RENDERIZADO PRINCIPAL ---
precios = descargar_datos_seguro()

if not precios.empty:
    # Llamamos a la función cacheada. Si cambias los filtros en la barra lateral, solo recula esto.
    df_res, df_bitacora, dd_est, dd_bench, cagr_est, ulcer_est, mdd_est, res_hoy, hoy = ejecutar_backtest(precios, lookback, freq_reb, sma_filtro)

    st.markdown("### 📊 Métricas de Rendimiento")
    c1, c2, c3 = st.columns(3)
    c1.metric("CAGR Estrategia", f"{cagr_est:.2%}")
    c2.metric("Ulcer Index", f"{ulcer_est:.2%}")
    c3.metric("Max Drawdown", f"{mdd_est:.2%}")

    st.markdown("### 📈 Crecimiento vs Benchmark (Base 100)")
    df_chart = df_res.copy()
    df_chart.index = df_chart.index.tz_localize(None) 
    st.line_chart(df_chart)

    st.markdown("### 📉 Drawdown Comparativo")
    df_dd = pd.DataFrame({'DD Estrategia': dd_est, 'DD Benchmark': dd_bench})
    df_dd.index = df_dd.index.tz_localize(None)
    st.line_chart(df_dd)

    st.markdown(f"### 🎯 Selección Hipotética para Hoy ({hoy.strftime('%Y-%m-%d')})")
    cols_hoy = st.columns(len(SECCIONES))
    for idx, (nom, resultado) in enumerate(res_hoy.items()):
        cols_hoy[idx].info(f"**{nom}**\n\n{resultado}")

    st.markdown("### 📓 Historial de Asignación")
    st.dataframe(df_bitacora, use_container_width=True)
    
    csv = df_bitacora.to_csv().encode('utf-8')
    st.download_button(
        label="📥 Descargar Historial (CSV)",
        data=csv,
        file_name='historial_rotacion.csv',
        mime='text/csv',
    )
else:
    st.error("No se pudieron obtener datos. Revisa tu conexión a internet o los tickers proporcionados.")
