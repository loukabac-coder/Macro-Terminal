import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import feedparser
import requests

st.set_page_config(page_title="PRO Macro Terminal", layout="wide", initial_sidebar_state="expanded")

# --- DESIGN SYSTEM & CSS PREMIUM ---
st.markdown('''
    <style>
    .stApp { background-color: #030303; color: #FFFFFF; font-family: 'Inter', sans-serif; }
    .stSidebar { background-color: #0A0A0A !important; border-right: 1px solid #1a1a1a; }
    .metric-card {
        background: linear-gradient(145deg, #0d0d0d, #141414);
        border: 1px solid #222222; border-radius: 12px; padding: 18px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5); transition: all 0.3s ease; margin-bottom: -15px;
    }
    .metric-card:hover { transform: translateY(-4px); border-color: #3b82f6; box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15); }
    .metric-title { color: #888; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .metric-value { color: #FFF; font-size: 1.8rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .metric-delta.positive { color: #10B981; font-size: 1rem; font-weight: 600; margin-left: 10px; font-family: 'JetBrains Mono', monospace; }
    .metric-delta.negative { color: #EF4444; font-size: 1rem; font-weight: 600; margin-left: 10px; font-family: 'JetBrains Mono', monospace; }
    h1 { font-weight: 800; background: -webkit-linear-gradient(0deg, #FFFFFF, #666666); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-bottom: 10px;}
    </style>
''', unsafe_allow_html=True)

# --- UNIVERSE DES ACTIFS EXHAUSTIF ---
UNIVERSE = {
    "🏛️ Taux & Banques Centrales": {
        "US 10Y Treasury": "^TNX",
        "US 2Y Treasury": "^IRX",
        "Bund 10Y (Allemagne)": "^DE10Y=X",
        "OAT 10Y (France)": "^FR10Y=X",
        "BTP 10Y (Italie)": "^IT10Y=X",
        "Gilt 10Y (UK)": "^GB10Y=X",
        "JGB 10Y (Japon)": "^JP10Y=X"
    },
    "🌍 Actions & Indices": {
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
        "CSI 300 (Chine)": "000300.SS",
        "Nifty 50 (Inde)": "^NSEI",
        "MSCI World (Proxy URTH)": "URTH",
        "MSCI Emerging (Proxy EEM)": "EEM"
    },
    "💱 Devises (Forex)": {
        "DXY (Dollar Index)": "DX-Y.NYB",
        "EUR/USD (Fiber)": "EURUSD=X",
        "GBP/USD (Cable)": "GBPUSD=X",
        "USD/JPY (Ninja)": "USDJPY=X",
        "USD/CHF (Refuge)": "USDCHF=X",
        "AUD/USD (Aussie)": "AUDUSD=X",
        "USD/CAD (Loonie)": "USDCAD=X",
        "USD/CNH (Yuan)": "USDCNH=X",
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
        "Novo Nordisk (Santé)": "NVO",
        "LVMH (Luxe)": "MC.PA",
        "ASML (Semi-conducteurs)": "ASML.AS",
        "Bitcoin (Crypto)": "BTC-USD"
    },
    "🚨 Volatilité & Crédit": {
        "VIX (Indice de la Peur)": "^VIX",
        "MOVE (Volatilité Taux)": "^MOVE",
        "High Yield (Risque Crédit)": "HYG",
        "Investment Grade (Dette)": "LQD"
    }
}

# --- FETCH DATA (REQUÊTE BATCH UNIQUE ANTI-BLOCAGE) ---
@st.cache_data(ttl=300)
def load_all_data():
    all_tickers = []
    for cat in UNIVERSE.values():
        all_tickers.extend(cat.values())
    df = yf.download(all_tickers, period="3mo", threads=True, progress=False)
    return df['Close']

