import re
import html
import time
from datetime import datetime, timezone
from urllib.parse import quote

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import feedparser
import requests
from deep_translator import GoogleTranslator

st.set_page_config(page_title="PRO Macro Terminal", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
#  BACKEND (INCHANGÉ) : UNIVERSE + load_all_data
# =====================================================================
UNIVERSE = {
    "🏛️ Taux & Banques Centrales": {
        "US 10Y Treasury": "^TNX",
        "US 2Y Treasury": "^IRX",
        "Eurozone 10Y (Proxy IGOV)": "IGOV",
        "Japon 10Y (Proxy JGBL)": "JGBL.L",
        "Intl Treasuries (BWX)": "BWX"
    },
    "🌍 Indices": {
        "S&P 500 (US)": "^GSPC",
        "Nasdaq 100 (Tech)": "^NDX",
        "Dow Jones": "^DJI",
        "Russell 2000 (Small Caps)": "^RUT",
        "Euro Stoxx 50": "^STOXX50E",
        "CAC 40 (France)": "^FCHI",
        "DAX 40 (Allemagne)": "^GDAXI",
        "FTSE 100 (UK)": "^FTSE",
        "SMI (Suisse)": "^SSMI",
        "Nikkei 225 (Japon)": "^N225",
        "Hang Seng (Hong Kong)": "^HSI",
        "CSI 300 (Proxy ASHR)": "ASHR",
        "Nifty 50 (Inde)": "^NSEI",
        "MSCI World (URTH)": "URTH",
        "MSCI Emerging (EEM)": "EEM"
    },
    "💱 Devises (Forex)": {
        "DXY (Dollar Index)": "DX-Y.NYB",
        "EUR/USD (Fiber)": "EURUSD=X",
        "GBP/USD (Cable)": "GBPUSD=X",
        "USD/JPY (Ninja)": "USDJPY=X",
        "USD/CHF (Refuge)": "USDCHF=X",
        "AUD/USD (Aussie)": "AUDUSD=X",
        "USD/CAD (Loonie)": "USDCAD=X",
        "USD/CNY (Yuan Onshore)": "USDCNY=X",
        "EUR/GBP": "EURGBP=X",
        "EUR/CHF": "EURCHF=X"
    },
    "🛢️ Matières Premières": {
        "Brent Crude (Europe)": "BZ=F",
        "WTI Crude (US)": "CL=F",
        "Or (Valeur Refuge)": "GC=F",
        "Argent (Silver)": "SI=F",
        "Cuivre (Dr. Copper)": "HG=F",
        "Gaz Naturel (US)": "NG=F",
        "Blé (Wheat)": "ZW=F",
        "Maïs (Corn)": "ZC=F",
        "Soja (Soybeans)": "ZS=F"
    },
    "🚀 Leaders & Mega-Caps": {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Nvidia": "NVDA",
        "Alphabet": "GOOGL",
        "Amazon": "AMZN",
        "Meta": "META",
        "TSMC": "TSM",
        "Novo Nordisk": "NVO",
        "LVMH (Luxe)": "MC.PA",
        "ASML (Semi-conducteurs)": "ASML.AS"
    },
    "🪙 Crypto-Actifs": {
        "Bitcoin (BTC)": "BTC-USD",
        "Ethereum (ETH)": "ETH-USD",
        "Solana (SOL)": "SOL-USD",
        "Binance Coin (BNB)": "BNB-USD",
        "Ripple (XRP)": "XRP-USD"
    },
    "🚨 Volatilité & Crédit": {
        "VIX (Indice de la Peur)": "^VIX",
        "MOVE (Volatilité Taux)": "^MOVE",
        "High Yield (Risque Crédit)": "HYG",
        "Investment Grade (Dette)": "LQD"
    }
}


@st.cache_data(ttl=300)
def load_all_data():
    all_tickers = []
    for cat in UNIVERSE.values():
        all_tickers.extend(cat.values())
    df = yf.download(all_tickers, period="3mo", threads=True, progress=False)
    return df['Close']


# =====================================================================
#  DESIGN SYSTEM
# =====================================================================
UP, DN, A1, A2 = "#34D399", "#FB7185", "#6366F1", "#22D3EE"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
:root{--up:#34D399;--dn:#FB7185;--a1:#6366F1;--a2:#22D3EE;--bd:rgba(255,255,255,.09);--mut:#8B93A7}
html,body,.stApp,[class*="css"]{font-family:'Inter',sans-serif}
.stApp{color:#E8ECF5;background:
 radial-gradient(900px 520px at 6% -8%,rgba(99,102,241,.24),transparent 60%),
 radial-gradient(800px 520px at 100% 0%,rgba(34,211,238,.15),transparent 60%),
 radial-gradient(700px 600px at 50% 125%,rgba(168,85,247,.14),transparent 60%),#05060A}
header[data-testid="stHeader"]{background:transparent}
#MainMenu,footer{visibility:hidden}
.block-container{padding-top:2.2rem;max-width:1400px}
hr{border-color:var(--bd)!important}

/* Sidebar */
section[data-testid="stSidebar"]{background:rgba(10,12,20,.78);backdrop-filter:blur(24px);border-right:1px solid var(--bd)}
.brand{display:flex;align-items:center;gap:12px;margin:6px 0 4px}
.brand-logo{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(135deg,var(--a1),var(--a2));box-shadow:0 0 24px rgba(99,102,241,.55)}
.brand-t{font-weight:800;letter-spacing:.5px;font-size:1.05rem;color:#fff}
.brand-s{font-size:.7rem;color:var(--mut);letter-spacing:2px;text-transform:uppercase}
.live{display:inline-flex;align-items:center;gap:8px;margin:14px 0 22px;padding:6px 12px;border-radius:99px;background:rgba(52,211,153,.08);border:1px solid rgba(52,211,153,.25);color:#6EE7B7;font-size:.75rem;font-family:'JetBrains Mono',monospace}
.live i{width:7px;height:7px;border-radius:50%;background:var(--up);box-shadow:0 0 0 0 rgba(52,211,153,.7);animation:pulse 1.8s infinite}
@keyframes pulse{70%{box-shadow:0 0 0 8px rgba(52,211,153,0)}100%{box-shadow:0 0 0 0 rgba(52,211,153,0)}}
.navlab{font-size:.68rem;letter-spacing:2px;color:#5B6479;text-transform:uppercase;margin:0 0 8px 6px}
section[data-testid="stSidebar"] div[role="radiogroup"]{gap:4px}
section[data-testid="stSidebar"] div[role="radiogroup"]>label{padding:10px 14px;border-radius:12px;border:1px solid transparent;transition:.25s;cursor:pointer;width:100%}
section[data-testid="stSidebar"] div[role="radiogroup"]>label>div:first-child{display:none}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:hover{background:rgba(255,255,255,.05)}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked){background:linear-gradient(135deg,rgba(99,102,241,.30),rgba(34,211,238,.12));border-color:rgba(129,140,248,.45);box-shadow:0 0 22px rgba(99,102,241,.25)}
section[data-testid="stSidebar"] div[role="radiogroup"]>label p{font-size:.92rem;font-weight:500;color:#AEB6CA;display:flex;align-items:center}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked) p{color:#fff}

/* Hero */
.hero{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap;margin-bottom:26px;padding-bottom:20px;border-bottom:1px solid var(--bd)}
.eyebrow{font-size:.72rem;letter-spacing:3px;text-transform:uppercase;color:var(--a2);font-weight:600}
.hero h1{margin:4px 0 4px;padding:0;font-size:2.4rem;font-weight:800;letter-spacing:-.5px;background:linear-gradient(90deg,#fff 30%,#A5B4FC 70%,var(--a2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero p{margin:0;color:var(--mut);font-size:.95rem}
.pills{display:flex;gap:10px;flex-wrap:wrap}
.pill{padding:7px 14px;border-radius:99px;font-size:.78rem;font-weight:600;background:rgba(255,255,255,.05);border:1px solid var(--bd);color:#CBD3E6;font-family:'JetBrains Mono',monospace}
.pill.up{color:var(--up);border-color:rgba(52,211,153,.35);background:rgba(52,211,153,.08)}
.pill.dn{color:var(--dn);border-color:rgba(251,113,133,.35);background:rgba(251,113,133,.08)}

/* Metric cards (st.container key=card_*) */
[class*="st-key-card_"]{background:linear-gradient(160deg,rgba(255,255,255,.065),rgba(255,255,255,.015));border:1px solid var(--bd);border-radius:18px;padding:16px 16px 4px;backdrop-filter:blur(14px);box-shadow:0 10px 30px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.07);transition:transform .3s,border-color .3s,box-shadow .3s;margin-bottom:8px;gap:0!important}
[class*="st-key-card_"]:hover{transform:translateY(-4px);border-color:rgba(129,140,248,.6);box-shadow:0 18px 44px rgba(99,102,241,.25),inset 0 1px 0 rgba(255,255,255,.1)}
.mt{color:var(--mut);font-size:.74rem;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mrow{display:flex;align-items:center;justify-content:space-between;gap:8px}
.mv{font-family:'JetBrains Mono',monospace;font-size:1.65rem;font-weight:700;color:#fff;letter-spacing:-.5px}
.chip{font-family:'JetBrains Mono',monospace;font-size:.8rem;font-weight:700;padding:4px 10px;border-radius:99px}
.chip.up{color:var(--up);background:rgba(52,211,153,.12);box-shadow:0 0 14px rgba(52,211,153,.15)}
.chip.dn{color:var(--dn);background:rgba(251,113,133,.12);box-shadow:0 0 14px rgba(251,113,133,.15)}
.sub{font-size:.72rem;color:#6B7389;margin-top:6px}
.sub b.up{color:var(--up)}.sub b.dn{color:var(--dn)}

/* News */
.sec{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin:8px 0 18px}
.sec h2{margin:0;padding:0;font-size:1.45rem;font-weight:700;color:#fff}
.sec span{color:var(--mut);font-size:.85rem}
.nc{display:block;text-decoration:none!important;position:relative;overflow:hidden;padding:20px 22px;border-radius:20px;margin-bottom:14px;min-height:150px;background:linear-gradient(150deg,rgba(255,255,255,.07),rgba(255,255,255,.015));border:1px solid var(--bd);box-shadow:0 12px 34px rgba(0,0,0,.4);transition:.3s}
.nc::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--c),transparent)}
.nc::after{content:"";position:absolute;right:-60px;top:-60px;width:180px;height:180px;border-radius:50%;background:radial-gradient(circle,var(--c),transparent 70%);opacity:.16}
.nc:hover{transform:translateY(-4px);border-color:var(--c);box-shadow:0 18px 44px rgba(0,0,0,.5),0 0 30px -6px var(--c)}
.nc.big{min-height:190px;padding:28px 30px}
.nc-top{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.rank{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.5rem;color:var(--c);opacity:.95}
.tag{font-size:.7rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:4px 10px;border-radius:99px;color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);border:1px solid color-mix(in srgb,var(--c) 40%,transparent)}
.nc-t{color:#fff;font-weight:700;font-size:1.08rem;line-height:1.4}
.nc.big .nc-t{font-size:1.6rem;line-height:1.3;max-width:900px}
.nc-m{margin-top:14px;color:#6B7389;font-size:.78rem;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.dots{letter-spacing:2px;color:var(--c)}
.btn{display:inline-flex;align-items:center;gap:8px;text-decoration:none!important;padding:11px 20px;border-radius:12px;font-weight:600;font-size:.88rem;color:#fff!important;background:linear-gradient(135deg,var(--a1),#8B5CF6 60%,var(--a2));box-shadow:0 8px 26px rgba(99,102,241,.45);transition:.25s}
.btn:hover{transform:translateY(-2px);box-shadow:0 12px 34px rgba(99,102,241,.65)}
.fx{display:flex;align-items:center;gap:14px;text-decoration:none!important;padding:13px 18px;border-radius:14px;margin-bottom:8px;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.06);transition:.25s}
.fx:hover{background:rgba(99,102,241,.1);border-color:rgba(129,140,248,.4);transform:translateX(4px)}
.fx-t{font-family:'JetBrains Mono',monospace;color:#6B7389;font-size:.78rem;min-width:92px}
.fx-x{color:#E2E8F0;font-weight:500;font-size:.95rem;flex:1;line-height:1.35}
.fx-a{color:var(--a2);font-weight:700}

/* Knowledge base */
.kc{padding:20px;border-radius:18px;margin-bottom:14px;background:linear-gradient(155deg,rgba(255,255,255,.065),rgba(255,255,255,.015));border:1px solid var(--bd);box-shadow:0 10px 30px rgba(0,0,0,.35);transition:.3s;height:calc(100% - 14px)}
.kc:hover{border-color:rgba(129,140,248,.5);box-shadow:0 14px 38px rgba(99,102,241,.2)}
.kc h4{margin:0 0 4px;font-size:.72rem;letter-spacing:2px;text-transform:uppercase;color:var(--mut);font-weight:600}
.kc .big{font-family:'JetBrains Mono',monospace;font-size:1.9rem;font-weight:700;background:linear-gradient(90deg,#fff,var(--c,#A5B4FC));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:12px}
.kc p{margin:0 0 10px;color:var(--mut);font-size:.85rem}
.co{display:inline-block;margin:3px 4px 3px 0;padding:6px 12px;border-radius:10px;font-size:.84rem;font-weight:600;color:#E8ECF5;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1)}
.tip{position:relative;cursor:help}
.tip:hover{border-color:var(--a2);color:#fff}
.tip:hover::after{content:attr(data-tip);position:absolute;left:50%;bottom:calc(100% + 8px);transform:translateX(-50%);width:max-content;max-width:230px;padding:8px 12px;border-radius:10px;font-size:.75rem;font-weight:500;line-height:1.35;color:#E8ECF5;background:#11142A;border:1px solid rgba(129,140,248,.5);box-shadow:0 10px 30px rgba(0,0,0,.6);z-index:50}
.rk{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.06);font-size:.92rem}
.rk:last-child{border:0}
.rk .n{width:28px;height:28px;border-radius:9px;display:grid;place-items:center;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:.8rem;background:rgba(99,102,241,.18);color:#A5B4FC}
.rk .n.g{background:rgba(250,204,21,.18);color:#FACC15}.rk .n.s{background:rgba(203,213,225,.15);color:#CBD5E1}.rk .n.b{background:rgba(251,146,60,.18);color:#FB923C}
.rk em{margin-left:auto;font-style:normal;color:var(--mut);font-size:.8rem}

/* Tabs / expanders */
button[data-baseweb="tab"]{font-weight:600;color:#8B93A7;padding:10px 16px}
button[data-baseweb="tab"][aria-selected="true"]{color:#fff}
div[data-baseweb="tab-highlight"]{background:linear-gradient(90deg,var(--a1),var(--a2))!important;height:3px;border-radius:3px}
div[data-baseweb="tab-border"]{background:var(--bd)!important}
[data-testid="stExpander"]{border:1px solid var(--bd)!important;border-radius:14px!important;background:rgba(255,255,255,.035);margin-bottom:10px;overflow:hidden}
[data-testid="stExpander"] summary:hover{background:rgba(99,102,241,.08)}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- Icônes SVG (style Lucide) pour la navigation, dans l'ordre des options ---
ICONS = [
    '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
    '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
    '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
    '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/>',
    '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
]


def icon_css():
    out = "<style>"
    for i, paths in enumerate(ICONS, 1):
        svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' "
               "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>" + paths + "</svg>")
        uri = "data:image/svg+xml," + quote(svg)
        out += (f'section[data-testid="stSidebar"] div[role="radiogroup"]>label:nth-child({i}) p::before'
                f'{{content:"";display:inline-block;width:18px;height:18px;margin-right:12px;background:currentColor;'
                f'-webkit-mask:url("{uri}") center/contain no-repeat;mask:url("{uri}") center/contain no-repeat}}')
    return out + "</style>"


st.markdown(icon_css(), unsafe_allow_html=True)


# =====================================================================
#  HELPERS UI
# =====================================================================
def clean_label(k):
    return re.sub(r"^[^\w]+", "", k).strip()


def hex_rgba(h, a):
    h = h.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def show(fig, key=None):
    cfg = {'displayModeBar': False}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg, key=key)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config=cfg, key=key)


def hero(eyebrow, title, sub, pills=""):
    st.markdown(f'<div class="hero"><div><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p></div>'
                f'<div class="pills">{pills}</div></div>', unsafe_allow_html=True)


def sec(title, sub, right=""):
    st.markdown(f'<div class="sec"><div><h2>{title}</h2><span>{sub}</span></div><div>{right}</div></div>',
                unsafe_allow_html=True)


def mini_chart(series, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values, mode='lines',
        line=dict(color=color, width=2.4, shape='spline', smoothing=.6),
        fill='tozeroy', fillcolor=hex_rgba(color, .14),
        hovertemplate="%{x|%d %b} · <b>%{y:,.2f}</b><extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[series.index[-1]], y=[series.values[-1]], mode='markers',
        marker=dict(color=color, size=8, line=dict(color='rgba(255,255,255,.9)', width=2)), hoverinfo='skip'))
    lo, hi = float(series.min()), float(series.max())
    pad = (hi - lo) * .12 or 1
    fig.update_layout(
        margin=dict(l=0, r=0, t=4, b=0), height=86, showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=False, visible=False, range=[lo - pad, hi + pad]),
        hovermode='x unified', hoverlabel=dict(bgcolor="#11142A", font=dict(family="Inter", color="#fff", size=12), bordercolor=color))
    return fig


def gauge(v, title, color=A1, rng=(0, 100), suffix="%", height=215):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=v,
        number=dict(suffix=suffix, font=dict(size=34, color="#fff", family="JetBrains Mono")),
        title=dict(text=title, font=dict(size=13, color="#8B93A7")),
        gauge=dict(axis=dict(range=list(rng), tickcolor="#4B5367", tickfont=dict(size=10, color="#6B7389")),
                   bar=dict(color=color, thickness=.3), bgcolor="rgba(255,255,255,.04)", borderwidth=0)))
    fig.update_layout(height=height, margin=dict(l=24, r=24, t=44, b=0),
                      paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Inter"))
    return fig


# =====================================================================
#  SIDEBAR
# =====================================================================
st.sidebar.markdown(
    '<div class="brand"><div class="brand-logo"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" '
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 17 9 11 13 15 21 7"/>'
    '<polyline points="15 7 21 7 21 13"/></svg></div><div><div class="brand-t">MACRO TERMINAL</div>'
    '<div class="brand-s">Global Markets</div></div></div>'
    f'<div class="live"><i></i>LIVE · {datetime.now(timezone.utc).strftime("%H:%M UTC")}</div>'
    '<div class="navlab">Navigation</div>', unsafe_allow_html=True)
options = list(UNIVERSE.keys()) + ["📰 Actualités Macro (FR)", "📚 Base de Connaissances"]
category = st.sidebar.radio("NAVIGATION", options, format_func=clean_label, label_visibility="collapsed")
st.sidebar.markdown('<div style="margin-top:30px;font-size:.7rem;color:#4B5367;line-height:1.5">Données : Yahoo Finance · cache 5 min<br>Informations à but pédagogique, pas un conseil en investissement.</div>',
                    unsafe_allow_html=True)

# =====================================================================
#  PAGE : DONNÉES DE MARCHÉ
# =====================================================================
if category in UNIVERSE:
    with st.spinner("Synchronisation avec les marchés..."):
        df_close = load_all_data()

    assets = UNIVERSE[category]
    rows = []
    for name, ticker in assets.items():
        if ticker in df_close.columns:
            s = df_close[ticker].dropna()
            if len(s) >= 2:
                rows.append((name, ticker, s))

    ups = sum(1 for _, _, s in rows if s.iloc[-1] >= s.iloc[-2])
    downs = len(rows) - ups
    hero("Marchés en temps réel", clean_label(category),
         f"{len(assets)} instruments suivis · variation vs clôture précédente",
         f'<span class="pill up">▲ {ups} en hausse</span><span class="pill dn">▼ {downs} en baisse</span>')

    cols = st.columns(4)
    for i, (name, ticker) in enumerate(assets.items()):
        with cols[i % 4]:
            if ticker in df_close.columns:
                series = df_close[ticker].dropna()
                if len(series) >= 2:
                    curr, prev = series.iloc[-1], series.iloc[-2]
                    pct = ((curr - prev) / prev) * 100
                    base30 = series.tail(30).iloc[0]
                    p30 = ((curr - base30) / base30) * 100

                    is_rate = "10Y" in name or "2Y" in name or "VIX" in name or "MOVE" in name
                    val_str = f"{curr:.2f}%" if is_rate and curr < 150 else f"{curr:,.2f}"
                    inverse = "VIX" in name or "MOVE" in name
                    good = (pct < 0) if inverse else (pct >= 0)
                    good30 = (p30 < 0) if inverse else (p30 >= 0)
                    color = UP if good else DN
                    cls, cls30 = ("up" if good else "dn"), ("up" if good30 else "dn")
                    arrow = "▲" if pct >= 0 else "▼"

                    with st.container(key=f"card_{i}"):
                        st.markdown(
                            f'<div class="mt">{html.escape(name)}</div>'
                            f'<div class="mrow"><span class="mv">{val_str}</span><span class="chip {cls}">{arrow} {pct:+.2f}%</span></div>'
                            f'<div class="sub">Tendance 30 j · <b class="{cls30}">{p30:+.1f}%</b></div>',
                            unsafe_allow_html=True)
                        show(mini_chart(series.tail(30), color), key=f"mini_{i}")
                else:
                    st.warning(f"{name} : Données insuffisantes")
            else:
                st.warning(f"{name} : Hors ligne")

# =====================================================================
#  PAGE : ACTUALITÉS
# =====================================================================
elif category == "📰 Actualités Macro (FR)":
    FEED = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
    AGGREGATOR = "https://www.tradingview.com/news/"
    TAGS = {
        "Banques centrales": ("#818CF8", 5, ["fed", "federal reserve", "ecb", "boj", "powell", "lagarde", "rate cut", "rate hike", "interest rate", "central bank", "fomc", "bank of england"]),
        "Inflation & Emploi": ("#FBBF24", 4, ["inflation", "cpi", "pce", "jobs", "payroll", "unemployment", "gdp", "recession", "layoffs"]),
        "Géopolitique": ("#FB7185", 4, ["war", "sanction", "iran", "russia", "ukraine", "china", "israel", "tariff", "trade war", "middle east", "taiwan", "election", "trump"]),
        "Énergie": ("#FB923C", 3, ["oil", "crude", "natural gas", "opec", "energy", "brent"]),
        "Marchés": ("#22D3EE", 2, ["stocks", "s&p", "nasdaq", "dow", "yields", "treasury", "dollar", "bond", "bitcoin", "earnings"]),
    }

    @st.cache_data(ttl=600, show_spinner=False)
    def fetch_news():
        r = requests.get(FEED, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        feed = feedparser.parse(r.content)
        out = []
        for e in feed.entries[:40]:
            ts = time.mktime(e.published_parsed) if getattr(e, "published_parsed", None) else 0
            out.append({"title": e.title, "link": e.link, "ts": ts,
                        "summary": re.sub(r"<[^>]+>", "", getattr(e, "summary", ""))})
        return out

    @st.cache_data(ttl=86400, show_spinner=False)
    def fr(text):
        try:
            return GoogleTranslator(source='auto', target='fr').translate(text) or text
        except Exception:
            return text

    def score(n):
        txt = (n["title"] + " " + n["summary"]).lower()
        total, best, best_w = 0, "Marchés", 0
        for tag, (_, w, kws) in TAGS.items():
            hits = sum(1 for k in kws if re.search(r"\b" + re.escape(k), txt))
            if hits:
                total += w * min(hits, 2)
                if w * hits > best_w:
                    best, best_w = tag, w * hits
        return total, best

    def fmt(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d/%m · %H:%M UTC") if ts else "—"

    hero("Intelligence de marché", "Actualités Macro",
         "Sélection automatique des événements à plus fort impact · traduction française",
         f'<span class="pill">Source · CNBC</span>')

    try:
        with st.spinner("Chargement et traduction des actualités..."):
            news = []
            for n in fetch_news():
                n = dict(n)
                n["score"], n["tag"] = score(n)
                news.append(n)
            top5 = sorted(news, key=lambda n: (n["score"], n["ts"]), reverse=True)[:5]
            top_links = {n["link"] for n in top5}
            flux = sorted([n for n in news if n["link"] not in top_links], key=lambda n: n["ts"], reverse=True)[:15]
            for n in top5 + flux:
                n["fr"] = fr(n["title"])

        if not news:
            st.warning("Aucune actualité trouvée.")
        else:
            # ---------- SECTION A ----------
            sec("Le Résumé de la Semaine", "Top 5 · classé par impact macro & géopolitique estimé (banques centrales, inflation, conflits, énergie)")

            def card(n, rank, big=False):
                c = TAGS[n["tag"]][0]
                dots = min(5, 1 + n["score"] // 3)
                return (f'<a class="nc{" big" if big else ""}" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank">'
                        f'<div class="nc-top"><span class="rank">0{rank}</span><span class="tag">{n["tag"]}</span></div>'
                        f'<div class="nc-t">{html.escape(n["fr"])}</div>'
                        f'<div class="nc-m"><span>{fmt(n["ts"])}</span><span>·</span><span>CNBC</span><span>·</span>'
                        f'<span>Impact <span class="dots">{"●" * dots}{"○" * (5 - dots)}</span></span></div></a>')

            st.markdown(card(top5[0], 1, big=True), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            for j, n in enumerate(top5[1:], 2):
                with (c1 if j % 2 == 0 else c2):
                    st.markdown(card(n, j), unsafe_allow_html=True)

            # ---------- SECTION B ----------
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            sec("Le Flux du Jour", "Dernières publications, de la plus récente à la plus ancienne",
                f'<a class="btn" href="{AGGREGATOR}" target="_blank">Toutes les infos en temps réel '
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg></a>')
            rows_html = ""
            for n in flux:
                c = TAGS[n["tag"]][0]
                rows_html += (f'<a class="fx" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank">'
                              f'<span class="fx-t">{fmt(n["ts"])}</span><span class="tag" style="--c:{c}">{n["tag"]}</span>'
                              f'<span class="fx-x">{html.escape(n["fr"])}</span><span class="fx-a">↗</span></a>')
            st.markdown(rows_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erreur de chargement ou de traduction : {e}")

# =====================================================================
#  PAGE : BASE DE CONNAISSANCES
# =====================================================================
elif category == "📚 Base de Connaissances":
    hero("Repères institutionnels", "Base de Connaissances",
         "Ordres de grandeur, économies, matières premières et blocs géopolitiques",
         '<span class="pill">Valeurs approximatives</span>')

    TIPS = {
        "Apple": "Hardware & services · iPhone, App Store",
        "Microsoft": "Cloud Azure, logiciels, IA (OpenAI)",
        "NVIDIA": "GPU et accélérateurs pour l'IA",
        "Alphabet": "Maison mère de Google · publicité & cloud",
        "Amazon": "E-commerce et AWS (cloud)",
        "Saudi Aramco": "Compagnie pétrolière nationale saoudienne",
        "Meta": "Facebook, Instagram, WhatsApp",
        "Berkshire Hathaway": "Holding de Warren Buffett",
        "TSMC": "Taiwan Semiconductor · fondeur n°1 mondial",
        "Eli Lilly": "Pharma · traitements diabète / obésité",
        "Broadcom": "Semi-conducteurs et logiciels d'infrastructure",
        "Novo Nordisk": "Santé · diabète et obésité (GLP-1)",
        "LVMH": "Leader mondial du luxe",
        "ASML": "Monopole des machines de lithographie EUV",
        "SAP": "Logiciels de gestion d'entreprise (ERP)",
        "Hermès": "Luxe · maroquinerie",
    }

    def chips(names):
        return "".join(f'<span class="co tip" data-tip="{html.escape(TIPS.get(n, n))}">{n}</span>' for n in names)

    def ranks(items):
        medal = ["g", "s", "b"]
        out = ""
        for i, it in enumerate(items):
            label, extra = (it if isinstance(it, tuple) else (it, ""))
            m = medal[i] if i < 3 else ""
            out += f'<div class="rk"><span class="n {m}">{i + 1}</span><span>{label}</span><em>{extra}</em></div>'
        return out

    t1, t2, t3, t4, t5, t6 = st.tabs(["Capitalisations", "S&P 500", "Économies", "Matières premières", "Blocs & Alliances", "Leaders étrangers"])

    # ---- Capitalisations ----
    with t1:
        st.caption("Survolez une entreprise pour afficher son activité.")
        c1, c2, c3 = st.columns(3)
        for col, (big, title, names, clr) in zip((c1, c2, c3), [
            ("> 3 000 Mds $", 'Le club des « Big 3 »', ["Apple", "Microsoft", "NVIDIA"], "#FACC15"),
            ("> 2 000 Mds $", "Le club des 2 000", ["Alphabet", "Amazon", "Saudi Aramco"], "#CBD5E1"),
            ("> 1 000 Mds $", "Le club des 1 000", ["Meta", "Berkshire Hathaway", "TSMC", "Eli Lilly", "Broadcom"], "#FB923C")]):
            with col:
                st.markdown(f'<div class="kc" style="--c:{clr}"><h4>{title}</h4><div class="big">{big}</div>{chips(names)}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="kc"><h4>Poids lourds européens</h4><p>Capitalisation approximative (milliards de dollars). SAP et Hermès complètent le podium élargi.</p>', unsafe_allow_html=True)
            fig = go.Figure(go.Bar(
                y=["ASML", "LVMH", "Novo Nordisk"], x=[375, 400, 575], orientation='h',
                text=["~350-400", "~400", "~550-600"], textposition="inside",
                marker=dict(color=["#22D3EE", "#A78BFA", A1], line=dict(width=0)),
                hovertemplate="%{y} : %{text} Mds $<extra></extra>"))
            fig.update_layout(height=200, margin=dict(l=0, r=10, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(visible=False), yaxis=dict(color="#CBD3E6", tickfont=dict(size=13)),
                              font=dict(family="Inter", color="#fff"))
            show(fig, key="eu_caps")
            st.markdown(chips(["SAP", "Hermès"]) + '</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc"><h4>Total crypto-marché</h4><div class="big" style="--c:#FBBF24">~2 500 Mds $</div>', unsafe_allow_html=True)
            show(gauge(52.5, "Dominance du Bitcoin (≈ 50-55 %)", color="#F59E0B"), key="btc_dom")
            st.markdown('</div>', unsafe_allow_html=True)

    # ---- S&P 500 ----
    with t2:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="kc"><h4>Plus grandes pondérations du S&P 500</h4>' + ranks([
                ("<b>Microsoft</b>", "Tech · Cloud · IA"), ("<b>Apple</b>", "Hardware · Services"),
                ("<b>NVIDIA</b>", "Semi-conducteurs · IA"), ("<b>Amazon</b>", "E-commerce · Cloud"),
                ("<b>Alphabet</b>", "Publicité · Recherche")]) + '</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc"><h4>Concentration</h4><p>Ces 5 entreprises pèsent à elles seules près de 25 % de l\'indice : un risque de concentration majeur.</p>', unsafe_allow_html=True)
            show(gauge(25, "Poids cumulé du Top 5", color=A1), key="sp_conc")
            st.markdown('</div>', unsafe_allow_html=True)

    # ---- Économies ----
    with t3:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="kc"><h4>Plus grandes économies · PIB nominal</h4>', unsafe_allow_html=True)
            fig = go.Figure(go.Bar(
                y=["Inde", "Japon", "Allemagne", "Chine", "États-Unis"], x=[3900, 4200, 4500, 18500, 28000], orientation='h',
                text=["~3 900", "~4 200", "~4 500", "~18 500", "~28 000"], textposition="outside", cliponaxis=False,
                marker=dict(color=["#34D399", "#22D3EE", "#818CF8", "#A78BFA", A1]),
                hovertemplate="%{y} : %{text} Mds $<extra></extra>"))
            fig.update_layout(height=290, margin=dict(l=0, r=60, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(visible=False), yaxis=dict(color="#CBD3E6", tickfont=dict(size=13)),
                              font=dict(family="Inter", color="#fff"))
            show(fig, key="gdp")
            st.markdown('</div>', unsafe_allow_html=True)
            with st.expander("Contexte : Allemagne, Japon, Inde"):
                st.markdown("L'**Allemagne** a récemment dépassé le **Japon** suite à la faiblesse du Yen. "
                            "L'**Inde**, en forte croissance, vise le top 3 avant 2030.")
        with c2:
            st.markdown('<div class="kc"><h4>Plus grandes économies d\'Europe</h4>' + ranks([
                ("<b>Allemagne</b>", "Moteur industriel"), ("<b>Royaume-Uni</b>", "Finance & services"),
                ("<b>France</b>", "Luxe · aéro · énergie"), ("<b>Italie</b>", "Manufacturier"),
                ("<b>Espagne</b>", "Tourisme & services")]) + '</div>', unsafe_allow_html=True)

    # ---- Matières premières ----
    with t4:
        st.caption("Top 3 des plus grands producteurs mondiaux.")
        commo = [
            ("Pétrole (barils/jour)", ["États-Unis", "Arabie Saoudite", "Russie"]),
            ("Gaz naturel", ["États-Unis", "Russie", "Iran"]),
            ("Or (mines)", ["Chine", "Australie", "Russie"]),
            ("Cuivre", ["Chili", "Pérou", "RDC (Congo)"]),
            ("Lithium (batteries)", ["Australie", "Chili", "Chine"]),
        ]
        for k, (name, top) in enumerate(commo):
            with st.expander(name, expanded=(k == 0)):
                st.markdown(ranks(top), unsafe_allow_html=True)

    # ---- Blocs ----
    with t5:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="kc" style="--c:#818CF8"><h4>G7</h4><div class="big">7 + UE</div>' + chips(["États-Unis", "Japon", "Allemagne", "Royaume-Uni", "France", "Italie", "Canada"]).replace('class="co tip" data-tip="', 'class="co" data-x="') + '<p style="margin-top:10px">Union européenne invitée aux sommets.</p></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc" style="--c:#FB7185"><h4>BRICS+</h4><div class="big">Bloc élargi</div>' + "".join(f'<span class="co">{x}</span>' for x in ["Brésil", "Russie", "Inde", "Chine", "Afrique du Sud"]) + '<p style="margin-top:10px">Rejoints récemment par l\'Iran, l\'Égypte, l\'Éthiopie et les Émirats arabes unis.</p></div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="kc" style="--c:#FB923C"><h4>OPEP+</h4><div class="big">Cartel pétrolier</div><p>Mené par l\'<b>Arabie Saoudite</b>, allié à la <b>Russie</b> pour contrôler l\'offre mondiale de brut.</p></div>', unsafe_allow_html=True)

    # ---- Leaders étrangers ----
    with t6:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="kc"><h4>Inde · Nifty 50</h4>' + ranks([
                ("<b>Reliance Industries</b>", "Conglomérat · M. Ambani"), ("<b>TCS</b>", "Services IT"), ("<b>HDFC Bank</b>", "Banque")]) + '</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc"><h4>Europe · Stoxx 600</h4>' + ranks([
                ("<b>Novo Nordisk</b>", "Santé · diabète"), ("<b>LVMH</b>", "Luxe"), ("<b>ASML</b>", "Semi-conducteurs · EUV")]) + '</div>', unsafe_allow_html=True)
