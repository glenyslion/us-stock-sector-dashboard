"""
Generates a static HTML site from pre-computed market data.
Output goes to docs/ which GitHub Pages serves.
"""
import json
import os
import sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.calculations import (
    load_prices, load_metrics, load_rankings_history,
    SECTORS, INDICES, get_period_prices, normalize_to_100,
)

DOCS_DIR = Path(__file__).parent.parent / "docs"
DOCS_DIR.mkdir(exist_ok=True)

PERIODS = ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y"]
GREEN  = "#00c805"
RED    = "#ff3b30"
BLUE   = "#0a84ff"

# Distinct colors that are legible on both dark and light backgrounds
INDEX_COLORS = {
    "SPY": "#2196F3",
    "QQQ": "#FF9800",
    "DIA": "#4CAF50",
    "IWM": "#AB47BC",
}
SECTOR_LINE_COLORS = [
    "#2196F3", "#FF9800", "#4CAF50", "#AB47BC", "#F44336",
    "#00BCD4", "#FF5722", "#8BC34A", "#E91E63", "#03A9F4", "#FFC107",
]

INDEX_DESCRIPTIONS = {
    "SPY":  "SPDR S&P 500 ETF — tracks the 500 largest US public companies",
    "QQQ":  "Invesco QQQ — tracks Nasdaq 100, heavily weighted toward tech",
    "DIA":  "SPDR Dow Jones ETF — tracks 30 blue-chip US companies",
    "IWM":  "iShares Russell 2000 — tracks ~2,000 US small-cap companies",
    "^VIX": "CBOE Volatility Index — measures expected market volatility (fear gauge)",
    "TLT":  "iShares 20+ Year Treasury Bond ETF — long-duration US government debt",
    "GLD":  "SPDR Gold Shares — tracks the price of physical gold",
    "UUP":  "Invesco US Dollar Index Bullish — measures USD vs basket of currencies",
}

# ─── Shared CSS ───────────────────────────────────────────────────────────────

