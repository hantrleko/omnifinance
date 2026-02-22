"""储蓄目标达成计算器

计算在给定报酬率与每月投入下，何时能达成储蓄目标。
逐月复利模拟 + Plotly 可视化。
"""

import math
from dataclasses import dataclass
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="储蓄目标计算器", page_icon="🎯", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .stMetric { background: #0E1117; border: 1px solid #262730; border-radius: 8px; padding: 14px; }
  .achieved { background: #1b5e20 !important; border-color: #4caf50 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 储蓄目标达成计算器")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 参数设置")

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
    format="¥%d",
)
# 以滑杆值为准（与 number_input 联动）
effective_deposit = float(monthly_deposit_slider)

st.sidebar.caption(f"当前生效：每月 ¥{effective_deposit:,.0f}")


# ══════════════════════════════════════════════════════════
#  核心计算
# ══════════════════════════════════════════════════════════

@dataclass
class SavingsResult:
    reached: bool           # 是否已达成
    months_needed: int      # 达成所需月数（0=已达成, -1=永远无法达成）
    schedule: pd.DataFrame  # 逐月明细
    yearly: pd.DataFrame    # 逐年汇总
    total_deposited: float  # 总投入本金（含初始）
    total_interest: float   # 复利贡献总额


def calculate_savings_goal(
    current: float,
    goal: float,
    annual_rate_pct: float,
    monthly_deposit: float,
    max_months: int = 1200,  # 最多模拟 100 年
) -> SavingsResult:
    """逐月复利模拟，返回完整结果。"""

    # 已达成
    if current >= goal:
        empty = pd.DataFrame()
        return SavingsResult(
            reached=True, months_needed=0,
            schedule=empty, yearly=empty,
            total_deposited=current, total_interest=0.0,
        )

    monthly_rate = (annual_rate_pct / 100.0) / 12
    balance = current
    total_deposited = current
    months_needed = -1

    rows: list[dict] = []

    for m in range(1, max_months + 1):
        interest = balance * monthly_rate
        balance += interest + monthly_deposit
        total_deposited += monthly_deposit

        # 无报酬的纯储蓄余额
        no_return_balance = current + monthly_deposit * m

        rows.append({
            "月数": m,
            "余额": balance,
            "当月利息": interest,
            "当月投入": monthly_deposit,
            "纯储蓄余额": no_return_balance,
        })

        if balance >= goal and months_needed == -1:
            months_needed = m

        # 达成后再多算 12 个月用于图表展示
        if months_needed != -1 and m >= months_needed + 12:
            break

    # 若永远无法达成（报酬率=0 且 月投入=0）
    if months_needed == -1 and monthly_deposit == 0 and annual_rate_pct == 0:
        pass  # months_needed 保持 -1

    schedule = pd.DataFrame(rows)

    # 逐年汇总
    yearly_rows: list[dict] = []
    yr_balance = current
    yr_interest_total = 0.0
    yr_deposit_total = 0.0

    for _, row in schedule.iterrows():
        yr_interest_total += row["当月利息"]
        yr_deposit_total += row["当月投入"]

        if row["月数"] % 12 == 0 or row["月数"] == len(schedule):
            year_num = math.ceil(row["月数"] / 12)
            yearly_rows.append({
                "年份": year_num,
                "年初余额": yr_balance,
                "当年利息": yr_interest_total,
                "当年投入": yr_deposit_total,
                "年末余额": row["余额"],
            })
            yr_balance = row["余额"]
            yr_interest_total = 0.0
            yr_deposit_total = 0.0

    yearly = pd.DataFrame(yearly_rows)

    total_interest = balance - total_deposited if months_needed != -1 else 0.0
    # 如果达成了，用达成时刻的数据
    if months_needed > 0:
        goal_row = schedule[schedule["月数"] == months_needed].iloc[0]
        deposited_at_goal = current + monthly_deposit * months_needed
        interest_at_goal = goal_row["余额"] - deposited_at_goal
        total_deposited = deposited_at_goal
        total_interest = interest_at_goal

    return SavingsResult(
        reached=(months_needed >= 0),
        months_needed=months_needed,
        schedule=schedule,
        yearly=yearly,
        total_deposited=total_deposited,
        total_interest=total_interest,
    )


# ══════════════════════════════════════════════════════════
#  执行计算
# ══════════════════════════════════════════════════════════

result = calculate_savings_goal(current_savings, goal_amount, annual_rate, effective_deposit)

# ── 已达成特殊情况 ────────────────────────────────────────
st.markdown("---")

if current_savings >= goal_amount:
    st.balloons()
    st.success(f"🎉 **已达成目标！** 目前储蓄 ¥{current_savings:,.0f} 已超过目标 ¥{goal_amount:,.0f}")
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

# 达成日期
target_month = start_date.month + result.months_needed
target_year = start_date.year + (target_month - 1) // 12
target_month = (target_month - 1) % 12 + 1
target_date_str = f"{target_year} 年 {target_month} 月"

c1, c2, c3, c4 = st.columns(4)
c1.metric("⏰ 预估达成时间", time_str, delta=target_date_str, delta_color="off")
c2.metric("💵 总需投入本金", f"¥{result.total_deposited:,.0f}")
c3.metric("📈 复利贡献金额", f"¥{result.total_interest:,.0f}")
c4.metric("🎯 复利贡献占比", f"{interest_ratio:.1f}%")

# ── Plotly 资产成长曲线 ───────────────────────────────────
st.subheader("📈 资产成长曲线")

LAYOUT_DARK = dict(
    template="plotly_dark",
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(color="#FAFAFA")),
    margin=dict(t=30, b=40),
    hovermode="x unified",
)

