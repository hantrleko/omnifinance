"""保险产品测算器：保护型与储蓄型保险的量化评估。

v1.4:
- 新增一页结论文字分析
- 新增 CSV 导出功能
- 图表美化（使用 build_layout，货币符号动态引用）
- 新增替代投资 vs 累计保费差距对比指标
"""

from __future__ import annotations

import io

import plotly.graph_objects as go
import streamlit as st

from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import currency_selector, fmt, get_symbol
from core.insurance import analyze_insurance_plan
from core.storage import scheme_manager_ui

st.set_page_config(page_title="保险产品测算器", page_icon="🛡️", layout="wide")
st.title("🛡️ 保险产品测算器")
st.caption("用于评估保费效率、通胀后的保障力度，以及储蓄型保险 IRR。")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 参数设置")
currency_selector()

annual_premium = st.sidebar.number_input("年保费", min_value=0.0, value=CFG.insurance.annual_premium_default, step=CFG.insurance.annual_premium_step)
pay_years = st.sidebar.number_input("缴费年限", min_value=1, max_value=CFG.insurance.pay_years_max, value=CFG.insurance.pay_years_default, step=1)
coverage_years = st.sidebar.number_input("保障期限（年）", min_value=1, max_value=CFG.insurance.coverage_years_max, value=CFG.insurance.coverage_years_default, step=1)
sum_assured = st.sidebar.number_input("名义保额", min_value=0.0, value=CFG.insurance.sum_assured_default, step=CFG.insurance.sum_assured_step)
inflation_pct = st.sidebar.number_input("长期通胀假设（%）", min_value=0.0, max_value=CFG.insurance.inflation_max, value=CFG.insurance.inflation_default, step=CFG.insurance.inflation_step)
alt_return_pct = st.sidebar.number_input("替代投资年化收益（%）", min_value=0.0, max_value=CFG.insurance.alt_return_max, value=CFG.insurance.alt_return_default, step=CFG.insurance.alt_return_step)
maturity_benefit = st.sidebar.number_input("满期/退保可得金额", min_value=0.0, value=CFG.insurance.maturity_benefit_default, step=CFG.insurance.maturity_benefit_step)

scheme_manager_ui(
    "insurance",
    {
        "annual_premium": annual_premium,
        "pay_years": int(pay_years),
        "coverage_years": int(coverage_years),
        "sum_assured": sum_assured,
        "inflation_pct": inflation_pct,
        "alt_return_pct": alt_return_pct,
        "maturity_benefit": maturity_benefit,
    },
)

# ══════════════════════════════════════════════════════════
#  执行计算
# ══════════════════════════════════════════════════════════

result = analyze_insurance_plan(
    annual_premium=annual_premium,
    pay_years=int(pay_years),
    coverage_years=int(coverage_years),
    sum_assured=sum_assured,
    inflation_pct=inflation_pct,
    alt_return_pct=alt_return_pct,
    maturity_benefit=maturity_benefit,
)

sym = get_symbol()
st.session_state["dashboard_insurance"] = {
    "total_premium": result.protection.total_premium,
    "irr_pct": result.savings.irr_pct,
}

# ── 保障维度 ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📌 保障维度")
c1, c2, c3, c4 = st.columns(4)
c1.metric("累计总保费", fmt(result.protection.total_premium, decimals=0))
c2.metric("每万元保额成本", fmt(result.protection.coverage_cost_per_10k, decimals=2))
c3.metric("保费回本理赔率", f"{result.protection.break_even_claim_prob * 100:.2f}%",
          help=MSG.insurance_breakeven_help)
c4.metric("期末实际保额（折现）", fmt(result.protection.inflation_adjusted_coverage, decimals=0),
          delta=f"通胀侵蚀 {fmt(sum_assured - result.protection.inflation_adjusted_coverage, decimals=0)}",
          delta_color="inverse")

# ── 储蓄维度 ──────────────────────────────────────────────
st.subheader("💼 储蓄维度")
alt_gap = result.protection.alt_investment_value - maturity_benefit
s1, s2, s3, s4 = st.columns(4)
s1.metric("满期净收益", fmt(result.savings.net_gain, decimals=0),
          delta_color="normal" if result.savings.net_gain >= 0 else "inverse",
          delta=f"{'盈利' if result.savings.net_gain >= 0 else '亏损'}")
