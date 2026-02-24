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

def descargar_precios_optimizados(tickers):
    """Descarga el historial largo de 1 año y lo guarda en CSV para máxima velocidad"""
    if not tickers:
        return pd.DataFrame()
        
    hoy = date.today().strftime("%Y-%m-%d")
    archivo_cache = f"msci_precios_cache_{hoy}.csv"
    
    if os.path.exists(archivo_cache):
        try:
            return pd.read_csv(archivo_cache, index_col=0, parse_dates=True)
        except Exception:
            pass 
            
    tickers_unicos = list(set(tickers))
    data = yf.download(tickers_unicos, period="1y", auto_adjust=True, progress=False, threads=True)
    
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
                
        if not df_close.empty:
            for f in os.listdir():
                if f.startswith("msci_precios_cache_") and f.endswith(".csv"):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
            df_close.to_csv(archivo_cache)
            
        return df_close
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=120) 
def descargar_precios_tiempo_real(tickers):
    """Descarga ligera (5 días) en tiempo real con actualización cada 2 minutos"""
    if not tickers:
        return pd.DataFrame()
        
    tickers_unicos = list(set(tickers))
    data = yf.download(tickers_unicos, period="5d", auto_adjust=True, progress=False, threads=True)
    
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

# --- 4. NAVEGACIÓN Y RENDERIZADO DE PANTALLAS ---
df_msci = obtener_empresas_msci_world_v9()

if df_msci.empty:
    st.error("Error crítico: No se ha podido cargar el universo MSCI World.")