sched = result.schedule

fig = go.Figure()

# 资产成长（实线）
fig.add_trace(go.Scatter(
    x=sched["月数"], y=sched["余额"],
    mode="lines", name="复利成长",
    line=dict(width=2.5, color="#00CC96"),
    hovertemplate="第 %{x} 月<br>余额: ¥%{y:,.0f}<extra></extra>",
))

# 纯储蓄（虚线）
fig.add_trace(go.Scatter(
    x=sched["月数"], y=sched["纯储蓄余额"],
    mode="lines", name="纯储蓄（无报酬）",
    line=dict(width=2, dash="dash", color="#636EFA"),
    hovertemplate="第 %{x} 月<br>纯储蓄: ¥%{y:,.0f}<extra></extra>",
))

# 目标线
fig.add_hline(
    y=goal_amount, line_dash="dot", line_color="#EF553B", line_width=1.5,
    annotation_text=f"目标 ¥{goal_amount:,.0f}",
    annotation_position="top left",
    annotation_font_color="#EF553B",
)

# 达成点
goal_row = sched[sched["月数"] == result.months_needed].iloc[0]
fig.add_trace(go.Scatter(
    x=[result.months_needed], y=[goal_row["余额"]],
    mode="markers", name="达成点",
    marker=dict(size=14, color="#FFD600", symbol="star", line=dict(width=1.5, color="#fff")),
    hovertemplate=f"第 {result.months_needed} 月达成<br>余额: ¥{goal_row['余额']:,.0f}<extra></extra>",
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
    **LAYOUT_DARK,
    xaxis_title="月数",
    yaxis_title="金额（元）",
    yaxis_tickformat=",",
)
st.plotly_chart(fig, use_container_width=True)

# ── 逐年明细表格 ──────────────────────────────────────────
st.subheader("📋 逐年明细")

display_yr = result.yearly.copy()
money_cols = ["年初余额", "当年利息", "当年投入", "年末余额"]
for col in money_cols:
    display_yr[col] = display_yr[col].apply(lambda v: f"¥{v:,.2f}")
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
# 去重 + 去零 + 排序
comparison_deposits = sorted(set(d for d in comparison_deposits if d > 0))

comp_rows: list[dict] = []
for dep in comparison_deposits:
    r = calculate_savings_goal(current_savings, goal_amount, annual_rate, dep)
    if r.reached:
        y = r.months_needed // 12
        m = r.months_needed % 12
        comp_rows.append({
            "每月投入": f"¥{dep:,.0f}",
            "达成时间": f"{y}年{m}个月",
            "总月数": r.months_needed,
            "总投入本金": f"¥{r.total_deposited:,.0f}",
            "复利贡献": f"¥{r.total_interest:,.0f}",
        })
    else:
        comp_rows.append({
            "每月投入": f"¥{dep:,.0f}",
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
