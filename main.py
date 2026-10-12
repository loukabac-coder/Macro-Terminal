# -*- coding: utf-8 -*-
"""PRO Macro Terminal — terminal de marché en ligne (Streamlit).

Architecture
------------
Toute donnée externe (Yahoo Finance, FRED, BCE, Eurostat, flux d'actualités…) passe par un
cache « stale-while-revalidate » (classe SWR) :
  • l'interface lit toujours la dernière valeur connue et n'attend jamais plus de quelques secondes ;
  • un seul rafraîchissement à la fois par source, avec une concurrence bornée (pas d'emballement) ;
  • une source en panne ne bloque ni ne fait tomber le site : on garde la dernière valeur valide.
Chaque page est protégée : une erreur affiche un encadré propre au lieu de tout arrêter.
"""
import calendar
import functools
import html
import inspect
import io
import json
import logging
import platform
import re
import sys
import threading
import time
import traceback
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import requests
import streamlit as st
from plotly.subplots import make_subplots

try:  # si yfinance est indisponible, le site bascule sur l'API Yahoo directe
    import yfinance as yf
except Exception:
    yf = None
try:
    import feedparser
except Exception:
    feedparser = None
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None
try:
    import streamlit.components.v1 as components
except Exception:
    components = None

log = logging.getLogger("macro-terminal")

st.set_page_config(page_title="PRO Macro Terminal", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

pio.templates["mt"] = go.layout.Template(layout=dict(
    font=dict(family="IBM Plex Sans, sans-serif", color="#E9E6DF"),
    colorway=["#E3A33B", "#6C9BC9", "#46B37D", "#E5574C", "#A9B4C2"],
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor="#23262C", zerolinecolor="#23262C", linecolor="#343841"),
    yaxis=dict(gridcolor="#23262C", zerolinecolor="#23262C", linecolor="#343841"),
    hoverlabel=dict(bgcolor="#111317", bordercolor="#343841", font=dict(family="IBM Plex Mono, monospace", color="#E9E6DF"))))
pio.templates.default = "mt"

PARIS = ZoneInfo("Europe/Paris")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# =====================================================================
#  UNIVERS D'INSTRUMENTS
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
ALL_ASSETS = {name: t for items in UNIVERSE.values() for name, t in items.items()}
LABEL_OF = {t: n for n, t in ALL_ASSETS.items()}

YIELDS = {"^IRX", "^FVX", "^TNX", "^TYX", "2YY=F"}
INVERSE = {"^VIX", "^MOVE"}  # une hausse est une mauvaise nouvelle
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


def chg_info(ticker, sr):
    """Variation sur la dernière séance : texte, sens, et couleur (VIX/MOVE inversés)."""
    curr, prev = float(sr.iloc[-1]), float(sr.iloc[-2])
    is_y = ticker in YIELDS or ticker.startswith("ext:")
    d = curr - prev
    pct = (curr / prev - 1) * 100 if prev else 0.0
    txt = sgn(d * 100, 1, " pb") if is_y else sgn(pct, 2, " %")
    good = (d < 0) if ticker in INVERSE else (d >= 0)
    return dict(curr=curr, prev=prev, d=d, pct=pct, txt=txt, up=d >= 0, good=good, cls="up" if good else "dn", is_y=is_y)


# =====================================================================
#  CACHE « STALE-WHILE-REVALIDATE » (état partagé entre toutes les sessions)
# =====================================================================
class SWR:
    """Sert la dernière valeur connue ; rafraîchit en tâche de fond, un seul appel à la fois par clé."""

    def __init__(self, workers=6, max_keys=240):
        self._lock = threading.Lock()
        self._d = {}
        self._max = max_keys
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="mt-data")

    def _evict(self):
        idle = [(e["ts"], k) for k, e in self._d.items() if e["fut"] is None]
        for _, k in sorted(idle, key=lambda x: x[0])[: max(1, len(idle) // 4)]:
            del self._d[k]

    def _run(self, key, fn, args):
        try:
            value = fn(*args)
            with self._lock:
                e = self._d[key]
                e.update(v=value, ts=time.time(), err=None, n=e["n"] + 1)
        except Exception as ex:
            with self._lock:
                e = self._d[key]
                e["err"] = (type(ex).__name__ + ": " + str(ex))[:160]
                e["fail"] = time.time()
            log.warning("source %s : %s", e["label"], ex)
        finally:
            with self._lock:
                self._d[key]["fut"] = None

    def get(self, key, fn, ttl, args=(), wait_first=20.0, wait_stale=2.5, retry=20.0, label=None):
        """Retourne (valeur, horodatage, erreur). Ne lève jamais d'exception."""
        now = time.time()
        with self._lock:
            e = self._d.get(key)
            if e is None:
                if len(self._d) >= self._max:
                    self._evict()
                e = self._d[key] = dict(v=None, ts=0.0, err=None, fail=0.0, fut=None, n=0, label=label or str(key)[:60])
            if (now - e["ts"]) >= ttl and e["fut"] is None and (now - e["fail"]) >= retry:
                e["fut"] = self._pool.submit(self._run, key, fn, args)
            fut, first = e["fut"], e["ts"] == 0.0
        if fut is not None:
            try:
                fut.result(timeout=wait_first if first else wait_stale)
            except Exception:
                pass
        with self._lock:
            e = self._d[key]
            return e["v"], e["ts"], e["err"]

    def stats(self):
        with self._lock:
            return [(e["label"], e["ts"], e["err"], e["n"], e["fut"] is not None) for e in self._d.values()]


class Hub:
    def __init__(self):
        self.swr = SWR()
        self.last = {}   # dernière série valide par ticker (évite les trous si Yahoo refuse un ticker ponctuellement)
        self.dead = {}   # ticker -> instant du dernier échec de l'API directe
        self.t0 = time.time()


@st.cache_resource(show_spinner=False)
def get_hub():
    return Hub()


HUB = get_hub()


def sget(key, fn, ttl, **kw):
    """Valeur (ou None) + horodatage, via le cache partagé."""
    kw.setdefault("label", key if isinstance(key, str) else str(key[0]))
    v, ts, _ = HUB.swr.get(key, fn, ttl, **kw)
    return v, ts


# =====================================================================
#  COTATIONS (Yahoo Finance : yfinance, avec secours par l'API graphique directe)
# =====================================================================
YF_LOCK = threading.Lock()  # yfinance partage de l'état interne : un téléchargement à la fois


def _naive(idx):
    idx = pd.DatetimeIndex(pd.to_datetime(idx))
    return idx.tz_convert(None) if idx.tz is not None else idx


def _yf_download(tickers, period, interval="1d"):
    if yf is None:
        raise RuntimeError("yfinance indisponible")
    kw = dict(period=period, interval=interval, progress=False, threads=True, auto_adjust=True)
    with YF_LOCK:
        try:
            return yf.download(list(tickers), timeout=15, **kw)
        except TypeError:
            return yf.download(list(tickers), **kw)


def _closes(raw, chunk):
    out = {}
    if raw is None or len(raw) == 0:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" not in raw.columns.get_level_values(0):
            return out
        c = raw["Close"]
    elif "Close" in raw.columns:
        c = raw[["Close"]].rename(columns={"Close": chunk[0]})
    else:
        return out
    if isinstance(c, pd.Series):
        c = c.to_frame(chunk[0])
    for t in c.columns:
        sr = pd.to_numeric(c[t], errors="coerce").dropna()
        if len(sr) >= 2:
            sr.index = _naive(sr.index)
            sr = sr[~sr.index.duplicated(keep="last")].astype("float64")
            out[str(t)] = sr
    return out


def _chart_df(t, rng="3mo", interval="1d"):
    """API graphique Yahoo en direct (indépendante de yfinance) : OHLCV."""
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(t)}",
                     params={"range": rng, "interval": interval}, headers=UA, timeout=8)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    idx = pd.to_datetime(res["timestamp"], unit="s")
    df = pd.DataFrame({"Open": q.get("open"), "High": q.get("high"), "Low": q.get("low"),
                       "Close": q.get("close"), "Volume": q.get("volume")}, index=idx).dropna(subset=["Close"])
    daily = interval in ("1d", "1wk", "1mo")
    if daily:
        df.index = df.index.normalize()
    else:
        df.index = pd.DatetimeIndex(df.index).tz_localize("UTC").tz_convert(PARIS).tz_localize(None)
    df = df[~df.index.duplicated(keep="last")].astype("float64")
    m = res.get("meta", {})
    if daily and interval == "1d" and m.get("regularMarketPrice") and m.get("regularMarketTime"):
        d_ = pd.to_datetime(m["regularMarketTime"], unit="s").normalize()
        if len(df) == 0 or d_ >= df.index[-1]:
            df.loc[d_, "Close"] = float(m["regularMarketPrice"])
            df = df.sort_index()
    if len(df) < 2:
        raise RuntimeError("série trop courte")
    return df


def _safe_chart(t, deadline):
    if time.time() > deadline:
        return None
    try:
        return _chart_df(t)["Close"].astype("float64")
    except Exception:
        return None


def fetch_prices(tickers, hub):
    """3 mois de clôtures quotidiennes (la dernière valeur est la cotation du jour)."""
    tickers = list(dict.fromkeys(tickers))
    got = {}
    for i in range(0, len(tickers), 25):  # par lots : contourne les blocages IP en production
        chunk = tickers[i:i + 25]
        try:
            got.update(_closes(_yf_download(chunk, "3mo"), chunk))
        except Exception as ex:
            log.warning("yfinance lot %s… : %s", chunk[0], ex)
    now = time.time()
    miss = [t for t in tickers if t not in got and now - hub.dead.get(t, 0) > 1800]
    if miss:
        deadline = now + 30
        with ThreadPoolExecutor(4) as ex:
            for t, sr in zip(miss, ex.map(lambda x: _safe_chart(x, deadline), miss)):
                if sr is not None and len(sr) >= 2:
                    got[t] = sr
                else:
                    hub.dead[t] = time.time()
    for t in tickers:  # trous éventuels : dernière série valide
        if t in got:
            hub.last[t] = got[t]
        elif t in hub.last:
            got[t] = hub.last[t]
    if not got:
        raise RuntimeError("aucune donnée de marché reçue")
    return got


def px(tickers, ttl=25, wait_first=25.0):
    """Séries de clôture pour des tickers : (dict, horodatage, erreur). Jamais bloquant plus de wait_first s."""
    tk = tuple(dict.fromkeys(tickers))
    v, ts, err = HUB.swr.get(("px", tk), fetch_prices, ttl, args=(tk, HUB), wait_first=wait_first,
                             label="Cotations (%d instruments)" % len(tk))
    return (v or {}), ts, err


