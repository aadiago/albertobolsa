import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import io

# --- 1. CONFIGURACIÓN VISUAL Y ESTADOS ---
st.set_page_config(layout="wide", page_title="MSCI WORLD TRACKER PRO", page_icon="🌍")

if 'page' not in st.session_state:
    st.session_state.page = 'main'

# Parámetros de Análisis (Aplicados por defecto)
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
            
            # --- EXCEPCIONES DIRECTAS ---
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
            
            # --- LIMPIEZA ESTÁNDAR ---
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

@st.cache_data(ttl=3600) 
def descargar_precios_v9(tickers):
    if not tickers:
        return pd.DataFrame()
        
    tickers_unicos = list(set(tickers))
    data = yf.download(tickers_unicos, period="1y", auto_adjust=True, progress=False, threads=False)
    
    if data.empty:
        return pd.DataFrame()
        
    try:
        if isinstance(data.columns, pd.MultiIndex):
            if 'Close' in data.columns.levels[0]:
                df_close = data['Close']
            elif 'Close' in data.columns.levels[1]:
                df_close = data.xs('Close', axis=1, level=1)
            else:
                return pd.DataFrame()
        else:
            if 'Close' in data.columns:
                if len(tickers_unicos) == 1:
                    df_close = data[['Close']].rename(columns={'Close': tickers_unicos[0]})
                else:
                    df_close = data[['Close']]
            else:
                return pd.DataFrame()
                
        return df_close
    except Exception:
        return pd.DataFrame()

def dar_color(val):
    if isinstance(val, (int, float)):
        color = '#d4edda' if val > 0 else '#f8d7da' if val < 0 else 'white'
        return f'background-color: {color}; color: #155724 if val > 0 else #721c24'
    return ''

# --- 4. NAVEGACIÓN Y RENDERIZADO DE PANTALLAS ---
df_msci = obtener_empresas_msci_world_v9()

if df_msci.empty:
    st.error("Error crítico: No se ha podido cargar el universo MSCI World. Verifica tu conexión a internet o los servidores de iShares.")
