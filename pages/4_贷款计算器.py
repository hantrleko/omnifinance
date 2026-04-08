"""贷款计算器 —— 等额本息 / 等额本金

支持月供、季供、年供三种还款频率，Plotly 可视化，CSV 导出。
"""

import io

import pandas as pd

from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import currency_selector, fmt, fmt_delta
from core.planning import calculate_loan
from core.storage import scheme_manager_ui
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

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
pass

loan_amount = st.sidebar.number_input(
    "贷款金额（元）",
    min_value=CFG.loan.amount_min,
    max_value=CFG.loan.amount_max,
    value=CFG.loan.amount_default,
    step=CFG.loan.amount_step,
    format="%.0f",
)
annual_rate = st.sidebar.number_input(
    "年利率（%）",
    min_value=CFG.loan.rate_min,
    max_value=CFG.loan.rate_max,
    value=CFG.loan.rate_default,
    step=CFG.loan.rate_step,
    format="%.2f",
)
loan_years = st.sidebar.number_input(
    "贷款期限（年）",
    min_value=CFG.loan.years_min,
    max_value=CFG.loan.years_max,
    value=CFG.loan.years_default,
    step=1,
)

repay_method = st.sidebar.radio("还款方式", ["等额本息", "等额本金"], horizontal=True)

freq_map = {"每月": 12, "每季度": 4, "每年": 1}
freq_label = st.sidebar.radio("还款频率", list(freq_map.keys()), horizontal=True)
periods_per_year = freq_map[freq_label]

total_periods = loan_years * periods_per_year
st.sidebar.markdown(f"**总期数：{total_periods} 期** （{loan_years} 年 × {periods_per_year} 期/年 = {loan_years * 12} 个月）")

st.sidebar.divider()
st.sidebar.caption("等额本息：每期还款额固定")

scheme_manager_ui("loan", {
    "loan_amount": loan_amount,
    "annual_rate": annual_rate,
    "loan_years": loan_years,
    "repay_method": repay_method,
    "freq_label": freq_label,
})

st.sidebar.divider()
st.sidebar.subheader("💸 提前还款模拟")
enable_prepay = st.sidebar.checkbox("启用提前还款", value=False)
prepay_period = None
prepay_amount = 0.0
if enable_prepay:
    prepay_period = st.sidebar.number_input("提前还款发生期数", min_value=1, max_value=total_periods, value=min(CFG.loan.prepay_period_default, total_periods), step=1)
    prepay_amount = st.sidebar.number_input("提前还款金额（元）", min_value=0.0, max_value=loan_amount, value=min(CFG.loan.prepay_default, loan_amount), step=CFG.loan.prepay_step, format="%.0f")


# ══════════════════════════════════════════════════════════
#  核心计算
# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
#  执行计算
# ══════════════════════════════════════════════════════════

schedule, summary = calculate_loan(
    loan_amount, annual_rate, loan_years, periods_per_year, repay_method,
    int(prepay_period) if prepay_period is not None else None, prepay_amount,
)
base_schedule, base_summary = calculate_loan(loan_amount, annual_rate, loan_years, periods_per_year, repay_method)

st.session_state["dashboard_loan"] = {
    "total_interest": summary["总利息"],
    "monthly_payment": summary["首期还款"],
}

# ── 核心指标卡片 ──────────────────────────────────────────
st.markdown("---")
st.subheader("📊 核心指标")

freq_name = freq_label.replace("每", "每期（") + "）"

c1, c2, c3, c4, c5 = st.columns(5)

if repay_method == "等额本息":
    c1.metric(f"每期还款（{freq_label}）", fmt(summary['首期还款']))
else:
    c1.metric(f"首期还款（{freq_label}）", fmt(summary['首期还款']),
              delta=f"末期 {fmt(summary['末期还款'])}", delta_color="inverse")

c2.metric("总还款金额", fmt(summary['总还款']))
c3.metric("总利息支出", fmt(summary['总利息']))
c4.metric("实际年化利率 (APR)", f"{summary['APR(%)']:.4f}%")
interest_saved = max(0.0, base_summary["总利息"] - summary["总利息"])
periods_saved = max(0, base_summary["实际期数"] - summary["实际期数"])
c5.metric("提前还款节省", fmt(interest_saved), delta=f"少 {periods_saved} 期")

if enable_prepay and prepay_amount > 0:
    st.info(MSG.loan_prepay_info.format(
        period=int(prepay_period),
        amount=fmt(prepay_amount, decimals=0),
        saved=fmt(interest_saved),
        periods=periods_saved,
    ))


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
        **build_layout(xaxis_title="期数", yaxis_title="剩余本金（元）", yaxis_tickformat=","),
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
        **build_layout(barmode="stack", xaxis_title="期数", yaxis_title="金额（元）", yaxis_tickformat=","),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── 还款明细表格 ──────────────────────────────────────────
st.subheader("📋 逐期还款明细")

