import os
import time
from datetime import datetime, timezone

import feedparser
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="Sri Lanka & Global Market Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# Configuration
# -----------------------------

CSE_LINKS = {
    "CSE Trade Summary": "https://www.cse.lk/equity/trade-summary",
    "GICS Industry Group Summary": (
        "https://www.cse.lk/equity/gics-industry-group-summary"
    ),
    "CSE Official Announcements": "https://www.cse.lk/announcements",
    "CSE Debt Market": "https://www.cse.lk/debt/debt-market?page=debt",
    "CSE Advanced Charts": "https://www.cse.lk/equity/advanced-charts",
    "CSE Daily Publications": "https://www.cse.lk/publications/cse-daily",
    "CSE Annual Statistics": "https://www.cse.lk/equity/annual-trading-statistics",
}

MACRO_LINKS = {
    "CBSL Daily Economic Indicators": (
        "https://www.cbsl.gov.lk/en/statistics/economic-indicators/daily-indicators"
    ),
    "CBSL Treasury Bills & Bonds": (
        "https://www.cbsl.lk/eResearch/Modules/RD/SearchPages/Search_Criteria.aspx"
    ),
    "OEC Sri Lanka Trade Data": "https://oec.world/en/profile/country/lka",
}

GLOBAL_LINKS = {
    "CNN Premarket & World Map": "https://edition.cnn.com/markets/premarkets#world-map",
    "TradingEconomics Commodities": "https://tradingeconomics.com/commodities",
    "Investing.com Screener": "https://www.investing.com/stock-screener",
}

RSS_FEEDS = {
    "Global markets": (
        "https://news.google.com/rss/search?q=global+markets+stocks+economy"
        "&hl=en-US&gl=US&ceid=US:en"
    ),
    "Sri Lanka markets": (
        "https://news.google.com/rss/search?q=Sri+Lanka+CSE+stock+market+economy"
        "&hl=en-US&gl=US&ceid=US:en"
    ),
    "Geopolitics": (
        "https://news.google.com/rss/search?q=geopolitics+war+markets+economy"
        "&hl=en-US&gl=US&ceid=US:en"
    ),
}

GLOBAL_SYMBOLS = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow Jones": "^DJI",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Shanghai Composite": "000001.SS",
    "Nifty 50": "^NSEI",
    "US 10Y Yield": "^TNX",
    "VIX": "^VIX",
    "US Dollar Index": "DX-Y.NYB",
    "Brent Crude": "BZ=F",
    "Gold": "GC=F",
}

DEFAULT_WATCHLIST = [
    "COMB.N0000",
    "JKH.N0000",
    "HNB.N0000",
    "SAMP.N0000",
    "LOLC.N0000",
]


# -----------------------------
# Utility functions
# -----------------------------

def fmt_number(value, decimals=2):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}"


def pct_change(current, previous):
    if current is None or previous in (None, 0) or pd.isna(current):
        return np.nan
    return ((current / previous) - 1) * 100


def change_color(value):
    if pd.isna(value):
        return "neutral"
    return "positive" if value > 0 else "negative" if value < 0 else "neutral"


def metric_card(label, value, change=None, suffix=""):
    if change is None or pd.isna(change):
        delta = "N/A"
    else:
        delta = f"{change:+.2f}%"
    st.metric(label, f"{value}{suffix}", delta)


def render_links(links):
    cols = st.columns(min(4, max(1, len(links))))
    for index, (label, url) in enumerate(links.items()):
        with cols[index % len(cols)]:
            st.link_button(label, url, use_container_width=True)


# -----------------------------
# Market-data functions
# -----------------------------

@st.cache_data(ttl=300, show_spinner=False)
def download_yahoo(symbols, period="1y", interval="1d"):
    symbols = list(symbols)
    try:
        data = yf.download(
            tickers=symbols,
            period=period,
            interval=interval,
            auto_adjust=False,
            group_by="ticker",
            progress=False,
            threads=True,
        )
        return data
    except Exception:
        return pd.DataFrame()


def yahoo_history(symbol, period="1y", interval="1d"):
    data = download_yahoo((symbol,), period, interval)
    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        try:
            data = data[symbol]
        except KeyError:
            data.columns = data.columns.get_level_values(-1)

    data = data.dropna(how="all").copy()
    data.index = pd.to_datetime(data.index)
    return data


def latest_yahoo_quote(symbol):
    history = yahoo_history(symbol, period="5d", interval="1d")
    if history.empty or "Close" not in history:
        return None, None

    close = history["Close"].dropna()
    if len(close) == 0:
        return None, None

    current = float(close.iloc[-1])
    previous = float(close.iloc[-2]) if len(close) > 1 else None
    return current, pct_change(current, previous)


