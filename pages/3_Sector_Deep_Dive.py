import streamlit as st
import plotly.graph_objects as go
from utils.calculations import load_metrics, load_prices, load_rankings_history, SECTORS, get_period_prices
from utils.charts import line_chart

st.set_page_config(page_title="Sector Deep Dive", layout="wide")
st.title("🔍 Sector Deep Dive")

metrics = load_metrics()
prices = load_prices()

# ── Selectors ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 5])
with col1:
    selected = st.selectbox(
        "Sector",
        options=list(SECTORS.keys()),
        format_func=lambda x: SECTORS[x],
    )
with col2:
    period = st.radio(
        "Period",
        ["1W", "1M", "3M", "6M", "YTD", "1Y"],
        horizontal=True,
        index=1,
        key="dive_period",
    )

st.divider()

row = metrics[metrics["ticker"] == selected].iloc[0]
st.subheader(f"{SECTORS[selected]} ({selected})")

# ── Return across all periods ─────────────────────────────────────────────────
all_periods = ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y"]
period_cols = st.columns(len(all_periods))
for col, p in zip(period_cols, all_periods):
    ret = row.get(f"return_{p}")
    if ret is not None:
        col.metric(p, f"{ret:+.2f}%")

st.divider()

# ── Price chart vs SPY  |  Relative strength ─────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"Price vs S&P 500 — {period}")
    if selected in prices.columns and "SPY" in prices.columns:
        period_prices = get_period_prices(prices[[selected, "SPY"]], period).copy()
        period_prices.columns = [SECTORS[selected], "S&P 500"]
        fig = line_chart(period_prices, normalize=True)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader(f"Relative Strength vs S&P 500 — {period}")
    if selected in prices.columns and "SPY" in prices.columns:
        period_prices = get_period_prices(prices[[selected, "SPY"]], period)
        ratio = (period_prices[selected] / period_prices["SPY"])
        rel_strength = ((ratio / ratio.iloc[0]) - 1) * 100

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=rel_strength.index,
            y=rel_strength.round(2),
            mode="lines",
            fill="tozeroy",
            line=dict(color="#0A84FF", width=2),
            fillcolor="rgba(10,132,255,0.15)",
            hovertemplate="%{x|%b %d}: %{y:+.2f}%<extra></extra>",
        ))
        fig2.add_hline(y=0, line_dash="dash", line_color="gray")
        fig2.update_layout(
            template="plotly_dark",
            yaxis_title="Relative to SPY (%)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=380,
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── Key stat cards ────────────────────────────────────────────────────────────
st.divider()
st.subheader("Key Metrics")
col1, col2, col3, col4 = st.columns(4)

score = row.get("momentum_score")
col1.metric("Momentum Score", f"{score:.2f}" if score is not None else "—")

vol = row.get("volatility_1M")
col2.metric("Volatility (1M ann.)", f"{vol:.1f}%" if vol is not None else "—")

vs_spy_1m = row.get("vs_spy_1M")
col3.metric("vs S&P 500 (1M)", f"{vs_spy_1m:+.2f}%" if vs_spy_1m is not None else "—")

vs_spy_3m = row.get("vs_spy_3M")
col4.metric("vs S&P 500 (3M)", f"{vs_spy_3m:+.2f}%" if vs_spy_3m is not None else "—")

# ── Ranking history for this sector ──────────────────────────────────────────
st.divider()
history = load_rankings_history()
if not history.empty and selected in history["ticker"].values:
    st.subheader("Ranking History")
    sector_hist = history[history["ticker"] == selected].sort_values("date")

    col1, col2 = st.columns([1, 3])
    with col1:
        current_rank = int(sector_hist.iloc[-1]["rank"])
        prev_rank = int(sector_hist.iloc[-2]["rank"]) if len(sector_hist) > 1 else current_rank
        delta = prev_rank - current_rank
        delta_str = f"{'↑' if delta > 0 else '↓' if delta < 0 else '→'} was #{prev_rank}"
        st.metric("Current Rank", f"#{current_rank}", delta_str)

    with col2:
        fig3 = go.Figure(go.Scatter(
            x=sector_hist["date"],
            y=sector_hist["rank"],
            mode="lines+markers",
            line=dict(color="#0A84FF", width=2),
            marker=dict(size=5),
            hovertemplate="%{x|%b %d}: Rank #%{y}<extra></extra>",
        ))
        fig3.update_layout(
            template="plotly_dark",
            yaxis=dict(autorange="reversed", title="Rank", tickmode="linear", tick0=1, dtick=1),
            margin=dict(l=0, r=0, t=10, b=0),
            height=260,
        )
        st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Ranking history will appear after several daily pipeline runs.")
