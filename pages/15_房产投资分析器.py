"""房产投资分析器 — 买房 vs 租房、租金回报率、贷款+增值 ROI

综合评估房产购买决策的财务合理性。
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import fmt, get_symbol

st.set_page_config(page_title="房产投资分析器", page_icon="🏘️", layout="wide")
st.title("🏘️ 房产投资分析器")
st.caption("买房 vs 租房对比、租金回报率分析、房产投资 ROI 综合评估")

sym = get_symbol()

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.header("🏠 房产参数")
property_price = st.sidebar.number_input("房产总价", min_value=100000.0, value=3000000.0, step=100000.0, format="%.0f")
down_payment_pct = st.sidebar.slider("首付比例(%)", min_value=10, max_value=100, value=30, step=5)
mortgage_rate = st.sidebar.slider("房贷年利率(%)", min_value=0.1, max_value=10.0, value=3.5, step=0.1)
mortgage_years = st.sidebar.slider("贷款年限", min_value=1, max_value=30, value=30)
appreciation_pct = st.sidebar.slider("年房价涨幅(%)", min_value=-5.0, max_value=15.0, value=3.0, step=0.5)
property_tax_pct = st.sidebar.slider("年房产税率(%)", min_value=0.0, max_value=3.0, value=0.5, step=0.1)
maintenance_pct = st.sidebar.slider("年维护费率(%)", min_value=0.0, max_value=3.0, value=1.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.header("🏢 租房参数")
monthly_rent = st.sidebar.number_input("月租金（替代方案）", min_value=0.0, value=8000.0, step=500.0, format="%.0f")
rent_increase_pct = st.sidebar.slider("年租金涨幅(%)", min_value=0.0, max_value=10.0, value=3.0, step=0.5)
invest_return_pct = st.sidebar.slider("首付投资年化收益(%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5, help="如不买房，首付款可获得的投资收益")

analysis_years = st.sidebar.slider("分析年限", min_value=5, max_value=40, value=20, step=1)

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

# ── Calculations ──────────────────────────────────────────
down_payment = property_price * down_payment_pct / 100
loan_amount = property_price - down_payment
r_m = mortgage_rate / 100 / 12
n_payments = mortgage_years * 12

if r_m > 0 and n_payments > 0:
    monthly_mortgage = loan_amount * r_m * (1 + r_m) ** n_payments / ((1 + r_m) ** n_payments - 1)
else:
    monthly_mortgage = loan_amount / max(n_payments, 1)

# Year-by-year simulation
buy_rows: list[dict[str, Any]] = []
rent_rows: list[dict[str, Any]] = []
buy_total_cost = down_payment
rent_total_cost = 0.0
property_value = property_price
rent_current = monthly_rent
loan_balance = loan_amount
invest_balance = down_payment  # If renting, invest the down payment

for yr in range(1, analysis_years + 1):
    # Buy scenario
    yr_mortgage = 0.0
    for _ in range(12):
        if loan_balance > 0:
            interest = loan_balance * r_m
            principal_part = monthly_mortgage - interest
            if principal_part > loan_balance:
                principal_part = loan_balance
            loan_balance -= principal_part
            yr_mortgage += monthly_mortgage
        if loan_balance < 0:
            loan_balance = 0

    yr_tax = property_value * property_tax_pct / 100
    yr_maintenance = property_value * maintenance_pct / 100
    property_value *= (1 + appreciation_pct / 100)
    buy_yr_cost = yr_mortgage + yr_tax + yr_maintenance
    buy_total_cost += buy_yr_cost

    equity = property_value - max(loan_balance, 0)
    buy_net_worth = equity - buy_total_cost + property_value  # Simplified: equity is the gain

    buy_rows.append({
        "年份": yr, "房产市值": property_value, "贷款余额": max(loan_balance, 0),
        "权益": equity, "当年总支出": buy_yr_cost, "累计总支出": buy_total_cost,
    })

    # Rent scenario
    yr_rent = rent_current * 12
    rent_total_cost += yr_rent
    invest_balance = invest_balance * (1 + invest_return_pct / 100)
    # Also invest the monthly difference if buying costs more
    diff_monthly = monthly_mortgage + (yr_tax + yr_maintenance) / 12 - rent_current
    if diff_monthly > 0:
        for _ in range(12):
            invest_balance += diff_monthly
            invest_balance *= (1 + invest_return_pct / 100 / 12)

    rent_current *= (1 + rent_increase_pct / 100)

    rent_rows.append({
        "年份": yr, "当年租金": yr_rent, "累计租金": rent_total_cost,
        "投资组合价值": invest_balance,
    })

buy_df = pd.DataFrame(buy_rows)
rent_df = pd.DataFrame(rent_rows)

# ── Key metrics ───────────────────────────────────────────
st.markdown("---")
st.subheader("📊 核心指标")

final_equity = buy_df.iloc[-1]["权益"]
final_invest = rent_df.iloc[-1]["投资组合价值"]
buy_net = final_equity
rent_net = final_invest - rent_total_cost

c1, c2, c3, c4 = st.columns(4)
c1.metric("🏠 房产终值", fmt(property_value, decimals=0))
c2.metric("📊 买房净权益", fmt(final_equity, decimals=0))
c3.metric("💰 租房净资产", fmt(rent_net, decimals=0), help="投资组合 - 累计租金")
c4.metric("🏆 更优选择", "买房" if buy_net > rent_net else "租房")

advantage = abs(buy_net - rent_net)
if buy_net > rent_net:
    st.success(f"✅ 在当前参数下，**买房**在 {analysis_years} 年后净资产多出 **{fmt(advantage, decimals=0)}**。")
else:
    st.info(f"💡 在当前参数下，**租房+投资**在 {analysis_years} 年后净资产多出 **{fmt(advantage, decimals=0)}**。")

# Rental yield
annual_rental_yield = monthly_rent * 12 / property_price * 100
st.metric("📈 当前租金回报率", f"{annual_rental_yield:.2f}%", help="年租金 / 房产总价")

# ── Charts ────────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 买房 vs 租房 净资产对比")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=buy_df["年份"], y=buy_df["权益"],
    mode="lines+markers", name="买房净权益",
    line=dict(width=3, color="#2563eb"),
))
fig.add_trace(go.Scatter(
    x=rent_df["年份"], y=rent_df["投资组合价值"] - rent_df["累计租金"],
    mode="lines+markers", name="租房净资产",
    line=dict(width=3, color="#ef4444"),
))
fig.update_layout(**build_layout(
    title="买房 vs 租房 净资产变化",
    xaxis_title="年份", yaxis_title=f"净资产 ({sym})", yaxis_tickformat=",.0f",
))
st.plotly_chart(fig, use_container_width=True)

# Property value and loan balance
st.subheader("🏠 房产价值与贷款余额")
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=buy_df["年份"], y=buy_df["房产市值"], mode="lines", name="房产市值", line=dict(width=2.5, color="#10b981")))
fig2.add_trace(go.Scatter(x=buy_df["年份"], y=buy_df["贷款余额"], mode="lines", name="贷款余额", line=dict(width=2.5, color="#ef4444")))
fig2.add_trace(go.Bar(x=buy_df["年份"], y=buy_df["权益"], name="净权益", marker_color="rgba(37,99,235,0.3)"))
fig2.update_layout(**build_layout(title="房产价值构成", xaxis_title="年份", yaxis_title=f"金额 ({sym})", yaxis_tickformat=",.0f"))
st.plotly_chart(fig2, use_container_width=True)

# ── Detail tables ─────────────────────────────────────────
st.markdown("---")
with st.expander("📋 买房逐年明细"):
    disp = buy_df.copy()
    for c in ["房产市值", "贷款余额", "权益", "当年总支出", "累计总支出"]:
        disp[c] = disp[c].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp, use_container_width=True, hide_index=True)

with st.expander("📋 租房逐年明细"):
    disp2 = rent_df.copy()
    for c in ["当年租金", "累计租金", "投资组合价值"]:
        disp2[c] = disp2[c].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp2, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("🏘️ 房产投资分析器 | 运行命令：`streamlit run app.py`")
