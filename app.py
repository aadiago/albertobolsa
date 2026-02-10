import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.interpolate import make_interp_spline
import base64
import os

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS ---
st.set_page_config(layout="wide", page_title="RRG Pro Mobile", page_icon="🐧")

# CSS REFORZADO PARA CENTRAR TODO (Headers, Celdas y Números)
st.markdown("""
    <style>
    /* 1. Centrar Encabezados */
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        justify-content: center !important;
        text-align: center !important;
    }

    /* 2. Centrar Celdas (incluye texto y números) */
    div[data-testid="stDataFrame"] div[role="gridcell"] {
        justify-content: center !important;
        text-align: center !important;
        display: flex !important;
    }

    /* 3. Centrar contenido interno de las celdas (divs internos) */
    div[data-testid="stDataFrame"] div[role="gridcell"] > div {
        justify-content: center !important;
        text-align: center !important;
        margin: auto !important;
    }

    /* 4. Centrar imágenes específicamente */
    div[data-testid="stDataFrame"] td img {
        display: block;
        margin-left: auto;
        margin-right: auto;
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

# TU CARTERA
MY_PORTFOLIO = [
    "QDVF.DE", "ZPRX.DE", "XDWI.DE",
    "SPYU.DE", "XDWM.DE", "CEMS.DE"
]

# MAPA DE IMÁGENES
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

# LISTA DE ACTIVOS
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


# --- 3. FUNCIONES AUXILIARES ---

def get_image_base64(path):
    """Convierte imagen a base64. Retorna None si no existe."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def calculate_rrg_zscore(p_ticker, p_bench, offset):
    try:
        df = pd.DataFrame({'t': p_ticker, 'b': p_bench}).dropna()
        min_req = RRG_PERIOD_TREND + abs(offset) + 2
        if len(df) < min_req: return ("Error", 0.0, 0.0)

        rs_series = (df['t'] / df['b']) * 100
        rs_cut = rs_series if offset == 0 else rs_series.iloc[:offset]

        mean_long = rs_cut.rolling(window=RRG_PERIOD_TREND).mean().iloc[-1]
        std_long = rs_cut.rolling(window=RRG_PERIOD_TREND).std().iloc[-1]
        current_rs = rs_cut.iloc[-1]
        if std_long == 0: std_long = 1
        strength_x = ((current_rs - mean_long) / std_long) * 10

        mean_short = rs_cut.rolling(window=RRG_PERIOD_MOM).mean().iloc[-1]
        std_short = rs_cut.rolling(window=RRG_PERIOD_MOM).std().iloc[-1]
        if std_short == 0: std_short = 1
        momentum_y = ((current_rs - mean_short) / std_short) * 10

        label = "Improving"
        if strength_x >= 0 and momentum_y >= 0:
            label = "Leading"
        elif strength_x >= 0 and momentum_y < 0:
            label = "Weakening"
        elif strength_x < 0 and momentum_y < 0:
            label = "Lagging"

        return (label, float(strength_x), float(momentum_y))
    except:
        return ("Error", 0.0, 0.0)


@st.cache_data(ttl=3600)
def load_data_and_history():
    try:
        bench_obj = yf.Ticker(BENCHMARK)
        bench_hist = bench_obj.history(period="2y")
        if bench_hist.empty: return pd.DataFrame(), {}
        bench_series = bench_hist['Close'].resample('W-FRI').last().dropna().tz_localize(None)
    except:
        return pd.DataFrame(), {}

    rows = []
    history_dict = {}

    # Pre-cargar imágenes
    cached_images = {}
    for k, v in IMG_PATHS.items():
        cached_images[k] = get_image_base64(v)

    progress_text = "Analizando mercado..."
    my_bar = st.progress(0, text=progress_text)
    total = len(ASSETS)

    for i, (sector, region, ticker) in enumerate(ASSETS):
        my_bar.progress((i + 1) / total, text=f"Procesando {ticker}...")
        try:
            t_obj = yf.Ticker(ticker)
            t_hist = t_obj.history(period="2y")
            if t_hist.empty: continue

            try:
                daily_close = t_hist['Close']
                d_curr, d_prev = float(daily_close.iloc[-1]), float(daily_close.iloc[-2])
                change_daily_pct = ((d_curr / d_prev) - 1) * 100
            except:
                change_daily_pct = 0.0

            t_series = t_hist['Close'].resample('W-FRI').last().dropna().tz_localize(None)
            try:
                curr = float(t_series.iloc[-1])
                prev_3m = float(t_series.iloc[-14]) if len(t_series) >= 14 else curr
                change_3m = ((curr / prev_3m) - 1) * 100
            except:
                change_3m = 0.0

            rrg_data = []
            for off in [0, OFFSET_1W, OFFSET_2W, OFFSET_3W, OFFSET_4W]:
                rrg_data.append(calculate_rrg_zscore(t_series, bench_series, off))

            history_dict[ticker] = rrg_data

            def get_score(rd):
                return 5.0 + (rd[1] * 0.12) + (rd[2] * 0.04) if rd[0] != "Error" else 0.0

            scores = [get_score(rrg_data[4]), get_score(rrg_data[3]), get_score(rrg_data[2]), get_score(rrg_data[1]),
                      get_score(rrg_data[0])]
            weights = [0.05, 0.10, 0.15, 0.25, 0.45]
            weighted_avg = np.average(scores, weights=weights)
            bonus = 0.0
            for k in range(1, 5):
                if scores[k] > scores[k - 1]: bonus += 0.2
            final_score = max(0.0, min(10.0, weighted_avg + bonus))

            # ICONOS (VACÍO "" SI ES NONE)
            img_sec_key = SECTOR_IMG_MAP.get(sector, "")
            icon_sector = cached_images.get(img_sec_key)
            if icon_sector is None: icon_sector = ""

            icon_region = cached_images.get(region)
            if icon_region is None: icon_region = ""

            icon_profile = ""
            if ticker in MY_PORTFOLIO:
                res = cached_images.get("PENGUIN")
                if res: icon_profile = res
            elif sector == "INDICE" or sector == "MSCI WORLD EW":
                res = cached_images.get("PIRANHA")
                if res: icon_profile = res

            is_selected = ticker in MY_PORTFOLIO

            row = {
                "Ver": is_selected,
                "Img_S": icon_sector,
                "Img_R": icon_region,
                "Img_P": icon_profile,
                "Ticker": ticker,
                "Sector": sector,
                "Region": region,
                "Score": final_score,
                "% Hoy": change_daily_pct,
                "% 3M": change_3m,
                "POS": rrg_data[0][0], "STR": rrg_data[0][1], "MOM": rrg_data[0][2],
            }
            rows.append(row)

        except:
            continue

    my_bar.empty()
    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)
        df.insert(1, "#", range(1, len(df) + 1))

    return df, history_dict


