"""财务日记 — 每月净资产快照 + 心情标注 + 年度时间轴

数据通过 core/storage.py JSON 机制本地持久化。
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.currency import fmt, get_symbol
from core.report_generator import build_single_report

st.set_page_config(page_title="财务日记", page_icon="📔", layout="wide")
st.markdown("""<style>.block-container{padding-top:1.2rem}.stMetric{background-color:var(--secondary-background-color);border:1px solid var(--secondary-background-color);border-radius:8px;padding:14px}</style>""", unsafe_allow_html=True)
st.title("📔 财务日记")
st.caption("记录每月净资产快照与心情标注，追踪财务旅程")

sym = get_symbol()

# ── Storage helpers ────────────────────────────────────────
_DIARY_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "diary.json"


def _load_entries() -> list[dict[str, Any]]:
    if not _DIARY_PATH.exists():
        return []
    try:
        data = json.loads(_DIARY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_entries(entries: list[dict[str, Any]]) -> None:
    _DIARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DIARY_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


MOOD_OPTIONS = ["😊 满意", "😐 一般", "😟 担忧", "💪 充满斗志", "🎉 里程碑！"]

# ── New entry form ─────────────────────────────────────────
st.subheader("➕ 添加本月记录")

with st.form("diary_form"):
    fc1, fc2 = st.columns(2)
    entry_date = fc1.date_input("记录日期", value=datetime.date.today())
    net_worth = fc2.number_input(f"本月净资产 ({sym})", value=0.0, step=1000.0)
    mood = st.selectbox("心情标注", MOOD_OPTIONS)
    note = st.text_input("一句话备注（可选）", placeholder="例如：终于还清了信用卡！")
    submitted = st.form_submit_button("💾 保存记录", use_container_width=True)

if submitted:
    entries = _load_entries()
    new_entry: dict[str, Any] = {
        "date": str(entry_date),
        "net_worth": net_worth,
        "mood": mood,
        "note": note,
    }
    date_keys = [e["date"] for e in entries]
    if str(entry_date) in date_keys:
        idx = date_keys.index(str(entry_date))
        entries[idx] = new_entry
        st.success(f"已更新 {entry_date} 的记录。")
    else:
        entries.append(new_entry)
        st.success(f"已保存 {entry_date} 的财务日记。")
    entries.sort(key=lambda e: e["date"])
    _save_entries(entries)
    st.rerun()

# ── Load and display ───────────────────────────────────────
entries = _load_entries()

if not entries:
    st.info("还没有记录。填写上方表单添加第一条财务日记吧！")
    st.stop()

# ── Timeline chart ─────────────────────────────────────────
st.markdown("---")
st.subheader("📈 净资产时间轴")

df = pd.DataFrame(entries)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["date"], y=df["net_worth"],
    mode="lines+markers",
    name="净资产",
    line=dict(width=2.5, color="#2563eb"),
    marker=dict(size=8, color="#2563eb"),
    hovertemplate=(
        "%{x|%Y-%m-%d}<br>"
        "净资产: " + sym + "%{y:,.0f}<br>"
        "%{customdata}<extra></extra>"
    ),
    customdata=[(f"{e['mood']}  {e.get('note', '')}") for _, e in df.iterrows()],
))
fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
fig.update_layout(**build_layout(
    title="财务日记 — 净资产走势",
    xaxis_title="日期",
    yaxis_title=f"净资产 ({sym})",
    yaxis_tickformat=",.0f",
))
st.plotly_chart(fig, use_container_width=True)

# ── Year filter ────────────────────────────────────────────
years_available = sorted(df["date"].dt.year.unique().tolist(), reverse=True)
selected_year = st.selectbox("筛选年份", ["全部"] + [str(y) for y in years_available])

if selected_year != "全部":
    df_view = df[df["date"].dt.year == int(selected_year)]
else:
    df_view = df

# ── Entry list ─────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 日记记录列表")

display_rows = []
for _, row in df_view.sort_values("date", ascending=False).iterrows():
    display_rows.append({
        "日期": row["date"].strftime("%Y-%m-%d"),
        "净资产": fmt(row["net_worth"], decimals=0),
        "心情": row["mood"],
        "备注": row.get("note", ""),
    })

st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

# ── Delete entry ───────────────────────────────────────────
with st.expander("🗑️ 删除记录"):
    del_date = st.selectbox("选择要删除的日期", [e["date"] for e in entries])
    if st.button("确认删除", type="secondary"):
        entries = [e for e in entries if e["date"] != del_date]
        _save_entries(entries)
        st.success(f"已删除 {del_date} 的记录。")
        st.rerun()

# ── Annual review export ───────────────────────────────────
st.markdown("---")
st.subheader("📄 生成年度财务回顾")

review_year = st.selectbox("选择年份", [str(y) for y in years_available], key="review_yr")
if st.button("生成年度财务回顾 HTML"):
    yr_int = int(review_year)
    yr_df = df[df["date"].dt.year == yr_int].sort_values("date")

    if yr_df.empty:
        st.warning("该年份没有记录。")
    else:
        start_nw = yr_df["net_worth"].iloc[0]
        end_nw = yr_df["net_worth"].iloc[-1]
        change_nw = end_nw - start_nw
        change_pct = (change_nw / abs(start_nw) * 100) if start_nw != 0 else 0
        best_mood_row = yr_df.loc[yr_df["net_worth"].idxmax()]
        worst_mood_row = yr_df.loc[yr_df["net_worth"].idxmin()]

        row_html = "".join(
            f"<tr><td>{r['date'].strftime('%Y-%m-%d')}</td><td>{fmt(r['net_worth'], decimals=0)}</td><td>{r['mood']}</td><td>{r.get('note','')}</td></tr>"
            for _, r in yr_df.iterrows()
        )

        body = f"""
<div class="summary">
  <div><div class="label">年初净资产</div><div class="value">{fmt(start_nw, decimals=0)}</div></div>
  <div><div class="label">年末净资产</div><div class="value">{fmt(end_nw, decimals=0)}</div></div>
  <div><div class="label">全年变动</div><div class="value {'highlight' if change_nw >= 0 else 'warn'}">{'+' if change_nw >= 0 else ''}{fmt(change_nw, decimals=0)} ({change_pct:+.1f}%)</div></div>
  <div><div class="label">记录次数</div><div class="value">{len(yr_df)} 条</div></div>
</div>
<h2>最佳时刻：{best_mood_row['date'].strftime('%Y-%m-%d')}</h2>
<p>净资产 {fmt(best_mood_row['net_worth'], decimals=0)} — {best_mood_row['mood']}</p>
<h2>待改善时刻：{worst_mood_row['date'].strftime('%Y-%m-%d')}</h2>
<p>净资产 {fmt(worst_mood_row['net_worth'], decimals=0)} — {worst_mood_row['mood']}</p>
<h2>全年记录明细</h2>
<table>
  <thead><tr><th style="text-align:left">日期</th><th>净资产</th><th>心情</th><th style="text-align:left">备注</th></tr></thead>
  <tbody>{row_html}</tbody>
</table>
"""
        html = build_single_report(
            title=f"📔 {review_year} 年度财务回顾",
            subtitle=f"共 {len(yr_df)} 条日记记录 | OmniFinance 财务日记",
            body_html=body,
        )
        st.download_button(
            "📥 下载年度回顾 HTML",
            data=html,
            file_name=f"财务日记年度回顾_{review_year}.html",
            mime="text/html",
            use_container_width=True,
        )

st.markdown("---")
st.caption("📔 财务日记 | 运行命令：`streamlit run app.py`")
