"""场景对比分析器 — 跨工具全局敏感度分析

统一对比不同通胀率、收益率假设对复利、储蓄、退休的影响。
v1.9.8: 新增贷款利率敏感度、退休年龄敏感度两个分析维度。
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import MSG
from core.currency import fmt, get_symbol
from core.scenarios import run_inflation_scenarios, run_return_scenarios

st.set_page_config(page_title="场景对比分析器", page_icon="🔬", layout="wide")
st.markdown("""<style>.block-container{padding-top:1.2rem}.stMetric{background-color:var(--secondary-background-color);border:1px solid var(--secondary-background-color);border-radius:8px;padding:14px}</style>""", unsafe_allow_html=True)
st.title("🔬 场景对比分析器")
st.caption("跨工具 What-If 分析 — 同一参数变动在复利、储蓄、退休、贷款中的联动影响")

sym = get_symbol()

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.header("📋 基准参数")
tab_choice = st.sidebar.radio("分析维度", ["通胀率敏感度", "收益率敏感度", "贷款利率敏感度", "退休年龄敏感度"])

st.sidebar.subheader("复利参数")
c_principal = st.sidebar.number_input("本金", min_value=0.0, value=100000.0, step=10000.0, format="%.0f", key="sc_cp")
c_years = st.sidebar.slider("投资年限", min_value=5, max_value=50, value=20, key="sc_cy")

st.sidebar.subheader("储蓄参数")
s_current = st.sidebar.number_input("当前储蓄", min_value=0.0, value=50000.0, step=10000.0, format="%.0f", key="sc_sc")
s_goal = st.sidebar.number_input("目标金额", min_value=100000.0, value=1000000.0, step=100000.0, format="%.0f", key="sc_sg")
s_deposit = st.sidebar.number_input("月定投", min_value=0.0, value=10000.0, step=1000.0, format="%.0f", key="sc_sd")

st.sidebar.subheader("退休参数")
r_age = st.sidebar.number_input("当前年龄", min_value=20, max_value=60, value=35, key="sc_ra")
r_retire = st.sidebar.number_input("退休年龄", min_value=r_age+1, max_value=80, value=65, key="sc_rr")
r_expense = st.sidebar.number_input("月支出(今日)", min_value=5000.0, value=30000.0, step=5000.0, format="%.0f", key="sc_re")

if tab_choice in ("贷款利率敏感度",):
    st.sidebar.subheader("贷款参数")
    loan_amount = st.sidebar.number_input("贷款金额（元）", min_value=100000.0, value=1000000.0, step=50000.0, format="%.0f", key="sc_la")
    loan_years = st.sidebar.slider("贷款年限（年）", min_value=5, max_value=30, value=20, key="sc_ly")

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

# ── Run scenarios ─────────────────────────────────────────
st.markdown("---")

if tab_choice == "通胀率敏感度":
    st.subheader("📊 通胀率敏感度分析")
    inflation_values = [0.0, 1.0, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]

    result = run_inflation_scenarios(
        inflation_values=inflation_values,
        compound_principal=c_principal, compound_rate=6.0, compound_years=c_years,
        savings_current=s_current, savings_goal=s_goal, savings_rate=6.0, savings_deposit=s_deposit,
        current_age=r_age, retire_age=r_retire, life_expectancy=85,
        current_assets=500000, monthly_saving=10000, monthly_expense=r_expense,
        pre_return=7.0, post_return=4.0,
    )

    fig = make_subplots(rows=1, cols=3, subplot_titles=["复利实际终值", "储蓄达成月数", "退休缺口"])
    fig.add_trace(go.Bar(x=[f"{v}%" for v in inflation_values], y=result.compound_finals, marker_color="#2563eb", name="复利终值"), row=1, col=1)
    fig.add_trace(go.Bar(x=[f"{v}%" for v in inflation_values], y=result.savings_months, marker_color="#10b981", name="储蓄月数"), row=1, col=2)
    fig.add_trace(go.Bar(x=[f"{v}%" for v in inflation_values], y=result.retirement_gaps, marker_color="#ef4444", name="退休缺口"), row=1, col=3)
    fig.update_layout(height=420, showlegend=False, **build_layout(title="通胀率对各工具的影响"))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 详细数据")
    disp = result.summary.copy()
    disp["复利实际终值"] = disp["复利实际终值"].apply(lambda x: fmt(x, decimals=0))
    disp["退休缺口"] = disp["退休缺口"].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp, use_container_width=True, hide_index=True)

elif tab_choice == "收益率敏感度":
    st.subheader("📊 收益率敏感度分析")
    return_values = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0]

    result = run_return_scenarios(
        return_values=return_values,
        compound_principal=c_principal, compound_years=c_years,
        savings_current=s_current, savings_goal=s_goal, savings_deposit=s_deposit,
        current_age=r_age, retire_age=r_retire, life_expectancy=85,
        current_assets=500000, monthly_saving=10000, monthly_expense=r_expense,
        inflation=2.5,
    )

    fig = make_subplots(rows=1, cols=3, subplot_titles=["复利终值", "储蓄达成月数", "退休缺口"])
    fig.add_trace(go.Bar(x=[f"{v}%" for v in return_values], y=result.compound_finals, marker_color="#2563eb", name="复利终值"), row=1, col=1)
    fig.add_trace(go.Bar(x=[f"{v}%" for v in return_values], y=result.savings_months, marker_color="#10b981", name="储蓄月数"), row=1, col=2)
    fig.add_trace(go.Bar(x=[f"{v}%" for v in return_values], y=result.retirement_gaps, marker_color="#ef4444", name="退休缺口"), row=1, col=3)
    fig.update_layout(height=420, showlegend=False, **build_layout(title="收益率对各工具的影响"))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 详细数据")
    disp = result.summary.copy()
    disp["复利终值"] = disp["复利终值"].apply(lambda x: fmt(x, decimals=0))
    disp["退休缺口"] = disp["退休缺口"].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp, use_container_width=True, hide_index=True)

elif tab_choice == "贷款利率敏感度":
    st.subheader("📊 贷款利率敏感度分析")
    st.caption("分析贷款利率变动对月还款额、总利息、利息占比的影响。")

    rate_values = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0]
    n_months = loan_years * 12
    loan_rows = []

    for rate in rate_values:
        r_m = rate / 100 / 12
        if r_m > 0:
            monthly_pmt = loan_amount * r_m * (1 + r_m) ** n_months / ((1 + r_m) ** n_months - 1)
        else:
            monthly_pmt = loan_amount / n_months
        total_paid = monthly_pmt * n_months
        total_interest = total_paid - loan_amount
        interest_ratio = total_interest / loan_amount * 100
        loan_rows.append({
            "利率": f"{rate}%",
            "rate_val": rate,
            "月还款额": monthly_pmt,
            "总还款额": total_paid,
            "总利息": total_interest,
            "利息/本金比": interest_ratio,
        })

    loan_df = pd.DataFrame(loan_rows)

    fig_loan = make_subplots(rows=1, cols=3, subplot_titles=["月还款额", "总利息支出", "利息/本金比（%）"])
    fig_loan.add_trace(go.Bar(x=loan_df["利率"], y=loan_df["月还款额"], marker_color="#636EFA", name="月还款"), row=1, col=1)
    fig_loan.add_trace(go.Bar(x=loan_df["利率"], y=loan_df["总利息"], marker_color="#EF553B", name="总利息"), row=1, col=2)
    fig_loan.add_trace(go.Bar(x=loan_df["利率"], y=loan_df["利息/本金比"], marker_color="#FFA15A", name="利息占比"), row=1, col=3)
    fig_loan.update_layout(height=420, showlegend=False, **build_layout(title="贷款利率敏感度分析"))
    st.plotly_chart(fig_loan, use_container_width=True)

    baseline_idx = next((i for i, r in enumerate(rate_values) if r == 4.5), 4)
    baseline_interest = loan_df.iloc[baseline_idx]["总利息"]
    min_interest = loan_df["总利息"].min()
    st.success(f"✅ 利率每下降 0.5%，可节省总利息约 {fmt((loan_df.iloc[1]['总利息'] - loan_df.iloc[0]['总利息']), decimals=0)}。相比 {rate_values[baseline_idx]}%，最低利率可少付 {fmt(baseline_interest - min_interest, decimals=0)} 总利息。")

    st.subheader("📋 详细数据")
    display_df = loan_df[["利率", "月还款额", "总还款额", "总利息", "利息/本金比"]].copy()
    display_df["月还款额"] = display_df["月还款额"].apply(lambda x: fmt(x, decimals=0))
    display_df["总还款额"] = display_df["总还款额"].apply(lambda x: fmt(x, decimals=0))
    display_df["总利息"] = display_df["总利息"].apply(lambda x: fmt(x, decimals=0))
    display_df["利息/本金比"] = display_df["利息/本金比"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.subheader("📊 退休年龄敏感度分析")
    st.caption("分析不同退休年龄对退休资金需求、缺口、所需月储蓄的影响。")

    from core.retirement import calculate_retirement
    retire_age_values = list(range(max(r_age + 5, 50), 71))

    ret_rows = []
    for ra in retire_age_values:
        try:
            rr = calculate_retirement(
                current_age=r_age, retire_age=ra, life_expectancy=85,
                current_assets=300000, monthly_saving=8000,
                monthly_expense_today=r_expense, inflation_pct=3.0,
                pre_return_pct=7.0, post_return_pct=4.0,
            )
            ret_rows.append({
                "退休年龄": f"{ra}岁",
                "ra_val": ra,
                "所需资产": rr.total_needed_at_retire,
                "预测可积累": rr.projected_at_retire,
                "缺口": max(0, rr.gap),
                "额外月储蓄": max(0, rr.extra_monthly_needed),
            })
        except Exception:
            pass

    if ret_rows:
        ret_df = pd.DataFrame(ret_rows)

        fig_ret = make_subplots(rows=1, cols=3, subplot_titles=["所需退休资产", "退休资金缺口", "额外月储蓄需求"])
        fig_ret.add_trace(go.Scatter(x=ret_df["退休年龄"], y=ret_df["所需资产"], mode="lines+markers", line=dict(color="#636EFA", width=2.5), name="所需资产"), row=1, col=1)
        fig_ret.add_trace(go.Bar(x=ret_df["退休年龄"], y=ret_df["缺口"], marker_color="#EF553B", name="缺口"), row=1, col=2)
        fig_ret.add_trace(go.Scatter(x=ret_df["退休年龄"], y=ret_df["额外月储蓄"], mode="lines+markers", line=dict(color="#00CC96", width=2.5), name="月储蓄"), row=1, col=3)
        fig_ret.update_layout(height=420, showlegend=False, **build_layout(title="退休年龄对退休规划的影响"))
        st.plotly_chart(fig_ret, use_container_width=True)

        zero_gap = [r for r in ret_rows if r["缺口"] == 0]
        if zero_gap:
            earliest_zero = zero_gap[0]["ra_val"]
            st.success(f"✅ 按当前储蓄计划，**最早 {earliest_zero} 岁**退休即可实现无资金缺口。")
        else:
            st.warning("⚠️ 即使延迟至 70 岁退休，仍存在资金缺口。建议增加月储蓄或调低月支出预期。")

        st.subheader("📋 详细数据")
        display_ret = ret_df[["退休年龄", "所需资产", "预测可积累", "缺口", "额外月储蓄"]].copy()
        for col in ["所需资产", "预测可积累", "缺口", "额外月储蓄"]:
            display_ret[col] = display_ret[col].apply(lambda x: fmt(x, decimals=0))
        st.dataframe(display_ret, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("🔬 场景对比分析器 | 跨工具敏感度分析平台")
