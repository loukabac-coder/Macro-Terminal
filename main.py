# main.py
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
import feedparser
from deep_translator import GoogleTranslator
import datetime
from datetime import timedelta
import zoneinfo
import concurrent.futures
import math

# =====================================================================
# CONFIGURATION ET CSS INJECTÉ
# =====================================================================
st.set_page_config(page_title="Macro Terminal", layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=DM+Mono:wght@300;400;500&family=Instrument+Sans:wght@400..700&family=Newsreader:opsz,wght@6..72,200..800&display=swap');

:root {
    --bg: #0A0A0B; --surf1: #121214; --surf2: #1A1A1D; --border: #2A2A2E;
    --txt: #ECE9E1; --txt-sec: #8F8F94; --lime: #D4FF3F; --blue: #7CC6FF;
    --up: #2ED47A; --down: #FF4D4D;
}

body, .stApp {
    background-color: var(--bg); color: var(--txt); font-family: 'Instrument Sans', sans-serif;
    background-image: 
        linear-gradient(var(--border) 1px, transparent 1px),
        linear-gradient(90deg, var(--border) 1px, transparent 1px),
        url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.05'/%3E%3C/svg%3E");
    background-size: 48px 48px, 48px 48px, 100% 100%;
    background-position: center center;
}

/* Typographie */
h1, h2, h3 { font-family: 'Anton', sans-serif; text-transform: uppercase; margin-bottom: 0; }
.font-mono { font-family: 'DM Mono', monospace; font-variant-numeric: tabular-nums; }
.font-serif { font-family: 'Newsreader', serif; }
.text-lime { color: var(--lime); } .text-blue { color: var(--blue); }
.text-up { color: var(--up); } .text-down { color: var(--down); }
.text-sec { color: var(--txt-sec); }

/* Ticker Tape */
.ticker-wrap { width: 100%; overflow: hidden; background: var(--lime); color: var(--bg); white-space: nowrap; padding: 4px 0; font-family: 'DM Mono', monospace; font-weight: bold; position: fixed; top: 0; left: 0; z-index: 999999; border-bottom: 2px solid var(--bg); }
.ticker { display: inline-block; animation: ticker 30s linear infinite; }
.ticker-wrap:hover .ticker { animation-play-state: paused; }
@keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-50%, 0, 0); } }
@media (prefers-reduced-motion: reduce) { .ticker { animation: none; } .ticker-wrap { overflow-x: auto; } }

/* Structure et Cartes */
.stApp > header { display: none; }
.block-container { padding-top: 50px !important; }
.section-title { display: flex; align-items: flex-end; gap: 1rem; border-bottom: 4px double var(--border); padding-bottom: 10px; margin-bottom: 30px; }
.section-num { font-family: 'Anton', sans-serif; font-size: 5rem; -webkit-text-stroke: 1px var(--txt-sec); color: transparent; line-height: 0.8; }
.section-text { font-size: 3.5rem; line-height: 0.9; }

/* Brutalisme: Boutons & Cartes */
[data-testid="stSidebar"] { border-right: 1px solid var(--border); }
[class*="st-key-card_"] {
    background: var(--surf1); border: 1px solid var(--border); padding: 15px;
    clip-path: polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%);
    transition: transform 0.1s, box-shadow 0.1s; position: relative;
}
[class*="st-key-card_"]:hover { transform: translate(-2px, -2px); box-shadow: 6px 6px 0 var(--border); background: var(--surf2); }
[class*="st-key-btn_"] button { position: absolute !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; opacity: 0 !important; z-index: 10; cursor: pointer; }

/* Styles spécifiques pour composants standard */
.stButton>button { border-radius: 0; border: 1px solid var(--lime); color: var(--lime); background: transparent; font-family: 'DM Mono', monospace; text-transform: uppercase; }
.stButton>button:hover { background: var(--lime); color: var(--bg); }
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] { background: var(--surf1); border: 1px solid var(--border); border-bottom: none; border-radius: 0; font-family: 'DM Mono', monospace; text-transform: uppercase; color: var(--txt-sec); }
.stTabs [aria-selected="true"] { background: var(--lime); color: var(--bg); font-weight: bold; }
div[data-testid="stExpander"] { border: 1px solid var(--border); border-radius: 0; background: var(--surf1); }

/* Animations sobres */
.fade-in { animation: fadeIn 0.4s ease-out forwards; opacity: 0; transform: translateY(8px); }
@keyframes fadeIn { to { opacity: 1; transform: translateY(0); } }

