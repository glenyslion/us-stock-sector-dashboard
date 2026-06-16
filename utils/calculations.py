import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

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

PERIOD_DAYS = {
    "1D": 1,
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "YTD": None,
    "1Y": 252,
}


def load_prices() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "prices.parquet")


def load_metrics() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "metrics.parquet")


def load_rankings_history() -> pd.DataFrame:
    path = DATA_DIR / "rankings_history.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        return df
    return pd.DataFrame()


def get_period_prices(df: pd.DataFrame, period: str) -> pd.DataFrame:
    days = PERIOD_DAYS.get(period)
    if period == "YTD":
        year = df.index[-1].year
        return df[df.index.year >= year]
    elif days:
        return df.iloc[-(days + 1):]
    return df


def normalize_to_100(df: pd.DataFrame) -> pd.DataFrame:
    first_valid = df.apply(lambda col: col.first_valid_index())
    result = df.copy()
    for col in df.columns:
        idx = first_valid[col]
        if idx is not None:
            result[col] = (df[col] / df.loc[idx, col]) * 100
    return result


def get_trend_arrow(current_rank: int, prev_rank: int) -> str:
    diff = prev_rank - current_rank
    if diff >= 3:
        return "↑↑"
    elif diff > 0:
        return "↑"
    elif diff == 0:
        return "→"
    elif diff > -3:
        return "↓"
    else:
        return "↓↓"
