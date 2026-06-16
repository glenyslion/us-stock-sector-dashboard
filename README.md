# US Stock Sector Dashboard

A market intelligence dashboard tracking US equity sector rotation, momentum, and relative performance — updated automatically every weekday after market close.

**Live dashboard:** https://glenyslion.github.io/us-stock-sector-dashboard/index.html

---

## What it shows

| Page | Description |
|---|---|
| **Overview** | Major index cards (S&P 500, Nasdaq, Dow, Russell 2000), 1-month normalized performance chart, macro indicators (VIX, TLT, GLD, UUP), leading/lagging sectors |
| **Sector Rotation** | All 11 SPDR sectors ranked by momentum score, returns bar chart, multi-period heatmap, ranking bump chart over time |
| **Sector Deep Dive** | Per-sector price vs S&P 500, relative strength chart, key metrics, and ranking history |

Sectors covered: XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLRE, XLU, XLB, XLC

---

## How the live dashboard works

The static site in `docs/` is served by GitHub Pages. A GitHub Actions workflow runs every weekday at 4 PM ET (after market close) to:

1. Fetch latest prices from Yahoo Finance (`pipeline/fetch_data.py`)
2. Compute returns, momentum scores, and volatility (`utils/calculations.py`)
3. Regenerate the static HTML site (`pipeline/generate_site.py`)
4. Commit and push the updated `data/` and `docs/` folders automatically

You can also trigger a manual refresh from the **Actions** tab → **Daily Data Refresh** → **Run workflow**.

---

## Run locally (Streamlit)

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch data first
python pipeline/fetch_data.py

# Launch the app
streamlit run Home.py
```

The app will open at `http://localhost:8501`.

---

## Tech stack

- **Data:** [yfinance](https://github.com/ranaroussi/yfinance)
- **App:** [Streamlit](https://streamlit.io)
- **Charts:** [Plotly](https://plotly.com/python/)
- **Automation:** GitHub Actions (cron schedule)
- **Hosting:** GitHub Pages (static HTML export)
