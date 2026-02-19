import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.interpolate import make_interp_spline
import base64
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="PENGUIN PORTFOLIO", page_icon="🐧")

# CSS: Forzamos el centrado y un tamaño fijo pequeño para que el móvil no sufra
st.markdown("""
    <style>
    div[data-testid="stDataFrame"] div[role="columnheader"] { justify-content: center !important; text-align: center !important; }
    div[data-testid="stDataFrame"] div[role="gridcell"] { justify-content: center !important; text-align: center !important; }
    div[data-testid="stDataFrame"] td img { 
        display: block !important; 
        margin: auto !important; 
        width: 24px !important; 
        height: 24px !important; 
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONSTANTES ---
BENCHMARK = "MWEQ.DE"
RRG_PERIOD_TREND, RRG_PERIOD_MOM = 26, 4
OFFSET_1W, OFFSET_2W, OFFSET_3W, OFFSET_4W = -1, -2, -3, -4

MY_PORTFOLIO = ["QDVF.DE", "JREM.DE", "XDWI.DE", "SPYH.DE", "XDWM.DE", "XDW0.DE"]
PIRANHA_ETFS = ["SXR8.DE", "XDEW.DE", "XDEE.DE", "IBCF.DE"]

# --- LISTA DE ACTIVOS (Tu lista completa de 178) ---
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


# --- 3. LECTURA DE IMAGEN (VERSION LIGERA) ---
@st.cache_data
def get_img(path):
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"


# --- 4. FUNCIONES ---
def calculate_rrg(p_ticker, p_bench, offset):
    try:
        df = pd.DataFrame({'t': p_ticker, 'b': p_bench}).dropna()
        if len(df) < 32: return ("Error", 0.0, 0.0)
        rs = (df['t'] / df['b']) * 100
        cut = rs if offset == 0 else rs.iloc[:offset]
        m_l, s_l = cut.rolling(26).mean().iloc[-1], cut.rolling(26).std().iloc[-1]
        m_s, s_s = cut.rolling(4).mean().iloc[-1], cut.rolling(4).std().iloc[-1]
        sx = ((cut.iloc[-1] - m_l) / (s_l if s_l else 1)) * 10
        my = ((cut.iloc[-1] - m_s) / (s_s if s_s else 1)) * 10
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
    rows, h_dict = [], {}
    bar = st.progress(0, "🐧 Analizando mercado...")
    for i, (nom, reg, tick, isec, ireg) in enumerate(ASSETS):
        bar.progress((i + 1) / len(ASSETS))
        try:
            h = yf.Ticker(tick).history(period="2y")['Close']
            if h.empty: continue
            ws = h.resample('W-FRI').last().dropna().tz_localize(None)
            rrg = [calculate_rrg(ws, bench, o) for o in [0, -1, -2, -3, -4]]
            h_dict[tick] = rrg
            scs = [5.0 + (d[1] * 0.12 + d[2] * 0.04) for d in rrg if d[0] != "Error"]
            fsc = max(0, min(10, np.average(scs[::-1], weights=[0.05, 0.1, 0.15, 0.25, 0.45]) if scs else 0))

            p_img = "BENCH.PNG" if tick == BENCHMARK else "penguin.png" if tick in MY_PORTFOLIO else "PIRANHA.png" if tick in PIRANHA_ETFS else ""

            rows.append({
                "Ver": (tick in MY_PORTFOLIO), "Sec": get_img(isec), "Reg": get_img(ireg),
                "👤": get_img(p_img) if p_img else "",
                "Ticker": tick, "Nombre": nom, "Score": round(fsc, 1),
                "% Hoy": round(((h.iloc[-1] / h.iloc[-2]) - 1) * 100, 2),
                "POS": rrg[0][0]
            })
        except:
            continue
    return pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True), h_dict


# --- 5. INTERFAZ ---
c1, c2 = st.columns([1, 15])
with c1:
    if os.path.exists("PINGUINO.PNG"): st.image("PINGUINO.PNG", width=60)
with c2: st.header("PENGUIN PORTFOLIO")

df, rrg_hist = load_data()

conf = {
    "Ver": st.column_config.CheckboxColumn("Ver"),
    "Sec": st.column_config.ImageColumn("Sec"),
    "Reg": st.column_config.ImageColumn("Reg"),
    "👤": st.column_config.ImageColumn("👤"),
    "Score": st.column_config.NumberColumn("Nota"),
    "% Hoy": st.column_config.NumberColumn("% Hoy", format="%.2f%%"),
}
v_cols = ["Ver", "Sec", "Reg", "👤", "Ticker", "Nombre", "Score", "% Hoy", "POS"]

st.data_editor(df, hide_index=True, column_order=v_cols, column_config=conf, disabled=[c for c in v_cols if c != "Ver"],
               height=500)

# --- GRÁFICA ---
plot_t = st.multiselect("Activos en Gráfica", df["Ticker"].tolist(), default=MY_PORTFOLIO)
if plot_t:
    fig, ax = plt.subplots(figsize=(10, 8))
    for t in plot_t:
        pts = [(r[1], r[2]) for r in rrg_hist.get(t, []) if r[0] != "Error"][::-1]
        if len(pts) < 2: continue
        xs, ys = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
        if len(xs) >= 3:
            tr = np.arange(len(xs))
            td = np.linspace(0, len(xs) - 1, 100)
            xs, ys = make_interp_spline(tr, xs, k=2)(td), make_interp_spline(tr, ys, k=2)(td)
        ax.plot(xs, ys, lw=2);
        ax.scatter(xs[-1], ys[-1], s=100)
    ax.axhline(0, c='gray', lw=1);
    ax.axvline(0, c='gray', lw=1)
    st.pyplot(fig)