# --- 4. INTERFAZ PRINCIPAL ---

st.header("📊 RRG Pro Mobile")

df, rrg_history = load_data_and_history()

if df.empty:
    st.error("Error cargando datos. Verifica tu conexión o las imágenes .png.")
    st.stop()

# --- TABLA EDITABLE ---
st.caption("Marca 'Ver' para graficar. Datos centrados y ranking fijo.")

column_config = {
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

# Columnas visibles (Ticker está oculto en la vista, pero disponible en datos)
# Nota: Si ocultas el Ticker, no sabrás qué activo es. Lo añadiré al final o puedes dejarlo.
# Dejaré "Ticker" visible para que sepas qué es, pero la gráfica usará Sector+Region.
cols_visible = ["Ver", "#", "Img_S", "Img_R", "Img_P", "Ticker", "Score", "% Hoy", "% 3M", "POS", "STR", "MOM"]

edited_df = st.data_editor(
    df,
    use_container_width=True,
    hide_index=True,
    column_order=cols_visible,
    column_config=column_config,
    disabled=["#", "Img_S", "Img_R", "Img_P", "Ticker", "Score", "% Hoy", "% 3M", "POS", "STR", "MOM"],
    height=500
)

# --- GRÁFICA ---

subset_to_plot = edited_df[edited_df["Ver"] == True]
tickers_to_plot = subset_to_plot["Ticker"].tolist()

st.divider()
st.subheader(f"📈 Gráfico RRG ({len(tickers_to_plot)} activos)")

if not tickers_to_plot:
    st.warning("Selecciona activos en la tabla de arriba.")
else:
    fig, ax = plt.subplots(figsize=(10, 10))

    all_x, all_y = [], []
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22',
              '#17becf']

    for i, ticker in enumerate(tickers_to_plot):
        rrg_data = rrg_history.get(ticker, [])
        if not rrg_data: continue

        points = []
        for k in [4, 3, 2, 1, 0]:
            if rrg_data[k][0] != "Error":
                points.append((rrg_data[k][1], rrg_data[k][2]))
                all_x.append(rrg_data[k][1])
                all_y.append(rrg_data[k][2])

        if len(points) < 2: continue

        xs = np.array([p[0] for p in points])
        ys = np.array([p[1] for p in points])

        plot_x, plot_y = xs, ys
        if len(points) >= 3:
            try:
                t_raw = np.arange(len(xs))
                t_dense = np.linspace(0, len(xs) - 1, 100)
                spl_x = make_interp_spline(t_raw, xs, k=2)
                spl_y = make_interp_spline(t_raw, ys, k=2)
                plot_x, plot_y = spl_x(t_dense), spl_y(t_dense)
            except:
                pass

        col = colors[i % len(colors)]

        # Plot Línea
        ax.plot(plot_x, plot_y, color=col, linewidth=2, alpha=0.8)
        ax.scatter(xs[:-1], ys[:-1], s=20, color=col, alpha=0.6)

        # --- ETIQUETADO PERSONALIZADO (NO TICKER) ---
        # 1. Buscar la fila correspondiente en el dataframe editado
        row_info = edited_df[edited_df['Ticker'] == ticker].iloc[0]

        # 2. Extraer Sector y Región
        sec_name = row_info['Sector']
        reg_name = row_info['Region']

        # 3. Crear texto: "UTILITIES USA"
        label_text = f" {sec_name} {reg_name}"

        # Estilo cabeza
        edge_c = 'black' if ticker in MY_PORTFOLIO else col
        ax.scatter(xs[-1], ys[-1], s=120, color=col, edgecolors=edge_c, zorder=5)

        # Estilo texto
        font_w = 'bold' if ticker in MY_PORTFOLIO else 'normal'
        if ticker in MY_PORTFOLIO: label_text = "🐧" + label_text

        ax.text(xs[-1], ys[-1], label_text, color=col, fontweight=font_w, fontsize=9)

    # Ejes
    if not all_x:
        limit = 5
    else:
        limit = max(max(abs(x) for x in all_x), max(abs(y) for y in all_y)) * 1.15
    if limit < 5: limit = 5

    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)

    # Fondo
    ax.add_patch(Rectangle((0, 0), limit, limit, color='#e8f5e9', alpha=0.3))
    ax.add_patch(Rectangle((0, -limit), limit, limit, color='#fffde7', alpha=0.3))
    ax.add_patch(Rectangle((-limit, -limit), limit, limit, color='#ffebee', alpha=0.3))
    ax.add_patch(Rectangle((-limit, 0), limit, limit, color='#e3f2fd', alpha=0.3))

    ax.axhline(0, color='gray', lw=1)
    ax.axvline(0, color='gray', lw=1)
    ax.text(limit * 0.9, limit * 0.9, "LEADING", color='green', ha='right', fontweight='bold')
    ax.text(limit * 0.9, -limit * 0.9, "WEAKENING", color='orange', ha='right', va='bottom', fontweight='bold')
    ax.text(-limit * 0.9, -limit * 0.9, "LAGGING", color='red', ha='left', va='bottom', fontweight='bold')
    ax.text(-limit * 0.9, limit * 0.9, "IMPROVING", color='blue', ha='left', fontweight='bold')

    st.pyplot(fig)