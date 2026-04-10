"""债务还清规划器 — 雪球法 / 雪崩法 / 混合法策略对比

支持多笔债务同时管理，对比三种还款策略的总利息、还清时长差异。
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import fmt, get_symbol
from core.debt import DebtItem, compare_strategies, simulate_payoff

st.set_page_config(page_title="债务还清规划器", page_icon="💳", layout="wide")
st.markdown("""<style>.block-container{padding-top:1.2rem}.stMetric{background-color:var(--secondary-background-color);border:1px solid var(--secondary-background-color);border-radius:8px;padding:14px}</style>""", unsafe_allow_html=True)
st.title("💳 债务还清规划器")
st.caption("对比雪球法（最小余额优先）、雪崩法（最高利率优先）和混合法，找到最优还款策略")

# ── Sidebar inputs ────────────────────────────────────────
st.sidebar.header("📋 债务清单")

num_debts = st.sidebar.number_input("债务笔数", min_value=1, max_value=10, value=3, step=1)

debts: list[DebtItem] = []
for i in range(int(num_debts)):
    with st.sidebar.expander(f"债务 #{i+1}", expanded=(i < 3)):
        name = st.text_input("名称", value=f"债务{i+1}", key=f"debt_name_{i}")
        balance = st.number_input("余额", min_value=0.0, value=[50000.0, 20000.0, 80000.0, 30000.0][i % 4], step=1000.0, key=f"debt_bal_{i}")
        rate = st.number_input("年利率(%)", min_value=0.0, max_value=50.0, value=[18.0, 12.0, 5.0, 24.0][i % 4], step=0.1, key=f"debt_rate_{i}")
        min_pay = st.number_input("最低月还款", min_value=0.0, value=[1500.0, 800.0, 2000.0, 1000.0][i % 4], step=100.0, key=f"debt_min_{i}")
        if balance > 0:
            debts.append(DebtItem(name=name, balance=balance, rate_pct=rate, min_payment=min_pay))

extra = st.sidebar.number_input("每月额外可用还款金额", min_value=0.0, value=3000.0, step=500.0, help="在所有最低还款之外，每月可以额外投入的还款预算")

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

# ── Validation ────────────────────────────────────────────
if len(debts) < 1:
    st.warning("请添加至少一笔债务。")
    st.stop()

total_min = sum(d.min_payment for d in debts)
total_balance = sum(d.balance for d in debts)
sym = get_symbol()

# ── Run strategies ────────────────────────────────────────
st.markdown("---")
st.subheader("📊 策略对比总览")

results = compare_strategies(debts, extra)

strategy_names = {"avalanche": "🏔️ 雪崩法（高利率优先）", "snowball": "⛄ 雪球法（小余额优先）", "hybrid": "🔀 混合法"}

cols = st.columns(3)
best_strategy = min(results, key=lambda k: results[k].total_interest)

for idx, (key, label) in enumerate(strategy_names.items()):
    r = results[key]
    with cols[idx]:
        badge = " 🏆" if key == best_strategy else ""
        st.metric(f"{label}{badge}", f"{r.months_to_payoff}个月")
        y, m = r.months_to_payoff // 12, r.months_to_payoff % 12
        st.caption(f"约 {y}年{m}个月")
        st.metric("总利息支出", fmt(r.total_interest, decimals=0))
        st.metric("总还款额", fmt(r.total_paid, decimals=0))

# Interest savings
best = results[best_strategy]
worst_strategy = max(results, key=lambda k: results[k].total_interest)
worst = results[worst_strategy]
savings = worst.total_interest - best.total_interest
if savings > 0:
    st.success(f"✅ **{strategy_names[best_strategy]}** 是最优策略！相比最差方案可节省利息 **{fmt(savings, decimals=0)}**，提前 **{worst.months_to_payoff - best.months_to_payoff}** 个月还清。")

# ── Balance over time chart ───────────────────────────────
st.markdown("---")
st.subheader("📈 总余额变化对比")

fig = go.Figure()
for key, label in strategy_names.items():
    r = results[key]
    fig.add_trace(go.Scatter(
        x=r.schedule["月份"], y=r.schedule["总余额"],
        mode="lines", name=label,
        line=dict(width=2.5),
    ))
fig.update_layout(**build_layout(
    title="三种策略债务余额对比",
    xaxis_title="月份",
    yaxis_title=f"总余额 ({sym})",
    yaxis_tickformat=",.0f",
))
st.plotly_chart(fig, use_container_width=True)

# ── Per-debt payoff timeline ──────────────────────────────
st.markdown("---")
st.subheader("🗓️ 各债务还清时间线")

selected_strategy = st.selectbox("选择策略查看详情", list(strategy_names.keys()), format_func=lambda x: strategy_names[x])
result = results[selected_strategy]

st.dataframe(result.per_debt_summary.style.format({
    "初始余额": lambda x: fmt(x, decimals=0),
    "累计利息": lambda x: fmt(x, decimals=0),
}), use_container_width=True, hide_index=True)

# Per-debt balance chart
fig2 = go.Figure()
for d in debts:
    col_name = f"{d.name}_余额"
    if col_name in result.schedule.columns:
        fig2.add_trace(go.Scatter(
            x=result.schedule["月份"], y=result.schedule[col_name],
            mode="lines", name=d.name,
            stackgroup="one",
        ))
fig2.update_layout(**build_layout(
    title=f"{strategy_names[selected_strategy]} - 各债务余额变化",
    xaxis_title="月份",
    yaxis_title=f"余额 ({sym})",
    yaxis_tickformat=",.0f",
))
st.plotly_chart(fig2, use_container_width=True)

# ── Strategy explanation ──────────────────────────────────
st.markdown("---")
with st.expander("📖 策略说明"):
    st.markdown("""
**🏔️ 雪崩法 (Avalanche)**：优先偿还利率最高的债务。数学上最优，总利息最少。

**⛄ 雪球法 (Snowball)**：优先偿还余额最小的债务。心理学上更有动力，快速消灭小债务带来成就感。

**🔀 混合法 (Hybrid)**：在中小额债务中优先偿还高利率的。兼顾数学效率与心理激励。

**建议**：如果自律性强，选雪崩法省最多钱；如果需要激励感，选雪球法；不确定就用混合法。
""")

st.markdown("---")
st.caption("💳 债务还清规划器 | 运行命令：`streamlit run app.py`")
