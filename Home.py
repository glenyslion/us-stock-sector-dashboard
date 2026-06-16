import streamlit as st
from pathlib import Path
from utils.calculations import load_metrics, SECTORS, INDICES

st.set_page_config(
    page_title="Market Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Market Dashboard")
st.caption("Sector rotation & market trend analysis — updated daily after market close")

data_path = Path("data/metrics.parquet")
if not data_path.exists():
    st.warning(
        "No data found. Run the pipeline first:\n\n"
        "```bash\npython pipeline/fetch_data.py\n```"
    )
    st.stop()

metrics = load_metrics()
last_updated = metrics["date"].max()
st.caption(f"Last updated: {last_updated}")

st.divider()

# ── Major Index Cards ─────────────────────────────────────────────────────────
st.subheader("Major Indices — Today")
index_tickers = ["SPY", "QQQ", "DIA", "IWM"]
cols = st.columns(len(index_tickers))

for col, ticker in zip(cols, index_tickers):
    rows = metrics[metrics["ticker"] == ticker]
    if rows.empty:
        continue
    row = rows.iloc[0]
    ret_1d = row.get("return_1D") or 0.0
    ret_1m = row.get("return_1M") or 0.0
    col.metric(
        INDICES.get(ticker, ticker),
        f"{ret_1d:+.2f}% (1D)",
        f"{ret_1m:+.2f}% (1M)",
    )

st.divider()

# ── Sector Leaders / Laggards ─────────────────────────────────────────────────
sector_metrics = metrics[metrics["ticker"].isin(SECTORS.keys())].copy()
sector_metrics["name"] = sector_metrics["ticker"].map(SECTORS)
sector_metrics = sector_metrics.dropna(subset=["momentum_score"])
sector_metrics = sector_metrics.sort_values("momentum_score", ascending=False).reset_index(drop=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔥 Leading Sectors")
    for _, row in sector_metrics.head(3).iterrows():
        ret_1m = row.get("return_1M") or 0.0
        score = row.get("momentum_score") or 0.0
        st.markdown(f"**{row['name']}** &nbsp; `{ret_1m:+.1f}%` (1M) &nbsp; score: `{score:.1f}`")

with col2:
    st.subheader("🧊 Lagging Sectors")
    for _, row in sector_metrics.tail(3).iloc[::-1].iterrows():
        ret_1m = row.get("return_1M") or 0.0
        score = row.get("momentum_score") or 0.0
        st.markdown(f"**{row['name']}** &nbsp; `{ret_1m:+.1f}%` (1M) &nbsp; score: `{score:.1f}`")

st.divider()
st.caption("Use the sidebar to navigate to Market Overview, Sector Rotation, or Sector Deep Dive.")