def make_candlestick(history, title):
    if history.empty:
        return go.Figure()

    figure = go.Figure(
        data=[
            go.Candlestick(
                x=history.index,
                open=history["Open"],
                high=history["High"],
                low=history["Low"],
                close=history["Close"],
                name=title,
            )
        ]
    )
    figure.update_layout(
        title=title,
        height=430,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis_rangeslider_visible=False,
    )
    return figure


@st.cache_data(ttl=300, show_spinner=False)
def get_cse_summary():
    """
    CSE endpoints are not guaranteed public APIs and may change.
    Keep this function isolated so it can be updated without changing the UI.
    """
    endpoint_candidates = [
        "https://www.cse.lk/api/marketSummery",
        "https://www.cse.lk/api/dailyMarketSummery",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for endpoint in endpoint_candidates:
        try:
            response = requests.post(
                endpoint,
                json={},
                headers=headers,
                timeout=15,
            )
            if response.ok:
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
        except Exception:
            continue

    return {}


@st.cache_data(ttl=900, show_spinner=False)
def get_cse_sectors():
    """
    Placeholder adapter for the CSE sector endpoint.
    The endpoint may require a request body or session headers.
    Return an empty frame rather than breaking the complete dashboard.
    """
    candidates = [
        "https://www.cse.lk/api/gicsIndustryGroupSummary",
        "https://www.cse.lk/api/sectorPerformance",
    ]

    for endpoint in candidates:
        try:
            response = requests.post(
                endpoint,
                json={},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            if response.ok:
                payload = response.json()
                if isinstance(payload, list):
                    return pd.DataFrame(payload)
                if isinstance(payload, dict):
                    for key in ("data", "content", "result"):
                        if isinstance(payload.get(key), list):
                            return pd.DataFrame(payload[key])
        except Exception:
            continue

    return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def get_news(feed_url, limit=8):
    try:
        feed = feedparser.parse(feed_url)
        rows = []
        for entry in feed.entries[:limit]:
            published = entry.get("published", "")
            rows.append(
                {
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", "#"),
                    "published": published,
                    "source": entry.get("source", {}).get("title", ""),
                }
            )
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def render_news(feed_name, feed_url):
    news = get_news(feed_url)
    if news.empty:
        st.info("No news items were returned.")
        return

    for _, row in news.iterrows():
        st.markdown(
            f"**[{row['title']}]({row['link']})**  \n"
            f"{row['source']} · {row['published']}"
        )
        st.divider()


# -----------------------------
# Sidebar
# -----------------------------

with st.sidebar:
    st.header("Dashboard controls")

    auto_refresh = st.checkbox("Auto-refresh", value=False)
    refresh_seconds = st.slider(
        "Refresh interval",
        min_value=60,
        max_value=1800,
        value=300,
        step=60,
        disabled=not auto_refresh,
    )

    period = st.selectbox(
        "Chart history",
        ["1mo", "3mo", "6mo", "1y", "2y"],
        index=3,
    )

    st.caption(
        "Free data may be delayed and can be subject to rate limits. "
        "Verify important figures using official exchange sources."
    )

    st.subheader("Sri Lankan watchlist")
    watchlist_text = st.text_area(
        "CSE symbols, one per line",
        value="\n".join(DEFAULT_WATCHLIST),
        height=160,
    )
    watchlist = [
        symbol.strip()
        for symbol in watchlist_text.splitlines()
        if symbol.strip()
    ]

    st.subheader("Official source hubs")
    render_links(CSE_LINKS)
    render_links(MACRO_LINKS)
    render_links(GLOBAL_LINKS)


if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()


# -----------------------------
# Header
# -----------------------------

now = datetime.now(timezone.utc).astimezone()
st.title("📈 Sri Lanka & Global Equity Morning Dashboard")
st.caption(
    f"Last application refresh: {now.strftime('%Y-%m-%d %H:%M:%S %Z')} "
    "· Prices may be delayed"
)


# -----------------------------
# Top market cards
# -----------------------------

st.header("Market overview")

top_symbols = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Gold": "GC=F",
    "Brent Crude": "BZ=F",
}

cols = st.columns(len(top_symbols))
for col, (name, symbol) in zip(cols, top_symbols.items()):
    value, change = latest_yahoo_quote(symbol)
    with col:
        metric_card(name, fmt_number(value), change, "")


# -----------------------------
# CSE section
# -----------------------------

st.header("🇱🇰 CSE direct hub")

cse_summary = get_cse_summary()

cse_aspi = None
cse_sl20 = None
cse_turnover = None
cse_volume = None
cse_trades = None

if cse_summary:
    cse_aspi = cse_summary.get("aspi") or cse_summary.get("ASPI")
    cse_sl20 = cse_summary.get("sl20") or cse_summary.get("SL20")
    cse_turnover = (
        cse_summary.get("turnover")
        or cse_summary.get("tradeTurnover")
        or cse_summary.get("totalTurnover")
    )
    cse_volume = (
        cse_summary.get("volume")
        or cse_summary.get("tradeVolume")
        or cse_summary.get("shareVolume")
    )
    cse_trades = cse_summary.get("trades") or cse_summary.get("numberOfTrades")

cse_cols = st.columns(5)
with cse_cols[0]:
    metric_card("ASPI", fmt_number(cse_aspi))
with cse_cols[1]:
    metric_card("S&P SL20", fmt_number(cse_sl20))
with cse_cols[2]:
    metric_card("Turnover", fmt_number(cse_turnover))
with cse_cols[3]:
    metric_card("Share volume", fmt_number(cse_volume))
with cse_cols[4]:
    metric_card("Trades", fmt_number(cse_trades))

if not cse_summary:
    st.warning(
        "CSE summary data was not returned. The CSE adapter is isolated in "
        "`get_cse_summary()` because the public endpoint format can change."
    )

st.subheader("CSE market resources")
render_links(CSE_LINKS)

sector_data = get_cse_sectors()
if not sector_data.empty:
    st.subheader("GICS industry-group performance")
    st.dataframe(sector_data, use_container_width=True, hide_index=True)
else:
    st.info(
        "Sector data was not returned by the adapter. Until the exact CSE "
        "request format is confirmed, use the official GICS link above."
    )


# -----------------------------
# Charts
# -----------------------------

st.header("Interactive market charts")

chart_left, chart_right = st.columns(2)

with chart_left:
    global_chart_name = st.selectbox(
        "Global chart",
        list(GLOBAL_SYMBOLS.keys()),
        index=0,
    )
    global_history = yahoo_history(
        GLOBAL_SYMBOLS[global_chart_name],
        period=period,
        interval="1d",
    )
    st.plotly_chart(
        make_candlestick(global_history, global_chart_name),
        use_container_width=True,
    )

with chart_right:
    watch_chart = st.selectbox(
        "Sri Lankan watchlist chart",
        watchlist if watchlist else DEFAULT_WATCHLIST,
    )
    cse_chart_history = yahoo_history(
        watch_chart,
        period=period,
        interval="1d",
    )
    if cse_chart_history.empty:
        st.info(
            "Yahoo Finance may not provide historical data for this CSE symbol. "
            "Add a licensed CSE data adapter if you need guaranteed CSE charts."
        )
    else:
        st.plotly_chart(
            make_candlestick(cse_chart_history, watch_chart),
            use_container_width=True,
        )


# -----------------------------
# Watchlist table
# -----------------------------

st.header("Sri Lankan watchlist")

watch_rows = []
for symbol in watchlist:
    value, change = latest_yahoo_quote(symbol)
    watch_rows.append(
        {
            "Symbol": symbol,
            "Latest": value,
            "Change %": change,
        }
    )

watch_df = pd.DataFrame(watch_rows)
if not watch_df.empty:
    st.dataframe(
        watch_df.style.format(
            {"Latest": "{:,.2f}", "Change %": "{:+.2f}%"},
            na_rep="N/A",
        ),
        use_container_width=True,
        hide_index=True,
    )


# -----------------------------
# Macro and commodities
# -----------------------------

st.header("🏛️ Macro, currencies and commodities")

macro_symbols = {
    "US 10Y Yield": "^TNX",
    "VIX": "^VIX",
    "US Dollar Index": "DX-Y.NYB",
    "Brent Crude": "BZ=F",
    "Gold": "GC=F",
}

macro_rows = []
for name, symbol in macro_symbols.items():
    value, change = latest_yahoo_quote(symbol)
    macro_rows.append(
        {
            "Indicator": name,
            "Latest": value,
            "Change %": change,
        }
    )

st.dataframe(
    pd.DataFrame(macro_rows).style.format(
        {"Latest": "{:,.2f}", "Change %": "{:+.2f}%"},
        na_rep="N/A",
    ),
    use_container_width=True,
    hide_index=True,
)

render_links(MACRO_LINKS)


# -----------------------------
# News
# -----------------------------

st.header("🧠 Morning intelligence")

news_tabs = st.tabs(list(RSS_FEEDS.keys()))
for tab, (name, url) in zip(news_tabs, RSS_FEEDS.items()):
    with tab:
        render_news(name, url)


# -----------------------------
# Footer
# -----------------------------

st.divider()
st.caption(
    "For information and monitoring only. Confirm market prices, corporate "
    "announcements, yields, and economic figures using official sources before "
    "making investment decisions."
)
