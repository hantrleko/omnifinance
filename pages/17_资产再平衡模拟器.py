"""资产再平衡模拟器 — 定期再平衡 vs 买入持有对比

模拟多种再平衡策略（日历/阈值）对投资组合的收益影响。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.navigation import track_recent_page
track_recent_page(st.session_state, 'rebalance')

from core.theme import inject_theme

inject_theme()

from core.chart_config import build_layout
from core.config import MSG
from core.currency import fmt, get_symbol

st.set_page_config(page_title="资产再平衡模拟器", page_icon="⚖️", layout="wide")
st.title("⚖️ 资产再平衡模拟器")
st.caption("对比定期再平衡、阈值再平衡与买入持有策略的长期收益差异")

sym = get_symbol()

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.header("📋 参数设置")

initial_value = st.sidebar.number_input("初始投资金额", min_value=10000.0, value=1000000.0, step=100000.0, format="%.0f")
years = st.sidebar.slider("投资年限", min_value=3, max_value=40, value=20)
rebal_fee_pct = st.sidebar.slider("每次再平衡手续费(%)", min_value=0.0, max_value=2.0, value=0.1, step=0.05)

st.sidebar.subheader("资产配置")
n_assets = st.sidebar.number_input("资产类别数", min_value=2, max_value=6, value=3, step=1)

asset_names: list[str] = []
target_weights: list[float] = []
expected_returns: list[float] = []
volatilities: list[float] = []

defaults_name = ["股票", "债券", "现金", "商品", "房产REITs", "黄金"]
defaults_weight = [60, 30, 10, 0, 0, 0]
defaults_return = [10.0, 4.0, 2.0, 6.0, 7.0, 5.0]
defaults_vol = [20.0, 5.0, 1.0, 15.0, 12.0, 18.0]

for i in range(int(n_assets)):
    with st.sidebar.expander(f"资产 #{i+1}", expanded=True):
        nm = st.text_input("名称", value=defaults_name[i % len(defaults_name)], key=f"rb_name_{i}")
        w = st.number_input("目标权重(%)", min_value=0, max_value=100, value=defaults_weight[i % len(defaults_weight)], step=5, key=f"rb_w_{i}")
        r = st.number_input("预期年化收益(%)", min_value=-10.0, max_value=30.0, value=defaults_return[i % len(defaults_return)], step=0.5, key=f"rb_r_{i}")
        v = st.number_input("年化波动率(%)", min_value=0.0, max_value=50.0, value=defaults_vol[i % len(defaults_vol)], step=1.0, key=f"rb_v_{i}")
        asset_names.append(nm)
        target_weights.append(w / 100)
        expected_returns.append(r / 100)
        volatilities.append(v / 100)

# Validate weights
weight_sum = sum(target_weights)
if abs(weight_sum - 1.0) > 0.01:
    st.sidebar.error(f"⚠️ 权重之和为 {weight_sum*100:.0f}%，需等于 100%")
    st.stop()

threshold_pct = st.sidebar.slider("阈值再平衡触发偏差(%)", min_value=1, max_value=20, value=5, step=1, help="某资产偏离目标超过此百分点时触发再平衡")

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

# ── Simulation ────────────────────────────────────────────
n_months = years * 12
rng = np.random.default_rng(42)

mu_m = [np.log(1 + r) / 12 for r in expected_returns]
sig_m = [v / np.sqrt(12) for v in volatilities]

# Generate monthly returns
monthly_returns = np.zeros((n_months, int(n_assets)))
for i in range(int(n_assets)):
    monthly_returns[:, i] = np.exp(rng.normal(mu_m[i], sig_m[i], n_months)) - 1

def simulate_strategy(
    strategy: str,
    track_weights: bool = False,
) -> tuple[list[float], int, float, list[list[float]] | None]:
    """Simulate a rebalancing strategy.

    Returns (portfolio_values, rebal_count, total_fees, weight_history|None).
    weight_history is a list of per-month weight vectors when track_weights=True.
    """
    n = int(n_assets)
    allocations = np.array([initial_value * w for w in target_weights])
    portfolio_values = [initial_value]
    rebal_count = 0
    total_fees = 0.0
    weight_history: list[list[float]] | None = [] if track_weights else None

    for m in range(n_months):
        for i in range(n):
            allocations[i] *= (1 + monthly_returns[m, i])

        total = allocations.sum()

        should_rebal = False
        if strategy == "monthly" or strategy == "quarterly" and (m + 1) % 3 == 0 or strategy == "annually" and (m + 1) % 12 == 0:
            should_rebal = True
        elif strategy == "threshold":
            current_weights = allocations / total if total > 0 else np.zeros(n)
            max_drift = max(abs(current_weights[i] - target_weights[i]) for i in range(n))
            if max_drift >= threshold_pct / 100:
                should_rebal = True

        if should_rebal and strategy != "buy_and_hold":
            fee = total * rebal_fee_pct / 100
            total -= fee
            total_fees += fee
            allocations = np.array([total * w for w in target_weights])
            rebal_count += 1

        portfolio_values.append(allocations.sum())

        if track_weights:
            t = allocations.sum()
            weight_history.append((allocations / t).tolist() if t > 0 else list(target_weights))  # type: ignore[union-attr]

    return portfolio_values, rebal_count, total_fees, weight_history


strategies = {
    "buy_and_hold": "📦 买入持有",
    "annually": "📅 年度再平衡",
    "quarterly": "📅 季度再平衡",
    "monthly": "📅 月度再平衡",
    "threshold": f"🎯 阈值再平衡 (±{threshold_pct}%)",
}

results: dict[str, dict[str, Any]] = {}
for key, label in strategies.items():
    values, count, fees, _wh = simulate_strategy(key)
    final = values[-1]
    total_return = (final / initial_value - 1) * 100
    ann_return = ((final / initial_value) ** (1 / years) - 1) * 100
    results[key] = {
        "label": label, "values": values, "rebal_count": count,
        "total_fees": fees, "final": final,
        "total_return": total_return, "ann_return": ann_return,
    }

# Drift data: track weights for buy-and-hold and threshold strategies
_bah_vals, _bah_cnt, _bah_fees, bah_weight_hist = simulate_strategy("buy_and_hold", track_weights=True)
_thr_vals, _thr_cnt, _thr_fees, thr_weight_hist = simulate_strategy("threshold", track_weights=True)

# ── Key metrics ───────────────────────────────────────────
st.markdown("---")
st.subheader("📊 策略对比总览")

best_key = max(results, key=lambda k: results[k]["final"])
cols = st.columns(len(strategies))
for idx, (key, data) in enumerate(results.items()):
    with cols[idx]:
        badge = " 🏆" if key == best_key else ""
        st.metric(f"{data['label']}{badge}", fmt(data["final"], decimals=0))
        st.caption(f"年化 {data['ann_return']:.2f}%")
        st.caption(f"再平衡 {data['rebal_count']} 次")
        st.caption(f"手续费 {fmt(data['total_fees'], decimals=0)}")

# ── Portfolio value chart ─────────────────────────────────
st.markdown("---")
st.subheader("📈 组合价值走势对比")

months_axis = list(range(n_months + 1))
fig = go.Figure()
colors = ["#6b7280", "#2563eb", "#10b981", "#f59e0b", "#ef4444"]
for idx, (key, data) in enumerate(results.items()):
    fig.add_trace(go.Scatter(
        x=months_axis, y=data["values"],
        mode="lines", name=data["label"],
        line=dict(width=2, color=colors[idx % len(colors)]),
    ))
fig.update_layout(**build_layout(
    title="各策略组合价值走势",
    xaxis_title="月份", yaxis_title=f"组合价值 ({sym})", yaxis_tickformat=",.0f",
))
st.plotly_chart(fig, use_container_width=True)

# ── Summary table ─────────────────────────────────────────
st.markdown("---")
st.subheader("📋 详细对比")

summary_rows = []
for key, data in results.items():
    summary_rows.append({
        "策略": data["label"],
        "终值": fmt(data["final"], decimals=0),
        "总收益率": f"{data['total_return']:.2f}%",
        "年化收益率": f"{data['ann_return']:.2f}%",
        "再平衡次数": data["rebal_count"],
        "累计手续费": fmt(data["total_fees"], decimals=0),
    })
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

# ── Drift Corridor Visualization ─────────────────────────
st.markdown("---")
st.subheader("📐 权重漂移走廊")
st.caption("显示各资产权重随时间偏离目标值的程度。蓝色=目标，橙色=买入持有漂移，绿色=阈值再平衡。")

_drift_asset_idx = st.selectbox(
    "选择资产",
    range(int(n_assets)),
    format_func=lambda i: asset_names[i],
    key="drift_asset_select",
)

if bah_weight_hist and thr_weight_hist:
    _months_x = list(range(1, n_months + 1))
    _target_w = target_weights[_drift_asset_idx]
    _bah_w = [row[_drift_asset_idx] * 100 for row in bah_weight_hist]
    _thr_w = [row[_drift_asset_idx] * 100 for row in thr_weight_hist]
    _target_line = [_target_w * 100] * n_months

    # Upper/lower threshold bands
    _upper = [(_target_w + threshold_pct / 100) * 100] * n_months
    _lower = [max(0.0, (_target_w - threshold_pct / 100) * 100)] * n_months

    fig_drift = go.Figure()

    # Threshold band
    fig_drift.add_trace(go.Scatter(
        x=_months_x, y=_upper, mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig_drift.add_trace(go.Scatter(
        x=_months_x, y=_lower, mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(251,191,36,0.15)",
        name=f"阈值带 ±{threshold_pct}%", hoverinfo="skip",
    ))
    # Target
    fig_drift.add_trace(go.Scatter(
        x=_months_x, y=_target_line, mode="lines",
        name=f"目标 {_target_w*100:.0f}%",
        line=dict(width=2, color="#2563eb", dash="dash"),
    ))
    # Buy-and-hold drift
    fig_drift.add_trace(go.Scatter(
        x=_months_x, y=_bah_w, mode="lines",
        name="买入持有漂移",
        line=dict(width=1.5, color="#f97316"),
        hovertemplate="第%{x}月<br>权重: %{y:.1f}%<extra></extra>",
    ))
    # Threshold rebalanced
    fig_drift.add_trace(go.Scatter(
        x=_months_x, y=_thr_w, mode="lines",
        name="阈值再平衡",
        line=dict(width=1.5, color="#10b981"),
        hovertemplate="第%{x}月<br>权重: %{y:.1f}%<extra></extra>",
    ))

    fig_drift.update_layout(**build_layout(
        xaxis_title="月份", yaxis_title="权重（%）",
        height=360,
    ))
    st.plotly_chart(fig_drift, use_container_width=True)

    # Max drift stats
    _max_bah_drift = max(abs(w - _target_w * 100) for w in _bah_w)
    _max_thr_drift = max(abs(w - _target_w * 100) for w in _thr_w)
    _dc1, _dc2 = st.columns(2)
    _dc1.metric(
        f"买入持有最大漂移（{asset_names[_drift_asset_idx]}）",
        f"{_max_bah_drift:.1f}pp",
        help="偏离目标权重的最大百分点数",
    )
    _dc2.metric(
        f"阈值再平衡最大漂移（{asset_names[_drift_asset_idx]}）",
        f"{_max_thr_drift:.1f}pp",
        delta=f"控制效果：漂移缩减 {(_max_bah_drift-_max_thr_drift)/_max_bah_drift*100:.0f}%" if _max_bah_drift > 0 else "—",
        delta_color="normal",
    )

st.markdown("---")
with st.expander("📖 再平衡策略说明"):
    st.markdown("""
**📦 买入持有**：初始配置后不做调整。简单省心，但资产漂移可能导致风险偏离目标。

**📅 日历再平衡**：按固定时间间隔（月/季/年）将配置恢复至目标权重。

**🎯 阈值再平衡**：当任一资产偏离目标权重超过设定阈值时触发再平衡。更灵活，减少不必要交易。

**要点**：再平衡可以控制风险、强制"低买高卖"，但过于频繁会增加交易成本。通常年度或阈值策略效果最佳。
""")

st.markdown("---")
st.caption("⚖️ 资产再平衡模拟器 | 运行命令：`streamlit run app.py`")