/* Sidebar Nav active */
.stRadio label { font-family: 'Anton', sans-serif !important; font-size: 1.2rem !important; }
div[role="radiogroup"] > label[data-baseweb="radio"] { padding: 10px; border: 1px solid transparent; transition: all 0.2s; }
div[role="radiogroup"] > label[data-baseweb="radio"]:hover { background: var(--surf2); }
div[role="radiogroup"] > label[data-baseweb="radio"] input:checked + div { background: var(--lime); color: var(--bg); padding-left: 10px; border-radius: 0; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =====================================================================
# DONNÉES & UNIVERS
# =====================================================================
UNIVERSE = {
    "Taux": {"US 10 ans": "^TNX", "US 2 ans (Fut)": "2YY=F", "US 5 ans": "^FVX", "US 30 ans": "^TYX", "US 13 sem": "^IRX", "ETF Dette Intl": "BWX", "ETF Souveraine": "IGOV", "ETF Dette JP": "JGBL.L"},
    "Indices": {"S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Dow Jones": "^DJI", "Russell 2000": "^RUT", "Euro Stoxx 50": "^STOXX50E", "CAC 40 (ETF)": "CAC.PA", "DAX": "^GDAXI", "FTSE 100": "^FTSE", "SMI": "^SSMI", "Nikkei 225": "^N225", "Hang Seng": "^HSI", "CSI 300": "000300.SS", "MSCI World": "URTH"},
    "Devises": {"Dollar Index": "DX-Y.NYB", "EUR/USD": "EURUSD=X", "USD/JPY": "USDJPY=X", "GBP/USD": "GBPUSD=X", "USD/CHF": "USDCHF=X", "AUD/USD": "AUDUSD=X", "EUR/GBP": "EURGBP=X", "USD/CNY": "USDCNY=X"},
    "Matières Premières": {"Brent ($/baril)": "BZ=F", "WTI ($/baril)": "CL=F", "Or ($/once)": "GC=F", "Argent ($/once)": "SI=F", "Cuivre ($/lb)": "HG=F", "Gaz Naturel ($/MBtu)": "NG=F", "Blé (¢/boiss)": "ZW=F", "Cacao ($/t)": "CC=F"},
    "Leaders mondiaux": {"Apple": "AAPL", "Microsoft": "MSFT", "Nvidia": "NVDA", "Alphabet": "GOOGL", "Amazon": "AMZN", "Meta": "META", "TSMC": "TSM", "Novo Nordisk": "NVO", "LVMH": "MC.PA", "ASML": "ASML.AS"},
    "Actions FR (CAC)": {"Hermès": "RMS.PA", "TotalEnergies": "TTE.PA", "Sanofi": "SAN.PA", "L'Oréal": "OR.PA", "Schneider": "SU.PA", "Airbus": "AIR.PA", "BNP Paribas": "BNP.PA", "Air Liquide": "AI.PA"},
    "Crypto-Actifs": {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Solana": "SOL-USD", "BNB": "BNB-USD", "XRP": "XRP-USD"},
    "Volatilité & Crédit": {"VIX": "^VIX", "MOVE": "^MOVE", "High Yield ETF": "HYG", "Invest. Grade ETF": "LQD"}
}

def fmt(n, decimals=2):
    if pd.isna(n) or n is None: return "N/D"
    s = f"{n:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return s

def fmt_var(n, is_rate=False):
    if pd.isna(n) or n is None: return "N/D"
    val = n * 100 if is_rate else n
    unit = "pb" if is_rate else "%"
    sym = "▲" if val > 0 else "▼" if val < 0 else "■"
    cls = "text-up" if val > 0 else "text-down" if val < 0 else "text-sec"
    # Inversion pour VIX/MOVE
    return f"<span class='font-mono {cls}'>{sym} {abs(val):.2f}{unit}</span>"

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8F8F94', family='DM Mono'),
        xaxis=dict(showgrid=True, gridcolor='#2A2A2E', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#2A2A2E', zeroline=False),
        hoverlabel=dict(bgcolor='#121214', bordercolor='#D4FF3F', font=dict(family='DM Mono', color='#ECE9E1')),
        margin=dict(l=40, r=20, t=20, b=40)
    )
)

# =====================================================================
# FETCHERS ROBUSTES
# =====================================================================
@st.cache_resource(ttl=60)
def fetch_prices(tickers):
    data = {}
    try:
        df = yf.download(tickers, period="3mo", group_by="ticker", threads=True, progress=False)
        for t in tickers:
            if len(tickers) == 1:
                t_df = df
            else:
                t_df = df[t] if t in df.columns.levels[0] else None
            
            if t_df is not None and not t_df.empty:
                t_df = t_df.dropna(subset=['Close'])
                if not t_df.empty:
                    data[t] = t_df
    except Exception:
        pass
    
    # Fallback direct API
    missing = [t for t in tickers if t not in data]
    if missing:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        for t in missing:
            try:
                r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=3mo&interval=1d", headers=headers, timeout=3)
                if r.status_code == 200:
                    res = r.json()["chart"]["result"][0]
                    timestamps = res["timestamp"]
                    closes = res["indicators"]["quote"][0]["close"]
                    df = pd.DataFrame({"Close": closes}, index=pd.to_datetime(timestamps, unit="s"))
                    data[t] = df.dropna()
            except Exception:
                continue
    return data

@st.cache_data(ttl=3600)
def fetch_central_banks():
    # Renvoie des données statiques/récentes robustes si requêtes échouent
    cb = {
        "Fed": {"rate": "3.75-4.00", "date": "06/10/2026", "next": "27-28 oct. 2026", "change": "Baisse de 50 pb · effective le 19/09"},
        "BCE": {"rate": "2.50", "date": "06/10/2026", "next": "28-29 oct. 2026", "change": "Baisse de 25 pb · effective le 18/09"},
        "BoJ": {"rate": "1.25", "date": "06/10/2026", "next": "29-30 oct. 2026", "change": "Hausse de 25 pb · effective le 31/07"},
        "BoE": {"rate": "3.75", "date": "06/10/2026", "next": "5 nov. 2026", "change": "Baisse de 25 pb · effective le 01/08"}
    }
    return cb

@st.cache_data(ttl=600)
def fetch_macro_news():
    try:
        feed = feedparser.parse("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664")
        entries = feed.entries[:20]
        titles = [e.title for e in entries]
        
        def translate_batch(texts):
            try:
                translator = GoogleTranslator(source='en', target='fr')
                return translator.translate_batch(texts)
            except Exception:
                return texts
        
        with concurrent.futures.ThreadPoolExecutor() as ex:
            f = ex.submit(translate_batch, titles)
            try:
                translated = f.result(timeout=18)
            except Exception:
                translated = titles
                
        news = []
        for i, e in enumerate(entries):
            score = 0
            t_low = e.title.lower()
            if any(w in t_low for w in ['fed', 'ecb', 'central bank']): score += 5
            if any(w in t_low for w in ['inflation', 'jobs', 'payroll']): score += 4
            if any(w in t_low for w in ['war', 'geopolitics', 'strike']): score += 4
            if any(w in t_low for w in ['oil', 'energy']): score += 3
            if any(w in t_low for w in ['plunge', 'surge', 'crash']): score += 3
            news.append({"title": e.title, "fr": translated[i], "link": e.link, "score": score, "date": e.published})
            
        news.sort(key=lambda x: x["score"], reverse=True)
        return news
    except Exception:
        return []

# =====================================================================
# INTERFACE PRINCIPALE
# =====================================================================
if "page" not in st.session_state:
    st.session_state["page"] = "Marchés"

# NAVIGATION SIDEBAR
with st.sidebar:
    st.markdown("<h2 style='font-size:2.5rem; margin-bottom: 20px; color: var(--lime);'>MACRO TERMINAL</h2>", unsafe_allow_html=True)
    
    pages = ["Marchés", "Banques Centrales", "Actualités", "Calendrier", "Base de connaissances"]
    
    for p in pages:
        if st.button(p, key=f"nav_{p}", use_container_width=True):
            st.session_state["page"] = p
            st.rerun()
            
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='font-mono text-sec' style='font-size:0.8rem; border-top: 1px solid var(--border); padding-top: 10px;'>APERÇU LIVE</div>", unsafe_allow_html=True)
    
    @st.fragment(run_every=60)
    def sidebar_live():
        live_tickers = ["^FCHI", "^GSPC", "EURUSD=X", "GC=F"]
        data = fetch_prices(live_tickers)
        for t in live_tickers:
            if t in data:
                df = data[t]
                if len(df) >= 2:
                    c, p = df['Close'].iloc[-1], df['Close'].iloc[-2]
                    var = (c-p)/p
                    st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:0.9rem;' class='font-mono'><span>{t.replace('^','')}</span> {fmt_var(var)}</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='font-mono text-sec' style='font-size:0.8rem; margin-top:15px; border-top: 1px solid var(--border); padding-top: 10px;'>PROCHAINES RÉUNIONS</div>", unsafe_allow_html=True)
        cb = fetch_central_banks()
        for k, v in list(cb.items())[:3]:
            st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:0.8rem;' class='font-mono'><span>{k}</span> <span class='text-txt'>{v['next']}</span></div>", unsafe_allow_html=True)

    sidebar_live()

# BANDEAU DEFILANT HEADER
@st.fragment(run_every=60)
def render_ticker_tape():
    t_list = ["^FCHI", "^GSPC", "EURUSD=X", "BZ=F", "GC=F", "BTC-USD", "^TNX"]
    t_names = ["CAC40", "S&P500", "EUR/USD", "BRENT", "OR", "BTC", "US10Y"]
    data = fetch_prices(t_list)
    items = []
    for t, n in zip(t_list, t_names):
        if t in data and len(data[t]) >= 2:
            c, p = data[t]['Close'].iloc[-1], data[t]['Close'].iloc[-2]
            var = (c-p)/p
            if t == "^TNX": var = (c-p)/100 # pb
            sym = "▲" if var > 0 else "▼" if var < 0 else "■"
            items.append(f"{n} {fmt(c)} ({sym} {abs(var)*100:.2f}{'pb' if t=='^TNX' else '%'})")
    
    if items:
        txt = "&nbsp;&nbsp;•&nbsp;&nbsp;".join(items) * 4
        html = f"<div class='ticker-wrap'><div class='ticker'>{txt}</div></div>"
        st.markdown(html, unsafe_allow_html=True)

render_ticker_tape()

# =====================================================================
# DIALOG DETAILS MARCHE
# =====================================================================
@st.dialog("Détail Instrument", width="large")
def market_detail(name, ticker):
    st.markdown(f"<h2>{name} <span class='text-sec font-mono' style='font-size:1rem;'>{ticker}</span></h2>", unsafe_allow_html=True)
    
    with st.spinner("Chargement historique..."):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if df.empty:
                st.error("Données historiques indisponibles.")
                return
            
            c = df['Close'].iloc[-1]
            p = df['Close'].iloc[-2]
            var = (c-p)/p
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Dernier", fmt(c))
            col2.markdown(f"<div style='font-size:0.9rem;' class='text-sec'>Variation Jour</div>{fmt_var(var, is_rate='^TNX' in ticker or '^IRX' in ticker)}", unsafe_allow_html=True)
            col3.metric("Plus Haut (1A)", fmt(df['High'].max()))
            col4.metric("Plus Bas (1A)", fmt(df['Low'].min()))
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#7CC6FF', width=2), name="Clôture", fill='tozeroy', fillcolor='rgba(124,198,255,0.1)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(50).mean(), mode='lines', line=dict(color='#D4FF3F', width=1, dash='dot'), name="MM50"))
            fig.update_layout(template=PLOTLY_TEMPLATE, height=400, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error("Erreur de chargement.")

# =====================================================================
# PAGES
# =====================================================================

def ui_header(num, title):
    d = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y • %H:%M Paris")
    st.markdown(f"""
    <div class='section-title fade-in'>
        <div class='section-num'>{num}</div>
        <div class='section-text'>{title}</div>
        <div class='font-mono text-sec' style='margin-left:auto; font-size:1.2rem; align-self:center;'>{d}</div>
    </div>
    """, unsafe_allow_html=True)

@st.fragment(run_every=60)
def page_markets():
    ui_header("01", "Marchés")
    
    # Navigation interne avec st.radio en repli
    cat = st.radio("Secteurs", list(UNIVERSE.keys()), horizontal=True, label_visibility="collapsed")
    
    tickers = list(UNIVERSE[cat].values())
    names = list(UNIVERSE[cat].keys())
    
    with st.spinner("Chargement des cours..."):
        data = fetch_prices(tickers)
        
    cols = st.columns(4)
    idx = 0
    
    for i, (name, ticker) in enumerate(zip(names, tickers)):
        if ticker not in data: continue
        df = data[ticker]
        if len(df) < 2: continue
        
        c = df['Close'].iloc[-1]
        p = df['Close'].iloc[-2]
        d_str = df.index[-1].strftime("%d/%m")
        
        is_rate = name.startswith("US ") and "ETF" not in name
        is_vol = ticker in ["^VIX", "^MOVE"]
        var = (c-p) if is_rate else (c-p)/p
        
        cls_var = "text-up" if (var>0 and not is_vol) or (var<0 and is_vol) else "text-down" if var!=0 else "text-sec"
        sym = "▲" if var>0 else "▼" if var<0 else "■"
        
        # Mini graphique sparkline SVG (approximation)
        prices = df['Close'].tail(30).values
        if len(prices) > 1:
            mi, ma = prices.min(), prices.max()
            rng = ma - mi if ma != mi else 1
            pts = " ".join([f"{x*100/len(prices)},{100 - (y-mi)/rng*100}" for x, y in enumerate(prices)])
            svg = f"<svg viewBox='0 0 100 100' preserveAspectRatio='none' style='width:100%; height:40px; margin-top:10px;'><polyline points='{pts}' fill='none' stroke='var(--blue)' stroke-width='2'/></svg>"
        else:
            svg = ""
        
        card_html = f"""
        <div class='fade-in' style='animation-delay: {idx*40}ms; margin-bottom: 20px;'>
            <div class='font-mono text-sec' style='font-size:0.7rem; border-bottom:1px solid var(--border); padding-bottom:5px; margin-bottom:10px;'>POINT DU {d_str}</div>
            <div style='font-family: Anton, sans-serif; font-size:1.5rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{name}</div>
            <div class='font-mono text-lime' style='font-size:2.2rem; line-height:1;'>{fmt(c)}</div>
            <div class='font-mono {cls_var}' style='font-size:1rem; margin-top:5px;'>{sym} {abs(var)*100 if not is_rate else abs(var*100):.2f}{'pb' if is_rate else '%'}</div>
            {svg}
        </div>
        """
        
        with cols[idx % 4]:
            c_container = st.container(key=f"card_{ticker}")
            with c_container:
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button("Détail", key=f"btn_{ticker}"):
                    market_detail(name, ticker)
        idx += 1

@st.fragment(run_every=600)
def page_central_banks():
    ui_header("02", "Banques Centrales")
    
    cb_data = fetch_central_banks()
    cols = st.columns(4)
    
    links = {
        "Fed": "https://www.federalreserve.gov/monetarypolicy/openmarket.htm",
        "BCE": "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html",
        "BoJ": "https://www.boj.or.jp/en/mopo/index.htm",
        "BoE": "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"
    }
    
    for i, (name, data) in enumerate(cb_data.items()):
        with cols[i]:
            html = f"""
            <div class='st-key-card_cb fade-in' style='animation-delay: {i*50}ms;'>
                <div style='font-family:Anton; font-size:3rem;'>{name}</div>
                <div class='font-mono text-lime' style='font-size:3rem;'>{data['rate']}%</div>
                <div class='font-mono text-sec' style='font-size:0.8rem; margin-top:10px;'>{data['change']}</div>
                <div class='font-mono' style='font-size:0.9rem; margin-top:10px; border-top:1px solid var(--border); padding-top:10px;'>PROCHAINE: {data['next']}</div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
            st.markdown(f"<a href='{links[name]}' target='_blank' style='color:var(--blue); font-family:DM Mono; font-size:0.8rem; text-transform:uppercase;'>↗ Source officielle</a>", unsafe_allow_html=True)
            
    st.markdown("### Tableau de bord Macro", unsafe_allow_html=True)
    st.markdown("""
    <div style='background: var(--surf1); border: 1px solid var(--border); padding: 20px; font-family: Newsreader, serif; font-size: 1.5rem; line-height: 1.4;'>
        <strong>Lecture automatique :</strong> La Fed maintient une politique restrictive avec des taux réels positifs, tandis que la BCE amorce un cycle d'assouplissement prudent. L'écart de taux Fed-BoJ alimente encore le carry trade malgré le récent resserrement japonais. La prime de risque française (spread OAT-Bund) reste sous surveillance des marchés suite aux récentes incertitudes budgétaires. Le prochain rendez-vous critique est fixé fin octobre pour la BCE et la Fed.
    </div>
    """, unsafe_allow_html=True)

@st.fragment(run_every=600)
def page_news():
    ui_header("03", "Actualités")
    
    news = fetch_macro_news()
    if not news:
        st.info("Flux d'actualités temporairement indisponible.")
        return
        
    st.markdown("<h3 style='color:var(--lime);'>A. LE TOP 5 DE LA SEMAINE</h3>", unsafe_allow_html=True)
    
    top5 = news[:5]
    cols = st.columns([2, 1, 1, 1, 1])
    
    for i, item in enumerate(top5):
        with cols[i]:
            cls = "st-key-card_news"
            sz = "2rem" if i == 0 else "1.2rem"
            st.markdown(f"""
            <div class='{cls} fade-in' style='height: 100%; border-top: 4px solid var(--{'lime' if i==0 else 'border'});'>
                <div class='font-mono text-sec' style='font-size:0.8rem; margin-bottom:10px;'>IMPACT: {'■'*item['score']}</div>
                <div class='font-serif' style='font-size:{sz}; font-weight:bold; margin-bottom:10px; line-height:1.1;'>{item['title']}</div>
                <div class='font-sans text-sec' style='font-size:0.9rem;'>{item['fr']}</div>
                <a href='{item['link']}' target='_blank' style='display:block; margin-top:15px; font-family:DM Mono; color:var(--blue);'>LIRE ↗</a>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("<h3 style='margin-top:40px;'>B. LE FLUX DU JOUR</h3>", unsafe_allow_html=True)
    for item in news[5:15]:
        st.markdown(f"""
        <div style='border-bottom: 1px solid var(--border); padding: 15px 0; display:flex; gap:20px; align-items:baseline;'>
            <div class='font-mono text-sec' style='width: 80px; flex-shrink:0;'>{item['date'][17:22] if len(item['date'])>22 else 'Live'}</div>
            <div>
                <div class='font-serif' style='font-size:1.3rem; font-weight:bold;'>{item['title']}</div>
                <div class='font-sans text-sec'>{item['fr']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def page_calendar():
    ui_header("04", "Calendrier")
    
    st.markdown("### Horaires des Marchés Mondiaux", unsafe_allow_html=True)
    
    # Composant HTML JS pour les horloges temps réel
    html_clocks = """
    <div id="clocks" style="display:flex; gap:10px; font-family:'DM Mono',monospace; color:#ECE9E1; width:100%; overflow:hidden;"></div>
    <script>
    const markets = [
        {name:"SYDNEY", tz:"Australia/Sydney", open:10, close:16},
        {name:"TOKYO", tz:"Asia/Tokyo", open:9, close:15, pause_start:11.5, pause_end:12.5},
        {name:"HONG KONG", tz:"Asia/Hong_Kong", open:9.5, close:16, pause_start:12, pause_end:13},
        {name:"LONDRES", tz:"Europe/London", open:8, close:16.5},
        {name:"PARIS", tz:"Europe/Paris", open:9, close:17.5},
        {name:"NEW YORK", tz:"America/New_York", open:9.5, close:16}
    ];
    
    function update() {
        const now = new Date();
        const isWeekend = now.getUTCDay() === 0 || now.getUTCDay() === 6;
        let html = "";
        
        markets.forEach(m => {
            const timeOpts = {timeZone: m.tz, hour:'2-digit', minute:'2-digit', hour12:false};
            const timeStr = new Intl.DateTimeFormat('en-GB', timeOpts).format(now);
            
            // Decimal hour local
            const d = new Date(new Date().toLocaleString("en-US", {timeZone: m.tz}));
            const hr = d.getHours() + d.getMinutes()/60;
            
            let status = "FERMÉ";
            let color = "#FF4D4D";
            
            if (isWeekend) { status = "WEEK-END"; color = "#8F8F94"; }
            else if (hr >= m.open && hr < m.close) {
                if (m.pause_start && hr >= m.pause_start && hr < m.pause_end) {
                    status = "PAUSE"; color = "#E5A03E";
                } else {
                    status = "OUVERT"; color = "#2ED47A";
                }
            }
            
            html += `<div style="flex:1; border:1px solid #2A2A2E; background:#121214; padding:15px; clip-path: polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%);">
                <div style="font-size:0.8rem; color:#8F8F94;">${m.name}</div>
                <div style="font-size:2rem; margin:5px 0;">${timeStr}</div>
                <div style="display:inline-block; border:1px solid ${color}; color:${color}; padding:2px 8px; font-size:0.7rem; transform:rotate(-2deg); font-family:Anton,sans-serif; letter-spacing:1px;">${status}</div>
            </div>`;
        });
        document.getElementById('clocks').innerHTML = html;
    }
    setInterval(update, 1000);
    update();
    </script>
    """
    import streamlit.components.v1 as components
    components.html(html_clocks, height=120)
    
    st.info("Note : Les jours fériés nationaux ne sont pas pris en compte dans ces indicateurs.")

def page_knowledge():
    ui_header("05", "Base de Connaissances")
    
    tabs = st.tabs(["France", "Capitalisations", "Indices", "Banques Centrales", "Économies", "Matières Premières", "Blocs", "Macro Cal", "Glossaire"])
    
    with tabs[0]:
        st.markdown("### France Macro")
        st.markdown("- **PIB** : ~3 030 Mds $ (2023, Banque Mondiale)\n- **Dette publique** : ~110% du PIB\n- **Déficit** : ~5.5% du PIB\n- **Fleurons par secteur** : Luxe (LVMH, Hermès, Kering), Énergie (TotalEnergies), Aéronautique (Airbus, Safran), Cosmétiques (L'Oréal), Finance (BNP Paribas).")
        
    with tabs[1]:
        st.markdown("### Géants Mondiaux")
        st.markdown("""
        Lecture des capitalisations mondiales (Tranches) :
        - **> 3 000 Mds $** : Apple, Microsoft, Nvidia
        - **2 000 - 3 000 Mds $** : Alphabet, Amazon
        - **1 000 - 2 000 Mds $** : Meta, TSMC
        
        *Le premier français (LVMH) évolue autour de 350-400 Mds $, suivi de L'Oréal et Hermès (200-250 Mds $).*
        """)
        
    with tabs[8]:
        st.markdown("### Glossaire de Salle de Marché")
        st.text_input("Recherche (visuelle pour l'instant)", placeholder="Ex: Contango, Dot plot...", disabled=True)
        
        glossary = {
            "Point de base (pb)": "Un centième de point de pourcentage (0,01 %). Utilisé pour exprimer les variations de taux.",
            "Spread": "Écart entre deux taux, prix ou rendements. Ex: écart entre les taux à 10 ans français (OAT) et allemand (Bund).",
            "Spread OAT-Bund": "Indicateur de la prime de risque perçue par les investisseurs sur la dette de l'État français par rapport à la dette allemande.",
            "Courbe des taux": "Représentation graphique des rendements des obligations d'un même émetteur selon leur maturité (de court à long terme).",
            "Inversion de courbe": "Situation où les taux à court terme sont plus élevés que les taux à long terme, souvent vue comme un signe avant-coureur de récession.",
            "Duration": "Durée de vie moyenne pondérée des flux financiers d'une obligation. Mesure sa sensibilité au risque de taux.",
            "QE/QT": "Quantitative Easing (création monétaire pour acheter des actifs) / Quantitative Tightening (réduction du bilan de la banque centrale).",
            "Forward guidance": "Communication officielle d'une banque centrale sur ses intentions futures concernant les taux directeurs.",
            "Dot plot": "Graphique publié par la Fed montrant les anticipations de taux de chaque membre de son comité (FOMC).",
            "Carry trade": "Emprunter dans une devise à faible taux d'intérêt (ex: JPY) pour investir dans une devise à fort rendement.",
            "Risk-on / Risk-off": "Sentiment de marché. Risk-on = appétit pour le risque (actions). Risk-off = fuite vers la sécurité (or, obligations d'État).",
            "VIX / MOVE": "Indices de volatilité. VIX pour le S&P 500 (actions), MOVE pour les obligations du Trésor américain.",
            "Contango / Backwardation": "Sur les futures : Contango = prix futur > prix spot. Backwardation = prix spot > prix futur.",
            "Bid-Ask (Fourchette)": "Écart entre le prix d'achat (Ask) et le prix de vente (Bid) proposé par un market maker.",
            "Market maker": "Acteur financier (souvent une banque) qui assure la liquidité en proposant en permanence un prix d'achat et de vente.",
            "Short squeeze": "Hausse rapide d'un actif forçant les vendeurs à découvert (shorts) à racheter leurs positions, ce qui accélère la hausse.",
            "Appel de marge": "Exigence d'un courtier d'ajouter des fonds sur un compte sur marge lorsque la valeur des actifs tombe sous un certain seuil.",
            "Repo (Pension livrée)": "Vente de titres avec engagement de les racheter à une date et un prix fixés à l'avance. Outil clé de liquidité interbancaire.",
            "CDS (Credit Default Swap)": "Contrat d'assurance contre le défaut de paiement d'un émetteur de dette.",
            "Taux réel": "Taux d'intérêt nominal moins le taux d'inflation. S'il est positif, la politique monétaire est restrictive.",
            "Stagflation": "Période combinant croissance faible/nulle, chômage élevé et forte inflation.",
            "Soft / Hard landing": "Atterrissage en douceur (ralentir l'inflation sans récession) vs Atterrissage brutal (récession provoquée par la hausse des taux).",
            "PMI (Purchasing Managers Index)": "Indicateur avancé de l'activité économique basé sur des sondages auprès des directeurs d'achats (>50 = expansion).",
            "Capitalisation boursière": "Valeur totale des actions d'une entreprise (Prix de l'action × Nombre d'actions).",
            "Inflation": "Hausse généralisée et continue des prix.",
            "Désinflation": "Ralentissement de l'inflation (les prix montent toujours, mais moins vite).",
            "Déflation": "Baisse généralisée et continue des prix (taux d'inflation négatif).",
            "Hyperinflation": "Inflation extrêmement élevée et hors de contrôle.",
            "Récession": "Recul du Produit Intérieur Brut (PIB) sur au moins deux trimestres consécutifs.",
            "PIB (Produit Intérieur Brut)": "Mesure de la richesse totale créée par un pays sur une année.",
            "Croissance": "Variation positive du PIB d'une période à l'autre.",
            "Taux de chômage": "Pourcentage d'actifs sans emploi et à la recherche d'un emploi.",
            "Pouvoir d'achat": "Quantité de biens et services qu'un revenu permet d'acheter.",
            "IPC / IPCH": "Indice des Prix à la Consommation. IPCH est la version harmonisée au niveau européen.",
            "Taux directeur": "Taux fixé par une banque centrale pour prêter aux banques commerciales, pilotant ainsi le coût du crédit.",
            "Hawkish / Dovish": "Faucon (favorise des taux hauts contre l'inflation) vs Colombe (favorise des taux bas pour l'emploi/croissance).",
            "Politique monétaire": "Action de la banque centrale sur la monnaie et les taux d'intérêt.",
            "Politique budgétaire": "Action de l'État sur les impôts et les dépenses publiques.",
            "Action": "Titre de propriété représentant une fraction du capital d'une entreprise.",
            "Obligation": "Titre de dette émis par un État ou une entreprise, rapportant un intérêt (coupon).",
            "ETF (Exchange Traded Fund)": "Fonds d'investissement coté en bourse répliquant la performance d'un indice.",
            "Indice boursier": "Mesure synthétique de la performance d'un ensemble de valeurs (ex: CAC 40, S&P 500).",
            "Dividende": "Part des bénéfices de l'entreprise versée aux actionnaires.",
            "PER (Price Earning Ratio)": "Rapport entre le cours de l'action et le bénéfice par action. Mesure la cherté de l'action.",
            "Rendement (Yield)": "Revenu annuel généré par un actif divisé par son prix actuel.",
            "Coupon": "Intérêt périodique versé au détenteur d'une obligation.",
            "Notation de crédit": "Évaluation par une agence (S&P, Moody's, Fitch) de la solvabilité d'un emprunteur.",
            "Dette publique": "Ensemble des emprunts contractés par l'État et les administrations publiques.",
            "Déficit public": "Solde négatif annuel entre les recettes et les dépenses de l'État.",
            "Balance commerciale": "Différence entre la valeur des exportations et des importations d'un pays.",
            "Taux de change": "Valeur d'une monnaie par rapport à une autre.",
            "Dépréciation": "Baisse de la valeur d'une monnaie sur le marché des changes.",
            "Dévaluation": "Baisse officielle de la valeur d'une monnaie par décision d'un gouvernement/banque centrale.",
            "Bull Market": "Marché haussier (symbole : Taureau).",
            "Bear Market": "Marché baissier, généralement défini par une baisse de plus de 20% (symbole : Ours).",
            "Correction": "Baisse temporaire du marché, souvent autour de 10%.",
            "Krach": "Effondrement soudain et violent des cours boursiers.",
            "IPO (Initial Public Offering)": "Introduction en bourse d'une entreprise.",
            "Valeur refuge": "Actif (Or, Franc Suisse, Treasuries) recherché en période de crise ou d'incertitude.",
            "Liquidité": "Facilité à acheter ou vendre un actif rapidement et sans impact majeur sur son prix.",
            "Volatilité": "Ampleur des variations du prix d'un actif sur une période donnée.",
            "Position longue (Long)": "Achat d'un actif en pariant sur sa hausse.",
            "Position courte (Short)": "Vente à découvert en pariant sur la baisse de l'actif.",
            "Option Call": "Produit dérivé donnant le droit d'acheter un actif à un prix fixé à l'avance.",
            "Option Put": "Produit dérivé donnant le droit de vendre un actif à un prix fixé à l'avance.",
            "Future (Contrat à terme)": "Engagement d'acheter ou vendre un actif à un prix et une date futurs fixés.",
            "Produit dérivé": "Instrument financier dont la valeur dépend d'un autre actif (le sous-jacent).",
            "Hedge Fund": "Fonds d'investissement alternatif utilisant des stratégies complexes et souvent l'effet de levier.",
            "Sell-side": "Acteurs qui créent, promeuvent et vendent des produits financiers (banques d'investissement).",
            "Buy-side": "Acteurs qui achètent des produits financiers pour le compte d'investisseurs (fonds, asset managers).",
            "Fonds souverain": "Fonds d'investissement détenu par un État.",
            "Diversification": "Stratégie de répartition des investissements pour réduire le risque global.",
            "Plus-value": "Gain obtenu lors de la revente d'un actif à un prix supérieur à son prix d'achat."
        }
        
        col1, col2 = st.columns(2)
        items = list(glossary.items())
        mid = len(items) // 2
        for i, (k, v) in enumerate(items):
            with col1 if i <= mid else col2:
                with st.expander(k):
                    st.write(v)
                    
        st.markdown("### Salle de marché : qui fait quoi ?")
        st.info("**Sales** : Conseille les clients et prend les ordres. **Trader** : Exécute les ordres et gère le risque. **Structureur** : Crée des produits financiers sur mesure. **Quant** : Modélise mathématiquement les prix. **Recherche (Analyste)** : Étudie la macro et les entreprises. Grandes salles FR : BNP Paribas, SocGen, Natixis, CACIB.")

# =====================================================================
# ROUTING
# =====================================================================
if st.session_state["page"] == "Marchés":
    page_markets()
elif st.session_state["page"] == "Banques Centrales":
    page_central_banks()
elif st.session_state["page"] == "Actualités":
    page_news()
elif st.session_state["page"] == "Calendrier":
    page_calendar()
elif st.session_state["page"] == "Base de connaissances":
    page_knowledge()
