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
import json
from datetime import timedelta
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor
import calendar
import io
from datetime import date
import plotly.io as pio

pio.templates["mt"] = go.layout.Template(layout=dict(
    font=dict(family="IBM Plex Sans, sans-serif", color="#E9E6DF"),
    colorway=["#E3A33B", "#6C9BC9", "#46B37D", "#E5574C", "#A9B4C2"],
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor="#23262C", zerolinecolor="#23262C", linecolor="#343841"),
    yaxis=dict(gridcolor="#23262C", zerolinecolor="#23262C", linecolor="#343841"),
    hoverlabel=dict(bgcolor="#111317", bordercolor="#343841", font=dict(family="IBM Plex Mono, monospace", color="#E9E6DF"))))
pio.templates.default = "mt"

st.set_page_config(page_title="PRO Macro Terminal", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
#  BACKEND (INCHANGÉ) : UNIVERSE + load_all_data
# =====================================================================
UNIVERSE = {
    "🏛️ Taux & Banques Centrales": {
        "US 13 semaines (T-Bill)": "^IRX",
        "US 2 ans (futures de rendement)": "2YY=F",
        "US 5 ans": "^FVX",
        "US 10 ans": "^TNX",
        "US 30 ans": "^TYX",
        "ETF dette intl hors USD (BWX)": "BWX",
        "ETF dette souveraine intl (IGOV)": "IGOV",
        "ETF dette japonaise (JGBL)": "JGBL.L"
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
        "Euronext 100": "^N100",
        "Stoxx Europe 600": "^STOXX",
        "CAC 40 ETF (Amundi)": "CAC.PA",
        "AEX (Pays-Bas)": "^AEX",
        "IBEX 35 (Espagne)": "^IBEX",
        "FTSE MIB (Italie)": "FTSEMIB.MI",
        "Nikkei 225 (Japon)": "^N225",
        "Hang Seng (Hong Kong)": "^HSI",
        "CSI 300 (Chine)": "000300.SS",
        "Nifty 50 (Inde)": "^NSEI",
        "MSCI World (ETF URTH)": "URTH",
        "MSCI Emerging (ETF EEM)": "EEM"
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
        "EUR/CHF": "EURCHF=X",
        "EUR/JPY": "EURJPY=X",
        "EUR/CNY": "EURCNY=X",
        "EUR/AUD": "EURAUD=X"
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
        "Soja (Soybeans)": "ZS=F",
        "Cacao (futures ICE US)": "CC=F",
        "Café (Arabica)": "KC=F",
        "Sucre": "SB=F",
        "Platine": "PL=F",
        "Palladium": "PA=F"
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
    "🇫🇷 Actions Françaises (CAC 40)": {
        "Hermès": "RMS.PA", "TotalEnergies": "TTE.PA", "Sanofi": "SAN.PA", "L'Oréal": "OR.PA",
        "Schneider Electric": "SU.PA", "Airbus": "AIR.PA", "Safran": "SAF.PA", "BNP Paribas": "BNP.PA",
        "AXA": "CS.PA", "Air Liquide": "AI.PA", "EssilorLuxottica": "EL.PA", "Vinci": "DG.PA",
        "Kering": "KER.PA", "Dassault Systèmes": "DSY.PA", "Danone": "BN.PA", "Pernod Ricard": "RI.PA",
        "Société Générale": "GLE.PA", "Crédit Agricole": "ACA.PA", "Thales": "HO.PA", "Stellantis": "STLAP.PA",
        "Capgemini": "CAP.PA", "Orange": "ORA.PA", "Engie": "ENGI.PA", "Michelin": "ML.PA"
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


YIELDS = {"^IRX", "^FVX", "^TNX", "^TYX", "2YY=F"}
UNIT = {"BZ=F": "$/baril", "CL=F": "$/baril", "GC=F": "$/once", "SI=F": "$/once", "HG=F": "$/lb", "NG=F": "$/MMBtu", "ZW=F": "¢/boisseau",
        "ZC=F": "¢/boisseau", "ZS=F": "¢/boisseau", "CC=F": "$/tonne", "KC=F": "¢/lb", "SB=F": "¢/lb", "PL=F": "$/once", "PA=F": "$/once",
        "BWX": "$ · prix ETF", "IGOV": "$ · prix ETF", "JGBL.L": "prix ETF", "URTH": "$ · prix ETF", "EEM": "$ · prix ETF", "DX-Y.NYB": "pts"}


def unit_of(t):
    if t in YIELDS or t.startswith("ext:"):
        return "%"
    if t in UNIT:
        return UNIT[t]
    if t.endswith(".PA") or t.endswith(".AS"):
        return "€"
    if t.endswith("=X"):
        return ""
    if t.startswith("^") or t.endswith(".MI") or t.endswith(".SS"):
        return "pts"
    return "$"


def fnum(v, d=2):
    return f"{v:,.{d}f}".replace(",", "\u00a0").replace(".", ",")


def sgn(v, d=2, suf=""):
    return f"{v:+.{d}f}{suf}".replace(".", ",")


def dec_of(t, v):
    if t in YIELDS or t.startswith("ext:"):
        return 3
    if t.endswith("=X"):
        return 4 if v < 20 else 2
    return 3 if v < 10 else 2


@st.cache_resource
def _last():
    return {}  # dernières séries valides : évite les trous si Yahoo refuse un ticker ponctuellement


def _chart(t, rng="3mo"):
    """Secours : API graphique Yahoo en direct (indépendante de yfinance)."""
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(t)}", params={"range": rng, "interval": "1d"},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    sr = pd.Series(res["indicators"]["quote"][0]["close"], index=pd.to_datetime(res["timestamp"], unit="s").normalize(), dtype="float64").dropna()
    sr = sr[~sr.index.duplicated(keep="last")]
    m = res.get("meta", {})
    if m.get("regularMarketPrice") and m.get("regularMarketTime"):
        d_ = pd.to_datetime(m["regularMarketTime"], unit="s").normalize()
        if len(sr) == 0 or d_ >= sr.index[-1]:
            sr.loc[d_] = float(m["regularMarketPrice"])
            sr = sr.sort_index()
    return sr


def _safe_chart(t):
    try:
        return _chart(t)
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_prices(tickers):
    all_tickers = list(dict.fromkeys(tickers))
    got = {}
    for i in range(0, len(all_tickers), 30):  # import par lots : contourne les blocages IP en production
        chunk = all_tickers[i:i + 30]
        try:
            c = yf.download(chunk, period="3mo", threads=True, progress=False)["Close"]
            if isinstance(c, pd.Series):
                c = c.to_frame(chunk[0])
            for t in c.columns:
                sr = c[t].dropna()
                if len(sr) >= 2:
                    got[t] = sr
        except Exception:
            pass
    miss = [t for t in all_tickers if t not in got]  # 2e chance : appel direct à l'API Yahoo, 4 en parallèle
    if miss:
        with ThreadPoolExecutor(4) as ex:
            for t, sr in zip(miss, ex.map(_safe_chart, miss)):
                if sr is not None and len(sr) >= 2:
                    got[t] = sr
    last = _last()
    for t in all_tickers:
        if t in got:
            last[t] = got[t]
        elif t in last:
            got[t] = last[t]
    return pd.DataFrame(got)


def load_all_data():
    return fetch_prices(tuple(dict.fromkeys(t for cat in UNIVERSE.values() for t in cat.values())))


@st.cache_data(ttl=900, show_spinner=False)
def ext_rates():  # séries officielles pour ce que Yahoo ne fournit pas
    out = {}
    try:
        out["US 2 ans (FRED, officiel)"] = _s_fred("DGS2").tail(90)
    except Exception:
        pass
    try:
        d = pd.read_csv(io.StringIO(_get("https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?startPeriod="
                                         + (date.today() - timedelta(days=140)).isoformat() + "&format=csvdata")))
        out["Zone euro 10 ans (courbe BCE, AAA)"] = _ser(d, "TIME_PERIOD", "OBS_VALUE").tail(90)
    except Exception:
        pass
    if not out:
        raise RuntimeError("séries officielles indisponibles")
    return out


CAP_LIST = {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Alphabet": "GOOGL", "Amazon": "AMZN", "Meta": "META", "Broadcom": "AVGO", "Tesla": "TSLA",
            "Berkshire Hathaway": "BRK-B", "TSMC": "TSM", "Eli Lilly": "LLY", "JPMorgan": "JPM", "Walmart": "WMT", "Visa": "V", "Oracle": "ORCL",
            "Saudi Aramco": "2222.SR", "Novo Nordisk": "NVO", "ASML": "ASML", "SAP": "SAP", "LVMH": "MC.PA", "Hermès": "RMS.PA", "TotalEnergies": "TTE.PA",
            "Sanofi": "SAN.PA", "L'Oréal": "OR.PA", "Schneider Electric": "SU.PA", "Airbus": "AIR.PA", "Safran": "SAF.PA", "BNP Paribas": "BNP.PA",
            "AXA": "CS.PA", "Air Liquide": "AI.PA"}
FR_NAMES = {"LVMH", "Hermès", "TotalEnergies", "Sanofi", "L'Oréal", "Schneider Electric", "Airbus", "Safran", "BNP Paribas", "AXA", "Air Liquide"}


@st.cache_data(ttl=1800, show_spinner=False)
def caps_live():  # capitalisations lues sur Yahoo Finance, converties en dollars
    def one(item):
        n, t = item
        try:
            fi = yf.Ticker(t).fast_info
            try:
                cap = float(fi["marketCap"])
            except Exception:
                cap = float(fi["market_cap"])
            return n, t, cap, str(fi["currency"])
        except Exception:
            return None
    with ThreadPoolExecutor(8) as ex:
        res = [r for r in ex.map(one, CAP_LIST.items()) if r]
    fx = {"USD": 1.0}
    for cur in {r[3] for r in res} - {"USD"}:
        try:
            fi = yf.Ticker(f"{cur}USD=X").fast_info
            try:
                fx[cur] = float(fi["lastPrice"])
            except Exception:
                fx[cur] = float(fi["last_price"])
        except Exception:
            pass
    out = sorted(((n, c * fx[cur] / 1e9, t) for n, t, c, cur in res if cur in fx), key=lambda x: -x[1])
    if len(out) < 8:
        raise RuntimeError("capitalisations indisponibles")
    return out


# =====================================================================
#  DESIGN SYSTEM
# =====================================================================
UP, DN, A1, A2 = "#46B37D", "#E5574C", "#E3A33B", "#6C9BC9"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap');
:root{color-scheme:dark;--bg:#0B0C0E;--bg2:#111317;--bg3:#171A1F;--ln:#23262C;--bd:#23262C;--ln2:#343841;--tx:#E9E6DF;--mut:#8E9099;--dim:#5E6168;--am:#E3A33B;--st:#6C9BC9;--a1:#E3A33B;--a2:#6C9BC9;--up:#46B37D;--dn:#E5574C;--serif:'Newsreader',Georgia,serif;--sans:'IBM Plex Sans',system-ui,sans-serif;--mono:'IBM Plex Mono',ui-monospace,monospace}
html,body,.stApp,[class*="css"]{font-family:var(--sans)}
.stApp{background:var(--bg);color:var(--tx)}
header[data-testid="stHeader"]{background:transparent}
#MainMenu,footer{visibility:hidden}
.block-container{padding-top:1.4rem;max-width:1500px}
hr{border-color:var(--ln)!important}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-thumb{background:var(--ln2)}::-webkit-scrollbar-track{background:var(--bg)}

/* ---------- Barre latérale ---------- */
section[data-testid="stSidebar"]{background:#08090B;border-right:1px solid var(--ln2)}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding-top:1.1rem}
.brand{display:flex;align-items:center;gap:13px;margin:2px 0 4px;padding-bottom:16px;border-bottom:1px solid var(--ln)}
.brand-mark{width:5px;height:38px;background:var(--am)}
.brand-t{font-family:var(--serif);font-size:1.5rem;font-weight:500;letter-spacing:-.01em;color:var(--tx);line-height:1.05}
.brand-s{font-size:.64rem;color:var(--mut);letter-spacing:.18em;text-transform:uppercase;margin-top:4px}
.live{display:flex;align-items:center;gap:8px;margin:12px 0 2px;font-family:var(--mono);font-size:.72rem;color:var(--mut)}
.live i{width:6px;height:6px;background:var(--up);border-radius:50%;animation:blink 2s steps(2,start) infinite}
@keyframes blink{50%{opacity:.25}}
.navlab,.sbh{font-family:var(--mono);font-size:.64rem;letter-spacing:.2em;text-transform:uppercase;color:var(--dim);margin:22px 0 6px;padding-bottom:7px;border-bottom:1px solid var(--ln)}
section[data-testid="stSidebar"] div[role="radiogroup"]{gap:0}
section[data-testid="stSidebar"] div[role="radiogroup"]>label{padding:12px 10px;margin:0;border-left:2px solid transparent;border-radius:0;cursor:pointer;width:100%;transition:background .15s}
section[data-testid="stSidebar"] div[role="radiogroup"]>label>div:first-child{display:none}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:hover{background:var(--bg2)}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked){background:var(--bg2);border-left-color:var(--am)}
section[data-testid="stSidebar"] div[role="radiogroup"]>label p{font-size:.95rem;font-weight:500;color:var(--mut);display:flex;align-items:center;margin:0}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked) p{color:var(--tx)}
section[data-testid="stSidebar"] div[role="radiogroup"]>label p::before{content:"";flex:none;width:16px;height:16px;margin-right:14px;background:currentColor;-webkit-mask:var(--ic) center/contain no-repeat;mask:var(--ic) center/contain no-repeat}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked) p::before{background:var(--am)}
.qk{display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:baseline;padding:9px 4px;border-bottom:1px solid var(--ln);font-size:.82rem}
.qk b{font-weight:500;color:var(--tx)}.qk span{font-family:var(--mono);font-size:.78rem;color:var(--mut)}
.qk .up{color:var(--up)}.qk .dn{color:var(--dn)}

/* ---------- En-tête de page ---------- */
.hero{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;flex-wrap:wrap;margin:6px 0 26px;padding-bottom:16px;border-bottom:1px solid var(--ln2);position:relative}
.hero::after{content:"";position:absolute;left:0;right:0;bottom:-5px;border-bottom:1px solid var(--ln)}
.eyebrow{font-family:var(--mono);font-size:.68rem;letter-spacing:.2em;text-transform:uppercase;color:var(--am);display:flex;align-items:center;gap:10px}
.eyebrow::before{content:"";width:22px;height:1px;background:var(--am)}
.hero h1{margin:8px 0 6px;padding:0;font-family:var(--serif);font-size:2.9rem;font-weight:500;letter-spacing:-.02em;line-height:1.02;color:var(--tx)}
.hero p{margin:0;color:var(--mut);font-size:.92rem}
.hmeta{text-align:right}
.hdate{font-family:var(--mono);font-size:.72rem;color:var(--dim);margin-top:8px;text-transform:capitalize}
.pills{display:flex;gap:20px;flex-wrap:wrap;justify-content:flex-end}
.pill{font-family:var(--mono);font-size:.76rem;color:var(--mut)}
.pill.up{color:var(--up)}.pill.dn{color:var(--dn)}
.kc .pill{display:inline-block;border:1px solid var(--ln2);border-radius:2px;padding:2px 8px;font-size:.7rem;margin-top:4px}
.sec{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin:30px 0 14px;padding-bottom:9px;border-bottom:1px solid var(--ln)}
.sec h2{margin:0;padding:0;font-family:var(--serif);font-weight:500;font-size:1.55rem;letter-spacing:-.01em;color:var(--tx)}
.sec span{color:var(--mut);font-size:.8rem}
.btn{display:inline-flex;align-items:center;gap:8px;text-decoration:none!important;padding:9px 16px;border:1px solid var(--am);border-radius:2px;font-family:var(--mono);font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:var(--am)!important;transition:.15s}
.btn:hover{background:var(--am);color:#0B0C0E!important}

/* ---------- Cellules de marché (clic = détail) ---------- */
[class*="st-key-card_"]{position:relative;cursor:pointer;background:var(--bg2);border:1px solid var(--ln);border-radius:3px;padding:14px 16px 4px;margin-bottom:10px;gap:0!important;transition:border-color .15s,background .15s}
[class*="st-key-card_"]:hover{border-color:var(--am);background:var(--bg3)}
[class*="st-key-btn_"]{position:absolute!important;inset:0;z-index:5;width:100%!important;height:100%!important;margin:0!important}
[class*="st-key-btn_"] div,[class*="st-key-btn_"] button{width:100%!important;height:100%!important;opacity:0;cursor:pointer}
.mt{position:relative;padding-right:20px;color:var(--mut);font-size:.7rem;font-weight:500;text-transform:uppercase;letter-spacing:.12em;margin-bottom:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mt .ex{position:absolute;right:0;top:0;opacity:.35;transition:.15s}
[class*="st-key-card_"]:hover .ex{opacity:1;color:var(--am)}
.mrow{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.mv{font-family:var(--mono);font-size:1.5rem;font-weight:500;color:var(--tx);letter-spacing:-.02em}
.un{font-family:var(--sans);font-size:.62rem;color:var(--dim);margin-left:6px;letter-spacing:.04em;font-weight:400}
.chip{font-family:var(--mono);font-size:.82rem;font-weight:500}
.chip.up{color:var(--up)}.chip.dn{color:var(--dn)}
.sub{font-size:.7rem;color:var(--dim);margin-top:5px;font-family:var(--mono)}
.sub b{font-weight:500}.sub b.up{color:var(--up)}.sub b.dn{color:var(--dn)}

/* ---------- Actualités ---------- */
.tp{background:var(--bg2);border:1px solid var(--ln);border-radius:3px;margin-bottom:10px}
.tr{display:grid;grid-template-columns:46px 1fr auto;gap:16px;align-items:center;padding:15px 20px;text-decoration:none!important;border-bottom:1px solid var(--ln);transition:background .15s}
.tr:last-child{border-bottom:0}.tr:hover{background:var(--bg3)}
.tr.f{border-left:3px solid var(--c);padding-top:20px;padding-bottom:20px}
.rk2{font-family:var(--serif);font-size:2rem;font-weight:400;font-style:italic;color:var(--c);line-height:1}
.en{color:var(--tx);font-family:var(--serif);font-weight:500;font-size:1.05rem;line-height:1.28}
.tr.f .en{font-size:1.4rem;font-weight:600}
.fr{color:var(--mut);font-size:.84rem;line-height:1.4;margin-top:4px}
.sm{color:var(--mut);font-size:.82rem;margin-top:8px;line-height:1.5;max-width:880px}
.mt2{display:flex;flex-direction:column;align-items:flex-end;gap:7px;min-width:130px}
.bars{display:flex;gap:2px}.bars i{width:12px;height:3px;background:var(--ln2)}.bars i.on{background:var(--c)}
.tm{font-size:.7rem;color:var(--dim);font-family:var(--mono)}
.tag{font-family:var(--mono);font-size:.62rem;text-transform:uppercase;letter-spacing:.12em;color:var(--c);display:inline-flex;align-items:center;gap:6px}
.tag::before{content:"";width:6px;height:6px;background:var(--c)}
.fl{display:grid;grid-template-columns:110px 1fr auto;gap:14px;align-items:center;padding:12px 20px;text-decoration:none!important;border-bottom:1px solid var(--ln);transition:background .15s}
.fl:last-child{border-bottom:0}.fl:hover{background:var(--bg3)}
@media(max-width:760px){.tr{grid-template-columns:34px 1fr}.mt2{flex-direction:row;align-items:center;grid-column:2}.fl{grid-template-columns:1fr}}

/* ---------- Panneaux de référence ---------- */
.kc{padding:18px 20px;border:1px solid var(--ln);border-top:2px solid var(--c,var(--ln2));border-radius:3px;margin-bottom:14px;background:var(--bg2);height:calc(100% - 14px);transition:border-color .15s}
.kc:hover{border-color:var(--ln2);border-top-color:var(--c,var(--am))}
.kc h4{margin:0 0 6px;font-family:var(--mono);font-size:.68rem;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);font-weight:500}
.kc .big{font-family:var(--serif);font-size:2.1rem;font-weight:500;letter-spacing:-.02em;color:var(--tx);margin:2px 0 12px;line-height:1.1}
.kc p{margin:0 0 9px;color:var(--mut);font-size:.84rem;line-height:1.45}
.co{display:inline-block;margin:3px 5px 3px 0;padding:5px 11px;border:1px solid var(--ln2);border-radius:2px;font-size:.82rem;font-weight:500;color:var(--tx);background:transparent}
.co b{font-family:var(--mono);font-weight:500;color:var(--am);margin-left:6px;font-size:.76rem}
.tip{position:relative;cursor:help}.tip:hover{border-color:var(--am)}
.tip:hover::after{content:attr(data-tip);position:absolute;left:50%;bottom:calc(100% + 8px);transform:translateX(-50%);width:max-content;max-width:240px;padding:8px 12px;border:1px solid var(--am);border-radius:2px;font-size:.75rem;font-weight:400;line-height:1.35;color:var(--tx);background:var(--bg);z-index:50}
.rk{display:flex;align-items:center;gap:14px;padding:11px 0;border-bottom:1px solid var(--ln);font-size:.92rem}
.rk:last-child{border:0}
.rk .n{font-family:var(--serif);font-style:italic;font-size:1.25rem;color:var(--dim);min-width:22px}
.rk .n.g{color:#D8B04A}.rk .n.s{color:#B9BEC6}.rk .n.b{color:#C77D4A}
.rk em{margin-left:auto;font-style:normal;color:var(--mut);font-size:.8rem}
.ct{width:100%;border-collapse:collapse;margin:4px 0 14px}
.ct th{padding:9px 14px;text-align:left;font-family:var(--mono);font-size:.64rem;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);font-weight:500;border-bottom:1px solid var(--ln2)}
.ct td{padding:12px 14px;border-bottom:1px solid var(--ln);font-size:.88rem;color:var(--mut)}
.ct td:first-child{color:var(--tx);font-weight:600}
.ct tr:hover td{background:var(--bg2)}
.ct .mono{font-family:var(--mono);font-size:.8rem;color:var(--tx)}
.ct a,.lk .src{color:var(--am);text-decoration:none;font-weight:500}
.lk .src{margin-top:8px;font-size:.76rem;font-family:var(--mono);letter-spacing:.06em}
a.lk{display:block;text-decoration:none!important;color:inherit;height:100%}
.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}
.sgt{padding:12px 14px;border:1px solid var(--ln);border-radius:3px;background:var(--bg2)}
.sgt span{display:block;font-family:var(--mono);font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);margin-bottom:5px}
.sgt b{font-family:var(--mono);font-size:1.05rem;font-weight:500;color:var(--tx)}
.sgt b.up{color:var(--up)}.sgt b.dn{color:var(--dn)}
.rb{position:relative;height:4px;background:linear-gradient(90deg,var(--dn),var(--ln2) 50%,var(--up));margin:14px 0 6px}
.rb i{position:absolute;top:-5px;width:2px;height:14px;background:var(--tx)}
.rl{display:flex;justify-content:space-between;font-size:.72rem;color:var(--mut);font-family:var(--mono)}

/* ---------- Composants Streamlit ---------- */
button[data-baseweb="tab"]{font-family:var(--mono);font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);padding:11px 16px}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--am)}
div[data-baseweb="tab-highlight"]{background:var(--am)!important;height:2px}
div[data-baseweb="tab-border"]{background:var(--ln)!important}
[data-testid="stExpander"]{border:1px solid var(--ln)!important;border-radius:3px!important;background:var(--bg2);margin-bottom:8px;overflow:hidden}
[data-testid="stExpander"] summary:hover{background:var(--bg3)}
div[data-testid="stTextInput"] input{background:var(--bg2);border:1px solid var(--ln2);border-radius:2px;color:var(--tx)}
button[kind="pills"],button[kind="pillsActive"]{border-radius:2px!important;font-family:var(--mono);font-size:.7rem;letter-spacing:.08em;text-transform:uppercase}
div[role="dialog"]{background:var(--bg2)!important;border:1px solid var(--ln2);border-radius:3px!important}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- Icônes SVG (style Lucide) pour la navigation, dans l'ordre des options ---
ICONS = [
    '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
    '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
    '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
    '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/>',
    '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
]