# --- MINI CHART (DESIGN ÉPURÉ) ---
def mini_chart(series, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode='lines', line=dict(color=color, width=2.5),
        fill='tozeroy', 
        fillcolor=f"rgba{tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.15,)}"
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=80,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=False, visible=False),
        hovermode='x unified'
    )
    return fig

# --- NAVIGATION SIDEBAR ---
st.sidebar.title("⚡ MACRO TERMINAL")
st.sidebar.markdown(f"<div style='color: #666; font-size: 0.8rem; margin-bottom: 30px;'>Live: {datetime.utcnow().strftime('%H:%M UTC')}</div>", unsafe_allow_html=True)
category = st.sidebar.radio("NAVIGATION", list(UNIVERSE.keys()) + ["📰 Actualités Macro En Direct"])

# --- CONTENU PRINCIPAL ---
if category != "📰 Actualités Macro En Direct":
    st.title(category)
    st.markdown("---")
    
    with st.spinner("Synchronisation avec les marchés..."):
        df_close = load_all_data()
        
    assets = UNIVERSE[category]
    cols = st.columns(4)
    
    for i, (name, ticker) in enumerate(assets.items()):
        col = cols[i % 4]
        with col:
            if ticker in df_close.columns:
                series = df_close[ticker].dropna()
                if len(series) >= 2:
                    curr = series.iloc[-1]
                    prev = series.iloc[-2]
                    pct = ((curr - prev) / prev) * 100
                    
                    is_rate = "10Y" in name or "2Y" in name or "VIX" in name or "MOVE" in name
                    val_str = f"{curr:.2f}%" if is_rate and curr < 150 else f"{curr:,.2f}"
                    pct_str = f"{pct:+.2f}%"
                    
                    color = "#10B981" if pct >= 0 else "#EF4444"
                    delta_class = "positive" if pct >= 0 else "negative"
                    
                    if "VIX" in name or "MOVE" in name:
                        color = "#EF4444" if pct >= 0 else "#10B981"
                        delta_class = "negative" if pct >= 0 else "positive"
                        
                    chart = mini_chart(series.tail(30), color)
                    
                    html_card = f'''
                    <div class="metric-card">
                        <div class="metric-title">{name}</div>
                        <div>
                            <span class="metric-value">{val_str}</span>
                            <span class="metric-delta {delta_class}">{pct_str}</span>
                        </div>
                    </div>
                    '''
                    st.markdown(html_card, unsafe_allow_html=True)
                    st.plotly_chart(chart, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.warning(f"{name} : Données insuffisantes")
            else:
                st.warning(f"{name} : Hors ligne")

else:
    # --- ONGLET ACTUALITÉS (FIXÉ AVEC HEADERS ET FLUX FIABLE) ---
    st.title("📰 Actualités Macro En Direct")
    st.markdown("---")
    
    # Remplacement de Yahoo Finance (souvent bloqué) par le flux Global Markets du Wall Street Journal ou CNBC
    feed_url = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
    
    try:
        # L'ajout du User-Agent est obligatoire pour ne pas se faire bloquer par les sites d'actualité
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(feed_url, headers=headers, timeout=5)
        news_feed = feedparser.parse(response.content)
        
        if not news_feed.entries:
            st.warning("Aucune actualité trouvée sur le flux principal.")
            
        for entry in news_feed.entries[:20]:
            pub_date = getattr(entry, 'published', 'Date inconnue')
            st.markdown(f'''
            <div style="background: linear-gradient(145deg, #0d0d0d, #141414); padding: 20px; border-radius: 12px; border: 1px solid #222; margin-bottom: 15px; transition: all 0.3s ease;">
                <a href="{entry.link}" target="_blank" style="color: #FFF; font-size: 1.1rem; font-weight: 600; text-decoration: none;">{entry.title}</a>
                <div style="color: #666; font-size: 0.8rem; margin-top: 8px;">🕒 {pub_date}</div>
            </div>
            ''', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Impossible de charger les news. Détail technique : {e}")