CSS = """
:root{
  --bg:#0e1117;--card:#1a1a2e;--border:#2d2d44;--text:#fafafa;--sub:#888;
  --accent:#0a84ff;--green:#00c805;--red:#ff3b30;--hover:rgba(255,255,255,.03);
}
[data-theme="light"]{
  --bg:#f0f2f6;--card:#ffffff;--border:#d1d5db;--text:#111827;--sub:#6b7280;
  --accent:#0066cc;--green:#16a34a;--red:#dc2626;--hover:rgba(0,0,0,.03);
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.5;transition:background .2s,color .2s}
a{text-decoration:none;color:inherit}
nav{display:flex;align-items:center;padding:12px 24px;background:var(--card);
    border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100;gap:8px;transition:background .2s,border-color .2s}
.brand{font-weight:700;font-size:1.1rem;margin-right:24px;white-space:nowrap}
.nav-links{display:flex;gap:6px;flex:1}
.nav-link{padding:7px 14px;border-radius:7px;color:var(--sub);font-size:.875rem;transition:all .15s}
.nav-link:hover,.nav-link.active{background:var(--border);color:var(--text)}
.theme-select{background:var(--card);color:var(--text);border:1px solid var(--border);
  border-radius:7px;padding:6px 10px;font-size:.83rem;cursor:pointer;transition:all .2s;
  margin-left:auto;white-space:nowrap}
.theme-select:hover{border-color:var(--accent)}
main{max-width:1200px;margin:0 auto;padding:28px 24px}
h1{font-size:1.6rem;font-weight:700;margin-bottom:4px}
h2{font-size:1.05rem;font-weight:600;margin-bottom:14px;color:var(--text)}
.sub{color:var(--sub);font-size:.82rem;margin-bottom:24px}
hr{border:none;border-top:1px solid var(--border);margin:28px 0}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px;transition:background .2s,border-color .2s}
.metric-label{font-size:.78rem;color:var(--sub);margin-bottom:4px}
.metric-desc{font-size:.72rem;color:var(--sub);margin-top:6px;line-height:1.3;opacity:.8}
.metric-value{font-size:1.45rem;font-weight:700}
.metric-delta{font-size:.83rem;margin-top:5px}
.pos{color:var(--green)}.neg{color:var(--red)}.neu{color:var(--sub)}
.toggle{display:flex;gap:6px;margin:0 0 20px;flex-wrap:wrap}
.btn{padding:6px 14px;border-radius:20px;border:1px solid var(--border);
     background:transparent;color:var(--sub);cursor:pointer;font-size:.83rem;transition:all .15s}
.btn:hover,.btn.active{background:var(--accent);border-color:var(--accent);color:#fff}
.period-data{display:none}
table{width:100%;border-collapse:collapse;font-size:.875rem}
th{text-align:left;padding:10px 14px;color:var(--sub);font-weight:500;
   border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:10px 14px;border-bottom:1px solid var(--border)}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--hover)}
.rank-num{color:var(--sub);font-weight:700}
footer{text-align:center;padding:28px;color:var(--sub);font-size:.8rem;
       border-top:1px solid var(--border);margin-top:48px}
.sbtn{padding:6px 13px;border-radius:7px;border:1px solid var(--border);
      background:transparent;color:var(--text);cursor:pointer;font-size:.83rem;transition:all .15s}
.sbtn:hover,.sbtn.active{background:var(--accent);border-color:var(--accent);color:#fff}
.sbtn-wrap{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}
.stats-row{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;margin:20px 0}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;text-align:center;transition:background .2s}
.stat-label{font-size:.72rem;color:var(--sub);margin-bottom:4px}
.stat-val{font-size:1rem;font-weight:700}
.key-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}
.ai-summary{background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:20px;margin:0 0 8px;border-left:3px solid var(--accent)}
.ai-summary-label{font-size:.75rem;color:var(--accent);font-weight:600;
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.ai-summary-text{font-size:.9rem;color:var(--text);line-height:1.6}
@media(max-width:768px){
  .grid-4{grid-template-columns:repeat(2,1fr)}
  .grid-2{grid-template-columns:1fr}
  .stats-row{grid-template-columns:repeat(4,1fr)}
  .key-stats{grid-template-columns:repeat(2,1fr)}
}
"""

# ─── Shared JS ────────────────────────────────────────────────────────────────

BASE_JS = """
function switchPeriod(period, ns) {
  document.querySelectorAll('.' + ns + '-data').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.' + ns + '-' + period).forEach(el => el.style.display = 'block');
  document.querySelectorAll('.' + ns + '-btn').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.period === period));
}

function getPlotlyTheme() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  return {
    template: isLight ? 'plotly_white' : 'plotly_dark',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
  };
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem('theme', theme); } catch(e) {}
  var sel = document.getElementById('theme-select');
  if (sel) sel.value = theme;
  var layout = getPlotlyTheme();
  document.querySelectorAll('.plotly-graph-div').forEach(function(div) {
    try { Plotly.relayout(div.id, layout); } catch(e) {}
  });
  if (typeof onThemeChange === 'function') onThemeChange(theme);
}

(function() {
  var theme;
  try { theme = localStorage.getItem('theme'); } catch(e) {}
  if (!theme) {
    theme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches)
      ? 'light' : 'dark';
  }
  document.documentElement.setAttribute('data-theme', theme);
  var sel = document.getElementById('theme-select');
  if (sel) sel.value = theme;
  // Delay Plotly update until charts are rendered
  window.addEventListener('load', function() { applyTheme(theme); });
})();
"""

# ─── Helpers ──────────────────────────────────────────────────────────────────

def chart_div(fig: go.Figure, div_id: str = "") -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id or None,
        config={"responsive": True, "displayModeBar": False},
    )

def dark_layout(**kwargs) -> dict:
    base = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=360,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    base.update(kwargs)
    return base

