"""历史回测储蓄模拟器 — 用真实历史收益率回测储蓄/退休计划

如果从2000年/2008年/2015年开始定投，实际结果如何？
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import MSG
from core.currency import fmt, get_symbol

st.set_page_config(page_title="历史回测储蓄模拟", page_icon="📜", layout="wide")
st.markdown("""<style>.block-container{padding-top:1.2rem}.stMetric{background-color:var(--secondary-background-color);border:1px solid var(--secondary-background-color);border-radius:8px;padding:14px}</style>""", unsafe_allow_html=True)
st.title("📜 历史回测储蓄模拟")
st.caption("用历史市场真实回报率验证定投计划，对比假设收益 vs 实际结果")

sym = get_symbol()

# ── Historical data (simplified annual returns) ───────────
# S&P 500 approximate annual total returns
SP500_RETURNS = {
    2000: -9.1, 2001: -11.9, 2002: -22.1, 2003: 28.7, 2004: 10.9,
    2005: 4.9, 2006: 15.8, 2007: 5.5, 2008: -37.0, 2009: 26.5,
    2010: 15.1, 2011: 2.1, 2012: 16.0, 2013: 32.4, 2014: 13.7,
    2015: 1.4, 2016: 12.0, 2017: 21.8, 2018: -4.4, 2019: 31.5,
    2020: 18.4, 2021: 28.7, 2022: -18.1, 2023: 26.3, 2024: 25.0,
    2025: 5.0,
}

# CSI 300 (沪深300) approximate annual returns
CSI300_RETURNS = {
    2005: -7.7, 2006: 121.0, 2007: 161.6, 2008: -65.9, 2009: 96.7,
    2010: -12.5, 2011: -25.0, 2012: 7.6, 2013: -7.6, 2014: 51.7,
    2015: 5.6, 2016: -11.3, 2017: 21.8, 2018: -25.3, 2019: 36.1,
    2020: 27.2, 2021: -5.2, 2022: -21.6, 2023: -11.4, 2024: 14.7,
    2025: 2.0,
}

MARKET_DATA = {"标普500 (S&P 500)": SP500_RETURNS, "沪深300 (CSI 300)": CSI300_RETURNS}

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.header("📋 参数设置")
market = st.sidebar.selectbox("参考市场", list(MARKET_DATA.keys()))
returns_data = MARKET_DATA[market]
available_years = sorted(returns_data.keys())

start_year = st.sidebar.selectbox("起始年份", available_years[:len(available_years)-5], index=0)
end_year = available_years[-1]
initial = st.sidebar.number_input("初始投入", min_value=0.0, value=100000.0, step=10000.0, format="%.0f")
monthly = st.sidebar.number_input("每月定投", min_value=0.0, value=5000.0, step=1000.0, format="%.0f")
assumed_rate = st.sidebar.slider("假设固定收益率(%)", min_value=0.0, max_value=15.0, value=6.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.caption(MSG.disclaimer_research)

# ── Simulation ────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 模拟结果")

sim_years = [y for y in available_years if start_year <= y <= end_year]
if len(sim_years) < 2:
    st.warning("选择的时间范围内数据不足。")
    st.stop()

# Historical simulation
balance_hist = initial
rows_hist: list[dict[str, Any]] = [{"年份": start_year, "余额": balance_hist, "类型": "历史实际"}]
for yr in sim_years[1:]:
    ret = returns_data.get(yr, 0.0) / 100
    yearly_contrib = monthly * 12
    # Monthly DCA: approximate as contribution at mid-year earning half the annual return
    balance_hist = balance_hist * (1 + ret) + yearly_contrib * (1 + ret / 2)
    rows_hist.append({"年份": yr, "余额": balance_hist, "类型": "历史实际"})

# Assumed fixed rate simulation
balance_assumed = initial
rows_assumed: list[dict[str, Any]] = [{"年份": start_year, "余额": balance_assumed, "类型": "假设固定"}]
for yr in sim_years[1:]:
    ret = assumed_rate / 100
    yearly_contrib = monthly * 12
    balance_assumed = balance_assumed * (1 + ret) + yearly_contrib * (1 + ret / 2)
    rows_assumed.append({"年份": yr, "余额": balance_assumed, "类型": "假设固定"})

df_hist = pd.DataFrame(rows_hist)
df_assumed = pd.DataFrame(rows_assumed)

# Metrics
actual_years = len(sim_years) - 1
total_contrib = initial + monthly * 12 * actual_years
actual_return = (balance_hist / total_contrib - 1) * 100 if total_contrib > 0 else 0
assumed_return_total = (balance_assumed / total_contrib - 1) * 100 if total_contrib > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("📅 投资期", f"{actual_years} 年")
c2.metric("💰 历史终值", fmt(balance_hist, decimals=0))
c3.metric("📊 假设终值", fmt(balance_assumed, decimals=0))
c4.metric("📈 差距", fmt(balance_hist - balance_assumed, decimals=0))

if balance_hist > balance_assumed:
    st.success(f"✅ 在 {market} 中，{start_year}年开始的实际收益 **优于** {assumed_rate}% 的固定假设，多出 {fmt(balance_hist - balance_assumed, decimals=0)}。")
else:
    st.warning(f"⚠️ 在 {market} 中，{start_year}年开始的实际收益 **低于** {assumed_rate}% 的固定假设，少了 {fmt(balance_assumed - balance_hist, decimals=0)}。")

# ── Chart ─────────────────────────────────────────────────
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_hist["年份"], y=df_hist["余额"], mode="lines+markers", name="历史实际", line=dict(width=3, color="#2563eb")))
fig.add_trace(go.Scatter(x=df_assumed["年份"], y=df_assumed["余额"], mode="lines", name=f"假设{assumed_rate}%", line=dict(width=2, dash="dash", color="#ef4444")))
fig.update_layout(**build_layout(title=f"{market} 定投回测 ({start_year}-{end_year})", xaxis_title="年份", yaxis_title=f"余额 ({sym})", yaxis_tickformat=",.0f"))
st.plotly_chart(fig, use_container_width=True)

# ── Annual returns table ──────────────────────────────────
st.markdown("---")
st.subheader("📋 历史年度收益率")

ret_rows = []
for yr in sim_years:
    r = returns_data.get(yr, 0.0)
    ret_rows.append({"年份": yr, "收益率(%)": f"{r:+.1f}%", "正负": "📈" if r >= 0 else "📉"})
st.dataframe(pd.DataFrame(ret_rows), use_container_width=True, hide_index=True)

# ── Multi-start comparison ────────────────────────────────
st.markdown("---")
st.subheader("🔄 不同起始年份对比")
st.caption("如果在不同年份开始同样的定投计划，10年后的结果")

comp_rows = []
for sy in available_years:
    end_y = sy + 10
    sub_years = [y for y in available_years if sy <= y <= end_y]
    if len(sub_years) < 5:
        continue
    bal = initial
    for yr in sub_years[1:]:
        ret = returns_data.get(yr, 0.0) / 100
        bal = bal * (1 + ret) + monthly * 12 * (1 + ret / 2)
    actual_yrs = len(sub_years) - 1
    total_in = initial + monthly * 12 * actual_yrs
    comp_rows.append({
        "起始年": sy, "结束年": sub_years[-1], "投入": fmt(total_in, decimals=0),
        "终值": fmt(bal, decimals=0), "总收益率": f"{(bal/total_in-1)*100:.1f}%",
    })
if comp_rows:
    st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("📜 历史回测储蓄模拟 | 数据仅供参考，历史不代表未来 | 运行命令：`streamlit run app.py`")
