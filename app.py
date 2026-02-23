import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.interpolate import make_interp_spline
import base64
import os
from PIL import Image
import io

# --- 1. PARÁMETROS POR DEFECTO DEL PROGRAMA ---
DEF_RS_SMOOTH = 42
DEF_PERIODO_X = 126
DEF_PERIODO_Y = 42
DEF_TAIL_LENGTH = 5  # Número de puntos en la cola (cada uno representa 5 días)

# --- 2. CONFIGURACIÓN VISUAL ---
st.set_page_config(layout="wide", page_title="PENGUIN PORTFOLIO PRO", page_icon="🐧")

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

# --- 3. CABECERA COMPACTA ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

col_h1, col_h2 = st.columns([1, 25])
with col_h1:
    p_path = os.path.join(BASE_DIR, "pinguino.png")
    if os.path.exists(p_path): st.image(p_path, width=32)
with col_h2: 
    st.markdown('<p class="main-title">PENGUIN PORTFOLIO</p>', unsafe_allow_html=True)
    st.markdown('<p class="alberto-sofia">Sofía y Alberto 2026</p>', unsafe_allow_html=True)

# --- 4. CONSTANTES Y ASSETS ---
BENCHMARK = "MWEQ.DE"
MY_PORTFOLIO = ["LCUJ.DE", "B41J.DE", "XDWI.DE", "XDW0.DE", "XDWM.DE", "LBRA.DE"]
PIRANHA_ETFS = ["SXR8.DE", "XDEW.DE", "XDEE.DE", "IBCF.DE"]

