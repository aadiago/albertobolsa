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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="PENGUIN PORTFOLIO", page_icon="🐧")

# CSS: Forzamos al navegador a renderizar las imágenes de las celdas
st.markdown("""
    <style>
    div[data-testid="stDataFrame"] div[role="columnheader"] { justify-content: center !important; text-align: center !important; }
    div[data-testid="stDataFrame"] div[role="gridcell"] { justify-content: center !important; text-align: center !important; display: flex !important; }
    div[data-testid="stDataFrame"] td img { 
        display: block !important; 
        max-height: 25px !important; 
        width: auto !important;
        image-rendering: -webkit-optimize-contrast !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONSTANTES ---
BENCHMARK = "MWEQ.DE"
RRG_PERIOD_TREND = 26
RRG_PERIOD_MOM = 4
OFFSET_1W, OFFSET_2W, OFFSET_3W, OFFSET_4W = -1, -2, -3, -4

MY_PORTFOLIO = ["QDVF.DE", "JREM.DE", "XDWI.DE", "SPYH.DE", "XDWM.DE", "LBRA.DE"]
PIRANHA_ETFS = ["SXR8.DE", "XDEW.DE", "XDEE.DE", "IBCF.DE"]

# --- LISTA DE ACTIVOS ---
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
    ("MSCI JAPAN JPN", "JPN", "LCUJ.DE", "INDICEP.PNG", "JAPAN.PNG"),
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
    ("NIKKEI 225", "WRL", "XDJP.DE", "INDICEP.PNG", "WRL.PNG"),
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

# --- 3. LECTURA DE IMÁGENES (LOCAL ESTRICTO) ---

# Calculamos la ruta absoluta de la carpeta donde está este .py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Diccionario de Python para guardar en memoria las imágenes reducidas
_img_cache = {}

def get_img(filename):
    if not filename: 
        return ""
        
    # Si ya la hemos convertido antes, la sacamos de la memoria al instante
    if filename in _img_cache:
        return _img_cache[filename]
        
    # Construimos la ruta absoluta e inamovible al archivo
    filepath = os.path.join(BASE_DIR, filename)
    
    # CHIVATO: Si no encuentra la imagen, devuelve un cuadrado rojo SVG
    cuadrado_rojo = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'><rect width='20' height='20' fill='red'/></svg>"
    
    if not os.path.exists(filepath):
        return cuadrado_rojo
        
    try:
        # Abrimos la imagen
        img = Image.open(filepath)
        
        # Convertimos a formato RGBA por si hay PNGs con transparencias conflictivas
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        # Miniaturizamos radicalmente a 25x25 px
        img.thumbnail((25, 25)) 
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG", optimize=True)
        
        b64_str = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()
        
        # Guardamos en nuestro caché manual
        _img_cache[filename] = b64_str
        return b64_str
        
    except Exception as e:
        # Si hay un error leyendo el archivo (corrupto, etc), mostramos el cuadrado rojo
        return cuadrado_rojo

# --- 4. FUNCIONES PRINCIPALES ---
def calculate_rrg_zscore(p_ticker, p_bench, offset):
    try:
        df = pd.DataFrame({'t': p_ticker, 'b': p_bench}).dropna()
        if len(df) < 32: return ("Error", 0.0, 0.0)
        rs = (df['t'] / df['b']) * 100
        rs_cut = rs if offset == 0 else rs.iloc[:offset]
        m_l, s_l = rs_cut.rolling(RRG_PERIOD_TREND).mean().iloc[-1], rs_cut.rolling(RRG_PERIOD_TREND).std().iloc[-1]
        m_s, s_s = rs_cut.rolling(RRG_PERIOD_MOM).mean().iloc[-1], rs_cut.rolling(RRG_PERIOD_MOM).std().iloc[-1]
        sx = ((rs_cut.iloc[-1] - m_l) / (s_l if s_l else 1)) * 10
        my = ((rs_cut.iloc[-1] - m_s) / (s_s if s_s else 1)) * 10
        lbl = "Leading" if sx >= 0 and my >= 0 else "Weakening" if sx >= 0 and my < 0 else "Lagging" if sx < 0 and my < 0 else "Improving"
        return (lbl, float(sx), float(my))
    except:
        return ("Error", 0.0, 0.0)

@st.cache_data(ttl=300)
def load_data():
    try:
        bench = yf.Ticker(BENCHMARK).history(period="2y")['Close'].resample('W-FRI').last().dropna().tz_localize(None)
    except:
        return pd.DataFrame(), {}

    rows, hist_dict = [], {}
    bar = st.progress(0, "Actualizando precios...")
    for i, (nom, reg, tick, isec, ireg) in enumerate(ASSETS):
        bar.progress((i + 1) / len(ASSETS))
        try:
            h = yf.Ticker(tick).history(period="2y")['Close']
            if h.empty: continue
            d_pct = ((h.iloc[-1] / h.iloc[-2]) - 1) * 100
            ws = h.resample('W-FRI').last().dropna().tz_localize(None)
            m3 = ((ws.iloc[-1] / ws.iloc[-14]) - 1) * 100 if len(ws) >= 14 else 0.0
            rrg = [calculate_rrg_zscore(ws, bench, o) for o in [0, OFFSET_1W, OFFSET_2W, OFFSET_3W, OFFSET_4W]]
            hist_dict[tick] = rrg
            scs = [5.0 + (d[1] * 0.12 + d[2] * 0.04) for d in rrg if d[0] != "Error"]
            fsc = max(0, min(10, np.average(scs[::-1], weights=[0.05, 0.1, 0.15, 0.25, 0.45]) if scs else 0))

            ip = get_img("BENCH.PNG") if tick == BENCHMARK else get_img(
                "penguin.png") if tick in MY_PORTFOLIO else get_img("PIRANHA.png") if tick in PIRANHA_ETFS else ""

            rows.append({
                "Ver": (tick in MY_PORTFOLIO), "Img_S": get_img(isec), "Img_R": get_img(ireg), "Img_P": ip,
                "Ticker": tick, "Nombre": nom, "Reg": reg, "Score": round(fsc, 1),
                "% Hoy": round(d_pct, 2), "% 3M": round(m3, 2), "POS": rrg[0][0], "STR": rrg[0][1], "MOM": rrg[0][2]
            })
        except:
            continue
    bar.empty()
    df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
    df.insert(1, "#", range(1, len(df) + 1))
    return df, hist_dict

# --- 5. INTERFAZ ---
col1, col2 = st.columns([1, 15])
with col1:
    # Aseguramos que el logo también use la ruta absoluta para no perderse
    pinguino_path = os.path.join(BASE_DIR, "PINGUINO.PNG")
    if os.path.exists(pinguino_path): 
        st.image(pinguino_path, width=60)
with col2: st.header("PENGUIN PORTFOLIO")

df, rrg_hist = load_data()
st.caption("Sofía & Alberto 2026")

conf = {
    "Ver": st.column_config.CheckboxColumn("Ver"),
    "Img_S": st.column_config.ImageColumn("Sec"),
    "Img_R": st.column_config.ImageColumn("Reg"),
    "Img_P": st.column_config.ImageColumn("👤"),
    "Score": st.column_config.NumberColumn("Nota"),
    "% Hoy": st.column_config.NumberColumn("% Hoy", format="%.2f%%"),
    "% 3M": st.column_config.NumberColumn("% 3M", format="%.2f%%"),
}

v_cols = ["Ver", "#", "Img_S", "Img_R", "Img_P", "Ticker", "Nombre", "Score", "% Hoy", "% 3M", "POS"]

edited_df = st.data_editor(df, use_container_width=False, hide_index=True, column_order=v_cols, column_config=conf,
                           disabled=[c for c in v_cols if c != "Ver"], height=500)

# --- GRÁFICA ---
plot_t = edited_df[edited_df["Ver"] == True]["Ticker"].tolist()
st.divider()
st.subheader(f"📈 Gráfico RRG")

if plot_t:
    fig, ax = plt.subplots(figsize=(10, 8))
    for i, t in enumerate(plot_t):
        raw = rrg_hist.get(t, [])
        pts = [(r[1], r[2]) for r in raw if r[0] != "Error"][::-1]
        if len(pts) < 2: continue
        xs, ys = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
        if len(xs) >= 3:
            tr = np.arange(len(xs))
            td = np.linspace(0, len(xs) - 1, 100)
            xs = make_interp_spline(tr, xs, k=2)(td)
            ys = make_interp_spline(tr, ys, k=2)(td)
        ax.plot(xs, ys, lw=2, alpha=0.8)
        ax.scatter(xs[-1], ys[-1], s=120)
        row = edited_df[edited_df['Ticker'] == t].iloc[0]
        ax.text(xs[-1], ys[-1], f" {row['Nombre']}", fontsize=9)

    ax.axhline(0, c='gray', lw=1)
    ax.axvline(0, c='gray', lw=1)
    ax.add_patch(Rectangle((0, 0), 20, 20, color='green', alpha=0.1))
    ax.add_patch(Rectangle((-20, 0), 20, 20, color='blue', alpha=0.1))
    ax.add_patch(Rectangle((-20, -20), 20, 20, color='red', alpha=0.1))
    ax.add_patch(Rectangle((0, -20), 20, 20, color='yellow', alpha=0.1))
    st.pyplot(fig)
