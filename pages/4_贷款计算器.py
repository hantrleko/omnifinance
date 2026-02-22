"""贷款计算器 —— 等额本息 / 等额本金

支持月供、季供、年供三种还款频率，Plotly 可视化，CSV 导出。
"""

import io

import numpy as np
import pandas as pd
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

def calculate_loan(
    principal: float,
    annual_rate_pct: float,
    years: int,
    periods_per_year: int,
    method: str,
) -> tuple[pd.DataFrame, dict]:
    """计算还款明细。

    Returns
    -------
    schedule : 逐期还款 DataFrame
    summary  : 汇总指标 dict
    """
    n = years * periods_per_year  # 总期数
    r_period = (annual_rate_pct / 100.0) / periods_per_year  # 每期利率

    rows: list[dict] = []
    balance = principal

    if method == "等额本息":
        if r_period == 0:
            payment = principal / n
        else:
            payment = principal * r_period * (1 + r_period) ** n / ((1 + r_period) ** n - 1)

        for i in range(1, n + 1):
            interest = balance * r_period
            principal_part = payment - interest
            # 最后一期修正浮点误差
            if i == n:
                principal_part = balance
                payment = principal_part + interest
            balance -= principal_part
            if balance < 0:
                balance = 0.0

            rows.append({
                "期数": i,
                "每期还款": payment,
                "本金": principal_part,
                "利息": interest,
                "剩余本金": balance,
            })

    else:  # 等额本金
        principal_fixed = principal / n

        for i in range(1, n + 1):
            interest = balance * r_period
            pmt = principal_fixed + interest
            # 最后一期修正
            if i == n:
                principal_fixed = balance
                pmt = principal_fixed + interest
            balance -= principal_fixed
            if balance < 0:
                balance = 0.0

            rows.append({
                "期数": i,
                "每期还款": pmt,
                "本金": principal_fixed,
                "利息": interest,
                "剩余本金": balance,
            })

    df = pd.DataFrame(rows)

    total_payment = df["每期还款"].sum()
    total_interest = df["利息"].sum()

    # 实际年化利率 (APR)：基于现金流的 IRR × periods_per_year
    cash_flows = [-principal] + df["每期还款"].tolist()
    try:
        irr = np.irr(cash_flows) if hasattr(np, "irr") else np.nan
    except Exception:
        irr = np.nan
    if np.isnan(irr):
        # 手动牛顿法求 IRR
        irr = _solve_irr(cash_flows)
    apr = irr * periods_per_year * 100 if not np.isnan(irr) else annual_rate_pct

    # 首期与末期还款额（等额本金时不同）
    first_payment = df["每期还款"].iloc[0]
    last_payment = df["每期还款"].iloc[-1]

    summary = {
        "首期还款": first_payment,
        "末期还款": last_payment,
        "总还款": total_payment,
        "总利息": total_interest,
        "APR(%)": apr,
    }
    return df, summary


def _solve_irr(cash_flows: list[float], tol: float = 1e-10, max_iter: int = 1000) -> float:
    """牛顿法求解 IRR。"""
    rate = 0.005  # 初始猜测
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if abs(dnpv) < 1e-14:
            break
        rate_new = rate - npv / dnpv
        if abs(rate_new - rate) < tol:
            return rate_new
        rate = rate_new
    return rate


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
