import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import feedparser
import requests
from deep_translator import GoogleTranslator

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

# --- UNIVERSE DES ACTIFS (Tickers Corrigés) ---
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

# --- FETCH DATA ---
@st.cache_data(ttl=300)
def load_all_data():
    all_tickers = []
    for cat in UNIVERSE.values():
        all_tickers.extend(cat.values())
    df = yf.download(all_tickers, period="3mo", threads=True, progress=False)
    return df['Close']

# --- MINI CHART ---
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
options = list(UNIVERSE.keys()) + ["📰 Actualités Macro (FR)", "📚 Base de Connaissances"]
category = st.sidebar.radio("NAVIGATION", options)

# --- CONTENU : DONNÉES DE MARCHÉ ---
if category in UNIVERSE:
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

# --- CONTENU : ACTUALITÉS (TRADUITES) ---
elif category == "📰 Actualités Macro (FR)":
    st.title("📰 Actualités & Résumé de la Semaine")
    st.markdown("---")
    
    feed_url = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
    translator = GoogleTranslator(source='auto', target='fr')
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers, timeout=5)
        news_feed = feedparser.parse(response.content)
        
        if news_feed.entries:
            st.subheader("🔥 Top 5 : Les faits marquants de la semaine")
            st.markdown("Sélection des événements à plus fort impact macroéconomique et géopolitique :")
            
            # Top 5 News
            for entry in news_feed.entries[:5]:
                fr_title = translator.translate(entry.title)
                pub_date = getattr(entry, 'published', 'Date inconnue')
                st.markdown(f'''
                <div style="background: linear-gradient(145deg, #1a0f0f, #2a1111); border-left: 4px solid #EF4444; padding: 20px; border-radius: 8px; margin-bottom: 15px;">
                    <a href="{entry.link}" target="_blank" style="color: #FFF; font-size: 1.2rem; font-weight: 700; text-decoration: none;">{fr_title}</a>
                    <div style="color: #888; font-size: 0.85rem; margin-top: 8px;">🕒 {pub_date} | Source: CNBC Markets</div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📡 Flux Macro Continu")
            
            # Rest of the news
            for entry in news_feed.entries[5:20]:
                fr_title = translator.translate(entry.title)
                pub_date = getattr(entry, 'published', 'Date inconnue')
                st.markdown(f'''
                <div style="background: linear-gradient(145deg, #0d0d0d, #141414); padding: 15px; border-radius: 8px; border: 1px solid #222; margin-bottom: 10px;">
                    <a href="{entry.link}" target="_blank" style="color: #E2E8F0; font-size: 1rem; font-weight: 500; text-decoration: none;">{fr_title}</a>
                    <div style="color: #666; font-size: 0.8rem; margin-top: 5px;">🕒 {pub_date}</div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.warning("Aucune actualité trouvée.")
    except Exception as e:
        st.error(f"Erreur de chargement ou de traduction : {e}")

# --- CONTENU : BASE DE CONNAISSANCES ---
elif category == "📚 Base de Connaissances":
    st.title("📚 Base de Connaissances Macroéconomiques")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('''
        ### 💰 Capitalisations Boursières : Les Ordres de Grandeur (En USD)
        * **Le Club des > 3 000 Milliards $ (Les "Big 3")** : Apple, Microsoft, NVIDIA.
        * **Le Club des > 2 000 Milliards $** : Alphabet (Google), Amazon, Saudi Aramco.
        * **Le Club des > 1 000 Milliards $** : Meta, Berkshire Hathaway, TSMC (Taiwan Semiconductor), Eli Lilly (Pharma), Broadcom.
        * **Les Poids Lourds Européens (En EUR/USD)** : Novo Nordisk (~550-600 Mds $), LVMH (~400 Mds $), ASML (~350-400 Mds $), SAP, Hermès.
        * **Total Crypto-marché** : ~2 500 Milliards $ (dont Bitcoin représente environ 50 à 55 %).
        
        ### 🏭 Les plus grandes entreprises du S&P 500 (Par pondération)
        1. **Microsoft** (Tech / Cloud / IA)
        2. **Apple** (Hardware / Services)
        3. **NVIDIA** (Semi-conducteurs / IA)
        4. **Amazon** (E-commerce / Cloud)
        5. **Alphabet** (Publicité / Moteur de recherche)
        *(Note : Ces 5 entreprises pèsent à elles seules près de 25% de l'indice total).*
        
        ### 🌍 Les Blocs Économiques & Alliances
        * **G7** : USA, Japon, Allemagne, UK, France, Italie, Canada (+ UE).
        * **BRICS+** : Brésil, Russie, Inde, Chine, Afrique du Sud (rejoints récemment par l'Iran, l'Égypte, l'Éthiopie et les Émirats arabes unis).
        * **OPEP+** : Le cartel pétrolier mené par l'Arabie Saoudite, allié à la Russie pour contrôler l'offre mondiale de brut.
        ''')
        
    with col2:
        st.markdown('''
        ### 🗺️ Les plus grandes économies du monde (PIB nominal)
        1. **États-Unis** (~28 000 Milliards $)
        2. **Chine** (~18 500 Milliards $)
        3. **Allemagne** (~4 500 Milliards $ - a récemment dépassé le Japon suite à la faiblesse du Yen)
        4. **Japon** (~4 200 Milliards $)
        5. **Inde** (~3 900 Milliards $ - en forte croissance, vise le top 3 avant 2030)
        
        ### 🇪🇺 Les plus grandes économies d'Europe (Par PIB)
        1. **Allemagne** (Moteur industriel)
        2. **Royaume-Uni** (Moteur financier et services)
        3. **France** (Moteur diversifié : luxe, aéro, énergie, services)
        4. **Italie** (Moteur manufacturier)
        5. **Espagne** (Tourisme et services)
        
        ### 🛢️ Géopolitique des Matières Premières (Plus grands producteurs)
        * **Pétrole (Barils/jour)** : 1. États-Unis, 2. Arabie Saoudite, 3. Russie.
        * **Gaz Naturel** : 1. États-Unis, 2. Russie, 3. Iran.
        * **Or (Mines)** : 1. Chine, 2. Australie, 3. Russie.
        * **Cuivre** : 1. Chili, 2. Pérou, 3. RDC (Congo).
        * **Lithium (Batteries)** : 1. Australie, 2. Chili, 3. Chine.
        
        ### 📊 Leaders Étrangers Clés
        * **Inde (Nifty 50)** : 1. Reliance Industries (Conglomérat / Mukesh Ambani), 2. TCS (Services IT), 3. HDFC Bank.
        * **Europe (Stoxx 600)** : 1. Novo Nordisk (Santé/Diabète), 2. LVMH (Luxe), 3. ASML (Semi-conducteurs / EUV).
        ''')
