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
        "Euronext 100": "^N100",
        "Stoxx Europe 600": "^STOXX",
        "CAC 40 ETF (Amundi)": "CAC.PA",
        "AEX (Pays-Bas)": "^AEX",
        "IBEX 35 (Espagne)": "^IBEX",
        "FTSE MIB (Italie)": "FTSEMIB.MI",
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
        "Cacao (Côte d'Ivoire)": "CC=F",
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

/* Cartes cliquables : le bouton invisible recouvre toute la carte */
[class*="st-key-card_"]{position:relative;cursor:pointer}
[class*="st-key-btn_"]{position:absolute!important;inset:0;z-index:5;width:100%!important;height:100%!important;margin:0!important}
[class*="st-key-btn_"] div,[class*="st-key-btn_"] button{width:100%!important;height:100%!important;opacity:0;cursor:pointer}
.mt{position:relative;padding-right:20px}
.mt .ex{position:absolute;right:0;top:0;opacity:.4;transition:.25s}
[class*="st-key-card_"]:hover .ex{opacity:1;color:var(--a2)}

/* Top 5 compact */
.hl{display:block;position:relative;overflow:hidden;text-decoration:none!important;padding:24px 26px;border-radius:20px;min-height:276px;background:linear-gradient(150deg,rgba(255,255,255,.08),rgba(255,255,255,.015));border:1px solid var(--bd);box-shadow:0 12px 34px rgba(0,0,0,.4);transition:.3s}
.hl::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--c),transparent)}
.hl:hover{transform:translateY(-3px);border-color:var(--c);box-shadow:0 0 30px -6px var(--c)}
.hl-t{color:#fff;font-weight:800;font-size:1.4rem;line-height:1.3;margin:6px 0 12px}
.hl-s{color:#AEB6CA;font-size:.9rem;line-height:1.55}
.sl{display:flex;gap:14px;align-items:center;text-decoration:none!important;padding:10px 14px;border-radius:14px;margin-bottom:8px;min-height:62px;background:rgba(255,255,255,.04);border:1px solid var(--bd);border-left:3px solid var(--c);transition:.25s}
.sl:hover{background:rgba(255,255,255,.08);transform:translateX(4px)}
.sl .rank{font-size:1.1rem}
.sl-t{color:#F1F5F9;font-weight:600;font-size:.88rem;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.sl-m{display:flex;gap:8px;align-items:center;margin-top:4px;font-size:.7rem;color:#6B7389}

/* Vue détaillée */
.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}
.sgt{padding:10px 12px;border-radius:12px;background:rgba(255,255,255,.05);border:1px solid var(--bd)}
.sgt span{display:block;font-size:.65rem;letter-spacing:1px;text-transform:uppercase;color:var(--mut)}
.sgt b{font-family:'JetBrains Mono',monospace;font-size:1.05rem}
.sgt b.up{color:var(--up)}.sgt b.dn{color:var(--dn)}
.rb{position:relative;height:8px;border-radius:8px;background:linear-gradient(90deg,var(--dn),#FBBF24,var(--up));margin:10px 0 4px}
.rb i{position:absolute;top:-4px;width:6px;height:16px;border-radius:4px;background:#fff;box-shadow:0 0 10px #fff}
.rl{display:flex;justify-content:space-between;font-size:.72rem;color:var(--mut);font-family:'JetBrains Mono',monospace}

/* Calendrier */
.ct{width:100%;border-collapse:separate;border-spacing:0 8px}
.ct th{padding:6px 14px;text-align:left;font-size:.68rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--mut);font-weight:600}
.ct td{padding:13px 14px;background:rgba(255,255,255,.04);border-top:1px solid var(--bd);border-bottom:1px solid var(--bd);font-size:.9rem}
.ct td:first-child{border-left:1px solid var(--bd);border-radius:12px 0 0 12px;font-weight:700}
.ct td:last-child{border-right:1px solid var(--bd);border-radius:0 12px 12px 0}
.ct .mono{font-family:'JetBrains Mono',monospace;font-size:.82rem;color:#CBD3E6}

/* Nav latérale v2 */
section[data-testid="stSidebar"] div[role="radiogroup"]{gap:3px}
section[data-testid="stSidebar"] div[role="radiogroup"]>label{position:relative;padding:6px 10px;border-radius:14px}
section[data-testid="stSidebar"] div[role="radiogroup"]>label p::before{content:"";flex:none;width:34px;height:34px;margin-right:12px;border-radius:11px;background:var(--ic) center/17px no-repeat,rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);transition:.25s}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:hover p::before{background:var(--ic) center/17px no-repeat,rgba(99,102,241,.25)}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked){background:linear-gradient(90deg,rgba(99,102,241,.18),transparent);border-color:rgba(129,140,248,.25);box-shadow:none}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked) p::before{background:var(--ic) center/17px no-repeat,linear-gradient(135deg,#6366F1,#22D3EE);border-color:transparent;box-shadow:0 0 18px rgba(99,102,241,.6)}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked)::after{content:"";position:absolute;left:-16px;top:24%;height:52%;width:4px;border-radius:4px;background:linear-gradient(var(--a1),var(--a2));box-shadow:0 0 12px var(--a2)}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:nth-child(10){margin-top:16px}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:nth-child(10)::before{content:"";position:absolute;left:10px;right:10px;top:-9px;height:1px;background:var(--bd)}

/* Actualités v3 : panneau compact */
.tp{border-radius:20px;overflow:hidden;background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(255,255,255,.015));border:1px solid var(--bd);box-shadow:0 12px 34px rgba(0,0,0,.4);margin-bottom:10px}
.tr{display:grid;grid-template-columns:42px 1fr auto;gap:14px;align-items:center;padding:13px 18px;text-decoration:none!important;border-bottom:1px solid rgba(255,255,255,.06);border-left:3px solid var(--c);transition:.25s}
.tr:last-child{border-bottom:0}.tr:hover{background:rgba(255,255,255,.05)}
.tr.f{background:linear-gradient(90deg,color-mix(in srgb,var(--c) 15%,transparent),transparent 65%)}
.rk2{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;font-family:'JetBrains Mono',monospace;font-weight:700;color:#fff;background:linear-gradient(135deg,var(--c),color-mix(in srgb,var(--c) 40%,#000))}
.en{color:#fff;font-weight:700;font-size:.95rem;line-height:1.3}.tr.f .en{font-size:1.1rem}
.fr{color:#9AA4BC;font-size:.84rem;line-height:1.35;margin-top:3px;font-style:italic}
.sm{color:#7F89A1;font-size:.8rem;margin-top:6px;line-height:1.45}
.mt2{display:flex;flex-direction:column;align-items:flex-end;gap:6px;min-width:130px}
.bars{display:flex;gap:3px}.bars i{width:14px;height:5px;border-radius:3px;background:rgba(255,255,255,.12)}.bars i.on{background:var(--c)}
.tm{font-size:.7rem;color:#6B7389;font-family:'JetBrains Mono',monospace}
.fl{display:grid;grid-template-columns:96px 1fr auto;gap:12px;align-items:center;padding:10px 16px;text-decoration:none!important;border-bottom:1px solid rgba(255,255,255,.05);transition:.2s}
.fl:last-child{border-bottom:0}.fl:hover{background:rgba(99,102,241,.1)}
@media(max-width:760px){.tr{grid-template-columns:36px 1fr}.mt2{flex-direction:row;align-items:center;grid-column:2}.fl{grid-template-columns:1fr}}
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


def icon_css():
    out = "<style>"
    for i, paths in enumerate(ICONS, 1):
        svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' "
               "stroke-linecap='round' stroke-linejoin='round'>" + paths + "</svg>")
        out += (f'section[data-testid="stSidebar"] div[role="radiogroup"]>label:nth-child({i}){{--ic:url("data:image/svg+xml,{quote(svg)}")}}')
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


def show(fig, key=None, static=False):
    cfg = {'displayModeBar': False, 'staticPlot': static}
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


def kc(title, big="", body="", color="#A5B4FC"):
    return (f'<div class="kc" style="--c:{color}"><h4>{title}</h4>' + (f'<div class="big">{big}</div>' if big else "") + body + '</div>')


# ---- TAUX DIRECTEURS : À METTRE À JOUR APRÈS CHAQUE RÉUNION (saisie manuelle) ----
CB_DATE = "06/10/2026"
CB = [  # (banque, zone, affichage, valeur médiane, nom du taux, dernier mouvement, prochaine réunion, couleur)
    ("Fed", "États-Unis", "3,75 – 4,00 %", 3.875, "Fed funds · fourchette cible", "Hausse de +25 pb le 16/09/26 (vote 12-0)", "Prochaine : 27-28 oct.", "#6366F1"),
    ("BCE", "Zone euro", "2,50 %", 2.50, "Taux de la facilité de dépôt", "Hausse de +25 pb le 10/09/26 · refi 2,65 % · prêt marginal 2,90 %", "Prochaine : 29 oct.", "#22D3EE"),
    ("BoJ", "Japon", "1,25 %", 1.25, "Taux au jour le jour", "Hausse de +25 pb le 18/09/26 (7-2) · plus haut depuis 1995", "Prochaine : 29-30 oct.", "#FB7185"),
    ("BoE", "Royaume-Uni", "3,75 %", 3.75, "Bank Rate", "Statu quo le 17/09/26 (6-3, trois voix pour +25 pb)", "Prochaine : 5 nov.", "#34D399"),
]


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
    page = """<style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700&family=JetBrains+Mono:wght@500;700&display=swap');
body{margin:0;font-family:Inter,sans-serif}#w{display:flex;gap:10px;overflow-x:auto;padding:4px 2px 8px}
.m{flex:1 0 150px;padding:11px 14px;border-radius:14px;color:#E8ECF5;background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,255,255,.1)}
.m.open{border-color:rgba(52,211,153,.45);box-shadow:0 0 18px rgba(52,211,153,.12)}.m.lunch{border-color:rgba(251,191,36,.4)}
.h{display:flex;justify-content:space-between;align-items:baseline}.h b{font-size:.85rem}.h i{font-style:normal;font-size:.62rem;letter-spacing:1px;color:#6B7389}
.t{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.3rem;margin:4px 0}
.s{font-size:.68rem;color:#8B93A7;display:flex;align-items:center;gap:6px}.s u{width:7px;height:7px;border-radius:50%;background:#4B5367;flex:none}
.open .s{color:#6EE7B7}.open u{background:#34D399;box-shadow:0 0 8px #34D399}.lunch .s{color:#FBBF24}.lunch u{background:#FBBF24}</style>
<div id="w"></div><script>const M=__CFG__,w=document.getElementById('w');
M.forEach((m,i)=>w.insertAdjacentHTML('beforeend','<div class="m" id="m'+i+'"><div class="h"><b>'+m.n+'</b><i>'+m.x+'</i></div><div class="t"></div><div class="s"><u></u><span></span></div></div>'));
const mn=s=>{const a=s.split(':');return +a[0]*60+ +a[1]},fm=x=>Math.floor(x/60)+'h'+String(x%60).padStart(2,'0');
function tick(){M.forEach((m,i)=>{const p=new Intl.DateTimeFormat('en-GB',{timeZone:m.tz,weekday:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).formatToParts(new Date());
const g=t=>p.find(x=>x.type===t).value,H=+g('hour')%24,cur=H*60+ +g('minute'),wd=g('weekday'),wk=wd!=='Sat'&&wd!=='Sun';
let st='closed',tx=wk?'Fermé':'Week-end';
if(wk){const ss=m.s.map(a=>[mn(a[0]),mn(a[1])]);for(let k=0;k<ss.length;k++){if(cur>=ss[k][0]&&cur<ss[k][1]){st='open';tx='Ouvert · ferme dans '+fm(ss[k][1]-cur);break}
if(cur<ss[k][0]){st=k>0?'lunch':'closed';tx=(k>0?'Pause':'Fermé')+' · ouvre dans '+fm(ss[k][0]-cur);break}}}
const e=document.getElementById('m'+i);e.className='m '+st;e.querySelector('.t').textContent=g('hour').replace('24','00')+':'+g('minute')+':'+g('second');e.querySelector('.s span').textContent=tx})}
tick();setInterval(tick,1000)</script>""".replace("__CFG__", json.dumps(cfg))
    try:
        st.iframe(page, height=108)  # Streamlit récent : components.html est déprécié
    except Exception:
        components.html(page, height=108)


# =====================================================================
#  VUE DÉTAILLÉE (clic sur une carte)
# =====================================================================
@st.cache_data(ttl=900, show_spinner=False)
def load_detail(ticker, period):
    df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=["Close"])


@st.dialog("Analyse détaillée", width="large")
def detail_dialog(name, ticker, cat):
    st.markdown(f'<div class="eyebrow">{cat} · {ticker}</div><h2 style="margin:2px 0 10px;font-weight:800">{html.escape(name)}</h2>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    per = c1.radio("Période", ["1M", "3M", "6M", "1A", "5A"], index=1, horizontal=True, label_visibility="collapsed")
    mode = c2.radio("Type", ["Ligne", "Chandeliers"], horizontal=True, label_visibility="collapsed")
    try:
        df = load_detail(ticker, {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1A": "1y", "5A": "5y"}[per])
        assert len(df) > 2
    except Exception:
        df = pd.DataFrame({"Close": load_all_data()[ticker].dropna()})
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
    for w_, c_ in ((20, "#FBBF24"), (50, "#A78BFA")):
        if len(cl) > w_ + 2:
            fig.add_trace(go.Scatter(x=df.index, y=cl.rolling(w_).mean(), name=f"MM{w_}", line=dict(color=c_, width=1.3, dash="dot")), row=1, col=1)
    if has_vol:
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color="rgba(129,140,248,.45)"), row=2, col=1)
    lo_y, hi_y = float(cl.min()), float(cl.max())
    fig.update_layout(height=440 if has_vol else 380, margin=dict(l=0, r=0, t=6, b=0), hovermode="x unified",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#CBD3E6"),
                      xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.07, x=0),
                      hoverlabel=dict(bgcolor="#11142A", bordercolor=col))
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
    '<div class="brand"><div class="brand-logo"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" '
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 17 9 11 13 15 21 7"/>'
    '<polyline points="15 7 21 7 21 13"/></svg></div><div><div class="brand-t">MACRO TERMINAL</div>'
    '<div class="brand-s">Global Markets</div></div></div>'
    f'<div class="live"><i></i>LIVE · {datetime.now(timezone.utc).strftime("%H:%M UTC")}</div>'
    '<div class="navlab">Navigation</div>', unsafe_allow_html=True)
_k = list(UNIVERSE.keys())
options = _k[:1] + ["🏦 Banques Centrales"] + _k[1:] + ["🕐 Calendrier des Marchés", "📰 Actualités Macro (FR)", "📚 Base de Connaissances"]
category = st.sidebar.radio("NAVIGATION", options, format_func=clean_label, label_visibility="collapsed")
st.sidebar.markdown('<div style="margin-top:30px;font-size:.7rem;color:#4B5367;line-height:1.5">Données : Yahoo Finance · cache 5 min<br>Informations à but pédagogique, pas un conseil en investissement.</div>',
                    unsafe_allow_html=True)

# =====================================================================
#  PAGE : DONNÉES DE MARCHÉ
# =====================================================================
market_strip()

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
                            f'<div class="mt">{html.escape(name)}<svg class="ex" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg></div>'
                            f'<div class="mrow"><span class="mv">{val_str}</span><span class="chip {cls}">{arrow} {pct:+.2f}%</span></div>'
                            f'<div class="sub">Tendance 30 j · <b class="{cls30}">{p30:+.1f}%</b></div>',
                            unsafe_allow_html=True)
                        show(mini_chart(series.tail(30), color), key=f"mini_{i}", static=True)
                        if st.button("Détails", key=f"btn_{i}"):
                            detail_dialog(name, ticker, clean_label(category))
                else:
                    st.warning(f"{name} : Données insuffisantes")
            else:
                st.warning(f"{name} : Hors ligne")

# =====================================================================
#  PAGE : ACTUALITÉS
# =====================================================================
elif category == "🏦 Banques Centrales":
    hero("Politique monétaire", "Banques Centrales", f"Taux directeurs · saisie manuelle au {CB_DATE}, à vérifier sur les sites officiels",
         '<span class="pill">Fed · BCE · BoJ · BoE</span>')
    for col, (n_, zone, rate, val, lab, move, nxt, c_) in zip(st.columns(4), CB):
        with col:
            st.markdown(kc(f"{n_} · {zone}", rate, f"<p><b>{lab}</b></p><p>{move}</p><span class='pill'>{nxt}</span>", c_), unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        sec("Niveau des taux directeurs", "En %, milieu de fourchette pour la Fed")
        fig = go.Figure(go.Bar(y=[x[0] for x in CB][::-1], x=[x[3] for x in CB][::-1], orientation="h", text=[x[2] for x in CB][::-1],
                               textposition="outside", cliponaxis=False, marker=dict(color=[x[7] for x in CB][::-1])))
        fig.update_layout(height=260, margin=dict(l=0, r=90, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(visible=False, range=[0, 5]), font=dict(family="Inter", color="#fff"))
        show(fig, key="cb_bar")
    with c2:
        sec("Écarts de taux", "En points de base (pb)")
        d_ = {x[0]: x[3] for x in CB}
        tl = [("Fed − BCE", d_["Fed"] - d_["BCE"]), ("Fed − BoJ", d_["Fed"] - d_["BoJ"]), ("BCE − BoJ", d_["BCE"] - d_["BoJ"]), ("BoE − BCE", d_["BoE"] - d_["BCE"])]
        st.markdown('<div class="sg" style="grid-template-columns:repeat(2,1fr)">' + "".join(
            f'<div class="sgt"><span>{a_}</span><b>{v * 100:+.0f} pb</b></div>' for a_, v in tl) + '</div>', unsafe_allow_html=True)
        st.caption("Un écart élevé alimente le carry trade (emprunt en yen ou en euro, placement en dollar).")
    sec("Prochaines échéances", "Dates prévues · à confirmer sur le calendrier officiel de chaque banque")
    st.markdown(table(["Date", "Banque", "Événement"], [
        ["27-28 oct.", "Fed", "Réunion du FOMC"], ["29 oct.", "BCE", "Décision de politique monétaire (14h15, heure de Paris)"],
        ["29-30 oct.", "BoJ", "Réunion de politique monétaire"], ["5 nov.", "BoE", "Décision du MPC + Monetary Policy Report"],
        ["17 déc.", "BCE · BoE", "Dernières décisions de l'année"]]), unsafe_allow_html=True)
    with st.expander("Contexte macro (automne 2026)", expanded=True):
        st.markdown("- **Choc énergétique** lié au conflit au Moyen-Orient : le pétrole a fortement monté et nourrit l'inflation partout.\n"
                    "- **Fed** : présidée par Kevin Warsh, elle est passée d'un débat « statu quo ou hausse » à une hausse en septembre.\n"
                    "- **BCE** : inflation attendue à 3,0 % en 2026, 2,5 % en 2027 et 2,1 % en 2028 selon ses projections de septembre.\n"
                    "- **BoJ** : poursuite de la normalisation, l'inflation devant dépasser 2 % au second semestre de l'exercice 2026.\n"
                    "- **BoE** : inflation à 3,1 % en août, trois membres du MPC voulaient déjà relever le taux.")
    with st.expander("Et la France ? Banque de France et taux"):
        st.markdown("- Les **taux directeurs en France sont ceux de la BCE** : la Banque de France fait partie de l'Eurosystème et son gouverneur siège au Conseil des gouverneurs.\n"
                    "- La Banque de France publie les **taux d'usure** (plafond légal des crédits) et son gouverneur donne un avis sur le **taux du Livret A**, fixé par l'État.\n"
                    "- Le coût de la dette française se lit dans le **taux de l'OAT 10 ans** et son écart avec le Bund allemand (voir le glossaire).")

elif category == "🕐 Calendrier des Marchés":
    now = datetime.now(PARIS)
    origin = datetime.combine(now.date(), datetime.min.time(), PARIS)
    now_h = (now - origin).total_seconds() / 3600
    hm = lambda h: f"{int(h) % 24:02d}:{int(round(h % 1 * 60)) % 60:02d}"
    toM = lambda t: int(t[:2]) * 60 + int(t[3:])
    reg = {"Asia": "#A78BFA", "Australia": "#A78BFA", "Europe": "#818CF8", "America": "#22D3EE"}

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
    fig.add_trace(go.Bar(y=["Crypto"], x=[24], base=[0], orientation="h", marker=dict(color="#FBBF24", opacity=.55), hovertemplate="<b>Crypto</b> · 24/7<extra></extra>", showlegend=False))
    fig.add_vline(x=now_h, line=dict(color=DN, width=2, dash="dot"), annotation_text="Maintenant", annotation_font_color=DN)
    fig.update_layout(height=430, barmode="overlay", margin=dict(l=0, r=10, t=24, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter", color="#CBD3E6"), xaxis=dict(range=[0, 24], tickvals=list(range(0, 25, 2)), ticktext=[f"{h:02d}h" for h in range(0, 25, 2)],
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

elif category == "📰 Actualités Macro (FR)":
    FEED = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
    AGGREGATOR = "https://www.tradingview.com/news/"
    TAGS = {
        "Banques centrales": ("#818CF8", 5, ["fed", "federal reserve", "ecb", "boj", "bank of japan", "bank of england", "powell", "warsh", "lagarde", "rate cut", "rate hike", "interest rate", "central bank", "fomc"]),
        "Inflation & Emploi": ("#FBBF24", 4, ["inflation", "cpi", "pce", "jobs", "payroll", "unemployment", "gdp", "recession", "layoffs", "consumer prices"]),
        "Géopolitique": ("#FB7185", 4, ["war", "sanction", "iran", "russia", "ukraine", "china", "israel", "tariff", "trade war", "middle east", "taiwan", "election", "trump", "ceasefire"]),
        "Énergie": ("#FB923C", 3, ["oil", "crude", "natural gas", "opec", "energy", "brent"]),
        "Europe & France": ("#60A5FA", 3, ["france", "french", "macron", "eurozone", "euro zone", "european", "europe", "germany", "paris", "cac"]),
        "Marchés": ("#22D3EE", 2, ["stocks", "s&p", "nasdaq", "dow", "yields", "treasury", "dollar", "bond", "bitcoin", "earnings", "wall street"]),
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

# =====================================================================
#  PAGE : BASE DE CONNAISSANCES
# =====================================================================
elif category == "📚 Base de Connaissances":
    hero("Repères institutionnels", "Base de Connaissances", "France, marchés, taux, économies, matières premières et glossaire de salle de marché",
         '<span class="pill">Ordres de grandeur 2025-2026</span>')
    st.markdown('<div class="sg">' + "".join(f'<div class="sgt"><span>{a_}</span><b>{b_}</b></div>' for a_, b_ in [
        ("PIB États-Unis", "≈ 28 000 Mds $"), ("PIB France", "≈ 3 100 Mds $"), ("Crypto-marché", "≈ 2 500 Mds $"),
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
        SECT = [("Luxe", ["LVMH", "Hermès", "Kering"], "#A78BFA"), ("Énergie", ["TotalEnergies", "Engie"], "#FB923C"),
                ("Santé", ["Sanofi", "EssilorLuxottica"], "#34D399"), ("Industrie & Défense", ["Airbus", "Safran", "Thales", "Schneider Electric", "Vinci"], "#22D3EE"),
                ("Finance", ["BNP Paribas", "AXA", "Société Générale", "Crédit Agricole"], "#818CF8"),
                ("Conso & Auto", ["L'Oréal", "Danone", "Pernod Ricard", "Stellantis", "Michelin"], "#FBBF24")]
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
        c1, c2, c3 = st.columns(3)
        for col, (big, title, names, clr) in zip((c1, c2, c3), [
            ("> 3 000 Mds $", "Le club des « Big 3 »", ["Apple", "Microsoft", "NVIDIA"], "#FACC15"),
            ("> 2 000 Mds $", "Le club des 2 000", ["Alphabet", "Amazon", "Saudi Aramco"], "#CBD5E1"),
            ("> 1 000 Mds $", "Le club des 1 000", ["Meta", "Berkshire Hathaway", "TSMC", "Eli Lilly", "Broadcom"], "#FB923C")]):
            with col:
                st.markdown(kc(title, big, chips(names), clr), unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="kc"><h4>Poids lourds européens</h4><p>Capitalisation approximative (Mds $).</p>', unsafe_allow_html=True)
            fig = go.Figure(go.Bar(y=["ASML", "LVMH", "Novo Nordisk"], x=[375, 400, 575], orientation="h", text=["~350-400", "~400", "~550-600"],
                                   textposition="inside", marker=dict(color=["#22D3EE", "#A78BFA", A1])))
            fig.update_layout(height=190, margin=dict(l=0, r=10, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(visible=False), yaxis=dict(color="#CBD3E6"), font=dict(family="Inter", color="#fff"))
            show(fig, key="eu_caps")
            st.markdown("<p>Autres noms : </p>" + chips(["SAP", "Hermès", "TotalEnergies", "Sanofi", "Schneider Electric", "L'Oréal", "Airbus"]) + '</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc"><h4>Total crypto-marché</h4><div class="big" style="--c:#FBBF24">~2 500 Mds $</div>', unsafe_allow_html=True)
            show(gauge(52.5, "Dominance du Bitcoin (≈ 50-55 %)", color="#F59E0B"), key="btc_dom")
            st.markdown('</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(kc("Top 5 du S&P 500", "", ranks([("<b>Microsoft</b>", "Tech · Cloud · IA"), ("<b>Apple</b>", "Hardware · Services"),
                         ("<b>NVIDIA</b>", "Semi-conducteurs · IA"), ("<b>Amazon</b>", "E-commerce · Cloud"), ("<b>Alphabet</b>", "Publicité · Recherche")])), unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc"><h4>Concentration</h4>', unsafe_allow_html=True)
            show(gauge(25, "Poids cumulé du Top 5", color=A1), key="sp_conc")
            st.markdown('</div>', unsafe_allow_html=True)

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
            fig = go.Figure(go.Bar(y=ce, x=ve, orientation="h", text=[f"~{v:,}".replace(",", " ") for v in ve], textposition="outside", cliponaxis=False,
                                   marker=dict(color=["#60A5FA" if c == "France" else A1 for c in ce])))
            fig.update_layout(height=400, margin=dict(l=0, r=70, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(visible=False), yaxis=dict(autorange="reversed", color="#CBD3E6"), font=dict(family="Inter", color="#fff"))
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
                st.markdown(ranks(top) + f'<p style="color:#8B93A7;font-size:.85rem;margin-top:8px">{note_}</p>', unsafe_allow_html=True)

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
              ("PMI", "Indice des directeurs d'achat : au-dessus de 50, l'activité progresse.")]
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
