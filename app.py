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

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:italic,wght@400;700&display=swap');
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }
    .main-title { font-size: 1.6rem; font-weight: bold; margin-top: -2rem; color: #1E1E1E; }
    .alberto-sofia { font-family: 'Playfair Display', serif; font-style: italic; font-size: 1rem; color: #4A4A4A; }
    </style>
""", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([1, 25])
with col_h1: st.markdown("<h1>🌍</h1>", unsafe_allow_html=True)
with col_h2: 
    st.markdown('<p class="main-title">PENGUIN MSCI WORLD TRACKER</p>', unsafe_allow_html=True)
    st.markdown('<p class="alberto-sofia">Sofía y Alberto 2026</p>', unsafe_allow_html=True)

st.divider()

# --- 2. MOTOR DE DATOS (OPTIMIZADO PARA RAM) ---
@st.cache_data(ttl=86400) 
def obtener_universo_msci():
    url = "https://www.ishares.com/us/products/239696/ishares-msci-world-etf/1467271812596.ajax?fileType=csv&fileName=URTH_holdings&dataType=fund"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        lineas = response.text.splitlines()
        h_idx = 0
        for i, l in enumerate(lineas):
            if "Ticker" in l and "Name" in l:
                h_idx = i
                break
        df = pd.read_csv(io.StringIO(response.text), skiprows=h_idx)
        df.columns = df.columns.str.strip()
        peso_col = 'Weight (%)' if 'Weight (%)' in df.columns else 'Weight'
        df = df.dropna(subset=['Ticker', 'Sector'])
        df = df[df['Asset Class'] == 'Equity']
        
        sufijos = {'london':'.L', 'tokyo':'.T', 'toronto':'.TO', 'amsterdam':'.AS', 'paris':'.PA', 
                   'xetra':'.DE', 'madrid':'.MC', 'milan':'.MI', 'sydney':'.AX', 'hong kong':'.HK'}
        
        tickers = []
        for _, row in df.iterrows():
            n, t = str(row['Name']).upper(), str(row['Ticker']).strip().upper()
            if 'CONSTELLATION SOFTWARE' in n: tickers.append('CSU.TO')
            elif 'CAPITALAND INTEGRATED' in n: tickers.append('M3T.F')
            elif 'BERKSHIRE' in n: tickers.append('BRK-B')
            else:
                tk = t.replace('.', '-').replace(' ', '-')
                ex = str(row['Exchange']).lower()
                for m, s in sufijos.items():
                    if m in ex: 
                        tk += s
                        break
                tickers.append(tk)
        df['Symbol_Yahoo'] = tickers
        return df.rename(columns={'Name':'Security','Sector':'GICS Sector','Location':'Nacionalidad', peso_col:'Peso_Global'})
    except: return pd.DataFrame()

def descargar_lotes(tickers_list, period):
    diccionario = {}
    tamano_lote = 50 
    for i in range(0, len(tickers_list), tamano_lote):
        lote = tickers_list[i:i+tamano_lote]
        try:
            data = yf.download(lote, period=period, auto_adjust=True, progress=False, threads=False)
            if not data.empty:
                close = data['Close'] if 'Close' in data.columns.levels[0] else data.xs('Close', axis=1, level=1) if isinstance(data.columns, pd.MultiIndex) else data[['Close']]
                for col in close.columns:
                    diccionario[col] = close[col].astype('float32')
        except: continue
    return pd.DataFrame(diccionario)

def get_precios_final(tickers):
    hoy = date.today().strftime("%Y-%m-%d")
    archivo = f"cache_3y_{hoy}.csv"
    if os.path.exists(archivo): 
        try: return pd.read_csv(archivo, index_col=0, parse_dates=True)
        except: pass
    df = descargar_lotes(list(set(tickers)), "3y")
    if not df.empty: df.to_csv(archivo)
    return df

@st.cache_data(ttl=120)
def get_tiempo_real(tickers):
    return descargar_lotes(list(set(tickers)), "5d")

# --- 3. LÓGICA DE PANTALLAS ---
df_msci = obtener_universo_msci()

if df_msci.empty:
    st.error("Error al cargar datos de iShares. Verifica la conexión.")
else:
    if st.session_state.page == 'main':
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.subheader("Amplitud y Rendimiento Sectorial")
            op = st.selectbox("Ventana de Análisis:", ["5 días", "10 días", "21 días", "42 días", "63 días", "126 días", "252 días"], index=1)
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📊 Ver Componentes", use_container_width=True):
                st.session_state.page = 'components'
                st.rerun()
        
        d = int(op.split()[0])
        with st.spinner("Sincronizando 3 años de historial (Modo Ahorro RAM)..."):
            p_l = get_precios_final(df_msci['Symbol_Yahoo'].tolist())
            p_rt = get_tiempo_real(df_msci['Symbol_Yahoo'].tolist())
            
            if not p_l.empty and not p_rt.empty:
                p_l, p_rt = p_l.ffill(), p_rt.ffill()
                res_amplitud = []
                for t in df_msci['Symbol_Yahoo'].tolist():
                    if t in p_l.columns and t in p_rt.columns:
                        s_l, s_rt = p_l[t].dropna(), p_rt[t].dropna()
                        if len(s_l) >= d and not s_rt.empty:
                            v_p = float(s_rt.iloc[-1])
                            v_b = float(s_l.iloc[-(d+1)]) if len(s_l) > d else float(s_l.iloc[0])
                            ventana = s_l.tail(d).copy()
                            res_amplitud.append({'Symbol_Yahoo':t, 'Max':1 if v_p >= ventana.max() else 0, 
                                                 'Min':1 if v_p <= ventana.min() else 0, 'Ret':((v_p/v_b)-1)*100})
                
                df_calc = pd.merge(df_msci, pd.DataFrame(res_amplitud), on='Symbol_Yahoo')
                tabla_main = []
                for sector, group in df_calc.groupby('GICS Sector'):
                    tot = len(group)
                    dif = group['Max'].sum() - group['Min'].sum()
                    ret_p = (group['Ret'] * group['Peso_Global']).sum() / group['Peso_Global'].sum()
                    tabla_main.append({'Sector': sector, 'Peso %': group['Peso_Global'].sum(), 
                                       f'Dif. Neta % ({op})': (dif/tot)*100, f'Ganancia % ({op})': ret_p})
                
                st.dataframe(pd.DataFrame(tabla_main).sort_values('Peso %', ascending=False).style.format("{:.2f}"), 
                             use_container_width=True, hide_index=True)

        # --- BACKTESTING ---
        st.divider()
        st.subheader("Backtesting: Estrategia de Fuerza Técnica")
        c_bt1, c_bt2 = st.columns([1, 2])
        with c_bt1:
            bt_d = int(st.selectbox("Ventana Backtest:", ["10 días", "21 días", "42 días", "63 días", "126 días", "252 días"]).split()[0])
        with c_bt2:
            st.markdown("<br>", unsafe_allow_html=True)
            run_bt = st.button("⚙️ Ejecutar Backtest 250 días")
        
        if run_bt:
            with st.spinner("Simulando últimos 250 días..."):
                fechas = p_l.index
                if len(fechas) > 260:
                    indices = list(range(-251, -1, bt_d))
                    bt_final = []
                    for i in indices:
                        f_i, f_f = fechas[i], fechas[i+bt_d] if (i+bt_d) < 0 else fechas[-1]
                        v_precios = p_l.iloc[i-bt_d:i+1]
                        p_ahora = v_precios.iloc[-1]
                        mx, mn = (p_ahora >= v_precios.max()).astype(int), (p_ahora >= v_precios.min()).astype(int)
                        df_b = pd.merge(df_msci, pd.DataFrame({'M':mx}), left_on='Symbol_Yahoo', right_index=True)
                        # Top 3 sectores por diferencia neta simplificada para el backtest
                        ranking = df_b.groupby('GICS Sector')['M'].mean().sort_values(ascending=False).head(3).index.tolist()
                        ret_all = ((p_l.iloc[i+bt_d if i+bt_d < 0 else -1] / p_l.iloc[i]) - 1) * 100
                        df_ret = pd.merge(df_msci, pd.DataFrame({'R':ret_all}), left_on='Symbol_Yahoo', right_index=True)
                        r_msci = (df_ret['R'] * df_ret['Peso_Global']).sum() / df_ret['Peso_Global'].sum()
                        r_t3 = (df_ret[df_ret['GICS Sector'].isin(ranking)]['R'] * df_ret[df_ret['GICS Sector'].isin(ranking)]['Peso_Global']).sum() / df_ret[df_ret['GICS Sector'].isin(ranking)]['Peso_Global'].sum()
                        bt_final.append({'Periodo':f"{f_i.strftime('%d/%m')} - {f_f.strftime('%d/%m')}", 'Ret T3':r_t3, 'Ret MSCI':r_msci})
                    
                    df_res = pd.DataFrame(bt_final)
                    st.dataframe(df_res.style.format("{:.2f}"), use_container_width=True, hide_index=True)
                    p_t3, p_msci = ((1+df_res['Ret T3']/100).prod()-1)*100, ((1+df_res['Ret MSCI']/100).prod()-1)*100
                    st.info(f"Estrategia: {p_t3:.2f}% | MSCI World: {p_msci:.2f}% | Alpha: {(p_t3-p_msci):.2f}%")
                else: st.warning("Datos históricos insuficientes para el backtest.")

    elif st.session_state.page == 'components':
        if st.button("⬅️ Volver al Resumen"):
            st.session_state.page = 'main'
            st.rerun()
        s_list = ["Todos"] + sorted(df_msci['GICS Sector'].unique())
        s_sel = st.selectbox("🎯 Filtrar por Sector:", s_list)
        df_sec = df_msci if s_sel == "Todos" else df_msci[df_msci['GICS Sector'] == s_sel]
        with st.spinner("Cargando componentes..."):
            p_hist = descargar_precios_optimizados(df_sec['Symbol_Yahoo'].tolist())
            p_v = get_tiempo_real(df_sec['Symbol_Yahoo'].tolist())
            if not p_hist.empty and not p_v.empty:
                c_res = []
                for t in df_sec['Symbol_Yahoo'].tolist():
                    if t in p_hist.columns and t in p_v.columns:
                        sh, sv = p_hist[t].dropna(), p_v[t].dropna()
                        if len(sh) > 50 and not sv.empty:
                            pa = float(sv.iloc[-1])
                            c_res.append({'Ticker':t, 'Security':df_sec[df_sec['Symbol_Yahoo']==t]['Security'].values[0], 'Peso':df_sec[df_sec['Symbol_Yahoo']==t]['Peso_Global'].values[0],
                                          'Precio':pa, '1D':((pa/sv.iloc[-2])-1)*100 if len(sv)>1 else 0, '1M':((pa/sh.iloc[-22])-1)*100, '1Y':((pa/sh.iloc[-252])-1)*100})
                st.dataframe(pd.DataFrame(c_res).sort_values('Peso', ascending=False).style.format({'Peso':'{:.3f}%','Precio':'$ {:.2f}','1D':'{:.2f}%','1M':'{:.2f}%','1Y':'{:.2f}%'}), use_container_width=True, hide_index=True)