def icon_css(nav, icons):
    out = "<style>"
    for gi, (_, items) in enumerate(nav):
        for i, page in enumerate(items, 1):
            if page in icons:
                svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' "
                       "stroke-linecap='round' stroke-linejoin='round'>" + icons[page] + "</svg>")
                out += f'.st-key-nav_{gi} div[role="radiogroup"]>label:nth-child({i}){{--ic:url("data:image/svg+xml,{quote(svg)}")}}'
    return out + "</style>"


# =====================================================================
#  HELPERS UI
# =====================================================================
def clean_label(k):
    return re.sub(r"^[^\w]+", "", k).strip()


def hex_rgba(h, a):
    h = h.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def show(fig, key=None, static=False):
    cfg = {'displayModeBar': False, 'staticPlot': static}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg, key=key)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config=cfg, key=key)


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_L = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def hero(eyebrow, title, sub, pills=""):
    n = datetime.now(PARIS)
    st.markdown(f'<div class="hero"><div><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p></div>'
                f'<div class="hmeta"><div class="pills">{pills}</div>'
                f'<div class="hdate">{JOURS[n.weekday()]} {n.day} {MOIS_L[n.month - 1]} {n.year} · {n:%H:%M} Paris</div></div></div>', unsafe_allow_html=True)


def sec(title, sub, right=""):
    st.markdown(f'<div class="sec"><div><h2>{title}</h2><span>{sub}</span></div><div>{right}</div></div>',
                unsafe_allow_html=True)


def mini_chart(series, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=[series.values[0]] * len(series), mode="lines", hoverinfo="skip",
                             line=dict(color="#343841", width=1, dash="dot")))
    fig.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", line=dict(color=color, width=1.7),
                             hovertemplate="%{x|%d %b} · <b>%{y:,.2f}</b><extra></extra>"))
    fig.add_trace(go.Scatter(x=[series.index[-1]], y=[series.values[-1]], mode="markers", hoverinfo="skip",
                             marker=dict(color=color, size=7, symbol="square")))
    lo, hi = float(series.min()), float(series.max())
    pad = (hi - lo) * .12 or 1
    fig.update_layout(margin=dict(l=0, r=0, t=4, b=0), height=78, showlegend=False,
                      xaxis=dict(showgrid=False, visible=False), yaxis=dict(showgrid=False, visible=False, range=[lo - pad, hi + pad]),
                      hovermode="x unified")
    return fig


