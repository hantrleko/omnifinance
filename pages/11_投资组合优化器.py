"""投资组合优化器 — 马科维茨均值-方差模型

允许用户输入多个标的，自动计算在特定风险偏好下的最优资产权重：
  - 最大夏普比率组合（Tangency Portfolio）
  - 最小方差组合（Minimum Variance Portfolio）
  - 有效前沿（Efficient Frontier）可视化

数据来源：Yahoo Finance（通过 yfinance 下载历史收益率）
"""

from __future__ import annotations

import logging
import urllib.error

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from core.theme import inject_theme
inject_theme()
import yfinance as yf

from core.chart_config import build_layout, render_empty_state
from core.config import CFG
from core.currency import currency_selector
from core.export import dataframes_to_excel
from core.portfolio import optimize_portfolio, EfficientFrontierResult

# ── 模块级 logger ─────────────────────────────────────────
_logger = logging.getLogger(__name__)

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="投资组合优化器", page_icon="📐", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .stMetric { background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 8px; padding: 14px; }
</style>
""", unsafe_allow_html=True)

st.title("📐 投资组合优化器")
st.caption("基于马科维茨均值-方差模型，计算最大夏普比率组合与最小方差组合，并展示有效前沿。")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 标的与参数")
pass

tickers_input = st.sidebar.text_area(
    "输入标的代码（每行一个或逗号分隔）",
    value=CFG.backtest.default_portfolio,
    height=120,
    help="支持 Yahoo Finance 格式，如 AAPL、0700.HK、BTC-USD 等。至少输入 2 个标的。",
)

period = st.sidebar.selectbox(
    "历史数据周期",
    options=["1y", "2y", "3y", "5y"],
    index=1,
    help="用于计算历史平均收益率和波动率的时间窗口。",
)

risk_free_rate = st.sidebar.number_input(
    "无风险利率（%）",
    min_value=0.0,
    max_value=CFG.backtest.risk_free_rate_max,
    value=CFG.backtest.risk_free_rate_default,
    step=CFG.backtest.risk_free_rate_step,
    format="%.1f",
    help="用于计算夏普比率的基准利率，通常参考国债收益率。",
)

n_frontier = st.sidebar.slider(
    "有效前沿点数",
    min_value=20,
    max_value=100,
    value=50,
    step=10,
    help="有效前沿上的采样点数，越多曲线越平滑但计算稍慢。",
)

# ── 解析标的 ──────────────────────────────────────────────
raw_tickers = [
    t.strip().upper()
    for part in tickers_input.replace("\n", ",").split(",")
    for t in [part.strip()]
    if t.strip()
]
raw_tickers = list(dict.fromkeys(raw_tickers))  # deduplicate, preserve order

if len(raw_tickers) < 2:
    st.warning("⚠️ 请至少输入 **2 个**标的代码才能进行组合优化。")
    st.stop()


# ── 数据下载 ──────────────────────────────────────────────
@st.cache_data(ttl=600)
def _download_prices(tickers: tuple[str, ...], period: str) -> pd.DataFrame:
    """Download adjusted close prices from Yahoo Finance."""
    try:
        raw = yf.download(
            list(tickers), period=period, progress=False, auto_adjust=True
        )
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw[["Close"]] if "Close" in raw.columns else raw
        return prices.dropna(how="all")
    except (urllib.error.URLError, requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as exc:
        _logger.warning("下载价格数据网络错误: %s", exc, exc_info=True)
        return pd.DataFrame()
    except Exception as exc:  # noqa: BLE001
        _logger.error("下载价格数据未预期错误: %s", exc, exc_info=True)
        return pd.DataFrame()


with st.spinner("正在下载历史价格数据…"):
    prices_df = _download_prices(tuple(raw_tickers), period)

if prices_df.empty:
    render_empty_state(
        title="无法获取历史价格数据",
        message="数据源（Yahoo Finance）暂时不可用，或所输入的标的代码无效。请检查网络连接或代码格式后重试。",
        icon="📡",
    )
    st.stop()

# Filter to only columns that exist in the downloaded data
available_tickers = [t for t in raw_tickers if t in prices_df.columns]
missing_tickers = [t for t in raw_tickers if t not in prices_df.columns]

if missing_tickers:
    st.warning(f"⚠️ 以下标的数据不可用，已跳过：{', '.join(missing_tickers)}")

if len(available_tickers) < 2:
    render_empty_state(
        title="有效标的不足",
        message=f"需要至少 2 个有有效数据的标的，当前仅找到 {len(available_tickers)} 个：{', '.join(available_tickers) or '无'}。",
        icon="📭",
    )
    st.stop()

prices_df = prices_df[available_tickers].dropna()

# Compute daily returns
returns_df = prices_df.pct_change().dropna()

if len(returns_df) < 60:
    st.error("❌ 历史数据不足（少于 60 个交易日），请选择更长的数据周期。")
    st.stop()

# ── 运行优化 ──────────────────────────────────────────────
try:
    with st.spinner("正在运行马科维茨均值-方差优化…"):
        result: EfficientFrontierResult = optimize_portfolio(
            returns_df=returns_df,
            risk_free_rate_pct=risk_free_rate,
            n_frontier_points=n_frontier,
        )
except ValueError as exc:
    st.error(f"优化失败：{exc}")
    st.stop()

# ── 核心指标 ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 最优组合结果")

tab_sharpe, tab_minvar = st.tabs(["🏆 最大夏普比率组合", "🛡️ 最小方差组合"])

def _render_portfolio_tab(stats, label: str) -> None:
    m1, m2, m3 = st.columns(3)
    m1.metric("📈 预期年化收益", f"{stats.annual_return:.2%}")
    m2.metric("📉 年化波动率", f"{stats.annual_volatility:.2%}")
    m3.metric("⚖️ 夏普比率", f"{stats.sharpe_ratio:.3f}")

    st.markdown(f"**{label} — 资产权重分配**")
    weight_rows = [
        {"标的": t, "权重": f"{w:.2%}", "权重数值": w}
        for t, w in sorted(stats.weights.items(), key=lambda x: -x[1])
        if w >= 0.001  # hide near-zero weights
    ]
    if weight_rows:
        weight_df = pd.DataFrame(weight_rows)
        # Bar chart for weights
        fig_bar = go.Figure(go.Bar(
            x=[r["标的"] for r in weight_rows],
            y=[r["权重数值"] for r in weight_rows],
            text=[r["权重"] for r in weight_rows],
            textposition="outside",
            marker_color="#636EFA",
        ))
        fig_bar.update_layout(**build_layout(
            yaxis_title="权重",
            yaxis_tickformat=".0%",
            showlegend=False,
            margin=dict(t=20, b=30),
        ))
        fig_bar.update_yaxes(range=[0, max(r["权重数值"] for r in weight_rows) * 1.2])
        st.plotly_chart(fig_bar, use_container_width=True)
        st.dataframe(weight_df.drop(columns=["权重数值"]), use_container_width=True, hide_index=True)

with tab_sharpe:
    _render_portfolio_tab(result.max_sharpe, "最大夏普比率组合")
with tab_minvar:
    _render_portfolio_tab(result.min_variance, "最小方差组合")

# ── 有效前沿图 ────────────────────────────────────────────
st.subheader("🌐 有效前沿（Efficient Frontier）")

ef = result.efficient_frontier

if ef.empty:
    render_empty_state(
        title="有效前沿计算失败",
        message="优化器未能找到足够的有效点，请尝试减少标的数量或更换数据周期。",
        icon="📭",
    )
else:
    fig_ef = go.Figure()

    # Efficient frontier curve
    fig_ef.add_trace(go.Scatter(
        x=ef["volatility"],
        y=ef["annual_return"],
        mode="lines+markers",
        name="有效前沿",
        line=dict(color="#636EFA", width=2),
        marker=dict(size=4),
        customdata=ef["sharpe_ratio"],
        hovertemplate=(
            "波动率: %{x:.2%}<br>"
            "年化收益: %{y:.2%}<br>"
            "夏普比率: %{customdata:.3f}<extra></extra>"
        ),
    ))

    # Max Sharpe point
    fig_ef.add_trace(go.Scatter(
        x=[result.max_sharpe.annual_volatility],
        y=[result.max_sharpe.annual_return],
        mode="markers",
        name="最大夏普",
        marker=dict(size=14, color="#FFD600", symbol="star"),
        hovertemplate=(
            f"最大夏普<br>波动率: {result.max_sharpe.annual_volatility:.2%}<br>"
            f"收益: {result.max_sharpe.annual_return:.2%}<br>"
            f"夏普: {result.max_sharpe.sharpe_ratio:.3f}<extra></extra>"
        ),
    ))

    # Min Variance point
    fig_ef.add_trace(go.Scatter(
        x=[result.min_variance.annual_volatility],
        y=[result.min_variance.annual_return],
        mode="markers",
        name="最小方差",
        marker=dict(size=12, color="#00CC96", symbol="diamond"),
        hovertemplate=(
            f"最小方差<br>波动率: {result.min_variance.annual_volatility:.2%}<br>"
            f"收益: {result.min_variance.annual_return:.2%}<br>"
            f"夏普: {result.min_variance.sharpe_ratio:.3f}<extra></extra>"
        ),
    ))

    # Individual asset scatter
    for ticker in result.tickers:
        ticker_ret = float(result.annual_returns[ticker])
        ticker_vol = float(result.cov_matrix.loc[ticker, ticker] ** 0.5)
        fig_ef.add_trace(go.Scatter(
            x=[ticker_vol],
            y=[ticker_ret],
            mode="markers+text",
            name=ticker,
            text=[ticker],
            textposition="top center",
            marker=dict(size=9, symbol="circle"),
            hovertemplate=(
                f"{ticker}<br>波动率: {ticker_vol:.2%}<br>"
                f"收益: {ticker_ret:.2%}<extra></extra>"
            ),
        ))

    fig_ef.update_layout(**build_layout(
        xaxis_title="年化波动率（风险）",
        yaxis_title="预期年化收益",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
    ))
    st.plotly_chart(fig_ef, use_container_width=True)

# ── 相关性热力图 ──────────────────────────────────────────
st.subheader("🔗 资产相关性矩阵")
corr = returns_df.corr()
fig_corr = go.Figure(go.Heatmap(
    z=corr.values,
    x=corr.columns.tolist(),
    y=corr.index.tolist(),
    colorscale="RdBu_r",
    zmin=-1, zmax=1,
    text=corr.round(2).values,
    texttemplate="%{text}",
    hovertemplate="%{y} vs %{x}: %{z:.3f}<extra></extra>",
))
fig_corr.update_layout(**build_layout(
    margin=dict(t=30, b=60, l=60),
    showlegend=False,
))
st.plotly_chart(fig_corr, use_container_width=True)
st.caption("值越接近 +1 正相关性越高（同涨同跌）；越接近 -1 负相关性越高（互相对冲）。组合中加入低相关资产可有效降低整体风险。")

# ── 年化统计摘要 ──────────────────────────────────────────
with st.expander("📋 各标的年化统计"):
    stats_rows = []
    for ticker in result.tickers:
        ret = float(result.annual_returns[ticker])
        vol = float(result.cov_matrix.loc[ticker, ticker] ** 0.5)
        sh = (ret - risk_free_rate / 100) / vol if vol > 0 else 0.0
        stats_rows.append({
            "标的": ticker,
            "年化收益": f"{ret:.2%}",
            "年化波动率": f"{vol:.2%}",
            "夏普比率": f"{sh:.3f}",
        })
    st.dataframe(pd.DataFrame(stats_rows), use_container_width=True, hide_index=True)

# ── 导出 ─────────────────────────────────────────────────
st.subheader("📤 导出数据")

sharpe_weights_df = pd.DataFrame([
    {"标的": t, "权重": w} for t, w in result.max_sharpe.weights.items()
])
minvar_weights_df = pd.DataFrame([
    {"标的": t, "权重": w} for t, w in result.min_variance.weights.items()
])
frontier_export_df = ef[["volatility", "annual_return", "sharpe_ratio"]].copy() if not ef.empty else pd.DataFrame()

_xlsx_bytes = dataframes_to_excel(
    sheets=[
        ("最大夏普组合权重", sharpe_weights_df),
        ("最小方差组合权重", minvar_weights_df),
        ("有效前沿", frontier_export_df),
        ("相关性矩阵", corr.reset_index().rename(columns={"index": "标的"})),
    ],
    title="投资组合优化报告",
)
st.download_button(
    "📊 下载分析报告 (Excel)",
    data=_xlsx_bytes,
    file_name="投资组合优化.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── 方法论说明 ────────────────────────────────────────────
with st.expander("ℹ️ 方法论说明"):
    st.markdown(f"""
**马科维茨均值-方差模型（Markowitz Mean-Variance Optimization）**

- 使用 Yahoo Finance 历史价格（{period}）计算日收益率，再年化（×252交易日）
- 通过 SciPy SLSQP 数值优化求解**最大夏普比率**和**最小方差**组合
- 权重约束：所有资产权重之和 = 1，且每个资产权重 ∈ [0, 1]（不允许卖空）
- 无风险利率：**{risk_free_rate:.1f}%**（用于夏普比率计算）
- 有效前沿：在最小方差收益到最高单资产收益之间均匀采样 {n_frontier} 个目标收益率，对每个目标求最小方差组合

**注意事项**：
1. 历史收益率和波动率不代表未来表现。
2. 优化结果对输入参数敏感，历史窗口选择会显著影响权重分配。
3. 本工具仅供学习和参考，不构成投资建议。
""")

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("📐 投资组合优化器 | 仅供参考，不构成投资建议 | 运行：`streamlit run app.py`")
