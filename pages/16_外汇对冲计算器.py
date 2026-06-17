"""外汇对冲计算器 — 汇率敞口评估与远期对冲分析

计算外汇敞口、远期汇率、对冲成本及利率平价关系。
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.page_setup import init_page
init_page("外汇对冲计算器", "💹", "fx")
from core.chart_config import build_layout
from core.config import MSG
from core.currency import fmt, get_symbol

st.title("💱 外汇对冲计算器")
st.caption("评估多币种资产敞口，计算远期汇率与对冲成本（利率平价法）")

sym = get_symbol()

# ── Currency pair registry ────────────────────────────────
_CURRENCY_PAIRS: dict[str, dict] = {
    "USD/CNY": {"base": "USD", "quote": "CNY", "default_spot": 7.25, "default_rd": 2.5, "default_rf": 5.0, "label": "美元/人民币"},
    "EUR/CNY": {"base": "EUR", "quote": "CNY", "default_spot": 7.85, "default_rd": 2.5, "default_rf": 4.0, "label": "欧元/人民币"},
    "GBP/CNY": {"base": "GBP", "quote": "CNY", "default_spot": 9.20, "default_rd": 2.5, "default_rf": 5.25, "label": "英镑/人民币"},
    "JPY/CNY": {"base": "JPY", "quote": "CNY", "default_spot": 0.048, "default_rd": 2.5, "default_rf": 0.1, "label": "日元/人民币"},
    "HKD/CNY": {"base": "HKD", "quote": "CNY", "default_spot": 0.928, "default_rd": 2.5, "default_rf": 5.5, "label": "港币/人民币"},
    "AUD/USD": {"base": "AUD", "quote": "USD", "default_spot": 0.655, "default_rd": 5.25, "default_rf": 4.35, "label": "澳元/美元"},
    "USD/JPY": {"base": "USD", "quote": "JPY", "default_spot": 149.5, "default_rd": 0.1, "default_rf": 5.25, "label": "美元/日元"},
    "EUR/USD": {"base": "EUR", "quote": "USD", "default_spot": 1.085, "default_rd": 5.25, "default_rf": 4.0, "label": "欧元/美元"},
    "GBP/USD": {"base": "GBP", "quote": "USD", "default_spot": 1.265, "default_rd": 5.25, "default_rf": 5.25, "label": "英镑/美元"},
    "USD/SGD": {"base": "USD", "quote": "SGD", "default_spot": 1.345, "default_rd": 3.7, "default_rf": 5.25, "label": "美元/新加坡元"},
}

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.header("📋 参数设置")

st.sidebar.subheader("货币对选择")
_pair_keys = list(_CURRENCY_PAIRS.keys())
_pair_labels = [f"{k} — {v['label']}" for k, v in _CURRENCY_PAIRS.items()]
_pair_idx = st.sidebar.selectbox(
    "货币对",
    range(len(_pair_keys)),
    format_func=lambda i: _pair_labels[i],
    key="fx_pair_select",
)
_selected_pair = _pair_keys[_pair_idx]
_pair_info = _CURRENCY_PAIRS[_selected_pair]

st.sidebar.subheader("汇率与利率")

_default_spot = _pair_info["default_spot"]
try:
    from core.exchange_rates import get_last_updated_str as _get_ts
    from core.exchange_rates import get_rate as _get_rate
    from core.exchange_rates import is_live as _is_live
    _live_rate = _get_rate(_pair_info["base"], _pair_info["quote"])
    if st.sidebar.button(f"获取实时 {_selected_pair}"):
        _default_spot = _live_rate
        st.sidebar.caption(f"已填入实时汇率 {_live_rate:.4f}（{'实时' if _is_live() else '离线参考'}，{_get_ts()}）")
    else:
        st.sidebar.caption(f"参考汇率 {_selected_pair}: {_live_rate:.4f}（{'实时' if _is_live() else '离线参考'}，{_get_ts()}）")
except Exception:
    pass

spot_rate = st.sidebar.number_input(f"即期汇率 ({_selected_pair})", min_value=0.001, value=_default_spot, step=0.001, format="%.4f", help=f"如 {_selected_pair} = {_pair_info['default_spot']}")
domestic_rate = st.sidebar.slider(f"{_pair_info['quote']} 年化利率(%)", min_value=0.0, max_value=20.0, value=float(_pair_info["default_rd"]), step=0.1, help="报价货币（本币）无风险利率")
foreign_rate = st.sidebar.slider(f"{_pair_info['base']} 年化利率(%)", min_value=0.0, max_value=20.0, value=float(_pair_info["default_rf"]), step=0.1, help="基础货币（外币）无风险利率")
hedge_period_months = st.sidebar.slider("对冲期限(月)", min_value=1, max_value=60, value=12, step=1)

st.sidebar.subheader("资产敞口")
num_positions = st.sidebar.number_input("外币资产笔数", min_value=1, max_value=10, value=3, step=1)

positions: list[dict[str, Any]] = []
for i in range(int(num_positions)):
    with st.sidebar.expander(f"资产 #{i+1}", expanded=(i < 3)):
        name = st.text_input("名称", value=["美股组合", "海外债券", "外币存款"][i % 3], key=f"fx_name_{i}")
        amount_foreign = st.number_input("外币金额", min_value=0.0, value=[100000.0, 50000.0, 200000.0][i % 3], step=10000.0, key=f"fx_amt_{i}")
        if amount_foreign > 0:
            positions.append({"name": name, "amount": amount_foreign})

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

if not positions:
    st.warning("请添加至少一笔外币资产。")
    st.stop()

# ── Calculations ──────────────────────────────────────────
# Covered Interest Rate Parity: F = S × (1 + r_d × T) / (1 + r_f × T)
T = hedge_period_months / 12
r_d = domestic_rate / 100
r_f = foreign_rate / 100

forward_rate = spot_rate * (1 + r_d * T) / (1 + r_f * T)
forward_premium = (forward_rate - spot_rate) / spot_rate * 100

total_foreign = sum(p["amount"] for p in positions)
total_domestic_spot = total_foreign * spot_rate
total_domestic_forward = total_foreign * forward_rate
hedge_cost = total_domestic_forward - total_domestic_spot
hedge_cost_pct = hedge_cost / total_domestic_spot * 100 if total_domestic_spot > 0 else 0

# ── Key metrics ───────────────────────────────────────────
st.markdown("---")
st.subheader("📊 对冲分析概览")

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"📈 即期汇率 ({_selected_pair})", f"{spot_rate:.4f}")
c2.metric(f"📉 远期汇率 ({_selected_pair})", f"{forward_rate:.4f}", delta=f"{forward_premium:+.2f}%")
c3.metric(f"💰 总 {_pair_info['base']} 敞口", f"{total_foreign:,.0f}")
c4.metric("🛡️ 对冲成本", fmt(abs(hedge_cost), decimals=0), delta=f"{hedge_cost_pct:+.2f}%")

if forward_rate < spot_rate:
    st.success(f"✅ 远期汇率低于即期（本币升值预期）。锁定远期可以以更优汇率结汇，节省 **{fmt(abs(hedge_cost), decimals=0)}**。")
else:
    st.warning(f"⚠️ 远期汇率高于即期（本币贬值预期）。对冲成本为 **{fmt(abs(hedge_cost), decimals=0)}**（占敞口 {abs(hedge_cost_pct):.2f}%），需权衡风险与成本。")

# ── Position breakdown ────────────────────────────────────
st.markdown("---")
st.subheader("📋 各资产敞口详情")

pos_rows = []
for p in positions:
    pos_rows.append({
        "资产名称": p["name"],
        "外币金额": f"{p['amount']:,.0f}",
        "即期本币值": fmt(p["amount"] * spot_rate, decimals=0),
        "远期本币值": fmt(p["amount"] * forward_rate, decimals=0),
        "对冲损益": fmt(p["amount"] * (forward_rate - spot_rate), decimals=0),
    })
st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)

# ── Scenario analysis ────────────────────────────────────
st.markdown("---")
st.subheader("📈 汇率情景分析")
st.caption("不同汇率变动下的资产价值变化（未对冲 vs 已对冲）")

scenarios = [spot_rate * f for f in [0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15]]
scenario_rows = []
for s in scenarios:
    unhedged = total_foreign * s
    hedged = total_foreign * forward_rate
    pnl_unhedged = unhedged - total_domestic_spot
    pnl_hedged = hedged - total_domestic_spot
    scenario_rows.append({
        "汇率": f"{s:.4f}",
        "变动": f"{(s / spot_rate - 1) * 100:+.1f}%",
        "未对冲本币值": fmt(unhedged, decimals=0),
        "已对冲本币值": fmt(hedged, decimals=0),
        "未对冲损益": fmt(pnl_unhedged, decimals=0),
        "已对冲损益": fmt(pnl_hedged, decimals=0),
    })
st.dataframe(pd.DataFrame(scenario_rows), use_container_width=True, hide_index=True)

# Chart
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=[s for s in scenarios], y=[total_foreign * s for s in scenarios],
    mode="lines+markers", name="未对冲",
    line=dict(width=2.5, color="#ef4444"),
))
fig.add_hline(y=total_foreign * forward_rate, line_dash="dash", line_color="#2563eb",
              annotation_text=f"已对冲: {fmt(total_foreign * forward_rate, decimals=0)}")
fig.update_layout(**build_layout(
    title="汇率变动敏感度分析",
    xaxis_title="即期汇率",
    yaxis_title=f"本币价值 ({sym})",
    yaxis_tickformat=",.0f",
))
st.plotly_chart(fig, use_container_width=True)

# ── Interest rate parity explanation ──────────────────────
st.markdown("---")
with st.expander("📖 利率平价理论说明"):
    st.markdown(f"""
**抛补利率平价 (Covered Interest Rate Parity)**

远期汇率 = 即期汇率 × (1 + 本币利率 × T) / (1 + 外币利率 × T)

- 即期汇率: **{spot_rate:.4f}**
- 本币利率: **{domestic_rate}%** → 外币利率: **{foreign_rate}%**
- 对冲期限: **{hedge_period_months}** 个月
- 计算远期: {spot_rate:.4f} × (1 + {r_d:.4f} × {T:.4f}) / (1 + {r_f:.4f} × {T:.4f}) = **{forward_rate:.4f}**

**解读**：利率较高的货币远期贴水（远期比即期便宜），利率较低的货币远期升水。
这确保了无套利条件下，两种货币的无风险投资收益等价。
""")

st.markdown("---")
st.caption("💱 外汇对冲计算器 | 运行命令：`streamlit run app.py`")