def gauge(v, title, color=A1, rng=(0, 100), suffix="%", height=215):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=v,
        number=dict(suffix=suffix, font=dict(size=34, color="#fff", family="IBM Plex Mono")),
        title=dict(text=title, font=dict(size=13, color="#8E9099")),
        gauge=dict(axis=dict(range=list(rng), tickcolor="#5E6168", tickfont=dict(size=10, color="#6A6D75")),
                   bar=dict(color=color, thickness=.3), bgcolor="rgba(255,255,255,.04)", borderwidth=0)))
    fig.update_layout(height=height, margin=dict(l=24, r=24, t=44, b=0),
                      paper_bgcolor='rgba(0,0,0,0)', font=dict(family="IBM Plex Sans"))
    return fig


TIPS = {
    "Apple": "Hardware & services · iPhone, App Store", "Microsoft": "Cloud Azure, logiciels, IA (OpenAI)",
    "NVIDIA": "GPU et accélérateurs pour l'IA", "Alphabet": "Maison mère de Google · publicité & cloud",
    "Amazon": "E-commerce et AWS (cloud)", "Saudi Aramco": "Compagnie pétrolière nationale saoudienne",
    "Meta": "Facebook, Instagram, WhatsApp", "Berkshire Hathaway": "Holding de Warren Buffett",
    "TSMC": "Taiwan Semiconductor · fondeur n°1 mondial", "Eli Lilly": "Pharma · diabète / obésité",
    "Broadcom": "Semi-conducteurs et logiciels d'infrastructure", "Novo Nordisk": "Santé · diabète et obésité (GLP-1)",
    "ASML": "Monopole des machines de lithographie EUV", "SAP": "Logiciels de gestion d'entreprise (ERP)",
    "LVMH": "N°1 mondial du luxe · Louis Vuitton, Dior, Moët Hennessy", "Hermès": "Luxe · maroquinerie (Birkin), très haute marge",
    "Kering": "Luxe · Gucci, Saint Laurent", "TotalEnergies": "Major pétrole, gaz & électricité bas carbone",
    "Engie": "Électricité, gaz et renouvelables", "Sanofi": "Pharma · vaccins, dermatologie (Dupixent)",
    "EssilorLuxottica": "Verres et lunettes (Ray-Ban, Oakley)", "Airbus": "Constructeur d'avions · duopole avec Boeing",
    "Safran": "Moteurs d'avions (CFM) et équipements", "Thales": "Défense, aéronautique, cybersécurité",
    "Schneider Electric": "Gestion de l'énergie et automatisation (data centers)", "Vinci": "Concessions (autoroutes, aéroports) et BTP",
    "BNP Paribas": "1re banque de la zone euro · BNP Paribas CIB", "AXA": "Assurance et gestion d'actifs",
    "Société Générale": "Banque · fort en dérivés actions", "Crédit Agricole": "Banque mutualiste · Crédit Agricole CIB",
    "L'Oréal": "N°1 mondial de la beauté", "Danone": "Produits laitiers et nutrition", "Pernod Ricard": "Spiritueux (Ricard, Absolut, Jameson)",
    "Stellantis": "Auto · Peugeot, Citroën, Fiat, Jeep", "Michelin": "Pneumatiques",
}


def table(heads, rows):
    h = "".join(f"<th>{x}</th>" for x in heads)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="ct"><tr>{h}</tr>{b}</table>'


def ranks(items):
    out = ""
    for i, it in enumerate(items):
        label, extra = it if isinstance(it, tuple) else (it, "")
        m = ["g", "s", "b"][i] if i < 3 else ""
        out += f'<div class="rk"><span class="n {m}">{i + 1}</span><span>{label}</span><em>{extra}</em></div>'
    return out


def chips(names):
    return "".join(f'<span class="co tip" data-tip="{html.escape(TIPS.get(n, n))}">{n}</span>' for n in names)


def kc(title, big="", body="", color="#8E9099"):
    return (f'<div class="kc" style="--c:{color}"><h4>{title}</h4>' + (f'<div class="big">{big}</div>' if big else "") + body + '</div>')


