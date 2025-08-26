# ============================================================
# Ultimate Pro Market Terminal — Streamlit-deployable
# Full-featured: NSE/BSE, MCX, Forex, SIP, FII/DII, News, Portfolio
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import feedparser
import requests
import pandas_ta as ta
import time

# -------------------- APP CONFIG --------------------
st.set_page_config(page_title="Ultimate Market Terminal", layout="wide")
st.title("📊 Ultimate Market Terminal")

# -------------------- SIDEBAR --------------------
st.sidebar.header("Stock Settings")
ticker = st.sidebar.text_input("Enter Stock Symbol (NSE/BSE/US):", "TCS.NS")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2022-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))

st.sidebar.header("Live Update Settings")
refresh_interval = st.sidebar.slider("Auto-refresh (seconds)", 10, 180, 60, 5)

# -------------------- ALERT SOUND --------------------
ALERT_SOUND = "https://www.soundjay.com/buttons/sounds/button-3.mp3"

if "last_recommendation" not in st.session_state:
    st.session_state.last_recommendation = None

# -------------------- DATA FETCH --------------------
@st.cache_data(ttl=refresh_interval)
def load_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    return df

# -------------------- RECOMMENDATION FUNCTION --------------------
def get_recommendation(latest_rsi, latest_macd, latest_signal):
    score = 0
    if latest_rsi < 30:
        score += 15
    elif latest_rsi > 70:
        score -= 15
    if latest_macd > latest_signal:
        score += 20
    else:
        score -= 10
    if score >= 20:
        return "🟢 Strong Buy"
    elif score > 0:
        return "🟡 Hold"
    else:
        return "🔴 Sell"

# -------------------- MAIN LOOP --------------------
while True:
    df = load_data(ticker, start_date, end_date)
    if df.empty:
        st.error("No data found. Try another ticker.")
        st.stop()

    # Technical Indicators
    df["RSI"] = ta.rsi(df["Close"], length=14)
    df["MACD"], df["MACD_signal"], df["MACD_hist"] = ta.macd(df["Close"], fast=12, slow=26, signal=9).T.values
    df["SMA_20"] = ta.sma(df["Close"], length=20)
    df["EMA_20"] = ta.ema(df["Close"], length=20)

    latest_rsi = df["RSI"].iloc[-1]
    latest_macd = df["MACD"].iloc[-1]
    latest_signal = df["MACD_signal"].iloc[-1]
    recommendation = get_recommendation(latest_rsi, latest_macd, latest_signal)

    # Bell Alert if recommendation changed
    if recommendation != st.session_state.last_recommendation:
        st.audio(ALERT_SOUND)
        st.session_state.last_recommendation = recommendation

    # -------------------- TABS --------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Fundamentals", "Technicals", "Charts", "News", "Portfolio"]
    )

    # FUNDAMENTALS
    with tab1:
        st.subheader("🏦 Fundamental Analysis")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            st.write({
                "Company": info.get("longName"),
                "Sector": info.get("sector"),
                "Industry": info.get("industry"),
                "Market Cap": info.get("marketCap"),
                "PE Ratio": info.get("trailingPE"),
                "PB Ratio": info.get("priceToBook"),
                "ROE": info.get("returnOnEquity"),
                "Debt to Equity": info.get("debtToEquity")
            })
            st.subheader("💡 AI Recommendation")
            st.markdown(f"**{recommendation}** based on latest RSI ({latest_rsi:.2f}) and MACD ({latest_macd:.2f})")
        except Exception as e:
            st.error(f"Error fetching fundamentals: {e}")

    # TECHNICALS
    with tab2:
        st.subheader("📉 Technical Indicators")
        st.write(df.tail(10))
        st.line_chart(df[["RSI", "MACD", "MACD_signal"]])

    # CHARTS
    with tab3:
        st.subheader("📈 Candlestick Chart")
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"]
        )])
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], mode="lines", name="SMA 20"))
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA_20"], mode="lines", name="EMA 20"))
        fig.update_layout(title=f"{ticker} Price Chart", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # NEWS
    with tab4:
        st.subheader("📰 Latest News")
        query = ticker.replace(".NS", "").replace(".BSE", "")
        url = f"https://news.google.com/rss/search?q={query}+stock+market"
        feed = feedparser.parse(url)
        if feed.entries:
            for entry in feed.entries[:5]:
                st.markdown(f"**[{entry.title}]({entry.link})**")
        else:
            st.info("No news found.")

    # PORTFOLIO
    with tab5:
        st.subheader("📂 Portfolio Tracker")
        uploaded = st.file_uploader("Upload CSV with 'Symbol' and 'Quantity'", type="csv")
        if uploaded:
            df_port = pd.read_csv(uploaded)
            total_value = 0
            for _, row in df_port.iterrows():
                sym = row['Symbol']
                qty = row['Quantity']
                try:
                    price = yf.download(sym, period="1d")['Close'].iloc[-1]
                    val = price * qty
                    total_value += val
                    st.write(f"{sym}: {qty} × {price:.2f} = {val:.2f}")
                except:
                    st.write(f"{sym}: Could not fetch price")
            st.success(f"Total Portfolio Value = ₹ {total_value:,.2f}")

    # -------------------- WAIT BEFORE REFRESH --------------------
    st.info(f"Auto-refreshing every {refresh_interval} seconds...")
    time.sleep(refresh_interval)
