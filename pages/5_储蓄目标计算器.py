"""储蓄目标达成计算器

计算在给定报酬率与每月投入下，何时能达成储蓄目标。
逐月复利模拟 + Plotly 可视化。

v1.4: 核心计算已下沉到 core/savings.py；图表货币符号动态引用。
"""

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.chart_config import build_layout
from core.currency import currency_selector, fmt, get_symbol
from core.savings import SavingsResult, calculate_savings_goal
from core.storage import scheme_manager_ui

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="储蓄目标计算器", page_icon="🎯", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .stMetric { background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 8px; padding: 14px; }
  .achieved { background: #1b5e20 !important; border-color: #4caf50 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 储蓄目标达成计算器")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 参数设置")
currency_selector()

current_savings = st.sidebar.number_input(
    "目前储蓄金额（元）", min_value=0.0, max_value=5_000_000.0,
    value=50_000.0, step=10_000.0, format="%.0f",
)
goal_amount = st.sidebar.number_input(
    "目标金额（元）", min_value=100_000.0, max_value=10_000_000.0,
    value=1_000_000.0, step=50_000.0, format="%.0f",
)
annual_rate = st.sidebar.number_input(
    "预期年化报酬率（%）", min_value=0.0, max_value=15.0,
    value=6.0, step=0.1, format="%.1f",
)
monthly_deposit = st.sidebar.number_input(
    "每月固定投入（元）", min_value=0.0, max_value=200_000.0,
    value=10_000.0, step=1_000.0, format="%.0f",
)
start_date = st.sidebar.date_input("计算起始日期", value=date.today())

st.sidebar.divider()

# 即时调整滑杆
st.sidebar.subheader("⚡ 快速调整每月投入")
monthly_deposit_slider = st.sidebar.slider(
    "每月投入（滑杆）",
    min_value=0, max_value=200_000, value=int(monthly_deposit), step=1_000,
    format=f"{get_symbol()}%d",
)
effective_deposit = float(monthly_deposit_slider)
st.sidebar.caption(f"当前生效：每月 {fmt(effective_deposit, decimals=0)}")

scheme_manager_ui("savings", {
    "current_savings": current_savings,
    "goal_amount": goal_amount,
    "annual_rate": annual_rate,
    "monthly_deposit": monthly_deposit,
})

# ══════════════════════════════════════════════════════════
#  执行计算
# ══════════════════════════════════════════════════════════

result = calculate_savings_goal(current_savings, goal_amount, annual_rate, effective_deposit)

st.session_state["dashboard_savings"] = {
    "months_needed": result.months_needed,
    "total_interest": result.total_interest,
}

sym = get_symbol()

# ── 已达成特殊情况 ────────────────────────────────────────
st.markdown("---")

if current_savings >= goal_amount:
    st.balloons()
    st.success(f"🎉 **已达成目标！** 目前储蓄 {fmt(current_savings, decimals=0)} 已超过目标 {fmt(goal_amount, decimals=0)}")
    st.stop()

if not result.reached:
    st.error("⚠️ 以当前参数设定，无法在 100 年内达成目标。请增加每月投入或提高报酬率。")
    st.stop()

# ── 核心指标卡片 ──────────────────────────────────────────
st.subheader("📊 达成概览")

years_needed = result.months_needed // 12
months_remain = result.months_needed % 12
time_str = f"{years_needed} 年 {months_remain} 个月" if years_needed > 0 else f"{months_remain} 个月"

interest_ratio = (result.total_interest / goal_amount * 100) if goal_amount > 0 else 0

target_month = start_date.month + result.months_needed
target_year = start_date.year + (target_month - 1) // 12
target_month = (target_month - 1) % 12 + 1
target_date_str = f"{target_year} 年 {target_month} 月"

c1, c2, c3, c4 = st.columns(4)
c1.metric("⏰ 预估达成时间", time_str, delta=target_date_str, delta_color="off")
c2.metric("💵 总需投入本金", fmt(result.total_deposited, decimals=0))
c3.metric("📈 复利贡献金额", fmt(result.total_interest, decimals=0))
c4.metric("🎯 复利贡献占比", f"{interest_ratio:.1f}%")

st.subheader("🧭 一页结论")
if result.months_needed <= 24:
    st.success("结论：目标可在较短周期内达成。")
    st.caption(f"原因：按当前参数预计 {time_str} 达成，复利贡献约 {fmt(result.total_interest, decimals=0)}。")
    st.caption("下一步：保持当前投入节奏，定期复盘收益率假设。")
elif result.months_needed <= 120:
    st.info("结论：目标可达成，但时间中等。")
    st.caption(f"原因：按当前参数预计 {time_str} 达成。")
    st.caption("下一步：若希望提前达成，可提高每月投入或下调目标金额。")
else:
    st.warning("结论：目标可达成但周期较长。")
    st.caption(f"原因：按当前参数预计需要 {time_str}。")
    st.caption("下一步：建议优先提高月投入，其次再考虑调整收益率假设。")

# ── Plotly 资产成长曲线 ───────────────────────────────────
st.subheader("📈 资产成长曲线")

sched = result.schedule

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=sched["月数"], y=sched["余额"],
    mode="lines", name="复利成长",
    line=dict(width=2.5, color="#00CC96"),
    hovertemplate=f"第 %{{x}} 月<br>余额: {sym}%{{y:,.0f}}<extra></extra>",
))

