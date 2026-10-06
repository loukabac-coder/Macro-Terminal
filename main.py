# ================================================================
# MACRO TERMINAL — GLOBAL MARKETS
# main.py
# ================================================================

import html
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import feedparser
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None


# ================================================================
# CONFIG
# ================================================================

st.set_page_config(
    page_title="Macro Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

PARIS = ZoneInfo("Europe/Paris")


# ================================================================
# UNIVERSE
# ================================================================

UNIVERSE = {
    "🚀 Leaders & Mega-Caps": {
        # 🇺🇸 US
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Nvidia": "NVDA",
        "Alphabet": "GOOGL",
        "Amazon": "AMZN",
        "Meta": "META",
        "Tesla": "TSLA",
        "Broadcom": "AVGO",
        "Berkshire Hathaway": "BRK-B",
        "Eli Lilly": "LLY",
        "JPMorgan": "JPM",
        "Visa": "V",
        "Walmart": "WMT",
        "Oracle": "ORCL",
        "Netflix": "NFLX",
        "AMD": "AMD",

        # 🌏 ASIE
        "TSMC": "TSM",
        "Tencent": "0700.HK",
        "Alibaba": "BABA",
        "Samsung Electronics": "005930.KS",
        "Toyota": "7203.T",

        # 🇪🇺 EUROPE
        "Novo Nordisk": "NVO",
        "ASML": "ASML.AS",
        "SAP": "SAP",
        "LVMH": "MC.PA",
        "Hermès": "RMS.PA",
        "L'Oréal": "OR.PA",
    }
}


# ================================================================
# CSS
# ================================================================

st.markdown(
    """
    <style>

    /* GLOBAL */

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #090D16 0%,
                #0B101B 55%,
                #080C14 100%
            );
        border-right: 1px solid rgba(255,255,255,.06);
    }

    /* SIDEBAR */

    section[data-testid="stSidebar"] {
        scrollbar-width: thin;
        scrollbar-color: rgba(129,140,248,.35) transparent;
    }

    section[data-testid="stSidebar"]::-webkit-scrollbar {
        width: 5px;
    }

    section[data-testid="stSidebar"]::-webkit-scrollbar-track {
        background: transparent;
    }

    section[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg,#6366F1,#22D3EE);
        border-radius: 99px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] {
        padding: 4px 2px 8px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        min-height: 42px;
        margin: 2px 0;
        padding: 9px 12px;
        border-radius: 13px;
        position: relative;
        overflow: hidden;
        transition: .2s;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"] > label::before {
        content: "";
        position: absolute;
        left: 0;
        top: 20%;
        width: 3px;
        height: 60%;
        border-radius: 99px;
        background: linear-gradient(180deg,#6366F1,#22D3EE);
        opacity: 0;
        transition: .2s;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    > label:has(input:checked)::before {
        opacity: 1;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    > label:has(input:checked) {
        background:
            linear-gradient(
                100deg,
                rgba(99,102,241,.25),
                rgba(34,211,238,.08)
            );
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"] > label:hover {
        transform: translateX(2px);
        background: rgba(255,255,255,.055);
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"] > label p {
        font-size: .84rem !important;
        line-height: 1.2;
    }

    section[data-testid="stSidebar"] .stRadio {
        margin-bottom: 4px;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 11px;
        margin-bottom: 12px;
    }

    .brand-logo {
        width: 38px;
        height: 38px;
        border-radius: 11px;
        display: flex;
        align-items: center;
        justify-content: center;
        background:
            linear-gradient(
                135deg,
                #6366F1,
                #22D3EE
            );
        box-shadow: 0 0 25px rgba(99,102,241,.25);
    }

    .brand-t {
        color: #F8FAFC;
        font-weight: 800;
        font-size: .82rem;
        letter-spacing: 1.4px;
    }

    .brand-s {
        color: #626B80;
        font-size: .65rem;
        margin-top: 2px;
    }

    .live {
        color: #A7F3D0;
        font-size: .63rem;
        letter-spacing: .8px;
        margin: 8px 0 20px;
    }

    .live i {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #34D399;
        box-shadow: 0 0 8px #34D399;
        margin-right: 6px;
    }

    .navlab {
        color: #687187;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        font-size: .58rem;
        margin-bottom: 7px;
    }

    .sidebar-status {
        margin-top: 20px;
        padding: 12px 13px;
        border-radius: 14px;
        background:
            linear-gradient(
                145deg,
                rgba(255,255,255,.055),
                rgba(255,255,255,.015)
            );
        border: 1px solid rgba(255,255,255,.07);
    }

    .sidebar-status-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }

    .sidebar-status-title {
        font-size: .65rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #687187;
    }

    .sidebar-status-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: .72rem;
        color: #A7F3D0;
    }

    .sidebar-status-sub {
        color: #596174;
        font-size: .65rem;
        line-height: 1.4;
    }

    /* HERO */

    .hero {
        position: relative;
        padding: 30px 32px;
        border-radius: 24px;
        overflow: hidden;
        margin-bottom: 24px;
        background:
            radial-gradient(
                circle at 90% 10%,
                rgba(99,102,241,.25),
                transparent 35%
            ),
            linear-gradient(
                145deg,
                rgba(255,255,255,.075),
                rgba(255,255,255,.018)
            );
        border: 1px solid rgba(255,255,255,.09);
    }

    .hero-eyebrow {
        color: #818CF8;
        font-size: .65rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 7px;
    }

    .hero-title {
        color: #F8FAFC;
        font-size: 2.1rem;
        font-weight: 850;
        line-height: 1.15;
    }

    .hero-sub {
        color: #7F899E;
        max-width: 800px;
        margin-top: 9px;
        line-height: 1.55;
        font-size: .9rem;
    }

    .pill {
        display: inline-flex;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(34,211,238,.08);
        border: 1px solid rgba(34,211,238,.2);
        color: #67E8F9;
        font-size: .58rem;
        font-weight: 800;
        letter-spacing: 1px;
    }

    /* NEWS */

    .news-pulse {
        display: flex;
        gap: 9px;
        overflow-x: auto;
        margin: -6px 0 24px;
        padding: 2px 2px 9px;
        scrollbar-width: none;
    }

    .news-pulse::-webkit-scrollbar {
        display: none;
    }

    .npulse {
        min-width: 145px;
        padding: 10px 13px;
        border-radius: 13px;
        background: rgba(255,255,255,.035);
        border: 1px solid rgba(255,255,255,.07);
    }

    .npulse-label {
        color: #687187;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: .58rem;
        margin-bottom: 3px;
    }

    .npulse-value {
        color: #F8FAFC;
        font-family: 'JetBrains Mono', monospace;
        font-size: .82rem;
        font-weight: 700;
    }

    .npulse-up {
        color: #34D399 !important;
    }

    .npulse-down {
        color: #FB7185 !important;
    }

    .news-hero {
        position: relative;
        overflow: hidden;
        min-height: 340px;
        padding: 30px;
        border-radius: 24px;
        display: block;
        text-decoration: none !important;
        background:
            radial-gradient(
                circle at 92% 5%,
                var(--c),
                transparent 34%
            ),
            linear-gradient(
                145deg,
                rgba(255,255,255,.095),
                rgba(255,255,255,.018)
            );
        border: 1px solid rgba(255,255,255,.11);
        box-shadow:
            0 25px 70px rgba(0,0,0,.42),
            inset 0 1px rgba(255,255,255,.08);
        transition: .3s;
    }

    .news-hero:hover {
        transform: translateY(-3px);
        border-color: var(--c);
        box-shadow:
            0 30px 80px rgba(0,0,0,.5),
            0 0 45px -10px var(--c);
    }

    .news-hero::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(180deg,var(--c),transparent);
    }

    .news-kicker {
        display: flex;
        align-items: center;
        gap: 9px;
        margin-bottom: 18px;
    }

    .news-rank {
        font-family: 'JetBrains Mono',monospace;
        color: var(--c);
        font-weight: 800;
        font-size: 1.4rem;
    }

    .news-category {
        display: inline-flex;
        align-items: center;
        padding: 5px 10px;
        border-radius: 99px;
        color: var(--c);
        background: color-mix(in srgb,var(--c) 12%,transparent);
        border: 1px solid color-mix(in srgb,var(--c) 35%,transparent);
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: .62rem;
        font-weight: 800;
    }

    .news-hero-title {
        color: #fff;
        font-size: 1.65rem;
        line-height: 1.28;
        font-weight: 800;
        max-width: 850px;
        margin-bottom: 13px;
    }

    .news-hero-fr {
        color: #8BE9FD;
        font-size: 1rem;
        line-height: 1.45;
        font-style: italic;
        max-width: 850px;
    }

    .news-meta {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 22px;
        color: #6B7389;
        font-size: .72rem;
    }

    .impact-dots {
        letter-spacing: 2px;
        color: var(--c);
    }

    .news-side {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .news-side-card {
        display: block;
        text-decoration: none !important;
        min-height: 102px;
        padding: 15px 16px;
        border-radius: 16px;
        background: rgba(255,255,255,.035);
        border: 1px solid rgba(255,255,255,.07);
        border-left: 3px solid var(--c);
        transition: .25s;
    }

    .news-side-card:hover {
        transform: translateX(4px);
        background: rgba(255,255,255,.065);
        border-color: var(--c);
    }

    .news-side-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        margin-bottom: 6px;
    }

    .news-side-rank {
        font-family: 'JetBrains Mono',monospace;
        color: var(--c);
        font-weight: 800;
    }

    .news-side-title {
        color: #F1F5F9;
        font-size: .88rem;
        line-height: 1.35;
        font-weight: 650;
    }

    .news-side-fr {
        color: #8B93A7;
        font-size: .74rem;
        line-height: 1.35;
        margin-top: 5px;
    }

    .news-feed {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .news-row {
        display: grid;
        grid-template-columns: 105px 135px 1fr 25px;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 13px;
        background: rgba(255,255,255,.028);
        border: 1px solid rgba(255,255,255,.055);
        text-decoration: none !important;
        transition: .22s;
    }

    .news-row:hover {
        transform: translateX(4px);
        background: rgba(99,102,241,.07);
        border-color: rgba(129,140,248,.3);
    }

    .news-time {
        font-family: 'JetBrains Mono',monospace;
        color: #626B80;
        font-size: .68rem;
    }

    .news-source {
        color: #8B93A7;
        font-size: .68rem;
    }

    .news-row-title {
        color: #E8ECF5;
        font-size: .82rem;
        font-weight: 550;
        line-height: 1.35;
    }

    .news-arrow {
        color: #22D3EE;
        font-weight: 800;
    }

    .news-section-header {
        display: flex;
        justify-content: space-between;
        align-items: end;
        gap: 20px;
        margin: 28px 0 14px;
    }

    .news-section-title {
        font-size: 1.3rem;
        color: #fff;
        font-weight: 750;
    }

    .news-section-sub {
        color: #687187;
        font-size: .76rem;
        margin-top: 3px;
    }

    .news-stat-grid {
        display: grid;
        grid-template-columns: repeat(4,1fr);
        gap: 10px;
        margin: 0 0 20px;
    }

    .news-stat {
        padding: 13px 15px;
        border-radius: 14px;
        background: rgba(255,255,255,.035);
        border: 1px solid rgba(255,255,255,.07);
    }

    .news-stat-label {
        color: #687187;
        text-transform: uppercase;
        font-size: .58rem;
        letter-spacing: 1.2px;
    }

    .news-stat-value {
        color: #F8FAFC;
        font-family: 'JetBrains Mono',monospace;
        font-size: 1rem;
        font-weight: 700;
        margin-top: 4px;
    }

    /* KNOWLEDGE */

    .kc {
        min-height: 180px;
        padding: 20px;
        border-radius: 18px;
        background:
            linear-gradient(
                145deg,
                rgba(255,255,255,.06),
                rgba(255,255,255,.018)
            );
        border: 1px solid rgba(255,255,255,.08);
        border-top: 2px solid var(--c,#6366F1);
        margin-bottom: 15px;
    }

    .kc h4 {
        color: #F8FAFC;
        margin: 0 0 12px;
        font-size: 1rem;
    }

    .kc .big {
        color: #818CF8;
        font-family: 'JetBrains Mono',monospace;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .kc p {
        color: #8791A5;
        font-size: .82rem;
        line-height: 1.5;
    }

    .co {
        display: inline-block;
        padding: 5px 9px;
        margin: 3px;
        border-radius: 8px;
        color: #CBD5E1;
        background: rgba(255,255,255,.045);
        border: 1px solid rgba(255,255,255,.06);
        font-size: .7rem;
    }

    .rank-row {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        padding: 11px 0;
        border-bottom: 1px solid rgba(255,255,255,.06);
        color: #CBD5E1;
        font-size: .82rem;
    }

    .rank-row:last-child {
        border-bottom: none;
    }

    .rank-row span:last-child {
        color: #687187;
        text-align: right;
    }

    /* TABLE */

    .market-card {
        padding: 18px;
        border-radius: 18px;
        background: rgba(255,255,255,.035);
        border: 1px solid rgba(255,255,255,.07);
    }

    .market-name {
        color: #F8FAFC;
        font-weight: 700;
        font-size: .95rem;
    }

    .market-ticker {
        color: #626B80;
        font-size: .67rem;
        font-family: 'JetBrains Mono',monospace;
    }

    .market-price {
        color: #E2E8F0;
        font-family: 'JetBrains Mono',monospace;
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 12px;
    }

    .up {
        color: #34D399;
    }

    .down {
        color: #FB7185;
    }

    @media(max-width:900px) {

        .news-row {
            grid-template-columns: 80px 1fr 20px;
        }

        .news-source {
            display: none;
        }

        .news-stat-grid {
            grid-template-columns: repeat(2,1fr);
        }
    }

    @media(max-width:650px) {

        .hero-title {
            font-size: 1.55rem;
        }

        .news-hero {
            padding: 22px;
        }

        .news-hero-title {
            font-size: 1.25rem;
        }

        .news-stat-grid {
            grid-template-columns: 1fr 1fr;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ================================================================
# HELPERS
# ================================================================

def clean_label(text):
    return re.sub(r"^[^\wÀ-ÿ]+", "", text).strip()


def hero(eyebrow, title, subtitle="", badge=""):
    st.markdown(
        f"""
        <div class="hero">

            <div class="hero-eyebrow">
                {html.escape(eyebrow)}
            </div>

            <div class="hero-title">
                {html.escape(title)}
            </div>

            <div class="hero-sub">
                {html.escape(subtitle)}
            </div>

            <div style="margin-top:16px">
                {badge}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


def ranks(items):
    return "".join(
        f"""
        <div class="rank-row">
            <span>{name}</span>
            <span>{description}</span>
        </div>
        """
        for name, description in items
    )


def fmt_number(value):
    if value is None:
        return "—"

    if abs(value) >= 1000:
        return f"{value:,.2f}"

    return f"{value:.2f}"


# ================================================================
# SIDEBAR
# ================================================================

st.sidebar.markdown(
    '<div class="brand">'
    '<div class="brand-logo">'
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
    'stroke="white" stroke-width="2.4" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<polyline points="3 17 9 11 13 15 21 7"/>'
    '<polyline points="15 7 21 7 21 13"/>'
    '</svg>'
    '</div>'
    '<div>'
    '<div class="brand-t">MACRO TERMINAL</div>'
    '<div class="brand-s">Global Markets</div>'
    '</div>'
    '</div>'
    f'<div class="live"><i></i>LIVE · '
    f'{datetime.now(timezone.utc).strftime("%H:%M UTC")}</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="navlab">Navigation</div>',
    unsafe_allow_html=True,
)

all_options = list(UNIVERSE.keys()) + [
    "🕐 Calendrier des Marchés",
    "📰 Actualités Macro (FR)",
    "📚 Base de Connaissances",
]

search_nav = st.sidebar.text_input(
    "Rechercher",
    placeholder="⌕  Rechercher une section...",
    label_visibility="collapsed",
    key="nav_search",
)

if search_nav.strip():

    q = search_nav.lower().strip()

    filtered_options = [
        x
        for x in all_options
        if q in clean_label(x).lower()
        or q in x.lower()
    ]

    if not filtered_options:
        filtered_options = all_options

else:
    filtered_options = all_options


current_category = st.session_state.get(
    "category",
    all_options[0],
)

if current_category not in filtered_options:
    current_category = filtered_options[0]


category = st.sidebar.radio(
    "NAVIGATION",
    filtered_options,
    index=filtered_options.index(current_category),
    format_func=clean_label,
    label_visibility="collapsed",
    key="main_navigation",
)

st.session_state["category"] = category


st.sidebar.markdown(
    '<div class="sidebar-status">'
    '<div class="sidebar-status-row">'
    '<span class="sidebar-status-title">Terminal status</span>'
    '<span class="sidebar-status-value">● ONLINE</span>'
    '</div>'
    '<div class="sidebar-status-sub">'
    'Yahoo Finance · cache 5 min<br>'
    'News feed · CNBC · traduction FR'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div style="margin-top:12px;text-align:center;font-size:.58rem;'
    'color:#41495B;letter-spacing:.5px">'
    'INFORMATION À BUT PÉDAGOGIQUE · NOT FINANCIAL ADVICE'
    '</div>',
    unsafe_allow_html=True,
)


# ================================================================
# PAGE — LEADERS & MEGA-CAPS
# ================================================================

if category == "🚀 Leaders & Mega-Caps":

    hero(
        "Global Equities",
        "Leaders & Mega-Caps",
        "Les principales capitalisations mondiales suivies par le terminal.",
        '<span class="pill">GLOBAL MARKETS</span>',
    )

    companies = list(
        UNIVERSE["🚀 Leaders & Mega-Caps"].items()
    )

    try:

        tickers = [ticker for _, ticker in companies]

        data = yf.download(
            tickers,
            period="5d",
            progress=False,
            auto_adjust=True,
            threads=True,
        )

        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"]
        else:
            close = data[["Close"]]

        cols = st.columns(3)

        for i, (name, ticker) in enumerate(companies):

            with cols[i % 3]:

                try:

                    if ticker not in close.columns:
                        raise ValueError()

                    series = close[ticker].dropna()

                    if len(series) < 2:
                        raise ValueError()

                    price = float(series.iloc[-1])
                    previous = float(series.iloc[-2])

                    change = (
                        (price / previous) - 1
                    ) * 100

                    cls = "up" if change >= 0 else "down"

                    st.markdown(
                        f"""
                        <div class="market-card"
                             style="margin-bottom:12px">

                            <div class="market-name">
                                {html.escape(name)}
                            </div>

                            <div class="market-ticker">
                                {html.escape(ticker)}
                            </div>

                            <div class="market-price">
                                {fmt_number(price)}
                            </div>

                            <div class="{cls}"
                                 style="font-family:JetBrains Mono;
                                        font-size:.75rem;
                                        margin-top:5px">
                                {change:+.2f}%
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                except Exception:

                    st.markdown(
                        f"""
                        <div class="market-card"
                             style="margin-bottom:12px">

                            <div class="market-name">
                                {html.escape(name)}
                            </div>

                            <div class="market-ticker">
                                {html.escape(ticker)}
                            </div>

                            <div class="market-price">
                                —
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    except Exception as e:

        st.warning(
            f"Impossible de récupérer les données de marché : {e}"
        )


# ================================================================
# PAGE — ACTUALITÉS MACRO
# ================================================================

elif category == "📰 Actualités Macro (FR)":

    FEED = (
        "https://search.cnbc.com/rs/search/"
        "combinedcms/view.xml?partnerId=wrss01&id=10000664"
    )

    TAGS = {

        "Banques centrales": (
            "#818CF8",
            5,
            [
                "fed",
                "federal reserve",
                "ecb",
                "boj",
                "powell",
                "lagarde",
                "rate cut",
                "rate hike",
                "interest rate",
                "central bank",
                "fomc",
                "bank of england",
            ],
        ),

        "Inflation & Emploi": (
            "#FBBF24",
            4,
            [
                "inflation",
                "cpi",
                "pce",
                "jobs",
                "payroll",
                "unemployment",
                "gdp",
                "recession",
                "layoffs",
                "wages",
            ],
        ),

        "Géopolitique": (
            "#FB7185",
            4,
            [
                "war",
                "sanction",
                "iran",
                "russia",
                "ukraine",
                "china",
                "israel",
                "tariff",
                "trade war",
                "middle east",
                "taiwan",
                "election",
                "trump",
                "conflict",
            ],
        ),

        "Énergie": (
            "#FB923C",
            3,
            [
                "oil",
                "crude",
                "natural gas",
                "opec",
                "energy",
                "brent",
            ],
        ),

        "Marchés": (
            "#22D3EE",
            2,
            [
                "stocks",
                "s&p",
                "nasdaq",
                "dow",
                "yields",
                "treasury",
                "dollar",
                "bond",
                "bitcoin",
                "earnings",
                "equity",
                "market",
            ],
        ),
    }


    @st.cache_data(ttl=600, show_spinner=False)
    def fetch_news():

        response = requests.get(
            FEED,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        output = []

        for entry in feed.entries[:40]:

            ts = (
                time.mktime(entry.published_parsed)
                if getattr(
                    entry,
                    "published_parsed",
                    None,
                )
                else 0
            )

            summary = re.sub(
                r"<[^>]+>",
                "",
                getattr(
                    entry,
                    "summary",
                    "",
                ),
            ).strip()

            image = ""

            if getattr(entry, "media_content", None):

                try:
                    image = entry.media_content[0].get(
                        "url",
                        "",
                    )
                except Exception:
                    pass

            output.append(
                {
                    "title": entry.title,
                    "link": entry.link,
                    "ts": ts,
                    "summary": summary,
                    "image": image,
                }
            )

        return output


    @st.cache_data(ttl=3600, show_spinner=False)
    def translate_news(text):

        if not text:
            return ""

        if GoogleTranslator is None:
            return text

        try:

            return GoogleTranslator(
                source="auto",
                target="fr",
            ).translate(text)

        except Exception:

            return text


    def score_news(news_item):

        text = (
            news_item["title"]
            + " "
            + news_item["summary"]
        ).lower()

        total = 0
        best = "Marchés"
        best_weight = 0

        for tag, (_, weight, keywords) in TAGS.items():

            hits = sum(
                1
                for keyword in keywords
                if re.search(
                    r"\b" + re.escape(keyword),
                    text,
                )
            )

            if hits:

                contribution = (
                    weight
                    * min(hits, 3)
                )

                total += contribution

                if contribution > best_weight:

                    best = tag
                    best_weight = contribution

        return total, best


    def impact_level(score):

        if score >= 10:
            return 5

        if score >= 7:
            return 4

        if score >= 5:
            return 3

        if score >= 3:
            return 2

        return 1


    def fmt_news_time(ts):

        if not ts:
            return "—"

        dt = datetime.fromtimestamp(
            ts,
            tz=timezone.utc,
        )

        return dt.astimezone(PARIS).strftime(
            "%d %b · %H:%M"
        )


    def relative_time(ts):

        if not ts:
            return ""

        delta = (
            datetime.now(timezone.utc)
            - datetime.fromtimestamp(
                ts,
                tz=timezone.utc,
            )
        )

        minutes = int(
            delta.total_seconds() / 60
        )

        if minutes < 1:
            return "à l'instant"

        if minutes < 60:
            return f"il y a {minutes} min"

        hours = minutes // 60

        if hours < 24:
            return f"il y a {hours} h"

        return f"il y a {hours // 24} j"


    hero(
        "Intelligence de marché",
        "Actualités Macro",
        "Les événements susceptibles de faire bouger "
        "les taux, devises, actions, matières premières et marchés.",
        '<span class="pill">CNBC · LIVE FEED</span>',
    )


    try:

        with st.spinner("Analyse du flux macro..."):

            raw_news = fetch_news()

            news = []

            for item in raw_news:

                current = dict(item)

                current["score"], current["tag"] = (
                    score_news(current)
                )

                current["impact"] = impact_level(
                    current["score"]
                )

                news.append(current)

            news.sort(
                key=lambda x: (
                    x["score"],
                    x["ts"],
                ),
                reverse=True,
            )

            if not news:

                st.warning(
                    "Aucune actualité disponible."
                )

                st.stop()

            top5 = news[:5]

            top_links = {
                item["link"]
                for item in top5
            }

            flux = [
                item
                for item in news
                if item["link"]
                not in top_links
            ][:20]

            for item in top5:

                item["fr"] = translate_news(
                    item["title"]
                )

                summary = item["summary"][:320]

                item["fr_sum"] = (
                    translate_news(summary)
                    if summary
                    else ""
                )


        # ============================================================
        # MARKET PULSE
        # ============================================================

        pulse_items = []

        pulse_assets = [
            ("S&P 500", "^GSPC"),
            ("Nasdaq", "^NDX"),
            ("CAC 40", "^FCHI"),
            ("EUR/USD", "EURUSD=X"),
            ("Brent", "BZ=F"),
            ("Gold", "GC=F"),
            ("VIX", "^VIX"),
        ]

        try:

            pulse_df = yf.download(
                [x[1] for x in pulse_assets],
                period="5d",
                progress=False,
                threads=True,
                auto_adjust=True,
            )

            if isinstance(
                pulse_df.columns,
                pd.MultiIndex,
            ):
                pulse_df = pulse_df["Close"]

            for label, ticker in pulse_assets:

                if ticker not in pulse_df.columns:
                    continue

                series = pulse_df[ticker].dropna()

                if len(series) < 2:
                    continue

                current = float(
                    series.iloc[-1]
                )

                previous = float(
                    series.iloc[-2]
                )

                pct = (
                    current / previous - 1
                ) * 100

                inverse = ticker == "^VIX"

                if inverse:

                    cls = (
                        "npulse-up"
                        if pct < 0
                        else "npulse-down"
                    )

                else:

                    cls = (
                        "npulse-up"
                        if pct >= 0
                        else "npulse-down"
                    )

                if ticker == "EURUSD=X":
                    value = f"{current:.4f}"

                elif ticker == "^VIX":
                    value = f"{current:.1f}"

                else:
                    value = f"{current:,.2f}"

                pulse_items.append(
                    f"""
                    <div class="npulse">

                        <div class="npulse-label">
                            {label}
                        </div>

                        <div class="npulse-value {cls}">
                            {value}

                            <span style="font-size:.65rem">
                                {pct:+.2f}%
                            </span>
                        </div>

                    </div>
                    """
                )

        except Exception:

            pulse_items = []


        if pulse_items:

            st.markdown(
                '<div class="news-pulse">'
                + "".join(pulse_items)
                + "</div>",
                unsafe_allow_html=True,
            )


        # ============================================================
        # STATISTICS
        # ============================================================

        categories_count = {}

        for item in news:

            categories_count[item["tag"]] = (
                categories_count.get(
                    item["tag"],
                    0,
                )
                + 1
            )

        dominant_category = max(
            categories_count,
            key=categories_count.get,
        )

        avg_impact = (
            sum(
                item["impact"]
                for item in news
            )
            / len(news)
        )

        st.markdown(
            f"""
            <div class="news-stat-grid">

                <div class="news-stat">

                    <div class="news-stat-label">
                        Articles analysés
                    </div>

                    <div class="news-stat-value">
                        {len(news)}
                    </div>

                </div>


                <div class="news-stat">

                    <div class="news-stat-label">
                        Sujet dominant
                    </div>

                    <div class="news-stat-value">
                        {html.escape(dominant_category)}
                    </div>

                </div>


                <div class="news-stat">

                    <div class="news-stat-label">
                        Impact moyen
                    </div>

                    <div class="news-stat-value">
                        {avg_impact:.1f}/5
                    </div>

                </div>


                <div class="news-stat">

                    <div class="news-stat-label">
                        Dernière mise à jour
                    </div>

                    <div class="news-stat-value">
                        {datetime.now(PARIS).strftime("%H:%M")}
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


        # ============================================================
        # TOP STORIES
        # ============================================================

        st.markdown(
            """
            <div class="news-section-header">

                <div>

                    <div class="news-section-title">
                        Intelligence du jour
                    </div>

                    <div class="news-section-sub">
                        Classement automatique selon pertinence macro,
                        géopolitique et proximité avec les marchés.
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


        headline = top5[0]

        headline_color = TAGS[
            headline["tag"]
        ][0]

        dots = (
            "●" * headline["impact"]
            + "○" * (
                5 - headline["impact"]
            )
        )

        left, right = st.columns(
            [3, 1.65],
            gap="medium",
        )


        with left:

            st.markdown(
                f"""
                <a
                    class="news-hero"
                    style="--c:{headline_color}"
                    href="{html.escape(headline["link"])}"
                    target="_blank"
                >

                    <div class="news-kicker">

                        <span class="news-rank">
                            01
                        </span>

                        <span class="news-category">
                            {html.escape(headline["tag"])}
                        </span>

                    </div>


                    <div class="news-hero-title">
                        {html.escape(headline["title"])}
                    </div>


                    <div class="news-hero-fr">
                        🇫🇷 {html.escape(headline["fr"])}
                    </div>


                    <div class="news-meta">

                        <span>
                            {fmt_news_time(headline["ts"])}
                        </span>

                        <span>·</span>

                        <span>
                            {relative_time(headline["ts"])}
                        </span>

                        <span>·</span>

                        <span>
                            Impact
                            <b class="impact-dots">
                                {dots}
                            </b>
                        </span>

                        <span>·</span>

                        <span>
                            CNBC ↗
                        </span>

                    </div>

                </a>
                """,
                unsafe_allow_html=True,
            )


        with right:

            cards = []

            for rank, item in enumerate(
                top5[1:],
                2,
            ):

                color = TAGS[
                    item["tag"]
                ][0]

                cards.append(
                    f"""
                    <a
                        class="news-side-card"
                        style="--c:{color}"
                        href="{html.escape(item["link"])}"
                        target="_blank"
                    >

                        <div class="news-side-top">

                            <span class="news-side-rank">
                                {rank:02d}
                            </span>

                            <span
                                class="news-category"
                                style="font-size:.53rem"
                            >
                                {html.escape(item["tag"])}
                            </span>

                        </div>


                        <div class="news-side-title">
                            {html.escape(item["title"])}
                        </div>


                        <div class="news-side-fr">
                            {html.escape(item["fr"])}
                        </div>

                    </a>
                    """
                )

            st.markdown(
                '<div class="news-side">'
                + "".join(cards)
                + "</div>",
                unsafe_allow_html=True,
            )


        # ============================================================
        # NEWS FEED
        # ============================================================

        st.markdown(
            """
            <div style="height:18px"></div>

            <div class="news-section-header">

                <div>

                    <div class="news-section-title">
                        Flux de marché
                    </div>

                    <div class="news-section-sub">
                        Publications récentes · titres originaux
                        pour conserver la vitesse de lecture.
                    </div>

                </div>

                <a
                    class="pill"
                    href="https://www.tradingview.com/news/"
                    target="_blank"
                    style="text-decoration:none"
                >
                    TERMINAL NEWS ↗
                </a>

            </div>
            """,
            unsafe_allow_html=True,
        )


        opts = ["Tous"] + list(TAGS)

        if hasattr(st, "pills"):

            selected = st.pills(
                "Filtre",
                opts,
                default="Tous",
                label_visibility="collapsed",
            )

        else:

            selected = st.radio(
                "Filtre",
                opts,
                horizontal=True,
                label_visibility="collapsed",
            )


        filtered_flux = flux

        if selected and selected != "Tous":

            filtered_flux = [
                item
                for item in flux
                if item["tag"] == selected
            ]


        rows = []

        for item in filtered_flux:

            rows.append(
                f"""
                <a
                    class="news-row"
                    href="{html.escape(item["link"])}"
                    target="_blank"
                >

                    <div class="news-time">
                        {fmt_news_time(item["ts"])}
                    </div>

                    <div class="news-source">
                        CNBC
                    </div>

                    <div class="news-row-title">
                        {html.escape(item["title"])}
                    </div>

                    <div class="news-arrow">
                        ↗
                    </div>

                </a>
                """
            )


        if rows:

            st.markdown(
                '<div class="news-feed">'
                + "".join(rows)
                + "</div>",
                unsafe_allow_html=True,
            )

        else:

            st.info(
                "Aucune actualité ne correspond à ce filtre."
            )


    except Exception as error:

        st.error(
            f"Impossible de charger les actualités : {error}"
        )


# ================================================================
# PAGE — BASE DE CONNAISSANCES
# ================================================================

elif category == "📚 Base de Connaissances":

    hero(
        "Knowledge Base",
        "Base de Connaissances",
        "Repères rapides sur les principaux blocs économiques, "
        "marchés et entreprises internationales.",
        '<span class="pill">MACRO · MARKETS · EQUITIES</span>',
    )

    t1, t2, t3, t4, t5, t6, t7 = st.tabs(
        [
            "🌍 Macro",
            "🏦 Banques centrales",
            "📈 Marchés",
            "🛢️ Matières premières",
            "💱 FX",
            "🌐 Géopolitique",
            "🏢 Leaders étrangers",
        ]
    )


    # ------------------------------------------------------------
    # MACRO
    # ------------------------------------------------------------

    with t1:

        c1, c2, c3 = st.columns(3)

        with c1:

            st.markdown(
                """
                <div class="kc" style="--c:#818CF8">

                    <h4>PIB</h4>

                    <div class="big">
                        Production économique
                    </div>

                    <p>
                        Le produit intérieur brut mesure la valeur
                        des biens et services produits dans une économie.
                    </p>

                </div>
                """,
                unsafe_allow_html=True,
            )


        with c2:

            st.markdown(
                """
                <div class="kc" style="--c:#FBBF24">

                    <h4>Inflation</h4>

                    <div class="big">
                        Prix à la consommation
                    </div>

                    <p>
                        Une inflation élevée influence les banques
                        centrales, les taux et les valorisations d'actifs.
                    </p>

                </div>
                """,
                unsafe_allow_html=True,
            )


        with c3:

            st.markdown(
                """
                <div class="kc" style="--c:#22D3EE">

                    <h4>Chômage</h4>

                    <div class="big">
                        Marché du travail
                    </div>

                    <p>
                        Les données d'emploi influencent directement
                        les anticipations de politique monétaire.
                    </p>

                </div>
                """,
                unsafe_allow_html=True,
            )


    # ------------------------------------------------------------
    # CENTRAL BANKS
    # ------------------------------------------------------------

    with t2:

        c1, c2 = st.columns(2)

        with c1:

            st.markdown(
                '<div class="kc" style="--c:#818CF8">'
                '<h4>Federal Reserve</h4>'
                '<div class="big">États-Unis</div>'
                '<p>'
                'La Fed pilote notamment les Fed Funds et cherche '
                'à maintenir la stabilité des prix tout en soutenant '
                'un marché du travail équilibré.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        with c2:

            st.markdown(
                '<div class="kc" style="--c:#22D3EE">'
                '<h4>ECB</h4>'
                '<div class="big">Zone euro</div>'
                '<p>'
                'La Banque centrale européenne définit la politique '
                'monétaire de la zone euro et agit principalement '
                'via ses taux directeurs.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )


    # ------------------------------------------------------------
    # MARKETS
    # ------------------------------------------------------------

    with t3:

        c1, c2, c3 = st.columns(3)

        with c1:

            st.markdown(
                '<div class="kc">'
                '<h4>S&P 500</h4>'
                '<div class="big">Large Caps US</div>'
                '<p>'
                'Indice représentant 500 grandes entreprises '
                'cotées aux États-Unis.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        with c2:

            st.markdown(
                '<div class="kc" style="--c:#22D3EE">'
                '<h4>Nasdaq</h4>'
                '<div class="big">Growth · Tech</div>'
                '<p>'
                'Indice fortement exposé aux entreprises '
                'technologiques et de croissance.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        with c3:

            st.markdown(
                '<div class="kc" style="--c:#FB7185">'
                '<h4>CAC 40</h4>'
                '<div class="big">France</div>'
                '<p>'
                'Principal indice actions français.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )


    # ------------------------------------------------------------
    # COMMODITIES
    # ------------------------------------------------------------

    with t4:

        c1, c2, c3 = st.columns(3)

        with c1:

            st.markdown(
                '<div class="kc" style="--c:#FB923C">'
                '<h4>Brent</h4>'
                '<div class="big">Pétrole</div>'
                '<p>'
                'Référence internationale majeure pour le prix du brut.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        with c2:

            st.markdown(
                '<div class="kc" style="--c:#FBBF24">'
                '<h4>Gold</h4>'
                '<div class="big">Valeur refuge</div>'
                '<p>'
                'L’or est souvent suivi lors des épisodes de stress '
                'de marché et d’incertitude.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        with c3:

            st.markdown(
                '<div class="kc" style="--c:#22D3EE">'
                '<h4>OPEP+</h4>'
                '<div class="big">Offre pétrolière</div>'
                '<p>'
                'Organisation et partenaires représentant une part '
                'majeure de la production mondiale de pétrole.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )


    # ------------------------------------------------------------
    # FX
    # ------------------------------------------------------------

    with t5:

        c1, c2 = st.columns(2)

        with c1:

            st.markdown(
                '<div class="kc" style="--c:#22D3EE">'
                '<h4>EUR/USD</h4>'
                '<div class="big">Euro · Dollar</div>'
                '<p>'
                'La paire de devises la plus négociée au monde. '
                'Elle réagit notamment aux différentiels de taux '
                'et aux anticipations de politique monétaire.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        with c2:

            st.markdown(
                '<div class="kc" style="--c:#818CF8">'
                '<h4>Dollar</h4>'
                '<div class="big">Devise dominante</div>'
                '<p>'
                'Le dollar joue un rôle central dans les marchés '
                'mondiaux, notamment pour les matières premières '
                'et les flux financiers internationaux.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )


    # ------------------------------------------------------------
    # GEOPOLITICS
    # ------------------------------------------------------------

    with t6:

        c1, c2, c3 = st.columns(3)

        with c1:

            st.markdown(
                '<div class="kc" style="--c:#FB7185">'
                '<h4>BRICS+</h4>'
                '<div class="big">Bloc élargi</div>'
                + "".join(
                    f'<span class="co">{x}</span>'
                    for x in [
                        "Brésil",
                        "Russie",
                        "Inde",
                        "Chine",
                        "Afrique du Sud",
                    ]
                )
                + """
                <p style="margin-top:10px">
                    Rejoints notamment par plusieurs économies
                    émergentes au sein du format élargi.
                </p>

                </div>
                """,
                unsafe_allow_html=True,
            )


        with c2:

            st.markdown(
                '<div class="kc" style="--c:#FB923C">'
                '<h4>OPEP+</h4>'
                '<div class="big">Bloc pétrolier</div>'
                '<p>'
                'Mené notamment par l’Arabie Saoudite et la Russie, '
                'avec une influence importante sur l’offre mondiale '
                'de brut.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )


        with c3:

            st.markdown(
                '<div class="kc" style="--c:#818CF8">'
                '<h4>États-Unis · Chine</h4>'
                '<div class="big">Rivalité stratégique</div>'
                '<p>'
                'Commerce, semi-conducteurs, technologies et chaînes '
                'd’approvisionnement constituent des axes majeurs.'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )


    # ------------------------------------------------------------
    # FOREIGN LEADERS
    # ------------------------------------------------------------

    with t7:

        c1, c2 = st.columns(2)

        with c1:

            st.markdown(
                '<div class="kc">'
                '<h4>Inde · Nifty 50</h4>'
                + ranks(
                    [
                        (
                            "<b>Reliance Industries</b>",
                            "Conglomérat · M. Ambani",
                        ),
                        (
                            "<b>TCS</b>",
                            "Services IT",
                        ),
                        (
                            "<b>HDFC Bank</b>",
                            "Banque",
                        ),
                    ]
                )
                + '</div>',
                unsafe_allow_html=True,
            )


        with c2:

            st.markdown(
                '<div class="kc">'
                '<h4>Europe · Stoxx 600</h4>'
                + ranks(
                    [
                        (
                            "<b>Novo Nordisk</b>",
                            "Santé · diabète",
                        ),
                        (
                            "<b>LVMH</b>",
                            "Luxe",
                        ),
                        (
                            "<b>ASML</b>",
                            "Semi-conducteurs · EUV",
                        ),
                    ]
                )
                + '</div>',
                unsafe_allow_html=True,
            )


# ================================================================
# PAGE — CALENDRIER DES MARCHÉS
# ================================================================

elif category == "🕐 Calendrier des Marchés":

    hero(
        "Market Calendar",
        "Calendrier des Marchés",
        "Les principaux indicateurs à surveiller pour comprendre "
        "les mouvements macro et financiers.",
        '<span class="pill">MACRO EVENTS</span>',
    )

    events = [
        ("🇺🇸", "Federal Reserve", "Décision de taux", "Très élevé"),
        ("🇺🇸", "CPI", "Inflation américaine", "Très élevé"),
        ("🇺🇸", "Nonfarm Payrolls", "Emploi américain", "Très élevé"),
        ("🇪🇺", "ECB", "Décision de taux", "Très élevé"),
        ("🇪🇺", "Eurostat", "Inflation zone euro", "Élevé"),
        ("🇬🇧", "Bank of England", "Décision de taux", "Élevé"),
        ("🇯🇵", "Bank of Japan", "Décision de taux", "Élevé"),
    ]

    st.markdown(
        """
        <div class="news-stat-grid">

            <div class="news-stat">
                <div class="news-stat-label">
                    Événements
                </div>
                <div class="news-stat-value">
                    7
                </div>
            </div>

            <div class="news-stat">
                <div class="news-stat-label">
                    Focus
                </div>
                <div class="news-stat-value">
                    Taux
                </div>
            </div>

            <div class="news-stat">
                <div class="news-stat-label">
                    Focus 2
                </div>
                <div class="news-stat-value">
                    Inflation
                </div>
            </div>

            <div class="news-stat">
                <div class="news-stat-label">
                    Focus 3
                </div>
                <div class="news-stat-value">
                    Emploi
                </div>
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    for flag, name, event, impact in events:

        st.markdown(
            f"""
            <div class="market-card"
                 style="margin-bottom:9px">

                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    gap:20px;
                ">

                    <div>
                        <span style="font-size:1.2rem">
                            {flag}
                        </span>

                        <span style="
                            color:#F8FAFC;
                            font-weight:700;
                            margin-left:9px;
                        ">
                            {html.escape(name)}
                        </span>

                        <span style="
                            color:#687187;
                            margin-left:12px;
                            font-size:.78rem;
                        ">
                            {html.escape(event)}
                        </span>
                    </div>

                    <span class="pill">
                        {html.escape(impact)}
                    </span>

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ================================================================
# FALLBACK
# ================================================================

else:

    hero(
        "Global Markets",
        category,
        "Terminal de suivi des marchés financiers.",
        '<span class="pill">LIVE MARKET DATA</span>',
    )

    st.info(
        "Sélectionnez une section dans la barre latérale."
    )