def fetch_ohlc(ticker, period, interval):
    try:
        df = _yf_download([ticker], period, interval)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Close"])
        if len(df) < 3:
            raise ValueError("série trop courte")
        idx = pd.DatetimeIndex(df.index)
        if idx.tz is not None:
            idx = idx.tz_convert(PARIS).tz_localize(None) if interval not in ("1d", "1wk", "1mo") else idx.tz_localize(None)
        df.index = idx
        return df.astype({c: "float64" for c in df.columns if c in ("Open", "High", "Low", "Close", "Volume")})
    except Exception as ex:
        log.info("ohlc %s via API directe (%s)", ticker, ex)
        return _chart_df(ticker, period, interval)


def fetch_hist_close(tickers, period, interval):
    tickers = list(tickers)
    got = {}
    try:
        got = _closes(_yf_download(tickers, period, interval), tickers)
    except Exception as ex:
        log.info("historique lot : %s", ex)
    for t in tickers:
        if t not in got:
            try:
                got[t] = _chart_df(t, period, interval)["Close"].astype("float64")
            except Exception:
                pass
    if not got:
        raise RuntimeError("historique indisponible")
    return pd.DataFrame(got)


# =====================================================================
#  SÉRIES OFFICIELLES (FRED, BCE, BoE, BRI, Eurostat) ET AUTRES SOURCES OUVERTES
# =====================================================================
def _get(url, accept=None):
    h = dict(UA)
    if accept:
        h["Accept"] = accept
    r = requests.get(url, headers=h, timeout=8)
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


def fetch_cb():
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
        raise RuntimeError("aucune source de taux directeurs disponible")
    return out


def fetch_macro():
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


def fetch_ext_rates():  # séries officielles pour ce que Yahoo ne fournit pas
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


FRED_CURVE = {"1M": "DGS1MO", "3M": "DGS3MO", "6M": "DGS6MO", "1A": "DGS1", "2A": "DGS2", "3A": "DGS3",
              "5A": "DGS5", "7A": "DGS7", "10A": "DGS10", "20A": "DGS20", "30A": "DGS30"}


