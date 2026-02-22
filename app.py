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
st.set_page_config(layout="wide", page_title="PENGUIN PORTFOLIO PRO", page_icon="🐧")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:italic,wght@400;700&display=swap');
    .alberto-sofia {
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 1.6rem;
        color: #4A4A4A;
        margin-top: -20px;
        margin-bottom: 25px;
    }
    /* Optimización de visualización de imágenes en tablas */
    div[data-testid="stDataFrame"] td img { 
        display: block !important; 
        max-height: 30px !important; 
        width: auto !important;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. LÓGICA DE ESTADO (SESSIÓN) ---
if 'w_pos' not in st.session_state: st.session_state.w_pos = 60.0
if 'w_ang' not in st.session_state: st.session_state.w_ang = 30.0
if 'w_r2' not in st.session_state: st.session_state.w_r2 = 10.0

def sync_pos():
    val = st.session_state.sl_pos
    rem = 100.0 - val
    st.session_state.w_pos, st.session_state.w_ang, st.session_state.w_r2 = val, rem / 2, rem / 2

def sync_ang():
    val = st.session_state.sl_ang
    rem = 100.0 - val
    st.session_state.w_ang, st.session_state.w_pos, st.session_state.w_r2 = val, rem / 2, rem / 2

def sync_r2():
    val = st.session_state.sl_r2
    rem = 100.0 - val
    st.session_state.w_r2, st.session_state.w_pos, st.session_state.w_ang = val, rem / 2, rem / 2

# --- 3. CABECERA ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

col_h1, col_h2 = st.columns([1, 15])
with col_h1:
    img_p_path = os.path.join(BASE_DIR, "pinguino.png")
    if os.path.exists(img_p_path): 
        st.image(img_p_path, width=65)
with col_h2: 
    st.header("PENGUIN PORTFOLIO")
st.markdown('<p class="alberto-sofia">Sofía y Alberto 2026</p>', unsafe_allow_html=True)

# --- 4. CONTROLES ---
c1, c2, c3 = st.columns(3)
with c1: st.slider("POS %", 0.0, 100.0, float(st.session_state.w_pos), key="sl_pos", on_change=sync_pos)
with c2: st.slider("ANG %", 0.0, 100.0, float(st.session_state.w_ang), key="sl_ang", on_change=sync_ang)
with c3: st.slider("R² %", 0.0, 100.0, float(st.session_state.w_r2), key="sl_r2", on_change=sync_r2)

WP, WA, WR = st.session_state.w_pos / 100, st.session_state.w_ang / 100, st.session_state.w_r2 / 100

# --- 5. ASSETS Y CONSTANTES ---
BENCHMARK = "MWEQ.DE"
MY_PORTFOLIO = ["LCUJ.DE", "B41J.DE", "XDWI.DE", "SW2CHB.SW", "XDWM.DE", "LBRA.DE"]
PIRANHA_ETFS = ["SXR8.DE", "XDEW.DE", "XDEE.DE", "IBCF.DE"]

# Lista de activos corregida
ASSETS = [
    ("AGGREGATE HDG", "EME", "XEMB.DE", "BONDS.PNG", "EME.PNG"),
    ("AGGREGATE HDG", "WRL", "DBZB.DE", "BONDS.PNG", "WRL.PNG"),
    ("CASH", "EUR", "YCSH.DE", "CASH.PNG", "EUR.PNG"),
    ("CORPORATE BONDS", "WRL", "D5BG.DE", "BONDS.PNG", "WRL.PNG"),
    ("CORPORATE HY", "WRL", "XHYA.DE", "BONDS.PNG", "WRL.PNG"),
    ("EUR GOV 1-3", "EUR", "DBXP.DE", "BONDS.PNG", "EUR.PNG"),
    ("EUR GOV 10-15", "EUR", "LYQ6.DE", "BONDS.PNG", "EUR.PNG"),
    ("EUR GOV 15+", "EUR", "LYXF.DE", "BONDS.PNG", "EUR.PNG"),
    ("EUR GOV 3-5", "EUR", "LYQ3.DE", "BONDS.PNG", "EUR.PNG"),
    ("EUR GOV 7-10", "EUR", "LYXD.DE", "BONDS.PNG", "EUR.PNG"),
    ("JAPAN AGG HDG", "JPN", "CEB2.DE", "BONDS.PNG", "JAPAN.PNG"),
    ("TIPS", "EUR", "XEIN.DE", "BONDS.PNG", "EUR.PNG"),
    ("TIPS HDG", "USA", "IBC5.DE", "BONDS.PNG", "USA.PNG"),
    ("TREASURY AGG", "USA", "VAGT.DE", "BONDS.PNG", "USA.PNG"),
    ("AGRICULTURE", "COM", "AIGA.MI", "FARM.PNG", "COM.PNG"),
    ("BITCOIN", "COM", "IB1T.DE", "CRYPTO.PNG", "COM.PNG"),
    ("BLOOMBERG COMM", "COM", "CMOE.MI", "COM.PNG", "COM.PNG"),
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
    ("DOW JONES", "USA", "SXRU.DE", "INDICEP.PNG", "USA.PNG"),
    ("FTSE 100", "EUR", "CEB4.DE", "INDICEP.PNG", "EUR.PNG"),
    ("FTSE KOREA", "EME", "FLXK.DE", "INDICEP.PNG", "EME.PNG"),
    ("FTSE MIB", "EUR", "SXRY.DE", "INDICEP.PNG", "EUR.PNG"),
    ("IBEX 35", "EUR", "AMES.DE", "INDICEP.PNG", "EUR.PNG"),
    ("MSCI ARABIA", "EME", "IUSS.DE", "INDICEP.PNG", "EME.PNG"),
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
    ("MSCI SWISS CHF", "EUR", "SW2CHB.SW", "INDICEP.PNG", "EUR.PNG"),
    ("MSCI TAIWAN", "EME", "DBX5.DE", "INDICEP.PNG", "EME.PNG"),
    ("MSCI THAILAND", "EME", "XCS4.DE", "INDICEP.PNG", "EME.PNG"),
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
    ("MSCI EM ASIA", "EME", "AMEA.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI EM EX-CHN", "EME", "EMXC.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI EM", "EME", "IS3N.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI LATAM", "EME", "DBX3.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI NORDIC", "EUR", "XDN0.DE", "INDICES.PNG", "EUR.PNG"),
    ("MSCI PACIFIC-EX", "EME", "18MM.DE", "INDICES.PNG", "EME.PNG"),
    ("MSCI WORLD", "WRL", "EUNL.DE", "INDICES.PNG", "WRL.PNG"),
    ("MSCI WORLD EW", "WRL", "MWEQ.DE", "INDICES.PNG", "WRL.PNG"),
    ("MSCI WORLD EX-USA", "WRL", "EXUS.DE", "INDICES.PNG", "WRL.PNG"),
    ("MSCI WORLD HDG", "WRL", "IBCH.DE", "INDICES.PNG", "WRL.PNG"),
    ("STOXX 50", "EUR", "SXRT.DE", "INDICES.PNG", "EUR.PNG"),
    ("STOXX 600", "EUR", "LYP6.DE", "INDICES.PNG", "EUR.PNG"),
    ("COMMUNICATION", "EUR", "SPYT.DE", "COMMUNICATIONS.PNG", "EUR.PNG"),
    ("COMMUNICATION", "USA", "IU5C.DE", "COMMUNICATIONS.PNG", "USA.PNG"),
    ("COMMUNICATION", "WRL", "TELW.PA", "COMMUNICATIONS.PNG", "WRL.PNG"),
    ("DISCRETIONARY", "EUR", "SPYR.DE", "DISCRETIONARY.PNG", "EUR.PNG"),
    ("DISCRETIONARY", "USA", "QDVK.DE", "DISCRETIONARY.PNG", "USA.PNG"),
    ("DISCRETIONARY", "WRL", "WELJ.DE", "DISCRETIONARY.PNG", "WRL.PNG"),
    ("STAPLES", "EUR", "SPYC.DE", "STAPLES.PNG", "EUR.PNG"),
    ("STAPLES", "USA", "2B7D.DE", "STAPLES.PNG", "USA.PNG"),
    ("STAPLES", "WRL", "WELW.DE", "STAPLES.PNG", "WRL.PNG"),
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
    ("UTILITIES", "EUR", "SPYU.DE", "UTILITIES.PNG", "EUR.PNG"),
    ("UTILITIES", "USA", "2B7A.DE", "UTILITIES.PNG", "USA.PNG"),
    ("UTILITIES", "WRL", "WELD.DE", "UTILITIES.PNG", "WRL.PNG"),
    ("AI INFRA", "ALL", "AIFS.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("ARK INNOV", "WRL", "ARXK.DE", "THEMATIC.PNG", "WRL.PNG"),
    ("CYBER SECURITY", "WRL", "USPY.DE", "THEMATIC.PNG", "WRL.PNG"),
    ("DEFENSE EUR", "EUR", "EDFS.DE", "THEMATIC.PNG", "EUR.PNG"),
    ("INFRA EUR", "EUR", "B41J.DE", "THEMATIC.PNG", "EUR.PNG"),
    ("SEMICONDUCTOR", "ALL", "VVSM.DE", "THEMATIC.PNG", "ALL.PNG"),
    ("URANIUM", "ALL", "NUKL.DE", "THEMATIC.PNG", "ALL.PNG")
]

# --- 6. SERVICIOS ---
_img_cache = {}

def get_img_b64(filename):
    if not filename: return None
    if filename in _img_cache: return _img_cache[filename]
    
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        with Image.open(path) as img:
            # Convertir a RGBA para consistencia
            img = img.convert("RGBA")
            img.thumbnail((35, 35))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
            _img_cache[filename] = b64
            return b64
    except:
        return None

def get_rrg_pts(ticker_df, bench_df):
    rs = (ticker_df / bench_df) * 100
    rs_sm = rs.ewm(span=20, adjust=False).mean()
    m_l, s_l = rs_sm.rolling(130).mean(), rs_sm.rolling(130).std()
    rs_ratio = ((rs_sm - m_l) / s_l.replace(0, 1)) * 10 + 100
    rs_mom_raw = rs_sm.pct_change(periods=20) * 100
    m_s, s_s = rs_mom_raw.rolling(20).mean(), rs_mom_raw.rolling(20).std()
    rs_mom = ((rs_mom_raw - m_s) / s_s.replace(0, 1)) * 10 + 100
    return rs_ratio, rs_mom

@st.cache_data(ttl=300)
def load_data(tickers):
    try:
        return yf.download(tickers, period="2y", auto_adjust=True, progress=False)['Close']
    except:
        return pd.DataFrame()

# --- 7. PROCESAMIENTO ---
t_list = list(set([a[2] for a in ASSETS] + [BENCHMARK]))
with st.status("ACTUALIZANDO MERCADOS...", expanded=False) as status:
    raw_prices = load_data(t_list)
    status.update(label="DATOS LISTOS", state="complete")

if not raw_prices.empty:
    bench_p = raw_prices[BENCHMARK]
    res_raw, rrg_hist = [], {}

    for name, reg, tick, isec, ireg in ASSETS:
        if tick not in raw_prices.columns: continue
        r_ser, m_ser = get_rrg_pts(raw_prices[tick], bench_p)
        if r_ser.isna().all() or len(r_ser) < 30: continue

        pts = []
        for d in [0, 5, 10, 15, 20]:
            idx = -(d + 1)
            pts.append((float(r_ser.iloc[idx]), float(m_ser.iloc[idx])))

        # Cálculo de Score
        d_curr = np.sqrt((140 - pts[0][0]) ** 2 + (140 - pts[0][1]) ** 2)
        t_ax = np.array([1, 2, 3, 4, 5])
        xv, yv = np.array([p[0] for p in pts][::-1]), np.array([p[1] for p in pts][::-1])
        sx, _ = np.polyfit(t_ax, xv, 1)
        sy, _ = np.polyfit(t_ax, yv, 1)
        angle = np.degrees(np.arctan2(sy, sx))
        diff = angle - 45
        if diff > 180: diff -= 360
        if diff < -180: diff += 360
        ang_val = np.clip(10 - (abs(diff) / 18), 0, 10)

        def get_r2(t, v, s):
            res = np.sum((v - (s * t + (np.mean(v) - s * np.mean(t)))) ** 2)
            tot = np.sum((v - np.mean(v)) ** 2)
            return 1 - (res / tot) if tot > 1e-6 else 0

        r2_sc = np.clip(((get_r2(t_ax, xv, sx) + get_r2(t_ax, yv, sy)) / 2) * 10, 0, 10)
        ret1d = ((raw_prices[tick].iloc[-1] / raw_prices[tick].iloc[-2]) - 1) * 100
        ret3m = ((raw_prices[tick].iloc[-1] / raw_prices[tick].iloc[-63]) - 1) * 100 if len(raw_prices[tick]) >= 63 else 0

        res_raw.append({
            "tick": tick, "name": name, "reg": reg, "isec": isec, "ireg": ireg,
            "d_curr": d_curr, "ang": ang_val, "r2": r2_sc, "str": pts[0][0] - 100, "mom": pts[0][1] - 100,
            "r1d": ret1d, "r3m": ret3m
        })
        rrg_hist[tick] = pts

    dists = [r['d_curr'] for r in res_raw]
    min_d, max_d = min(dists), max(dists)

    final_rows = []
    for r in res_raw:
        pos_sc = ((max_d - r['d_curr']) / (max_d - min_d)) * 10 if max_d != min_d else 5.0
        score = (pos_sc * WP) + (r['ang'] * WA) + (r['r2'] * WR)
        
        # Asignación de iconos
        ic_p = "pinguino.png" if r['tick'] in MY_PORTFOLIO else "PIRANHA.png" if r['tick'] in PIRANHA_ETFS else ""

        final_rows.append({
            "Ver": (r['tick'] in MY_PORTFOLIO), 
            "Img_S": get_img_b64(r['isec']), 
            "Img_R": get_img_b64(r['ireg']),
            "Img_P": get_img_b64(ic_p),
            "Ticker": r['tick'], "Nombre": r['name'], "Score": round(score, 2),
            "P-Pos": round(pos_sc, 2), "P-Ang": round(r['ang'], 2), "P-R2": round(r['r2'], 2),
            "STR": round(r['str'], 2), "MOM": round(r['mom'], 2),
            "% Hoy": round(r['r1d'], 2), "% 3M": round(r['r3m'], 2),
            "POS": "Leading" if r['str'] >= 0 and r['mom'] >= 0 else "Weakening" if r['str'] >= 0 and r['mom'] < 0 else "Lagging" if r['str'] < 0 and r['mom'] < 0 else "Improving"
        })

    df = pd.DataFrame(final_rows).sort_values("Score", ascending=False).reset_index(drop=True)
    df.insert(1, "#", range(1, len(df) + 1))

    # --- 8. VISTA TABLA ---
    conf = {
        "Ver": st.column_config.CheckboxColumn("Ver"), 
        "Img_S": st.column_config.ImageColumn("Sec", width="small"),
        "Img_R": st.column_config.ImageColumn("Reg", width="small"), 
        "Img_P": st.column_config.ImageColumn("👤", width="small"),
        "Score": st.column_config.NumberColumn("Nota"),
        "% Hoy": st.column_config.NumberColumn("% Hoy", format="%.2f%%"),
        "% 3M": st.column_config.NumberColumn("% 3M", format="%.2f%%"),
    }
    
    v_cols = ["Ver", "#", "Img_S", "Img_R", "Img_P", "Ticker", "Nombre", "Score", "P-Pos", "P-Ang", "P-R2", "STR", "MOM", "% Hoy", "% 3M", "POS"]
    
    edit_df = st.data_editor(df, hide_index=True, column_order=v_cols, column_config=conf,
                             disabled=[c for c in v_cols if c != "Ver"], height=550)

    # --- 9. GRÁFICA ---
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

            if len(xs) >= 3:
                tr = np.arange(len(xs))
                td = np.linspace(0, len(xs)-1, 100)
                xs_s = make_interp_spline(tr, xs, k=2)(td)
                ys_s = make_interp_spline(tr, ys, k=2)(td)
                ax.plot(xs_s, ys_s, lw=1.5, alpha=0.8)

            ax.scatter(xs[:-1], ys[:-1], s=30, alpha=0.3)
            ax.scatter(xs[-1], ys[-1], s=180, edgecolors='white', linewidth=2, zorder=5)
            ax.text(xs[-1], ys[-1], f"  {t}", fontsize=10, fontweight='bold')

        ax.axhline(0, c='#999999', lw=1); ax.axvline(0, c='#999999', lw=1)
        limit = max(max(abs(min(all_x or [-10])), abs(max(all_x or [10]))), max(abs(min(all_y or [-10])), abs(max(all_y or [10])))) * 1.2
        ax.set_xlim(-limit, limit); ax.set_ylim(-limit, limit)
        
        ax.add_patch(Rectangle((0, 0), limit, limit, color='green', alpha=0.05))
        ax.add_patch(Rectangle((-limit, 0), limit, limit, color='blue', alpha=0.05))
        ax.add_patch(Rectangle((-limit, -limit), limit, limit, color='red', alpha=0.05))
        ax.add_patch(Rectangle((0, -limit), limit, limit, color='yellow', alpha=0.05))
        
        st.pyplot(fig)
