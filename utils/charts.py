import plotly.graph_objects as go
import pandas as pd
from utils.calculations import normalize_to_100

GREEN = "#00C805"
RED = "#FF3B30"
BLUE = "#0A84FF"


def line_chart(df: pd.DataFrame, title: str = "", normalize: bool = True) -> go.Figure:
    plot_df = normalize_to_100(df) if normalize else df

    fig = go.Figure()
    for col in plot_df.columns:
        fig.add_trace(go.Scatter(
            x=plot_df.index,
            y=plot_df[col].round(2),
            name=col,
            mode="lines",
            line=dict(width=2),
            hovertemplate=f"<b>{col}</b><br>%{{x|%b %d}}: %{{y:.1f}}<extra></extra>",
        ))

    yaxis_title = "Indexed to 100" if normalize else ""
    fig.update_layout(
        title=title,
        template="plotly_dark",
        hovermode="x unified",
        yaxis_title=yaxis_title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=50 if title else 10, b=0),
        height=380,
    )
    return fig


def bar_chart_returns(metrics: pd.DataFrame, period: str, sector_names: dict) -> go.Figure:
    col = f"return_{period}"
    df = metrics[["ticker", col]].copy().dropna(subset=[col])
    df["name"] = df["ticker"].map(sector_names).fillna(df["ticker"])
    df = df.sort_values(col, ascending=True)

    colors = [GREEN if v >= 0 else RED for v in df[col]]

    fig = go.Figure(go.Bar(
        x=df[col],
        y=df["name"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in df[col]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Return: %{x:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark",
        xaxis_title=f"{period} Return (%)",
        margin=dict(l=0, r=70, t=10, b=0),
        height=420,
    )
    return fig


def sector_heatmap(metrics: pd.DataFrame, sector_names: dict) -> go.Figure:
    periods = ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y"]
    available = [p for p in periods if f"return_{p}" in metrics.columns]

    tickers = metrics["ticker"].tolist()
    labels = [sector_names.get(t, t) for t in tickers]

    z = []
    text = []
    for p in available:
        col = f"return_{p}"
        vals = metrics[col].tolist()
        z.append(vals)
        text.append([f"{v:+.1f}%" if v is not None and not pd.isna(v) else "" for v in vals])

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=labels,
        y=available,
        colorscale=[[0.0, "#CC0000"], [0.5, "#1C1C1E"], [1.0, GREEN]],
        zmid=0,
        text=text,
        texttemplate="%{text}",
        showscale=True,
        hovertemplate="<b>%{x} — %{y}</b><br>%{text}<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=0, r=0, t=10, b=0),
        height=320,
    )
    return fig


def ranking_bump_chart(history: pd.DataFrame, sector_names: dict) -> go.Figure:
    fig = go.Figure()

    for ticker in history["ticker"].unique():
        df = history[history["ticker"] == ticker].sort_values("date")
        name = sector_names.get(ticker, ticker)

        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["rank"],
            name=name,
            mode="lines+markers",
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate=f"<b>{name}</b><br>%{{x|%b %d}}: Rank #%{{y}}<extra></extra>",
        ))

    fig.update_layout(
        template="plotly_dark",
        yaxis=dict(autorange="reversed", title="Rank", tickmode="linear", tick0=1, dtick=1),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=50, b=0),
        height=480,
    )
    return fig