else:
    # --- PANTALLA PRINCIPAL ---
    if st.session_state.page == 'main':
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader("Resumen Sectorial MSCI World")
        with col2:
            if st.button("📊 Componentes", use_container_width=True):
                st.session_state.page = 'components'
                st.rerun()
                
        with st.spinner("Calculando ponderaciones y rendimiento sectorial (1 año)..."):
            # Preparar gráfico de barras nativo de Streamlit
            sector_weights = df_msci.groupby('GICS Sector')['Peso_Global'].sum().sort_values(ascending=False)
            
            # Preparar rendimientos por sector
            tickers_todos = df_msci['Symbol_Yahoo'].tolist()
            precios_todos = descargar_precios_v9(tickers_todos)
            
            if not precios_todos.empty:
                precios_todos = precios_todos.ffill()
                datos_retornos = []
                
                for ticker in tickers_todos:
                    if ticker in precios_todos.columns:
                        serie = precios_todos[ticker].dropna()
                        if len(serie) >= 2:
                            p_act = float(serie.iloc[-1])
                            p_1d = float(serie.iloc[-2])
                            p_1m = float(serie.iloc[-22]) if len(serie) >= 22 else float(serie.iloc[0])
                            p_3m = float(serie.iloc[-64]) if len(serie) >= 64 else float(serie.iloc[0])
                            p_1y = float(serie.iloc[-252]) if len(serie) >= 252 else float(serie.iloc[0])
                            
                            datos_retornos.append({
                                'Symbol_Yahoo': ticker,
                                '1 Día': ((p_act / p_1d) - 1) * 100,
                                '1 Mes': ((p_act / p_1m) - 1) * 100,
                                '3 Meses': ((p_act / p_3m) - 1) * 100,
                                '1 Año': ((p_act / p_1y) - 1) * 100
                            })
                            
                df_retornos = pd.DataFrame(datos_retornos)
                df_completo = pd.merge(df_msci, df_retornos, on='Symbol_Yahoo')
                
                def promedio_ponderado(group, col):
                    if group['Peso_Global'].sum() == 0: return 0
                    return (group[col] * group['Peso_Global']).sum() / group['Peso_Global'].sum()
                
                resumen_sectores = []
                for sector, group in df_completo.groupby('GICS Sector'):
                    resumen_sectores.append({
                        'Sector': sector,
                        'Peso (%)': group['Peso_Global'].sum(),
                        '1 Día': promedio_ponderado(group, '1 Día'),
                        '1 Mes': promedio_ponderado(group, '1 Mes'),
                        '3 Meses': promedio_ponderado(group, '3 Meses'),
                        '1 Año': promedio_ponderado(group, '1 Año')
                    })
                    
                df_resumen = pd.DataFrame(resumen_sectores).sort_values(by='Peso (%)', ascending=False)
                
                # Visualización Principal
                col_chart, col_table = st.columns([1, 1.5])
                with col_chart:
                    st.markdown("##### Distribución de Sectores (%)")
                    st.bar_chart(sector_weights)
                with col_table:
                    st.markdown("<br>", unsafe_allow_html=True)
                    estilo_resumen = df_resumen.style.map(dar_color, subset=['1 Día', '1 Mes', '3 Meses', '1 Año']) \
                                                     .format({
                                                         "Peso (%)": "{:.2f} %",
                                                         "1 Día": "{:.2f} %",
                                                         "1 Mes": "{:.2f} %",
                                                         "3 Meses": "{:.2f} %",
                                                         "1 Año": "{:.2f} %"
                                                     })
                    st.dataframe(estilo_resumen, use_container_width=True, hide_index=True, height=450)

    # --- PANTALLA SECUNDARIA (COMPONENTES) ---
    elif st.session_state.page == 'components':
        if st.button("⬅️ Volver al Resumen Principal"):
            st.session_state.page = 'main'
            st.rerun()
            
        st.divider()
        sectores = ["Todos los Sectores"] + sorted(df_msci['GICS Sector'].unique())
        
        col_sel, col_empty = st.columns([1, 3])
        with col_sel:
            sector_elegido = st.selectbox("🎯 Selecciona un Sector Global (MSCI World):", sectores)
        
        if sector_elegido == "Todos los Sectores":
            empresas_sector = df_msci
        else:
            empresas_sector = df_msci[df_msci['GICS Sector'] == sector_elegido]
            
        tickers_sector = empresas_sector['Symbol_Yahoo'].tolist()
        
        nombres_dict = dict(zip(empresas_sector['Symbol_Yahoo'], empresas_sector['Security']))
        nacionalidad_dict = dict(zip(empresas_sector['Symbol_Yahoo'], empresas_sector['Nacionalidad']))
        peso_dict = dict(zip(empresas_sector['Symbol_Yahoo'], empresas_sector['Peso_Global']))
        
        with st.spinner(f"Sincronizando {len(tickers_sector)} activos globales de forma segura..."):
            precios = descargar_precios_v9(tickers_sector)
        
        if not precios.empty:
            resultados = []
            activos_fallidos = []
            
            precios = precios.ffill()
            if isinstance(precios, pd.Series):
                precios = precios.to_frame(name=tickers_sector[0])
                
            for ticker in tickers_sector:
                if ticker not in precios.columns:
                    activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict.get(ticker, ""), "País": nacionalidad_dict.get(ticker, ""), "Motivo": "Rechazado por Yahoo Finance"})
                    continue
                    
                serie = precios[ticker].dropna()
                
                if len(serie) < 51: 
                    activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict.get(ticker, ""), "País": nacionalidad_dict.get(ticker, ""), "Motivo": "Historial insuficiente (< 50 días)"})
                    continue
                    
                precio_actual = float(serie.iloc[-1])
                
                try:
                    ret_1d = ((precio_actual / float(serie.iloc[-2])) - 1) * 100
                    ret_5d = ((precio_actual / float(serie.iloc[-6])) - 1) * 100
                    ret_10d = ((precio_actual / float(serie.iloc[-11])) - 1) * 100
                    ret_30d = ((precio_actual / float(serie.iloc[-31])) - 1) * 100
                    ret_50d = ((precio_actual / float(serie.iloc[-51])) - 1) * 100
                    
                    resultados.append({
                        "Ticker": ticker,
                        "Empresa": nombres_dict[ticker],
                        "Nacionalidad": nacionalidad_dict[ticker],
                        "Sector": empresas_sector.loc[empresas_sector['Symbol_Yahoo'] == ticker, 'GICS Sector'].values[0],
                        "Peso Global": peso_dict[ticker],
                        "Precio Actual": precio_actual,
                        "1 Día": ret_1d,
                        "5 Días": ret_5d,
                        "10 Días": ret_10d,
                        "30 Días": ret_30d,
                        "50 Días": ret_50d
                    })
                except Exception:
                    activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict.get(ticker, ""), "País": nacionalidad_dict.get(ticker, ""), "Motivo": "Error de cálculo interno"})
                    
            if resultados:
                df_resultados = pd.DataFrame(resultados)
                df_resultados = df_resultados.sort_values(by="Peso Global", ascending=False).reset_index(drop=True)
                df_resultados.insert(0, "#", range(1, len(df_resultados) + 1))
                
                st.markdown(f"### 📈 Rendimiento Global: **{sector_elegido}**")
                
                estilo_df = df_resultados.style.map(dar_color, subset=['1 Día', '5 Días', '10 Días', '30 Días', '50 Días']) \
                                               .format({
                                                   "Peso Global": "{:.3f} %",
                                                   "Precio Actual": "$ {:.2f}",
                                                   "1 Día": "{:.2f} %",
                                                   "5 Días": "{:.2f} %",
                                                   "10 Días": "{:.2f} %",
                                                   "30 Días": "{:.2f} %",
                                                   "50 Días": "{:.2f} %"
                                               })
                
                st.dataframe(estilo_df, use_container_width=True, hide_index=True, height=600)
            
            if activos_fallidos:
                st.divider()
                st.markdown(f"### ⚠️ Activos no cargados ({len(activos_fallidos)})")
                
                df_fallos = pd.DataFrame(activos_fallidos)
                st.dataframe(df_fallos, use_container_width=True, hide_index=True)
