import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import feedparser
import requests_cache

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Institutional Global Macro Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- DESIGN SYSTEM : BLOOMBERG / LINEAR DARK THEME ---
st.markdown("""
    <style>
    .stApp { background-color: #090D16; color: #E2E8F0; font-family: 'Inter', -apple-system, sans-serif; }
    h1, h2, h3 { color: #F8FAFC; font-weight: 700; letter-spacing: -0.025em; }
    div[data-testid="stMetricValue"] { color: #F8FAFC; font-size: 20px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    div[data-testid="stMetricDelta"] { font-size: 12px; font-family: 'JetBrains Mono', monospace; }
    div[data-testid="stMetricDelta"] svg { display: none; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #090D16; padding-bottom: 8px; border-bottom: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab"] { background-color: #111827; border-radius: 4px; padding: 6px 14px; border: 1px solid #1F2937; color: #94A3B8; font-weight: 500; font-size: 14px; }
    .stTabs [aria-selected="true"] { background-color: #1E293B; border: 1px solid #3B82F6; color: #FFFFFF; }
    .news-card { background-color: #111827; border: 1px solid #1F2937; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; }
    .news-title { color: #F8FAFC; font-weight: 600; font-size: 15px; text-decoration: none; }
    .news-title:hover { color: #3B82F6; }
    .news-date { color: #64748B; font-size: 11px; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

# --- EN-TÊTE DU TERMINAL ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("⚡ GLOBAL MACRO & MARKET TERMINAL")
    st.caption("Flux Multi-Actifs en Temps Réel — Taux, Central Banks, FX, Indices mondiaux, Commodities & Actualités")
with col_head2:
    st.markdown(f"<div style='text-align: right; color: #10B981; font-family: monospace; font-weight: 600; padding-top: 15px;'>● CONNECTÉ<br><span style='color: #64748B; font-size: 10px;'>{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</span></div>", unsafe_allow_html=True)

st.markdown("---")

# --- DICTIONNAIRE DES TICKERS FIABILISÉS ---
UNIVERSE = {
    "1. Taux & Banques Centrales": {
        "US 10Y Treasury Yield": "^TNX",
        "US 2Y Treasury Yield": "^IRX",
        "Germany 10Y Bund": "^DE10Y=X",
        "UK 10Y Gilt": "^GB10Y=X",
        "Japan 10Y JGB": "^JP10Y=X",
        "VIX (Volatilité Actions)": "^VIX",
        "DXY (US Dollar Index)": "DX-Y.NYB"
    },
    "2. Devises (Forex)": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "USDJPY=X",
        "USD/CHF": "USDCHF=X",
        "AUD/USD": "AUDUSD=X",
        "USD/CAD": "USDCAD=X",
        "USD/BRL (Brésil)": "USDBRL=X",
        "USD/ZAR (Afrique du Sud)": "USDZAR=X",
        "USD/MXN (Mexique)": "USDMXN=X",
        "USD/CNY (Yuan Chinois)": "USDCNY=X",
        "USD/INR (Roupie Indienne)": "USDINR=X"
    },
    "3. Actions Développées": {
        "S&P 500 (US)": "^GSPC",
        "Nasdaq 100 (Tech US)": "^NDX",
        "Dow Jones Industrial": "^DJI",
        "Russell 2000 (Small Caps)": "^RUT",
        "Euro Stoxx 50": "^STOXX50E",
        "CAC 40 (France)": "^FCHI",
        "DAX 40 (Allemagne)": "^GDAXI",
        "FTSE 100 (UK)": "^FTSE"
    },
    "4. Actions Asie & Émergentes": {
        "Nikkei 225 (Japon)": "^N225",
        "Hang Seng (Hong Kong)": "^HSI",
        "Shanghai Composite": "000001.SS",
        "Nifty 50 (Inde)": "^NSEI",
        "KOSPI (Corée du Sud)": "^KS11",
        "Bovespa (Brésil)": "^BVSP"
    },
    "5. Mega-Caps & Big Tech": {
        "Apple (AAPL)": "AAPL",
        "Microsoft (MSFT)": "MSFT",
        "Nvidia (NVDA)": "NVDA",
        "Alphabet / Google (GOOGL)": "GOOGL",
        "Amazon (AMZN)": "AMZN",
        "Meta Platforms (META)": "META",
        "Tesla (TSLA)": "TSLA",
        "TSMC (Semi-conducteurs)": "TSM",
        "ASML (Équipementiers Tech)": "ASML.AS",
        "LVMH (Luxe Europe)": "MC.PA"
    },
    "6. Matières Premières & Énergie": {
        "WTI Crude (Pétrole US)": "CL=F",
        "Brent Crude (Pétrole Global)": "BZ=F",
        "Natural Gas (Henry Hub)": "NG=F",
        "Gold (Or)": "GC=F",
        "Silver (Argent)": "SI=F",
        "Copper (Cuivre - Baromètre Macro)": "HG=F",
        "Wheat (Blé)": "ZW=F",
        "Corn (Maïs)": "ZC=F"
    }
}

# --- FONCTION DE FETCH ROBUSTE AVEC SESSION HTTP ---
@st.cache_data(ttl=600)
def get_market_data(ticker_symbol):
    try:
        session = requests_cache.CachedSession('yfinance.cache', expire_after=300)
        session.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        t = yf.Ticker(ticker_symbol, session=session)
        df = t.history(period="6m")
        if df.empty or len(df) < 2:
            return None, 0.0, 0.0
        curr = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        pct = ((curr - prev) / prev) * 100
        return df, curr, pct
    except Exception:
        return None, 0.0, 0.0

# --- FONCTION GRAPHIQUE MINIMALISTE PRO ---
def mini_chart(df, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        mode='lines', line=dict(color=color, width=1.5),
        fill='tozeroy', fillcolor=f"rgba{tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.08,)}"
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=85,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=False, visible=False)
    )
    return fig

# --- NAVIGATION PAR ONGLETS ---
tabs = st.tabs(list(UNIVERSE.keys()) + ["7. 📰 News & Flux Macro En Direct"])

for idx, (cat_name, assets) in enumerate(UNIVERSE.items()):
    with tabs[idx]:
        st.subheader(cat_name)
        cols = st.columns(4)
        for i, (name, ticker) in enumerate(assets.items()):
            col = cols[i % 4]
            df, price, delta = get_market_data(ticker)
            
            if df is not None:
                is_rate_or_vix = "Yield" in name or "VIX" in name or "MOVE" in name
                p_str = f"{price:.2f}%" if is_rate_or_vix and price < 30 else f"{price:,.2f}"
                d_str = f"{delta:+.2f}%"
                
                color = "#10B981" if delta >= 0 else "#EF4444"
                if "VIX" in name or "MOVE" in name: 
                    color = "#EF4444" if delta >= 0 else "#10B981"

                with col:
                    st.metric(label=name, value=p_str, delta=d_str)
                    st.plotly_chart(mini_chart(df, color), use_container_width=True)
                    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
            else:
                col.warning(f"Indisponible ({name})")

# --- SECTION NEWS EN TEMPS RÉEL (FLUX RSS MONDIAL) ---
with tabs[-1]:
    st.subheader("📰 Actualités & Flux Macroéconomique en Temps Réel")
    st.caption("Dernières dépêches et analyses financières mondiales en direct des marchés.")
    
    try:
        feed_url = "https://finance.yahoo.com/news/rss"
        news_feed = feedparser.parse(feed_url)
        
        if news_feed.entries:
            for entry in news_feed.entries[:15]:
                pub_date = getattr(entry, 'published', 'Récemment')
                st.markdown(f"""
                <div class="news-card">
                    <a href="{entry.link}" target="_blank" class="news-title">{entry.title}</a>
                    <div class="news-date">🕒 {pub_date}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Chargement du flux d'actualités en cours...")
    except Exception as e:
        st.error("Impossible de charger les actualités en direct pour le moment.")
