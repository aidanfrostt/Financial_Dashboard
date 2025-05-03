import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import ollama
from datetime import datetime, timedelta
import plotly.express as px
from streamlit_tags import st_tags

# ========== SETTINGS ========== #
THEME = {
    "primary": "#6C5CE7",
    "secondary": "#A29BFE",
    "background": "#1E2130",
    "card": "#252A41",
    "text": "#FFFFFF",
    "positive": "#00B894",
    "negative": "#D63031",
    "warning": "#FDCB6E"
}

# ========== PAGE CONFIG ========== #
st.set_page_config(
    page_title="NeuraFin AI Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# ========== CUSTOM CSS ========== #
st.markdown(f"""
<style>
    /* Base styles */
    body {{
        background-color: {THEME['background']};
        color: {THEME['text']};
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}

    /* Input fields */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {{
        background-color: {THEME['card']} !important;
        color: {THEME['text']} !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
        padding: 10px !important;
        font-size: 16px !important;
    }}

    /* Dropdown menus */
    .stSelectbox div[data-baseweb="select"] {{
        background-color: {THEME['card']} !important;
        border-radius: 8px !important;
    }}

    /* Buttons */
    .stButton button {{
        background-color: {THEME['primary']} !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-size: 16px !important;
        transition: all 0.3s ease !important;
    }}

    .stButton button:hover {{
        background-color: {THEME['secondary']} !important;
        transform: translateY(-2px) !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab"] {{
        background-color: {THEME['card']} !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        margin-right: 5px !important;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: {THEME['primary']} !important;
    }}

    /* Charts */
    .plotly-graph-div {{
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }}
</style>
""", unsafe_allow_html=True)

# ========== UTILITY FUNCTIONS ========== #
def format_currency(value):
    """Format numbers as currency"""
    if pd.isna(value):
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    else:
        return f"${value:,.2f}"

def get_stock_data(ticker):
    """Fetch stock data from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist_data = stock.history(period="1y")
        return {
            "info": info,
            "history": hist_data,
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========== DASHBOARD COMPONENTS ========== #
def render_stock_header(ticker, data):
    """Display stock header with key metrics"""
    st.markdown(f"## 📊 {data['info'].get('longName', ticker)} ({ticker})")
    st.caption(f"📌 Sector: {data['info'].get('sector', 'N/A')} | Industry: {data['info'].get('industry', 'N/A')}")

    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Price", f"${data['info'].get('currentPrice', 'N/A')}", delta=f"{data['info'].get('regularMarketChangePercent', 0):.2f}%")
    with col2:
        st.metric("📈 Market Cap", format_currency(data['info'].get('marketCap')))
    with col3:
        st.metric("🔍 P/E Ratio", f"{data['info'].get('trailingPE', 'N/A')}")
    with col4:
        st.metric("📅 52W Range", f"${data['info'].get('fiftyTwoWeekLow', 'N/A')} - ${data['info'].get('fiftyTwoWeekHigh', 'N/A')}")

def render_stock_chart(ticker, data):
    """Display interactive stock chart"""
    st.markdown("### 📈 Price Chart")
    
    # Chart type selection
    chart_type = st.radio("Chart Type", ["Line", "Candlestick"], horizontal=True, key=f"chart_type_{ticker}")

    # Plot the chart
    if not data['history'].empty:
        if chart_type == "Candlestick":
            fig = go.Figure(data=[go.Candlestick(
                x=data['history'].index,
                open=data['history']['Open'],
                high=data['history']['High'],
                low=data['history']['Low'],
                close=data['history']['Close'],
                increasing_line_color=THEME['positive'],
                decreasing_line_color=THEME['negative']
            )])
        else:
            fig = go.Figure(data=[go.Scatter(
                x=data['history'].index,
                y=data['history']['Close'],
                line=dict(color=THEME['primary']),
                fill='tozeroy',
                fillcolor=f"rgba(108, 92, 231, 0.2)"
            )])

        fig.update_layout(
            plot_bgcolor=THEME['card'],
            paper_bgcolor=THEME['background'],
            font_color=THEME['text'],
            height=500,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No historical data available.")

def render_ai_insights(ticker, data):
    """AI-powered stock analysis with data context"""
    st.markdown("### 🤖 AI Analyst")
    
    # Prepare financial context for AI
    info = data['info']
    financial_context = f"""
    Company: {info.get('longName', ticker)} ({ticker})
    Sector: {info.get('sector', 'N/A')}
    Industry: {info.get('industry', 'N/A')}
    Current Price: ${info.get('currentPrice', 'N/A')}
    52-Week Range: ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}
    Market Cap: {format_currency(info.get('marketCap'))}
    P/E Ratio: {info.get('trailingPE', 'N/A')}
    PEG Ratio: {info.get('pegRatio', 'N/A')}
    Dividend Yield: {info.get('dividendYield', 0)*100:.2f}%
    Revenue Growth: {info.get('revenueGrowth', 0)*100:.2f}%
    Profit Margins: {info.get('profitMargins', 0)*100:.2f}%
    """
    
    user_question = st.text_input(
        f"Ask AI about {ticker}",
        value=f"What is the investment outlook for {ticker} considering its current valuation and growth prospects?",
        key=f"ai_question_{ticker}"
    )

    if st.button("Get AI Analysis", key=f"ai_btn_{ticker}"):
        with st.spinner("🧠 Analyzing financial data..."):
            try:
                # First get fundamental data summary
                analysis_prompt = f"""
                Analyze this stock based on the following financial data:
                {financial_context}
                
                Please provide a professional investment analysis covering:
                1. Valuation assessment (is the stock over/under/fairly valued?)
                2. Growth prospects
                3. Competitive position
                4. Key risks
                5. Recommendation (Buy/Hold/Sell) with rationale
                
                Be specific and reference the provided metrics in your analysis.
                """
                
                response = ollama.chat(
                    model="deepseek-r1:1.5b",
                    messages=[{"role": "user", "content": analysis_prompt}],
                    options={'temperature': 0.1, 'num_ctx': 4096}
                )
                
                # Format the response nicely
                analysis = response['message']['content'].strip()
                
                # Get answer to user's specific question in context
                if user_question.lower() not in analysis_prompt.lower():
                    qa_prompt = f"""
                    Based on this financial context:
                    {financial_context}
                    
                    And this previous analysis:
                    {analysis}
                    
                    Answer this specific question:
                    {user_question}
                    """
                    
                    qa_response = ollama.chat(
                        model="deepseek-r1:1.5b",
                        messages=[{"role": "user", "content": qa_prompt}],
                        options={'temperature': 0.1, 'num_ctx': 4096}
                    )
                    analysis += "\n\n---\n\n" + qa_response['message']['content'].strip()
                
                # Display with nice formatting
                st.markdown(f"""
                <div style='
                    background-color: {THEME['card']};
                    border-radius: 10px;
                    padding: 20px;
                    margin-top: 20px;
                    border-left: 4px solid {THEME['primary']};
                '>
                    {analysis}
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"AI Error: {str(e)}")
                st.info("Make sure Ollama is running (`ollama serve`) and the model is downloaded (`ollama pull deepseek-r1:1.5b`)")

