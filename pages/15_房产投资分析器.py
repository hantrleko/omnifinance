"""房产投资分析器 — 买房 vs 租房、租金回报率、贷款+增值 ROI

综合评估房产购买决策的财务合理性。
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.navigation import track_recent_page
track_recent_page(st.session_state, 'realestate')

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
st.sidebar.header("🏢 出租 / 租房参数")
monthly_rent_income = st.sidebar.number_input("月租金收入（出租该房产）", min_value=0.0, value=8000.0, step=500.0, format="%.0f", help="若自住则填0；用于计算Cap Rate、Cash-on-Cash等出租指标")
monthly_rent = st.sidebar.number_input("月租金（租房替代方案）", min_value=0.0, value=8000.0, step=500.0, format="%.0f", help="若选择租房而非买房，所需支付的月租金")
rent_increase_pct = st.sidebar.slider("年租金涨幅(%)", min_value=0.0, max_value=10.0, value=3.0, step=0.5)
invest_return_pct = st.sidebar.slider("首付投资年化收益(%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5, help="如不买房，首付款可获得的投资收益")

st.sidebar.markdown("---")
st.sidebar.header("🔧 运营成本（出租）")
hoa_monthly = st.sidebar.number_input("物业费/月（元）", min_value=0.0, value=500.0, step=100.0, format="%.0f")
vacancy_rate_pct = st.sidebar.slider("空置率(%)", min_value=0, max_value=30, value=5, step=1, help="全年空置月份占比，影响实际租金收入")
mgmt_fee_pct = st.sidebar.slider("委托管理费(%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5, help="若委托中介/管理公司，占租金收入的比例")

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

# ── 出租指标预计算 ─────────────────────────────────────────
# Effective gross income (vacancy adjusted)
egi_annual = monthly_rent_income * 12 * (1 - vacancy_rate_pct / 100)
# Operating expenses: tax + maintenance + HOA + mgmt fee
mgmt_fee_annual = egi_annual * mgmt_fee_pct / 100
hoa_annual = hoa_monthly * 12
op_expense_annual = (property_price * property_tax_pct / 100
                     + property_price * maintenance_pct / 100
                     + hoa_annual + mgmt_fee_annual)
# Net Operating Income
noi_annual = egi_annual - op_expense_annual
# Cap Rate = NOI / Property Price
cap_rate = noi_annual / property_price * 100 if property_price > 0 else 0.0
# Cash-on-Cash = (NOI - annual mortgage) / down_payment
annual_mortgage = monthly_mortgage * 12
annual_cash_flow = noi_annual - annual_mortgage
coc_return = annual_cash_flow / down_payment * 100 if down_payment > 0 else 0.0

# Year-by-year simulation
buy_rows: list[dict[str, Any]] = []
rent_rows: list[dict[str, Any]] = []
buy_total_cost = down_payment
rent_total_cost = 0.0
property_value = property_price
rent_current = monthly_rent
loan_balance = loan_amount
invest_balance = down_payment  # If renting, invest the down payment

# IRR cash flows: start with -down_payment at t=0
irr_cashflows: list[float] = [-down_payment]

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

    yr_prop_val_pre = property_value
    yr_tax = yr_prop_val_pre * property_tax_pct / 100
    yr_maintenance = yr_prop_val_pre * maintenance_pct / 100
    yr_hoa = hoa_monthly * 12
    property_value *= (1 + appreciation_pct / 100)

    # Rental income for this year (if renting out)
    yr_egi = monthly_rent_income * 12 * (1 - vacancy_rate_pct / 100)
    yr_mgmt = yr_egi * mgmt_fee_pct / 100
    yr_net_rental = yr_egi - yr_mgmt

    buy_yr_outflow = yr_mortgage + yr_tax + yr_maintenance + yr_hoa
    buy_yr_net_cost = buy_yr_outflow - yr_net_rental  # net after rental income
    buy_total_cost += buy_yr_outflow

    equity = property_value - max(loan_balance, 0)

    buy_rows.append({
        "年份": yr, "房产市值": property_value, "贷款余额": max(loan_balance, 0),
        "权益": equity, "当年净租金": yr_net_rental,
        "当年支出": buy_yr_outflow, "累计总支出": buy_total_cost,
        "年净现金流": yr_net_rental - buy_yr_outflow,
    })

    # IRR: annual cash flow = net rental income - mortgage - tax - maintenance - hoa
    # Final year: also add property sale proceeds (equity)
    if yr < analysis_years:
        irr_cashflows.append(yr_net_rental - buy_yr_outflow)
    else:
        irr_cashflows.append(yr_net_rental - buy_yr_outflow + equity)

    # Rent scenario
    yr_rent = rent_current * 12
    rent_total_cost += yr_rent
    invest_balance = invest_balance * (1 + invest_return_pct / 100)
    diff_monthly = monthly_mortgage + (yr_tax + yr_maintenance + yr_hoa) / 12 - rent_current
    if diff_monthly > 0:
        for _ in range(12):
            invest_balance += diff_monthly
            invest_balance *= (1 + invest_return_pct / 100 / 12)

    rent_current *= (1 + rent_increase_pct / 100)

    rent_rows.append({
        "年份": yr, "当年租金": yr_rent, "累计租金": rent_total_cost,
        "投资组合价值": invest_balance,
    })

# ── Property IRR (Newton-Raphson + brentq fallback) ───────
def _irr(cashflows: list[float]) -> float | None:
    import numpy as np
    from scipy.optimize import brentq
    cf = np.array(cashflows, dtype=float)
    def npv(r: float) -> float:
        t = np.arange(len(cf))
        return float(np.sum(cf / (1 + r) ** t))
    try:
        # Quick Newton-Raphson starting guess
        rate = 0.1
        for _ in range(100):
            f = npv(rate)
            t = np.arange(len(cf))
            df = float(np.sum(-t * cf / (1 + rate) ** (t + 1)))
            if abs(df) < 1e-12:
                break
            rate -= f / df
            if rate <= -1:
                rate = -0.999
        if -0.999 < rate < 10 and abs(npv(rate)) < 1:
            return rate
        return float(brentq(npv, -0.999, 10.0, maxiter=500))
    except Exception:
        return None

_irr_val = _irr(irr_cashflows)

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

# ── 出租投资指标 ──────────────────────────────────────────
if monthly_rent_income > 0:
    st.markdown("---")
    st.subheader("🏢 出租投资指标")
    st.caption("以下指标适用于出租该房产的投资场景")

    gross_yield = monthly_rent_income * 12 / property_price * 100
    net_yield = noi_annual / property_price * 100

    inv_c1, inv_c2, inv_c3, inv_c4, inv_c5 = st.columns(5)
    inv_c1.metric("毛租金回报率", f"{gross_yield:.2f}%", help="年租金总收入 / 房产总价")
    inv_c2.metric("净租金回报率", f"{net_yield:.2f}%", help="(年租金 - 空置损失) / 房产总价")
    inv_c3.metric(
        "Cap Rate（资本化率）",
        f"{cap_rate:.2f}%",
        help="NOI（净运营收入）/ 房产总价；衡量不含杠杆的回报率",
    )
    inv_c4.metric(
        "Cash-on-Cash（现金回报率）",
        f"{coc_return:.2f}%",
        help="年净现金流 / 首付；衡量杠杆后的现金回报",
        delta="正现金流" if annual_cash_flow >= 0 else "负现金流",
        delta_color="normal" if annual_cash_flow >= 0 else "inverse",
    )
    inv_c5.metric(
        "房产 IRR",
        f"{_irr_val*100:.2f}%" if _irr_val is not None else "N/A",
        help=f"含{analysis_years}年租金收入+期末出售的内部收益率",
    )

    # Operating cost breakdown
    with st.expander("💰 运营成本分解"):
        oc_col1, oc_col2 = st.columns(2)
        oc_rows = [
            ("房产税", property_price * property_tax_pct / 100),
            ("维护费", property_price * maintenance_pct / 100),
            ("物业费", hoa_annual),
            ("委托管理费", mgmt_fee_annual),
        ]
        oc_col1.markdown("**年度运营成本**")
        for name, val in oc_rows:
            oc_col1.metric(name, fmt(val, decimals=0))
        oc_col1.metric("合计", fmt(op_expense_annual, decimals=0))

        oc_col2.markdown("**年度收支**")
        oc_col2.metric("毛租金收入", fmt(monthly_rent_income * 12, decimals=0))
        oc_col2.metric("有效收入（扣空置）", fmt(egi_annual, decimals=0))
        oc_col2.metric("净运营收入 NOI", fmt(noi_annual, decimals=0))
        oc_col2.metric("年贷款还款", fmt(annual_mortgage, decimals=0))
        oc_col2.metric(
            "税前现金流",
            fmt(annual_cash_flow, decimals=0),
            delta_color="normal" if annual_cash_flow >= 0 else "inverse",
        )

    # Cap rate vs risk-free comparison
    risk_free_approx = 2.5
    if cap_rate < risk_free_approx:
        st.warning(f"⚠️ Cap Rate {cap_rate:.2f}% 低于无风险利率参考值 {risk_free_approx}%，出租回报偏低，需依赖房价增值补偿。")
    elif cap_rate < 4.0:
        st.info(f"📌 Cap Rate {cap_rate:.2f}% 属于一线城市常见水平（2–4%）。")
    else:
        st.success(f"✅ Cap Rate {cap_rate:.2f}% 较高，出租现金流表现良好。")
else:
    # Self-occupied: just show gross yield as reference
    annual_rental_yield = monthly_rent * 12 / property_price * 100
    st.metric("📈 参考租金回报率（按替代租金估算）", f"{annual_rental_yield:.2f}%", help="年租金 / 房产总价")

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

# ── Annual cash flow chart (if renting out) ───────────────
if monthly_rent_income > 0:
    st.markdown("---")
    st.subheader("📊 逐年现金流")
    _cf_colors = ["#00CC96" if v >= 0 else "#EF553B" for v in buy_df["年净现金流"]]
    fig_cf = go.Figure()
    fig_cf.add_trace(go.Bar(
        x=buy_df["年份"], y=buy_df["年净现金流"],
        marker_color=_cf_colors, name="年净现金流",
        text=[fmt(v, decimals=0) for v in buy_df["年净现金流"]],
        textposition="outside",
        hovertemplate="第%{x}年<br>净现金流: " + sym + "%{y:,.0f}<extra></extra>",
    ))
    fig_cf.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1)
    fig_cf.update_layout(**build_layout(
        xaxis_title="年份", yaxis_title=f"净现金流 ({sym})", yaxis_tickformat=",.0f", height=320,
    ))
    st.plotly_chart(fig_cf, use_container_width=True)

# ── Detail tables ─────────────────────────────────────────
st.markdown("---")
with st.expander("📋 买房逐年明细"):
    disp = buy_df.copy()
    _fmt_cols = [c for c in ["房产市值", "贷款余额", "权益", "当年净租金", "当年支出", "累计总支出", "年净现金流"] if c in disp.columns]
    for c in _fmt_cols:
        disp[c] = disp[c].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp, use_container_width=True, hide_index=True)

with st.expander("📋 租房逐年明细"):
    disp2 = rent_df.copy()
    for c in ["当年租金", "累计租金", "投资组合价值"]:
        disp2[c] = disp2[c].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp2, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("🏘️ 房产投资分析器 | 运行命令：`streamlit run app.py`")

