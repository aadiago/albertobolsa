import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import io

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(layout="wide", page_title="MSCI WORLD TRACKER PRO", page_icon="🌍")

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
@st.cache_data(ttl=86400) # Cachear 1 día
def obtener_empresas_msci_world():
    url = "https://www.ishares.com/us/products/239696/ishares-msci-world-etf/1467271812596.ajax?fileType=csv&fileName=URTH_holdings&dataType=fund"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        # Búsqueda dinámica de la cabecera
        lineas = response.text.splitlines()
        header_idx = 0
        for i, linea in enumerate(lineas):
            if "Ticker" in linea and "Name" in linea:
                header_idx = i
                break
                
        df = pd.read_csv(io.StringIO(response.text), skiprows=header_idx)
        df = df.dropna(subset=['Ticker', 'Sector'])
        df = df[df['Asset Class'] == 'Equity']
        
        # Traductor de Bolsas a Nomenclatura Yahoo Finance
        sufijos = {
            'London': '.L',
            'Tokyo': '.T',
            'Toronto': '.TO',
            'Euronext Amsterdam': '.AS',
            'Euronext Paris': '.PA',
            'Xetra': '.DE',
            'SIX Swiss': '.SW',
            'Madrid': '.MC',
            'Borsa Italiana': '.MI',
            'Sydney': '.AX',
            'Copenhagen': '.CO',
            'Stockholm': '.ST',
            'Oslo': '.OL',
            'Helsinki': '.HE',
            'Hong Kong': '.HK',
            'Singapore': '.SI',
            'Vienna': '.VI',
            'Tel Aviv': '.TA',
            'New Zealand': '.NZ',
            'Dublin': '.IR'
        }
        
        tickers_adaptados = []
        for _, row in df.iterrows():
            # Limpieza exhaustiva del ticker (puntos, espacios y barras a guiones)
            ticker_base = str(row['Ticker']).strip().replace('.', '-').replace(' ', '-').replace('/', '-')
            bolsa = str(row['Exchange'])
            ticker_final = ticker_base
            
            for mercado, sufijo in sufijos.items():
                if mercado in bolsa:
                    ticker_final = f"{ticker_base}{sufijo}"
                    break
            tickers_adaptados.append(ticker_final)
            
        df['Symbol_Yahoo'] = tickers_adaptados
        
        # Renombrar para mantener compatibilidad
        df = df.rename(columns={
            'Name': 'Security', 
            'Sector': 'GICS Sector',
            'Location': 'Nacionalidad',
            'Weight (%)': 'Peso_Global'
        })
        
        return df[['Symbol_Yahoo', 'Security', 'GICS Sector', 'Nacionalidad', 'Peso_Global']]
    except Exception as e:
        st.error(f"Error procesando el archivo de BlackRock: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600) # Cachear precios 1 hora
def descargar_precios(tickers):
    data = yf.download(tickers, period="4mo", auto_adjust=True, progress=False)
    if 'Close' in data:
        return data['Close']
    return data

# --- 4. LÓGICA DE INTERFAZ Y CÁLCULO ---
df_msci = obtener_empresas_msci_world()

if not df_msci.empty:
    sectores = sorted(df_msci['GICS Sector'].unique())
    
    col_sel, col_empty = st.columns([1, 3])
    with col_sel:
        sector_elegido = st.selectbox("🎯 Selecciona un Sector Global (MSCI World):", sectores)
    
    empresas_sector = df_msci[df_msci['GICS Sector'] == sector_elegido]
    tickers_sector = empresas_sector['Symbol_Yahoo'].tolist()
    
    # Diccionarios de acceso rápido
    nombres_dict = dict(zip(empresas_sector['Symbol_Yahoo'], empresas_sector['Security']))
    nacionalidad_dict = dict(zip(empresas_sector['Symbol_Yahoo'], empresas_sector['Nacionalidad']))
    peso_dict = dict(zip(empresas_sector['Symbol_Yahoo'], empresas_sector['Peso_Global']))
    
    with st.spinner(f"Sincronizando {len(tickers_sector)} activos globales de {sector_elegido}..."):
        precios = descargar_precios(tickers_sector)
    
    if not precios.empty:
        resultados = []
        activos_fallidos = []
        
        precios = precios.ffill()
        if isinstance(precios, pd.Series):
            precios = precios.to_frame(name=tickers_sector[0])
            
        for ticker in tickers_sector:
            if ticker not in precios.columns:
                activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict[ticker], "Motivo": "No encontrado en Yahoo Finance"})
                continue
                
            serie = precios[ticker].dropna()
            
            if len(serie) < 51: 
                activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict[ticker], "Motivo": "Historial insuficiente (< 50 días)"})
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
                    "Peso Global": peso_dict[ticker],
                    "Precio Actual": precio_actual,
                    "1 Día": ret_1d,
                    "5 Días": ret_5d,
                    "10 Días": ret_10d,
                    "30 Días": ret_30d,
                    "50 Días": ret_50d
                })
            except Exception:
                activos_fallidos.append({"Ticker": ticker, "Empresa": nombres_dict[ticker], "Motivo": "Error de cálculo"})
                
        # --- 5. VISUALIZACIÓN DE RESULTADOS ---
        if resultados:
            df_resultados = pd.DataFrame(resultados)
            # Ordenamos por el peso en el índice para ver los gigantes primero
            df_resultados = df_resultados.sort_values(by="Peso Global", ascending=False).reset_index(drop=True)
            df_resultados.insert(0, "#", range(1, len(df_resultados) + 1))
            
            st.markdown(f"### 📈 Rendimiento Global: **{sector_elegido}**")
            
            column_config = {
                "#": st.column_config.NumberColumn("#", width="small"),
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Empresa": st.column_config.TextColumn("Empresa", width="medium"),
                "Nacionalidad": st.column_config.TextColumn("País", width="small"),
                "Peso Global": st.column_config.NumberColumn("Peso (%)", format="%.3f %%"),
                "Precio Actual": st.column_config.NumberColumn("Cierre", format="%.2f"),
                "1 Día": st.column_config.NumberColumn("1 Día", format="%.2f %%"),
                "5 Días": st.column_config.NumberColumn("5 Días", format="%.2f %%"),
                "10 Días": st.column_config.NumberColumn("10 Días", format="%.2f %%"),
                "30 Días": st.column_config.NumberColumn("30 Días", format="%.2f %%"),
                "50 Días": st.column_config.NumberColumn("50 Días", format="%.2f %%"),
            }
            
            st.dataframe(df_resultados, use_container_width=True, hide_index=True, column_config=column_config, height=600)
        
        # --- 6. REPORTE DE ACTIVOS FALLIDOS ---
        if activos_fallidos:
            st.divider()
            st.markdown(f"### ⚠️ Activos no cargados ({len(activos_fallidos)})")
            
            df_fallos = pd.DataFrame(activos_fallidos)
            st.dataframe(df_fallos, use_container_width=True, hide_index=True)
else:
    st.error("Error crítico: No se ha podido cargar el universo MSCI World.")
