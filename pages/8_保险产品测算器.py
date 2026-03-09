"""保险产品测算器：保护型与储蓄型保险的量化评估。"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from core.currency import currency_selector, fmt
from core.insurance import analyze_insurance_plan
from core.storage import scheme_manager_ui

st.set_page_config(page_title="保险产品测算器", page_icon="🛡️", layout="wide")
st.title("🛡️ 保险产品测算器")
st.caption("用于评估保费效率、通胀后的保障力度，以及储蓄型保险 IRR。")

st.sidebar.header("📋 参数设置")
currency_selector()

annual_premium = st.sidebar.number_input("年保费", min_value=0.0, value=12_000.0, step=500.0)
pay_years = st.sidebar.number_input("缴费年限", min_value=1, max_value=50, value=20, step=1)
coverage_years = st.sidebar.number_input("保障期限（年）", min_value=1, max_value=80, value=30, step=1)
sum_assured = st.sidebar.number_input("名义保额", min_value=0.0, value=1_000_000.0, step=50_000.0)
inflation_pct = st.sidebar.number_input("长期通胀假设（%）", min_value=0.0, max_value=10.0, value=2.5, step=0.1)
alt_return_pct = st.sidebar.number_input("替代投资年化收益（%）", min_value=0.0, max_value=20.0, value=4.0, step=0.1)
maturity_benefit = st.sidebar.number_input("满期/退保可得金额", min_value=0.0, value=350_000.0, step=10_000.0)

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

result = analyze_insurance_plan(
    annual_premium=annual_premium,
    pay_years=int(pay_years),
    coverage_years=int(coverage_years),
    sum_assured=sum_assured,
    inflation_pct=inflation_pct,
    alt_return_pct=alt_return_pct,
    maturity_benefit=maturity_benefit,
)

st.markdown("---")
st.subheader("📌 保障维度")
c1, c2, c3, c4 = st.columns(4)
c1.metric("累计总保费", fmt(result.protection.total_premium, decimals=0))
c2.metric("每万元保额成本", fmt(result.protection.coverage_cost_per_10k, decimals=2))
c3.metric("保费回本理赔率", f"{result.protection.break_even_claim_prob * 100:.2f}%")
c4.metric("期末实际保额（折现）", fmt(result.protection.inflation_adjusted_coverage, decimals=0))

st.subheader("💼 储蓄维度")
s1, s2, s3 = st.columns(3)
s1.metric("满期净收益", fmt(result.savings.net_gain, decimals=0))
s2.metric("保单 IRR", f"{result.savings.irr_pct:.2f}%")
s3.metric("替代投资期末值", fmt(result.protection.alt_investment_value, decimals=0))

st.subheader("📈 走势对比")
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=result.yearly_schedule["保单年度"],
        y=result.yearly_schedule["累计保费"],
        mode="lines",
        name="累计保费",
    )
)
fig.add_trace(
    go.Scatter(
        x=result.yearly_schedule["保单年度"],
        y=result.yearly_schedule["替代投资账户"],
        mode="lines",
        name="替代投资账户",
    )
)
fig.add_trace(
    go.Scatter(
        x=result.yearly_schedule["保单年度"],
        y=result.yearly_schedule["实际保额(折现后)"],
        mode="lines",
        name="实际保额(折现后)",
    )
)
fig.update_layout(height=420, margin=dict(t=20, b=20), hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("🧾 年度明细")
st.dataframe(result.yearly_schedule, use_container_width=True)

st.session_state["dashboard_insurance"] = {
    "total_premium": result.protection.total_premium,
    "irr_pct": result.savings.irr_pct,
}