def ret_color(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "neu", "—"
    cls = "pos" if v >= 0 else "neg"
    return cls, f"{v:+.2f}%"

def period_toggle(ns: str, default: str = "1M") -> str:
    btns = "".join(
        f'<button class="btn {ns}-btn{"  active" if p == default else ""}" '
        f'data-period="{p}" onclick="switchPeriod(\'{p}\',\'{ns}\')">{p}</button>'
        for p in PERIODS
    )
    return f'<div class="toggle">{btns}</div>'

def base_html(title: str, content: str, active: str, last_updated: str, extra_js: str = "") -> str:
    nav = ""
    for href, label, key in [
        ("index.html", "📊 Overview", "index"),
        ("rotation.html", "🔄 Sector Rotation", "rotation"),
        ("deepdive.html", "🔍 Deep Dive", "deepdive"),
    ]:
        cls = " active" if active == key else ""
        nav += f'<a href="{href}" class="nav-link{cls}">{label}</a>'

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Market Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<nav>
  <span class="brand">📊 Market Dashboard</span>
  <div class="nav-links">{nav}</div>
  <select id="theme-select" class="theme-select" onchange="applyTheme(this.value)">
    <option value="dark">🌙 Dark</option>
    <option value="light">☀️ Light</option>
  </select>
</nav>
<main>{content}</main>
<footer>Updated daily after market close &nbsp;·&nbsp; Data: Yahoo Finance &nbsp;·&nbsp; Last refresh: {last_updated}</footer>
<script>{BASE_JS}{extra_js}</script>
</body>
</html>"""


# ─── AI Summary ───────────────────────────────────────────────────────────────

def generate_ai_summary(metrics: pd.DataFrame) -> str:
    if not HAS_ANTHROPIC:
        print("  Skipping AI summary (anthropic package not installed)")
        return ""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  Skipping AI summary (ANTHROPIC_API_KEY not set)")
        return ""

    try:
        sector_data = metrics[metrics["ticker"].isin(SECTORS.keys())].copy()
        sector_data["name"] = sector_data["ticker"].map(SECTORS)
        sector_data = sector_data.sort_values("momentum_score", ascending=False).reset_index(drop=True)

        lines = []
        for _, row in sector_data.iterrows():
            r1m  = row.get("return_1M")
            r3m  = row.get("return_3M")
            vs   = row.get("vs_spy_1M")
            score = row.get("momentum_score")
            lines.append(
                f"{row['name']}: 1M={r1m:+.1f}%, 3M={r3m:+.1f}%, "
                f"vs SPY={vs:+.1f}%, momentum={score:.2f}"
            )
        data_str = "\n".join(lines)

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=250,
            messages=[{
                "role": "user",
                "content": (
                    "You are a market analyst. Based on this US sector ETF performance data, "
                    "write 2–3 concise sentences identifying: (1) which sectors show signs of "
                    "capital inflow (strong momentum, outperforming SPY), and (2) which sectors "
                    "show signs of outflow (weak momentum, underperforming SPY). Mention specific "
                    "sector names. Plain text only, no markdown, under 100 words.\n\n"
                    + data_str
                ),
            }],
        )
        summary = msg.content[0].text.strip()
        print(f"  AI summary generated ({len(summary)} chars)")
        return summary
    except Exception as exc:
        print(f"  AI summary failed: {exc}")
        return ""


# ─── Page generators ──────────────────────────────────────────────────────────

def build_index(metrics: pd.DataFrame, prices: pd.DataFrame,
                last_updated: str, ai_summary: str = "") -> None:
    print("  Building index.html...")

    # ── Index cards ──────────────────────────────────────────────────────────
    cards_html = ""
    for ticker in ["SPY", "QQQ", "DIA", "IWM"]:
        rows = metrics[metrics["ticker"] == ticker]
        if rows.empty:
            continue
        row = rows.iloc[0]
        r1d = row.get("return_1D") or 0.0
        r1m = row.get("return_1M") or 0.0
        d_cls, d_val = ret_color(r1d)
        m_cls, m_val = ret_color(r1m)
        desc = INDEX_DESCRIPTIONS.get(ticker, "")
        cards_html += f"""
<div class="card">
  <div class="metric-label">{INDICES.get(ticker, ticker)}</div>
  <div class="metric-value {d_cls}">{d_val} <span style="font-size:.9rem">1D</span></div>
  <div class="metric-delta {m_cls}">{m_val} (1M)</div>
  <div class="metric-desc">{desc}</div>
</div>"""

    # ── Normalized chart with distinct colors ────────────────────────────────
    tickers = ["SPY", "QQQ", "DIA", "IWM"]
    avail = [t for t in tickers if t in prices.columns]
    period_prices = get_period_prices(prices[avail], "1M")
    normed = normalize_to_100(period_prices)

    fig = go.Figure()
    for t in normed.columns:
        name = INDICES.get(t, t)
        color = INDEX_COLORS.get(t, BLUE)
        fig.add_trace(go.Scatter(
            x=normed.index, y=normed[t].round(2), name=name, mode="lines",
            line=dict(width=2.5, color=color),
            hovertemplate=f"<b>{name}</b>: %{{y:.1f}}<extra></extra>",
        ))
    fig.update_layout(**dark_layout(height=320))
    chart = chart_div(fig)

    # ── Top / bottom sectors ──────────────────────────────────────────────────
    sm = metrics[metrics["ticker"].isin(SECTORS.keys())].copy()
    sm["name"] = sm["ticker"].map(SECTORS)
    sm = sm.dropna(subset=["momentum_score"]).sort_values("momentum_score", ascending=False).reset_index(drop=True)

    def sector_row(row, rank):
        r1m = row.get("return_1M") or 0.0
        score = row.get("momentum_score") or 0.0
        cls = "pos" if r1m >= 0 else "neg"
        return (
            f'<div style="display:flex;justify-content:space-between;padding:10px 0;'
            f'border-bottom:1px solid var(--border)">'
            f'<span><b style="margin-right:10px;color:var(--sub)">#{rank}</b>{row["name"]}</span>'
            f'<span><span class="{cls}">{r1m:+.1f}%</span>'
            f'<span style="color:var(--sub);margin-left:12px;font-size:.8rem">score {score:.1f}</span></span></div>'
        )

    leaders  = "".join(sector_row(sm.iloc[i], i + 1) for i in range(3))
    laggards = "".join(sector_row(sm.iloc[-(i+1)], len(sm) - i) for i in range(3))

    # ── Macro cards ──────────────────────────────────────────────────────────
    macro_html = ""
    for ticker in ["^VIX", "TLT", "GLD", "UUP"]:
        rows = metrics[metrics["ticker"] == ticker]
        if rows.empty:
            continue
        row = rows.iloc[0]
        r = row.get("return_1M") or 0.0
        cls, val = ret_color(r)
        desc = INDEX_DESCRIPTIONS.get(ticker, "")
        macro_html += f"""
<div class="card">
  <div class="metric-label">{INDICES.get(ticker, ticker)}</div>
  <div class="metric-value {cls}" style="font-size:1.2rem">{val}</div>
  <div class="metric-delta neu">1-month</div>
  <div class="metric-desc">{desc}</div>
</div>"""

    # ── AI summary block ─────────────────────────────────────────────────────
    ai_block = ""
    if ai_summary:
        ai_block = f"""
<div class="ai-summary">
  <div class="ai-summary-label">AI Rotation Insight</div>
  <div class="ai-summary-text">{ai_summary}</div>
</div>"""

    content = f"""
<h1>Market Dashboard</h1>
<p class="sub">Last updated: {last_updated} &nbsp;·&nbsp; Sector rotation & trend analysis</p>

{ai_block}

<h2>Major Indices — 1D / 1M</h2>
<div class="grid-4">{cards_html}</div>

<hr>
<h2>1-Month Performance (Indexed to 100)</h2>
{chart}

<hr>
<div class="grid-2">
  <div>
    <h2>🔥 Leading Sectors</h2>
    <div>{leaders}</div>
  </div>
  <div>
    <h2>🧊 Lagging Sectors</h2>
    <div>{laggards}</div>
  </div>
</div>

<hr>
<h2>Macro Indicators — 1M</h2>
<div class="grid-4">{macro_html}</div>
"""

    html = base_html("Overview", content, "index", last_updated)
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print("    ✓ index.html")


def build_rotation(metrics: pd.DataFrame, prices: pd.DataFrame,
                   history: pd.DataFrame, last_updated: str) -> None:
    print("  Building rotation.html...")

    sm = metrics[metrics["ticker"].isin(SECTORS.keys())].copy()
    sm["name"] = sm["ticker"].map(SECTORS)
    sm = sm.dropna(subset=["momentum_score"]).sort_values("momentum_score", ascending=False)

    tables_html = ""
    barcharts_html = ""

    for period in PERIODS:
        ret_col  = f"return_{period}"
        vs_col   = f"vs_spy_{period}"
        is_default = "block" if period == "1M" else "none"

        rows_html = ""
        df_sorted = sm.sort_values("momentum_score", ascending=False).reset_index(drop=True)
        for i, row in df_sorted.iterrows():
            r_cls, r_val = ret_color(row.get(ret_col))
            v_cls, v_val = ret_color(row.get(vs_col))
            score = row.get("momentum_score")
            score_str = f"{score:.2f}" if score is not None else "—"
            vol = row.get("volatility_1M")
            vol_str = f"{vol:.1f}%" if vol is not None and not np.isnan(vol) else "—"
            rows_html += f"""<tr>
              <td class="rank-num">{i+1}</td>
              <td><b>{row['name']}</b> <span style="color:var(--sub);font-size:.8rem">{row['ticker']}</span></td>
              <td class="{r_cls}">{r_val}</td>
              <td class="{v_cls}">{v_val}</td>
              <td>{score_str}</td>
              <td style="color:var(--sub)">{vol_str}</td>
            </tr>"""

        tables_html += f"""
<div class="rot-data rot-{period}" style="display:{is_default}">
  <table>
    <thead><tr>
      <th>#</th><th>Sector</th><th>Return ({period})</th><th>vs S&amp;P 500</th>
      <th>Momentum</th><th>Volatility (1M)</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""

        df_bar = sm[[ret_col, "name"]].dropna(subset=[ret_col]).sort_values(ret_col, ascending=True)
        colors = [GREEN if v >= 0 else RED for v in df_bar[ret_col]]
        fig = go.Figure(go.Bar(
            x=df_bar[ret_col], y=df_bar["name"], orientation="h",
            marker_color=colors,
            text=[f"{v:+.1f}%" for v in df_bar[ret_col]],
            textposition="outside",
            hovertemplate="<b>%{y}</b>: %{x:.2f}%<extra></extra>",
        ))
        fig.update_layout(**dark_layout(height=380, xaxis_title=f"{period} Return (%)"))
        barcharts_html += f"""
<div class="bar-data bar-{period}" style="display:{is_default}">
  {chart_div(fig)}
</div>"""

    # ── Heatmap ───────────────────────────────────────────────────────────────
    avail_periods = [p for p in PERIODS if f"return_{p}" in sm.columns]
    tickers_sorted = sm["ticker"].tolist()
    labels = [SECTORS.get(t, t) for t in tickers_sorted]
    z, text_vals = [], []
    for p in avail_periods:
        vals = sm.set_index("ticker").loc[tickers_sorted, f"return_{p}"].tolist()
        z.append(vals)
        text_vals.append([f"{v:+.1f}%" if v is not None and not np.isnan(v) else "" for v in vals])

    hfig = go.Figure(data=go.Heatmap(
        z=z, x=labels, y=avail_periods,
        colorscale=[[0, "#CC0000"], [0.5, "#1C1C1E"], [1, GREEN]],
        zmid=0, text=text_vals, texttemplate="%{text}", showscale=True,
        hovertemplate="<b>%{x} — %{y}</b><br>%{text}<extra></extra>",
    ))
    hfig.update_layout(**dark_layout(height=300))
    heatmap_html = chart_div(hfig)

    # ── Bump chart ────────────────────────────────────────────────────────────
    bump_html = ""
    if not history.empty:
        bfig = go.Figure()
        for i, (ticker, name) in enumerate(SECTORS.items()):
            df = history[history["ticker"] == ticker].sort_values("date")
            if df.empty:
                continue
            color = SECTOR_LINE_COLORS[i % len(SECTOR_LINE_COLORS)]
            bfig.add_trace(go.Scatter(
                x=df["date"], y=df["rank"], name=name,
                mode="lines+markers", line=dict(width=2, color=color), marker=dict(size=5),
                hovertemplate=f"<b>{name}</b><br>%{{x|%b %d}}: Rank #%{{y}}<extra></extra>",
            ))
        bfig.update_layout(**dark_layout(
            height=440,
            yaxis=dict(autorange="reversed", title="Rank", tickmode="linear", tick0=1, dtick=1),
        ))
        bump_html = f"<hr><h2>Sector Ranking Over Time</h2>{chart_div(bfig)}"
    else:
        bump_html = "<hr><p style='color:var(--sub)'>Ranking history builds up after daily runs.</p>"

    content = f"""
<h1>🔄 Sector Rotation</h1>
<p class="sub">Sectors ranked by momentum score (risk-adjusted weighted return)</p>

{period_toggle("rot")}

<div class="grid-2">
  <div>
    <h2>Sector Rankings</h2>
    {tables_html}
  </div>
  <div>
    <h2>Returns by Sector</h2>
    {barcharts_html}
  </div>
</div>

<hr>
<h2>Performance Heatmap — All Periods</h2>
{heatmap_html}
{bump_html}
"""

    extra_js = "switchPeriod('1M','rot');switchPeriod('1M','bar');"
    html = base_html("Sector Rotation", content, "rotation", last_updated, extra_js)
    (DOCS_DIR / "rotation.html").write_text(html, encoding="utf-8")
    print("    ✓ rotation.html")


def build_deepdive(metrics: pd.DataFrame, prices: pd.DataFrame,
                   history: pd.DataFrame, last_updated: str) -> None:
    print("  Building deepdive.html...")

    all_data: dict = {}
    for ticker, name in SECTORS.items():
        if ticker not in prices.columns or "SPY" not in prices.columns:
            continue
        row = metrics[metrics["ticker"] == ticker]
        if row.empty:
            continue
        row = row.iloc[0]

        stats = {}
        for p in PERIODS:
            stats[f"return_{p}"] = row.get(f"return_{p}")
            stats[f"vs_spy_{p}"] = row.get(f"vs_spy_{p}")
        stats["momentum_score"] = row.get("momentum_score")
        stats["volatility_1M"]  = row.get("volatility_1M")

        period_data: dict = {}
        for period in PERIODS:
            pp = get_period_prices(prices[[ticker, "SPY"]], period)
            normed = normalize_to_100(pp)
            ratio = (pp[ticker] / pp["SPY"])
            rs = ((ratio / ratio.iloc[0]) - 1) * 100
            dates = normed.index.strftime("%Y-%m-%d").tolist()
            period_data[period] = {
                "dates":       dates,
                "sector_norm": normed[ticker].round(2).tolist(),
                "spy_norm":    normed["SPY"].round(2).tolist(),
                "rs":          rs.round(2).tolist(),
            }

        rank_history: dict = {"dates": [], "ranks": []}
        if not history.empty and ticker in history["ticker"].values:
            sh = history[history["ticker"] == ticker].sort_values("date")
            rank_history["dates"] = sh["date"].dt.strftime("%Y-%m-%d").tolist()
            rank_history["ranks"] = sh["rank"].astype(int).tolist()

        all_data[ticker] = {
            "name":         name,
            "stats":        stats,
            "periods":      period_data,
            "rank_history": rank_history,
        }

    data_json = json.dumps(all_data)
    default_sector = "XLK"
    default_period = "1M"

    sector_btns = "".join(
        f'<button class="sbtn{"  active" if t == default_sector else ""}" '
        f'data-ticker="{t}" onclick="switchSector(\'{t}\')">{n}</button>'
        for t, n in SECTORS.items() if t in all_data
    )
    period_btns = "".join(
        f'<button class="btn dive-btn{"  active" if p == default_period else ""}" '
        f'data-period="{p}" onclick="switchDivePeriod(\'{p}\')">{p}</button>'
        for p in PERIODS
    )

    extra_js = f"""
const ALL = {data_json};
let curSector = '{default_sector}';
let curPeriod = '{default_period}';

function buildLayouts() {{
  var theme = getPlotlyTheme();
  var base = Object.assign({{
    margin:{{l:0,r:0,t:10,b:0}},
    hovermode:'x unified',
  }}, theme);
  return {{
    price: Object.assign({{}}, base, {{
      height:340,
      legend:{{orientation:'h',yanchor:'bottom',y:1.02,xanchor:'left',x:0}},
      yaxis:{{title:'Indexed to 100'}}
    }}),
    rs: Object.assign({{}}, base, {{
      height:340,
      yaxis:{{title:'Relative to SPY (%)'}},
      shapes:[{{type:'line',x0:0,x1:1,xref:'paper',y0:0,y1:0,
               line:{{color:'#888',dash:'dash',width:1}}}}]
    }}),
    rank: Object.assign({{}}, base, {{
      height:240,
      yaxis:{{autorange:'reversed',title:'Rank',tickmode:'linear',tick0:1,dtick:1}}
    }})
  }};
}}

function updateCharts() {{
  const d = ALL[curSector];
  if (!d) return;
  const p = d.periods[curPeriod];
  const L = buildLayouts();

  Plotly.react('price-chart', [
    {{x:p.dates, y:p.sector_norm, name:d.name, mode:'lines', line:{{width:2.5,color:'{BLUE}'}}}},
    {{x:p.dates, y:p.spy_norm, name:'S&P 500', mode:'lines', line:{{width:2,color:'#888'}}}}
  ], L.price, {{responsive:true,displayModeBar:false}});

  const lastRs = p.rs[p.rs.length-1];
  const rsColor = lastRs >= 0 ? '{GREEN}' : '{RED}';
  Plotly.react('rs-chart', [{{
    x:p.dates, y:p.rs, mode:'lines', fill:'tozeroy',
    line:{{width:2,color:rsColor}}, fillcolor:rsColor+'22',
    hovertemplate:'%{{x|%b %d}}: %{{y:+.2f}}%<extra></extra>', name:'vs SPY'
  }}], L.rs, {{responsive:true,displayModeBar:false}});

  const s = d.stats;
  const statsHtml = {json.dumps(PERIODS)}.map(period => {{
    const val = s['return_' + period];
    const fmt = val == null ? '—' : (val >= 0 ? '+' : '') + val.toFixed(2) + '%';
    const cls = val == null ? 'neu' : (val >= 0 ? 'pos' : 'neg');
    return `<div class="stat-card"><div class="stat-label">${{period}}</div><div class="stat-val ${{cls}}">${{fmt}}</div></div>`;
  }}).join('');
  document.getElementById('stats-row').innerHTML = statsHtml;

  const score = s.momentum_score != null ? s.momentum_score.toFixed(2) : '—';
  const vol   = s.volatility_1M  != null ? s.volatility_1M.toFixed(1) + '%' : '—';
  const vsSpy = s['vs_spy_' + curPeriod];
  const vsStr = vsSpy != null ? (vsSpy >= 0 ? '+' : '') + vsSpy.toFixed(2) + '%' : '—';
  const vsCls = vsSpy != null ? (vsSpy >= 0 ? 'pos' : 'neg') : 'neu';
  document.getElementById('key-stats').innerHTML = `
    <div class="card"><div class="metric-label">Momentum Score</div><div class="metric-value">${{score}}</div></div>
    <div class="card"><div class="metric-label">Volatility (1M ann.)</div><div class="metric-value">${{vol}}</div></div>
    <div class="card"><div class="metric-label">vs S&P 500 (${{curPeriod}})</div><div class="metric-value ${{vsCls}}">${{vsStr}}</div></div>
    <div class="card"><div class="metric-label">Sector</div><div class="metric-value" style="font-size:1rem">${{d.name}}</div></div>`;

  document.getElementById('sector-title').textContent = d.name + ' (' + curSector + ')';

  const rh = d.rank_history;
  if (rh.dates.length > 1) {{
    Plotly.react('rank-chart', [{{
      x:rh.dates, y:rh.ranks, mode:'lines+markers',
      line:{{color:'{BLUE}',width:2}}, marker:{{size:5}},
      hovertemplate:'%{{x|%b %d}}: Rank #%{{y}}<extra></extra>', name:'Rank'
    }}], L.rank, {{responsive:true,displayModeBar:false}});
    document.getElementById('rank-section').style.display = 'block';
    const cur  = rh.ranks[rh.ranks.length-1];
    const prev = rh.ranks.length > 1 ? rh.ranks[rh.ranks.length-2] : cur;
    const diff = prev - cur;
    const arrow = diff > 0 ? '↑' : diff < 0 ? '↓' : '→';
    const dCls  = diff > 0 ? 'pos' : diff < 0 ? 'neg' : 'neu';
    document.getElementById('rank-badge').innerHTML =
      `Current Rank: <b>#${{cur}}</b> <span class="${{dCls}}">${{arrow}} was #${{prev}}</span>`;
  }} else {{
    document.getElementById('rank-section').style.display = 'none';
  }}
}}

function switchSector(ticker) {{
  curSector = ticker;
  document.querySelectorAll('.sbtn').forEach(b => b.classList.toggle('active', b.dataset.ticker === ticker));
  updateCharts();
}}

function switchDivePeriod(period) {{
  curPeriod = period;
  document.querySelectorAll('.dive-btn').forEach(b => b.classList.toggle('active', b.dataset.period === period));
  updateCharts();
}}

function onThemeChange() {{ updateCharts(); }}

var L0 = buildLayouts();
Plotly.newPlot('price-chart', [], L0.price, {{responsive:true,displayModeBar:false}});
Plotly.newPlot('rs-chart',    [], L0.rs,    {{responsive:true,displayModeBar:false}});
Plotly.newPlot('rank-chart',  [], L0.rank,  {{responsive:true,displayModeBar:false}});
updateCharts();
"""

    content = f"""
<h1>🔍 Sector Deep Dive</h1>
<p class="sub">Select a sector and period to explore in detail</p>

<div class="sbtn-wrap">{sector_btns}</div>
<div class="toggle">{period_btns}</div>

<h2 id="sector-title"></h2>
<div class="stats-row" id="stats-row"></div>

<div class="grid-2">
  <div>
    <h2>Price vs S&amp;P 500</h2>
    <div id="price-chart"></div>
  </div>
  <div>
    <h2>Relative Strength vs S&amp;P 500</h2>
    <div id="rs-chart"></div>
  </div>
</div>

<hr>
<h2>Key Metrics</h2>
<div class="key-stats grid-4" id="key-stats"></div>

<div id="rank-section" style="display:none">
  <hr>
  <h2>Ranking History</h2>
  <p id="rank-badge" style="margin-bottom:12px;color:var(--sub)"></p>
  <div id="rank-chart"></div>
</div>
"""

    html = base_html("Deep Dive", content, "deepdive", last_updated, extra_js)
    (DOCS_DIR / "deepdive.html").write_text(html, encoding="utf-8")
    print("    ✓ deepdive.html")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading data...")
    prices  = load_prices()
    metrics = load_metrics()
    history = load_rankings_history()

    last_updated = str(metrics["date"].max())
    print(f"  Data as of {last_updated} — {len(metrics)} tickers, {len(prices)} trading days")

    print("Generating AI summary...")
    ai_summary = generate_ai_summary(metrics)

    print("Generating site...")
    build_index(metrics, prices, last_updated, ai_summary)
    build_rotation(metrics, prices, history, last_updated)
    build_deepdive(metrics, prices, history, last_updated)

    print(f"Done — site written to {DOCS_DIR}/")


if __name__ == "__main__":
    main()
