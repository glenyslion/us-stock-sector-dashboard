import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

SECTORS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLY": "Consumer Disc.",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLC": "Communication",
}

INDICES = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "DIA": "Dow Jones",
    "IWM": "Russell 2000",
    "^VIX": "VIX",
    "TLT": "Long Bonds",
    "GLD": "Gold",
    "UUP": "US Dollar",
}

ALL_TICKERS = list(SECTORS.keys()) + list(INDICES.keys())

PERIOD_DAYS = {
    "1D": 1,
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "1Y": 252,
}


def fetch_prices() -> pd.DataFrame:
    end = datetime.today()
    start = end - timedelta(days=730)

    print(f"Fetching {len(ALL_TICKERS)} tickers from {start.date()} to {end.date()}...")
    raw = yf.download(ALL_TICKERS, start=start, end=end, auto_adjust=True, progress=False)
    df = raw["Close"]
    df.index = pd.to_datetime(df.index)
    df.to_parquet(DATA_DIR / "prices.parquet")
    print(f"Saved prices.parquet — {df.shape[0]} rows x {df.shape[1]} tickers")
    return df


def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    today = df.index[-1]
    records = []

    for ticker in df.columns:
        series = df[ticker].dropna()
        if len(series) < 5:
            continue

        row: dict = {"ticker": ticker, "date": str(today.date())}

        for label, days in PERIOD_DAYS.items():
            if len(series) > days:
                ret = (series.iloc[-1] / series.iloc[-1 - days] - 1) * 100
                row[f"return_{label}"] = round(float(ret), 2)
            else:
                row[f"return_{label}"] = None

        # YTD return
        ytd_series = series[series.index.year == today.year]
        if len(ytd_series) > 1:
            row["return_YTD"] = round(float((series.iloc[-1] / ytd_series.iloc[0] - 1) * 100), 2)
        else:
            row["return_YTD"] = None

        # 21-day annualized volatility
        daily_rets = series.pct_change().dropna()
        if len(daily_rets) >= 21:
            row["volatility_1M"] = round(float(daily_rets.iloc[-21:].std() * np.sqrt(252) * 100), 2)
        else:
            row["volatility_1M"] = None

        records.append(row)

    metrics = pd.DataFrame(records)

    # Relative performance vs SPY
    spy_rows = metrics[metrics["ticker"] == "SPY"]
    if not spy_rows.empty:
        spy = spy_rows.iloc[0]
        for label in list(PERIOD_DAYS.keys()) + ["YTD"]:
            col = f"return_{label}"
            if col in metrics.columns and spy.get(col) is not None:
                metrics[f"vs_spy_{label}"] = (metrics[col] - spy[col]).round(2)

    # Momentum score: weighted risk-adjusted return
    def _momentum(row):
        weights = {"1W": 0.10, "1M": 0.40, "3M": 0.30, "6M": 0.20}
        total, w_sum = 0.0, 0.0
        for period, w in weights.items():
            val = row.get(f"return_{period}")
            if val is not None and not np.isnan(val):
                total += w * val
                w_sum += w
        if w_sum == 0:
            return None
        weighted_ret = total / w_sum
        vol = row.get("volatility_1M") or 15.0  # fallback to 15% if missing
        return round(weighted_ret / (vol / 10), 2)

    metrics["momentum_score"] = metrics.apply(_momentum, axis=1)

    metrics.to_parquet(DATA_DIR / "metrics.parquet", index=False)
    print(f"Saved metrics.parquet — {len(metrics)} rows")
    return metrics


def update_rankings_history(metrics: pd.DataFrame) -> None:
    history_path = DATA_DIR / "rankings_history.parquet"

    sector_metrics = metrics[metrics["ticker"].isin(SECTORS.keys())].copy()
    sector_metrics = sector_metrics.dropna(subset=["momentum_score"])
    sector_metrics["rank"] = sector_metrics["momentum_score"].rank(ascending=False).astype(int)

    keep_cols = ["date", "ticker", "rank", "momentum_score", "return_1W", "return_1M", "return_3M", "return_6M"]
    today_snapshot = sector_metrics[[c for c in keep_cols if c in sector_metrics.columns]]

    if history_path.exists():
        history = pd.read_parquet(history_path)
        history = pd.concat([history, today_snapshot], ignore_index=True)
        history = history.drop_duplicates(subset=["date", "ticker"], keep="last")
    else:
        history = today_snapshot

    history.to_parquet(history_path, index=False)
    print(f"Updated rankings_history.parquet — {len(history)} total rows")


if __name__ == "__main__":
    prices = fetch_prices()
    metrics = calculate_metrics(prices)
    update_rankings_history(metrics)
    print("Done.")