def fetch_us_curve():
    """Courbe des taux du Trésor américain (FRED, séries quotidiennes), historique ~2 ans."""
    ids = ",".join(FRED_CURVE.values())
    start = (date.today() - timedelta(days=800)).isoformat()
    d = pd.read_csv(io.StringIO(_get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={ids}&cosd={start}")))
    c0 = d.columns[0]
    d[c0] = pd.to_datetime(d[c0], errors="coerce")
    d = d.dropna(subset=[c0]).set_index(c0).apply(pd.to_numeric, errors="coerce").sort_index()
    d = d[[c for c in FRED_CURVE.values() if c in d.columns]]
    if d.dropna(how="all").empty:
        raise RuntimeError("courbe US vide")
    return d


EUR_CURVE = {"3M": "SR_3M", "1A": "SR_1Y", "2A": "SR_2Y", "5A": "SR_5Y", "10A": "SR_10Y", "30A": "SR_30Y"}


def fetch_eur_curve():
    """Courbe zéro-coupon de la zone euro (BCE, émetteurs notés AAA)."""
    start = (date.today() - timedelta(days=420)).isoformat()
    codes = "+".join(EUR_CURVE.values())
    d = pd.read_csv(io.StringIO(_get(f"https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.{codes}?startPeriod={start}&format=csvdata")))
    keycol = "KEY" if "KEY" in d.columns else "DATA_TYPE_FM"
    d["mat"] = d[keycol].astype(str).str.split(".").str[-1]
    d["dt"] = pd.to_datetime(d["TIME_PERIOD"], errors="coerce")
    d["v"] = pd.to_numeric(d["OBS_VALUE"], errors="coerce")
    pv = d.dropna(subset=["dt", "v"]).pivot_table(index="dt", columns="mat", values="v", aggfunc="last").sort_index()
    pv = pv[[c for c in EUR_CURVE.values() if c in pv.columns]]
    if pv.empty:
        raise RuntimeError("courbe euro vide")
    return pv


def fetch_crypto():
    j = requests.get("https://api.coingecko.com/api/v3/global", headers=UA, timeout=8).json()["data"]
    return {"cap": j["total_market_cap"]["usd"] / 1e9, "btc": j["market_cap_percentage"]["btc"]}


def fetch_gdp():
    names = {"USA": "États-Unis", "CHN": "Chine", "DEU": "Allemagne", "JPN": "Japon", "IND": "Inde", "GBR": "Royaume-Uni", "FRA": "France", "ITA": "Italie", "BRA": "Brésil", "CAN": "Canada"}
    j = requests.get("https://api.worldbank.org/v2/country/" + ";".join(names) + "/indicator/NY.GDP.MKTP.CD", headers=UA, timeout=10,
                     params={"format": "json", "mrnev": 1, "per_page": 30}).json()[1]
    out = {names[r["countryiso3code"]]: (r["value"] / 1e9, r["date"]) for r in j if r.get("value") and r.get("countryiso3code") in names}
    if len(out) < 8:
        raise RuntimeError("PIB incomplet")
    return out


CAP_LIST = {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Alphabet": "GOOGL", "Amazon": "AMZN", "Meta": "META", "Broadcom": "AVGO", "Tesla": "TSLA",
            "Berkshire Hathaway": "BRK-B", "TSMC": "TSM", "Eli Lilly": "LLY", "JPMorgan": "JPM", "Walmart": "WMT", "Visa": "V", "Oracle": "ORCL",
            "Saudi Aramco": "2222.SR", "Novo Nordisk": "NVO", "ASML": "ASML", "SAP": "SAP", "LVMH": "MC.PA", "Hermès": "RMS.PA", "TotalEnergies": "TTE.PA",
            "Sanofi": "SAN.PA", "L'Oréal": "OR.PA", "Schneider Electric": "SU.PA", "Airbus": "AIR.PA", "Safran": "SAF.PA", "BNP Paribas": "BNP.PA",
            "AXA": "CS.PA", "Air Liquide": "AI.PA"}
FR_NAMES = {"LVMH", "Hermès", "TotalEnergies", "Sanofi", "L'Oréal", "Schneider Electric", "Airbus", "Safran", "BNP Paribas", "AXA", "Air Liquide"}


def fetch_caps():  # capitalisations lues sur Yahoo Finance, converties en dollars
    if yf is None:
        raise RuntimeError("yfinance indisponible")

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

    res = []
    ex = ThreadPoolExecutor(6)
    try:
        futs = [ex.submit(one, it) for it in CAP_LIST.items()]
        try:
            for f in as_completed(futs, timeout=45):
                r = f.result()
                if r:
                    res.append(r)
        except Exception:
            pass
    finally:
        ex.shutdown(wait=False)
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


# ---- Actualités (CNBC) et traduction ----
FEED = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
AGGREGATOR = "https://www.tradingview.com/news/"


def fetch_news():
    if feedparser is None:
        raise RuntimeError("feedparser indisponible")
    r = requests.get(FEED, headers=UA, timeout=8)
    r.raise_for_status()
    out = []
    for e in feedparser.parse(r.content).entries[:40]:
        title = getattr(e, "title", "").strip()
        if not title:
            continue
        ts = calendar.timegm(e.published_parsed) if getattr(e, "published_parsed", None) else 0
        out.append({"title": title, "link": getattr(e, "link", AGGREGATOR), "ts": ts,
                    "summary": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", getattr(e, "summary", ""))).strip()})
    if not out:
        raise RuntimeError("flux vide")
    return out


def tr_batch(texts):
    if GoogleTranslator is None:
        raise RuntimeError("traduction indisponible")
    texts = list(texts)
    g = GoogleTranslator(source="en", target="fr")
    out = (g.translate("\n".join(texts)) or "").split("\n")
    if len(out) != len(texts):
        out = g.translate_batch(texts)
    if len(out) != len(texts):
        raise RuntimeError("traduction incomplète")
    return tuple(str(x or "") for x in out)


# ---- Calendrier économique (flux public Fair Economy / Forex Factory : consensus et précédent) ----
FF_URLS = ["https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
           "https://cdn-nfs.faireconomy.media/ff_calendar_nextweek.json"]


def fetch_eco():
    out, ok = [], 0
    for u in FF_URLS:
        try:
            r = requests.get(u, headers=UA, timeout=8)
            r.raise_for_status()
            data = r.json()
            ok += 1
        except Exception as ex:
            log.info("calendrier éco %s : %s", u, ex)
            continue
        for e in data:
            try:
                dt = pd.Timestamp(e["date"])
                dt = dt.tz_localize("UTC") if dt.tzinfo is None else dt
                out.append(dict(ts=dt.tz_convert(PARIS).to_pydatetime(), title=str(e.get("title", "")).strip(),
                                cur=str(e.get("country", "")).upper(), impact=str(e.get("impact", "")),
                                forecast=str(e.get("forecast") or "").strip(), previous=str(e.get("previous") or "").strip(),
                                actual=str(e.get("actual") or "").strip()))
            except Exception:
                continue
    if not ok:
        raise RuntimeError("calendrier économique injoignable")
    out.sort(key=lambda x: x["ts"])
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
@media (prefers-reduced-motion:reduce){.live i{animation:none}}
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
.hint{margin-top:18px;font-size:.7rem;color:var(--dim);line-height:1.5}

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
.pill.up{color:var(--up)}.pill.dn{color:var(--dn)}.pill.am{color:var(--am)}
.kc .pill{display:inline-block;border:1px solid var(--ln2);border-radius:2px;padding:2px 8px;font-size:.7rem;margin-top:4px}
.sec{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin:30px 0 14px;padding-bottom:9px;border-bottom:1px solid var(--ln)}
.sec h2{margin:0;padding:0;font-family:var(--serif);font-weight:500;font-size:1.55rem;letter-spacing:-.01em;color:var(--tx)}
.sec span{color:var(--mut);font-size:.8rem}
.btn{display:inline-flex;align-items:center;gap:8px;text-decoration:none!important;padding:9px 16px;border:1px solid var(--am);border-radius:2px;font-family:var(--mono);font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:var(--am)!important;transition:.15s}
.btn:hover{background:var(--am);color:#0B0C0E!important}
.note{margin:8px 0 0;color:var(--dim);font-size:.74rem;line-height:1.5}
.empty{padding:22px 20px;border:1px dashed var(--ln2);border-radius:3px;color:var(--mut);font-size:.88rem;line-height:1.5}

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

/* ---------- Carte thermique (vue d'ensemble) ---------- */
.hgrp{margin:0 0 18px}
.hgrp h4{margin:0 0 8px;font-family:var(--mono);font-size:.64rem;letter-spacing:.18em;text-transform:uppercase;color:var(--dim);font-weight:500}
.hgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(136px,1fr));gap:6px}
.ht{display:flex;flex-direction:column;gap:3px;padding:9px 11px;border:1px solid var(--ln);border-radius:3px;min-width:0}
.ht span{font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ht b{font-family:var(--mono);font-size:1rem;font-weight:500;color:var(--tx);white-space:nowrap}
.ht em{font-style:normal;font-family:var(--mono);font-size:.76rem}
.ht em.up{color:var(--up)}.ht em.dn{color:var(--dn)}
.rx{display:inline-flex;gap:6px;align-items:baseline;margin:6px 8px 0 0;padding:2px 8px;border:1px solid var(--ln2);border-radius:2px;font-family:var(--mono);font-size:.7rem;color:var(--mut)}
.rx b{font-weight:500}.rx b.up{color:var(--up)}.rx b.dn{color:var(--dn)}

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
.bars{display:inline-flex;gap:2px}.bars i{width:12px;height:3px;background:var(--ln2)}.bars i.on{background:var(--c)}
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
@media(max-width:900px){.sg{grid-template-columns:repeat(2,1fr)}}

/* ---------- Calendrier économique ---------- */
.evt td.day{padding:16px 14px 8px;font-family:var(--serif);font-size:1.05rem;font-weight:500;color:var(--tx);background:transparent;border-bottom:1px solid var(--ln2);text-transform:capitalize}
.evt tr.past td{opacity:.42}
.evt tr.now td{background:rgba(227,163,59,.08)}
.cur{display:inline-block;font-family:var(--mono);font-size:.68rem;border:1px solid var(--ln2);border-radius:2px;padding:2px 7px;color:var(--tx)}
.evt td.num{font-family:var(--mono);font-size:.8rem;color:var(--tx);white-space:nowrap}
.evt td.cd{font-family:var(--mono);font-size:.74rem;white-space:nowrap}

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

# --- Icônes SVG (style Lucide), une par page ---
ICON_PATHS = {
    "overview": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    "watch": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "rates": '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    "indices": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "fx": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "commo": '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
    "stocks": '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
    "france": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "crypto": '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
    "vol": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "news": '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/>',
    "book": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "curve": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M7 16c.5-2 1.5-7 4-7 2 0 2 3 4 3 2.5 0 4.5-5 5-6"/>',
    "eco": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/><path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/>',
    "bank": '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    "compare": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M11 18H8a2 2 0 0 1-2-2V9"/>',
}


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
#  OUTILS D'INTERFACE
# =====================================================================
def _has_param(fn, name):
    try:
        return name in inspect.signature(fn).parameters
    except Exception:
        return False


_PLOTLY_W = _has_param(st.plotly_chart, "width")
_DF_W = _has_param(st.dataframe, "width")


def show(fig, key=None, static=False):
    cfg = {"displayModeBar": False, "staticPlot": static}
    if _PLOTLY_W:
        st.plotly_chart(fig, width="stretch", config=cfg, key=key)
    else:
        st.plotly_chart(fig, use_container_width=True, config=cfg, key=key)


def df_show(df):
    if _DF_W:
        st.dataframe(df, width="stretch")
    else:
        st.dataframe(df, use_container_width=True)


def html_embed(page, height):
    """Intègre un bloc HTML/JS : st.iframe (Streamlit récent) puis components.html (versions plus anciennes)."""
    if hasattr(st, "iframe"):
        try:
            st.iframe(page, height=height)
            return
        except Exception as ex:
            log.info("st.iframe : %s", ex)
    if components is not None and hasattr(components, "html"):
        try:
            components.html(page, height=height)
        except Exception as ex:
            log.info("components.html : %s", ex)


def guarded(fn):
    """Une erreur dans une page affiche un encadré propre au lieu de tout arrêter (les exceptions de contrôle Streamlit passent)."""
    @functools.wraps(fn)
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except Exception:
            tb = traceback.format_exc()
            log.error("erreur dans %s :\n%s", fn.__name__, tb)
            st.error("Cette section a rencontré un problème temporaire. Elle se rechargera automatiquement ; "
                     "si le message reste affiché, ouvrez les détails techniques ci-dessous.")
            with st.expander("Détails techniques"):
                st.code(tb)
    return wrapper


def frag(every=None):
    """Page protégée + rafraîchissement automatique en direct (fragment Streamlit)."""
    def deco(fn):
        g = guarded(fn)
        return st.fragment(g, run_every=every) if every else st.fragment(g)
    return deco


def clean_label(k):
    return re.sub(r"^[^\w]+", "", k).strip()


def hex_rgba(h, a):
    h = h.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_L = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def fresh(ts):
    """Pastille de fraîcheur des données."""
    if not ts:
        return '<span class="pill dn">● En attente des données</span>'
    age = time.time() - ts
    hh = datetime.fromtimestamp(ts, tz=PARIS).strftime("%H:%M:%S")
    if age < 120:
        return f'<span class="pill up">● Actualisé à {hh}</span>'
    if age < 900:
        return f'<span class="pill am">◐ Dernière mise à jour {hh}</span>'
    return f'<span class="pill dn">✕ Source indisponible · données de {hh}</span>'


def hero(eyebrow, title, sub, pills=""):
    n = datetime.now(PARIS)
    st.markdown(f'<div class="hero"><div><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p></div>'
                f'<div class="hmeta"><div class="pills">{pills}</div>'
                f'<div class="hdate">{JOURS[n.weekday()]} {n.day} {MOIS_L[n.month - 1]} {n.year} · {n:%H:%M} Paris</div></div></div>', unsafe_allow_html=True)


def sec(title, sub, right=""):
    st.markdown(f'<div class="sec"><div><h2>{title}</h2><span>{sub}</span></div><div>{right}</div></div>', unsafe_allow_html=True)


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
tick();setInterval(tick,1000)
/* raccourcis clavier : touches 1 à 9 = pages du menu (sans effet si l'accès à la page parente est refusé) */
try{const P=window.parent;if(P&&!P.__mtKeys){P.__mtKeys=true;P.document.addEventListener('keydown',e=>{const t=((e.target&&e.target.tagName)||'').toLowerCase();if(['input','textarea','select'].indexOf(t)>=0||e.metaKey||e.ctrlKey||e.altKey)return;const n=parseInt(e.key,10);if(n>=1&&n<=9){const l=P.document.querySelectorAll('section[data-testid="stSidebar"] div[role="radiogroup"]>label');if(l[n-1])l[n-1].click()}})}}catch(err){}
</script>""".replace("__CFG__", json.dumps(cfg))
    html_embed(page, 88)


# =====================================================================
#  VUE DÉTAILLÉE (clic sur une carte)
# =====================================================================
PERIODS = {"1J": ("1d", "5m"), "5J": ("5d", "30m"), "1M": ("1mo", "1d"), "3M": ("3mo", "1d"),
           "6M": ("6mo", "1d"), "1A": ("1y", "1d"), "5A": ("5y", "1wk")}


@st.dialog("Analyse détaillée", width="large")
def detail_dialog(name, ticker, cat, ext, day_txt, day_cls):
    st.markdown(f'<div class="eyebrow">{html.escape(cat)} · {html.escape(ticker)}</div><h2 style="margin:2px 0 10px;font-weight:800">{html.escape(name)}</h2>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    per = c1.radio("Période", list(PERIODS), index=3, horizontal=True, label_visibility="collapsed", disabled=ext is not None, key="dlg_per")
    mode = c2.radio("Type", ["Ligne", "Chandeliers"], horizontal=True, label_visibility="collapsed", key="dlg_mode")
    if ext is not None:
        df, per_lbl, interval = pd.DataFrame({"Close": ext.astype(float)}), "90 j", "1d"
    else:
        period, interval = PERIODS[per]
        per_lbl = per
        df, _, _ = HUB.swr.get(("ohlc", ticker, per), fetch_ohlc, 45 if interval not in ("1d", "1wk") else 300,
                               args=(ticker, period, interval), wait_first=18, label="Historique " + ticker)
    if df is None or len(df) < 3 or "Close" not in df:
        st.warning("Historique momentanément indisponible pour cet instrument : réessayez dans un instant.")
        return
    cl = df["Close"].astype(float).dropna()
    last, first = float(cl.iloc[-1]), float(cl.iloc[0])
    is_y = ticker in YIELDS or ticker.startswith("ext:")
    perf_txt = sgn((last - first) * 100, 1, " pb") if is_y else sgn((last / first - 1) * 100 if first else 0, 2, " %")
    perf_cls = "up" if last >= first else "dn"
    hi, lo = float(cl.max()), float(cl.min())
    d = cl.diff()
    gain, loss = d.clip(lower=0).rolling(14).mean(), (-d.clip(upper=0)).rolling(14).mean()
    rsi = (100 - 100 / (1 + gain / loss)).iloc[-1]
    ann = {"1d": 252, "1wk": 52}.get(interval)
    vol = f"{cl.pct_change().std() * (ann ** .5) * 100:.1f} %".replace(".", ",") if ann and len(cl) > 5 else "n/a"
    rsi_txt = f"{rsi:.0f}" if pd.notna(rsi) and rsi != float("inf") else "n/a"
    rsi_cls = "" if rsi_txt == "n/a" else ("dn" if rsi > 70 else ("up" if rsi < 30 else ""))
    tiles = [("Dernier", fnum(last, dec_of(ticker, last)), ""), ("Variation jour", day_txt, day_cls),
             (f"Perf. {per_lbl}", perf_txt, perf_cls), ("Volatilité ann.", vol, ""),
             ("Plus haut", fnum(hi, dec_of(ticker, hi)), ""), ("Plus bas", fnum(lo, dec_of(ticker, lo)), ""),
             ("Écart au plus haut", sgn((last / hi - 1) * 100 if hi else 0, 2, " %"), "dn"),
             ("RSI (14)", rsi_txt, rsi_cls)]
    st.markdown('<div class="sg">' + "".join(f'<div class="sgt"><span>{a}</span><b class="{c}">{b}</b></div>' for a, b, c in tiles) + '</div>',
                unsafe_allow_html=True)
    pos = 0 if hi == lo else (last - lo) / (hi - lo) * 100
    st.markdown(f'<div class="rb"><i style="left:calc({pos:.0f}% - 3px)"></i></div><div class="rl"><span>{fnum(lo, dec_of(ticker, lo))}</span>'
                f'<span>position dans la fourchette {per_lbl}</span><span>{fnum(hi, dec_of(ticker, hi))}</span></div>', unsafe_allow_html=True)

    has_vol = "Volume" in df and df["Volume"].fillna(0).sum() > 0
    fig = make_subplots(rows=2 if has_vol else 1, cols=1, shared_xaxes=True, vertical_spacing=.03, row_heights=[.78, .22] if has_vol else [1])
    col = UP if last >= first else DN
    if mode == "Chandeliers" and {"Open", "High", "Low"} <= set(df.columns):
        fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Prix",
                                     increasing_line_color=UP, decreasing_line_color=DN), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=cl.index, y=cl, name="Clôture", line=dict(color=col, width=2.6, shape="spline", smoothing=.5),
                                 fill="tozeroy", fillcolor=hex_rgba(col, .08)), row=1, col=1)
    for w_, c_ in ((20, "#D9923A"), (50, "#A9B4C2")):
        if len(cl) > w_ + 2:
            fig.add_trace(go.Scatter(x=cl.index, y=cl.rolling(w_).mean(), name=f"MM{w_}", line=dict(color=c_, width=1.3, dash="dot")), row=1, col=1)
    if has_vol:
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color="rgba(108,155,201,.45)"), row=2, col=1)
    if interval not in ("1d", "1wk") and not ticker.endswith("-USD"):
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    pad = (hi - lo) * .08 or 1
    fig.update_layout(height=440 if has_vol else 380, margin=dict(l=0, r=0, t=6, b=0), hovermode="x unified",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="IBM Plex Sans", color="#CFCBC2"),
                      xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.07, x=0), hoverlabel=dict(bgcolor="#111317", bordercolor=col))
    fig.update_xaxes(gridcolor="rgba(255,255,255,.05)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,.05)")
    fig.update_yaxes(range=[lo - pad, hi + pad], row=1, col=1)
    show(fig, key="detail_chart")
    with st.expander("Dernières séances"):
        df_show(df.tail(10).iloc[::-1].round(2))


# =====================================================================
#  CARTES DE MARCHÉ (clic = détail)
# =====================================================================
def cards_grid(items, cat_label, prefix):
    cols = st.columns(4)
    for i, (name, ticker, series) in enumerate(items):
        with cols[i % 4]:
            info = chg_info(ticker, series)
            curr = info["curr"]
            base30 = float(series.tail(30).iloc[0])
            d30 = curr - base30
            if info["is_y"]:
                c30 = sgn(d30 * 100, 0, " pb")
            else:
                c30 = sgn((curr / base30 - 1) * 100 if base30 else 0, 1, " %")
            good30 = (d30 < 0) if ticker in INVERSE else (d30 >= 0)
            cls30 = "up" if good30 else "dn"
            color = UP if info["good"] else DN
            with st.container(key=f"card_{prefix}_{i}"):
                st.markdown(
                    f'<div class="mt">{html.escape(name)}<svg class="ex" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg></div>'
                    f'<div class="mrow"><span class="mv">{fnum(curr, dec_of(ticker, curr))}<span class="un">{unit_of(ticker)}</span></span>'
                    f'<span class="chip {info["cls"]}">{"▲" if info["d"] >= 0 else "▼"} {info["txt"]}</span></div>'
                    f'<div class="sub">30 j <b class="{cls30}">{c30}</b> · point du {series.index[-1]:%d/%m}</div>', unsafe_allow_html=True)
                show(mini_chart(series.tail(30), color), key=f"mini_{prefix}_{i}", static=True)
                if st.button("Détails", key=f"btn_{prefix}_{i}"):
                    st.session_state["detail"] = (name, ticker, cat_label, series if ticker.startswith("ext:") else None, info["txt"], info["cls"])
                    st.rerun()


@frag(30)
def render_market(cat):
    tk = tuple(UNIVERSE[cat].values())
    with st.spinner("Synchronisation avec les marchés..."):
        data, ts, err = px(tk)
    avail, missing = [], []
    for name, t in UNIVERSE[cat].items():
        sr = data.get(t)
        if sr is not None and len(sr) >= 2:
            avail.append((name, t, sr))
        else:
            missing.append(name)
    if cat == list(UNIVERSE)[0]:  # page des taux : séries officielles complémentaires
        ext, _ = sget("ext_rates", fetch_ext_rates, 900, wait_first=8)
        for n_, sr in (ext or {}).items():
            if n_.startswith("US 2 ans") and "2YY=F" in data:
                continue
            avail.append((n_, "ext:" + n_, sr))
    ups = sum(1 for _, _, sr in avail if sr.iloc[-1] >= sr.iloc[-2])
    hero("Marchés", clean_label(cat),
         f"{len(avail)} instruments · Yahoo Finance (différé jusqu'à 15 min selon les places) · actualisation automatique toutes les 30 s",
         fresh(ts) + f'<span class="pill up">▲ {ups} en hausse</span><span class="pill dn">▼ {len(avail) - ups} en baisse</span>')
    if not avail:
        st.markdown('<div class="empty">Yahoo Finance ne répond pas pour le moment. Le terminal réessaie automatiquement : '
                    'les cotations apparaîtront dès que la source répond, sans rien faire de ton côté.</div>', unsafe_allow_html=True)
        return
    cards_grid(avail, clean_label(cat), "m")
    if missing:
        st.caption("Temporairement indisponibles chez Yahoo Finance : " + ", ".join(missing))


# =====================================================================
#  VUE D'ENSEMBLE (carte thermique cross-asset, appétit pour le risque, agenda, actus)
# =====================================================================
HEAT = [
    ("Actions", [("S&P 500", "^GSPC"), ("Nasdaq 100", "^NDX"), ("Dow Jones", "^DJI"), ("Russell 2000", "^RUT"), ("CAC 40", "^FCHI"),
                 ("DAX 40", "^GDAXI"), ("Euro Stoxx 50", "^STOXX50E"), ("FTSE 100", "^FTSE"), ("Nikkei 225", "^N225"), ("Hang Seng", "^HSI")]),
    ("Taux américains", [("US 2 ans", "2YY=F"), ("US 5 ans", "^FVX"), ("US 10 ans", "^TNX"), ("US 30 ans", "^TYX")]),
    ("Devises", [("Dollar index", "DX-Y.NYB"), ("EUR/USD", "EURUSD=X"), ("USD/JPY", "USDJPY=X"), ("GBP/USD", "GBPUSD=X"), ("USD/CHF", "USDCHF=X")]),
    ("Matières premières", [("Brent", "BZ=F"), ("WTI", "CL=F"), ("Or", "GC=F"), ("Argent", "SI=F"), ("Cuivre", "HG=F"), ("Gaz naturel", "NG=F")]),
    ("Crypto", [("Bitcoin", "BTC-USD"), ("Ethereum", "ETH-USD")]),
    ("Volatilité & crédit", [("VIX", "^VIX"), ("MOVE", "^MOVE"), ("High Yield (HYG)", "HYG"), ("Inv. Grade (LQD)", "LQD")]),
]
HEAT_T = tuple(dict.fromkeys(t for _, items in HEAT for _, t in items))
SHORT = {t: n for _, items in HEAT for n, t in items}


def heat_tile(name, t, sr):
    info = chg_info(t, sr)
    if info["is_y"]:
        mag = abs(info["d"] * 100) / 12
    else:
        mag = abs(info["pct"]) / (10 if t in INVERSE else 2.5)
    mag = min(mag, 1.0)
    col = UP if info["good"] else DN
    return (f'<div class="ht" style="background:{hex_rgba(col, 0.07 + 0.30 * mag)};border-color:{hex_rgba(col, 0.22 + 0.40 * mag)}">'
            f'<span>{html.escape(name)}</span><b>{fnum(info["curr"], dec_of(t, info["curr"]))}</b><em class="{info["cls"]}">{info["txt"]}</em></div>')


def _chg_n(sr, n):
    if sr is None or len(sr) < 2:
        return None
    k = min(n, len(sr) - 1)
    a, b = float(sr.iloc[-1 - k]), float(sr.iloc[-1])
    return (b / a - 1) * 100 if a else None


RISK_COMPONENTS = [("Actions · S&P 500", "^GSPC", +1, 0.30, 3.0), ("Peur · VIX", "^VIX", -1, 0.25, 30.0),
                   ("Crédit · HYG/LQD", "RATIO", +1, 0.25, 1.0), ("Dollar · DXY", "DX-Y.NYB", -1, 0.10, 1.5), ("Or", "GC=F", -1, 0.10, 4.0)]


def risk_score(data):
    """Score 0-100 (0 = aversion maximale, 100 = appétit maximal) à partir des variations sur 5 séances. Indicatif."""
    rows, tot, wsum = [], 0.0, 0.0
    for label, t, sign, w, scale in RISK_COMPONENTS:
        if t == "RATIO":
            sr = (data["HYG"] / data["LQD"]).dropna() if "HYG" in data and "LQD" in data else None
        else:
            sr = data.get(t)
        c = _chg_n(sr, 5)
        if c is None:
            continue
        s = max(-1.0, min(1.0, sign * c / scale))
        rows.append((label, c, s))
        tot += w * s
        wsum += w
    if not rows or wsum == 0:
        return None
    return 50 + 50 * tot / wsum, rows


def react_chips(tag, data):
    out = ""
    for t in NEWS_REACT.get(tag, []):
        sr = data.get(t)
        if sr is not None and len(sr) >= 2:
            i = chg_info(t, sr)
            out += f'<span class="rx">{SHORT.get(t, t)} <b class="{i["cls"]}">{i["txt"]}</b></span>'
    return out


def eco_upcoming(events, n=6, hours=96):
    now = datetime.now(PARIS)
    return [e for e in (events or []) if e["impact"] == "High" and e["cur"] in ("USD", "EUR", "GBP", "JPY", "CNY", "CHF")
            and now - timedelta(minutes=30) <= e["ts"] <= now + timedelta(hours=hours)][:n]


def countdown(ts):
    delta = (ts - datetime.now(PARIS)).total_seconds()
    m = int(abs(delta) // 60)
    if m < 1:
        return "maintenant"
    txt = f"{m // 1440} j {m % 1440 // 60} h" if m >= 1440 else (f"{m // 60} h {m % 60:02d}" if m >= 60 else f"{m} min")
    return ("dans " if delta > 0 else "il y a ") + txt


@frag(30)
def render_overview():
    with st.spinner("Synchronisation avec les marchés..."):
        data, ts, err = px(HEAT_T)
    rs = risk_score(data) if data else None
    pills = fresh(ts)
    if rs:
        lab = "Risk-on" if rs[0] > 65 else ("Risk-off" if rs[0] < 35 else "Neutre")
        pills += f'<span class="pill {"up" if rs[0] > 65 else ("dn" if rs[0] < 35 else "am")}">Régime : {lab}</span>'
    hero("Terminal", "Vue d'ensemble", "Tous les marchés en un coup d'œil · actualisation automatique toutes les 30 s · cliquez sur « Marchés » pour le détail", pills)
    if not data:
        st.markdown('<div class="empty">Yahoo Finance ne répond pas pour le moment. Le terminal réessaie automatiquement : '
                    'les cotations apparaîtront dès que la source répond.</div>', unsafe_allow_html=True)
        return
    left, right = st.columns([3, 2])
    with left:
        sec("Carte des marchés", "Variation sur la dernière séance · vert = hausse, rouge = baisse (inversé pour VIX et MOVE)")
        for grp, items in HEAT:
            tiles = "".join(heat_tile(n, t, data[t]) for n, t in items if t in data and len(data[t]) >= 2)
            if tiles:
                st.markdown(f'<div class="hgrp"><h4>{grp}</h4><div class="hgrid">{tiles}</div></div>', unsafe_allow_html=True)
    with right:
        sec("Appétit pour le risque", "Indicateur composite, variations sur 5 séances")
        if rs:
            clr = UP if rs[0] > 65 else (DN if rs[0] < 35 else A1)
            show(gauge(round(rs[0]), "0 = aversion · 100 = appétit", color=clr, suffix=""), key="ov_risk")
            st.markdown(table(["Composante", "5 séances", "Lecture"], [
                [lab_, sgn(c, 2, " %"), '<span class="pill up">favorable</span>' if s > 0.05 else ('<span class="pill dn">défavorable</span>' if s < -0.05 else "neutre")]
                for lab_, c, s in rs[1]]), unsafe_allow_html=True)
            st.markdown('<div class="note">Indicateur pédagogique (S&amp;P 500, VIX, crédit, dollar, or) : un résumé du climat de marché, pas un signal de trading.</div>',
                        unsafe_allow_html=True)
        else:
            st.caption("Données insuffisantes pour calculer l'indicateur.")
        sec("Agenda à fort impact", "Prochaines publications · heure de Paris")
        events, _ = sget("eco", fetch_eco, 1800, wait_first=6)
        up = eco_upcoming(events)
        if up:
            st.markdown('<div class="tp">' + "".join(
                f'<div class="fl" style="grid-template-columns:96px 1fr auto"><span class="tm">{e["ts"]:%a %H:%M}</span>'
                f'<div><div class="en" style="font-weight:600;font-size:.88rem">{html.escape(eco_fr(e["title"]))}</div></div>'
                f'<span class="cur">{e["cur"]}</span></div>' for e in up) + '</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">Aucune publication à fort impact dans les 4 prochains jours, ou calendrier momentanément indisponible.</div>',
                        unsafe_allow_html=True)
    sec("À la une", "Les titres les plus marquants du moment et la réaction des marchés associés")
    news, _ = sget("news", fetch_news, 600, wait_first=6)
    if news:
        items = []
        for n in news:
            n = dict(n)
            n["score"], n["tag"] = score(n)
            items.append(n)
        top = sorted(items, key=lambda n: (n["score"], n["ts"]), reverse=True)[:4]
        titles = tuple(n["title"] for n in top)
        res, _ = sget(("tr", titles), tr_batch, 86400, args=(titles,), wait_first=0.5, label="Traduction")
        rows = ""
        for i, n in enumerate(top):
            c = TAGS[n["tag"]][0]
            fr_line = f'<div class="fr">{html.escape(res[i])}</div>' if res and res[i] and res[i].strip().lower() != n["title"].strip().lower() else ""
            rows += (f'<a class="tr" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank" rel="noopener"><div class="rk2">{i + 1}</div>'
                     f'<div><div class="en">{html.escape(n["title"])}</div>{fr_line}<div>{react_chips(n["tag"], data)}</div></div>'
                     f'<div class="mt2"><span class="tag">{n["tag"]}</span><span class="tm">{fmt(n["ts"])}</span></div></a>')
        st.markdown(f'<div class="tp">{rows}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty">Flux d\'actualités momentanément indisponible : rechargement automatique.</div>', unsafe_allow_html=True)


# =====================================================================
#  ACTUALITÉS MACRO
# =====================================================================
TAGS = {
    "Banques centrales": ("#C9A86A", 5, ["fed", "federal reserve", "ecb", "boj", "bank of japan", "bank of england", "powell", "warsh", "lagarde", "rate cut", "rate hike", "interest rate", "central bank", "fomc"]),
    "Inflation & Emploi": ("#D9923A", 4, ["inflation", "cpi", "pce", "jobs", "payroll", "unemployment", "gdp", "recession", "layoffs", "consumer prices"]),
    "Géopolitique": ("#E5574C", 4, ["war", "sanction", "iran", "russia", "ukraine", "china", "israel", "tariff", "trade war", "middle east", "taiwan", "election", "trump", "ceasefire"]),
    "Énergie": ("#C77D4A", 3, ["oil", "crude", "natural gas", "opec", "energy", "brent"]),
    "Europe & France": ("#9DB4A0", 3, ["france", "french", "macron", "eurozone", "euro zone", "european", "europe", "germany", "paris", "cac"]),
    "Marchés": ("#6C9BC9", 2, ["stocks", "s&p", "nasdaq", "dow", "yields", "treasury", "dollar", "bond", "bitcoin", "earnings", "wall street"]),
}
HOT = ["plunge", "surge", "soar", "crash", "record", "emergency", "shock", "collapse", "spike", "tumble", "warns", "default"]
# Instruments à surveiller pour chaque thème : la « réaction de marché » affichée sous chaque titre
NEWS_REACT = {
    "Banques centrales": ["^TNX", "DX-Y.NYB", "^GSPC"], "Inflation & Emploi": ["^TNX", "DX-Y.NYB", "GC=F"],
    "Géopolitique": ["GC=F", "BZ=F", "^VIX"], "Énergie": ["BZ=F", "CL=F", "NG=F"],
    "Europe & France": ["^FCHI", "EURUSD=X", "^GDAXI"], "Marchés": ["^GSPC", "^NDX", "BTC-USD"],
}


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


@frag(300)
def render_news():
    raw, ts = sget("news", fetch_news, 600, wait_first=15)
    data, _, _ = px(HEAT_T, wait_first=8)
    hero("Intelligence de marché", "Actualités Macro", "Titres d'origine (CNBC) classés par impact estimé, avec traduction française et réaction des marchés",
         fresh(ts) + '<span class="pill">Source · CNBC</span>')
    news = []
    for n in (raw or []):
        n = dict(n)
        n["score"], n["tag"] = score(n)
        news.append(n)
    if not news:
        st.markdown('<div class="empty">Le flux d\'actualités ne répond pas pour le moment. Il se rechargera automatiquement.</div>', unsafe_allow_html=True)
        return
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
            rx = react_chips(n["tag"], data)
            out += (f'<a class="tr{" f" if i == 1 else ""}" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank" rel="noopener">'
                    f'<div class="rk2">{i}</div><div><div class="en">{html.escape(n["title"])}</div>{line}{sm}<div>{rx}</div></div>'
                    f'<div class="mt2"><span class="tag">{n["tag"]}</span><div class="bars">{"".join("<i class=on></i>" if k < lvl else "<i></i>" for k in range(5))}</div>'
                    f'<span class="tm">{fmt(n["ts"])}</span></div></a>')
        return f'<div class="tp">{out}</div>'

    def flux_html(frm, sel):
        out = ""
        for n in flux:
            if sel not in (None, "Tous") and n["tag"] != sel:
                continue
            c, line, _ = trio(n, frm)
            out += (f'<a class="fl" style="--c:{c}" href="{html.escape(n["link"])}" target="_blank" rel="noopener"><span class="tm">{fmt(n["ts"])}</span>'
                    f'<div><div class="en" style="font-weight:600;font-size:.9rem">{html.escape(n["title"])}</div>{line}</div>'
                    f'<span class="tag">{n["tag"]}</span></a>')
        return f'<div class="tp">{out or "<div class=fr style=padding:16px>Aucune actualité pour ce filtre.</div>"}</div>'

    sec("Le Top 5", "Classé par impact macro & géopolitique estimé · titre d'origine, traduction en dessous, puis réaction des marchés associés")
    top_box = st.empty()
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    sec("Le Flux du Jour", "Du plus récent au plus ancien", f'<a class="btn" href="{AGGREGATOR}" target="_blank" rel="noopener">Toutes les infos en temps réel ↗</a>')
    opts = ["Tous"] + list(TAGS)
    sel = (st.pills("Filtre", opts, default="Tous", label_visibility="collapsed") if hasattr(st, "pills")
           else st.radio("Filtre", opts, horizontal=True, label_visibility="collapsed"))
    flux_box = st.empty()
    note = st.empty()
    top_box.markdown(top_html({}), unsafe_allow_html=True)
    flux_box.markdown(flux_html({}, sel), unsafe_allow_html=True)
    note.caption("Traduction en cours…")
    items = top5 + flux
    summ = top5[0]["summary"][:240].rsplit(" ", 1)[0] or top5[0]["title"]
    texts = tuple([n["title"] for n in items] + [summ])
    res, _ = sget(("tr", texts), tr_batch, 86400, args=(texts,), wait_first=18, label="Traduction")
    if res:
        frm = {n["link"]: (res[i], "") for i, n in enumerate(items)}
        frm[top5[0]["link"]] = (res[0], res[-1])
        top_box.markdown(top_html(frm), unsafe_allow_html=True)
        flux_box.markdown(flux_html(frm, sel), unsafe_allow_html=True)
        note.empty()
    else:
        note.caption("Traduction momentanément indisponible : titres affichés en anglais, nouvel essai automatique.")


# =====================================================================
#  CALENDRIER ÉCONOMIQUE
# =====================================================================
ECO_FR = {
    "Non-Farm Employment Change": "Emplois non agricoles (NFP)", "Unemployment Rate": "Taux de chômage",
    "Unemployment Claims": "Demandes d'allocations chômage", "Core CPI": "IPC sous-jacent", "CPI": "Inflation (CPI)",
    "Core PCE Price Index": "Déflateur PCE sous-jacent", "Federal Funds Rate": "Taux des Fed funds", "FOMC Statement": "Communiqué du FOMC",
    "FOMC Meeting Minutes": "Minutes du FOMC", "FOMC Press Conference": "Conférence de presse du FOMC",
    "Main Refinancing Rate": "Taux de refinancement principal (BCE)", "Monetary Policy Statement": "Déclaration de politique monétaire",
    "ECB Press Conference": "Conférence de presse de la BCE", "Official Bank Rate": "Taux directeur (Bank Rate)",
    "Retail Sales": "Ventes au détail", "GDP": "PIB", "Manufacturing PMI": "PMI manufacturier", "Services PMI": "PMI services",
    "PPI": "Prix à la production (PPI)", "Trade Balance": "Balance commerciale", "Consumer Confidence": "Confiance des consommateurs",
    "Industrial Production": "Production industrielle", "Speaks": "intervient", "Prelim": "préliminaire", "Final": "final", "Flash": "flash",
}
_ECO_RE = re.compile("|".join(re.escape(k) for k in sorted(ECO_FR, key=len, reverse=True)))


def eco_fr(title):
    return _ECO_RE.sub(lambda m: ECO_FR[m.group(0)], title)


ECO_IMPACT = {"Élevé": {"High"}, "Moyen et plus": {"High", "Medium"}, "Tous": {"High", "Medium", "Low", "Holiday"}}


def impact_bars(impact):
    lvl, col = {"High": (3, "#E5574C"), "Medium": (2, "#E3A33B"), "Low": (1, "#8E9099")}.get(impact, (0, "#8E9099"))
    if not lvl:
        return '<span class="tm">férié</span>'
    return f'<span class="bars" style="--c:{col}">' + "".join("<i class=on></i>" if k < lvl else "<i></i>" for k in range(3)) + "</span>"


@frag(60)
def eco_table(imp, curs):
    events, ts = sget("eco", fetch_eco, 1800, wait_first=12)
    if events is None:
        st.markdown('<div class="empty">Le flux du calendrier économique ne répond pas pour le moment. Il se rechargera automatiquement.</div>', unsafe_allow_html=True)
        return
    now = datetime.now(PARIS)
    keep = ECO_IMPACT[imp]
    ev = [e for e in events if e["impact"] in keep and (not curs or e["cur"] in curs)]
    if not ev:
        st.markdown('<div class="empty">Aucune publication pour ces filtres sur la période couverte (semaine en cours et suivante).</div>', unsafe_allow_html=True)
        return
    rows, day = "", None
    for e in ev:
        d = e["ts"].date()
        if d != day:
            day = d
            rows += f'<tr><td class="day" colspan="7">{JOURS[d.weekday()]} {d.day} {MOIS_L[d.month - 1]}</td></tr>'
        past = e["ts"] < now - timedelta(minutes=30)
        cls = "past" if past else ("now" if abs((e["ts"] - now).total_seconds()) <= 1800 else "")
        rows += (f'<tr class="{cls}"><td>{e["ts"]:%H:%M}</td><td><span class="cur">{html.escape(e["cur"])}</span></td>'
                 f'<td>{html.escape(eco_fr(e["title"]))}</td><td>{impact_bars(e["impact"])}</td>'
                 f'<td class="num">{html.escape(e["previous"]) or "—"}</td><td class="num">{html.escape(e["forecast"]) or "—"}</td>'
                 f'<td class="cd">{countdown(e["ts"])}</td></tr>')
    st.markdown('<table class="ct evt"><tr><th>Heure</th><th>Devise</th><th>Événement</th><th>Impact</th><th>Précédent</th><th>Consensus</th><th>Échéance</th></tr>'
                + rows + '</table>', unsafe_allow_html=True)
    st.markdown(f'<div class="note">{fresh(ts)} · Source : flux public Fair Economy (Forex Factory) · heures de Paris · '
                'le flux fournit le précédent et le consensus ; la valeur publiée n\'y figure pas.</div>', unsafe_allow_html=True)


@guarded
def render_eco():
    events, ts = sget("eco", fetch_eco, 1800, wait_first=12)
    hero("Agenda macro", "Calendrier Économique", "Publications de la semaine : précédent, consensus et impact estimé · heure de Paris", fresh(ts))
    c1, c2 = st.columns([3, 4])
    imp = c1.radio("Impact", list(ECO_IMPACT), index=1, horizontal=True, key="eco_imp")
    curs = c2.multiselect("Devises", ["USD", "EUR", "GBP", "JPY", "CNY", "CHF", "CAD", "AUD", "NZD"], default=["USD", "EUR", "GBP", "JPY"], key="eco_cur")
    eco_table(imp, tuple(curs))


# =====================================================================
#  COURBE DES TAUX
# =====================================================================
@frag(300)
def render_curve():
    us, ts = sget("us_curve", fetch_us_curve, 1800, wait_first=15)
    eur, ts2 = sget("eur_curve", fetch_eur_curve, 1800, wait_first=10)
    hero("Obligataire", "Courbe des taux", "Trésor américain (FRED) et zone euro (BCE, émetteurs AAA) · séries officielles quotidiennes",
         fresh(max(ts or 0, ts2 or 0)))
    if us is None and eur is None:
        st.markdown('<div class="empty">Les sources officielles (FRED, BCE) ne répondent pas pour le moment. La page se rechargera automatiquement.</div>', unsafe_allow_html=True)
        return
    if us is not None:
        c = us.ffill()
        asof = c.index[-1]
        now_row = c.iloc[-1]

        def at(days):
            sub = c.loc[:asof - pd.Timedelta(days=days)]
            return sub.iloc[-1] if len(sub) else None
        r1m, r1y = at(30), at(365)
        labels = [k for k, s in FRED_CURVE.items() if s in c.columns]

        def sp(a, b):
            try:
                v = (float(now_row[a]) - float(now_row[b])) * 100
                return None if pd.isna(v) else v
            except Exception:
                return None
        s2, s3m, s5 = sp("DGS10", "DGS2"), sp("DGS10", "DGS3MO"), sp("DGS30", "DGS5")
        tiles = []
        for lab_, v in (("2 ans / 10 ans", s2), ("3 mois / 10 ans", s3m), ("5 ans / 30 ans", s5)):
            if v is not None:
                tiles.append(f'<div class="sgt"><span>Pente {lab_}</span><b class="{"dn" if v < 0 else "up"}">{sgn(v, 0, " pb")}</b></div>')
        if "DGS10" in now_row and pd.notna(now_row["DGS10"]):
            tiles.append(f'<div class="sgt"><span>Taux 10 ans US</span><b>{fnum(float(now_row["DGS10"]), 2)} %</b></div>')
        sec("Courbe des taux américaine", f"Rendement par échéance · données du {asof:%d/%m/%Y}")
        if tiles:
            st.markdown('<div class="sg">' + "".join(tiles) + '</div>', unsafe_allow_html=True)
        fig = go.Figure()
        for lab_, row, clr, dash in (("Aujourd'hui", now_row, A1, "solid"), ("Il y a 1 mois", r1m, A2, "dot"), ("Il y a 1 an", r1y, "#8E9099", "dot")):
            if row is None:
                continue
            ys = [row[FRED_CURVE[k]] for k in labels]
            fig.add_trace(go.Scatter(x=labels, y=ys, name=lab_, mode="lines+markers", line=dict(color=clr, width=2.6 if dash == "solid" else 1.6, dash=dash),
                                     marker=dict(size=6, symbol="square"), hovertemplate="%{x} · <b>%{y:.2f} %</b><extra>" + lab_ + "</extra>"))
        fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified", legend=dict(orientation="h", y=1.12, x=0),
                          yaxis=dict(ticksuffix=" %"), xaxis=dict(title="Échéance"))
        show(fig, key="curve_us")
        if "DGS10" in c.columns and "DGS2" in c.columns:
            sec("Pente 2 ans / 10 ans", "En points de base : sous zéro, la courbe est inversée (signal historique de récession)")
            h = ((c["DGS10"] - c["DGS2"]) * 100).dropna().tail(520)
            fig2 = go.Figure(go.Scatter(x=h.index, y=h.values, mode="lines", line=dict(color=A1, width=2), fill="tozeroy", fillcolor=hex_rgba(A1, .08),
                                        hovertemplate="%{x|%d %b %Y} · <b>%{y:.0f} pb</b><extra></extra>"))
            if "DGS3MO" in c.columns:
                h3 = ((c["DGS10"] - c["DGS3MO"]) * 100).dropna().tail(520)
                fig2.add_trace(go.Scatter(x=h3.index, y=h3.values, mode="lines", name="3 mois / 10 ans", line=dict(color=A2, width=1.4, dash="dot"),
                                          hovertemplate="%{x|%d %b %Y} · <b>%{y:.0f} pb</b><extra>3m/10a</extra>"))
            fig2.add_hline(y=0, line=dict(color=DN, width=1, dash="dash"))
            fig2.update_layout(height=280, margin=dict(l=0, r=0, t=6, b=0), showlegend=False, hovermode="x unified", yaxis=dict(ticksuffix=" pb"))
            show(fig2, key="curve_hist")
        notes = []
        if s2 is not None:
            notes.append(f"**2s10s** : {sgn(s2, 0, ' pb')} · courbe {'inversée (taux courts supérieurs aux taux longs)' if s2 < 0 else 'normale (pentue)'}.")
        if s3m is not None:
            notes.append(f"**3m10y** : {sgn(s3m, 0, ' pb')} · {'inversion : le marché anticipe des baisses de taux' if s3m < 0 else 'pas d inversion sur cette pente, la plus suivie par la Fed'}.")
        if r1m is not None and "DGS10" in now_row and "DGS10" in r1m:
            notes.append(f"**10 ans US** : {sgn((float(now_row['DGS10']) - float(r1m['DGS10'])) * 100, 0, ' pb')} sur un mois.")
        if notes:
            st.markdown("\n".join(f"- {n}" for n in notes))
    if eur is not None:
        e = eur.ffill()
        asof = e.index[-1]
        sub = e.loc[:asof - pd.Timedelta(days=30)]
        rm = sub.iloc[-1] if len(sub) else None
        lab_e = [k for k, s in EUR_CURVE.items() if s in e.columns]
        sec("Courbe de la zone euro", f"Courbe zéro-coupon BCE, émetteurs notés AAA · données du {asof:%d/%m/%Y}")
        fig3 = go.Figure()
        for lab_, row, clr, dash in (("Aujourd'hui", e.iloc[-1], A1, "solid"), ("Il y a 1 mois", rm, A2, "dot")):
            if row is None:
                continue
            fig3.add_trace(go.Scatter(x=lab_e, y=[row[EUR_CURVE[k]] for k in lab_e], name=lab_, mode="lines+markers",
                                      line=dict(color=clr, width=2.6 if dash == "solid" else 1.6, dash=dash), marker=dict(size=6, symbol="square"),
                                      hovertemplate="%{x} · <b>%{y:.2f} %</b><extra>" + lab_ + "</extra>"))
        fig3.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified", legend=dict(orientation="h", y=1.14, x=0),
                           yaxis=dict(ticksuffix=" %"), xaxis=dict(title="Échéance"))
        show(fig3, key="curve_eur")
    st.markdown('<div class="note">Sources : FRED (Réserve fédérale de Saint-Louis) et Banque centrale européenne. Les rendements américains sont publiés le jour ouvré suivant.</div>',
                unsafe_allow_html=True)


# =====================================================================
#  COMPARATEUR (base 100, performance, corrélations)
# =====================================================================
@frag(300)
def cmp_chart(tickers, per, mode):
    period, interval = PERIODS[per]
    df, ts, _ = HUB.swr.get(("hist", tickers, per), fetch_hist_close, 300, args=(tickers, period, interval), wait_first=25, label="Comparateur")
    if df is None or df.empty:
        st.markdown('<div class="empty">Historique momentanément indisponible : nouvel essai automatique.</div>', unsafe_allow_html=True)
        return
    df = df.sort_index().ffill().dropna(axis=1, how="all").dropna(how="all")
    names = {t: LABEL_OF.get(t, t) for t in df.columns}
    base = df.apply(lambda s: s / s.dropna().iloc[0] * 100)
    shown = base - 100 if mode == "Performance %" else base
    fig = go.Figure()
    for t in shown.columns:
        fig.add_trace(go.Scatter(x=shown.index, y=shown[t], name=names[t], mode="lines", line=dict(width=2),
                                 hovertemplate="%{x|%d %b %Y} · <b>%{y:.1f}</b><extra>" + names[t] + "</extra>"))
    if mode == "Base 100":
        fig.add_hline(y=100, line=dict(color="#343841", width=1, dash="dot"))
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0),
                      yaxis=dict(ticksuffix=" %" if mode == "Performance %" else ""))
    show(fig, key="cmp_main")
    ann = {"1d": 252, "1wk": 52}.get(interval, 252)
    rows = []
    for t in df.columns:
        s = df[t].dropna()
        perf = (s.iloc[-1] / s.iloc[0] - 1) * 100
        vol = s.pct_change().std() * (ann ** .5) * 100
        dd = (s / s.cummax() - 1).min() * 100
        rows.append([names[t], f'<span class="{"up" if perf >= 0 else "dn"}">{sgn(perf, 1, " %")}</span>',
                     f'{vol:.1f} %'.replace(".", ","), f'{dd:.1f} %'.replace(".", ",")])
    sec("Statistiques", f"Sur la période {per}")
    st.markdown(table(["Instrument", "Performance", "Volatilité annualisée", "Plus forte baisse"], rows), unsafe_allow_html=True)
    if df.shape[1] >= 2:
        rets = df.pct_change().dropna(how="all")
        corr = rets.corr()
        labs = [names[t] for t in corr.columns]
        z = corr.values.tolist()
        fig2 = go.Figure(go.Heatmap(z=z, x=labs, y=labs, zmin=-1, zmax=1, colorscale=[[0, DN], [0.5, "#171A1F"], [1, UP]],
                                    text=[[f"{v:.2f}" for v in row] for row in z], texttemplate="%{text}", showscale=False,
                                    hovertemplate="%{y} / %{x} : <b>%{z:.2f}</b><extra></extra>"))
        fig2.update_layout(height=max(320, 70 * len(labs)), margin=dict(l=0, r=0, t=10, b=0), yaxis=dict(autorange="reversed"))
        sec("Corrélations", "Rendements quotidiens (ou hebdomadaires sur 5 ans) : +1 évoluent ensemble, −1 en sens opposé")
        show(fig2, key="cmp_corr")
    st.markdown(f'<div class="note">{fresh(ts)} · Source : Yahoo Finance.</div>', unsafe_allow_html=True)


@guarded
def render_compare():
    hero("Analyse", "Comparateur", "Comparez jusqu'à 8 instruments : performance en base 100, statistiques de risque et corrélations")
    c1, c2, c3 = st.columns([4, 3, 3])
    default = ["S&P 500 (US)", "Or (Valeur Refuge)", "US 10 ans", "Bitcoin (BTC)"]
    sel = c1.multiselect("Instruments (jusqu'à 8)", list(ALL_ASSETS), default=default, max_selections=8, key="cmp_sel")
    per = c2.radio("Période", ["1M", "3M", "6M", "1A", "5A"], index=2, horizontal=True, key="cmp_per")
    mode = c3.radio("Affichage", ["Base 100", "Performance %"], horizontal=True, key="cmp_mode")
    if len(sel) < 2:
        st.markdown('<div class="empty">Sélectionnez au moins deux instruments pour lancer la comparaison.</div>', unsafe_allow_html=True)
        return
    cmp_chart(tuple(ALL_ASSETS[n] for n in sel), per, mode)


# =====================================================================
#  WATCHLIST (mémorisée dans l'adresse de la page)
# =====================================================================
WL_DEFAULT = ["^FCHI", "^GSPC", "EURUSD=X", "GC=F", "BZ=F", "BTC-USD", "^TNX"]


@frag(30)
def watch_cards(tks):
    data, ts, _ = px(tks)
    items = [(LABEL_OF[t], t, data[t]) for t in tks if t in data and len(data[t]) >= 2]
    st.markdown(f'<div class="pills" style="justify-content:flex-start;margin-bottom:10px">{fresh(ts)}</div>', unsafe_allow_html=True)
    if not items:
        st.markdown('<div class="empty">Cotations momentanément indisponibles : nouvel essai automatique.</div>', unsafe_allow_html=True)
        return
    cards_grid(items, "Watchlist", "w")


@guarded
def render_watchlist():
    hero("Terminal", "Watchlist", "Vos instruments, en direct · l'adresse de la page mémorise votre sélection : ajoutez-la à vos favoris")
    if "wl_sel" not in st.session_state:
        qp = st.query_params.get("wl", "")
        tks = [t for t in str(qp).split(",") if t in LABEL_OF] or WL_DEFAULT
        st.session_state["wl_sel"] = [LABEL_OF[t] for t in tks]
    sel = st.multiselect("Instruments suivis", list(ALL_ASSETS), key="wl_sel", max_selections=24)
    tks = tuple(ALL_ASSETS[n] for n in sel)
    st.query_params["wl"] = ",".join(tks)
    if not tks:
        st.markdown('<div class="empty">Ajoutez des instruments avec le sélecteur ci-dessus.</div>', unsafe_allow_html=True)
        return
    watch_cards(tks)


# =====================================================================
#  BANQUES CENTRALES : tout est lu en ligne (FRED, BCE, BoE, BRI, Eurostat) ; les valeurs de référence ne servent que de secours
# =====================================================================
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
QUICK_ALL = [("CAC 40", "^FCHI"), ("S&P 500", "^GSPC"), ("EUR/USD", "EURUSD=X"), ("USD/JPY", "USDJPY=X"), ("Or", "GC=F"), ("Brent", "BZ=F"), ("Bitcoin", "BTC-USD"), ("US 10Y", "^TNX")]


def fr_range(a_, b_):
    a_, b_ = date.fromisoformat(a_), date.fromisoformat(b_)
    if a_ == b_:
        return f"{a_.day} {MOIS[a_.month - 1]} {a_.year}"
    return f"{a_.day}-{b_.day} {MOIS[b_.month - 1]} {b_.year}" if a_.month == b_.month else f"{a_.day} {MOIS[a_.month - 1]} - {b_.day} {MOIS[b_.month - 1]} {b_.year}"


def upcoming(bank, today, n=1):
    return [m for m in MEETINGS[bank] if date.fromisoformat(m[1]) >= today][:n]


@frag(600)
def render_bc():
    today = datetime.now(PARIS).date()
    live, _ = sget("cb", fetch_cb, 3600, wait_first=15)
    mac, _ = sget("macro", fetch_macro, 3600, wait_first=15)
    live, mac = live or {}, mac or {}
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
        nxt = f"Prochaine : {fr_range(*nm[0])}" if nm else "Prochaine : voir le calendrier officiel"
        with col:
            st.markdown(f'<a class="lk" href="{m["url"]}" target="_blank" rel="noopener">' + kc(f'{k_} · {m["zone"]}', pc(lo, hi),
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
        sp_ = (mac["fr10"][0] - mac["de10"][0]) * 100
        notes.append(f"**France** : l'OAT 10 ans rapporte {mac['fr10'][0]:.2f} % contre {mac['de10'][0]:.2f} % pour le Bund, un spread de {sp_:.0f} pb ({'prime de risque élevée' if sp_ > 75 else 'prime de risque modérée'}).")
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
    data, _, _ = px(HEAT_T, wait_first=8)
    cells = ""
    for n_, t in QUICK_ALL:
        if t in data and len(data[t]) >= 2:
            i_ = chg_info(t, data[t])
            cells += f'<div class="sgt"><span>{n_}</span><b class="{i_["cls"]}">{fnum(i_["curr"], dec_of(t, i_["curr"]))} · {i_["txt"]}</b></div>'
    if cells:
        st.markdown('<div class="sg" style="grid-template-columns:repeat(4,1fr)">' + cells + '</div>', unsafe_allow_html=True)

    sec("Dernières actualités banques centrales", "Sélectionnées automatiquement dans le flux CNBC · titre d'origine et traduction")
    raw, _ = sget("news", fetch_news, 600, wait_first=10)
    if raw:
        cbn = []
        for n in raw:
            n = dict(n)
            n["score"], n["tag"] = score(n)
            if n["tag"] == "Banques centrales":
                cbn.append(n)
        cbn = sorted(cbn, key=lambda n: n["ts"], reverse=True)[:5]
        titles = tuple(n["title"] for n in cbn)
        res = None
        if titles:
            res, _ = sget(("tr", titles), tr_batch, 86400, args=(titles,), wait_first=10, label="Traduction")
        res = res or [""] * len(cbn)
        rows_h = "".join(f'<a class="fl" style="--c:#C9A86A" href="{html.escape(n["link"])}" target="_blank" rel="noopener"><span class="tm">{fmt(n["ts"])}</span>'
                         f'<div><div class="en" style="font-weight:600;font-size:.9rem">{html.escape(n["title"])}</div><div class="fr">{html.escape(r_)}</div></div>'
                         f'<span class="tag">Banques centrales</span></a>' for n, r_ in zip(cbn, res))
        st.markdown(f'<div class="tp">{rows_h or "<div class=fr style=padding:16px>Aucune actualité récente.</div>"}</div>', unsafe_allow_html=True)
    else:
        st.caption("Flux d'actualités momentanément indisponible.")

    sec("Prochaines réunions", "Calendrier officiel intégré : les dates passées disparaissent toutes seules")
    rows_ = sorted((m_[1], k_, m_) for k_ in CB for m_ in upcoming(k_, today, 2))
    st.markdown(table(["Date", "Banque", "Dans", "Calendrier officiel"], [
        [fr_range(*m_), f'<b style="color:{CB[k_]["c"]}">{k_}</b>', f"{(date.fromisoformat(e_) - today).days} j", f'<a href="{CB[k_]["cal"]}" target="_blank" rel="noopener">Voir ↗</a>']
        for e_, k_, m_ in rows_[:8]]), unsafe_allow_html=True)
    if any(not upcoming(k_, today) for k_ in CB):
        st.markdown('<div class="note">Les dates de certaines banques ne sont pas encore intégrées au terminal : consultez leur calendrier officiel (liens ci-dessus).</div>', unsafe_allow_html=True)
    with st.expander("Et la France ? Banque de France et taux"):
        st.markdown("- Les **taux directeurs en France sont ceux de la BCE** : la Banque de France fait partie de l'Eurosystème et son gouverneur siège au Conseil des gouverneurs.\n"
                    "- La Banque de France publie les **taux d'usure** (plafond légal des crédits) et son gouverneur donne un avis sur le **taux du Livret A**, fixé par l'État.\n"
                    "- Le coût de la dette française se lit dans le **taux de l'OAT 10 ans** et son écart avec le Bund allemand.")


# =====================================================================
#  CALENDRIER DES PLACES BOURSIÈRES
# =====================================================================
@frag(60)
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
                      font=dict(family="IBM Plex Sans", color="#CFCBC2"),
                      xaxis=dict(range=[0, 24], tickvals=list(range(0, 25, 2)), ticktext=[f"{h:02d}h" for h in range(0, 25, 2)], gridcolor="rgba(255,255,255,.06)"),
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


# =====================================================================
#  BASE DE CONNAISSANCES
# =====================================================================
@guarded
def render_kb():
    hero("Repères institutionnels", "Base de Connaissances", "France, marchés, taux, économies, matières premières et glossaire de salle de marché",
         '<span class="pill">Ordres de grandeur 2025-2026 · crypto et PIB actualisés en ligne</span>')
    C_, _ = sget("crypto", fetch_crypto, 1800, wait_first=8)
    G_, _ = sget("gdp", fetch_gdp, 86400, wait_first=10)
    C_, G_ = C_ or {}, G_ or {}
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
        caps, _ = sget("caps", fetch_caps, 1800, wait_first=45)
        caps = caps or []
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
            st.markdown('<div class="kc"><h4>Total crypto-marché</h4><div class="big">' + CRY_TXT + '</div></div>', unsafe_allow_html=True)
            show(gauge(round(C_["btc"], 1) if C_ else 52.5, "Dominance du Bitcoin", color="#E3A33B"), key="btc_dom")
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
            st.markdown('<div class="kc"><h4>Top 10 · PIB nominal (Mds $, ordres de grandeur)</h4></div>', unsafe_allow_html=True)
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


# =====================================================================
#  NAVIGATION & BARRE LATÉRALE
# =====================================================================
P_OVERVIEW, P_WATCH = "🧭 Vue d'ensemble", "⭐ Watchlist"
P_CURVE, P_ECO, P_BC = "📈 Courbe des taux", "🗓️ Calendrier économique", "🏦 Banques Centrales"
P_NEWS, P_CMP, P_MKT, P_KB = "📰 Actualités Macro (FR)", "🔀 Comparateur", "🕐 Calendrier des Marchés", "📚 Base de Connaissances"
_k = list(UNIVERSE.keys())
NAV = [("Terminal", [P_OVERVIEW, P_WATCH]),
       ("Marchés", _k[0:4] + _k[6:8]),
       ("Actions", _k[4:6]),
       ("Macro", [P_CURVE, P_ECO, P_BC, P_NEWS, P_CMP, P_MKT]),
       ("Référence", [P_KB])]
options = [o for _, g in NAV for o in g]
ICON_BY_PAGE = {P_OVERVIEW: ICON_PATHS["overview"], P_WATCH: ICON_PATHS["watch"], _k[0]: ICON_PATHS["rates"], _k[1]: ICON_PATHS["indices"],
                _k[2]: ICON_PATHS["fx"], _k[3]: ICON_PATHS["commo"], _k[4]: ICON_PATHS["stocks"], _k[5]: ICON_PATHS["france"],
                _k[6]: ICON_PATHS["crypto"], _k[7]: ICON_PATHS["vol"], P_CURVE: ICON_PATHS["curve"], P_ECO: ICON_PATHS["eco"],
                P_BC: ICON_PATHS["bank"], P_NEWS: ICON_PATHS["news"], P_CMP: ICON_PATHS["compare"], P_MKT: ICON_PATHS["clock"], P_KB: ICON_PATHS["book"]}


def _slug(s):
    s = unicodedata.normalize("NFKD", clean_label(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


SLUGS = {p: _slug(p) for p in options}
BY_SLUG = {v: k for k, v in SLUGS.items()}

st.sidebar.markdown(
    '<div class="brand"><div class="brand-mark"></div><div><div class="brand-t">Macro Terminal</div>'
    '<div class="brand-s">Marchés mondiaux · Paris</div></div></div>'
    f'<div class="live"><i></i>{datetime.now(PARIS):%H:%M} · Paris</div>', unsafe_allow_html=True)
st.markdown(icon_css(NAV, ICON_BY_PAGE), unsafe_allow_html=True)

if "page" not in st.session_state:  # lien direct : ?p=courbe-des-taux
    st.session_state["page"] = BY_SLUG.get(str(st.query_params.get("p", "")), options[0])
elif st.session_state["page"] not in options:
    st.session_state["page"] = options[0]


def _go(gi):
    st.session_state["page"] = st.session_state[f"nav_{gi}"]


for gi, (gname, items) in enumerate(NAV):
    st.sidebar.markdown(f'<div class="navlab">{gname}</div>', unsafe_allow_html=True)
    st.session_state[f"nav_{gi}"] = st.session_state["page"] if st.session_state["page"] in items else None
    st.sidebar.radio(gname, items, index=None, key=f"nav_{gi}", format_func=clean_label, label_visibility="collapsed", on_change=_go, args=(gi,))
category = st.session_state["page"]
if st.query_params.get("p") != SLUGS[category]:
    st.query_params["p"] = SLUGS[category]


@frag(30)
def sidebar_panel():
    data, _, _ = px(HEAT_T, wait_first=20)
    rows = ""
    for name, t in QUICK_ALL:
        sr = data.get(t)
        if sr is not None and len(sr) >= 2:
            i_ = chg_info(t, sr)
            rows += (f'<div class="qk"><b>{name}</b><span>{fnum(i_["curr"], dec_of(t, i_["curr"]))}</span>'
                     f'<span class="{i_["cls"]}">{i_["txt"]}</span></div>')
    st.markdown('<div class="sbh">Aperçu des marchés</div>' + (rows or '<div class="qk"><b>Données en cours de chargement…</b></div>'), unsafe_allow_html=True)
    today_ = datetime.now(PARIS).date()
    nx = sorted((m[1], b_, m) for b_ in CB for m in upcoming(b_, today_))[:3]
    if nx:
        st.markdown('<div class="sbh">Prochaines réunions</div>' + "".join(
            f'<div class="qk"><b style="color:{CB[b_]["c"]}">{b_}</b><span>{fr_range(*m)}</span><span>{(date.fromisoformat(e_) - today_).days} j</span></div>'
            for e_, b_, m in nx), unsafe_allow_html=True)


with st.sidebar:
    sidebar_panel()

st.sidebar.markdown('<div class="hint">Données : Yahoo Finance (différé jusqu’à 15 min selon les places), FRED, BCE, Eurostat, BRI, Fair Economy.<br>'
                    'Touches 1 à 9 : navigation rapide.<br>Informations à but pédagogique, pas un conseil en investissement.</div>', unsafe_allow_html=True)


def health_panel():
    """État des sources de données : utile pour diagnostiquer sans ouvrir les journaux."""
    rows = HUB.swr.stats()
    now = time.time()
    yfv = getattr(yf, "__version__", "?") if yf else "absent"
    up = int(now - HUB.t0)
    with st.sidebar.expander("Santé du système"):
        lines = [f"Streamlit {st.__version__} · Python {platform.python_version()} · pandas {pd.__version__} · yfinance {yfv}",
                 f"Serveur actif depuis {up // 3600} h {up % 3600 // 60:02d} min"]
        for label, ts, err, n, running in sorted(rows, key=lambda r: r[0]):
            if ts:
                age = int(now - ts)
                st_ = f"ok, il y a {age} s" if age < 3600 else f"ok, il y a {age // 3600} h"
            else:
                st_ = "pas encore de donnée"
            if err:
                st_ += f" · dernière erreur : {err}"
            if running:
                st_ += " · mise à jour…"
            lines.append(f"- **{label}** : {st_}")
        st.markdown("\n".join(lines))


health_panel()

# =====================================================================
#  AFFICHAGE
# =====================================================================
market_strip()

PAGES = {P_OVERVIEW: render_overview, P_WATCH: render_watchlist, P_CURVE: render_curve, P_ECO: render_eco, P_BC: render_bc,
         P_NEWS: render_news, P_CMP: render_compare, P_MKT: render_cal, P_KB: render_kb}
for _c in UNIVERSE:
    PAGES[_c] = functools.partial(render_market, _c)

PAGES[category]()

# Fenêtre d'analyse détaillée : ouverte ici (hors fragment) pour rester affichée pendant les rafraîchissements automatiques
_detail = st.session_state.pop("detail", None)
if _detail:
    try:
        detail_dialog(*_detail)
    except Exception:
        log.error("fenêtre de détail :\n%s", traceback.format_exc())
        st.error("Impossible d'ouvrir le détail de cet instrument pour le moment.")
