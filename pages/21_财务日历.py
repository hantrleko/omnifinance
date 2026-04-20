"""财务日历与时间线 — 统一可视化所有财务事件

将贷款还款日、保费缴纳日、储蓄里程碑、退休节点等整合到一个时间线视图。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import MSG
from core.currency import fmt

st.set_page_config(page_title="财务日历", page_icon="📅", layout="wide")
st.title("📅 财务日历与时间线")
st.caption("将所有财务事件整合到统一时间线视图，掌控每个关键节点")

# ── Sidebar: Event Input ──────────────────────────────────
st.sidebar.header("📋 添加事件")
num_events = st.sidebar.number_input("事件数量", min_value=1, max_value=20, value=6, step=1)

events: list[dict[str, Any]] = []

default_events = [
    {"name": "房贷开始", "date": "2024-01-01", "cat": "债务", "amount": -8000, "recurring": "每月"},
    {"name": "保费缴纳", "date": "2024-03-15", "cat": "保险", "amount": -12000, "recurring": "每年"},
    {"name": "储蓄里程碑: 50万", "date": "2027-06-01", "cat": "储蓄", "amount": 500000, "recurring": "一次性"},
    {"name": "子女入学", "date": "2031-09-01", "cat": "教育", "amount": -200000, "recurring": "每年"},
    {"name": "贷款还清", "date": "2054-01-01", "cat": "债务", "amount": 0, "recurring": "一次性"},
    {"name": "退休日", "date": "2055-01-01", "cat": "退休", "amount": 0, "recurring": "一次性"},
]

categories = ["债务", "储蓄", "投资", "保险", "教育", "退休", "其他"]
recurrences = ["一次性", "每月", "每季", "每年"]

for i in range(int(num_events)):
    with st.sidebar.expander(f"事件 #{i+1}", expanded=(i < 3)):
        d = default_events[i] if i < len(default_events) else {"name": f"事件{i+1}", "date": "2025-01-01", "cat": "其他", "amount": 0, "recurring": "一次性"}
        name = st.text_input("名称", value=d["name"], key=f"ev_name_{i}")
        date = st.date_input("日期", value=datetime.strptime(d["date"], "%Y-%m-%d"), key=f"ev_date_{i}")
        cat = st.selectbox("类别", categories, index=categories.index(d["cat"]) if d["cat"] in categories else 0, key=f"ev_cat_{i}")
        amount = st.number_input("金额", value=float(d["amount"]), step=1000.0, key=f"ev_amt_{i}", help="正数=收入/里程碑，负数=支出")
        recurring = st.selectbox("频率", recurrences, index=recurrences.index(d["recurring"]) if d["recurring"] in recurrences else 0, key=f"ev_rec_{i}")
        events.append({"name": name, "date": date, "category": cat, "amount": amount, "recurring": recurring})

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

# ── Dashboard from session state ──────────────────────────
st.markdown("---")
st.subheader("🔗 从工具数据自动生成事件")

auto_events: list[dict[str, Any]] = []
today = datetime.now()

dash_savings = st.session_state.get("dashboard_savings")
if dash_savings:
    months = dash_savings.get("months_needed", 0)
    if months > 0:
        target_date = today + timedelta(days=months * 30)
        auto_events.append({"name": "储蓄目标达成", "date": target_date, "category": "储蓄", "amount": 0, "recurring": "一次性"})

dash_retirement = st.session_state.get("dashboard_retirement")
if dash_retirement:
    auto_events.append({"name": "退休目标评估", "date": today + timedelta(days=365), "category": "退休", "amount": -dash_retirement.get("gap", 0), "recurring": "一次性"})

if auto_events:
    st.info(f"从仪表盘数据中检测到 {len(auto_events)} 个自动事件。")
else:
    st.caption("使用更多工具后，将自动检测并关联财务事件。")

all_events = events + auto_events

# ── Timeline visualization ────────────────────────────────
st.markdown("---")
st.subheader("📅 事件时间线")

sorted_events = sorted(all_events, key=lambda e: e["date"])

# Category colors
cat_colors = {
    "债务": "#ef4444", "储蓄": "#10b981", "投资": "#2563eb",
    "保险": "#8b5cf6", "教育": "#f59e0b", "退休": "#ec4899", "其他": "#6b7280",
}

fig = go.Figure()
for idx, ev in enumerate(sorted_events):
    date_val = ev["date"] if isinstance(ev["date"], datetime) else datetime.combine(ev["date"], datetime.min.time())
    color = cat_colors.get(ev["category"], "#6b7280")
    fig.add_trace(go.Scatter(
        x=[date_val], y=[ev["category"]],
        mode="markers+text",
        marker=dict(size=16, color=color),
        text=[ev["name"]],
        textposition="top center",
        name=ev["name"],
        showlegend=False,
        hovertemplate=f"<b>{ev['name']}</b><br>日期: %{{x|%Y-%m-%d}}<br>类别: {ev['category']}<br>金额: {fmt(ev['amount'], decimals=0)}<extra></extra>",
    ))

fig.update_layout(
    **build_layout(title="财务事件时间线", xaxis_title="日期"),
    height=400,
    yaxis=dict(categoryorder="array", categoryarray=categories),
)
st.plotly_chart(fig, use_container_width=True)

# ── Event table ───────────────────────────────────────────
st.markdown("---")
st.subheader("📋 事件列表")

table_rows = []
for ev in sorted_events:
    date_str = ev["date"].strftime("%Y-%m-%d") if isinstance(ev["date"], datetime) else str(ev["date"])
    table_rows.append({
        "日期": date_str,
        "事件": ev["name"],
        "类别": ev["category"],
        "金额": fmt(ev["amount"], decimals=0),
        "频率": ev["recurring"],
    })
st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

# ── Annual cashflow projection ────────────────────────────
st.markdown("---")
st.subheader("📊 年度现金流预估")

current_year = today.year
projection_years = 10
year_cashflows: dict[int, float] = {y: 0.0 for y in range(current_year, current_year + projection_years)}

for ev in all_events:
    ev_date = ev["date"] if isinstance(ev["date"], datetime) else datetime.combine(ev["date"], datetime.min.time())
    for y in range(current_year, current_year + projection_years):
        if ev["recurring"] == "一次性" and ev_date.year == y:
            year_cashflows[y] += ev["amount"]
        elif ev["recurring"] == "每月":
            if ev_date.year <= y:
                year_cashflows[y] += ev["amount"] * 12
        elif ev["recurring"] == "每季":
            if ev_date.year <= y:
                year_cashflows[y] += ev["amount"] * 4
        elif ev["recurring"] == "每年":
            if ev_date.year <= y:
                year_cashflows[y] += ev["amount"]

fig2 = go.Figure()
years_list = list(year_cashflows.keys())
values_list = list(year_cashflows.values())
colors_bar = ["#10b981" if v >= 0 else "#ef4444" for v in values_list]
fig2.add_trace(go.Bar(x=years_list, y=values_list, marker_color=colors_bar))
fig2.update_layout(**build_layout(title="年度净现金流预估", xaxis_title="年份", yaxis_title="净现金流", yaxis_tickformat=",.0f"))
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.caption("📅 财务日历 | 运行命令：`streamlit run app.py`")