s2.metric("保单 IRR", f"{result.savings.irr_pct:.2f}%")
s3.metric("替代投资期末值", fmt(result.protection.alt_investment_value, decimals=0))
s4.metric("vs 替代投资差距", fmt(abs(alt_gap), decimals=0),
          delta=f"{'落后' if alt_gap > 0 else '领先'} {fmt(abs(alt_gap), decimals=0)}",
          delta_color="inverse" if alt_gap > 0 else "normal")

# ── 一页结论 ──────────────────────────────────────────────
st.subheader("🧭 一页结论")

irr = result.savings.irr_pct
if irr >= alt_return_pct:
    st.success(MSG.insurance_irr_competitive.format(irr=irr, alt=alt_return_pct))
    st.caption(MSG.insurance_irr_competitive_next)
elif irr >= 2.0:
    st.info(MSG.insurance_irr_low.format(irr=irr, alt=alt_return_pct))
    st.caption(MSG.insurance_irr_low_note.format(gap=fmt(alt_gap, decimals=0)))
    st.caption(MSG.insurance_irr_low_next)
else:
    st.warning(MSG.insurance_irr_weak.format(irr=irr, alt=alt_return_pct))
    st.caption(MSG.insurance_irr_weak_note.format(gap=fmt(alt_gap, decimals=0)))
    st.caption(MSG.insurance_irr_weak_next)

# ── 通胀侵蚀警示 ──────────────────────────────────────────
erosion_pct = (1 - result.protection.inflation_adjusted_coverage / sum_assured) * 100
if erosion_pct > 40:
    st.error(f"⚠️ 通胀警示：{coverage_years} 年后实际保额仅剩名义保额的 {100 - erosion_pct:.0f}%，"
             f"实际购买力缩水 {erosion_pct:.0f}%。建议考虑附加保额递增条款。")
elif erosion_pct > 20:
    st.warning(f"📉 通胀提示：{coverage_years} 年后实际保额约缩水 {erosion_pct:.0f}%，"
               f"剩余实际价值 {fmt(result.protection.inflation_adjusted_coverage, decimals=0)}。")

# ── 走势对比图 ────────────────────────────────────────────
st.subheader("📈 走势对比")

sched = result.yearly_schedule

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=sched["保单年度"], y=sched["累计保费"],
    mode="lines", name="累计保费",
    line=dict(width=2, color="#EF553B"),
    hovertemplate=f"第 %{{x}} 年<br>累计保费: {sym}%{{y:,.0f}}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=sched["保单年度"], y=sched["替代投资账户"],
    mode="lines", name="替代投资账户",
    line=dict(width=2, color="#00CC96"),
    hovertemplate=f"第 %{{x}} 年<br>替代投资: {sym}%{{y:,.0f}}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=sched["保单年度"], y=sched["实际保额(折现后)"],
    mode="lines", name="实际保额（折现）",
    line=dict(width=2, dash="dash", color="#636EFA"),
    hovertemplate=f"第 %{{x}} 年<br>折现保额: {sym}%{{y:,.0f}}<extra></extra>",
))

# 满期金水平线
if maturity_benefit > 0:
    fig.add_hline(
        y=maturity_benefit, line_dash="dot", line_color="#FFD600",
        annotation_text=f"满期金 {fmt(maturity_benefit, decimals=0)}",
        annotation_position="top left", annotation_font_color="#FFD600",
    )

fig.update_layout(
    **build_layout(xaxis_title="保单年度", yaxis_title="金额（元）", yaxis_tickformat=","),
    height=420,
)
st.plotly_chart(fig, use_container_width=True)

# ── 年度明细 ──────────────────────────────────────────────
st.subheader("🧾 年度明细")
st.dataframe(result.yearly_schedule, use_container_width=True, hide_index=True)

# ── 导出 CSV ──────────────────────────────────────────────
csv_buf = io.StringIO()
result.yearly_schedule.to_csv(csv_buf, index=False, encoding="utf-8-sig")
st.download_button(
    "📥 导出年度明细 CSV",
    data=csv_buf.getvalue(),
    file_name="保险产品分析.csv",
    mime="text/csv",
)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption(MSG.insurance_footer)
