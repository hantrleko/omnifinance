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
from core.page_setup import init_page
init_page("投资组合优化器", "📐", "portfolio")
import yfinance as yf

from core.chart_config import build_layout, render_empty_state
from core.config import CFG
from core.currency import currency_selector
from core.export import dataframes_to_excel
from core.portfolio import EfficientFrontierResult, optimize_portfolio

# ── 模块级 logger ─────────────────────────────────────────
_logger = logging.getLogger(__name__)

# ── 页面配置 ──────────────────────────────────────────────
st.title("📐 投资组合优化器")
st.caption("基于马科维茨均值-方差模型，计算最大夏普比率组合与最小方差组合，并展示有效前沿。")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 标的与参数")

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

st.sidebar.divider()
st.sidebar.subheader("⚖️ 权重约束")
enable_constraints = st.sidebar.checkbox("启用权重约束", value=False, help="限制单一资产的最高/最低持仓比例")
max_weight = 1.0
min_weight = 0.0
if enable_constraints:
    max_weight = st.sidebar.slider(
        "单资产最大权重（%）",
        min_value=10,
        max_value=100,
        value=60,
        step=5,
        help="例如：设为 60% 表示任何单一资产不超过总组合的 60%",
    ) / 100.0
    min_weight = st.sidebar.slider(
        "单资产最小权重（%）",
        min_value=0,
        max_value=20,
        value=0,
        step=1,
        help="例如：设为 5% 表示每个资产至少占总组合的 5%",
    ) / 100.0
    # Note: actual constraint validation is done after tickers are parsed below

# ── 解析标的 ──────────────────────────────────────────────
raw_tickers = [
    t.strip().upper()
    for part in tickers_input.replace("\n", ",").split(",")
    for t in [part.strip()]
    if t.strip()
]
raw_tickers = list(dict.fromkeys(raw_tickers))  # deduplicate, preserve order

# Validate weight constraints now that we know the number of tickers
if enable_constraints and min_weight * len(raw_tickers) > 1.0:
    st.warning(f"⚠️ 最小权重 {min_weight:.0%} × {len(raw_tickers)} 个资产 = {min_weight * len(raw_tickers):.0%}，超过 100%！请调低最小权重。")
    st.stop()

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

# ── 运行优化（带缓存，避免每次调参重新优化） ────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def _cached_optimize(
    _returns_df: pd.DataFrame,
    risk_free_rate: float,
    n_frontier: int,
) -> EfficientFrontierResult:
    """Cached wrapper around optimize_portfolio.

    Leading underscore on *_returns_df* tells Streamlit not to hash the
    DataFrame by value (it uses its contents implicitly via the other args
    and the upstream price-download TTL cache).
    """
    return optimize_portfolio(
        returns_df=_returns_df,
        risk_free_rate_pct=risk_free_rate,
        n_frontier_points=n_frontier,
    )


@st.cache_data(ttl=600, show_spinner=False)
def _cached_optimize_constrained(
    _returns_df: pd.DataFrame,
    risk_free_rate: float,
    n_frontier: int,
    max_weight: float,
    min_weight: float,
) -> EfficientFrontierResult:
    return optimize_portfolio(
        returns_df=_returns_df,
        risk_free_rate_pct=risk_free_rate,
        n_frontier_points=n_frontier,
        max_weight_per_asset=max_weight,
        min_weight_per_asset=min_weight,
    )


