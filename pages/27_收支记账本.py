"""收支记账本 — 个人收入与支出记录

支持：
- 收支记录的添加与删除
- 按月份/类别统计
- 月度收支趋势图
- 预算 vs 实际对比
- 数据本地持久化
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.theme import inject_theme

inject_theme()

from core.chart_config import build_layout
from core.currency import fmt, get_symbol

st.set_page_config(page_title="收支记账本", page_icon="📒", layout="wide")

st.title("📒 收支记账本")
st.caption("记录日常收支，追踪月度趋势，与预算对比，助力精细化财务管理。")

sym = get_symbol()

# ── 数据持久化 ────────────────────────────────────────────
_LEDGER_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "ledger.json"

def _load_ledger() -> list[dict]:
    if not _LEDGER_PATH.exists():
        return []
    try:
        data = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []

def _save_ledger(records: list[dict]) -> None:
    try:
        _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        _LEDGER_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass

if "ledger_records" not in st.session_state:
    st.session_state["ledger_records"] = _load_ledger()

records = st.session_state["ledger_records"]

# ── 分类常量 ──────────────────────────────────────────────
INCOME_CATS = ["工资薪金", "奖金", "兼职收入", "投资收益", "租金收入", "其他收入"]
EXPENSE_CATS = ["餐饮", "购物", "交通", "居住", "医疗", "教育", "娱乐", "旅行", "保险", "还贷", "其他支出"]

# ── 侧边栏：新增记录 ──────────────────────────────────────
st.sidebar.header("➕ 新增记录")

entry_type = st.sidebar.radio("类型", ["收入", "支出"], horizontal=True, key="entry_type")
entry_date = st.sidebar.date_input("日期", value=date.today(), key="entry_date")
entry_cat = st.sidebar.selectbox(
    "类别",
    INCOME_CATS if entry_type == "收入" else EXPENSE_CATS,
    key="entry_cat",
)
entry_amount = st.sidebar.number_input("金额（元）", min_value=0.01, value=100.0, step=10.0, format="%.2f", key="entry_amount")
entry_note = st.sidebar.text_input("备注（可选）", placeholder="如：午饭、房租…", key="entry_note")

if st.sidebar.button("✅ 添加记录", type="primary", key="add_entry_btn"):
    new_record = {
        "id": datetime.now().isoformat(),
        "date": entry_date.isoformat(),
        "type": entry_type,
        "category": entry_cat,
        "amount": float(entry_amount),
        "note": entry_note.strip(),
    }
    records.append(new_record)
    _save_ledger(records)
    st.sidebar.success(f"已添加：{entry_type} {fmt(entry_amount)} — {entry_cat}")
    st.rerun()

st.sidebar.divider()

# ── 预算设置 ──────────────────────────────────────────────
with st.sidebar.expander("📊 月度预算设置"):
    if "monthly_budgets" not in st.session_state:
        st.session_state["monthly_budgets"] = {}
    budgets = st.session_state["monthly_budgets"]

    st.caption("为各类别设置每月预算上限（0 = 不限制）")
    for cat in EXPENSE_CATS[:6]:
        budgets[cat] = st.number_input(f"{cat}（元）", min_value=0.0, value=float(budgets.get(cat, 0)), step=100.0, format="%.0f", key=f"budget_{cat}")

# ── 主体：数据分析 ────────────────────────────────────────
if not records:
    st.info("暂无记录。请在左侧添加收支记录。")
    st.stop()

df = pd.DataFrame(records)
df["date"] = pd.to_datetime(df["date"])
df["year_month"] = df["date"].dt.to_period("M").astype(str)
df["month_label"] = df["date"].dt.strftime("%Y-%m")

# ── 筛选面板 ─────────────────────────────────────────────
all_months = sorted(df["year_month"].unique(), reverse=True)
filter_col1, filter_col2, filter_col3 = st.columns(3)
sel_month = filter_col1.selectbox("按月筛选", ["全部"] + all_months, key="ledger_month_filter")
sel_type = filter_col2.radio("类型", ["全部", "收入", "支出"], horizontal=True, key="ledger_type_filter")
sel_cat = filter_col3.selectbox("类别", ["全部"] + INCOME_CATS + EXPENSE_CATS, key="ledger_cat_filter")

view_df = df.copy()
if sel_month != "全部":
    view_df = view_df[view_df["year_month"] == sel_month]
if sel_type != "全部":
    view_df = view_df[view_df["type"] == sel_type]
if sel_cat != "全部":
    view_df = view_df[view_df["category"] == sel_cat]

# ── 汇总指标 ──────────────────────────────────────────────
st.markdown("---")
total_income = view_df[view_df["type"] == "收入"]["amount"].sum()
total_expense = view_df[view_df["type"] == "支出"]["amount"].sum()
net = total_income - total_expense

m1, m2, m3, m4 = st.columns(4)
m1.metric("总收入", fmt(total_income, decimals=0))
m2.metric("总支出", fmt(total_expense, decimals=0))
m3.metric("净结余", fmt(net, decimals=0), delta_color="normal" if net >= 0 else "inverse")
m4.metric("记录条数", len(view_df))

# ── 记录明细表 ────────────────────────────────────────────
st.subheader("📋 收支明细")

display_df = view_df.sort_values("date", ascending=False).copy()
display_df["金额"] = display_df.apply(
    lambda r: f"+ {fmt(r['amount'], decimals=2)}" if r["type"] == "收入" else f"- {fmt(r['amount'], decimals=2)}",
    axis=1,
)
display_df["日期"] = display_df["date"].dt.strftime("%Y-%m-%d")
table_out = display_df[["日期", "type", "category", "金额", "note"]].rename(columns={
    "type": "类型", "category": "类别", "note": "备注"
})
st.dataframe(table_out, use_container_width=True, hide_index=True)

# ── 删除记录 ──────────────────────────────────────────────
with st.expander("🗑️ 删除记录"):
    if records:
        del_options = {
            f"{r['date']} | {r['type']} | {r['category']} | {sym}{r['amount']:,.2f} | {r.get('note','')}" : r["id"]
            for r in records
        }
        del_label = st.selectbox("选择要删除的记录", list(del_options.keys()), key="del_record_sel")
        if st.button("确认删除", key="del_record_btn"):
            del_id = del_options[del_label]
            records[:] = [r for r in records if r["id"] != del_id]
            _save_ledger(records)
            st.success("已删除记录")
            st.rerun()

# ── 月度趋势图 ────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 月度收支趋势")

monthly = df.groupby(["month_label", "type"])["amount"].sum().unstack(fill_value=0).reset_index()
monthly.columns.name = None
if "收入" not in monthly.columns:
    monthly["收入"] = 0.0
if "支出" not in monthly.columns:
    monthly["支出"] = 0.0

fig_trend = go.Figure()
fig_trend.add_trace(go.Bar(
    x=monthly["month_label"], y=monthly["收入"],
    name="收入", marker_color="#00CC96",
    hovertemplate="月份: %{x}<br>收入: " + sym + "%{y:,.0f}<extra></extra>",
))
fig_trend.add_trace(go.Bar(
    x=monthly["month_label"], y=monthly["支出"],
    name="支出", marker_color="#EF553B",
    hovertemplate="月份: %{x}<br>支出: " + sym + "%{y:,.0f}<extra></extra>",
))
fig_trend.add_trace(go.Scatter(
    x=monthly["month_label"],
    y=monthly["收入"] - monthly["支出"],
    mode="lines+markers", name="净结余",
    line=dict(width=2, color="#636EFA", dash="dot"),
    hovertemplate="月份: %{x}<br>净结余: " + sym + "%{y:,.0f}<extra></extra>",
))
fig_trend.update_layout(**build_layout(
    barmode="group", xaxis_title="月份", yaxis_title="金额（元）",
    yaxis_tickformat=",",
))
st.plotly_chart(fig_trend, use_container_width=True)

# ── 类别分析 ──────────────────────────────────────────────
tab_exp, tab_inc = st.tabs(["💸 支出分类", "💰 收入分类"])

with tab_exp:
    exp_df = df[df["type"] == "支出"]
    if sel_month != "全部":
        exp_df = exp_df[exp_df["year_month"] == sel_month]
    cat_exp = exp_df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    if not cat_exp.empty:
        fig_exp = go.Figure(go.Pie(
            labels=cat_exp["category"],
            values=cat_exp["amount"],
            hole=0.4,
            hovertemplate="%{label}<br>" + sym + "%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        fig_exp.update_layout(**build_layout(showlegend=True, height=400))
        st.plotly_chart(fig_exp, use_container_width=True)

        # 预算 vs 实际：遍历所有已设置预算的类别，支出为0的也显示
        _budgets = st.session_state.get("monthly_budgets", {})
        _active_budgets = {cat: amt for cat, amt in _budgets.items() if amt > 0}
        _cat_actual = dict(zip(cat_exp["category"], cat_exp["amount"]))
        budget_rows = []
        for cat, budget in _active_budgets.items():
            actual = float(_cat_actual.get(cat, 0.0))
            budget_rows.append({
                "类别": cat,
                "实际支出": actual,
                "预算": float(budget),
                "超支": max(0.0, actual - float(budget)),
                "状态": "⚠️ 超支" if actual > float(budget) else "✅ 达标",
            })
        if budget_rows:
            st.markdown("**预算 vs 实际对比**")
            bdf = pd.DataFrame(budget_rows)
            fig_bud = go.Figure()
            fig_bud.add_trace(go.Bar(x=bdf["类别"], y=bdf["预算"], name="预算", marker_color="rgba(100,149,237,0.6)"))
            fig_bud.add_trace(go.Bar(x=bdf["类别"], y=bdf["实际支出"], name="实际支出", marker_color="#EF553B"))
            fig_bud.update_layout(**build_layout(barmode="group", xaxis_title="类别", yaxis_title="金额（元）", yaxis_tickformat=",", height=350))
            st.plotly_chart(fig_bud, use_container_width=True)
    else:
        st.info("暂无支出记录。")

with tab_inc:
    inc_df = df[df["type"] == "收入"]
    if sel_month != "全部":
        inc_df = inc_df[inc_df["year_month"] == sel_month]
    cat_inc = inc_df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    if not cat_inc.empty:
        fig_inc = go.Figure(go.Pie(
            labels=cat_inc["category"],
            values=cat_inc["amount"],
            hole=0.4,
            hovertemplate="%{label}<br>" + sym + "%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        fig_inc.update_layout(**build_layout(showlegend=True, height=400))
        st.plotly_chart(fig_inc, use_container_width=True)
    else:
        st.info("暂无收入记录。")

# ── 导出 ──────────────────────────────────────────────────
st.markdown("---")
st.subheader("📤 导出数据")

import io
buf = io.StringIO()
df.drop(columns=["year_month", "month_label"], errors="ignore").to_csv(buf, index=False, encoding="utf-8-sig")
st.download_button("📥 导出全部记录 (CSV)", data=buf.getvalue(), file_name="收支记账本.csv", mime="text/csv")

st.divider()
st.caption("📒 收支记账本 | 数据存储于本地 ~/.omnifinance/ledger.json")
