import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import feedparser
import pandas as pd
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Sri Lanka & Global Market Brief",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for modern card aesthetics
st.markdown("""
<style>
    .stMetric {
        background-color: #1E222D;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2A2E39;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #1E222D;
        border-radius: 6px;
        padding-left: 18px;
        padding-right: 18px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Morning Financial Command Center")
st.caption(f"Last updated: {datetime.now().strftime('%A, %d %B %Y')} | Personal Market Intelligence")

# --- TOP STATS BAR ---
st.subheader("🌐 Key World Indicators & Commodities")
col1, col2, col3, col4, col5 = st.columns(5)

@st.cache_data(ttl=300)
def get_global_market_data():
    try:
        tickers = yf.Tickers('CL=F GC=F ^GSPC ^IXIC ^N225 LKR=X')
        crude = tickers.tickers['CL=F'].fast_info.get('lastPrice', 0.0)
        gold = tickers.tickers['GC=F'].fast_info.get('lastPrice', 0.0)
        sp500 = tickers.tickers['^GSPC'].fast_info.get('lastPrice', 0.0)
        usd_lkr = tickers.tickers['LKR=X'].fast_info.get('lastPrice', 0.0)
        return crude, gold, sp500, usd_lkr
    except Exception:
        return 0.0, 0.0, 0.0, 0.0

crude, gold, sp500, usd_lkr = get_global_market_data()

with col1:
    st.metric("S&P 500 Index", f"{sp500:,.2f}")
with col2:
    st.metric("Crude Oil (WTI)", f"${crude:.2f} / bbl")
with col3:
    st.metric("Gold Price (USD)", f"${gold:,.2f} / oz")
with col4:
    st.metric("USD / LKR Rate", f"LKR {usd_lkr:,.2f}" if usd_lkr else "Check CBSL")
with col5:
    st.metric("CBSL Policy Rate", "8.50%", "Overnight")

st.divider()

# --- NAVIGATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🇱🇰 CSE & Sri Lanka Macro", 
    "🌎 Global Markets & Commodities", 
    "📰 War & World News", 
    "🔗 Source Links & Deep Dives"
])

# === TAB 1: CSE & SRI LANKA MACRO ===
with tab1:
    st.header("Colombo Stock Exchange (CSE) & Technical Analysis")
    
    # TradingView Advanced Chart Widget for ASPI
    tv_widget = """
    <div class="tradingview-widget-container" style="height:550px;width:100%;">
      <iframe src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_1&symbol=CSELK%3AASI&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=1e222d&theme=dark&style=1&timezone=Asia%2FColombo"
              width="100%" height="550" frameborder="0" allowtransparency="true" scrolling="no"></iframe>
    </div>
    """
    components.html(tv_widget, height=560)
    
    st.divider()
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.subheader("📌 CSE Direct Hub")
        st.markdown("""
        * **[CSE Trade Summary](https://www.cse.lk/equity/trade-summary)** - Today's volume, turnover, and traded equity.
        * **[GICS Industry Group Summary](https://www.cse.lk/equity/gics-industry-group-summary)** - Sector-wise performance.
        * **[CSE Official Announcements](https://www.cse.lk/announcements)** - Company disclosures & earnings releases.
        * **[CSE Debt Market](https://www.cse.lk/debt/debt-market?page=debt)** - Corporate debt & government securities.
        """)
    
    with col_l2:
        st.subheader("🏛️ CBSL & Economic Trends")
        st.markdown("""
        * **[CBSL Daily Economic Indicators](https://www.cbsl.gov.lk/en/statistics/economic-indicators/daily-indicators)** - Inflation (CCPI/NCPI), policy rates, and daily liquidity.
        * **[CBSL Treasury Bills & Bonds](https://www.cbsl.lk/eResearch/Modules/RD/SearchPages/Search_Criteria.aspx)** - Latest auction yields & yield curves.
        * **[OEC Sri Lanka Trade Data](https://oec.world/en/profile/country/lka)** - Trade balance, export, and import statistics.
        """)

# === TAB 2: GLOBAL MARKETS & COMMODITIES ===
with tab2:
    st.header("Global Indices & Commodity Trackers")
    
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.subheader("Major World Indices")
        indices_data = {
            "Market / Index": ["S&P 500 (US)", "Nasdaq 100 (US)", "Nikkei 225 (Japan)", "FTSE 100 (UK)", "Gold Futures", "Crude Oil"],
            "Ticker Symbol": ["^GSPC", "^IXIC", "^N225", "^FTSE", "GC=F", "CL=F"]
        }
        df_idx = pd.DataFrame(indices_data)
        
        live_prices = []
        for sym in df_idx["Ticker Symbol"]:
            try:
                p = yf.Ticker(sym).fast_info.get('lastPrice', 0)
                live_prices.append(f"{p:,.2f}" if p else "N/A")
            except Exception:
                live_prices.append("N/A")
                
        df_idx["Live Price"] = live_prices
        st.dataframe(df_idx[["Market / Index", "Live Price"]], use_container_width=True)
        
    with g_col2:
        st.subheader("Interactive Global Market Maps & Premarkets")
        st.markdown("""
        * **[CNN Premarket & World Map](https://edition.cnn.com/markets/premarkets#world-map)** - Pre-market sentiment across Asia, Europe, and US.
        * **[TradingEconomics Commodities Hub](https://tradingeconomics.com/commodities)** - Real-time Brent Crude, Natural Gas, Agricultural products.
        * **[Investing.com Global Stock Screener](https://www.investing.com/stock-screener)** - Global equity momentum trackers.
        """)

# === TAB 3: NEWS & GEOPOLITICS ===
with tab3:
    st.header("Morning Intelligence: Global News, War & Geopolitics")
    
    n_col1, n_col2 = st.columns(2)
    
    with n_col1:
        st.subheader("🌐 Global Business, Politics & War News")
        # Google News RSS for geopolitics and global markets
        geo_feed = feedparser.parse("https://news.google.com/rss/search?q=global+markets+war+politics&hl=en-US&gl=US&ceid=US:en")
        for entry in geo_feed.entries[:6]:
            st.markdown(f"**[{entry.title}]({entry.link})**")
            st.caption(f"Published: {entry.published}")
            st.write("---")

    with n_col2:
        st.subheader("🇱🇰 Sri Lanka Market & Economic News")
        lk_feed = feedparser.parse("https://news.google.com/rss/search?q=Sri+Lanka+economy+stock+market+CSE&hl=en-US&gl=US&ceid=US:en")
        for entry in lk_feed.entries[:6]:
            st.markdown(f"**[{entry.title}]({entry.link})**")
            st.caption(f"Published: {entry.published}")
            st.write("---")

# === TAB 4: QUICK SOURCES ===
with tab4:
    st.header("Quick Access to All Your Bookmarks")
    
    st.markdown("""
    | Source Category | Direct Link |
    | :--- | :--- |
    | **CSE Advanced Charts** | [https://www.cse.lk/equity/advanced-charts](https://www.cse.lk/equity/advanced-charts) |
    | **CSE Daily Publications** | [https://www.cse.lk/publications/cse-daily](https://www.cse.lk/publications/cse-daily) |
    | **CSE Annual Statistics** | [https://www.cse.lk/equity/annual-trading-statistics](https://www.cse.lk/equity/annual-trading-statistics) |
    | **CSE Pal** | [https://csepal.lk/](https://csepal.lk/) |
    | **Simply Wall St (Community)** | [https://simplywall.st/community/narratives](https://simplywall.st/community/narratives) |
    | **TradingView CSE Technicals** | [https://www.tradingview.com/symbols/CSELK-ASI/technicals/](https://www.tradingview.com/symbols/CSELK-ASI/technicals/) |
    """)
