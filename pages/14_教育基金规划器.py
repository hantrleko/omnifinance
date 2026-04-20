"""教育基金规划器 — 子女教育费用模拟与策略规划

支持教育通胀调整、奖学金场景分析、月度定投模拟。
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import fmt, get_symbol
from core.education import calculate_education_fund

st.set_page_config(page_title="教育基金规划器", page_icon="🏫", layout="wide")
st.title("🏫 教育基金规划器")
st.caption("规划子女教育经费，模拟定投增长路径，评估奖学金影响")

# ── Sidebar inputs ────────────────────────────────────────
st.sidebar.header("📋 参数设置")
child_age = st.sidebar.number_input("孩子当前年龄", min_value=0, max_value=17, value=5, step=1)
target_age = st.sidebar.number_input("预计入学年龄", min_value=child_age + 1, max_value=30, value=18, step=1)
current_cost = st.sidebar.number_input("当前年学费（今日币值）", min_value=0.0, value=50000.0, step=5000.0, format="%.0f")
edu_inflation = st.sidebar.slider("教育通胀率(%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5, help="教育成本通常高于一般通胀，中国近年约5-7%")
current_savings = st.sidebar.number_input("已有教育储蓄", min_value=0.0, value=30000.0, step=10000.0, format="%.0f")
monthly_saving = st.sidebar.number_input("每月定投金额", min_value=0.0, value=3000.0, step=500.0, format="%.0f")
annual_return = st.sidebar.slider("预期年化收益率(%)", min_value=0.0, max_value=15.0, value=5.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

# ── Calculate ─────────────────────────────────────────────
result = calculate_education_fund(
    child_age=child_age,
    target_age=target_age,
    current_cost=current_cost,
    education_inflation_pct=edu_inflation,
    current_savings=current_savings,
    monthly_saving=monthly_saving,
    annual_return_pct=annual_return,
)

sym = get_symbol()

# ── Key metrics ───────────────────────────────────────────
st.markdown("---")
st.subheader("📊 规划概览")

c1, c2, c3, c4 = st.columns(4)
c1.metric("📅 距入学", f"{result.years_to_goal} 年")
c2.metric("🎓 届时总费用", fmt(result.future_cost, decimals=0))
c3.metric("💰 预计积累", fmt(result.projected_fund, decimals=0))
if result.gap <= 0:
    c4.metric("✅ 评估", "资金充足")
else:
    c4.metric("⚠️ 资金缺口", fmt(result.gap, decimals=0))

if result.gap > 0:
    st.warning(f"按当前计划，入学时资金缺口约 **{fmt(result.gap, decimals=0)}**。建议每月至少追加 **{fmt(result.monthly_needed, decimals=0)}** 的定投。")
else:
    surplus = -result.gap
    st.success(f"✅ 当前计划可充分覆盖教育费用，预计盈余 **{fmt(surplus, decimals=0)}**。")

# ── Growth chart ──────────────────────────────────────────
st.markdown("---")
st.subheader("📈 资金增长路径")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=result.schedule["孩子年龄"], y=result.schedule["年末余额"],
    mode="lines+markers", name="基金余额",
    line=dict(width=3, color="#2563eb"),
    fill="tozeroy", fillcolor="rgba(37,99,235,0.1)",
))
fig.add_trace(go.Scatter(
    x=result.schedule["孩子年龄"], y=result.schedule["目标值"],
    mode="lines", name="目标进度线",
    line=dict(width=2, dash="dash", color="#ef4444"),
))
fig.update_layout(**build_layout(
    title="教育基金增长 vs 目标进度",
    xaxis_title="孩子年龄",
    yaxis_title=f"金额 ({sym})",
    yaxis_tickformat=",.0f",
))
st.plotly_chart(fig, use_container_width=True)

# ── Yearly table ──────────────────────────────────────────
st.markdown("---")
st.subheader("📋 逐年明细")
display_df = result.schedule.copy()
for col in ["年初余额", "当年投入", "当年收益", "年末余额", "目标值"]:
    display_df[col] = display_df[col].apply(lambda x: fmt(x, decimals=0))
st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Scholarship analysis ─────────────────────────────────
st.markdown("---")
st.subheader("🎖️ 奖学金场景分析")
st.caption("不同奖学金覆盖比例下的资金充足性评估")

for col in ["实际费用", "资金缺口"]:
    result.scholarship_scenarios[col] = result.scholarship_scenarios[col].apply(lambda x: fmt(x, decimals=0))
st.dataframe(result.scholarship_scenarios, use_container_width=True, hide_index=True)

# ── Monthly deposit comparison ────────────────────────────
st.markdown("---")
st.subheader("💡 定投金额对比")

deposits_to_compare = [monthly_saving * f for f in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]]
comp_rows = []
for dep in deposits_to_compare:
    r = calculate_education_fund(
        child_age=child_age, target_age=target_age, current_cost=current_cost,
        education_inflation_pct=edu_inflation, current_savings=current_savings,
        monthly_saving=dep, annual_return_pct=annual_return,
    )
    comp_rows.append({
        "月定投": fmt(dep, decimals=0),
        "预计积累": fmt(r.projected_fund, decimals=0),
        "缺口/盈余": fmt(-r.gap, decimals=0) if r.gap <= 0 else f"-{fmt(r.gap, decimals=0)}",
        "状态": "✅ 充足" if r.gap <= 0 else "⚠️ 不足",
    })
import pandas as pd
st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("🏫 教育基金规划器 | 运行命令：`streamlit run app.py`")
