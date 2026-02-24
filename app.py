import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import io
import os
from datetime import date

# --- 1. CONFIGURACIÓN VISUAL Y ESTADOS ---
st.set_page_config(layout="wide", page_title="MSCI WORLD TRACKER PRO", page_icon="🌍")

if 'page' not in st.session_state:
    st.session_state.page = 'main'

if 'show_bt' not in st.session_state:
    st.session_state.show_bt = False

# Parámetros de Análisis
PARAM_PERIODOS_REG = 63
PARAM_R2_MIN = 60
PARAM_RSI_MIN = 50
PARAM_MAX_ULCER = 3.0
PARAM_MAX_DIST_MEDIA = 10
PARAM_VELOCITY = 30

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:italic,wght@400;700&display=swap');
    
    .block-container {
        padding-bottom: 1rem !important;
    }
    .main-title {
        font-size: 1.4rem;
        font-weight: bold;
        margin-bottom: 0px;
        margin-top: -2rem;
        color: #1E1E1E;
        line-height: 1.1;
    }
    .alberto-sofia {
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 0.9rem;
        color: #4A4A4A;
        margin-top: 2px;
        margin-bottom: 5px;
        line-height: 1.1;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CABECERA COMPACTA ---
col_h1, col_h2 = st.columns([1, 25])
with col_h1:
    st.markdown("<h1>🌍</h1>", unsafe_allow_html=True)
with col_h2: 
    st.markdown('<p class="main-title">PENGUIN MSCI WORLD TRACKER</p>', unsafe_allow_html=True)
    st.markdown('<p class="alberto-sofia">Sofía y Alberto 2026</p>', unsafe_allow_html=True)

st.divider()

# --- 3. MOTOR DE EXTRACCIÓN Y TRADUCCIÓN DE DATOS ---
@st.cache_data(ttl=86400) 
def obtener_empresas_msci_world_v9():
    url = "https://www.ishares.com/us/products/239696/ishares-msci-world-etf/1467271812596.ajax?fileType=csv&fileName=URTH_holdings&dataType=fund"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        lineas = response.text.splitlines()
        header_idx = 0
        for i, linea in enumerate(lineas):
            if "Ticker" in linea and "Name" in linea:
                header_idx = i
                break
                
        df = pd.read_csv(io.StringIO(response.text), skiprows=header_idx)
        df.columns = df.columns.str.strip()
        
        if 'Weight (%)' in df.columns:
            peso_col = 'Weight (%)'
        elif 'Weight' in df.columns:
            peso_col = 'Weight'
        else:
            df['Peso_Falso'] = 0.0
            peso_col = 'Peso_Falso'
            
        df = df.dropna(subset=['Ticker', 'Sector'])
        df = df[df['Asset Class'] == 'Equity']
        
        sufijos = {
            'london': '.L', 'tokyo': '.T', 'toronto': '.TO', 'amsterdam': '.AS',
            'paris': '.PA', 'brussels': '.BR', 'belgium': '.BR', 'lisbon': '.LS',
            'xetra': '.DE', 'frankfurt': '.DE', 'germany': '.DE', 'six swiss': '.SW',
            'switzerland': '.SW', 'madrid': '.MC', 'spain': '.MC', 'borsa italiana': '.MI',
            'milan': '.MI', 'italy': '.MI', 'sydney': '.AX', 'australia': '.AX',
            'copenhagen': '.CO', 'denmark': '.CO', 'stockholm': '.ST', 'sweden': '.ST',
            'oslo': '.OL', 'norway': '.OL', 'helsinki': '.HE', 'finland': '.HE',
            'hong kong': '.HK', 'singapore': '.SI', 'vienna': '.VI', 'austria': '.VI',
            'tel aviv': '.TA', 'israel': '.TA', 'new zealand': '.NZ', 'dublin': '.IR',
            'ireland': '.IR'
        }
        
        tickers_adaptados = []
        for _, row in df.iterrows():
            ticker_original = str(row['Ticker']).strip()
            ticker_upper = ticker_original.upper()
            nombre_empresa = str(row['Name']).upper()
            
            if 'CONSTELLATION SOFTWARE' in nombre_empresa:
                tickers_adaptados.append('CSU.TO')
                continue
            if 'CAPITALAND INTEGRATED' in nombre_empresa:
                tickers_adaptados.append('M3T.F')
                continue
            if 'BERKSHIRE' in nombre_empresa:
                tickers_adaptados.append('BRK-B')
                continue
            if ticker_upper == 'FUTU' or 'FUTU ' in nombre_empresa:
                tickers_adaptados.append('FUTU')
                continue
            if ticker_upper == 'SPOT':
                tickers_adaptados.append('SPOT')
                continue
            if ticker_upper.startswith('JD') and 'JD' in nombre_empresa:
                tickers_adaptados.append('JD.L')
                continue
            if ticker_upper == 'SE' or ('SEA' in nombre_empresa and 'LTD' in nombre_empresa):
                tickers_adaptados.append('SE')
                continue
            if ticker_upper in ['BFB', 'BF.B', 'BF/B', 'BF B', 'BF-B', 'BF.A', 'BFA'] or 'BROWN FORMAN' in nombre_empresa:
                tickers_adaptados.append('BF-B')
                continue
            if ticker_upper in ['HEIA', 'HEI.A', 'HEI A', 'HEI/A', 'HEI-A'] or ('HEICO' in nombre_empresa and 'CLASS A' in nombre_empresa):
                tickers_adaptados.append('HEI-A')
                continue
            if ticker_upper in ['BP.', 'BP/', 'BP'] and ('BP' in nombre_empresa or 'BRITISH' in nombre_empresa):
                tickers_adaptados.append('BP.L')
                continue
            
            ticker_base = ticker_original.replace('.', '-').replace(' ', '-').replace('/', '-')
            ticker_base = ticker_base.rstrip('-') 
            
            bolsa = str(row['Exchange']).lower()
            pais = str(row['Location']).lower()
            ticker_final = ticker_base
            asignado = False
            
            bolsas_us = ['new york', 'nasdaq', 'nyse', 'nyq', 'nms', 'united states']
            excepciones_nordicas = ['stockholm', 'helsinki', 'copenhagen', 'nordic']
            
            if any(b in bolsa for b in bolsas_us):
                if 'euronext' not in bolsa and not any(ex in bolsa for ex in excepciones_nordicas):
                    ticker_final = ticker_base
                    asignado = True
            
            if not asignado:
                for mercado, sufijo in sufijos.items():
                    if mercado in bolsa:
                        ticker_final = f"{ticker_base}{sufijo}"
                        asignado = True
                        break
            
            if not asignado:
                for mercado, sufijo in sufijos.items():
                    if mercado in pais:
                        ticker_final = f"{ticker_base}{sufijo}"
                        break
            
            if ticker_final.endswith('.HK'):
                base_hk = ticker_final.replace('.HK', '')
                ticker_final = f"{base_hk.zfill(4)}.HK"
                        
            tickers_adaptados.append(ticker_final)
            
        df['Symbol_Yahoo'] = tickers_adaptados
        df = df.rename(columns={
            'Name': 'Security', 
            'Sector': 'GICS Sector',
            'Location': 'Nacionalidad',
            peso_col: 'Peso_Global'
        })
        return df[['Symbol_Yahoo', 'Security', 'GICS Sector', 'Nacionalidad', 'Peso_Global']]
    except Exception as e:
        st.error(f"Error procesando el archivo de BlackRock: {e}")
        return pd.DataFrame()

# MOTOR ANTIBLOQUEO: Lotes de 50 y float32 para ahorrar RAM
def descargar_por_lotes(tickers_list, period):
    diccionario_series = {}
    tamano_lote = 50
    
    for i in range(0, len(tickers_list), tamano_lote):
        lote = tickers_list[i:i+tamano_lote]
        try:
            data = yf.download(lote, period=period, auto_adjust=True, progress=False, threads=False)
            if data.empty: continue
            
            if isinstance(data.columns, pd.MultiIndex):
                df_close = data['Close'] if 'Close' in data.columns.levels[0] else data.xs('Close', axis=1, level=1)
            else:
                df_close = data[['Close']].rename(columns={'Close': lote[0]}) if len(lote) == 1 else data[['Close']]
            
            for col in df_close.columns:
                diccionario_series[col] = df_close[col].astype('float32')
        except Exception:
            pass
            
    if diccionario_series:
        df_final = pd.DataFrame(diccionario_series)
        df_final = df_final.loc[:, ~df_final.columns.duplicated()]
        return df_final
    return pd.DataFrame()

def descargar_precios_optimizados(tickers):
    if not tickers: return pd.DataFrame()
    hoy = date.today().strftime("%Y-%m-%d")
    archivo_cache = f"msci_precios_cache_3y_{hoy}.csv"
    
    if os.path.exists(archivo_cache):
        try: return pd.read_csv(archivo_cache, index_col=0, parse_dates=True)
        except Exception: pass 
            
    tickers_unicos = list(set(tickers))
    # Reducido a 3 años para mayor velocidad y menor consumo RAM
    df_final = descargar_por_lotes(tickers_unicos, "3y")
    
    if not df_final.empty:
        for f in os.listdir():
            if f.startswith("msci_precios_cache_") and f.endswith(".csv"):
                try: os.remove(f)
                except Exception: pass
        df_final.to_csv(archivo_cache)
    return df_final

@st.cache_data(ttl=120) 
def descargar_precios_tiempo_real(tickers):
    if not tickers: return pd.DataFrame()
    return descargar_por_lotes(list(set(tickers)), "5d")

# --- 4. INTERFAZ ---
df_msci = obtener_empresas_msci_world_v9()

if df_msci.empty:
    st.error("Error crítico: No se ha podido cargar el universo MSCI World.")
else:
    if st.session_state.page == 'main':
        col1, col_vacia, col2 = st.columns([2, 2, 1])
        with col1:
            st.subheader("Amplitud y Rendimiento por Sectores")
            opcion_dias = st.selectbox("Configurar Ventana de Análisis:", 
                                       ["5 días", "10 días", "21 días", "42 días", "63 días", "126 días", "252 días"], 
                                       index=1)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📊 Ver Componentes", use_container_width=True):
                st.session_state.page = 'components'
                st.rerun()
                
        dias_analisis = int(opcion_dias.split()[0])
        with st.spinner("Descargando historial 3 años (Bajo consumo RAM)..."):
            tickers_todos = df_msci['Symbol_Yahoo'].tolist()
            precios_largo = descargar_precios_optimizados(tickers_todos)
            precios_corto = descargar_precios_tiempo_real(tickers_todos)
            
            if not precios_largo.empty and not precios_corto.empty:
                precios_largo, precios_corto = precios_largo.ffill(), precios_corto.ffill()
                datos_amplitud = []
                for ticker in tickers_todos:
                    if ticker in precios_largo.columns and ticker in precios_corto.columns:
                        serie_l, serie_c = precios_largo[ticker].dropna(), precios_corto[ticker].dropna()
                        if len(serie_l) >= dias_analisis and not serie_c.empty:
                            p_v = float(serie_c.iloc[-1])
                            p_b = float(serie_l.iloc[-(dias_analisis + 1)]) if len(serie_l) > dias_analisis else float(serie_l.iloc[0])
                            v = serie_l.tail(dias_analisis).copy()
                            v.iloc[-1] = p_v
                            datos_amplitud.append({'Symbol_Yahoo': ticker, 'Max': 1 if p_v >= v.max() else 0, 
                                                   'Min': 1 if p_v <= v.min() else 0, 'Ret': ((p_v / p_b) - 1) * 100})
                            
                df_amp = pd.DataFrame(datos_amplitud)
                df_c = pd.merge(df_msci, df_amp, on='Symbol_Yahoo')
                
                resumen = []
                for sector, group in df_c.groupby('GICS Sector'):
                    tot = len(group)
                    dif = group['Max'].sum() - group['Min'].sum()
                    resumen.append({'Sector': sector, 'Peso (%)': group['Peso_Global'].sum(),
                                    f'Dif. Neta % ({opcion_dias})': (dif/tot)*100 if tot > 0 else 0,
                                    f'Rendimiento ({opcion_dias})': (group['Ret'] * group['Peso_Global']).sum() / group['Peso_Global'].sum()})
                
                st.dataframe(pd.DataFrame(resumen).sort_values('Peso (%)', ascending=False).style.format({
                    "Peso (%)": "{:.2f} %", f'Dif. Neta % ({opcion_dias})': "{:.2f} %", f'Rendimiento ({opcion_dias})': "{:.2f} %"
                }), use_container_width=True, hide_index=True, height=480)

        # --- BACKTESTING ---
        st.divider()
        col_bt1, col_bt2, _ = st.columns([1, 2, 1])
        with col_bt1:
            bt_dias = int(st.selectbox("Ventana de Backtest:", ["10 días", "21 días", "42 días", "63 días", "126 días", "252 días"]).split()[0])
        with col_bt2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⚙️ Ejecutar Backtest: Top 3 Sectores vs MSCI World (Últ. 250 días)"):
                st.session_state.show_bt = True
        
        if st.session_state.show_bt:
            with st.spinner("Simulando estrategia..."):
                fechas = precios_largo.index
                if len(fechas) > (250 + bt_dias):
                    resultados = []
                    for i in list(range(-251, -1, bt_dias)):
                        f_i, f_f = fechas[i], fechas[i+bt_dias] if (i+bt_dias) < 0 else fechas[-1]
                        v_p = precios_largo.iloc[i-bt_dias:i+1]
                        p_v = v_p.iloc[-1]
                        es_max, es_min = (p_v >= v_p.max()).astype(int), (p_v <= v_p.min()).astype(int)
                        df_bt = pd.merge(df_msci, pd.DataFrame({'Max': es_max, 'Min': es_min}), left_on='Symbol_Yahoo', right_index=True)
                        rk = []
                        for s, g in df_bt.groupby('GICS Sector'):
                            rk.append({'Sector': s, 'Dif': ((g['Max'].sum()-g['Min'].sum())/len(g))*100 if len(g)>0 else 0})
                        top_3 = pd.DataFrame(rk).sort_values('Dif', ascending=False).head(3)['Sector'].tolist()
                        ret_a = ((precios_largo.iloc[i+bt_dias if (i+bt_dias)<0 else -1] / precios_largo.iloc[i]) - 1) * 100
                        df_e = pd.merge(df_msci, pd.DataFrame({'Ret': ret_a}), left_on='Symbol_Yahoo', right_index=True)
                        r_msci = (df_e['Ret'] * df_e['Peso_Global']).sum() / df_e['Peso_Global'].sum()
                        df_t3 = df_e[df_e['GICS Sector'].isin(top_3)]
                        r_t3 = (df_t3['Ret'] * df_t3['Peso_Global']).sum() / df_t3['Peso_Global'].sum()
                        resultados.append({'Periodo': f"{f_i.strftime('%d/%m/%y')} - {f_f.strftime('%d/%m/%y')}", 'Top 3': ", ".join(top_3), 'Ret T3': r_t3, 'Ret MSCI': r_msci, 'Dif': r_t3 - r_msci})
                    
                    df_res = pd.DataFrame(resultados)
                    st.dataframe(df_res.style.format({'Ret T3': "{:.2f}%", 'Ret MSCI': "{:.2f}%", 'Dif': "{:.2f}%"}), use_container_width=True, hide_index=True)
                    p_t3, p_msci = ((1 + df_res['Ret T3']/100).prod()-1)*100, ((1 + df_res['Ret MSCI']/100).prod()-1)*100
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Acum. Estrategia", f"{p_t3:.2f}%")
                    c2.metric("Acum. MSCI World", f"{p_msci:.2f}%")
                    c3.metric("Alpha (1 Año)", f"{(p_t3 - p_msci):.2f}%")
                else: st.warning("Historial insuficiente.")

    elif st.session_state.page == 'components':
        if st.button("⬅️ Volver"):
            st.session_state.page = 'main'
            st.rerun()
        s = ["Todos"] + sorted(df_msci['GICS Sector'].unique())
        sec = st.selectbox("🎯 Sector:", s)
        emp = df_msci if sec == "Todos" else df_msci[df_msci['GICS Sector'] == sec]
        with st.spinner("Sincronizando..."):
            p_l, p_c = descargar_precios_optimizados(emp['Symbol_Yahoo'].tolist()), descargar_precios_tiempo_real(emp['Symbol_Yahoo'].tolist())
        if not p_l.empty and not p_c.empty:
            res = []
            p_l, p_c = p_l.ffill(), p_c.ffill()
            for t in emp['Symbol_Yahoo'].tolist():
                if t in p_l.columns and t in p_c.columns:
                    sl, sc = p_l[t].dropna(), p_c[t].dropna()
                    if len(sl) >= 51 and len(sc) >= 2:
                        pa = float(sc.iloc[-1])
                        res.append({"Ticker": t, "Security": emp[emp['Symbol_Yahoo']==t]['Security'].values[0], "Peso": emp[emp['Symbol_Yahoo']==t]['Peso_Global'].values[0], "Precio": pa,
                                    "1D": ((pa/float(sc.iloc[-2]))-1)*100, "5D": ((pa/float(sl.iloc[-6]))-1)*100, "30D": ((pa/float(sl.iloc[-31]))-1)*100, "50D": ((pa/float(sl.iloc[-51]))-1)*100})
            st.dataframe(pd.DataFrame(res).sort_values("Peso", ascending=False).style.format({"Peso": "{:.3f}%", "Precio": "$ {:.2f}", "1D": "{:.2f}%", "5D": "{:.2f}%", "30D": "{:.2f}%", "50D": "{:.2f}%"}), use_container_width=True, hide_index=True)
