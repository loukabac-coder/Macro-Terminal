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

st.set_page_config(page_title="PRO Macro Terminal", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
#  BACKEND : UNIVERSE ÉLARGI (BIAIS FRANÇAIS)
# =====================================================================
UNIVERSE = {
    "🏛️️ Taux & Banques Centrales": {
        "US 10Y Treasury": "^TNX",
        "US 2Y Treasury": "^IRX",
        "Eurozone 10Y (IGOV)": "IGOV",
        "OAT 10Y (France)": "^FR10Y=X",
        "Japon 10Y (JGBL.L)": "JGBL.L",
        "Gilt 10Y (UK)": "^GB10Y=X"
    },
    "🌍 Indices": {
        "CAC 40 (France)": "^FCHI",
        "S&P 500 (US)": "^GSPC",
        "Nasdaq 100 (Tech)": "^NDX",
        "Euro Stoxx 50": "^STOXX50E",
        "DAX 40 (Allemagne)": "^GDAXI",
        "SMI (Suisse)": "^SSMI",
        "FTSE 100 (UK)": "^FTSE",
        "Nikkei 225 (Japon)": "^N225",
        "Hang Seng (Hong Kong)": "^HSI",
        "Nifty 50 (Inde)": "^NSEI",
        "MSCI World (URTH)": "URTH"
    },
    "🇫🇷 Fleurons Français": {
        "LVMH (Luxe)": "MC.PA",
        "L'Oréal (Cosmétique)": "OR.PA",
        "Hermès (Luxe)": "RMS.PA",
        "TotalEnergies (Énergie)": "TTE.PA",
        "Sanofi (Santé)": "SAN.PA",
        "Schneider Elec. (Industrie)": "SU.PA",
        "Airbus (Aérospatial)": "AIR.PA",
        "BNP Paribas (Banque)": "BNP.PA",
        "AXA (Assurance)": "CS.PA",
        "EssilorLuxottica": "EL.PA"
    },
    "💱 Devises (Forex)": {
        "DXY (Dollar Index)": "DX-Y.NYB",
        "EUR/USD (Fiber)": "EURUSD=X",
        "GBP/USD (Cable)": "GBPUSD=X",
        "USD/JPY (Ninja)": "USDJPY=X",
        "USD/CHF (Refuge)": "USDCHF=X",
        "AUD/USD (Aussie)": "AUDUSD=X",
        "USD/CNY (Yuan Onshore)": "USDCNY=X",
        "EUR/GBP": "EURGBP=X",
        "EUR/JPY": "EURJPY=X"
    },
    "🛢️ Matières Premières": {
        "Brent Crude (Europe)": "BZ=F",
        "WTI Crude (US)": "CL=F",
        "Or (Valeur Refuge)": "GC=F",
        "Argent (Silver)": "SI=F",
        "Cuivre (Dr. Copper)": "HG=F",
        "Gaz Naturel (US)": "NG=F",
        "Uranium (Proxy URA)": "URA",
        "Blé (Wheat)": "ZW=F",
        "Cacao (Cocoa)": "CC=F"
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
        "ASML (Semi-conducteurs)": "ASML.AS"
    },
    "🪙 Crypto-Actifs": {
        "Bitcoin (BTC)": "BTC-USD",
        "Ethereum (ETH)": "ETH-USD",
        "Solana (SOL)": "SOL-USD",
        "Binance Coin (BNB)": "BNB-USD",
        "Ripple (XRP)": "XRP-USD",
        "Cardano (ADA)": "ADA-USD"
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

/* Central Banks Panel */
.cb-panel {display:flex; gap:15px; margin-bottom:25px; flex-wrap:wrap;}
.cb-card {flex:1; min-width:180px; background:linear-gradient(150deg,rgba(255,255,255,.07),rgba(255,255,255,.015)); border:1px solid var(--bd); border-radius:18px; padding:16px; text-align:center; box-shadow:0 10px 30px rgba(0,0,0,.35);}
.cb-name {color:var(--mut); font-size:0.8rem; font-weight:600; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;}
.cb-rate {color:var(--a2); font-size:1.8rem; font-weight:700; font-family:'JetBrains Mono',monospace; margin-bottom:4px;}
.cb-desc {color:#6B7389; font-size:0.75rem;}

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

/* Top 5 compact & traduit */
.hl{display:block;position:relative;overflow:hidden;text-decoration:none!important;padding:24px 26px;border-radius:20px;min-height:276px;background:linear-gradient(150deg,rgba(255,255,255,.08),rgba(255,255,255,.015));border:1px solid var(--bd);box-shadow:0 12px 34px rgba(0,0,0,.4);transition:.3s}
.hl::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--c),transparent)}
.hl:hover{transform:translateY(-3px);border-color:var(--c);box-shadow:0 0 30px -6px var(--c)}
.hl-t{color:#fff;font-weight:800;font-size:1.2rem;line-height:1.3;margin:6px 0 6px}
.hl-s{color:var(--a2);font-size:0.95rem;line-height:1.4;margin-bottom:12px;font-style:italic;}
.sl{display:flex;gap:14px;align-items:center;text-decoration:none!important;padding:12px 16px;border-radius:14px;margin-bottom:10px;min-height:75px;background:rgba(255,255,255,.04);border:1px solid var(--bd);border-left:3px solid var(--c);transition:.25s}
.sl:hover{background:rgba(255,255,255,.08);transform:translateX(4px)}
.sl .rank{font-size:1.1rem}
.sl-t{color:#F1F5F9;font-weight:600;font-size:0.95rem;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.sl-fr{color:var(--mut);font-size:0.85rem;margin-top:2px;font-style:italic;}
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
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- Icônes SVG (style Lucide) pour la navigation, dans l'ordre des options ---
ICONS = [
    '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    '<circle cx="12" cy="12" r="10"/><path d="M12 2v20"/><path d="M2 12h20"/>',
    '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
    '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
    '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
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
options = list(UNIVERSE.keys()) + ["🕐 Calendrier des Marchés", "📰 Actualités Macro (FR)", "📚 Base de Connaissances"]
category = st.sidebar.radio("NAVIGATION", options, format_func=clean_label, label_visibility="collapsed")
st.sidebar.markdown('<div style="margin-top:30px;font-size:.7rem;color:#4B5367;line-height:1.5">Données : Yahoo Finance · cache 5 min<br>Informations à but pédagogique.</div>',
                    unsafe_allow_html=True)

# =====================================================================
#  PAGE : DONNÉES DE MARCHÉ
# =====================================================================
market_strip()

if category in UNIVERSE:
    
    # --- PANNEAU DES BANQUES CENTRALES ---
    if category == "🏛️ Taux & Banques Centrales":
        st.markdown("""
        <div class="cb-panel">
            <div class="cb-card"><div class="cb-name">FED (États-Unis)</div><div class="cb-rate">4.75% - 5.00%</div><div class="cb-desc">Fed Funds Rate</div></div>
            <div class="cb-card"><div class="cb-name">BCE (Zone Euro)</div><div class="cb-rate">3.50%</div><div class="cb-desc">Taux de dépôt</div></div>
            <div class="cb-card"><div class="cb-name">BoE (Royaume-Uni)</div><div class="cb-rate">5.00%</div><div class="cb-desc">Bank Rate</div></div>
            <div class="cb-card"><div class="cb-name">BoJ (Japon)</div><div class="cb-rate">0.25%</div><div class="cb-desc">Policy Rate</div></div>
        </div>
        """, unsafe_allow_html=True)

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
#  PAGE : CALENDRIER DES MARCHÉS
# =====================================================================
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

# =====================================================================
#  PAGE : ACTUALITÉS (TRADUCTION RAPIDE DU TOP 5)
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
        for e in feed.entries[:30]:
            ts = time.mktime(e.published_parsed) if getattr(e, "published_parsed", None) else 0
            out.append({"title": e.title, "link": e.link, "ts": ts,
                        "summary": re.sub(r"<[^>]+>", "", getattr(e, "summary", ""))})
        return out

    def tr(text):
        try:
            return GoogleTranslator(source='auto', target='fr').translate(text)
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
        with st.spinner("Chargement rapide des actualités..."):
            news = []
            for n in fetch_news():
                n = dict(n)
                n["score"], n["tag"] = score(n)
                news.append(n)
            
            # On trie et on prend le Top 5 le plus pertinent
            top5 = sorted(news, key=lambda n: (n["score"], n["ts"]), reverse=True)[:5]
            top_links = {n["link"] for n in top5}
            flux = sorted([n for n in news if n["link"] not in top_links], key=lambda n: n["ts"], reverse=True)[:15]
            
            # On traduit UNIQUEMENT le Top 5 pour éviter que l'API ne plante et que le site rame
            for n in top5:
                n["fr"] = tr(n["title"])
                n["fr_sum"] = tr(n["summary"][:300].rsplit(" ", 1)[0])

        if not news:
            st.warning("Aucune actualité trouvée.")
        else:
            # ---------- SECTION A ----------
            sec("Le Résumé de la Semaine", "Top 5 · classé par impact macro & géopolitique estimé (banques centrales, inflation, conflits, énergie)")

            def slim(n, rank):
                c = TAGS[n["tag"]][0]
                return (f'<a class="sl" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank"><span class="rank">{rank}</span>'
                        f'<div><div class="sl-t">{html.escape(n["title"])}</div><div class="sl-fr">🇫🇷 {html.escape(n["fr"])}</div><div class="sl-m"><span class="tag">{n["tag"]}</span>'
                        f'<span>{fmt(n["ts"])}</span></div></div></a>')

            h = top5[0]
            hc = TAGS[h["tag"]][0]
            dots = min(5, 1 + h["score"] // 3)
            L, R = st.columns([3, 2])
            with L:
                st.markdown(
                    f'<a class="hl" style="--c:{hc}" href="{html.escape(h["link"])}" target="_blank">'
                    f'<div class="nc-top" style="margin:0"><span class="rank">01</span><span class="tag">{h["tag"]}</span></div>'
                    f'<div class="hl-t">{html.escape(h["title"])}</div><div class="hl-s">🇫🇷 {html.escape(h["fr"])}</div>'
                    f'<div class="nc-m"><span>{fmt(h["ts"])}</span><span>·</span><span>Impact <span class="dots" style="--c:{hc}">{"●" * dots}{"○" * (5 - dots)}</span></span>'
                    f'<span>·</span><span>Lire l\'article ↗</span></div></a>', unsafe_allow_html=True)
            with R:
                st.markdown("".join(slim(n, j) for j, n in enumerate(top5[1:], 2)), unsafe_allow_html=True)

            # ---------- SECTION B ----------
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            sec("Le Flux du Jour", "Dernières publications (Titres originaux pour la rapidité)",
                f'<a class="btn" href="{AGGREGATOR}" target="_blank">Toutes les infos en temps réel '
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg></a>')
            
            opts = ["Tous"] + list(TAGS)
            sel = (st.pills("Filtre", opts, default="Tous", label_visibility="collapsed") if hasattr(st, "pills")
                   else st.radio("Filtre", opts, horizontal=True, label_visibility="collapsed"))
            rows_html = ""
            for n in flux:
                if sel not in (None, "Tous") and n["tag"] != sel:
                    continue
                c = TAGS[n["tag"]][0]
                rows_html += (f'<a class="fx" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank">'
                              f'<span class="fx-t">{fmt(n["ts"])}</span><span class="tag" style="--c:{c}">{n["tag"]}</span>'
                              f'<span class="fx-x">{html.escape(n["title"])}</span><span class="fx-a">↗</span></a>')
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

    t1, t2, t3, t4, t5, t6, t7 = st.tabs(["Banques Centrales", "Capitalisations", "S&P 500", "Économies", "Matières premières", "Blocs & Alliances", "Fleurons Étrangers"])

    # ---- Banques Centrales ----
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="kc"><h4>Réserve Fédérale (FED)</h4><p>Banque centrale des États-Unis.</p>' + ranks([
                ("<b>Double mandat</b>", "Plein emploi & Stabilité des prix (~2%)"),
                ("<b>Indicateurs surveillés</b>", "NFP (Emploi), PCE (Inflation)"),
                ("<b>Impact Taux</b>", "Hausse = DXY monte, Tech baisse")]) + '</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc"><h4>Banque Centrale Européenne (BCE)</h4><p>Banque centrale de la zone euro.</p>' + ranks([
                ("<b>Mandat unique</b>", "Stabilité des prix uniquement"),
                ("<b>Indicateurs surveillés</b>", "HICP, PMI manufacturiers"),
                ("<b>Dynamique</b>", "Souvent en décalage avec la FED")]) + '</div>', unsafe_allow_html=True)

    # ---- Capitalisations ----
    with t2:
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
    with t3:
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
    with t4:
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
    with t5:
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
    with t6:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="kc" style="--c:#818CF8"><h4>G7</h4><div class="big">7 + UE</div>' + chips(["États-Unis", "Japon", "Allemagne", "Royaume-Uni", "France", "Italie", "Canada"]).replace('class="co tip" data-tip="', 'class="co" data-x="') + '<p style="margin-top:10px">Union européenne invitée aux sommets.</p></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc" style="--c:#FB7185"><h4>BRICS+</h4><div class="big">Bloc élargi</div>' + "".join(f'<span class="co">{x}</span>' for x in ["Brésil", "Russie", "Inde", "Chine", "Afrique du Sud"]) + '<p style="margin-top:10px">Rejoints récemment par l\'Iran, l\'Égypte, l\'Éthiopie et les Émirats arabes unis.</p></div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="kc" style="--c:#FB923C"><h4>OPEP+</h4><div class="big">Cartel pétrolier</div><p>Mené par l\'<b>Arabie Saoudite</b>, allié à la <b>Russie</b> pour contrôler l\'offre mondiale de brut.</p></div>', unsafe_allow_html=True)

    # ---- Leaders étrangers ----
    with t7:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="kc"><h4>Inde · Nifty 50</h4>' + ranks([
                ("<b>Reliance Industries</b>", "Conglomérat · M. Ambani"), ("<b>TCS</b>", "Services IT"), ("<b>HDFC Bank</b>", "Banque")]) + '</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="kc"><h4>Europe · Stoxx 600</h4>' + ranks([
                ("<b>Novo Nordisk</b>", "Santé · diabète"), ("<b>LVMH</b>", "Luxe"), ("<b>ASML</b>", "Semi-conducteurs · EUV")]) + '</div>', unsafe_allow_html=True)
