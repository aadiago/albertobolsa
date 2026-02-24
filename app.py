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
    if not tickers:
        return pd.DataFrame()
        
    hoy = date.today().strftime("%Y-%m-%d")
    archivo_cache = f"msci_precios_cache_5y_{hoy}.csv"
    
    if os.path.exists(archivo_cache):
        try:
            return pd.read_csv(archivo_cache, index_col=0, parse_dates=True)
        except Exception:
            pass 
            
    tickers_unicos = list(set(tickers))
    # threads=False previene bloqueos del servidor (RuntimeError) en Streamlit Cloud
    data = yf.download(tickers_unicos, period="5y", auto_adjust=True, progress=False, threads=False)
    
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
    if not tickers:
        return pd.DataFrame()
        
    tickers_unicos = list(set(tickers))
    # threads=False por la misma razón que el histórico
    data = yf.download(tickers_unicos, period="5d", auto_adjust=True, progress=False, threads=False)
    
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
        col1, col_vacia, col2 = st.columns([2, 2, 1])
        with col1:
            st.subheader("Amplitud y Rendimiento por Sectores")
            opcion_dias = st.selectbox(
                "Configurar Ventana de Análisis:",
                ["5 días", "10 días", "21 días", "42 días", "63 días", "126 días", "252 días"],
                index=1
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📊 Ver Componentes", use_container_width=True):
                st.session_state.page = 'components'
                st.rerun()
                
        dias_analisis = int(opcion_dias.split()[0])
                
        with st.spinner(f"Calculando amplitud y ganancias de {dias_analisis} días en tiempo real... esto puede tardar unos minutos la primera vez (descarga segura sin crasheo)."):
            tickers_todos = df_msci['Symbol_Yahoo'].tolist()
            precios_largo = descargar_precios_optimizados(tickers_todos)
            precios_corto = descargar_precios_tiempo_real(tickers_todos)
            
            if not precios_largo.empty and not precios_corto.empty:
                precios_largo = precios_largo.ffill()
                precios_corto = precios_corto.ffill()
                
                datos_amplitud = []
                for ticker in tickers_todos:
                    if ticker in precios_largo.columns and ticker in precios_corto.columns:
                        serie_larga = precios_largo[ticker].dropna()
                        serie_corta = precios_corto[ticker].dropna()
                        
                        if len(serie_larga) >= dias_analisis and not serie_corta.empty:
                            precio_vivo = float(serie_corta.iloc[-1])
                            
                            idx_base = -(dias_analisis + 1) if len(serie_larga) >= (dias_analisis + 1) else 0
                            precio_base = float(serie_larga.iloc[idx_base])
                            retorno_periodo = ((precio_vivo / precio_base) - 1) * 100
                            
                            ventana = serie_larga.tail(dias_analisis).copy()
                            ventana.iloc[-1] = precio_vivo 
                            
                            max_ventana = ventana.max()
                            min_ventana = ventana.min()
                            
                            es_max = 1 if precio_vivo >= max_ventana else 0
                            es_min = 1 if precio_vivo <= min_ventana else 0
                            
                            datos_amplitud.append({
                                'Symbol_Yahoo': ticker,
                                'Maximos': es_max,
                                'Minimos': es_min,
                                'Retorno': retorno_periodo
                            })
                            
                df_amplitud = pd.DataFrame(datos_amplitud)
                df_completo = pd.merge(df_msci, df_amplitud, on='Symbol_Yahoo')
                
                def promedio_ponderado(group, col):
                    if group['Peso_Global'].sum() == 0: return 0
                    return (group[col] * group['Peso_Global']).sum() / group['Peso_Global'].sum()
                
                resumen_sectores = []
                for sector, group in df_completo.groupby('GICS Sector'):
                    total_activos = len(group)
                    total_maximos = group['Maximos'].sum()
                    total_minimos = group['Minimos'].sum()
                    diferencia_neta = total_maximos - total_minimos
                    
                    dif_neta_pct = (diferencia_neta / total_activos) * 100 if total_activos > 0 else 0
                    retorno_sector = promedio_ponderado(group, 'Retorno')
                    
                    resumen_sectores.append({
                        'Sector': sector,
                        'Peso (%)': group['Peso_Global'].sum(),
                        f'Dif. Neta % ({opcion_dias})': dif_neta_pct,
                        f'Rendimiento ({opcion_dias})': retorno_sector
                    })
                    
                df_resumen = pd.DataFrame(resumen_sectores).sort_values(by='Peso (%)', ascending=False)
                
                st.markdown("<br>", unsafe_allow_html=True)
                estilo_resumen = df_resumen.style.format({
                                                     "Peso (%)": "{:.2f} %",
                                                     f'Dif. Neta % ({opcion_dias})': "{:.2f} %",
                                                     f'Rendimiento ({opcion_dias})': "{:.2f} %"
                                                 })
                st.dataframe(estilo_resumen, use_container_width=True, hide_index=True, height=480)
        
        # --- SECCIÓN DE BACKTESTING ---
        st.divider()
        col_bt1, col_bt2, col_bt3 = st.columns([1, 2, 1])
        with col_bt1:
            opcion_bt_dias = st.selectbox(
                "Ventana de Backtest:",
                ["10 días", "21 días", "42 días", "63 días", "126 días", "252 días"],
                index=0
            )
            bt_dias = int(opcion_bt_dias.split()[0])
            
        with col_bt2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⚙️ Ejecutar Backtest: Top 3 Sectores vs MSCI World (Últ. 250 días)", use_container_width=True):
                st.session_state.show_bt = True
                
        if st.session_state.show_bt:
            with st.spinner(f"Simulando estrategia histórica (Evaluación cada {bt_dias} días, últimos 250 días)..."):
                fechas = precios_largo.index
                
                if len(fechas) > (250 + bt_dias):
                    resultados_bt = []
                    # Índices de rebalanceo cada X días bursátiles (últimos 250 días)
                    indices_rebalanceo = list(range(-251, -1, bt_dias))
                    
                    for i in indices_rebalanceo:
                        fecha_inicio = fechas[i]
                        fecha_fin = fechas[i+bt_dias] if (i+bt_dias) < 0 else fechas[-1]
                        
                        inicio_ventana = i - bt_dias
                        if inicio_ventana < -len(precios_largo):
                            inicio_ventana = -len(precios_largo)
                            
                        ventana_precios = precios_largo.iloc[inicio_ventana:i+1]
                        
                        precio_vivo = ventana_precios.iloc[-1]
                        max_ventana = ventana_precios.max()
                        min_ventana = ventana_precios.min()
                        
                        es_max = (precio_vivo >= max_ventana).astype(int)
                        es_min = (precio_vivo <= min_ventana).astype(int)
                        
                        datos_amp = pd.DataFrame({'Maximos': es_max, 'Minimos': es_min})
                        df_bt = pd.merge(df_msci, datos_amp, left_on='Symbol_Yahoo', right_index=True)
                        
                        ranking = []
                        for sector, group in df_bt.groupby('GICS Sector'):
                            tot = len(group)
                            dif = group['Maximos'].sum() - group['Minimos'].sum()
                            pct = (dif / tot) * 100 if tot > 0 else 0
                            ranking.append({'Sector': sector, 'Dif': pct})
                            
                        ranking_df = pd.DataFrame(ranking).sort_values('Dif', ascending=False)
                        top_3 = ranking_df.head(3)['Sector'].tolist()
                        
                        precios_inicio = precios_largo.iloc[i]
                        precios_fin = precios_largo.iloc[i+bt_dias] if (i+bt_dias) < 0 else precios_largo.iloc[-1]
                        
                        retornos_activos = ((precios_fin / precios_inicio) - 1) * 100
                        df_ret = pd.DataFrame({'Retorno': retornos_activos})
                        df_eval = pd.merge(df_msci, df_ret, left_on='Symbol_Yahoo', right_index=True)
                        
                        peso_msci = df_eval['Peso_Global'].sum()
                        retorno_msci = (df_eval['Retorno'] * df_eval['Peso_Global']).sum() / peso_msci if peso_msci > 0 else 0
                        
                        df_top3 = df_eval[df_eval['GICS Sector'].isin(top_3)]
                        peso_top3 = df_top3['Peso_Global'].sum()
                        retorno_top3 = (df_top3['Retorno'] * df_top3['Peso_Global']).sum() / peso_top3 if peso_top3 > 0 else 0
                        
                        resultados_bt.append({
                            'Periodo': f"{fecha_inicio.strftime('%d/%m/%y')} - {fecha_fin.strftime('%d/%m/%y')}",
                            'Sectores Top 3': ", ".join(top_3),
                            'Retorno Top 3': retorno_top3,
                            'Retorno MSCI': retorno_msci,
                            'Diferencia': retorno_top3 - retorno_msci
                        })
                        
                    df_res_bt = pd.DataFrame(resultados_bt)
                    
                    st.markdown(f"### 📊 Resultados Simulación Anual (Ventana/Rebalanceo {bt_dias}d)")
                    estilo_bt = df_res_bt.style.format({
                        'Retorno Top 3': "{:.2f} %",
                        'Retorno MSCI': "{:.2f} %",
                        'Diferencia': "{:.2f} %"
                    })
                    st.dataframe(estilo_bt, use_container_width=True, hide_index=True)
                    
                    # Cálculo de rendimiento acumulado compuesto
                    prod_top3 = ((1 + df_res_bt['Retorno Top 3']/100).prod() - 1) * 100
                    prod_msci = ((1 + df_res_bt['Retorno MSCI']/100).prod() - 1) * 100
                    
                    col_r1, col_r2, col_r3 = st.columns(3)
                    col_r1.metric("Acumulado Estrategia Top 3", f"{prod_top3:.2f} %")
                    col_r2.metric("Acumulado MSCI World", f"{prod_msci:.2f} %")
                    col_r3.metric("Alpha Generado (1 Año)", f"{(prod_top3 - prod_msci):.2f} %")
                    
                else:
                    st.warning(f"Historial insuficiente. Se necesitan {250 + bt_dias} días bursátiles para el backtesting.")

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
        
        with st.spinner(f"Sincronizando {len(tickers_sector)} activos..."):
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
