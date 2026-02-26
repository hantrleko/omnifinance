"""贷款计算器 —— 等额本息 / 等额本金

支持月供、季供、年供三种还款频率，Plotly 可视化，CSV 导出。
"""

import io

import pandas as pd

from core.planning import calculate_loan
import plotly.graph_objects as go
import streamlit as st

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="贷款计算器", page_icon="🏦", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .stMetric { background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 8px; padding: 14px; }
</style>
""", unsafe_allow_html=True)

st.title("🏦 贷款计算器")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 贷款参数")

loan_amount = st.sidebar.number_input(
    "贷款金额（元）", min_value=100_000.0, max_value=50_000_000.0,
    value=1_000_000.0, step=10_000.0, format="%.0f",
)
annual_rate = st.sidebar.number_input(
    "年利率（%）", min_value=0.1, max_value=20.0, value=4.5, step=0.1, format="%.2f",
)
loan_years = st.sidebar.number_input(
    "贷款期限（年）", min_value=1, max_value=40, value=30, step=1,
)

repay_method = st.sidebar.radio("还款方式", ["等额本息", "等额本金"], horizontal=True)

freq_map = {"每月": 12, "每季度": 4, "每年": 1}
freq_label = st.sidebar.radio("还款频率", list(freq_map.keys()), horizontal=True)
periods_per_year = freq_map[freq_label]

total_periods = loan_years * periods_per_year
st.sidebar.markdown(f"**总期数：{total_periods} 期** （{loan_years} 年 × {periods_per_year} 期/年 = {loan_years * 12} 个月）")

st.sidebar.divider()
st.sidebar.caption("等额本息：每期还款额固定")
st.sidebar.caption("等额本金：每期本金固定，利息逐期递减")


# ══════════════════════════════════════════════════════════
#  核心计算
# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
#  执行计算
# ══════════════════════════════════════════════════════════

schedule, summary = calculate_loan(loan_amount, annual_rate, loan_years, periods_per_year, repay_method)

# ── 核心指标卡片 ──────────────────────────────────────────
st.markdown("---")
st.subheader("📊 核心指标")

freq_name = freq_label.replace("每", "每期（") + "）"

c1, c2, c3, c4 = st.columns(4)

if repay_method == "等额本息":
    c1.metric(f"每期还款（{freq_label}）", f"¥{summary['首期还款']:,.2f}")
else:
    c1.metric(f"首期还款（{freq_label}）", f"¥{summary['首期还款']:,.2f}",
              delta=f"末期 ¥{summary['末期还款']:,.2f}", delta_color="inverse")

c2.metric("总还款金额", f"¥{summary['总还款']:,.2f}")
c3.metric("总利息支出", f"¥{summary['总利息']:,.2f}")
c4.metric("实际年化利率 (APR)", f"{summary['APR(%)']:.4f}%")

# ── 图表公共配置 ──────────────────────────────────────────
LAYOUT_DARK = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict()),
    margin=dict(t=30, b=40),
    hovermode="x unified",
)

# ── 图表：剩余本金 + 本金/利息堆叠柱状图 ─────────────────
st.subheader("📈 还款趋势")

tab_line, tab_bar = st.tabs(["剩余本金曲线", "本金 vs 利息"])

with tab_line:
    fig_bal = go.Figure()
    fig_bal.add_trace(go.Scatter(
        x=schedule["期数"], y=schedule["剩余本金"],
        mode="lines", name="剩余本金",
        line=dict(width=2.5, color="#636EFA"),
        fill="tozeroy", fillcolor="rgba(99,110,250,0.15)",
        hovertemplate="第 %{x} 期<br>剩余本金: ¥%{y:,.2f}<extra></extra>",
    ))
    fig_bal.update_layout(
        **LAYOUT_DARK,
        xaxis_title="期数",
        yaxis_title="剩余本金（元）",
        yaxis_tickformat=",",
    )
    st.plotly_chart(fig_bal, use_container_width=True)

with tab_bar:
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=schedule["期数"], y=schedule["本金"],
        name="本金", marker_color="#00CC96",
        hovertemplate="第 %{x} 期<br>本金: ¥%{y:,.2f}<extra></extra>",
    ))
    fig_bar.add_trace(go.Bar(
        x=schedule["期数"], y=schedule["利息"],
        name="利息", marker_color="#EF553B",
        hovertemplate="第 %{x} 期<br>利息: ¥%{y:,.2f}<extra></extra>",
    ))
    fig_bar.update_layout(
        **LAYOUT_DARK,
        barmode="stack",
        xaxis_title="期数",
        yaxis_title="金额（元）",
        yaxis_tickformat=",",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── 还款明细表格 ──────────────────────────────────────────
st.subheader("📋 逐期还款明细")

display = schedule.copy()
money_cols = ["每期还款", "本金", "利息", "剩余本金"]
for col in money_cols:
    display[col] = display[col].apply(lambda v: f"¥{v:,.2f}")
display["期数"] = display["期数"].astype(str)

st.dataframe(display, use_container_width=True, hide_index=True, height=420)

# ── 导出 CSV ──────────────────────────────────────────────
csv_buf = io.StringIO()
schedule.to_csv(csv_buf, index=False, encoding="utf-8-sig")
st.download_button(
    "📥 导出还款明细 CSV",
    data=csv_buf.getvalue(),
    file_name="贷款还款明细.csv",
    mime="text/csv",
)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("🏦 贷款计算器 | 运行命令：`streamlit run app.py`")
