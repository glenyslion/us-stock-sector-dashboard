import streamlit as st
import pandas as pd
from utils.calculations import load_metrics, load_rankings_history, SECTORS
from utils.charts import bar_chart_returns, sector_heatmap, ranking_bump_chart

st.set_page_config(page_title="Sector Rotation", layout="wide")
st.title("🔄 Sector Rotation")

metrics = load_metrics()
sector_metrics = metrics[metrics["ticker"].isin(SECTORS.keys())].copy()
sector_metrics["name"] = sector_metrics["ticker"].map(SECTORS)

# ── Period selector ───────────────────────────────────────────────────────────
period = st.radio(
    "Period",
    ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y"],
    horizontal=True,
    index=2,
    key="rotation_period",
)

st.divider()

# ── Ranked table ──────────────────────────────────────────────────────────────
st.subheader(f"Sector Rankings — {period}")

ret_col = f"return_{period}"
vs_col = f"vs_spy_{period}"

display_cols = {
    "name": "Sector",
    ret_col: f"Return ({period})",
    vs_col: "vs S&P 500",
    "momentum_score": "Momentum Score",
    "volatility_1M": "Volatility (1M)",
}

available_cols = ["name"] + [c for c in [ret_col, vs_col, "momentum_score", "volatility_1M"] if c in sector_metrics.columns]
display = sector_metrics[available_cols].copy()
display = display.sort_values("momentum_score", ascending=False, na_position="last").reset_index(drop=True)
display.index += 1
display.columns = [display_cols.get(c, c) for c in display.columns]

def _color(val):
    if isinstance(val, float):
        return f"color: {'#00C805' if val > 0 else '#FF3B30'}"
    return ""

color_cols = [c for c in [f"Return ({period})", "vs S&P 500"] if c in display.columns]
styled = display.style.applymap(_color, subset=color_cols).format(
    {c: "{:+.2f}%" for c in color_cols}
)
st.dataframe(styled, use_container_width=True)

st.divider()

# ── Bar chart + heatmap side by side ─────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"Returns by Sector — {period}")
    fig = bar_chart_returns(sector_metrics, period, SECTORS)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Heatmap — All Periods")
    sorted_sectors = sector_metrics.sort_values("momentum_score", ascending=False, na_position="last")
    fig2 = sector_heatmap(sorted_sectors, SECTORS)
    st.plotly_chart(fig2, use_container_width=True)

# ── Ranking history bump chart ────────────────────────────────────────────────
st.divider()
st.subheader("Sector Ranking Over Time")
history = load_rankings_history()
if not history.empty:
    fig3 = ranking_bump_chart(history, SECTORS)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Ranking history builds up automatically after each daily run. Check back tomorrow.")
