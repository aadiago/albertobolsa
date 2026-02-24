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

# --- 3. MOTOR DE EXTRACCIÓN DE DATOS (BLACKROCK CSV) ---
@st.cache_data(ttl=86400) # Cachear la lista por 1 día
def obtener_empresas_msci_world():
    url = "https://www.ishares.com/us/products/239696/ishares-msci-world-etf/1467271812596.ajax?fileType=csv&fileName=URTH_holdings&dataType=fund"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        # BlackRock suele poner 9 líneas de metadatos antes de la tabla
        df = pd.read_csv(io.StringIO(response.text), skiprows=9)
        
        # Limpieza básica
        df = df.dropna(subset=['Ticker', 'Sector'])
        df = df[df['Asset Class'] == 'Equity']
        
        # Adaptación de columnas para mantener la lógica anterior
        df = df.rename(columns={'Ticker': 'Symbol', 'Name': 'Security', 'Sector': 'GICS Sector'})
        
        # Limpieza de Tickers para Yahoo Finance (Reemplazar puntos por guiones, ej. BRK.B -> BRK-B)
        df['Symbol'] = df['Symbol'].astype(str).str.replace('.', '-', regex=False)
        
        return df[['Symbol', 'Security', 'GICS Sector']]
    except Exception as e:
        st.error(f"Error de conexión con iShares: {e}")
        return pd.DataFrame(columns=['Symbol', 'Security', 'GICS Sector'])

@st.cache_data(ttl=3600) # Cachear precios por 1 hora
def descargar_precios(tickers):
    data = yf.download(tickers, period="4mo", auto_adjust=True, progress=False)['Close']
    return data

# --- 4. LÓGICA DE INTERFAZ Y CÁLCULO ---
df_msci = obtener_empresas_msci_world()

if df_msci.empty:
    st.warning("No se pudieron cargar los datos del MSCI World. Inténtalo de nuevo más tarde.")
else:
    sectores = sorted(df_msci['GICS Sector'].unique())
    
    col_sel, col_empty = st.columns([1, 3])
    with col_sel:
        sector_elegido = st.selectbox("🎯 Selecciona un Sector global:", sectores)
    
    empresas_sector = df_msci[df_msci['GICS Sector'] == sector_elegido]
    tickers_sector = empresas_sector['Symbol'].tolist()
    nombres_dict = dict(zip(empresas_sector['Symbol'], empresas_sector['Security']))
    
    with st.spinner(f"Sincronizando {len(tickers_sector)} empresas globales de {sector_elegido}... (Las acciones no estadounidenses podrían no cargar sin su sufijo de país)"):
        precios = descargar_precios(tickers_sector)
    
    if not precios.empty:
        resultados = []
        precios = precios.ffill()
        
        # yfinance devuelve un DataFrame distinto si es 1 ticker vs múltiples
        if isinstance(precios, pd.Series):
            precios = precios.to_frame(name=tickers_sector[0])
            
        for ticker in tickers_sector:
            if ticker not in precios.columns:
                continue
                
            serie = precios[ticker].dropna()
            if len(serie) < 51: 
                continue
                
            precio_actual = float(serie.iloc[-1])
            
            # Cálculo de retornos (días hábiles)
            ret_1d = ((precio_actual / float(serie.iloc[-2])) - 1) * 100
            ret_5d = ((precio_actual / float(serie.iloc[-6])) - 1) * 100
            ret_10d = ((precio_actual / float(serie.iloc[-11])) - 1) * 100
            ret_30d = ((precio_actual / float(serie.iloc[-31])) - 1) * 100
            ret_50d = ((precio_actual / float(serie.iloc[-51])) - 1) * 100
            
            resultados.append({
                "Ticker": ticker,
                "Empresa": nombres_dict[ticker],
                "Precio Actual": precio_actual,
                "1 Día": ret_1d,
                "5 Días": ret_5d,
                "10 Días": ret_10d,
                "30 Días": ret_30d,
                "50 Días": ret_50d
            })
            
        if resultados:
            df_resultados = pd.DataFrame(resultados)
            df_resultados = df_resultados.sort_values(by="5 Días", ascending=False).reset_index(drop=True)
            df_resultados.insert(0, "#", range(1, len(df_resultados) + 1))
            
            st.markdown(f"### 🌍 Rendimiento Global: **{sector_elegido}**")
            
            column_config = {
                "#": st.column_config.NumberColumn("#", width="small"),
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Empresa": st.column_config.TextColumn("Empresa", width="medium"),
                "Precio Actual": st.column_config.NumberColumn("Cierre", format="%.2f"),
                "1 Día": st.column_config.NumberColumn("1 Día", format="%.2f %%"),
                "5 Días": st.column_config.NumberColumn("5 Días", format="%.2f %%"),
                "10 Días": st.column_config.NumberColumn("10 Días", format="%.2f %%"),
                "30 Días": st.column_config.NumberColumn("30 Días", format="%.2f %%"),
                "50 Días": st.column_config.NumberColumn("50 Días", format="%.2f %%"),
            }
            
            st.dataframe(
                df_resultados,
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                height=600
            )
            
            faltantes = len(tickers_sector) - len(resultados)
            if faltantes > 0:
                st.info(f"💡 **Aviso de Tickers Internacionales:** {faltantes} empresas no se han podido calcular. Esto ocurre porque el CSV de BlackRock usa tickers locales (ej. 'SAN' para Banco Santander) pero Yahoo Finance requiere un sufijo de mercado (ej. 'SAN.MC' para España). Las empresas de EE. UU. cargarán sin problema.")
        else:
            st.warning("No se pudieron calcular los retornos para este sector (posiblemente por falta de compatibilidad de los tickers con Yahoo Finance).")