# ---- BANQUES CENTRALES : tout est lu en ligne (FRED, BCE, BoE, BRI, Eurostat) ; les valeurs de référence ne servent que de secours hors-ligne ----
REF_DATE = date(2026, 10, 6)
CB = {
    "Fed": dict(zone="États-Unis", lab="Fed funds · fourchette cible", c="#E3A33B", ref=(3.75, 4.00), move="Hausse de +25 pb le 16/09/26 (vote 12-0)",
                url="https://www.federalreserve.gov/monetarypolicy/openmarket.htm", cal="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),
    "BCE": dict(zone="Zone euro", lab="Taux de la facilité de dépôt", c="#6C9BC9", ref=(2.50, 2.50), move="Hausse de +25 pb le 10/09/26 · refi 2,65 % · prêt marginal 2,90 %",
                url="https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html", cal="https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"),
    "BoJ": dict(zone="Japon", lab="Taux au jour le jour", c="#E5574C", ref=(1.25, 1.25), move="Hausse de +25 pb le 18/09/26 (7-2) · plus haut depuis 1995",
                url="https://www.boj.or.jp/en/mopo/index.htm", cal="https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm"),
    "BoE": dict(zone="Royaume-Uni", lab="Bank Rate", c="#46B37D", ref=(3.75, 3.75), move="Statu quo le 17/09/26 (6-3, trois voix pour +25 pb)",
                url="https://www.bankofengland.co.uk/monetary-policy/the-interest-rate-bank-rate", cal="https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"),
}
# Calendriers officiels connus (début, fin). La prochaine réunion est calculée automatiquement.
MEETINGS = {
    "Fed": [("2026-10-27", "2026-10-28"), ("2026-12-08", "2026-12-09"), ("2027-01-26", "2027-01-27"), ("2027-03-16", "2027-03-17"), ("2027-04-27", "2027-04-28"),
            ("2027-06-08", "2027-06-09"), ("2027-07-27", "2027-07-28"), ("2027-09-14", "2027-09-15"), ("2027-10-26", "2027-10-27"), ("2027-12-07", "2027-12-08")],
    "BCE": [("2026-10-28", "2026-10-29"), ("2026-12-16", "2026-12-17"), ("2027-02-03", "2027-02-04"), ("2027-03-17", "2027-03-18"), ("2027-04-28", "2027-04-29")],
    "BoJ": [("2026-10-29", "2026-10-30"), ("2026-12-17", "2026-12-18")],
    "BoE": [("2026-11-05", "2026-11-05"), ("2026-12-17", "2026-12-17")],
}
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def fr_range(a_, b_):
    a_, b_ = date.fromisoformat(a_), date.fromisoformat(b_)
    if a_ == b_:
        return f"{a_.day} {MOIS[a_.month - 1]} {a_.year}"
    return f"{a_.day}-{b_.day} {MOIS[b_.month - 1]} {b_.year}" if a_.month == b_.month else f"{a_.day} {MOIS[a_.month - 1]} - {b_.day} {MOIS[b_.month - 1]} {b_.year}"


def upcoming(bank, today, n=1):
    return [m for m in MEETINGS[bank] if date.fromisoformat(m[1]) >= today][:n]


UA = {"User-Agent": "Mozilla/5.0"}


def _get(url, accept=None):
    h = dict(UA)
    if accept:
        h["Accept"] = accept
    r = requests.get(url, headers=h, timeout=7)
    r.raise_for_status()
    return r.text


def _ser(df, dcol, vcol):
    d = pd.DataFrame({"d": pd.to_datetime(df[dcol].astype(str).str.strip(), errors="coerce"), "v": pd.to_numeric(df[vcol], errors="coerce")}).dropna()
    sr = d.set_index("d")["v"].sort_index()
    return sr[~sr.index.duplicated(keep="last")]


def _s_fred(sid):
    d = pd.read_csv(io.StringIO(_get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2023-01-01")))
    return _ser(d, d.columns[0], d.columns[1])


def _s_ecb():
    d = pd.read_csv(io.StringIO(_get("https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV?startPeriod=2023-01-01&format=csvdata")))
    return _ser(d, "TIME_PERIOD", "OBS_VALUE")


def _s_boe():
    d = pd.read_csv(io.StringIO(_get("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/2023&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N")))
    return _ser(d, d.columns[0], d.columns[1])


def _s_bis(code):  # taux directeurs de la BRI
    d = pd.read_csv(io.StringIO(_get(f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.{code}?startPeriod=2023-01-01&detail=dataonly",
                                     accept="application/vnd.sdmx.data+csv;version=1.0.0")))
    return _ser(d, "TIME_PERIOD", "OBS_VALUE")


def _dup(sr, name):
    return sr, sr, name


def last_change(sr):
    dif = sr.diff()
    ch = dif[dif.abs() > .001]
    return (float(ch.iloc[-1]) * 100, ch.index[-1].date()) if len(ch) else None


SOURCES = {
    "Fed": [lambda: (_s_fred("DFEDTARL"), _s_fred("DFEDTARU"), "FRED"), lambda: _dup(_s_bis("US"), "BRI")],
    "BCE": [lambda: _dup(_s_ecb(), "BCE"), lambda: _dup(_s_fred("ECBDFR"), "FRED"), lambda: _dup(_s_bis("XM"), "BRI")],
    "BoJ": [lambda: _dup(_s_bis("JP"), "BRI")],
    "BoE": [lambda: _dup(_s_boe(), "Bank of England"), lambda: _dup(_s_bis("GB"), "BRI")],
}


@st.cache_data(ttl=3600, show_spinner=False)
def cb_live():
    out = {}
    for bank, fns in SOURCES.items():
        for fn in fns:
            try:
                lo_s, hi_s, src = fn()
                lo, hi = float(lo_s.iloc[-1]), float(hi_s.iloc[-1])
                if 0 <= lo <= hi <= 20:
                    out[bank] = (lo, hi, hi_s.index[-1].date(), src, last_change(hi_s))
                    break
            except Exception:
                continue
    if not out:
        raise RuntimeError("aucune source disponible")  # non mis en cache : nouvel essai au prochain chargement
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def macro_live():
    out = {}
    try:
        c = _s_fred("CPIAUCSL")
        out["us_cpi"] = (float((c.iloc[-1] / c.iloc[-13] - 1) * 100), c.index[-1].date())
        u = _s_fred("UNRATE")
        out["us_u"] = (float(u.iloc[-1]), u.index[-1].date())
    except Exception:
        pass
    for key, geo in (("ea_hicp", "EA"), ("fr_hicp", "FR")):
        try:
            j = requests.get("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr", headers=UA, timeout=8,
                             params={"format": "JSON", "lang": "EN", "geo": geo, "coicop": "CP00", "unit": "RCH_A", "lastTimePeriod": 2}).json()
            per, pos = max(j["dimension"]["time"]["category"]["index"].items(), key=lambda kv: kv[1])
            if j["value"].get(str(pos)) is not None:
                out[key] = (float(j["value"][str(pos)]), pd.to_datetime(per).date())
        except Exception:
            pass
    for key, ctry in (("fr10", "FR"), ("de10", "DE")):
        try:
            d = pd.read_csv(io.StringIO(_get(f"https://data-api.ecb.europa.eu/service/data/IRS/M.{ctry}.L.L40.CI.0000.EUR.N.Z?lastNObservations=1&format=csvdata")))
            out[key] = (float(d["OBS_VALUE"].iloc[-1]), pd.to_datetime(str(d["TIME_PERIOD"].iloc[-1])).date())
        except Exception:
            pass
    if not out:
        raise RuntimeError("aucune donnée macro")
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def crypto_live():
    j = requests.get("https://api.coingecko.com/api/v3/global", headers=UA, timeout=6).json()["data"]
    return {"cap": j["total_market_cap"]["usd"] / 1e9, "btc": j["market_cap_percentage"]["btc"]}


@st.cache_data(ttl=86400, show_spinner=False)
def gdp_live():
    names = {"USA": "États-Unis", "CHN": "Chine", "DEU": "Allemagne", "JPN": "Japon", "IND": "Inde", "GBR": "Royaume-Uni", "FRA": "France", "ITA": "Italie", "BRA": "Brésil", "CAN": "Canada"}
    j = requests.get("https://api.worldbank.org/v2/country/" + ";".join(names) + "/indicator/NY.GDP.MKTP.CD", headers=UA, timeout=8,
                     params={"format": "json", "mrnev": 1, "per_page": 30}).json()[1]
    out = {names[r["countryiso3code"]]: (r["value"] / 1e9, r["date"]) for r in j if r.get("value") and r.get("countryiso3code") in names}
    if len(out) < 8:
        raise RuntimeError("PIB incomplet")
    return out


QUICK_ALL = [("CAC 40", "^FCHI"), ("S&P 500", "^GSPC"), ("EUR/USD", "EURUSD=X"), ("USD/JPY", "USDJPY=X"), ("Or", "GC=F"), ("Brent", "BZ=F"), ("Bitcoin", "BTC-USD"), ("US 10Y", "^TNX")]


@st.cache_data(ttl=60, show_spinner=False)
def quick_quotes():
    out, tk = {}, [t for _, t in QUICK_ALL]
    try:
        c = yf.download(tk, period="1mo", progress=False)["Close"]
        for t in c.columns:
            sr = c[t].dropna()
            if len(sr) >= 2:
                out[t] = (float(sr.iloc[-1]), float(sr.iloc[-1] / sr.iloc[-2] - 1) * 100)
    except Exception:
        pass
    for t in tk:
        if t not in out:
            try:
                sr = _chart(t, "1mo")
                if len(sr) >= 2:
                    out[t] = (float(sr.iloc[-1]), float(sr.iloc[-1] / sr.iloc[-2] - 1) * 100)
            except Exception:
                pass
    return out


# =====================================================================
#  HORAIRES DES PLACES BOURSIÈRES (heures locales, hors jours fériés)
# =====================================================================
MARKETS = [  # (ville, bourse, fuseau, sessions locales)
    ("Sydney", "ASX", "Australia/Sydney", [("10:00", "16:00")]),
    ("Tokyo", "TSE", "Asia/Tokyo", [("09:00", "11:30"), ("12:30", "15:30")]),
    ("Hong Kong", "HKEX", "Asia/Hong_Kong", [("09:30", "12:00"), ("13:00", "16:00")]),
    ("Shanghai", "SSE", "Asia/Shanghai", [("09:30", "11:30"), ("13:00", "15:00")]),
    ("Mumbai", "NSE", "Asia/Kolkata", [("09:15", "15:30")]),
    ("Londres", "LSE", "Europe/London", [("08:00", "16:30")]),
    ("Paris", "Euronext", "Europe/Paris", [("09:00", "17:30")]),
    ("Francfort", "Xetra", "Europe/Berlin", [("09:00", "17:30")]),
    ("New York", "NYSE", "America/New_York", [("09:30", "16:00")]),
]
STRIP = ["Sydney", "Tokyo", "Hong Kong", "Londres", "Paris", "New York"]
PARIS = ZoneInfo("Europe/Paris")


def market_strip():
    cfg = [{"n": n, "x": x, "tz": tz, "s": ss} for n, x, tz, ss in MARKETS if n in STRIP]
    cfg.sort(key=lambda m: STRIP.index(m["n"]))
    page = """<style>@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@500;600&display=swap');
html,body{margin:0;overflow:hidden;background:transparent;font-family:'IBM Plex Sans',sans-serif}
#w{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));border:1px solid #23262C;border-radius:3px;background:#111317}
.m{min-width:0;padding:10px 14px 9px;color:#E9E6DF;border-right:1px solid #23262C;border-top:2px solid transparent}
.m:last-child{border-right:0}
.m.open{border-top-color:#46B37D}.m.lunch{border-top-color:#D9923A}
.h{display:flex;justify-content:space-between;align-items:baseline;gap:4px}.h b{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;font-weight:600;white-space:nowrap}.h i{font-style:normal;font-size:.55rem;letter-spacing:.1em;color:#5E6168}
.t{font-family:'IBM Plex Mono',monospace;font-weight:500;font-size:clamp(.8rem,1.5vw,1.15rem);margin:3px 0 1px;white-space:nowrap}
.s{font-size:.66rem;color:#8E9099;display:flex;align-items:center;gap:6px;font-weight:600}.s u{width:6px;height:6px;background:#5E6168;flex:none}
.c{font-family:'IBM Plex Mono',monospace;font-size:.58rem;color:#5E6168;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.open .s{color:#46B37D}.open u{background:#46B37D}.lunch .s{color:#D9923A}.lunch u{background:#D9923A}</style>
<div id="w"></div><script>const M=__CFG__,w=document.getElementById('w'),D=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
M.forEach((m,i)=>w.insertAdjacentHTML('beforeend','<div class="m" id="m'+i+'"><div class="h"><b>'+m.n+'</b><i>'+m.x+'</i></div><div class="t"></div><div class="s"><u></u><span></span></div><div class="c"></div></div>'));
const mn=s=>{const a=s.split(':');return +a[0]*60+ +a[1]},p2=x=>String(x).padStart(2,'0'),fm=x=>x>=1440?Math.floor(x/1440)+'j '+Math.floor(x%1440/60)+'h':Math.floor(x/60)+'h'+p2(x%60);
function tick(){M.forEach((m,i)=>{const p=new Intl.DateTimeFormat('en-GB',{timeZone:m.tz,weekday:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).formatToParts(new Date());
const g=t=>p.find(x=>x.type===t).value,H=+g('hour')%24,cur=H*60+ +g('minute'),wi=D.indexOf(g('weekday')),wk=wi<5,ss=m.s.map(a=>[mn(a[0]),mn(a[1])]);
let st='closed',a=wk?'Fermé':'Week-end',c='';
if(wk){for(let k=0;k<ss.length;k++){if(cur>=ss[k][0]&&cur<ss[k][1]){st='open';a='Ouvert';c='ferme dans '+fm(ss[k][1]-cur);break}
if(cur<ss[k][0]){st=k>0?'lunch':'closed';a=k>0?'Pause':'Fermé';c='ouvre dans '+fm(ss[k][0]-cur);break}}}
if(!c){for(let d=1;d<=7;d++){if((wi+d)%7<5){c='ouvre dans '+fm(d*1440+ss[0][0]-cur);break}}}
const e=document.getElementById('m'+i);e.className='m '+st;e.querySelector('.t').textContent=g('hour').replace('24','00')+':'+g('minute')+':'+g('second');e.querySelector('.s span').textContent=a;e.querySelector('.c').textContent=c})}
tick();setInterval(tick,1000)</script>""".replace("__CFG__", json.dumps(cfg))
    try:
        st.iframe(page, height=88)  # Streamlit récent : components.html est déprécié
    except Exception:
        components.html(page, height=88)


# =====================================================================
#  VUE DÉTAILLÉE (clic sur une carte)
# =====================================================================
@st.cache_data(ttl=900, show_spinner=False)
def load_detail(ticker, period):
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Close"])
        assert len(df) > 2
        return df
    except Exception:
        return pd.DataFrame({"Close": _chart(ticker, period)})


@st.dialog("Analyse détaillée", width="large")
def detail_dialog(name, ticker, cat, ext=None):
    st.markdown(f'<div class="eyebrow">{cat} · {ticker}</div><h2 style="margin:2px 0 10px;font-weight:800">{html.escape(name)}</h2>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    per = c1.radio("Période", ["1M", "3M", "6M", "1A", "5A"], index=1, horizontal=True, label_visibility="collapsed", disabled=ext is not None)
    mode = c2.radio("Type", ["Ligne", "Chandeliers"], horizontal=True, label_visibility="collapsed")
    try:
        df = pd.DataFrame({"Close": ext.astype(float)}) if ext is not None else load_detail(ticker, {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1A": "1y", "5A": "5y"}[per])
        assert len(df) > 2
    except Exception:
        df = pd.DataFrame({"Close": fetch_prices((ticker,))[ticker].dropna()})
        st.caption("Historique étendu indisponible : affichage sur 3 mois.")
    cl = df["Close"].astype(float)
    last, prev = cl.iloc[-1], cl.iloc[-2]
    d = cl.diff()
    gain, loss = d.clip(lower=0).rolling(14).mean(), (-d.clip(upper=0)).rolling(14).mean()
    rsi = (100 - 100 / (1 + gain / loss)).iloc[-1]
    perf, hi, lo = (last / cl.iloc[0] - 1) * 100, cl.max(), cl.min()
    vol = cl.pct_change().std() * (252 ** .5) * 100
    sgn = lambda v: "up" if v >= 0 else "dn"
    tiles = [("Dernier", f"{last:,.2f}", ""), ("Variation jour", f"{(last / prev - 1) * 100:+.2f}%", sgn(last - prev)),
             (f"Perf. {per}", f"{perf:+.2f}%", sgn(perf)), ("Volatilité ann.", f"{vol:.1f}%", ""),
             ("Plus haut", f"{hi:,.2f}", ""), ("Plus bas", f"{lo:,.2f}", ""),
             ("Écart au plus haut", f"{(last / hi - 1) * 100:.2f}%", "dn"),
             ("RSI (14)", f"{rsi:.0f}" if pd.notna(rsi) else "n/a", "dn" if rsi > 70 else ("up" if rsi < 30 else ""))]
    st.markdown('<div class="sg">' + "".join(f'<div class="sgt"><span>{a}</span><b class="{c}">{b}</b></div>' for a, b, c in tiles) + '</div>',
                unsafe_allow_html=True)
    pos = 0 if hi == lo else (last - lo) / (hi - lo) * 100
    st.markdown(f'<div class="rb"><i style="left:calc({pos:.0f}% - 3px)"></i></div><div class="rl"><span>{lo:,.2f}</span>'
                f'<span>position dans la fourchette {per}</span><span>{hi:,.2f}</span></div>', unsafe_allow_html=True)

    has_vol = "Volume" in df and df["Volume"].fillna(0).sum() > 0
    fig = make_subplots(rows=2 if has_vol else 1, cols=1, shared_xaxes=True, vertical_spacing=.03,
                        row_heights=[.78, .22] if has_vol else [1])
    col = UP if perf >= 0 else DN
    if mode == "Chandeliers" and {"Open", "High", "Low"} <= set(df.columns):
        fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=cl, name="Prix",
                                     increasing_line_color=UP, decreasing_line_color=DN), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index, y=cl, name="Clôture", line=dict(color=col, width=2.6, shape="spline", smoothing=.5),
                                 fill="tozeroy", fillcolor=hex_rgba(col, .08)), row=1, col=1)
    for w_, c_ in ((20, "#D9923A"), (50, "#A9B4C2")):
        if len(cl) > w_ + 2:
            fig.add_trace(go.Scatter(x=df.index, y=cl.rolling(w_).mean(), name=f"MM{w_}", line=dict(color=c_, width=1.3, dash="dot")), row=1, col=1)
    if has_vol:
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color="rgba(108,155,201,.45)"), row=2, col=1)
    lo_y, hi_y = float(cl.min()), float(cl.max())
    fig.update_layout(height=440 if has_vol else 380, margin=dict(l=0, r=0, t=6, b=0), hovermode="x unified",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="IBM Plex Sans", color="#CFCBC2"),
                      xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.07, x=0),
                      hoverlabel=dict(bgcolor="#111317", bordercolor=col))
    fig.update_xaxes(gridcolor="rgba(255,255,255,.05)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,.05)")
    fig.update_yaxes(range=[lo_y - (hi_y - lo_y) * .08, hi_y + (hi_y - lo_y) * .08], row=1, col=1)
    show(fig, key="detail_chart")
    with st.expander("Dernières séances"):
        st.dataframe(df.tail(10).iloc[::-1].round(2), use_container_width=True)


# =====================================================================
#  SIDEBAR
# =====================================================================
st.sidebar.markdown(
    '<div class="brand"><div class="brand-mark"></div><div><div class="brand-t">Macro Terminal</div>'
    '<div class="brand-s">Marchés mondiaux · Paris</div></div></div>'
    f'<div class="live"><i></i>{datetime.now(PARIS):%H:%M} · Paris</div>', unsafe_allow_html=True)
_k = list(UNIVERSE.keys())
NAV = [("Marchés", _k[0:4] + _k[6:8]), ("Actions", _k[4:6]),
       ("Macro", ["🏦 Banques Centrales", "🕐 Calendrier des Marchés", "📰 Actualités Macro (FR)"]), ("Référence", ["📚 Base de Connaissances"])]
options = [o for _, g in NAV for o in g]
ICON_BY_PAGE = dict(zip([_k[0], "🏦 Banques Centrales", _k[1], _k[2], _k[3], _k[4], _k[5], _k[6], _k[7],
                         "🕐 Calendrier des Marchés", "📰 Actualités Macro (FR)", "📚 Base de Connaissances"], ICONS))
st.markdown(icon_css(NAV, ICON_BY_PAGE), unsafe_allow_html=True)
if st.session_state.get("page") not in options:
    st.session_state["page"] = options[0]


def _go(gi):
    st.session_state["page"] = st.session_state[f"nav_{gi}"]


for gi, (gname, items) in enumerate(NAV):
    st.sidebar.markdown(f'<div class="navlab">{gname}</div>', unsafe_allow_html=True)
    st.session_state[f"nav_{gi}"] = st.session_state["page"] if st.session_state["page"] in items else None
    st.sidebar.radio(gname, items, index=None, key=f"nav_{gi}", format_func=clean_label, label_visibility="collapsed", on_change=_go, args=(gi,))
category = st.session_state["page"]


@st.fragment(run_every="60s")
def sidebar_panel():
    q = quick_quotes()
    rows = ""
    for name, t in QUICK_ALL:
        if t in q:
            v, pc_ = q[t]
            rows += f'<div class="qk"><b>{name}</b><span>{v:,.2f}</span><span class="{"up" if pc_ >= 0 else "dn"}">{pc_:+.2f}%</span></div>'
    st.markdown('<div class="sbh">Aperçu des marchés</div>' + (rows or '<div class="qk"><b>Données en cours de chargement…</b></div>'), unsafe_allow_html=True)
    today_ = datetime.now(PARIS).date()
    nx = sorted((m[1], b_, m) for b_ in CB for m in upcoming(b_, today_))[:3]
    st.markdown('<div class="sbh">Prochaines réunions</div>' + "".join(
        f'<div class="qk"><b style="color:{CB[b_]["c"]}">{b_}</b><span>{fr_range(*m)}</span><span>{(date.fromisoformat(e_) - today_).days} j</span></div>' for e_, b_, m in nx), unsafe_allow_html=True)


with st.sidebar:
    sidebar_panel()
st.sidebar.markdown('<div style="margin-top:30px;font-size:.7rem;color:#5E6168;line-height:1.5">Données : Yahoo Finance (différé jusqu’à 15 min selon les places), FRED, BCE, Eurostat, BRI.<br>Informations à but pédagogique, pas un conseil en investissement.</div>',
                    unsafe_allow_html=True)

