"""税务优化提款策略 — 退休账户提款顺序优化

根据不同账户类型的税率差异，优化退休阶段的提款顺序以最小化总税负。
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

st.set_page_config(page_title="税务优化提款策略", page_icon="🏦", layout="wide")
st.title("🏦 税务优化提款策略")
st.caption("优化退休阶段从不同类型账户（应税/延税/免税）的提款顺序，最小化终身税负")

sym = get_symbol()

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.header("📋 账户参数")
taxable_balance = st.sidebar.number_input("应税账户余额（如股票）", min_value=0.0, value=500000.0, step=50000.0, format="%.0f", help="已缴税的投资账户，提取时仅缴资本利得税")
tax_deferred_balance = st.sidebar.number_input("延税账户余额（如养老金）", min_value=0.0, value=1000000.0, step=100000.0, format="%.0f", help="提取时按所得税率缴税")
tax_free_balance = st.sidebar.number_input("免税账户余额（如国债）", min_value=0.0, value=300000.0, step=50000.0, format="%.0f", help="提取时无需缴税")

st.sidebar.subheader("提款参数")
annual_expense = st.sidebar.number_input("年度生活支出", min_value=50000.0, value=360000.0, step=30000.0, format="%.0f")
years_in_retirement = st.sidebar.slider("退休年数", min_value=5, max_value=40, value=25)
investment_return = st.sidebar.slider("投资年化收益(%)", min_value=0.0, max_value=10.0, value=4.0, step=0.5)

st.sidebar.subheader("税率参数")
income_tax_rate = st.sidebar.slider("延税账户提款税率(%)", min_value=0.0, max_value=45.0, value=20.0, step=1.0)
capital_gains_rate = st.sidebar.slider("资本利得税率(%)", min_value=0.0, max_value=30.0, value=10.0, step=1.0)

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

# ── Simulation ────────────────────────────────────────────
def simulate_withdrawal(order: list[str], label: str) -> dict[str, Any]:
    """Simulate withdrawal from accounts in given order."""
    balances = {
        "应税": taxable_balance,
        "延税": tax_deferred_balance,
        "免税": tax_free_balance,
    }
    tax_rates = {
        "应税": capital_gains_rate / 100,
        "延税": income_tax_rate / 100,
        "免税": 0.0,
    }
    r = investment_return / 100
    total_tax = 0.0
    total_withdrawn = 0.0
    rows: list[dict[str, Any]] = []

    for yr in range(1, years_in_retirement + 1):
        # Grow all accounts
        for acct in balances:
            balances[acct] *= (1 + r)

        remaining_need = annual_expense
        yr_tax = 0.0
        yr_withdrawals = {acct: 0.0 for acct in balances}

        for acct in order:
            if remaining_need <= 0:
                break
            if balances[acct] <= 0:
                continue

            # Need to withdraw enough pre-tax to cover remaining_need after tax
            tax_rate = tax_rates[acct]
            # amount * (1 - tax_rate) = remaining_need => amount = remaining_need / (1 - tax_rate)
            if tax_rate < 1.0:
                gross_needed = remaining_need / (1 - tax_rate)
            else:
                gross_needed = remaining_need

            actual_withdraw = min(gross_needed, balances[acct])
            tax = actual_withdraw * tax_rate
            net = actual_withdraw - tax

            balances[acct] -= actual_withdraw
            yr_withdrawals[acct] = actual_withdraw
            yr_tax += tax
            remaining_need -= net

        total_tax += yr_tax
        total_withdrawn += annual_expense

        rows.append({
            "年份": yr,
            "应税账户": balances["应税"],
            "延税账户": balances["延税"],
            "免税账户": balances["免税"],
            "总余额": sum(balances.values()),
            "当年税负": yr_tax,
            "累计税负": total_tax,
        })

    return {
        "label": label,
        "total_tax": total_tax,
        "final_balance": sum(balances.values()),
        "schedule": pd.DataFrame(rows),
    }

# Three strategies
strategies = [
    (["应税", "延税", "免税"], "传统顺序（应税→延税→免税）"),
    (["免税", "延税", "应税"], "逆序（免税→延税→应税）"),
    (["应税", "免税", "延税"], "税务优化（应税→免税→延税）"),
]

results = []
for order, label in strategies:
    results.append(simulate_withdrawal(order, label))

# ── Metrics ───────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 策略对比")

best = min(results, key=lambda r: r["total_tax"])
cols = st.columns(3)
for idx, r in enumerate(results):
    with cols[idx]:
        badge = " 🏆" if r["total_tax"] == best["total_tax"] else ""
        st.metric(f"{r['label']}{badge}", "")
        st.metric("累计税负", fmt(r["total_tax"], decimals=0))
        st.metric("最终余额", fmt(r["final_balance"], decimals=0))

tax_savings = max(r["total_tax"] for r in results) - best["total_tax"]
if tax_savings > 0:
    st.success(f"✅ 最优策略可节省税负 **{fmt(tax_savings, decimals=0)}**！")

# ── Charts ────────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 各策略余额走势")

fig = go.Figure()
colors = ["#2563eb", "#ef4444", "#10b981"]
for idx, r in enumerate(results):
    fig.add_trace(go.Scatter(
        x=r["schedule"]["年份"], y=r["schedule"]["总余额"],
        mode="lines", name=r["label"],
        line=dict(width=2.5, color=colors[idx]),
    ))
fig.update_layout(**build_layout(title="不同提款顺序的资产余额", xaxis_title="退休年份", yaxis_title=f"总余额 ({sym})", yaxis_tickformat=",.0f"))
st.plotly_chart(fig, use_container_width=True)

# Tax comparison
st.subheader("📊 累计税负对比")
fig2 = go.Figure()
for idx, r in enumerate(results):
    fig2.add_trace(go.Scatter(
        x=r["schedule"]["年份"], y=r["schedule"]["累计税负"],
        mode="lines", name=r["label"],
        line=dict(width=2.5, color=colors[idx]),
    ))
fig2.update_layout(**build_layout(title="累计税负对比", xaxis_title="退休年份", yaxis_title=f"累计税负 ({sym})", yaxis_tickformat=",.0f"))
st.plotly_chart(fig2, use_container_width=True)

# Detail
st.markdown("---")
with st.expander("📋 最优策略逐年详情"):
    disp = best["schedule"].copy()
    for c in ["应税账户", "延税账户", "免税账户", "总余额", "当年税负", "累计税负"]:
        disp[c] = disp[c].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("🏦 税务优化提款策略 | 仅供参考 | 运行命令：`streamlit run app.py`")