fig.add_trace(go.Scatter(
    x=sched["月数"], y=sched["纯储蓄余额"],
    mode="lines", name="纯储蓄（无报酬）",
    line=dict(width=2, dash="dash", color="#636EFA"),
    hovertemplate=f"第 %{{x}} 月<br>纯储蓄: {sym}%{{y:,.0f}}<extra></extra>",
))

fig.add_hline(
    y=goal_amount, line_dash="dot", line_color="#EF553B", line_width=1.5,
    annotation_text=f"目标 {fmt(goal_amount, decimals=0)}",
    annotation_position="top left",
    annotation_font_color="#EF553B",
)

goal_row = sched[sched["月数"] == result.months_needed].iloc[0]
fig.add_trace(go.Scatter(
    x=[result.months_needed], y=[goal_row["余额"]],
    mode="markers", name="达成点",
    marker=dict(size=14, color="#FFD600", symbol="star", line=dict(width=1.5, color="#fff")),
    hovertemplate=f"第 {result.months_needed} 月达成<br>余额: {fmt(goal_row['余额'], decimals=0)}<extra></extra>",
))

# 复利贡献填充区域
fig.add_trace(go.Scatter(
    x=sched["月数"], y=sched["纯储蓄余额"],
    mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
))
fig.add_trace(go.Scatter(
    x=sched["月数"], y=sched["余额"],
    mode="lines", name="复利贡献区间",
    line=dict(width=0),
    fill="tonexty", fillcolor="rgba(0,204,150,0.12)",
    hoverinfo="skip",
))

fig.update_layout(
    **build_layout(xaxis_title="月数", yaxis_title="金额（元）", yaxis_tickformat=","),
)
st.plotly_chart(fig, use_container_width=True)

# ── 逐年明细表格 ──────────────────────────────────────────
st.subheader("📋 逐年明细")

display_yr = result.yearly.copy()
money_cols = ["年初余额", "当年利息", "当年投入", "年末余额"]
for col in money_cols:
    display_yr[col] = display_yr[col].apply(lambda v: fmt(v))
display_yr["年份"] = display_yr["年份"].apply(lambda v: f"第 {v} 年")

st.dataframe(display_yr, use_container_width=True, hide_index=True)

# ── 快速调整对比 ──────────────────────────────────────────
st.subheader("⚡ 不同月投入达成时间对比")

comparison_deposits = [
    effective_deposit * 0.5,
    effective_deposit * 0.75,
    effective_deposit,
    effective_deposit * 1.5,
    effective_deposit * 2.0,
]
comparison_deposits = sorted(set(d for d in comparison_deposits if d > 0))

comp_rows: list[dict] = []
for dep in comparison_deposits:
    r = calculate_savings_goal(current_savings, goal_amount, annual_rate, dep)
    if r.reached:
        y = r.months_needed // 12
        m = r.months_needed % 12
        comp_rows.append({
            "每月投入": fmt(dep, decimals=0),
            "达成时间": f"{y}年{m}个月",
            "总月数": r.months_needed,
            "总投入本金": fmt(r.total_deposited, decimals=0),
            "复利贡献": fmt(r.total_interest, decimals=0),
        })
    else:
        comp_rows.append({
            "每月投入": fmt(dep, decimals=0),
            "达成时间": "无法达成",
            "总月数": "—",
            "总投入本金": "—",
            "复利贡献": "—",
        })

comp_df = pd.DataFrame(comp_rows)
st.dataframe(comp_df, use_container_width=True, hide_index=True)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("🎯 储蓄目标达成计算器 | 运行命令：`streamlit run app.py`")