# =====================================================================
#  PAGE : DONNÉES DE MARCHÉ
# =====================================================================
market_strip()


@st.fragment(run_every="60s")
def render_market(cat):
    with st.spinner("Synchronisation avec les marchés..."):
        df_close = fetch_prices(tuple(UNIVERSE[cat].values()))
    avail, missing = [], []
    for name, ticker in UNIVERSE[cat].items():
        sr = df_close[ticker].dropna() if ticker in df_close.columns else pd.Series(dtype=float)
        if len(sr) >= 2:
            avail.append((name, ticker, sr))
        else:
            missing.append(name)
    if cat == list(UNIVERSE)[0]:  # page des taux : séries officielles complémentaires
        try:
            ext = ext_rates()
        except Exception:
            ext = {}
        for n_, sr in ext.items():
            if n_.startswith("US 2 ans") and "2YY=F" in df_close.columns:
                continue
            avail.append((n_, "ext:" + n_, sr))
    ups = sum(1 for _, _, sr in avail if sr.iloc[-1] >= sr.iloc[-2])
    hero("Marchés", clean_label(cat),
         f"{len(avail)} instruments · données Yahoo Finance (différées jusqu'à 15 min selon les places) · actualisation toutes les 60 s",
         f'<span class="pill up">▲ {ups} en hausse</span><span class="pill dn">▼ {len(avail) - ups} en baisse</span>')
    cols = st.columns(4)
    for i, (name, ticker, series) in enumerate(avail):
        with cols[i % 4]:
            curr, prev = float(series.iloc[-1]), float(series.iloc[-2])
            is_y = ticker in YIELDS or ticker.startswith("ext:")
            base30 = float(series.tail(30).iloc[0])
            if is_y:
                chg, c30 = sgn((curr - prev) * 100, 1, " pb"), sgn((curr - base30) * 100, 0, " pb")
            else:
                chg, c30 = sgn((curr / prev - 1) * 100, 2, " %"), sgn((curr / base30 - 1) * 100, 1, " %")
            d_ = curr - prev
            d30 = curr - base30
            inverse = "VIX" in name or "MOVE" in name
            good = (d_ < 0) if inverse else (d_ >= 0)
            good30 = (d30 < 0) if inverse else (d30 >= 0)
            cls, cls30 = ("up" if good else "dn"), ("up" if good30 else "dn")
            color = UP if good else DN
            unit = unit_of(ticker)
            with st.container(key=f"card_{i}"):
                st.markdown(
                    f'<div class="mt">{html.escape(name)}<svg class="ex" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg></div>'
                    f'<div class="mrow"><span class="mv">{fnum(curr, dec_of(ticker, curr))}<span class="un">{unit}</span></span>'
                    f'<span class="chip {cls}">{"▲" if d_ >= 0 else "▼"} {chg}</span></div>'
                    f'<div class="sub">30 j <b class="{cls30}">{c30}</b> · point du {series.index[-1]:%d/%m}</div>', unsafe_allow_html=True)
                show(mini_chart(series.tail(30), color), key=f"mini_{i}", static=True)
                if st.button("Détails", key=f"btn_{i}"):
                    detail_dialog(name, ticker, clean_label(cat), series if ticker.startswith("ext:") else None)
    if missing:
        st.caption("Temporairement indisponibles chez Yahoo Finance : " + ", ".join(missing))


FEED = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
AGGREGATOR = "https://www.tradingview.com/news/"
TAGS = {
    "Banques centrales": ("#C9A86A", 5, ["fed", "federal reserve", "ecb", "boj", "bank of japan", "bank of england", "powell", "warsh", "lagarde", "rate cut", "rate hike", "interest rate", "central bank", "fomc"]),
    "Inflation & Emploi": ("#D9923A", 4, ["inflation", "cpi", "pce", "jobs", "payroll", "unemployment", "gdp", "recession", "layoffs", "consumer prices"]),
    "Géopolitique": ("#E5574C", 4, ["war", "sanction", "iran", "russia", "ukraine", "china", "israel", "tariff", "trade war", "middle east", "taiwan", "election", "trump", "ceasefire"]),
    "Énergie": ("#C77D4A", 3, ["oil", "crude", "natural gas", "opec", "energy", "brent"]),
    "Europe & France": ("#9DB4A0", 3, ["france", "french", "macron", "eurozone", "euro zone", "european", "europe", "germany", "paris", "cac"]),
    "Marchés": ("#6C9BC9", 2, ["stocks", "s&p", "nasdaq", "dow", "yields", "treasury", "dollar", "bond", "bitcoin", "earnings", "wall street"]),
}
HOT = ["plunge", "surge", "soar", "crash", "record", "emergency", "shock", "collapse", "spike", "tumble", "warns", "default"]