# ========== MAIN APP ========== #
def main():
    """Main dashboard function"""
    
    # Initialize session state
    if "tickers" not in st.session_state:
        st.session_state.tickers = ["AAPL", "MSFT", "GOOG"]
    if "current_ticker" not in st.session_state:
        st.session_state.current_ticker = "AAPL"

    # Sidebar
    with st.sidebar:
        st.title("🔍 Stock Watchlist")
        
        # Add new stock
        new_ticker = st.text_input("Add Stock (e.g., TSLA)", key="new_ticker").upper()
        if st.button("➕ Add") and new_ticker:
            if new_ticker not in st.session_state.tickers:
                st.session_state.tickers.append(new_ticker)
                st.session_state.current_ticker = new_ticker
                st.rerun()

        # Stock selection
        st.markdown("### 📌 Your Stocks")
        for ticker in st.session_state.tickers:
            if st.button(ticker, key=f"btn_{ticker}"):
                st.session_state.current_ticker = ticker
                st.rerun()

        # Remove stock
        if st.button("🗑️ Remove Current Stock"):
            st.session_state.tickers.remove(st.session_state.current_ticker)
            st.session_state.current_ticker = st.session_state.tickers[0] if st.session_state.tickers else None
            st.rerun()

    # Main content
    ticker = st.session_state.current_ticker
    st.title(f"📊 {ticker} Dashboard")

    # Fetch data
    data = get_stock_data(ticker)
    if not data["success"]:
        st.error(f"❌ Failed to fetch data for {ticker}: {data.get('error', 'Unknown error')}")
        return

    # Render components
    render_stock_header(ticker, data)
    render_stock_chart(ticker, data)
    render_ai_insights(ticker, data)

if __name__ == "__main__":
    main()