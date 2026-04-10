"""场景对比分析器 — 跨工具全局敏感度分析

统一对比不同通胀率、收益率假设对复利、储蓄、退休的影响。
"""

from __future__ import annotations

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
st.caption("跨工具 What-If 分析 — 同一参数变动在复利、储蓄、退休中的联动影响")

sym = get_symbol()

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.header("📋 基准参数")
tab_choice = st.sidebar.radio("分析维度", ["通胀率敏感度", "收益率敏感度"])

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
    fig.update_layout(height=400, showlegend=False, **build_layout(title="通胀率对各工具的影响"))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 详细数据")
    disp = result.summary.copy()
    disp["复利实际终值"] = disp["复利实际终值"].apply(lambda x: fmt(x, decimals=0))
    disp["退休缺口"] = disp["退休缺口"].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp, use_container_width=True, hide_index=True)

else:
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
    fig.update_layout(height=400, showlegend=False, **build_layout(title="收益率对各工具的影响"))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 详细数据")
    disp = result.summary.copy()
    disp["复利终值"] = disp["复利终值"].apply(lambda x: fmt(x, decimals=0))
    disp["退休缺口"] = disp["退休缺口"].apply(lambda x: fmt(x, decimals=0))
    st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("🔬 场景对比分析器 | 运行命令：`streamlit run app.py`")
