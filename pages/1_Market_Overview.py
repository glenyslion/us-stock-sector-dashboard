import streamlit as st
from utils.calculations import load_prices, load_metrics, INDICES, get_period_prices
from utils.charts import line_chart

st.set_page_config(page_title="Market Overview", layout="wide")
st.title("📈 Market Overview")

metrics = load_metrics()
prices = load_prices()

# ── Period selector ───────────────────────────────────────────────────────────
period = st.radio(
    "Period",
    ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y"],
    horizontal=True,
    index=2,
    key="overview_period",
)

st.divider()

# ── Index metric cards ────────────────────────────────────────────────────────
st.subheader("Major Indices")
index_tickers = ["SPY", "QQQ", "DIA", "IWM"]
available_indices = [t for t in index_tickers if t in metrics["ticker"].values]
cols = st.columns(len(available_indices))

for col, ticker in zip(cols, available_indices):
    row = metrics[metrics["ticker"] == ticker].iloc[0]
    ret = row.get(f"return_{period}") or 0.0
    vs_spy = row.get(f"vs_spy_{period}")
    delta_str = f"vs SPY: {vs_spy:+.1f}%" if (vs_spy is not None and ticker != "SPY") else ""
    col.metric(INDICES.get(ticker, ticker), f"{ret:+.2f}%", delta_str)

# ── Normalized performance chart ──────────────────────────────────────────────
st.divider()
st.subheader(f"Relative Performance — {period} (indexed to 100)")

chart_tickers = ["SPY", "QQQ", "DIA", "IWM"]
available = [t for t in chart_tickers if t in prices.columns]
period_prices = get_period_prices(prices[available], period).copy()
period_prices.columns = [INDICES.get(t, t) for t in period_prices.columns]

fig = line_chart(period_prices, normalize=True)
st.plotly_chart(fig, use_container_width=True)

# ── Macro / risk indicators ───────────────────────────────────────────────────
st.divider()
st.subheader("Macro Indicators")

macro_tickers = ["^VIX", "TLT", "GLD", "UUP"]
available_macro = [t for t in macro_tickers if t in metrics["ticker"].values]
macro_cols = st.columns(len(available_macro))

for col, ticker in zip(macro_cols, available_macro):
    row = metrics[metrics["ticker"] == ticker].iloc[0]
    ret = row.get(f"return_{period}") or 0.0
    col.metric(INDICES.get(ticker, ticker), f"{ret:+.2f}%")

available_macro_prices = [t for t in macro_tickers if t in prices.columns]
if available_macro_prices:
    period_macro = get_period_prices(prices[available_macro_prices], period).copy()
    period_macro.columns = [INDICES.get(t, t) for t in period_macro.columns]
    fig2 = line_chart(period_macro, normalize=True)
    st.plotly_chart(fig2, use_container_width=True)
