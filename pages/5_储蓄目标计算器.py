"""储蓄目标达成计算器

计算在给定报酬率与每月投入下，何时能达成储蓄目标。
逐月复利模拟 + Plotly 可视化。

v1.4: 核心计算已下沉到 core/savings.py；图表货币符号动态引用。
"""

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import currency_selector, fmt, fmt_delta, get_symbol
from core.export import dataframes_to_excel
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
pass

current_savings = st.sidebar.number_input(
    "目前储蓄金额（元）",
    min_value=0.0,
    max_value=CFG.savings.current_max,
    value=CFG.savings.current_default,
    step=CFG.savings.current_step,
    format="%.0f",
)
goal_amount = st.sidebar.number_input(
    "目标金额（元）",
    min_value=CFG.savings.goal_min,
    max_value=CFG.savings.goal_max,
    value=CFG.savings.goal_default,
    step=CFG.savings.goal_step,
    format="%.0f",
)
annual_rate = st.sidebar.number_input(
    "预期年化报酬率（%）",
    min_value=0.0,
    max_value=CFG.savings.annual_rate_max,
    value=CFG.savings.annual_rate_default,
    step=CFG.savings.annual_rate_step,
    format="%.1f",
)
monthly_deposit = st.sidebar.number_input(
    "每月固定投入（元）",
    min_value=0.0,
    max_value=CFG.savings.monthly_deposit_max,
    value=CFG.savings.monthly_deposit_default,
    step=CFG.savings.monthly_deposit_step,
    format="%.0f",
)
inflation_rate = st.sidebar.number_input(
    "年通谀率（%）",
    min_value=0.0,
    max_value=CFG.savings.inflation_rate_max,
    value=CFG.savings.inflation_rate_default,
    step=CFG.savings.inflation_rate_step,
    format="%.1f",
    help=MSG.savings_inflation_help,
)
start_date = st.sidebar.date_input("计算起始日期", value=date.today())

st.sidebar.divider()

# 即时调整滑杆
st.sidebar.subheader("⚡ 快速调整每月投入")
monthly_deposit_slider = st.sidebar.slider(
    "每月投入（滑杆）",
    min_value=0, max_value=int(CFG.savings.monthly_deposit_max), value=int(monthly_deposit), step=int(CFG.savings.monthly_deposit_step),
    format=f"{get_symbol()}%d",
)
effective_deposit = float(monthly_deposit_slider)
st.sidebar.caption(f"当前生效：每月 {fmt(effective_deposit, decimals=0)}")

scheme_manager_ui("savings", {
    "current_savings": current_savings,
    "goal_amount": goal_amount,
    "annual_rate": annual_rate,
    "monthly_deposit": monthly_deposit,
    "inflation_rate": inflation_rate,
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
    st.success(MSG.savings_already_reached.format(
        current=fmt(current_savings, decimals=0), goal=fmt(goal_amount, decimals=0)
    ))
    st.stop()

if not result.reached:
    st.error(MSG.savings_never)
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

progress_pct = min(1.0, current_savings / goal_amount)
st.progress(progress_pct, text=f"📊 当前进度：{progress_pct*100:.1f}%（{fmt(current_savings, decimals=0)} / {fmt(goal_amount, decimals=0)}）")

st.subheader("🧭 一页结论")
if result.months_needed <= CFG.savings.goal_short_threshold:
    st.success(MSG.savings_short_conclusion)
    st.caption(f"原因：按当前参数预计 {time_str} 达成，复利贡献约 {fmt(result.total_interest, decimals=0)}。")
    st.caption(MSG.savings_short_next)
elif result.months_needed <= CFG.savings.goal_long_threshold:
    st.info(MSG.savings_medium_conclusion)
    st.caption(f"原因：按当前参数预计 {time_str} 达成。")
    st.caption(MSG.savings_medium_next)
else:
    st.warning(MSG.savings_long_conclusion)
    st.caption(f"原因：按当前参数预计需要 {time_str}。")
    st.caption(MSG.savings_long_next)

if inflation_rate > 0 and result.months_needed > 0:
    years_to_goal = result.months_needed / 12
    real_goal = goal_amount * (1 + inflation_rate / 100) ** years_to_goal
    real_return = annual_rate - inflation_rate
    st.markdown("---")
    st.subheader("💹 通胀影响分析")
    ic1, ic2, ic3 = st.columns(3)
    ic1.metric("📌 名义目标", fmt(goal_amount, decimals=0))
    ic2.metric("📈 通胀调整后目标", fmt(real_goal, decimals=0), delta=fmt_delta(real_goal - goal_amount, decimals=0), delta_color="inverse")
    ic3.metric("📉 实际报酬率", f"{real_return:.1f}%", delta=f"名义 {annual_rate:.1f}% − 通胀 {inflation_rate:.1f}%", delta_color="off")
    if real_goal > goal_amount * 1.3:
        st.warning(MSG.savings_inflation_warning.format(
            rate=inflation_rate, years=years_to_goal,
            real_goal=fmt(real_goal, decimals=0), goal=fmt(goal_amount, decimals=0),
        ))
    else:
        st.info(MSG.savings_inflation_info.format(
            rate=inflation_rate, years=years_to_goal, real_goal=fmt(real_goal, decimals=0),
        ))

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

# ── 导出报告 ──────────────────────────────────────────────
st.subheader("📤 导出报告")
def _build_sav_report() -> str:
    s = get_symbol()
    yr = "".join(f"<tr><td>第{int(r['年份'])}年</td><td>{s}{r['年初余额']:,.0f}</td><td>{s}{r['当年利息']:,.0f}</td><td>{s}{r['当年投入']:,.0f}</td><td>{s}{r['年末余额']:,.0f}</td></tr>" for _, r in result.yearly.iterrows())
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#222}}h1{{color:#333}}table{{border-collapse:collapse;width:100%;margin-top:12px}}th,td{{border:1px solid #ccc;padding:6px 10px;text-align:right;font-size:13px}}th{{background:#f5f5f5}}</style></head><body><h1>🎯 储蓄目标报告</h1><p>目标：{s}{goal_amount:,.0f} | 现有：{s}{current_savings:,.0f} | 月投入：{s}{effective_deposit:,.0f} | 报酬率：{annual_rate:.1f}%</p><table><tr><th>年份</th><th>年初</th><th>利息</th><th>投入</th><th>年末</th></tr>{yr}</table></body></html>"""
_sav_dl_col1, _sav_dl_col2 = st.columns(2)
_sav_dl_col1.download_button("📥 下载报告 (HTML)", data=_build_sav_report(), file_name="储蓄目标报告.html", mime="text/html")

_sav_xlsx_bytes = dataframes_to_excel(
    sheets=[("逐年明细", result.yearly), ("投入对比", comp_df)],
    title="储蓄目标达成报告",
)
_sav_dl_col2.download_button(
    "📊 下载数据 (Excel)",
    data=_sav_xlsx_bytes,
    file_name="储蓄目标报告.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
st.caption(MSG.print_hint)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption(MSG.savings_footer)