display = schedule.copy()
money_cols = ["每期还款", "本金", "利息", "提前还款", "剩余本金"]
for col in money_cols:
    display[col] = display[col].apply(lambda v: fmt(v))
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

# ── 贷款方案对比 ──────────────────────────────────────────
st.subheader("🔀 贷款方案对比")
with st.expander("📊 设置对比方案", expanded=False):
    st.caption(MSG.loan_compare_caption)
    cb1, cb2, cb3 = st.columns(3)
    cmp_amount = cb1.number_input("方案B 贷款金额", min_value=CFG.loan.amount_min, max_value=CFG.loan.amount_max, value=loan_amount, step=CFG.loan.amount_step, format="%.0f", key="cmp_a")
    cmp_rate = cb2.number_input("方案B 年利率(%)", min_value=CFG.loan.rate_min, max_value=CFG.loan.rate_max, value=annual_rate, step=CFG.loan.rate_step, format="%.2f", key="cmp_r")
    cmp_years = cb3.number_input("方案B 期限(年)", min_value=CFG.loan.years_min, max_value=CFG.loan.years_max, value=loan_years, step=1, key="cmp_y")
    cmp_method = st.radio("方案B 还款方式", ["等额本息", "等额本金"], horizontal=True, key="cmp_m")
    if st.button("📊 开始对比", key="cmp_run"):
        cmp_schedule, cmp_summary = calculate_loan(cmp_amount, cmp_rate, cmp_years, periods_per_year, cmp_method)
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**方案 A（当前）**")
            st.metric("总利息", fmt(summary['总利息']))
            st.metric("首期还款", fmt(summary['首期还款']))
        with cc2:
            st.markdown("**方案 B（对比）**")
            st.metric("总利息", fmt(cmp_summary['总利息']), delta=fmt_delta(cmp_summary['总利息'] - summary['总利息']), delta_color="inverse")
            st.metric("首期还款", fmt(cmp_summary['首期还款']), delta=fmt_delta(cmp_summary['首期还款'] - summary['首期还款']), delta_color="inverse")
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatter(x=schedule["期数"], y=schedule["剩余本金"], mode="lines", name="方案A", line=dict(width=2.5, color="#636EFA")))
        fig_cmp.add_trace(go.Scatter(x=cmp_schedule["期数"], y=cmp_schedule["剩余本金"], mode="lines", name="方案B", line=dict(width=2.5, color="#EF553B")))
        fig_cmp.update_layout(**build_layout(xaxis_title="期数", yaxis_title="剩余本金", yaxis_tickformat=","))
        st.plotly_chart(fig_cmp, use_container_width=True)

# ── 导出报告 ──────────────────────────────────────────────
st.subheader("📤 导出报告")
def _build_loan_report() -> str:
    from core.currency import get_symbol
    s = get_symbol()
    rh = ""
    for _, r in schedule.iterrows():
        rh += f"<tr><td>{int(r['期数'])}</td><td>{s}{r['每期还款']:,.2f}</td><td>{s}{r['本金']:,.2f}</td><td>{s}{r['利息']:,.2f}</td><td>{s}{r['剩余本金']:,.2f}</td></tr>"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#222}}h1{{color:#333}}table{{border-collapse:collapse;width:100%;margin-top:12px}}th,td{{border:1px solid #ccc;padding:6px 10px;text-align:right;font-size:13px}}th{{background:#f5f5f5}}.summary{{display:flex;gap:20px;margin:16px 0;flex-wrap:wrap}}.summary div{{background:#f9f9f9;padding:12px 20px;border-radius:6px}}.label{{font-size:12px;color:#888}}.value{{font-size:18px;font-weight:bold}}</style></head><body>
