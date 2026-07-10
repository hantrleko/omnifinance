"""高级资产配置 — 风险平价 (Risk Parity) 与 Black-Litterman 模型。

在均值-方差之外提供两种更稳健/更灵活的配置方法：
  - 风险平价：让每个资产对组合风险的贡献相等（或按自定义风险预算分配）。
  - Black-Litterman：以市场均衡收益为先验，叠加个人观点得到后验收益与权重。

计算逻辑全部下沉至 core/allocation.py，本文件仅负责 UI。
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.page_setup import init_page

init_page("高级资产配置", "🧬", "allocation")

from core.allocation import (
    View,
    allocation_comparison_table,
    black_litterman,
    risk_parity_weights,
)
from core.chart_config import apply_chart_config, build_layout, render_empty_state
from core.config import CFG
from core.glossary import render_glossary_sidebar
from core.market_cache import download_prices
from core.portfolio import optimize_portfolio

render_glossary_sidebar(page_key="portfolio")

st.title("🧬 高级资产配置")
st.caption("风险平价与 Black-Litterman：两种超越简单均值-方差的资产配置方法，并与最大夏普组合对比。")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 标的与参数")
tickers_input = st.sidebar.text_area(
    "输入标的代码（每行一个或逗号分隔）",
    value=CFG.backtest.default_portfolio,
    height=110,
    help="支持 Yahoo Finance 格式，如 AAPL、0700.HK、BTC-USD 等。至少输入 2 个标的。",
)
period = st.sidebar.selectbox("历史数据周期", ["1y", "2y", "3y", "5y"], index=1)
risk_free_rate = st.sidebar.number_input("无风险利率（%）", 0.0, 10.0, 2.0, 0.1, format="%.1f")

st.sidebar.divider()
st.sidebar.subheader("🧠 Black-Litterman 参数")
risk_aversion = st.sidebar.slider("风险厌恶系数 δ", 1.0, 5.0, 2.5, 0.1,
                                  help="市场整体风险厌恶程度，通常取 2~3。越大意味着均衡收益越高。")
tau = st.sidebar.slider("先验不确定性 τ", 0.01, 0.20, 0.05, 0.01,
                        help="对市场均衡收益的不确定程度，常用 0.025~0.05。")

# ── 解析标的 ──────────────────────────────────────────────
raw_tickers = [
    t.strip().upper()
    for part in tickers_input.replace("\n", ",").split(",")
    for t in [part.strip()]
    if t.strip()
]
raw_tickers = list(dict.fromkeys(raw_tickers))

if len(raw_tickers) < 2:
    st.warning("⚠️ 请至少输入 **2 个**标的代码。")
    st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def _download(tickers: tuple[str, ...], period: str) -> pd.DataFrame:
    return download_prices(tickers, period)


with st.spinner("正在下载历史价格数据…"):
    prices_df = _download(tuple(raw_tickers), period)

if prices_df.empty:
    render_empty_state(
        title="无法获取历史价格数据",
        message="数据源暂时不可用或标的代码无效，请检查后重试。",
        icon="📡",
    )
    st.stop()

available = [t for t in raw_tickers if t in prices_df.columns]
missing = [t for t in raw_tickers if t not in prices_df.columns]
if missing:
    st.warning(f"⚠️ 以下标的数据不可用，已跳过：{', '.join(missing)}")
if len(available) < 2:
    render_empty_state(title="有效标的不足", message="需要至少 2 个有有效数据的标的。", icon="📭")
    st.stop()

prices_df = prices_df[available].dropna()
returns_df = prices_df.pct_change().dropna()
if len(returns_df) < 60:
    st.error("❌ 历史数据不足（少于 60 个交易日），请选择更长的数据周期。")
    st.stop()

cov_annual = returns_df.cov() * 252

# ── 市场权重（用于 BL 先验；默认等权，可编辑） ─────────────
st.subheader("🌐 市场基准权重（Black-Litterman 先验）")
st.caption("默认按等权作为市场组合近似；如果你知道各标的的市值占比，可以在下方修改。")
mkt_cols = st.columns(min(len(available), 6))
market_weights: dict[str, float] = {}
for i, t in enumerate(available):
    with mkt_cols[i % len(mkt_cols)]:
        market_weights[t] = st.number_input(
            f"{t}", min_value=0.0, max_value=1.0,
            value=round(1.0 / len(available), 3), step=0.01,
            key=f"mkt_w_{t}", format="%.3f",
        )

# ── 个人观点输入 ──────────────────────────────────────────
st.subheader("💭 我的观点（可选）")
st.caption("绝对观点：\"某标的未来年化收益为 X%\"；相对观点：\"A 比 B 每年多涨 X%\"。观点越有信心，对权重的影响越大。")

n_views = st.number_input("观点数量", 0, 5, 0, help="不添加观点时，Black-Litterman 结果退化为市场均衡组合。")
views: list[View] = []
for v_idx in range(int(n_views)):
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1])
        with c1:
            view_type = st.selectbox("类型", ["绝对观点", "相对观点"], key=f"vtype_{v_idx}")
        with c2:
            asset_a = st.selectbox("标的 A", available, key=f"va_{v_idx}")
        asset_b = None
        if view_type == "相对观点":
            with c3:
                choices_b = [t for t in available if t != asset_a]
                asset_b = st.selectbox("标的 B（被跑赢方）", choices_b, key=f"vb_{v_idx}")
        with c4:
            exp_ret = st.number_input(
                "预期年化(%)" if view_type == "绝对观点" else "超额年化(%)",
                min_value=-50.0, max_value=100.0, value=10.0, step=1.0, key=f"vr_{v_idx}",
            )
        confidence = st.slider("观点信心", 0.05, 0.95, 0.5, 0.05, key=f"vc_{v_idx}")
        if view_type == "绝对观点":
            views.append(View(assets={asset_a: 1.0}, expected_return=exp_ret / 100, confidence=confidence))
        elif asset_b:
            views.append(View(assets={asset_a: 1.0, asset_b: -1.0}, expected_return=exp_ret / 100, confidence=confidence))

# ── 风险预算（风险平价扩展） ───────────────────────────────
with st.expander("⚖️ 自定义风险预算（可选，默认等风险贡献）"):
    st.caption("为每个资产设定目标风险贡献占比，留 0 表示按剩余份额均分。总和会自动归一化。")
    budget_cols = st.columns(min(len(available), 6))
    risk_budget: dict[str, float] = {}
    for i, t in enumerate(available):
        with budget_cols[i % len(budget_cols)]:
            risk_budget[t] = st.number_input(
                f"{t} 风险份额", min_value=0.0, max_value=1.0, value=0.0, step=0.05,
                key=f"rb_{t}", format="%.2f",
            )
    use_budget = any(v > 0 for v in risk_budget.values())

# ── 计算三种配置 ──────────────────────────────────────────
st.markdown("---")
try:
    with st.spinner("正在计算三种配置方案…"):
        rp = risk_parity_weights(cov_annual, risk_budget=risk_budget if use_budget else None)
        bl = black_litterman(
            cov_annual,
            market_weights,
            views=views,
            risk_aversion=risk_aversion,
            tau=tau,
            risk_free_rate_pct=risk_free_rate,
        )
        mv = optimize_portfolio(returns_df, risk_free_rate_pct=risk_free_rate, n_frontier_points=30)
except ValueError as exc:
    st.error(f"计算失败：{exc}")
    st.stop()

# ── 结果展示 ──────────────────────────────────────────────
tab_rp, tab_bl, tab_cmp = st.tabs(["⚖️ 风险平价", "🧠 Black-Litterman", "📊 三方案对比"])

with tab_rp:
    c1, c2 = st.columns(2)
    with c1:
        st.metric("组合年化波动率", f"{rp.portfolio_volatility:.2%}")
        rp_df = pd.DataFrame({
            "标的": list(rp.weights.keys()),
            "权重": [f"{w:.2%}" for w in rp.weights.values()],
            "风险贡献": [f"{rc:.2%}" for rc in rp.risk_contributions.values()],
        })
        st.dataframe(rp_df, hide_index=True, use_container_width=True)
        if not rp.converged:
            st.warning("⚠️ 求解器未完全收敛，结果仅供参考。")
    with c2:
        fig = go.Figure(go.Pie(
            labels=list(rp.weights.keys()),
            values=list(rp.weights.values()),
            hole=0.45,
            textinfo="label+percent",
        ))
        fig.update_layout(**build_layout(title="风险平价权重分布", height=360, showlegend=False))
        apply_chart_config(fig, key="rp_pie")
    st.info("💡 风险平价不依赖收益预测，只用协方差矩阵，因此对估计误差更稳健；低波动资产会获得更高权重。")

with tab_bl:
    bl_df = pd.DataFrame({
        "标的": available,
        "均衡收益(先验)": [f"{bl.equilibrium_returns[t]:.2%}" for t in available],
        "后验收益": [f"{bl.posterior_returns[t]:.2%}" for t in available],
        "BL 最优权重": [f"{bl.weights[t]:.2%}" for t in available],
    })
    st.dataframe(bl_df, hide_index=True, use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="均衡收益（先验）", x=available,
        y=[bl.equilibrium_returns[t] for t in available],
    ))
    fig.add_trace(go.Bar(
        name="后验收益（叠加观点）", x=available,
        y=[bl.posterior_returns[t] for t in available],
    ))
    fig.update_layout(**build_layout(
        title="先验 vs 后验预期收益", barmode="group", height=380,
        yaxis_tickformat=".1%",
    ))
    apply_chart_config(fig, key="bl_bar")
    if views:
        st.info(f"💡 已纳入 {len(views)} 条观点。信心越高，后验收益越向观点靠拢，组合权重偏移越明显。")
    else:
        st.info("💡 当前未添加观点，后验收益等于市场均衡收益，BL 组合即市场均衡组合。")

with tab_cmp:
    cmp_df = allocation_comparison_table({
        "风险平价": rp.weights,
        "Black-Litterman": bl.weights,
        "最大夏普(均值-方差)": mv.max_sharpe.weights,
    })
    fig = go.Figure()
    for scheme in cmp_df.columns:
        fig.add_trace(go.Bar(name=scheme, x=list(cmp_df.index), y=cmp_df[scheme].tolist()))
    fig.update_layout(**build_layout(
        title="三种配置方案权重对比", barmode="group", height=400, yaxis_tickformat=".0%",
    ))
    apply_chart_config(fig, key="cmp_bar")

    display_df = cmp_df.map(lambda x: f"{x:.2%}")
    display_df.index.name = "标的"
    st.dataframe(display_df, use_container_width=True)

    st.markdown(
        """
**如何选择？**

| 方案 | 适合场景 | 主要弱点 |
|---|---|---|
| 风险平价 | 不想预测收益、追求风险分散 | 可能过度配置低波动资产 |
| Black-Litterman | 有明确主观观点、想控制观点影响力 | 需要设定市场权重与信心参数 |
| 最大夏普 | 完全相信历史收益的延续性 | 对输入收益极度敏感，权重易极端 |
"""
    )

st.caption("⚠️ 以上结果基于历史数据与模型假设，不构成投资建议。")