@st.cache_data(ttl=600, show_spinner=False)
def fetch_news():
    r = requests.get(FEED, headers={'User-Agent': 'Mozilla/5.0'}, timeout=6)
    out = []
    for e in feedparser.parse(r.content).entries[:40]:
        ts = calendar.timegm(e.published_parsed) if getattr(e, "published_parsed", None) else 0
        out.append({"title": e.title, "link": e.link, "ts": ts,
                    "summary": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", getattr(e, "summary", ""))).strip()})
    return out

def _tr(texts):
    g = GoogleTranslator(source="en", target="fr")
    out = (g.translate("\n".join(texts)) or "").split("\n")
    return out if len(out) == len(texts) else g.translate_batch(texts)

@st.cache_data(ttl=86400, show_spinner=False)
def fr_batch(texts):  # 1 seule requête, limitée à 18 s ; une erreur n'est pas mise en cache
    ex = ThreadPoolExecutor(1)
    try:
        return tuple(ex.submit(_tr, list(texts)).result(timeout=18))
    finally:
        ex.shutdown(wait=False)

def score(n):
    txt = (n["title"] + " " + n["summary"]).lower()
    total, best, bw = 0, "Marchés", 0
    for tag, (_, w, kws) in TAGS.items():
        v = w * min(sum(1 for k in kws if re.search(r"\b" + re.escape(k), txt)), 2)
        total += v
        if v > bw:
            best, bw = tag, v
    total += sum(1 for k in HOT if k in txt)
    age = (time.time() - n["ts"]) / 3600 if n["ts"] else 99
    return total + (2 if age < 6 else 1 if age < 24 else 0), best

def fmt(ts):
    return datetime.fromtimestamp(ts, tz=PARIS).strftime("%d/%m · %H:%M") if ts else "—"



@st.fragment(run_every="10m")
def render_bc():
    today = datetime.now(PARIS).date()
    try:
        live = cb_live()
    except Exception:
        live = {}
    try:
        mac = macro_live()
    except Exception:
        mac = {}
    pc = lambda lo, hi: (f"{lo:.2f}".replace(".", ",") + " %") if lo == hi else (f"{lo:.2f} – {hi:.2f} %".replace(".", ","))
    ST = {}
    for k_, m in CB.items():
        lo, hi = m["ref"]
        info, mv, ch = f"Référence au {REF_DATE:%d/%m/%Y} · source en ligne injoignable", m["move"], None
        L = live.get(k_)
        if L and (L[2] >= REF_DATE or (abs(L[0] - lo) < .001 and abs(L[1] - hi) < .001)):
            lo, hi, info, ch = L[0], L[1], f"● En ligne · {L[3]} · obs. {L[2]:%d/%m/%Y}", L[4]
            if ch:
                mv = f"{'Hausse' if ch[0] > 0 else 'Baisse'} de {abs(ch[0]):.0f} pb · effective le {ch[1]:%d/%m/%Y}"
        ST[k_] = (lo, hi, info, mv, ch)
    hero("Politique monétaire", "Banques Centrales", "Tout se met à jour seul : taux, inflation, spreads, actualités et réunions · cliquez sur une carte pour ouvrir la source officielle",
         f'<span class="pill">Actualisé à {datetime.now(PARIS):%H:%M}</span>')
    for col, (k_, m) in zip(st.columns(4), CB.items()):
        lo, hi, info, mv, _ = ST[k_]
        nm = upcoming(k_, today)
        nxt = f"Prochaine : {fr_range(*nm[0])}" if nm else "Prochaine : calendrier à venir"
        with col:
            st.markdown(f'<a class="lk" href="{m["url"]}" target="_blank">' + kc(f'{k_} · {m["zone"]}', pc(lo, hi),
                        f'<p><b>{m["lab"]}</b></p><p>{mv}</p><span class="pill">{nxt}</span><p style="margin-top:10px;font-size:.72rem">{info}</p><div class="src">Site officiel ↗</div>',
                        m["c"]) + '</a>', unsafe_allow_html=True)
    mids = {k_: (v[0] + v[1]) / 2 for k_, v in ST.items()}
    c1, c2 = st.columns([3, 2])
    with c1:
        sec("Niveau des taux directeurs", "En %, milieu de fourchette pour la Fed")
        ks = list(CB)[::-1]
        fig = go.Figure(go.Bar(y=ks, x=[mids[k_] for k_ in ks], orientation="h", text=[pc(*ST[k_][:2]) for k_ in ks], textposition="outside",
                               cliponaxis=False, marker=dict(color=[CB[k_]["c"] for k_ in ks])))
        fig.update_layout(height=260, margin=dict(l=0, r=90, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(visible=False, range=[0, max(5, max(mids.values()) * 1.3)]), font=dict(family="IBM Plex Sans", color="#fff"))
        show(fig, key="cb_bar")
    with c2:
        sec("Écarts de taux", "En points de base (pb)")
        tl = [("Fed − BCE", mids["Fed"] - mids["BCE"]), ("Fed − BoJ", mids["Fed"] - mids["BoJ"]), ("BCE − BoJ", mids["BCE"] - mids["BoJ"]), ("BoE − BCE", mids["BoE"] - mids["BCE"])]
        st.markdown('<div class="sg" style="grid-template-columns:repeat(2,1fr)">' + "".join(
            f'<div class="sgt"><span>{a_}</span><b>{v * 100:+.0f} pb</b></div>' for a_, v in tl) + '</div>', unsafe_allow_html=True)

    sec("Tableau de bord macro", "Inflation, emploi et dette : données officielles lues en ligne (FRED, Eurostat, BCE)")
    tiles = []
    for key, lab, unit in (("us_cpi", "Inflation États-Unis", "%"), ("us_u", "Chômage États-Unis", "%"), ("ea_hicp", "Inflation zone euro", "%"), ("fr_hicp", "Inflation France", "%"),
                           ("fr10", "Taux 10 ans France (OAT)", "%"), ("de10", "Taux 10 ans Allemagne (Bund)", "%")):
        if key in mac:
            tiles.append((f"{lab} · {mac[key][1]:%m/%Y}", f"{mac[key][0]:.2f} {unit}".replace(".", ",")))
    if "fr10" in mac and "de10" in mac:
        tiles.append(("Spread OAT-Bund", f"{(mac['fr10'][0] - mac['de10'][0]) * 100:.0f} pb"))
    if tiles:
        st.markdown('<div class="sg" style="grid-template-columns:repeat(4,1fr)">' + "".join(f'<div class="sgt"><span>{a_}</span><b>{b_}</b></div>' for a_, b_ in tiles) + '</div>', unsafe_allow_html=True)
    else:
        st.caption("Sources macro momentanément injoignables : elles seront relues automatiquement.")

    notes = []
    if "us_cpi" in mac:
        r_ = mids["Fed"] - mac["us_cpi"][0]
        notes.append(f"**Fed** : taux à {pc(*ST['Fed'][:2])} pour une inflation américaine de {mac['us_cpi'][0]:.1f} % (cible 2 %), soit un taux réel d'environ {r_:+.1f} pt : politique {'restrictive' if r_ > 1 else 'plutôt neutre' if r_ > 0 else 'encore accommodante'}.")
    if "ea_hicp" in mac:
        r_ = mids["BCE"] - mac["ea_hicp"][0]
        fr_ = f", {mac['fr_hicp'][0]:.1f} % en France" if "fr_hicp" in mac else ""
        notes.append(f"**BCE** : facilité de dépôt à {pc(*ST['BCE'][:2])} pour une inflation de {mac['ea_hicp'][0]:.1f} % en zone euro{fr_}, soit un taux réel de {r_:+.1f} pt. Les taux français sont ceux de la BCE.")
    if "fr10" in mac and "de10" in mac:
        sp = (mac["fr10"][0] - mac["de10"][0]) * 100
        notes.append(f"**France** : l'OAT 10 ans rapporte {mac['fr10'][0]:.2f} % contre {mac['de10'][0]:.2f} % pour le Bund, un spread de {sp:.0f} pb ({'prime de risque élevée' if sp > 75 else 'prime de risque modérée'}).".replace(".", ",", 0))
    gap = mids["Fed"] - mids["BoJ"]
    notes.append(f"**Écart Fed − BoJ** : {gap * 100:.0f} pb. {'Terrain favorable au carry trade, avec un risque de débouclage si la BoJ continue de monter.' if gap > 1.5 else 'Écart modéré : le carry trade yen perd de son attrait.'}")
    for k_, v in ST.items():
        if v[4] and (today - v[4][1]).days <= 45:
            notes.append(f"**{k_}** a modifié son taux il y a {(today - v[4][1]).days} jours ({v[4][0]:+.0f} pb).")
    nx = sorted((m[1], b_, m) for b_ in CB for m in upcoming(b_, today))
    if nx:
        notes.append(f"**Prochain rendez-vous** : {nx[0][1]} le {fr_range(*nx[0][2])}, dans {(date.fromisoformat(nx[0][0]) - today).days} jours.")
    sec("Lecture automatique", "Générée à partir des chiffres ci-dessus, elle évolue avec eux")
    st.markdown("\n".join(f"- {n}" for n in notes))

    sec("Réaction des marchés", "Cotations en direct")
    q = quick_quotes()
    st.markdown('<div class="sg" style="grid-template-columns:repeat(4,1fr)">' + "".join(
        f'<div class="sgt"><span>{n_}</span><b class="{"up" if q[t][1] >= 0 else "dn"}">{q[t][0]:,.2f} · {q[t][1]:+.2f}%</b></div>' for n_, t in QUICK_ALL if t in q) + '</div>', unsafe_allow_html=True)

    sec("Dernières actualités banques centrales", "Sélectionnées automatiquement dans le flux CNBC · titre d'origine et traduction")
    try:
        cbn = []
        for n in fetch_news():
            n = dict(n)
            n["score"], n["tag"] = score(n)
            if n["tag"] == "Banques centrales":
                cbn.append(n)
        cbn = sorted(cbn, key=lambda n: n["ts"], reverse=True)[:5]
        try:
            res = fr_batch(tuple(n["title"] for n in cbn))
        except Exception:
            res = [""] * len(cbn)
        rows_h = "".join(f'<a class="fl" style="--c:#C9A86A" href="{html.escape(n["link"])}" target="_blank"><span class="tm">{fmt(n["ts"])}</span>'
                         f'<div><div class="en" style="font-weight:600;font-size:.9rem">{html.escape(n["title"])}</div><div class="fr">{html.escape(r_)}</div></div>'
                         f'<span class="tag">Banques centrales</span></a>' for n, r_ in zip(cbn, res))
        st.markdown(f'<div class="tp">{rows_h or "<div class=fr style=padding:16px>Aucune actualité récente.</div>"}</div>', unsafe_allow_html=True)
    except Exception:
        st.caption("Flux d'actualités momentanément indisponible.")

    sec("Prochaines réunions", "Calendrier officiel intégré : les dates passées disparaissent toutes seules")
    rows_ = sorted((m_[1], k_, m_) for k_ in CB for m_ in upcoming(k_, today, 2))
    st.markdown(table(["Date", "Banque", "Dans", "Calendrier officiel"], [
        [fr_range(*m_), f'<b style="color:{CB[k_]["c"]}">{k_}</b>', f"{(date.fromisoformat(e_) - today).days} j", f'<a href="{CB[k_]["cal"]}" target="_blank">Voir ↗</a>']
        for e_, k_, m_ in rows_[:8]]), unsafe_allow_html=True)
    with st.expander("Et la France ? Banque de France et taux"):
        st.markdown("- Les **taux directeurs en France sont ceux de la BCE** : la Banque de France fait partie de l'Eurosystème et son gouverneur siège au Conseil des gouverneurs.\n"
                    "- La Banque de France publie les **taux d'usure** (plafond légal des crédits) et son gouverneur donne un avis sur le **taux du Livret A**, fixé par l'État.\n"
                    "- Le coût de la dette française se lit dans le **taux de l'OAT 10 ans** et son écart avec le Bund allemand.")


@st.fragment(run_every="1m")
def render_cal():
    now = datetime.now(PARIS)
    origin = datetime.combine(now.date(), datetime.min.time(), PARIS)
    now_h = (now - origin).total_seconds() / 3600
    hm = lambda h: f"{int(h) % 24:02d}:{int(round(h % 1 * 60)) % 60:02d}"
    toM = lambda t: int(t[:2]) * 60 + int(t[3:])
    reg = {"Asia": "#A9B4C2", "Australia": "#A9B4C2", "Europe": "#C9A86A", "America": "#6C9BC9"}

    def bars(tz, sess):
        z, res = ZoneInfo(tz), []
        for dd in (-1, 0, 1):
            day = datetime.now(z).date() + timedelta(days=dd)
            if day.weekday() >= 5:
                continue
            for a_, b_ in sess:
                h0 = (datetime.combine(day, datetime.strptime(a_, "%H:%M").time(), z) - origin).total_seconds() / 3600
                h1 = (datetime.combine(day, datetime.strptime(b_, "%H:%M").time(), z) - origin).total_seconds() / 3600
                if h1 > 0 and h0 < 24:
                    res.append((max(h0, 0), min(h1, 24)))
        return res

    def status(tz, sess):
        t = datetime.now(ZoneInfo(tz))
        cur = t.hour * 60 + t.minute
        if t.weekday() >= 5:
            return "Week-end", ""
        return ("Ouvert", "up") if any(toM(a_) <= cur < toM(b_) for a_, b_ in sess) else ("Fermé", "")

    def paris_hours(tz, sess):
        z = ZoneInfo(tz)
        day = datetime.now(z).date()
        conv = lambda t: datetime.combine(day, datetime.strptime(t, "%H:%M").time(), z).astimezone(PARIS).strftime("%H:%M")
        return " · ".join(f"{conv(a_)}–{conv(b_)}" for a_, b_ in sess)

    n_open = sum(status(tz, ss)[0] == "Ouvert" for _, _, tz, ss in MARKETS)
    hero("Salle de marché", "Calendrier des Marchés", "Horaires convertis en heure de Paris · changement d'heure géré automatiquement",
         f'<span class="pill up">{n_open}/{len(MARKETS)} places ouvertes</span><span class="pill">Paris {now:%H:%M}</span><span class="pill">Crypto 24/7 · Forex 24h/5j</span>')

    sec("Les 24 prochaines heures", "Sessions de négociation (heure de Paris) · la ligne rouge marque l'instant présent")
    fig = go.Figure()
    for n_, x_, tz, ss in MARKETS:
        for h0, h1 in bars(tz, ss):
            fig.add_trace(go.Bar(y=[n_], x=[h1 - h0], base=[h0], orientation="h", marker=dict(color=reg.get(tz.split("/")[0], A1), line=dict(width=0)),
                                 hovertemplate=f"<b>{n_}</b> · {x_}<br>{hm(h0)} – {hm(h1)}<extra></extra>", showlegend=False))
    fig.add_trace(go.Bar(y=["Crypto"], x=[24], base=[0], orientation="h", marker=dict(color="#D9923A", opacity=.55), hovertemplate="<b>Crypto</b> · 24/7<extra></extra>", showlegend=False))
    fig.add_vline(x=now_h, line=dict(color=DN, width=2, dash="dot"), annotation_text="Maintenant", annotation_font_color=DN)
    fig.update_layout(height=430, barmode="overlay", margin=dict(l=0, r=10, t=24, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="IBM Plex Sans", color="#CFCBC2"), xaxis=dict(range=[0, 24], tickvals=list(range(0, 25, 2)), ticktext=[f"{h:02d}h" for h in range(0, 25, 2)],
                                                                          gridcolor="rgba(255,255,255,.06)"),
                      yaxis=dict(autorange="reversed", categoryorder="array", categoryarray=[m[0] for m in MARKETS] + ["Crypto"]))
    show(fig, key="cal_gantt")

    sec("Détail par place boursière", "Jours de négociation : lundi → vendredi · jours fériés locaux non inclus")
    rows_ = ""
    for n_, x_, tz, ss in MARKETS:
        stt, cls = status(tz, ss)
        loc = " · ".join(f"{a_}–{b_}" for a_, b_ in ss)
        rows_ += (f'<tr><td>{n_}</td><td>{x_}</td><td class="mono">{loc}</td><td class="mono">{paris_hours(tz, ss)}</td>'
                  f'<td>Lun–Ven</td><td><span class="pill {cls}">{stt}</span></td></tr>')
    st.markdown('<table class="ct"><tr><th>Place</th><th>Bourse</th><th>Heures locales</th><th>Heure de Paris</th><th>Jours</th><th>Statut</th></tr>' + rows_ + '</table>',
                unsafe_allow_html=True)
    with st.expander("À savoir"):
        st.markdown("- **Hong Kong** : la pause déjeuner (12h–13h) pourrait être supprimée : HKEX étudie un allongement des horaires.\n"
                    "- **Tokyo** : clôture à 15h30 (horaires étendus depuis fin 2024).\n"
                    "- **Pré-ouvertures / enchères de clôture** non représentées ici.\n"
                    "- Vérifiez toujours le calendrier officiel de la bourse pour les jours fériés et demi-journées.")


@st.fragment(run_every="10m")
def render_news():
    hero("Intelligence de marché", "Actualités Macro", "Titres d'origine (CNBC) classés par impact estimé, avec traduction française",
         '<span class="pill">Source · CNBC</span>')
    try:
        news = []
        for n in fetch_news():
            n = dict(n)
            n["score"], n["tag"] = score(n)
            news.append(n)
    except Exception as e:
        news = []
        st.error(f"Flux indisponible : {e}")

    if news:
        top5 = sorted(news, key=lambda n: (n["score"], n["ts"]), reverse=True)[:5]
        tl_ = {n["link"] for n in top5}
        flux = sorted([n for n in news if n["link"] not in tl_], key=lambda n: n["ts"], reverse=True)[:15]

        def trio(n, frm):
            c = TAGS[n["tag"]][0]
            t_fr, s_fr = frm.get(n["link"], ("", ""))
            line = f'<div class="fr">{html.escape(t_fr)}</div>' if t_fr and t_fr.strip().lower() != n["title"].strip().lower() else ""
            return c, line, s_fr

        def top_html(frm):
            out = ""
            for i, n in enumerate(top5, 1):
                c, line, s_fr = trio(n, frm)
                lvl = min(5, 1 + n["score"] // 3)
                sm = f'<div class="sm">{html.escape(s_fr or n["summary"][:220])}</div>' if i == 1 else ""
                out += (f'<a class="tr{" f" if i == 1 else ""}" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank">'
                        f'<div class="rk2">{i}</div><div><div class="en">{html.escape(n["title"])}</div>{line}{sm}</div>'
                        f'<div class="mt2"><span class="tag">{n["tag"]}</span><div class="bars">{"".join("<i class=on></i>" if k < lvl else "<i></i>" for k in range(5))}</div>'
                        f'<span class="tm">{fmt(n["ts"])}</span></div></a>')
            return f'<div class="tp">{out}</div>'

        def flux_html(frm, sel):
            out = ""
            for n in flux:
                if sel not in (None, "Tous") and n["tag"] != sel:
                    continue
                c, line, _ = trio(n, frm)
                out += (f'<a class="fl" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank"><span class="tm">{fmt(n["ts"])}</span>'
                        f'<div><div class="en" style="font-weight:600;font-size:.9rem">{html.escape(n["title"])}</div>{line}</div>'
                        f'<span class="tag">{n["tag"]}</span></a>')
            return f'<div class="tp">{out or "<div class=fr style=padding:16px>Aucune actualité pour ce filtre.</div>"}</div>'

        sec("Le Top 5 de la semaine", "Classé par impact macro & géopolitique estimé · titre d'origine, traduction en dessous")
        top_box = st.empty()
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        sec("Le Flux du Jour", "Du plus récent au plus ancien",
            f'<a class="btn" href="{AGGREGATOR}" target="_blank">Toutes les infos en temps réel ↗</a>')
        opts = ["Tous"] + list(TAGS)
        sel = (st.pills("Filtre", opts, default="Tous", label_visibility="collapsed") if hasattr(st, "pills")
               else st.radio("Filtre", opts, horizontal=True, label_visibility="collapsed"))
        flux_box = st.empty()
        note = st.empty()
        top_box.markdown(top_html({}), unsafe_allow_html=True)
        flux_box.markdown(flux_html({}, sel), unsafe_allow_html=True)
        note.caption("Traduction en cours…")
        try:
            items = top5 + flux
            summ = top5[0]["summary"][:240].rsplit(" ", 1)[0] or top5[0]["title"]
            res = fr_batch(tuple([n["title"] for n in items] + [summ]))
            frm = {n["link"]: (res[i], "") for i, n in enumerate(items)}
            frm[top5[0]["link"]] = (res[0], res[-1])
            top_box.markdown(top_html(frm), unsafe_allow_html=True)
            flux_box.markdown(flux_html(frm, sel), unsafe_allow_html=True)
            note.empty()
        except Exception:
            note.caption("Traduction momentanément indisponible : titres affichés en anglais. Rechargez dans un instant.")


if category in UNIVERSE:
    render_market(category)
elif category == "🏦 Banques Centrales":
    render_bc()
elif category == "🕐 Calendrier des Marchés":
    render_cal()
elif category == "📰 Actualités Macro (FR)":
    render_news()


# =====================================================================
#  PAGE : BASE DE CONNAISSANCES
# =====================================================================
elif category == "📚 Base de Connaissances":
    hero("Repères institutionnels", "Base de Connaissances", "France, marchés, taux, économies, matières premières et glossaire de salle de marché",
         '<span class="pill">Ordres de grandeur 2025-2026 · crypto et PIB actualisés en ligne</span>')
    try:
        C_ = crypto_live()
    except Exception:
        C_ = {}
    try:
        G_ = gdp_live()
    except Exception:
        G_ = {}
    CRY_TXT = f"≈ {C_['cap']:,.0f} Mds $".replace(",", " ") if C_ else "≈ 2 500 Mds $"
    GD = lambda n_, d_: (f"≈ {G_[n_][0]:,.0f} Mds $ ({G_[n_][1]})".replace(",", " ") if n_ in G_ else d_)
    st.markdown('<div class="sg">' + "".join(f'<div class="sgt"><span>{a_}</span><b>{b_}</b></div>' for a_, b_ in [
        ("PIB États-Unis", GD("États-Unis", "≈ 28 000 Mds $")), ("PIB France", GD("France", "≈ 3 100 Mds $")), ("Crypto-marché", CRY_TXT),
        ("Top 5 du S&P 500", "≈ 25 % de l'indice")]) + '</div>', unsafe_allow_html=True)
    T = st.tabs(["France", "Capitalisations", "Indices", "Banques centrales", "Économies", "Matières premières", "Blocs & Alliances", "Calendrier macro", "Glossaire"])

    with T[0]:
        st.markdown(table(["Repère", "Ordre de grandeur", "À retenir"], [
            ["PIB nominal", "≈ 3 100 Mds $", "7e économie mondiale, 3e d'Europe derrière l'Allemagne et le Royaume-Uni"],
            ["Dette publique", "≈ 115-118 % du PIB", "Parmi les plus élevées de la zone euro : suivie via le spread OAT-Bund"],
            ["Déficit public", "≈ 5 % du PIB", "Au-dessus du plafond de 3 % du Pacte de stabilité européen"],
            ["Monnaie & taux", "Euro · BCE", "Les taux directeurs sont fixés par la BCE à Francfort"],
            ["Bourse", "Euronext Paris", "CAC 40 : 40 grandes valeurs, base 1 000 au 31/12/1987"]]), unsafe_allow_html=True)
        sec("Les fleurons par secteur", "Survolez une entreprise pour voir son activité")
        SECT = [("Luxe", ["LVMH", "Hermès", "Kering"], "#A9B4C2"), ("Énergie", ["TotalEnergies", "Engie"], "#C77D4A"),
                ("Santé", ["Sanofi", "EssilorLuxottica"], "#46B37D"), ("Industrie & Défense", ["Airbus", "Safran", "Thales", "Schneider Electric", "Vinci"], "#6C9BC9"),
                ("Finance", ["BNP Paribas", "AXA", "Société Générale", "Crédit Agricole"], "#C9A86A"),
                ("Conso & Auto", ["L'Oréal", "Danone", "Pernod Ricard", "Stellantis", "Michelin"], "#D9923A")]
        for r_ in (0, 3):
            for col, (t_, names, c_) in zip(st.columns(3), SECT[r_:r_ + 3]):
                with col:
                    st.markdown(kc(t_, "", chips(names), c_), unsafe_allow_html=True)
        sec("Institutions & repères", "Qui fait quoi dans la finance française")
        for t_, d_ in [
            ("CAC 40", "Indice des 40 plus grosses capitalisations flottantes cotées à Paris, créé fin 1987 (base 1 000). Très exposé au luxe, à l'énergie, à l'aéronautique et à la finance, avec une majorité de revenus réalisés hors de France."),
            ("Euronext", "Bourse paneuropéenne qui exploite Paris, Amsterdam, Bruxelles, Lisbonne, Dublin, Milan et Oslo."),
            ("AMF & ACPR", "L'**AMF** régule les marchés financiers et protège les épargnants ; l'**ACPR** (adossée à la Banque de France) supervise banques et assurances."),
            ("Agence France Trésor (AFT)", "Émet la dette de l'État : **OAT** (obligations à long terme), **BTF** (court terme) et **BTAN**. Elle publie le calendrier des adjudications."),
            ("Insee", "Produit les statistiques officielles : PIB trimestriel, inflation (IPC), chômage, climat des affaires."),
            ("Spread OAT-Bund", "Écart entre le taux français à 10 ans et le taux allemand : le baromètre de la prime de risque France. Il s'élargit quand la confiance dans les finances publiques ou la stabilité politique baisse.")]:
            with st.expander(t_):
                st.markdown(d_)

    with T[1]:
        try:
            caps = caps_live()
        except Exception:
            caps = []
        if caps:
            st.caption("Capitalisations lues sur Yahoo Finance, converties en dollars · actualisées toutes les 30 min · survolez un nom pour voir l'activité")
            tiers = [("Plus de 3 000 Mds $", 3000, 1e9, "#E3A33B"), ("2 000 à 3 000 Mds $", 2000, 3000, "#B9BEC6"),
                     ("1 000 à 2 000 Mds $", 1000, 2000, "#C77D4A"), ("500 à 1 000 Mds $", 500, 1000, "#6C9BC9")]
            for col, (lab, lo, hi, clr) in zip(st.columns(4), tiers):
                names = [(n, v) for n, v, _ in caps if lo <= v < hi]
                body = "".join(f'<span class="co tip" data-tip="{html.escape(TIPS.get(n, n))}">{n}<b>{fnum(v, 0)}</b></span>' for n, v in names) or "<p>Aucune société suivie dans cette tranche.</p>"
                with col:
                    st.markdown(kc(lab, f"{len(names)} société{'s' if len(names) > 1 else ''}", body, clr), unsafe_allow_html=True)
            sec("Classement mondial", "Mds $ · en ambre : sociétés françaises")
            top = caps[:15]
            fig = go.Figure(go.Bar(y=[n for n, _, _ in top], x=[v for _, v, _ in top], orientation="h", text=[fnum(v, 0) for _, v, _ in top],
                                   textposition="outside", cliponaxis=False, marker=dict(color=["#E3A33B" if n in FR_NAMES else "#6C9BC9" for n, _, _ in top])))
            fig.update_layout(height=480, margin=dict(l=0, r=60, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(autorange="reversed", color="#CFCBC2"))
            show(fig, key="caps_rank")
            sec("Les géants français", "Rang parmi les sociétés suivies")
            rk = {n: i + 1 for i, (n, _, _) in enumerate(caps)}
            st.markdown(table(["Société", "Capitalisation", "Rang"], [[n, f"{fnum(v, 0)} Mds $", f"n°{rk[n]}"] for n, v, _ in caps if n in FR_NAMES]), unsafe_allow_html=True)
        else:
            st.warning("Capitalisations momentanément indisponibles chez Yahoo Finance : elles se rechargeront automatiquement.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="kc"><h4>Total crypto-marché</h4><div class="big">' + CRY_TXT + '</div>', unsafe_allow_html=True)
            show(gauge(round(C_["btc"], 1) if C_ else 52.5, "Dominance du Bitcoin", color="#E3A33B"), key="btc_dom")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(kc("Top 5 du S&P 500", "≈ 25 % de l'indice", ranks([("<b>Microsoft</b>", "Tech · Cloud · IA"), ("<b>Apple</b>", "Hardware · Services"),
                         ("<b>NVIDIA</b>", "Semi-conducteurs · IA"), ("<b>Amazon</b>", "E-commerce · Cloud"), ("<b>Alphabet</b>", "Publicité · Recherche")])), unsafe_allow_html=True)

    with T[2]:
        st.markdown(table(["Indice", "Zone", "Composition", "À retenir"], [
            ["S&P 500", "États-Unis", "500 grandes valeurs", "Pondéré par la capitalisation flottante · référence mondiale"],
            ["Nasdaq 100", "États-Unis", "100 valeurs non financières", "Très orienté tech et IA"],
            ["Dow Jones", "États-Unis", "30 valeurs", "Pondéré par le prix des actions, pas par la taille"],
            ["Russell 2000", "États-Unis", "≈ 2 000 petites capitalisations", "Baromètre de l'économie domestique"],
            ["CAC 40", "France", "40 valeurs d'Euronext Paris", "Luxe, énergie, aéro, santé · base 1 000 en 1987"],
            ["SBF 120", "France", "120 valeurs", "CAC 40 élargi aux valeurs moyennes"],
            ["Euronext 100", "Europe", "100 valeurs d'Euronext", "Paris, Amsterdam, Bruxelles, Lisbonne…"],
            ["Euro Stoxx 50", "Zone euro", "50 valeurs", "Sous-jacent des futures européens"],
            ["Stoxx Europe 600", "Europe", "600 valeurs, 17 pays", "Large couverture du marché européen"],
            ["DAX 40", "Allemagne", "40 valeurs", "Passé de 30 à 40 valeurs en 2021"],
            ["FTSE 100", "Royaume-Uni", "100 valeurs", "Beaucoup de revenus en devises : énergie, banques, matières premières"],
            ["Nikkei 225", "Japon", "225 valeurs", "Pondéré par le prix"],
            ["Hang Seng", "Hong Kong", "≈ 80 valeurs et plus", "Tech et finance chinoises"],
            ["CSI 300", "Chine", "300 valeurs Shanghai/Shenzhen", "Référence des actions A"],
            ["Nifty 50", "Inde", "50 valeurs de la NSE", "Reliance, TCS, HDFC Bank en tête"],
            ["MSCI World", "Monde", "≈ 1 400 valeurs, pays développés", "Benchmark de la gestion d'actifs"],
            ["MSCI Emerging", "Émergents", "≈ 1 200 valeurs", "Chine, Inde, Taïwan, Corée dominent"]]), unsafe_allow_html=True)
        with st.expander("Leaders par indice"):
            st.markdown("- **CAC 40** : LVMH, TotalEnergies, Hermès, Schneider Electric, Sanofi (parmi les plus fortes pondérations)\n"
                        "- **Nifty 50 (Inde)** : Reliance Industries (conglomérat de Mukesh Ambani), TCS (services IT), HDFC Bank\n"
                        "- **Stoxx 600 (Europe)** : Novo Nordisk (santé/diabète), LVMH (luxe), ASML (semi-conducteurs/EUV)")

    with T[3]:
        st.markdown(table(["Banque", "Zone", "Taux de référence", "Mandat", "Réunions"], [
            ["Fed", "États-Unis", "Fed funds (fourchette cible)", "Double mandat : plein-emploi + stabilité des prix (cible 2 %)", "8 / an"],
            ["BCE", "Zone euro", "Facilité de dépôt", "Stabilité des prix, cible symétrique de 2 %", "8 / an"],
            ["BoJ", "Japon", "Taux au jour le jour", "Stabilité des prix, cible 2 %", "8 / an"],
            ["BoE", "Royaume-Uni", "Bank Rate", "Inflation (IPC) à 2 %", "8 / an"],
            ["SNB", "Suisse", "Taux directeur SNB", "Stabilité des prix (inflation inférieure à 2 %)", "4 / an"],
            ["PBoC", "Chine", "LPR (Loan Prime Rate)", "Stabilité de la monnaie et soutien à la croissance", "LPR mensuel"]]), unsafe_allow_html=True)
        st.info("Les niveaux actuels des taux sont dans la page « Banques Centrales » du menu.")
        with st.expander("Les outils d'une banque centrale"):
            st.markdown("- **Taux directeurs** : le levier principal.\n- **QE / QT** : achats d'actifs ou réduction du bilan.\n"
                        "- **Forward guidance** : annoncer la trajectoire future des taux.\n- **Dot plot** : projections de taux des membres du FOMC, 4 fois par an.")

    with T[4]:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="kc"><h4>Top 10 · PIB nominal (Mds $, ordres de grandeur)</h4>', unsafe_allow_html=True)
            ce = ["États-Unis", "Chine", "Allemagne", "Japon", "Inde", "Royaume-Uni", "France", "Italie", "Brésil", "Canada"]
            ve = [28000, 18500, 4500, 4200, 3900, 3600, 3100, 2300, 2200, 2200]
            if G_:
                pr_ = sorted(((k, v[0]) for k, v in G_.items()), key=lambda kv: -kv[1])
                ce, ve = [x[0] for x in pr_], [round(x[1]) for x in pr_]
            fig = go.Figure(go.Bar(y=ce, x=ve, orientation="h", text=[f"~{v:,}".replace(",", " ") for v in ve], textposition="outside", cliponaxis=False,
                                   marker=dict(color=["#6C9BC9" if c == "France" else A1 for c in ce])))
            fig.update_layout(height=400, margin=dict(l=0, r=70, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(visible=False), yaxis=dict(autorange="reversed", color="#CFCBC2"), font=dict(family="IBM Plex Sans", color="#fff"))
            show(fig, key="gdp")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(kc("Les plus grandes économies d'Europe", "", ranks([("<b>Allemagne</b>", "Moteur industriel"), ("<b>Royaume-Uni</b>", "Finance & services"),
                         ("<b>France</b>", "Luxe · aéro · énergie"), ("<b>Italie</b>", "Manufacturier"), ("<b>Espagne</b>", "Tourisme & services")])), unsafe_allow_html=True)
        with st.expander("Contexte : Allemagne, Japon, Inde"):
            st.markdown("L'**Allemagne** a récemment dépassé le **Japon** suite à la faiblesse du Yen. L'**Inde**, en forte croissance, vise le top 3 avant 2030.")

    with T[5]:
        COM = [("Pétrole (barils/jour)", ["États-Unis", "Arabie saoudite", "Russie"], "Le Brent est la référence européenne. La France produit très peu de brut : TotalEnergies est un acteur mondial."),
               ("Gaz naturel", ["États-Unis", "Russie", "Iran"], "Le GNL a pris le relais du gaz russe en Europe."),
               ("Or (mines)", ["Chine", "Australie", "Russie"], "Valeur refuge, très demandée par les banques centrales."),
               ("Argent", ["Mexique", "Chine", "Pérou"], "À la fois métal précieux et métal industriel (solaire)."),
               ("Cuivre", ["Chili", "Pérou", "RDC (Congo)"], "« Dr. Copper » : baromètre de l'activité industrielle."),
               ("Lithium (batteries)", ["Australie", "Chili", "Chine"], "Clé de la voiture électrique."),
               ("Uranium", ["Kazakhstan", "Canada", "Namibie"], "Le nucléaire fournit environ deux tiers de l'électricité française (EDF, Orano)."),
               ("Blé", ["Chine", "Inde", "Russie"], "La France est le premier producteur de l'UE et un grand exportateur."),
               ("Cacao", ["Côte d'Ivoire", "Ghana"], "Ces deux pays assurent plus de la moitié de l'offre mondiale."),
               ("Café", ["Brésil", "Vietnam", "Colombie"], "Très sensible aux aléas climatiques brésiliens."),
               ("Platine", ["Afrique du Sud", "Russie", "Zimbabwe"], "Catalyseurs automobiles et hydrogène.")]
        for k_, (name, top, note_) in enumerate(COM):
            with st.expander(name, expanded=(k_ == 0)):
                st.markdown(ranks(top) + f'<p style="color:#8E9099;font-size:.85rem;margin-top:8px">{note_}</p>', unsafe_allow_html=True)

    with T[6]:
        BL = [("G7", "États-Unis, Japon, Allemagne, Royaume-Uni, France, Italie, Canada (+ UE invitée)."),
              ("G20", "Le G7 plus les grandes économies émergentes (Chine, Inde, Brésil, Arabie saoudite…), l'UE et l'Union africaine : plus de 80 % du PIB mondial."),
              ("Union européenne", "27 États membres, marché unique, institutions à Bruxelles et Strasbourg."),
              ("Zone euro", "21 pays (dont la Bulgarie, entrée le 1er janvier 2026), monnaie unique, politique monétaire de la BCE à Francfort."),
              ("OTAN", "Alliance militaire de 32 membres depuis l'adhésion de la Suède en 2024."),
              ("OCDE", "38 pays, siège à Paris : produit les statistiques et recommandations économiques de référence."),
              ("BRICS+", "Brésil, Russie, Inde, Chine, Afrique du Sud, rejoints récemment par l'Iran, l'Égypte, l'Éthiopie et les Émirats arabes unis."),
              ("OPEP+", "Cartel pétrolier mené par l'Arabie saoudite, allié à la Russie pour contrôler l'offre mondiale de brut."),
              ("ASEAN", "10 pays d'Asie du Sud-Est : Indonésie, Thaïlande, Vietnam, Singapour, Malaisie, Philippines…"),
              ("ACEUM (ex-ALENA)", "Accord commercial États-Unis, Mexique et Canada.")]
        cl, cr = st.columns(2)
        for k_, (t_, d_) in enumerate(BL):
            with (cl if k_ % 2 == 0 else cr):
                with st.expander(t_, expanded=(k_ < 2)):
                    st.markdown(d_)

    with T[7]:
        st.markdown(table(["Indicateur", "Zone", "Rythme", "Publié par", "Pourquoi ça bouge les marchés"], [
            ["Emploi non agricole (NFP)", "États-Unis", "Mensuel, 1er vendredi", "BLS", "Cap de la Fed : emploi et salaires"],
            ["Inflation (CPI)", "États-Unis", "Mensuel, mi-mois", "BLS", "Anticipations de taux directeurs"],
            ["Déflateur PCE", "États-Unis", "Mensuel, fin de mois", "BEA", "Indicateur d'inflation préféré de la Fed"],
            ["Demandes d'allocations", "États-Unis", "Hebdomadaire, jeudi", "Département du Travail", "Thermomètre du marché du travail"],
            ["PMI / ISM", "Monde", "Mensuel", "S&P Global / ISM", "Au-dessus de 50 : expansion"],
            ["Inflation flash", "Zone euro", "Mensuel, début de mois", "Eurostat", "Trajectoire des taux de la BCE"],
            ["IPC et PIB trimestriel", "France", "Mensuel / trimestriel", "Insee", "Croissance, inflation, finances publiques"],
            ["Climat des affaires, confiance des ménages", "France", "Mensuel", "Insee", "Indicateurs avancés de l'activité"],
            ["Balance commerciale", "France", "Mensuel", "Douanes", "Compétitivité, aéronautique, énergie"],
            ["Ifo / ZEW", "Allemagne", "Mensuel", "Ifo / ZEW", "Moral de l'industrie allemande"],
            ["Tankan", "Japon", "Trimestriel", "Banque du Japon", "Confiance des entreprises japonaises"],
            ["Réunions FOMC, BCE, BoJ, BoE", "Monde", "8 par an chacune", "Banques centrales", "Décisions et discours qui font les marchés"]]), unsafe_allow_html=True)

    with T[8]:
        q = st.text_input("Rechercher un terme", placeholder="ex. spread, carry, duration…").strip().lower()
        GL = [("Point de base (pb)", "0,01 % : une hausse de 25 pb correspond à +0,25 point."),
              ("Spread", "Écart de rendement entre deux titres ou taux. Mesure le risque relatif."),
              ("Spread OAT-Bund", "Écart entre le taux français et le taux allemand à 10 ans : prime de risque de la France."),
              ("Courbe des taux", "Rendements selon l'échéance (2 ans, 10 ans…). Une courbe pentue traduit des attentes de croissance."),
              ("Inversion de courbe", "Taux courts supérieurs aux taux longs : signal historique de récession."),
              ("Duration", "Sensibilité d'une obligation aux taux : duration 7, environ −7 % si les taux montent d'un point."),
              ("QE / QT", "Assouplissement quantitatif (achats d'actifs) ou resserrement (réduction du bilan)."),
              ("Forward guidance", "Communication de la banque centrale sur sa trajectoire future de taux."),
              ("Dot plot", "Graphique des projections de taux des membres du FOMC, publié 4 fois par an."),
              ("Carry trade", "Emprunter dans une devise à bas taux (yen) pour placer dans une devise mieux rémunérée. Risque de débouclage brutal."),
              ("Risk-on / Risk-off", "Appétit ou aversion pour le risque. En risk-off : or, yen, franc suisse et Treasuries sont recherchés."),
              ("VIX / MOVE", "Volatilité implicite des actions (S&P 500) / des taux (Treasuries)."),
              ("Contango / Backwardation", "Contrat à terme plus cher / moins cher que le prix comptant."),
              ("Bid-ask", "Écart entre prix d'achat et de vente : le coût de la liquidité."),
              ("Market maker", "Teneur de marché : cote en continu un prix d'achat et de vente."),
              ("Short squeeze", "Hausse brutale quand les vendeurs à découvert doivent racheter."),
              ("Levier & appel de marge", "Position plus grosse que le capital engagé ; si les pertes grossissent, la banque exige des fonds supplémentaires."),
              ("Repo", "Prêt de liquidités contre des titres donnés en garantie."),
              ("CDS", "Assurance contre le défaut d'un émetteur ; son prix reflète le risque de crédit."),
              ("Taux réel", "Taux nominal moins l'inflation."),
              ("Stagflation", "Croissance faible avec inflation élevée."),
              ("Soft / Hard landing", "Ralentissement maîtrisé de l'économie / récession brutale."),
              ("PMI", "Indice des directeurs d'achat : au-dessus de 50, l'activité progresse."),
              ("Capitalisation boursière", "Valeur d'une entreprise cotée : cours de l'action × nombre d'actions. Large cap : plus de 10 Mds $ ; mid cap : 2 à 10 Mds $ ; small cap : moins de 2 Mds $."),
              ("Inflation", "Hausse générale et durable des prix : la monnaie perd du pouvoir d'achat."),
              ("Désinflation", "L'inflation ralentit mais reste positive : les prix montent toujours, moins vite (de 6 % à 3 % par an, par exemple)."),
              ("Déflation", "Baisse générale des prix (inflation négative). Dangereuse car les ménages reportent leurs achats et l'activité s'enraye."),
              ("Hyperinflation", "Inflation extrême, souvent plus de 50 % par mois : la monnaie s'effondre."),
              ("Récession", "Recul du PIB pendant au moins deux trimestres consécutifs."),
              ("PIB", "Produit intérieur brut : valeur de tout ce qu'un pays produit en un an."),
              ("Croissance", "Variation du PIB d'une période à l'autre, en %."),
              ("Taux de chômage", "Part des actifs sans emploi qui en cherchent un."),
              ("Pouvoir d'achat", "Quantité de biens qu'un revenu permet d'acheter ; baisse si les prix montent plus vite que les salaires."),
              ("IPC / IPCH", "Indice des prix à la consommation, et sa version harmonisée européenne : les thermomètres de l'inflation."),
              ("Taux directeur", "Taux fixé par la banque centrale ; il influence tous les autres taux (crédits, épargne, obligations)."),
              ("Hawkish / Dovish", "Banque centrale « faucon » : plutôt pour des taux hauts contre l'inflation ; « colombe » : plutôt pour des taux bas pour soutenir l'économie."),
              ("Politique monétaire / budgétaire", "Monétaire : taux et monnaie, décidés par la banque centrale. Budgétaire : impôts et dépenses publiques, décidés par le gouvernement."),
              ("Action", "Part de propriété d'une entreprise ; donne droit à une partie des bénéfices (dividende) et aux plus-values."),
              ("Obligation", "Prêt à un État ou une entreprise : on touche des intérêts (coupon) et on récupère le capital à l'échéance."),
              ("ETF / tracker", "Fonds coté en bourse qui réplique un indice (CAC 40, S&P 500) à faible coût."),
              ("Indice boursier", "Panier d'actions qui mesure la santé d'un marché (CAC 40, S&P 500…)."),
              ("Dividende", "Part du bénéfice versée aux actionnaires."),
              ("PER", "Price Earning Ratio : cours ÷ bénéfice par action. Un PER élevé signifie que l'action est chère par rapport à ses profits."),
              ("Rendement (yield)", "Gain annuel d'un placement rapporté à son prix : pour une obligation, intérêts ÷ prix."),
              ("Coupon", "Intérêt périodique versé par une obligation."),
              ("Notation de crédit", "Note de solvabilité d'un émetteur par les agences (de AAA, la meilleure, à D, le défaut). Plus la note est basse, plus il paie cher pour emprunter."),
              ("Dette et déficit publics", "Le déficit est l'écart annuel entre dépenses et recettes de l'État ; la dette est l'accumulation des déficits passés."),
              ("Balance commerciale", "Exportations moins importations de biens : excédent si positif, déficit sinon."),
              ("Taux de change", "Prix d'une monnaie en une autre (1 € = x $). Un euro fort pénalise les exportateurs mais baisse le prix des importations."),
              ("Dépréciation / dévaluation", "Baisse de la valeur d'une monnaie : sur le marché pour la dépréciation, décidée par l'État pour la dévaluation."),
              ("Bull / Bear market", "Marché haussier (hausse de 20 % ou plus depuis le creux) / baissier (baisse de 20 % ou plus depuis le sommet)."),
              ("Correction / Krach", "Correction : baisse de 10 % à 20 %. Krach : chute brutale et profonde."),
              ("IPO", "Introduction en bourse : première cotation d'une entreprise."),
              ("Valeur refuge", "Actif recherché en période de crise : or, franc suisse, yen, dette américaine ou allemande."),
              ("Liquidité", "Facilité à acheter ou vendre un actif rapidement sans en bouger le prix."),
              ("Volatilité", "Amplitude des variations de prix : forte volatilité signifie des mouvements brusques et un risque plus élevé."),
              ("Position longue / courte", "Longue : on achète en espérant la hausse. Courte : on vend à découvert en espérant la baisse."),
              ("Option (call / put)", "Droit, sans obligation, d'acheter (call) ou de vendre (put) un actif à un prix fixé et avant une date donnée."),
              ("Future", "Contrat à terme : engagement d'acheter ou de vendre un actif à un prix et une date fixés à l'avance."),
              ("Produit dérivé", "Instrument dont la valeur dépend d'un autre actif (options, futures, swaps)."),
              ("Hedge fund", "Fonds spéculatif qui utilise levier, vente à découvert et dérivés pour viser un gain en tout type de marché."),
              ("Sell-side / Buy-side", "Sell-side : banques qui vendent des services et des produits (sales, traders, recherche). Buy-side : investisseurs qui achètent (gérants, hedge funds)."),
              ("Fonds souverain", "Fonds d'investissement détenu par un État, souvent financé par les matières premières (Norvège, Arabie saoudite)."),
              ("Diversification", "Répartir ses placements sur plusieurs actifs pour réduire le risque."),
              ("Plus-value / moins-value", "Gain / perte réalisé quand on vend un actif plus cher / moins cher qu'on l'a acheté.")]
        GL.sort(key=lambda g: g[0].lower())
        hit = [g for g in GL if q in g[0].lower() or q in g[1].lower()]
        if not hit:
            st.info("Aucun terme trouvé.")
        cl, cr = st.columns(2)
        for k_, (t_, d_) in enumerate(hit):
            with (cl if k_ % 2 == 0 else cr):
                with st.expander(t_):
                    st.markdown(d_)
        with st.expander("Salle de marché : qui fait quoi ?"):
            st.markdown("- **Sales** : relation avec les clients institutionnels, idées de trading, prise d'ordres.\n"
                        "- **Trader** : cote les prix, gère le risque de son portefeuille.\n"
                        "- **Structureur** : conçoit des produits dérivés sur mesure.\n"
                        "- **Quant / Strats** : modèles de pricing et outils.\n"
                        "- **Recherche (sell-side)** : analyses publiées pour les clients.\n"
                        "- **Middle & back office** : contrôle des risques, confirmation et règlement-livraison.\n"
                        "- Salles de marché françaises majeures : BNP Paribas, Société Générale, Natixis, Crédit Agricole CIB.")