ASSETS = [
    ("AGGREGATE HDG", "EME", "XEMB.DE", "BONDS.PNG", "EME.PNG"),
    ("AGGREGATE HDG", "WRL", "DBZB.DE", "BONDS.PNG", "WRL.PNG"),
    ("CASH", "EUR", "YCSH.DE", "CASH.PNG", "EUR.PNG"),
    ("CORPORATE BONDS", "WRL", "D5BG.DE", "BONDS.PNG", "WRL.PNG"),
    ("CORPORATE HIGH YIELD BONDS", "WRL", "XHYA.DE", "BONDS.PNG", "WRL.PNG"),
    ("EUROZONE GOVERNMENT BOND 1-3", "EUR", "DBXP.DE", "BONDS.PNG", "EUR.PNG"),
    ("EUROZONE GOVERNMENT BOND 10-15", "EUR", "LYQ6.DE", "BONDS.PNG", "EUR.PNG"),
    ("EUROZONE GOVERNMENT BOND 15+", "EUR", "LYXF.DE", "BONDS.PNG", "EUR.PNG"),
    ("EUROZONE GOVERNMENT BOND 3-5", "EUR", "LYQ3.DE", "BONDS.PNG", "EUR.PNG"),
    ("EUROZONE GOVERNMENT BOND 7-10", "EUR", "LYXD.DE", "BONDS.PNG", "EUR.PNG"),
    ("JAPAN AGGREGATE HDG", "JPN", "CEB2.DE", "BONDS.PNG", "JAPAN.PNG"),
    ("TIPS", "EUR", "XEIN.DE", "BONDS.PNG", "EUR.PNG"),
    ("TIPS HDG", "USA", "IBC5.DE", "BONDS.PNG", "USA.PNG"),
    ("TREASURY AGGREGATE", "USA", "VAGT.DE", "BONDS.PNG", "USA.PNG"),
    ("AGRICULTURE", "COM", "AIGA.MI", "FARM.PNG", "COM.PNG"),
    ("BITCOIN", "COM", "IB1T.DE", "CRYPTO.PNG", "COM.PNG"),
    ("BLOOMBERG COMMODITY", "COM", "CMOE.MI", "COM.PNG", "COM.PNG"),
    ("GOLD", "COM", "8PSG.DE", "GOLD.PNG", "COM.PNG"),
    ("GOLD HDG", "COM", "XGDE.DE", "GOLD.PNG", "COM.PNG"),
    ("STRATEGIC METALS", "COM", "WENH.DE", "METALS.PNG", "COM.PNG"),
    ("HIGH YIELD", "EME", "EUNY.DE", "HIGH YIELD.PNG", "EME.PNG"),
    ("HIGH YIELD", "EUR", "XZDZ.DE", "HIGH YIELD.PNG", "EUR.PNG"),
    ("HIGH YIELD", "USA", "XDND.DE", "HIGH YIELD.PNG", "USA.PNG"),
    ("HIGH YIELD", "WRL", "XZDW.DE", "HIGH YIELD.PNG", "WRL.PNG"),
    ("LOW VOLATILITY", "EME", "EUNZ.DE", "VOLATILITY.PNG", "EME.PNG"),
    ("LOW VOLATILITY", "EUR", "ZPRL.DE", "VOLATILITY.PNG", "EUR.PNG"),
    ("LOW VOLATILITY", "USA", "SPY1.DE", "VOLATILITY.PNG", "USA.PNG"),
    ("LOW VOLATILITY", "WRL", "CSY9.DE", "VOLATILITY.PNG", "WRL.PNG"),
    ("MOMENTUM", "EME", "EGEE.DE", "MOMENTUM.PNG", "EME.PNG"),
    ("MOMENTUM", "EUR", "CEMR.DE", "MOMENTUM.PNG", "EUR.PNG"),
    ("MOMENTUM", "USA", "QDVA.DE", "MOMENTUM.PNG", "USA.PNG"),
    ("MOMENTUM", "WRL", "IS3R.DE", "MOMENTUM.PNG", "WRL.PNG"),
    ("QUALITY", "EME", "JREM.DE", "QUALITY.PNG", "EME.PNG"),
    ("QUALITY", "EUR", "CEMQ.DE", "QUALITY.PNG", "EUR.PNG"),
    ("QUALITY", "USA", "QDVB.DE", "QUALITY.PNG", "USA.PNG"),
    ("QUALITY", "WRL", "IS3Q.DE", "QUALITY.PNG", "WRL.PNG"),
    ("SIZE", "EME", "SPYX.DE", "SIZE.PNG", "EME.PNG"),
    ("SIZE", "EUR", "ZPRX.DE", "SIZE.PNG", "EUR.PNG"),
    ("SIZE", "USA", "ZPRV.DE", "SIZE.PNG", "USA.PNG"),
    ("SIZE", "WRL", "IUSN.DE", "SIZE.PNG", "WRL.PNG"),
    ("SIZE", "JPN", "IUS4.DE", "SIZE.PNG", "JAPAN.PNG"),
    ("VALUE", "EME", "5MVL.DE", "VALUE.PNG", "EME.PNG"),
    ("VALUE", "EUR", "CEMS.DE", "VALUE.PNG", "EUR.PNG"),
    ("VALUE", "USA", "QDVI.DE", "VALUE.PNG", "USA.PNG"),
    ("VALUE", "WRL", "IS3S.DE", "VALUE.PNG", "WRL.PNG"),
    ("AEX 25", "EUR", "IAEA.AS", "INDICEP.PNG", "EUR.PNG"),
    ("CAC 40", "EUR", "GC40.DE", "INDICEP.PNG", "EUR.PNG"),
    ("CSI 300", "CHN", "XCHA.DE", "INDICEP.PNG", "CHINA.PNG"),
    ("DAX 40", "EUR", "EXS1.DE", "INDICEP.PNG", "EUR.PNG"),
    ("DOW JONES INDUSTRIAL", "USA", "SXRU.DE", "INDICEP.PNG", "USA.PNG"),
    ("FTSE 100", "EUR", "CEB4.DE", "INDICEP.PNG", "EUR.PNG"),
    ("FTSE KOREA", "EME", "FLXK.DE", "INDICEP.PNG", "EME.PNG"),
    ("FTSE MIB", "EUR", "SXRY.DE", "INDICEP.PNG", "EUR.PNG"),
    ("IBEX 35", "EUR", "AMES.DE", "INDICEP.PNG", "EUR.PNG"),
    ("MSCI ARABIA SAUDITA", "EME", "IUSS.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI AUSTRALIA", "WRL", "IBC6.DE", "INDICEP.PNG", "WRL.PNG"),
    ("MSCI BRASIL", "EME", "LBRA.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI CANADA", "WRL", "SXR2.DE", "INDICEP.PNG", "WRL.PNG"),
    ("MSCI CHINA", "CHN", "ICGA.DE", "INDICEP.PNG", "CHINA.PNG"),
    ("MSCI HONG KONG", "CHN", "HKDE.AS", "INDICEP.PNG", "CHINA.PNG"),
    ("MSCI INDIA", "EME", "QDV5.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI INDONESIA", "EME", "H4Z7.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI JAPAN HDG", "JPN", "IBCG.DE", "INDICEP.PNG", "JAPAN.PNG"),
    ("MSCI JAPAN", "JPN", "LCUJ.DE", "INDICEP.PNG", "JAPAN.PNG"),
    ("MSCI MALAYSIA", "EME", "XCS3.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI MEXICO", "EME", "D5BI.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI PHILIPPINES", "EME", "XPQP.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI POLAND", "EUR", "IBCJ.DE", "INDICEP.PNG", "EUR.PNG"),
    ("MSCI SINGAPORE", "EME", "XBAS.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI SUDÁFRICA", "EME", "IBC4.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI SWITZERLAND CHF", "EUR", "SW2CHB.SW", "INDICEP.PNG", "EUR.PNG"),
    ("MSCI TAIWAN", "EME", "DBX5.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI THAILANDIA", "EME", "XCS4.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI TURQUÍA", "EUR", "LTUR.DE", "INDICEP.PNG", "EUR.PNG"),
    ("NASDAQ 100", "USA", "SXRV.DE", "INDICEP.PNG", "USA.PNG"),
    ("NASDAQ 100 HDG", "USA", "NQSE.DE", "INDICEP.PNG", "USA.PNG"),
    ("NIKKEI 225", "JPN", "XDJP.DE", "INDICEP.PNG", "JAPAN.PNG"),
    ("RUSSELL 2000", "USA", "ZPRR.DE", "INDICEP.PNG", "USA.PNG"),
    ("S&P 500", "USA", "SXR8.DE", "INDICEP.PNG", "USA.PNG"),
    ("S&P 500 EW", "USA", "XDEW.DE", "INDICEP.PNG", "USA.PNG"),
    ("S&P 500 EW HDG", "USA", "XDEE.DE", "INDICEP.PNG", "USA.PNG"),
    ("S&P 500 HDG", "USA", "IBCF.DE", "INDICEP.PNG", "USA.PNG"),
    ("S&P 600", "USA", "SMLK.DE", "INDICEP.PNG", "USA.PNG"),
    ("TOPIX", "WRL", "TPXE.PA", "INDICEP.PNG", "WRL.PNG"),
    ("ACWI", "ALL", "VWCE.DE", "INDICES.PNG", "ALL.PNG"),
    ("ACWI HDG", "ALL", "SPP1.DE", "INDICES.PNG", "ALL.PNG"),
    ("MSCI AFRICA", "EME", "XMKA.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI EMERGING ASIA", "EME", "AMEA.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI EMERGING EX-CHINA", "EME", "EMXC.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI EMERGING MARKETS", "EME", "IS3N.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI LATINOAMERICA", "EME", "DBX3.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI NORDIC", "EUR", "XDN0.DE", "INDICES.PNG", "EUR.PNG"),
    ("MSCI PACIFIC-EX JAPAN", "EME", "18MM.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI WORLD", "WRL", "EUNL.DE", "INDICES.PNG", "WRL.PNG"),
    ("MSCI WORLD EW", "WRL", "MWEQ.DE", "INDICES.PNG", "WRL.PNG"),
    ("MSCI WORLD EX-USA", "WRL", "EXUS.DE", "INDICES.PNG", "WRL.PNG"),
    ("MSCI WORLD HDG", "WRL", "IBCH.DE", "INDICES.PNG", "WRL.PNG"),
    ("STOXX 50", "EUR", "SXRT.DE", "INDICES.PNG", "EUR.PNG"),
    ("STOXX 600", "EUR", "LYP6.DE", "INDICES.PNG", "EUR.PNG"),
    ("COMMUNICATION SERVICES", "EUR", "SPYT.DE", "COMMUNICATIONS.PNG", "EUR.PNG"),
    ("COMMUNICATION SERVICES", "USA", "IU5C.DE", "COMMUNICATIONS.PNG", "USA.PNG"),
    ("COMMUNICATION SERVICES", "WRL", "TELW.PA", "COMMUNICATIONS.PNG", "WRL.PNG"),
    ("CONSUMER DISCRETIONARY", "EUR", "SPYR.DE", "DISCRETIONARY.PNG", "EUR.PNG"),
    ("CONSUMER DISCRETIONARY", "USA", "QDVK.DE", "DISCRETIONARY.PNG", "USA.PNG"),
    ("CONSUMER DISCRETIONARY", "WRL", "WELJ.DE", "DISCRETIONARY.PNG", "WRL.PNG"),
    ("CONSUMER STAPLES", "EUR", "SPYC.DE", "STAPLES.PNG", "EUR.PNG"),
    ("CONSUMER STAPLES", "USA", "2B7D.DE", "STAPLES.PNG", "USA.PNG"),
    ("CONSUMER STAPLES", "WRL", "WELW.DE", "STAPLES.PNG", "WRL.PNG"),
    ("ENERGY", "EUR", "SPYN.DE", "ENERGY.PNG", "EUR.PNG"),
    ("ENERGY", "USA", "QDVF.DE", "ENERGY.PNG", "USA.PNG"),
    ("ENERGY", "WRL", "XDW0.DE", "ENERGY.PNG", "WRL.PNG"),
    ("FINANCIALS", "EUR", "SPYZ.DE", "FINANCIALS.PNG", "EUR.PNG"),
    ("FINANCIALS", "USA", "QDVH.DE", "FINANCIALS.PNG", "USA.PNG"),
    ("FINANCIALS", "WRL", "WF1E.DE", "FINANCIALS.PNG", "WRL.PNG"),
    ("HEALTH CARE", "EUR", "SPYH.DE", "HEALTH CARE.PNG", "EUR.PNG"),
    ("HEALTH CARE", "USA", "QDVG.DE", "HEALTH CARE.PNG", "USA.PNG"),
    ("HEALTH CARE", "WRL", "WELS.DE", "HEALTH CARE.PNG", "WRL.PNG"),
    ("INDUSTRIALS", "EUR", "ESIN.DE", "INDUSTRIALS.PNG", "EUR.PNG"),
    ("INDUSTRIALS", "USA", "2B7C.DE", "INDUSTRIALS.PNG", "USA.PNG"),
    ("INDUSTRIALS", "WRL", "XDWI.DE", "INDUSTRIALS.PNG", "WRL.PNG"),
    ("MATERIALS", "EUR", "SPYP.DE", "MATERIALS.PNG", "EUR.PNG"),
    ("MATERIALS", "USA", "2B7B.DE", "MATERIALS.PNG", "USA.PNG"),
    ("MATERIALS", "WRL", "XDWM.DE", "MATERIALS.PNG", "WRL.PNG"),
    ("REAL ESTATE", "EUR", "IPRE.DE", "REIT.PNG", "EUR.PNG"),
    ("REAL ESTATE", "USA", "IQQ7.DE", "REIT.PNG", "USA.PNG"),
    ("REAL ESTATE", "WRL", "SPY2.DE", "REIT.PNG", "WRL.PNG"),
    ("TECHNOLOGY", "CHN", "CBUK.DE", "TECHNOLOGY.PNG", "CHINA.PNG"),
    ("TECHNOLOGY", "EME", "EMQQ.DE", "TECHNOLOGY.PNG", "EME.PNG"),
    ("TECHNOLOGY", "EUR", "SPYK.DE", "TECHNOLOGY.PNG", "EUR.PNG"),
    ("TECHNOLOGY", "USA", "QDVE.DE", "TECHNOLOGY.PNG", "USA.PNG"),
    ("TECHNOLOGY", "WRL", "WELU.DE", "TECHNOLOGY.PNG", "WRL.PNG"),
    ("TECHNOLOGY", "EME", "H41X.DE", "TECHNOLOGY.PNG", "INDIA.PNG"),
    ("UTILITIES", "EUR", "SPYU.DE", "UTILITIES.PNG", "EUR.PNG"),
    ("UTILITIES", "USA", "2B7A.DE", "UTILITIES.PNG", "USA.PNG"),
    ("UTILITIES", "WRL", "WELD.DE", "UTILITIES.PNG", "WRL.PNG"),
    ("AGEING POPULATION", "ALL", "2B77.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("AGRIBUSINESS", "ALL", "ISAG.MI", "THEMATIC.PNG", "ALL.PNG"),
    ("AI ADOPTERS & APPLICATIONS", "ALL", "AIAA.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("AI INFRASTRUCTURE", "ALL", "AIFS.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("ARK INNOVATION", "WRL", "ARXK.DE", "THEMATIC.PNG", "WRL.PNG"),
    ("CLEAN ENERGY TRANSITION", "ALL", "Q8Y0.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("CLOUD COMPUTING", "USA", "SKYE.AS", "THEMATIC.PNG", "USA.PNG"),
    ("CYBER SECURITY", "WRL", "USPY.DE", "THEMATIC.PNG", "WRL.PNG"),
    ("DATA CENTER", "ALL", "V9N.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("DIGITAL ENTERTAINMENT & EDUCATION", "ALL", "CBUN.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("DIGITAL PAYMENTS", "ALL", "DPGA.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("ELECTRIC VEHICLES & DRIVING TECH", "ALL", "IEVD.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("EUROPE DEFENSE", "EUR", "EDFS.DE", "THEMATIC.PNG", "EUR.PNG"),
    ("EUROPEAN INFRASTRUCTURE", "EUR", "B41J.DE", "THEMATIC.PNG", "EUR.PNG"),
    ("GLOBAL BLOCKCHAIN", "ALL", "BNXG.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("GLOBAL DEFENSE", "ALL", "4MMR.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("GLOBAL HYDROGEN", "ALL", "AMEE.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("GLOBAL INFRASTRUCTURE", "ALL", "CBUX.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("GLOBAL INVESTORS TRAVEL", "ALL", "7RIP.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("GLOBAL LUXURY", "ALL", "GLUX.MI", "THEMATIC.PNG", "ALL.PNG"),
    ("GLOBAL TIMBER & FORESTRY", "ALL", "IUSB.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("HEALTHCARE INNOVATION", "ALL", "2B78.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("LITHIUM & BATTERY TECHNOLOGIES", "ALL", "LI7U.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("MEDICAL ROBOTICS", "ALL", "CIB0.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("METAVERSE", "ALL", "CBUV.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("MORNINGSTAR GLOBAL WIDE MOAT", "ALL", "VVGM.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("MORNINGSTAR US WIDE MOAT", "USA", "GMVM.DE", "THEMATIC.PNG", "USA.PNG"),
    ("MSCI MILENNIALS", "ALL", "GENY.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("MSCI WATER", "WRL", "WATC.MI", "THEMATIC.PNG", "WRL.PNG"),
    ("NASDAQ NEXT GENERATION 100", "USA", "EQQJ.DE", "THEMATIC.PNG", "USA.PNG"),
    ("NASDAQ US BIOTECHNOLOGY", "USA", "2B70.DE", "THEMATIC.PNG", "USA.PNG"),
    ("OIL SERVICES", "WRL", "V0IH.DE", "THEMATIC.PNG", "WRL.PNG"),
    ("QUANTUM COMPUTING", "ALL", "QUTM.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("RARE EARTH & STRATEGIC METALS", "ALL", "VVMX.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("ROBOTICS & AI", "WRL", "GOAI.DE", "THEMATIC.PNG", "WRL.PNG"),
    ("S&P 500 TOP 20", "USA", "IS20.DE", "THEMATIC.PNG", "USA.PNG"),
    ("SEMICONDUCTOR", "ALL", "VVSM.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("SOLAR ENERGY", "ALL", "S0LR.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("SPACE INNOVATORS", "ALL", "JEDI.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("SUSTAINABLE FUTURE OF FOOD", "ALL", "RIZF.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("URANIUM & NUCLEAR TECHNOLOGIES", "ALL", "NUKL.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("VIDEO GAMING & ESPORTS", "ALL", "ESP0.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("WEB 3.0", "WRL", "M37R.DE", "THEMATIC.PNG", "WRL.PNG")
]

# --- 5. SERVICIOS ---
_img_cache = {}
TRANSPARENT_1X1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def get_img_b64(filename):
    if not filename: return TRANSPARENT_1X1
    if filename in _img_cache: return _img_cache[filename]
    
    actual_filename = filename
    try:
        for f in os.listdir(BASE_DIR):
            if f.lower() == filename.lower():
                actual_filename = f
                break
    except Exception:
        pass
        
    path = os.path.join(BASE_DIR, actual_filename)
    if not os.path.exists(path):
        return TRANSPARENT_1X1 
        
    try:
        with Image.open(path) as img:
            img = img.convert("RGBA")
            
            if filename.lower() == "eme.png":
                img.thumbnail((24, 24), Image.Resampling.LANCZOS)
                bg = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
                offset = ((32 - img.width) // 2, (32 - img.height) // 2)
                bg.paste(img, offset)
                img = bg
            else:
                img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
            _img_cache[filename] = b64
            return b64
    except:
        return TRANSPARENT_1X1

def get_rrg_pts(ticker_df, bench_df, rs_smooth, periodo_x, periodo_y):
    rs = (ticker_df / bench_df) * 100
    rs_sm = rs.ewm(span=rs_smooth, adjust=False).mean()
    m_l, s_l = rs_sm.rolling(periodo_x).mean(), rs_sm.rolling(periodo_x).std()
    rs_ratio = ((rs_sm - m_l) / s_l.replace(0, 1)) * 10 + 100
    rs_mom_raw = rs_sm.pct_change(periods=periodo_y) * 100
    m_s, s_s = rs_mom_raw.rolling(periodo_y).mean(), rs_mom_raw.rolling(periodo_y).std()
    rs_mom = ((rs_mom_raw - m_s) / s_s.replace(0, 1)) * 10 + 100
    return rs_ratio, rs_mom

@st.cache_data(ttl=600)
def load_data_robust(tickers):
    all_data = []
    chunk_size = 45
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        data = yf.download(chunk, period="2y", auto_adjust=True, progress=False)['Close']
        all_data.append(data)
    return pd.concat(all_data, axis=1)

# --- 6. PESTAÑAS Y FLUJO PRINCIPAL ---
tab_app, tab_params, tab_manual = st.tabs(["📊 PORTFOLIO", "⚙️ PARÁMETROS", "📖 MANUAL TÉCNICO"])

with tab_params:
    st.markdown("### Configuración del Motor RRG")
    with st.form("parametros_form"):
        st.subheader("Sensibilidad del Modelo")
        col1, col2, col3 = st.columns(3)
        with col1: RS_SMOOTH = st.number_input("Suavizado RS (Periodos)", min_value=1, max_value=100, value=DEF_RS_SMOOTH, step=1)
        with col2: PERIODO_X = st.number_input("Periodo Eje X (STR)", min_value=10, max_value=252, value=DEF_PERIODO_X, step=5)
        with col3: PERIODO_Y = st.number_input("Periodo Eje Y (MOM)", min_value=5, max_value=100, value=DEF_PERIODO_Y, step=1)

        st.subheader("Gráfico")
        TAIL_LENGTH = st.number_input("Puntos de la cola (Saltos de 5 días)", min_value=3, max_value=20, value=DEF_TAIL_LENGTH, step=1)

        submit_button = st.form_submit_button("Actualizar Parámetros", use_container_width=True)

with tab_app:
    t_list = list(set([a[2] for a in ASSETS] + [BENCHMARK]))

    with st.spinner("SINCRONIZANDO PORTFOLIO (178 ACTIVOS)..."):
        raw_prices = load_data_robust(t_list)

    if not raw_prices.empty:
        bench_p = raw_prices[BENCHMARK]
        res_raw, rrg_hist = [], {}

        for name, reg, tick, isec, ireg in ASSETS:
            if tick not in raw_prices.columns: continue
            
            r_ser, m_ser = get_rrg_pts(raw_prices[tick], bench_p, RS_SMOOTH, PERIODO_X, PERIODO_Y)
            
            if r_ser.isna().all() or len(r_ser) < 30: continue

            pts = []
            for d in range(0, TAIL_LENGTH * 5, 5):
                idx = -(d + 1)
                if abs(idx) <= len(r_ser):
                    pts.append((float(r_ser.iloc[idx]), float(m_ser.iloc[idx])))

            if not pts: continue

            # Distancia euclídea del eje (0,0) al último punto de la cola (posición actual)
            str_val = pts[0][0] - 100
            mom_val = pts[0][1] - 100
            score_dist = np.sqrt(str_val**2 + mom_val**2)

            ret1d = ((raw_prices[tick].iloc[-1] / raw_prices[tick].iloc[-2]) - 1) * 100
            ret3m = ((raw_prices[tick].iloc[-1] / raw_prices[tick].iloc[-63]) - 1) * 100 if len(raw_prices[tick]) >= 63 else 0

            # Determinar fase para ordenar e icono
            if str_val >= 0 and mom_val >= 0:
                pos_str = "🟢 Leading"
                sort_order = 1
            elif str_val < 0 and mom_val >= 0:
                pos_str = "🔵 Improving"
                sort_order = 2
            elif str_val >= 0 and mom_val < 0:
                pos_str = "🟡 Weakening"
                sort_order = 3
            else:
                pos_str = "🔴 Lagging"
                sort_order = 4

            res_raw.append({
                "tick": tick, "name": name, "reg": reg, "isec": isec, "ireg": ireg,
                "score": score_dist, "str": str_val, "mom": mom_val,
                "r1d": ret1d, "r3m": ret3m, "pos_str": pos_str, "sort_order": sort_order
            })
            rrg_hist[tick] = pts

        final_rows = []
        for r in res_raw:
            p_ic = "pinguino.png" if r['tick'] in MY_PORTFOLIO else "PIRANHA.png" if r['tick'] in PIRANHA_ETFS else None

            final_rows.append({
                "Ver": (r['tick'] in MY_PORTFOLIO), 
                "Sort_Order": r['sort_order'],
                "Img_S": get_img_b64(r['isec']), 
                "Img_R": get_img_b64(r['ireg']),
                "Img_P": get_img_b64(p_ic),
                "Ticker": r['tick'], "Nombre": r['name'], "Score": round(r['score'], 2),
                "STR": round(r['str'], 2), "MOM": round(r['mom'], 2),
                "% Hoy": round(r['r1d'], 2), "% 3M": round(r['r3m'], 2),
                "POS": r['pos_str']
            })

        # Ordenar: Primero por categoría (Leading > Improving > Weakening > Lagging), luego por Score (descendente)
        df = pd.DataFrame(final_rows).sort_values(by=["Sort_Order", "Score"], ascending=[True, False]).reset_index(drop=True)
        df.insert(1, "#", range(1, len(df) + 1))

        conf = {
            "Ver": st.column_config.CheckboxColumn("Ver"), 
            "Img_S": st.column_config.ImageColumn("Sec", width="small"),
            "Img_R": st.column_config.ImageColumn("Reg", width="small"), 
            "Img_P": st.column_config.ImageColumn("👤", width="small"),
            "Nombre": st.column_config.TextColumn("Nombre", width=280),
            "% Hoy": st.column_config.NumberColumn("% Hoy", format="%.2f%%"),
            "% 3M": st.column_config.NumberColumn("% 3M", format="%.2f%%"),
        }
        
        v_cols = ["Ver", "#", "Img_S", "Img_R", "Img_P", "Ticker", "Nombre", "Score", "% Hoy", "% 3M", "STR", "MOM", "POS"]
        
        edit_df = st.data_editor(df, hide_index=True, column_order=v_cols, column_config=conf,
                                 disabled=[c for c in v_cols if c != "Ver"], height=550)

        plot_t = edit_df[edit_df["Ver"] == True]["Ticker"].tolist()
        st.divider()
        if plot_t:
            fig, ax = plt.subplots(figsize=(10, 8))
            all_x, all_y = [], []
            for t in plot_t:
                pts_raw = rrg_hist.get(t, [])
                xs = np.array([p[0] - 100 for p in pts_raw][::-1])
                ys = np.array([p[1] - 100 for p in pts_raw][::-1])
                all_x.extend(xs); all_y.extend(ys)

                dot_color = None
                
                if len(xs) >= 3:
                    tr = np.arange(len(xs))
                    td = np.linspace(0, len(xs) - 1, 100)
                    line = ax.plot(make_interp_spline(tr, xs, k=2)(td), make_interp_spline(tr, ys, k=2)(td), lw=1.5, alpha=0.7)[0]
                    dot_color = line.get_color()

                if dot_color:
                    ax.scatter(xs[:-1], ys[:-1], s=25, color=dot_color, alpha=0.4)
                    ax.scatter(xs[-1], ys[-1], s=160, color=dot_color, edgecolors='white', linewidth=1.5, zorder=5)
                else:
                    sc = ax.scatter(xs[:-1], ys[:-1], s=25, alpha=0.4)
                    dot_color = sc.get_facecolors()[0]
                    ax.scatter(xs[-1], ys[-1], s=160, color=dot_color, edgecolors='white', linewidth=1.5, zorder=5)
                    
                ax.text(xs[-1], ys[-1], f"  {t}", fontsize=9, fontweight='bold', va='center')

            ax.axhline(0, c='#CCCCCC', lw=1, zorder=1)
            ax.axvline(0, c='#CCCCCC', lw=1, zorder=1)
            
            limit = max([abs(val) for val in all_x + all_y] + [10]) * 1.3
            ax.set_xlim(-limit, limit); ax.set_ylim(-limit, limit)
            
            ax.add_patch(Rectangle((0, 0), limit, limit, color='green', alpha=0.04))
            ax.add_patch(Rectangle((-limit, 0), limit, limit, color='blue', alpha=0.04))
            ax.add_patch(Rectangle((-limit, -limit), limit, limit, color='red', alpha=0.04))
            ax.add_patch(Rectangle((0, -limit), limit, limit, color='yellow', alpha=0.04))

            st.pyplot(fig)

with tab_manual:
    manual_texto = r"""
    ## MANUAL TÉCNICO: MOTOR DE CÁLCULO PENGUIN PORTFOLIO PRO
    
    ### 1. Obtención de Datos Base
    El proceso arranca descargando los precios de cierre ajustados (`Close`) de los últimos 2 años para todos los activos de la lista y para el índice de referencia o *benchmark* (en este caso, `MWEQ.DE`, el MSCI World Equal Weight).
    
    ---
    
    ### 2. El Corazón del Sistema: Coordenadas RRG
    
    Para saber si un activo está liderando o rezagado respecto al mundo, no miramos su precio aislado, sino su comportamiento relativo usando la metodología de los *Relative Rotation Graphs* (RRG). Generamos dos coordenadas: **Fuerza (X)** y **Momentum (Y)**.
    
    * **Paso A: Fuerza Relativa Básica (RS)**
        Se divide el precio del activo entre el precio del benchmark.
        $$RS=\left(\frac{Precio_{Activo}}{Precio_{Benchmark}}\right)\times 100$$
        
    * **Paso B: Suavizado**
        Para evitar el "ruido" diario, se aplica una Media Móvil Exponencial (EMA) de **__RS_SMOOTH__ periodos** a la serie $RS$, obteniendo el $RS_{sm}$.
    
    * **Paso C: Coordenada X (JdK RS-Ratio / STR)**
        Mide la tendencia a largo plazo del activo frente al benchmark. Se normaliza el $RS_{sm}$ usando su media ($\mu$) y desviación estándar ($\sigma$) de los **últimos __PERIODO_X__ periodos**. Se centra en 100.
        $$X_{RRG}=\left(\frac{RS_{sm}-\mu_{__PERIODO_X__}}{\sigma_{__PERIODO_X__}}\right)\times 10+100$$
    
    * **Paso D: Coordenada Y (JdK RS-Momentum / MOM)**
        Mide la velocidad a la que cambia la fuerza relativa (la inercia a corto plazo). Se calcula la tasa de cambio porcentual a **__PERIODO_Y__ periodos** del $RS_{sm}$, y se vuelve a normalizar estadísticamente (media y desviación a **__PERIODO_Y__ días**).
        $$Y_{RRG}=\left(\frac{\Delta\%RS_{sm}-\mu_{__PERIODO_Y__}}{\sigma_{__PERIODO_Y__}}\right)\times 10+100$$
    
    ---
    
    ### 3. Asignación de Cuadrantes (POS)
    Dependiendo de dónde caigan las coordenadas X e Y (restando 100 para centrar el eje en el origen 0,0), el activo se clasifica en una de las cuatro fases del ciclo:
    * 🟢 **Leading (Líder):** $X \ge 0$ y $Y \ge 0$ (Fuerte y ganando inercia).
    * 🔵 **Improving (Mejorando):** $X < 0$ y $Y \ge 0$ (Débil pero ganando inercia).
    * 🟡 **Weakening (Debilitándose):** $X \ge 0$ y $Y < 0$ (Fuerte pero perdiendo inercia).
    * 🔴 **Lagging (Rezagado):** $X < 0$ y $Y < 0$ (Débil y perdiendo inercia).
    
    ---
    
    ### 4. Puntuación Definitiva (Score)
    El algoritmo valora de forma positiva la magnitud de la rotación. Para ello, el programa calcula el *Score* basado estrictamente en la **distancia euclídea** desde el eje de coordenadas $(0,0)$ hasta la posición del activo en el momento actual (el punto más reciente de la "cola").
    
    $$Score=\sqrt{X^2+Y^2}$$
    
    Cuanto mayor es la distancia respecto al origen, mayor es la fuerza del movimiento (ya sea liderando o rezagándose pronunciadamente). El algoritmo ordena la tabla final mostrando en primer lugar a los *Leading* con mayor amplitud, seguidos de los *Improving*, los *Weakening* y finalmente los *Lagging*.
    """
    
    manual_texto = manual_texto.replace("__RS_SMOOTH__", str(RS_SMOOTH))
    manual_texto = manual_texto.replace("__PERIODO_X__", str(PERIODO_X))
    manual_texto = manual_texto.replace("__PERIODO_Y__", str(PERIODO_Y))
    
    st.markdown(manual_texto)
