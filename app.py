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
st.set_page_config(layout="wide", page_title="RRG Pro Mobile", page_icon="🐧")

# CSS: Centrado agresivo y ajustes visuales
st.markdown("""
    <style>
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        justify-content: center !important; text-align: center !important;
    }
    div[data-testid="stDataFrame"] div[role="gridcell"] {
        justify-content: center !important; text-align: center !important; display: flex !important;
    }
    div[data-testid="stDataFrame"] div[role="gridcell"] > div {
        justify-content: center !important; text-align: center !important; margin: auto !important;
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

MY_PORTFOLIO = [
    "QDVF.DE", "ZPRX.DE", "XDWI.DE",
    "SPYU.DE", "XDWM.DE", "CEMS.DE"
]

IMG_PATHS = {
    "PENGUIN": "penguin.png", "PIRANHA": "PIRANHA.png",
    "USA": "usa.png", "EUR": "eur.png", "WRL": "wrl.png", "EME": "eme.png",
    "SEC_TECH": "TECHNOLOGY.png", "SEC_SIZE": "SIZE.png", "SEC_MOM": "MOMENTUM.png",
    "SEC_VAL": "VALUE.png", "SEC_REIT": "REIT.png", "SEC_YIELD": "HIGH YIELD.png",
    "SEC_VOL": "VOLATILITY.png", "SEC_IND": "INDUSTRIALS.png", "SEC_QUAL": "QUALITY.png",
    "SEC_DISC": "DISCRETIONARY.png", "SEC_STAPLES": "STAPLES.png", "SEC_ENERGY": "ENERGY.png",
    "SEC_MAT": "MATERIALS.png", "SEC_COMM": "COMMUNICATIONS.png", "SEC_UTIL": "UTILITIES.png",
    "SEC_FIN": "FINANCIALS.png", "SEC_HC": "HEALTH CARE.png", "SEC_CASH": "CASH.png",
    "SEC_IDX": "INDICES.png"
}

SECTOR_IMG_MAP = {
    "TECHNOLOGY": "SEC_TECH", "SIZE": "SEC_SIZE", "MOMENTUM": "SEC_MOM",
    "VALUE": "SEC_VAL", "REIT": "SEC_REIT", "HIGH YIELD": "SEC_YIELD",
    "LOW VOL": "SEC_VOL", "INDUSTRIALS": "SEC_IND", "QUALITY": "SEC_QUAL",
    "DISCRETIONARY": "SEC_DISC", "STAPLES": "SEC_STAPLES", "ENERGY": "SEC_ENERGY",
    "MATERIALS": "SEC_MAT", "COMMUNICATIONS": "SEC_COMM", "UTILITIES": "SEC_UTIL",
    "FINANCIALS": "SEC_FIN", "HEALTH CARE": "SEC_HC", "CASH": "SEC_CASH",
    "INDICE": "SEC_IDX", "MSCI WORLD EW": "SEC_IDX"
}

ASSETS = [
    ("CASH", "EUR", "YCSH.DE"),
    ("MSCI WORLD EW", "WRL", "MWEQ.DE"),
    ("ENERGY", "USA", "QDVF.DE"), ("ENERGY", "WRL", "XDW0.DE"), ("STAPLES", "USA", "2B7D.DE"),
    ("ENERGY", "EUR", "SPYN.DE"), ("STAPLES", "WRL", "XDWS.DE"), ("STAPLES", "EUR", "SPYC.DE"),
    ("VALUE", "EME", "5MVL.DE"), ("HIGH YIELD", "EME", "EUNY.DE"), ("UTILITIES", "EUR", "SPYU.DE"),
    ("HIGH YIELD", "USA", "XDND.DE"), ("INDUSTRIALS", "USA", "2B7C.DE"), ("VALUE", "WRL", "IS3S.DE"),
    ("MATERIALS", "EUR", "SPYP.DE"), ("MATERIALS", "WRL", "XDWM.DE"), ("MATERIALS", "USA", "2B7B.DE"),
    ("VALUE", "EUR", "CEMS.DE"),
    ("QUALITY", "EME", "JREM.DE"), ("VALUE", "USA", "QDVI.DE"),
    ("INDUSTRIALS", "WRL", "XDWI.DE"), ("SIZE", "USA", "ZPRV.DE"), ("SIZE", "EME", "SPYX.DE"),
    ("INDICE", "EME", "IS3N.DE"), ("MOMENTUM", "EME", "EGEE.DE"), ("LOW VOL", "EUR", "ZPRL.DE"),
    ("LOW VOL", "EME", "EUNZ.DE"), ("LOW VOL", "USA", "SPY1.DE"), ("SIZE", "EUR", "ZPRX.DE"),
    ("REIT", "USA", "IQQ7.DE"), ("REIT", "WRL", "SPY2.DE"), ("HIGH YIELD", "WRL", "XZDW.DE"),
    ("REIT", "EUR", "IPRE.DE"), ("UTILITIES", "WRL", "XDWU.DE"), ("SIZE", "WRL", "IUSN.DE"),
    ("INDICE", "EUR", "LYP6.DE"), ("MOMENTUM", "EUR", "CEMR.DE"), ("FINANCIALS", "EUR", "SPYZ.DE"),
    ("INDUSTRIALS", "EUR", "SPYQ.DE"),
    ("COMMUNICATIONS", "EUR", "SPYT.DE"),
    ("HIGH YIELD", "EUR", "XZDZ.DE"), ("HEALTH CARE", "EUR", "SPYH.DE"), ("QUALITY", "EUR", "CEMQ.DE"),
    ("UTILITIES", "USA", "2B7A.DE"), ("QUALITY", "WRL", "IS3Q.DE"), ("LOW VOL", "WRL", "CSY9.DE"),
    ("INDICE", "WRL", "EUNL.DE"), ("HEALTH CARE", "WRL", "XDWH.DE"), ("HEALTH CARE", "USA", "QDVG.DE"),
    ("TECHNOLOGY", "EUR", "SPYK.DE"), ("MOMENTUM", "WRL", "IS3R.DE"), ("QUALITY", "USA", "QDVB.DE"),
    ("FINANCIALS", "WRL", "XDWF.DE"), ("INDICE", "USA", "SXR8.DE"), ("COMMUNICATIONS", "USA", "IU5C.DE"),
    ("COMMUNICATIONS", "WRL", "XWTS.DE"), ("MOMENTUM", "USA", "QDVA.DE"), ("FINANCIALS", "USA", "QDVH.DE"),
    ("TECHNOLOGY", "WRL", "XDWT.DE"), ("TECHNOLOGY", "USA", "QDVE.DE"), ("DISCRETIONARY", "USA", "QDVK.DE"),
    ("DISCRETIONARY", "WRL", "XDWC.DE"), ("TECHNOLOGY", "EME", "EMQQ.DE"), ("DISCRETIONARY", "EUR", "SPYR.DE")
]


# --- 3. CÁLCULOS ---

def get_image_base64(path):
    if not os.path.exists(path): return None
    with open(path, "rb") as f: data = f.read()
    return "data:image/png;base64," + base64.b64encode(data).decode()


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


@st.cache_data(ttl=3600)
def load_data_and_history():
    try:
        bench = yf.Ticker(BENCHMARK).history(period="2y")['Close'].resample('W-FRI').last().dropna().tz_localize(None)
    except:
        return pd.DataFrame(), {}

    rows, history_dict = [], {}
    cached_imgs = {k: get_image_base64(v) for k, v in IMG_PATHS.items()}

    bar = st.progress(0, text="Analizando...")
    total = len(ASSETS)

    for i, (sec, reg, tick) in enumerate(ASSETS):
        bar.progress((i + 1) / total, text=f"{tick}...")
        try:
            hist = yf.Ticker(tick).history(period="2y")['Close']
            if hist.empty: continue

            # Precios
            d_curr, d_prev = float(hist.iloc[-1]), float(hist.iloc[-2])
            day_pct = ((d_curr / d_prev) - 1) * 100

            w_series = hist.resample('W-FRI').last().dropna().tz_localize(None)
            w_curr = float(w_series.iloc[-1])
            w_prev3m = float(w_series.iloc[-14]) if len(w_series) >= 14 else w_curr
            m3_pct = ((w_curr / w_prev3m) - 1) * 100

            # RRG Data: [Hoy, 1W, 2W, 3W, 4W]
            rrg_data = [calculate_rrg_zscore(w_series, bench, o) for o in
                        [0, OFFSET_1W, OFFSET_2W, OFFSET_3W, OFFSET_4W]]
            history_dict[tick] = rrg_data

            # --- CORRECCIÓN MATEMÁTICA DE LA NOTA ---
            # 1. Obtenemos nota pura de cada semana
            raw_scores = [5.0 + (d[1] * 0.12 + d[2] * 0.04) if d[0] != "Error" else 0.0 for d in rrg_data]

            # 2. Invertimos para que coincida con los pesos (Viejo -> Nuevo)
            # raw_scores original: [Hoy, 1W, 2W, 3W, 4W]
            # ordered_scores:      [4W, 3W, 2W, 1W, Hoy]
            ordered_scores = raw_scores[::-1]

            # 3. Media Ponderada (0.05 para 4W ... 0.45 para Hoy)
            weights = [0.05, 0.10, 0.15, 0.25, 0.45]
            final_sc = np.average(ordered_scores, weights=weights)

            # 4. Bonus Consistencia (Si mejora respecto a la semana anterior)
            bonus = 0.0
            for k in range(1, 5):
                if ordered_scores[k] > ordered_scores[k - 1]: bonus += 0.2

            final_sc = max(0.0, min(10.0, final_sc + bonus))
            # ---------------------------------------------

            # Iconos
            is_sec = cached_imgs.get(SECTOR_IMG_MAP.get(sec, "")) or ""
            is_reg = cached_imgs.get(reg) or ""
            is_pro = ""
            if tick in MY_PORTFOLIO:
                is_pro = cached_imgs.get("PENGUIN") or ""
            elif "INDICE" in sec or "WORLD" in sec:
                is_pro = cached_imgs.get("PIRANHA") or ""

            # Emojis Color POS
            pos_label = rrg_data[0][0]
            pos_display = pos_label
            if "Leading" in pos_label:
                pos_display = "🟢 Lead"
            elif "Weakening" in pos_label:
                pos_display = "🟡 Weak"
            elif "Lagging" in pos_label:
                pos_display = "🔴 Lagg"
            elif "Improving" in pos_label:
                pos_display = "🔵 Impr"

            rows.append({
                "Ver": (tick in MY_PORTFOLIO),
                "Img_S": is_sec, "Img_R": is_reg, "Img_P": is_pro,
                "Ticker": tick, "Sector": sec, "Region": reg,
                "Score": final_sc,
                "% Hoy": day_pct, "% 3M": m3_pct,
                "POS": pos_display,
                "STR": rrg_data[0][1], "MOM": rrg_data[0][2]
            })
        except:
            continue

    bar.empty()
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)
        df.insert(1, "#", range(1, len(df) + 1))
    return df, history_dict


# --- 4. INTERFAZ ---
st.header("📊 RRG Pro Mobile")
df, rrg_hist = load_data_and_history()

if df.empty:
    st.error("Error de datos.")
    st.stop()

st.caption("Marca 'Ver' para añadir/quitar del gráfico. Tu cartera está marcada por defecto.")

# Configuración Columnas
col_conf = {
    "Ver": st.column_config.CheckboxColumn("Ver", width="small"),
    "#": st.column_config.NumberColumn("#", width="small", format="%d"),
    "Img_S": st.column_config.ImageColumn("Sec", width="small"),
    "Img_R": st.column_config.ImageColumn("Reg", width="small"),
    "Img_P": st.column_config.ImageColumn("👤", width="small"),
    "Score": st.column_config.NumberColumn("Nota", format="%.1f"),
    "% Hoy": st.column_config.NumberColumn("% Hoy", format="%.2f%%"),
    "% 3M": st.column_config.NumberColumn("% 3M", format="%.2f%%"),
    "STR": st.column_config.NumberColumn(format="%.2f"),
    "MOM": st.column_config.NumberColumn(format="%.2f"),
}

visible_cols = ["Ver", "#", "Img_S", "Img_R", "Img_P", "Ticker", "Score", "% Hoy", "% 3M", "POS", "STR", "MOM"]

# TABLA EDITABLE
edited_df = st.data_editor(
    df,
    use_container_width=True,
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
    fig, ax = plt.subplots(figsize=(10, 10))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22',
              '#17becf']
    all_x, all_y = [], []

    for i, t in enumerate(plot_tickers):
        raw = rrg_hist.get(t, [])
        if not raw: continue

        pts = [(r[1], r[2]) for r in raw if r[0] != "Error"]
        if len(pts) < 2: continue

        # Ordenar cronológico para pintar traza: 4W -> Hoy
        pts_chron = list(reversed(pts))
        xs = np.array([p[0] for p in pts_chron])
        ys = np.array([p[1] for p in pts_chron])

        all_x.extend(xs)
        all_y.extend(ys)

        # Spline
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

        # Cabeza
        row_info = edited_df[edited_df['Ticker'] == t].iloc[0]
        label = f" {row_info['Sector']} {row_info['Region']}"
        fw, ec = 'normal', c
        if t in MY_PORTFOLIO:
            label = "🐧" + label
            fw, ec = 'bold', 'black'

        ax.scatter(xs[-1], ys[-1], s=120, color=c, edgecolors=ec, zorder=5)
        ax.text(xs[-1], ys[-1], label, color=c, fontweight=fw, fontsize=9)

    # Ejes
    lim = 5
    if all_x: lim = max(5, max(np.max(np.abs(all_x)), np.max(np.abs(all_y))) * 1.15)

    ax.set_xlim(-lim, lim);
    ax.set_ylim(-lim, lim)
    ax.add_patch(Rectangle((0, 0), lim, lim, color='#e8f5e9', alpha=0.3))
    ax.add_patch(Rectangle((0, -lim), lim, lim, color='#fffde7', alpha=0.3))
    ax.add_patch(Rectangle((-lim, -lim), lim, lim, color='#ffebee', alpha=0.3))
    ax.add_patch(Rectangle((-lim, 0), lim, lim, color='#e3f2fd', alpha=0.3))
    ax.axhline(0, c='gray');
    ax.axvline(0, c='gray')
    ax.text(lim * 0.9, lim * 0.9, "LEADING", color='green', ha='right', fontweight='bold')
    ax.text(lim * 0.9, -lim * 0.9, "WEAKENING", color='orange', ha='right', va='bottom', fontweight='bold')
    ax.text(-lim * 0.9, -lim * 0.9, "LAGGING", color='red', ha='left', va='bottom', fontweight='bold')
    ax.text(-lim * 0.9, lim * 0.9, "IMPROVING", color='blue', ha='left', fontweight='bold')

    st.pyplot(fig)
else:
    st.info("Selecciona activos.")