try:
    with st.spinner("正在运行马科维茨均值-方差优化…"):
        if enable_constraints:
            result: EfficientFrontierResult = _cached_optimize_constrained(
                returns_df,
                risk_free_rate,
                n_frontier,
                max_weight,
                min_weight,
            )
        else:
            result: EfficientFrontierResult = _cached_optimize(
                returns_df,
                risk_free_rate,
                n_frontier,
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
        ticker_vol = float(max(0.0, result.cov_matrix.loc[ticker, ticker]) ** 0.5)
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
        vol = float(max(0.0, result.cov_matrix.loc[ticker, ticker]) ** 0.5)
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

# ── Black-Litterman 模型 ───────────────────────────────────
st.markdown("---")
st.subheader("🎯 Black-Litterman 贝叶斯组合优化")
st.caption("在均衡市场隐含收益基础上，融合主观观点，通过贝叶斯后验推断优化组合权重。")

with st.expander("⚙️ Black-Litterman 参数与观点输入", expanded=True):
    bl_tau = st.slider("τ（先验不确定性）", min_value=0.01, max_value=1.0, value=0.05, step=0.01,
                       help="越大表示对先验均衡收益越不确定，观点影响越大")

    n_tickers = len(result.tickers)
    tickers_list = list(result.tickers)

    st.markdown("**投资者主观观点（最多 5 条）**")
    st.caption("每条观点格式：选择资产 + 预期超额年化收益率（正/负）。未添加观点时等价于纯均值-方差。")

    bl_views: list[tuple[str, float]] = []
    for vi in range(min(5, n_tickers)):
        _vcol1, _vcol2, _vcol3 = st.columns([3, 2, 1])
        _vticker = _vcol1.selectbox(f"观点 {vi+1} 资产", ["（不设置）"] + tickers_list, key=f"bl_ticker_{vi}")
        _vreturn = _vcol2.number_input("预期年化超额收益（%）", min_value=-50.0, max_value=100.0, value=0.0, step=0.5, format="%.1f", key=f"bl_ret_{vi}")
        if _vticker != "（不设置）":
            bl_views.append((_vticker, _vreturn / 100))

if st.button("🔄 运行 Black-Litterman 优化", key="bl_run"):
    try:
        import numpy as np
        from scipy.optimize import minimize

        mu = np.array([result.annual_returns[t] for t in tickers_list])
        cov = result.cov_matrix.values.copy()
        n = len(tickers_list)

        eq_weights = np.ones(n) / n
        _port_var = float(eq_weights @ cov @ eq_weights)
        lam = (float(mu @ eq_weights) - risk_free_rate / 100) / _port_var if _port_var > 1e-10 else 1.0
        pi_eq = lam * cov @ eq_weights

        if bl_views:
            P = np.zeros((len(bl_views), n))
            q = np.zeros(len(bl_views))
            for vi, (vt, vr) in enumerate(bl_views):
                tidx = tickers_list.index(vt)
                P[vi, tidx] = 1.0
                q[vi] = vr

            omega = np.diag(np.diag(bl_tau * P @ cov @ P.T))
            tau_cov_inv = np.linalg.inv(bl_tau * cov)
            omega_inv = np.linalg.inv(omega)
            M_inv = tau_cov_inv + P.T @ omega_inv @ P
            bl_mu = np.linalg.solve(M_inv, tau_cov_inv @ pi_eq + P.T @ omega_inv @ q)
        else:
            bl_mu = pi_eq.copy()

        def _neg_sharpe(w):
            port_ret = bl_mu @ w
            port_vol = np.sqrt(w @ cov @ w)
            return -(port_ret - risk_free_rate / 100) / port_vol if port_vol > 1e-8 else 0.0

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        bounds = [(0.0, 1.0)] * n
        x0 = np.ones(n) / n
        res_bl = minimize(_neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)

        if res_bl.success:
            bl_weights = dict(zip(tickers_list, res_bl.x, strict=True))
            bl_ret = float(bl_mu @ res_bl.x)
            bl_vol = float(np.sqrt(res_bl.x @ cov @ res_bl.x))
            bl_sr = (bl_ret - risk_free_rate / 100) / bl_vol if bl_vol > 0 else 0.0

            st.markdown("#### Black-Litterman 最优权重")
            _bl_c1, _bl_c2, _bl_c3 = st.columns(3)
            _bl_c1.metric("预期年化收益", f"{bl_ret:.2%}")
            _bl_c2.metric("年化波动率", f"{bl_vol:.2%}")
            _bl_c3.metric("夏普比率", f"{bl_sr:.3f}")

            fig_bl = go.Figure(go.Bar(
                x=list(bl_weights.keys()),
                y=[round(v * 100, 2) for v in bl_weights.values()],
                marker_color="#00CC96",
                text=[f"{v*100:.1f}%" for v in bl_weights.values()],
                textposition="outside",
            ))
            fig_bl.update_layout(**build_layout(
                xaxis_title="资产", yaxis_title="权重（%）",
                yaxis_range=[0, max(bl_weights.values()) * 120],
                showlegend=False, height=350,
            ))
            st.plotly_chart(fig_bl, use_container_width=True)

            with st.expander("📋 BL 权重与均衡权重对比"):
                _bl_rows = [{
                    "资产": t,
                    "均衡权重": f"{eq_weights[i]*100:.1f}%",
                    "BL权重": f"{res_bl.x[i]*100:.1f}%",
                    "均衡隐含收益": f"{pi_eq[i]*100:.2f}%",
                    "BL预期收益": f"{bl_mu[i]*100:.2f}%",
                } for i, t in enumerate(tickers_list)]
                st.dataframe(pd.DataFrame(_bl_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("Black-Litterman 优化求解失败，请检查参数设置。")
    except Exception as _bl_exc:
        st.error(f"Black-Litterman 计算错误：{_bl_exc}")

with st.expander("ℹ️ Black-Litterman 说明"):
    st.markdown(f"""
**Black-Litterman 贝叶斯融合流程**

1. **均衡隐含收益 (π)**：以等权重组合的超额收益和风险厌恶系数 λ 反推：π = λ·Σ·w_eq
2. **投资者观点 (P, q)**：对所选资产设置预期超额收益，构建观点矩阵
3. **贝叶斯后验 (μ_BL)**：融合先验均衡与观点后验：μ_BL = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹[(τΣ)⁻¹π + PᵀΩ⁻¹q]
4. **再优化**：用 μ_BL 替代原始收益，SLSQP 求解最大夏普组合

τ 参数（当前 **{bl_tau}**）控制先验不确定性：τ 越大，观点权重越高。
""")

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("📐 投资组合优化器 | 仅供参考，不构成投资建议 | 运行：`streamlit run app.py`")

