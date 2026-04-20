"""外汇对冲计算器 — 汇率敞口评估与远期对冲分析

计算外汇敞口、远期汇率、对冲成本及利率平价关系。
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import MSG
from core.currency import fmt, get_symbol

st.set_page_config(page_title="外汇对冲计算器", page_icon="💱", layout="wide")
st.markdown("""<style>.block-container{padding-top:1.2rem}.stMetric{background-color:var(--secondary-background-color);border:1px solid var(--secondary-background-color);border-radius:8px;padding:14px}</style>""", unsafe_allow_html=True)
st.title("💱 外汇对冲计算器")
st.caption("评估多币种资产敞口，计算远期汇率与对冲成本（利率平价法）")

sym = get_symbol()

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.header("📋 参数设置")

st.sidebar.subheader("汇率与利率")

_default_spot = 7.25
try:
    from core.exchange_rates import get_rate as _get_rate, get_last_updated_str as _get_ts, is_live as _is_live
    _live_rate = _get_rate("USD", "CNY")
    if st.sidebar.button("获取实时 USD/CNY"):
        _default_spot = _live_rate
        st.sidebar.caption(f"已填入实时汇率 {_live_rate:.4f}（{'实时' if _is_live() else '离线参考'}，{_get_ts()}）")
    else:
        st.sidebar.caption(f"参考汇率 USD/CNY: {_live_rate:.4f}（{'实时' if _is_live() else '离线参考'}，{_get_ts()}）")
except Exception:
    pass

spot_rate = st.sidebar.number_input("即期汇率 (外币/本币)", min_value=0.001, value=_default_spot, step=0.01, format="%.4f", help="如 USD/CNY = 7.25")
domestic_rate = st.sidebar.slider("本币年化利率(%)", min_value=0.0, max_value=20.0, value=2.5, step=0.1, help="本国无风险利率")
foreign_rate = st.sidebar.slider("外币年化利率(%)", min_value=0.0, max_value=20.0, value=5.0, step=0.1, help="外国无风险利率")
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
c1.metric("📈 即期汇率", f"{spot_rate:.4f}")
c2.metric("📉 远期汇率", f"{forward_rate:.4f}", delta=f"{forward_premium:+.2f}%")
c3.metric("💰 总外币敞口", f"{total_foreign:,.0f}")
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