<h1>🏦 贷款计算报告</h1><p>金额：{s}{loan_amount:,.0f} | 利率：{annual_rate:.2f}% | 期限：{loan_years}年 | 方式：{repay_method}</p>
<div class="summary"><div><div class="label">每期还款</div><div class="value">{s}{summary['首期还款']:,.2f}</div></div><div><div class="label">总利息</div><div class="value">{s}{summary['总利息']:,.2f}</div></div><div><div class="label">APR</div><div class="value">{summary['APR(%)']:.4f}%</div></div></div>
<h2>还款明细</h2><table><tr><th>期数</th><th>每期还款</th><th>本金</th><th>利息</th><th>剩余本金</th></tr>{rh}</table>
<p style="margin-top:24px;font-size:11px;color:#aaa">由贷款计算器自动生成</p></body></html>"""

st.download_button("📥 下载报告 (HTML)", data=_build_loan_report(), file_name="贷款报告.html", mime="text/html")
st.caption(MSG.print_hint)

# ── 再融资（转贷）模拟器 ──────────────────────────────────
st.markdown("---")
st.subheader("🔄 再融资（转贷）模拟器")
st.caption("模拟在当前贷款进行到某一期后，降低利率或延长/缩短期限的转贷收益分析。")

with st.expander("⚙️ 设置转贷条件", expanded=False):
    rf_col1, rf_col2, rf_col3 = st.columns(3)
    _max_rf_period = max(1, int(summary["实际期数"]) - 1)
    rf_period = rf_col1.number_input(
        "转贷发生在第几期",
        min_value=1,
        max_value=_max_rf_period,
        value=min(24, _max_rf_period),
        step=1,
        key="rf_period",
        help="转贷前已还的期数",
    )
    rf_new_rate = rf_col2.number_input(
        "转贷后新年利率（%）",
        min_value=0.01,
        max_value=CFG.loan.rate_max,
        value=max(0.01, annual_rate - 1.0),
        step=CFG.loan.rate_step,
        format="%.2f",
        key="rf_rate",
    )
    rf_new_years = rf_col3.number_input(
        "转贷后剩余年限（年）",
        min_value=1,
        max_value=CFG.loan.years_max,
        value=max(1, loan_years - int(rf_period) // periods_per_year),
        step=1,
        key="rf_years",
    )
    rf_cost = st.number_input(
        "转贷手续费（元）",
        min_value=0.0,
        value=round(loan_amount * 0.005 / 100) * 100,
        step=500.0,
        format="%.0f",
        key="rf_cost",
        help="转贷通常产生评估费、律师费等，一般为贷款余额的 0.3%–1%",
    )

    _rf_period_int = int(rf_period)
    _period_row = schedule[schedule["期数"] == _rf_period_int]
    if not _period_row.empty:
        rf_remaining = float(_period_row["剩余本金"].values[0])
        _orig_remaining_periods = max(1, int(summary["实际期数"]) - _rf_period_int)
        _orig_remaining_years = max(1, _orig_remaining_periods // periods_per_year)

        original_remaining_schedule, original_remaining_summary = calculate_loan(
            rf_remaining, annual_rate,
            _orig_remaining_years,
            periods_per_year, repay_method,
        )
        new_schedule_rf, new_summary_rf = calculate_loan(
            rf_remaining, rf_new_rate, int(rf_new_years), periods_per_year, repay_method,
        )

        original_interest_remaining = original_remaining_summary["总利息"]
        new_total_cost = new_summary_rf["总利息"] + rf_cost
        savings_rf = original_interest_remaining - new_total_cost

        monthly_saving_rf = original_remaining_summary["首期还款"] - new_summary_rf["首期还款"]
        break_even_periods = int(rf_cost / monthly_saving_rf) + 1 if monthly_saving_rf > 0 else 0

        rf_c1, rf_c2, rf_c3, rf_c4 = st.columns(4)
        rf_c1.metric("转贷时剩余本金", fmt(rf_remaining, decimals=0))
        rf_c2.metric(
            "转贷后利息节省",
            fmt(max(0, savings_rf), decimals=0),
            delta="扣除手续费后净节省" if savings_rf > 0 else "转贷不划算",
            delta_color="normal" if savings_rf > 0 else "inverse",
        )
        rf_c3.metric(
            "转贷后每期还款",
            fmt(new_summary_rf["首期还款"], decimals=0),
            delta=fmt(new_summary_rf["首期还款"] - original_remaining_summary["首期还款"], decimals=0),
            delta_color="inverse" if new_summary_rf["首期还款"] > original_remaining_summary["首期还款"] else "normal",
        )
        rf_c4.metric(
            "手续费回本期数",
            f"{break_even_periods} 期" if break_even_periods > 0 else "立即回本",
            delta=f"约 {break_even_periods // periods_per_year} 年" if break_even_periods > periods_per_year else "",
            delta_color="off",
        )

        if savings_rf > 0:
            st.success(f"转贷划算：综合手续费后净节省利息 {fmt(savings_rf, decimals=0)}，新利率 {rf_new_rate:.2f}% 低于原利率 {annual_rate:.2f}%。")
        else:
            st.warning(f"转贷不划算：手续费 {fmt(rf_cost, decimals=0)} 超过节省的利息 {fmt(max(0, original_interest_remaining - new_summary_rf['总利息']), decimals=0)}，建议等待利率下降幅度更大时再转贷。")

        fig_rf = go.Figure()
        fig_rf.add_trace(go.Scatter(
            x=original_remaining_schedule["期数"],
            y=original_remaining_schedule["剩余本金"],
            mode="lines", name=f"原贷款继续（{annual_rate:.2f}%）",
            line=dict(width=2, color="#EF553B"),
        ))
        fig_rf.add_trace(go.Scatter(
            x=new_schedule_rf["期数"],
            y=new_schedule_rf["剩余本金"],
            mode="lines", name=f"转贷后（{rf_new_rate:.2f}%，{int(rf_new_years)}年）",
            line=dict(width=2, color="#00CC96"),
        ))
        from core.chart_config import build_layout as _bl
        fig_rf.update_layout(**_bl(xaxis_title="剩余期数", yaxis_title="剩余本金（元）", yaxis_tickformat=","))
        st.plotly_chart(fig_rf, use_container_width=True)
    else:
        st.warning("所选转贷期数超出还款明细范围，请调整参数。")

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption(MSG.loan_footer)