else:
    # --- PANTALLA PRINCIPAL ---
    if st.session_state.page == 'main':
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader("Resumen Sectorial MSCI World")
        with col2:
            if st.button("📊 Ver Componentes", use_container_width=True):
                st.session_state.page = 'components'
                st.rerun()
                
        with st.spinner("Actualizando datos en tiempo real y calculando osciladores..."):
            tickers_todos = df_msci['Symbol_Yahoo'].tolist()
            precios_largo = descargar_precios_optimizados(tickers_todos)
            precios_corto = descargar_precios_tiempo_real(tickers_todos)
            
            if not precios_largo.empty and not precios_corto.empty:
                precios_largo = precios_largo.ffill()
                precios_corto = precios_corto.ffill()
                
                # Matriz de retornos diarios de todo el año para el McClellan
                retornos_diarios = precios_largo.pct_change()
                
                datos_retornos = []
                for ticker in tickers_todos:
                    if ticker in precios_largo.columns and ticker in precios_corto.columns:
                        serie_larga = precios_largo[ticker].dropna()
                        serie_corta = precios_corto[ticker].dropna()
                        
                        if len(serie_larga) >= 252 and len(serie_corta) >= 2:
                            p_act = float(serie_corta.iloc[-1])
                            p_1d = float(serie_corta.iloc[-2])
                            p_1m = float(serie_larga.iloc[-22])
                            p_3m = float(serie_larga.iloc[-64])
                            p_1y = float(serie_larga.iloc[-252])
                            
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
                    # --- CÁLCULO OSCILADOR MCCLELLAN DEL SECTOR ---
                    tickers_del_sector = group['Symbol_Yahoo'].tolist()
                    tickers_validos_mcc = [t for t in tickers_del_sector if t in retornos_diarios.columns]
                    
                    if tickers_validos_mcc:
                        retornos_sector = retornos_diarios[tickers_validos_mcc]
                        avances = (retornos_sector > 0).sum(axis=1)
                        retrocesos = (retornos_sector < 0).sum(axis=1)
                        avances_netos = avances - retrocesos
                        
                        # EMAs de 19 y 39 días
                        ema19 = avances_netos.ewm(span=19, adjust=False).mean()
                        ema39 = avances_netos.ewm(span=39, adjust=False).mean()
                        
                        mcclellan = (ema19 - ema39).iloc[-1]
                    else:
                        mcclellan = 0.0
                    
                    resumen_sectores.append({
                        'Sector': sector,
                        'Peso (%)': group['Peso_Global'].sum(),
                        'McClellan Osc.': mcclellan,
                        '1 Día': promedio_ponderado(group, '1 Día'),
                        '1 Mes': promedio_ponderado(group, '1 Mes'),
                        '3 Meses': promedio_ponderado(group, '3 Meses'),
                        '1 Año': promedio_ponderado(group, '1 Año')
                    })
                    
                df_resumen = pd.DataFrame(resumen_sectores).sort_values(by='Peso (%)', ascending=False)
                
                # Visualización Principal enfocada solo en la tabla
                st.markdown("<br>", unsafe_allow_html=True)
                estilo_resumen = df_resumen.style.format({
                                                     "Peso (%)": "{:.2f} %",
                                                     "McClellan Osc.": "{:.2f}",
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
        
        with st.spinner(f"Sincronizando {len(tickers_sector)} activos en tiempo real..."):
            precios_largo = descargar_precios_optimizados(tickers_sector)
            precios_corto = descargar_precios_tiempo_real(tickers_sector)
        
        if not precios_largo.empty and not precios_corto.empty:
            resultados = []
            activos_fallidos = []
            
            precios_largo = precios_largo.ffill()
            precios_corto = precios_corto.ffill()
                
            for ticker in tickers_sector:
                if ticker not in precios_largo.columns or ticker not in precios_corto.columns:
                    activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict.get(ticker, ""), "País": nacionalidad_dict.get(ticker, ""), "Motivo": "Rechazado por Yahoo Finance"})
                    continue
                    
                serie_larga = precios_largo[ticker].dropna()
                serie_corta = precios_corto[ticker].dropna()
                
                if len(serie_larga) < 51 or len(serie_corta) < 2: 
                    activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict.get(ticker, ""), "País": nacionalidad_dict.get(ticker, ""), "Motivo": "Historial insuficiente"})
                    continue
                
                try:
                    p_act = float(serie_corta.iloc[-1])
                    p_1d = float(serie_corta.iloc[-2])
                    p_5d = float(serie_larga.iloc[-6]) if len(serie_larga) >= 6 else float(serie_larga.iloc[0])
                    p_10d = float(serie_larga.iloc[-11]) if len(serie_larga) >= 11 else float(serie_larga.iloc[0])
                    p_30d = float(serie_larga.iloc[-31]) if len(serie_larga) >= 31 else float(serie_larga.iloc[0])
                    p_50d = float(serie_larga.iloc[-51]) if len(serie_larga) >= 51 else float(serie_larga.iloc[0])
                    
                    resultados.append({
                        "Ticker": ticker,
                        "Empresa": nombres_dict[ticker],
                        "Nacionalidad": nacionalidad_dict[ticker],
                        "Sector": empresas_sector.loc[empresas_sector['Symbol_Yahoo'] == ticker, 'GICS Sector'].values[0],
                        "Peso Global": peso_dict[ticker],
                        "Precio Actual": p_act,
                        "1 Día": ((p_act / p_1d) - 1) * 100,
                        "5 Días": ((p_act / p_5d) - 1) * 100,
                        "10 Días": ((p_act / p_10d) - 1) * 100,
                        "30 Días": ((p_act / p_30d) - 1) * 100,
                        "50 Días": ((p_act / p_50d) - 1) * 100
                    })
                except Exception:
                    activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict.get(ticker, ""), "País": nacionalidad_dict.get(ticker, ""), "Motivo": "Error de cálculo interno"})
                    
            if resultados:
                df_resultados = pd.DataFrame(resultados)
                df_resultados = df_resultados.sort_values(by="Peso Global", ascending=False).reset_index(drop=True)
                df_resultados.insert(0, "#", range(1, len(df_resultados) + 1))
                
                st.markdown(f"### 📈 Rendimiento Global: **{sector_elegido}**")
                
                estilo_df = df_resultados.style.format({
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
