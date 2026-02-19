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

# CSS: Ajustes para dispositivos táctiles
st.markdown("""
    <style>
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        justify-content: center !important; text-align: center !important;
    }
    div[data-testid="stDataFrame"] div[role="gridcell"] {
        justify-content: center !important; text-align: center !important;
    }
    div[data-testid="stDataFrame"] td img {
        display: block; margin-left: auto; margin-right: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONSTANTES ---
BENCHMARK = "MWEQ.DE"
RRG_PERIOD_TREND = 26
RRG_PERIOD_MOM = 4
OFFSET_1W = -1
OFFSET_2W = -2
OFFSET_3W = -3
OFFSET_4W = -4

# TU CARTERA ORIGINAL
MY_PORTFOLIO = [
    "QDVF.DE", "JREM.DE", "XDWI.DE",
    "SPYH.DE", "XDWM.DE", "XDW0.DE"
]

# ETFs PARA LA PIRAÑA
PIRANHA_ETFS = ["SXR8.DE", "XDEW.DE", "XDEE.DE", "IBCF.DE"]

# FORMATO: ("Nombre del Activo", "Región", "Ticker", "Img_Sector", "Img_Región")
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


# --- 3. FUNCIONES DE IMAGEN EXTREMA ---
def get_image_base64(path, is_profile=False):
    if not os.path.exists(path): return ""
    try:
        # A los Pingüinos/Pirañas/Bench los tratamos con cariño (son pocos)
        if is_profile:
            with open(path, "rb") as f: data = f.read()
            return "data:image/png;base64," + base64.b64encode(data).decode()

        # A los 356 Sectores y Regiones los ponemos a dieta extrema para los móviles
        img = Image.open(path).convert("RGBA")

        # 1. Le quitamos el canal Alpha (transparencia) que ahoga la memoria gráfica
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, (0, 0), img)  # Usa la propia imagen como máscara de recorte

        # 2. La encogemos brutalmente (28x28)
        bg.thumbnail((28, 28), Image.Resampling.LANCZOS)

        # 3. La guardamos como JPEG en calidad 50%
        buffered = io.BytesIO()
        bg.save(buffered, format="JPEG", quality=50)
        data = buffered.getvalue()

        return "data:image/jpeg;base64," + base64.b64encode(data).decode()

    except Exception:
        return ""


IMG_PATHS_SEC_REG = {}
for item in ASSETS:
    IMG_PATHS_SEC_REG[item[3]] = item[3]
    IMG_PATHS_SEC_REG[item[4]] = item[4]

IMG_PATHS_PROFILE = {"PENGUIN": "penguin.png", "PIRANHA": "PIRANHA.png", "BENCH": "BENCH.PNG"}

cached_imgs = {}

# Procesar los Pingüinos como PNG
for k, v in IMG_PATHS_PROFILE.items():
    cached_imgs[v] = get_image_base64(v, is_profile=True)

# Procesar Sectores y Regiones como JPEG
for v in IMG_PATHS_SEC_REG.values():
    cached_imgs[v] = get_image_base64(v, is_profile=False)


# --- 4. FUNCIONES PRINCIPALES ---
@st.cache_data(ttl=300)
def load_data_and_history():
    try:
        bench = yf.Ticker(BENCHMARK).history(period="2y")['Close'].resample('W-FRI').last().dropna().tz_localize(None)
    except:
        return pd.DataFrame(), {}, []

    rows, history_dict = [], {}
    failed_tickers = []
    bar = st.progress(0, text="Analizando mercado...")
    total = len(ASSETS)

    for i, (nombre, reg, tick, img_sec, img_reg) in enumerate(ASSETS):
        bar.progress((i + 1) / total, text=f"{tick}...")
        try:
            hist = yf.Ticker(tick).history(period="2y")['Close']
            if hist.empty:
                failed_tickers.append(tick)
                continue

            d_curr, d_prev = float(hist.iloc[-1]), float(hist.iloc[-2])
            day_pct = ((d_curr / d_prev) - 1) * 100

            w_series = hist.resample('W-FRI').last().dropna().tz_localize(None)
            w_curr = float(w_series.iloc[-1])
            w_prev3m = float(w_series.iloc[-14]) if len(w_series) >= 14 else w_curr
            m3_pct = ((w_curr / w_prev3m) - 1) * 100

            rrg_data = [calculate_rrg_zscore(w_series, bench, o) for o in
                        [0, OFFSET_1W, OFFSET_2W, OFFSET_3W, OFFSET_4W]]
            history_dict[tick] = rrg_data

            raw_scores = [5.0 + (d[1] * 0.12 + d[2] * 0.04) if d[0] != "Error" else 0.0 for d in rrg_data]
            ordered_scores = raw_scores[::-1]
            final_sc = np.average(ordered_scores, weights=[0.05, 0.1, 0.15, 0.25, 0.45])

            bonus = sum([0.2 for k in range(1, 5) if ordered_scores[k] > ordered_scores[k - 1]])
            final_sc = max(0, min(10, final_sc + bonus))

            is_sec = cached_imgs.get(img_sec) or ""
            is_reg = cached_imgs.get(img_reg) or ""
            is_pro = ""

            if tick == BENCHMARK:
                is_pro = cached_imgs.get("BENCH.PNG") or ""
            elif tick in MY_PORTFOLIO:
                is_pro = cached_imgs.get("penguin.png") or ""
            elif tick in PIRANHA_ETFS:
                is_pro = cached_imgs.get("PIRANHA.png") or ""

            pos_label = rrg_data[0][0]
            pos_display = "🟩 Leading" if "Leading" in pos_label else "🟨 Weak" if "Weakening" in pos_label else "🟥 Lagging" if "Lagging" in pos_label else "🟦 Impr" if "Improving" in pos_label else pos_label

            rows.append({
                "Ver": (tick in MY_PORTFOLIO),
                "Img_S": is_sec, "Img_R": is_reg, "Img_P": is_pro,
                "Ticker": tick, "Nombre": nombre, "Region": reg,
                "Score": float(final_sc),
                "% Hoy": float(day_pct),
                "% 3M": float(m3_pct),
                "POS": pos_display,
                "STR": float(rrg_data[0][1]),
                "MOM": float(rrg_data[0][2])
            })
        except:
            failed_tickers.append(tick)
            continue

    bar.empty()
    df = pd.DataFrame(rows)
    if not df.empty:
        cols_num = ["Score", "% Hoy", "% 3M", "STR", "MOM"]
        for c in cols_num: df[c] = pd.to_numeric(df[c])
        df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)
        df.insert(1, "#", range(1, len(df) + 1))
    return df, history_dict, failed_tickers


def calculate_rrg_zscore(p_ticker, p_bench, offset):
    try:
        df = pd.DataFrame({'t': p_ticker, 'b': p_bench}).dropna()
        if len(df) < (RRG_PERIOD_TREND + abs(offset) + 2): return ("Error", 0.0, 0.0)

        rs = (df['t'] / df['b']) * 100
        rs_cut = rs if offset == 0 else rs.iloc[:offset]

        mean_l, std_l = rs_cut.rolling(RRG_PERIOD_TREND).mean().iloc[-1], rs_cut.rolling(RRG_PERIOD_TREND).std().iloc[
            -1]
        mean_s, std_s = rs_cut.rolling(RRG_PERIOD_MOM).mean().iloc[-1], rs_cut.rolling(RRG_PERIOD_MOM).std().iloc[-1]

        sx = ((rs_cut.iloc[-1] - mean_l) / (std_l if std_l else 1)) * 10
        my = ((rs_cut.iloc[-1] - mean_s) / (std_s if std_s else 1)) * 10

        label = "Improving"
        if sx >= 0 and my >= 0:
            label = "Leading"
        elif sx >= 0 and my < 0:
            label = "Weakening"
        elif sx < 0 and my < 0:
            label = "Lagging"

        return (label, float(sx), float(my))
    except:
        return ("Error", 0.0, 0.0)


# --- 5. INTERFAZ ---
col_logo, col_title = st.columns([1, 15])
with col_logo:
    if os.path.exists("PINGUINO.PNG"):
        st.image("PINGUINO.PNG", width=60)
    else:
        st.header("🐧")
with col_title:
    st.header("PENGUIN PORTFOLIO")

df, rrg_hist, failed_tickers = load_data_and_history()

if failed_tickers:
    st.warning(
        f"Yahoo Finance no ha devuelto datos para {len(failed_tickers)} activo(s) y se han omitido: {', '.join(failed_tickers)}")

if df.empty:
    st.error("Error de datos.")
    st.stop()

st.caption("Sofía & Alberto 2026")

col_conf = {
    "Ver": st.column_config.CheckboxColumn("Ver"),
    "#": st.column_config.NumberColumn("#", format="%d"),
    "Img_S": st.column_config.ImageColumn("Sec", width="small"),
    "Img_R": st.column_config.ImageColumn("Reg", width="small"),
    "Img_P": st.column_config.ImageColumn("👤", width="small"),
    "Score": st.column_config.NumberColumn("Nota", format="%.1f"),
    "% Hoy": st.column_config.NumberColumn("% Hoy", format="%.2f%%"),
    "% 3M": st.column_config.NumberColumn("% 3M", format="%.2f%%"),
    "STR": st.column_config.NumberColumn("STR", format="%.2f"),
    "MOM": st.column_config.NumberColumn("MOM", format="%.2f"),
}

visible_cols = ["Ver", "#", "Img_S", "Img_R", "Img_P", "Ticker", "Nombre", "Score", "% Hoy", "% 3M", "POS", "STR",
                "MOM"]

edited_df = st.data_editor(
    df,
    use_container_width=False,
    hide_index=True,
    column_order=visible_cols,
    column_config=col_conf,
    disabled=[c for c in visible_cols if c != "Ver"],
    height=500
)

# --- GRÁFICA ---
plot_tickers = edited_df[edited_df["Ver"] == True]["Ticker"].tolist()

st.divider()
st.subheader(f"📈 Gráfico RRG ({len(plot_tickers)} activos)")

if plot_tickers:
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22',
              '#17becf']
    all_x, all_y = [], []

    for i, t in enumerate(plot_tickers):
        raw = rrg_hist.get(t, [])
        if not raw: continue

        pts = [(r[1], r[2]) for r in raw if r[0] != "Error"]
        if len(pts) < 2: continue

        pts_chron = list(reversed(pts))
        xs = np.array([p[0] for p in pts_chron])
        ys = np.array([p[1] for p in pts_chron])
        all_x.extend(xs);
        all_y.extend(ys)

        px, py = xs, ys
        if len(xs) >= 3:
            try:
                tr = np.arange(len(xs))
                td = np.linspace(0, len(xs) - 1, 100)
                px = make_interp_spline(tr, xs, k=2)(td)
                py = make_interp_spline(tr, ys, k=2)(td)
            except:
                pass

        c = colors[i % len(colors)]
        ax.plot(px, py, color=c, lw=2, alpha=0.8)
        ax.scatter(xs[:-1], ys[:-1], s=20, color=c, alpha=0.6)

        row_info = edited_df[edited_df['Ticker'] == t].iloc[0]
        label = f" {row_info['Nombre']} ({row_info['Region']})"
        fw, ec = 'normal', c
        if t in MY_PORTFOLIO:
            label = "🐧 " + label
            fw, ec = 'bold', 'black'

        ax.scatter(xs[-1], ys[-1], s=120, color=c, edgecolors=ec, zorder=5)
        ax.text(xs[-1], ys[-1], label, color=c, fontweight=fw, fontsize=9)

    if all_x and all_y:
        margin = 0.1
        x_min_dat, x_max_dat = min(all_x), max(all_x)
        x_rng = x_max_dat - x_min_dat if x_max_dat != x_min_dat else 1.0
        x_lim_min = x_min_dat - (x_rng * margin)
        x_lim_max = x_max_dat + (x_rng * margin)
        if x_lim_min > -0.5 and x_lim_min < 0: x_lim_min = -0.5
        if x_lim_max < 0.5 and x_lim_max > 0: x_lim_max = 0.5

        y_min_dat, y_max_dat = min(all_y), max(all_y)
        y_rng = y_max_dat - y_min_dat if y_max_dat != y_min_dat else 1.0
        y_lim_min = y_min_dat - (y_rng * margin)
        y_lim_max = y_max_dat + (y_rng * margin)

        ax.set_xlim(x_lim_min, x_lim_max)
        ax.set_ylim(y_lim_min, y_lim_max)

        w_right, h_top = max(0, x_lim_max), max(0, y_lim_max)
        w_left, h_bot = min(0, x_lim_min), min(0, y_lim_min)

        ax.add_patch(Rectangle((0, 0), w_right, h_top, color='#e8f5e9', alpha=0.3, zorder=0))
        ax.add_patch(Rectangle((0, 0), w_right, h_bot, color='#fffde7', alpha=0.3, zorder=0))
        ax.add_patch(Rectangle((0, 0), w_left, h_bot, color='#ffebee', alpha=0.3, zorder=0))
        ax.add_patch(Rectangle((0, 0), w_left, h_top, color='#e3f2fd', alpha=0.3, zorder=0))
        ax.axhline(0, c='gray', lw=1, zorder=1)
        ax.axvline(0, c='gray', lw=1, zorder=1)

        ax.text(x_lim_max * 0.95, y_lim_max * 0.95, "LEADING", color='green', ha='right', va='top', fontweight='bold')
        ax.text(x_lim_max * 0.95, y_lim_min * 0.95, "WEAKENING", color='orange', ha='right', va='bottom',
                fontweight='bold')
        ax.text(x_lim_min * 0.95, y_lim_min * 0.95, "LAGGING", color='red', ha='left', va='bottom', fontweight='bold')
        ax.text(x_lim_min * 0.95, y_lim_max * 0.95, "IMPROVING", color='blue', ha='left', va='top', fontweight='bold')

    st.pyplot(fig)
else:
    st.info("Selecciona activos.")