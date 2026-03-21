"""退休金需求估算器

双阶段模型：退休前复利累积 → 退休后提领消耗。
通胀调整 + 敏感度分析 + Plotly 可视化。

v1.4: 核心计算已下沉到 core/retirement.py；图表货币符号动态引用。
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import currency_selector, fmt, fmt_delta, get_symbol
from core.export import dataframes_to_excel
from core.retirement import RetirementResult, calculate_retirement
from core.storage import scheme_manager_ui

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="退休金估算器", page_icon="🏖️", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .stMetric { background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 8px; padding: 14px; }
</style>
""", unsafe_allow_html=True)

st.title("🏖️ 退休金需求估算器")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("👤 退休前参数")
currency_selector()

current_age = st.sidebar.number_input("目前年龄", 18, 80, 35)
retire_age = st.sidebar.number_input("预计退休年龄", current_age + 1, 90, max(65, current_age + 1))
current_assets = st.sidebar.number_input(
    "目前已累积退休资产（元）", 0.0, CFG.retirement.current_assets_max, CFG.retirement.current_assets_default, step=CFG.retirement.current_assets_step, format="%.0f",
)
monthly_saving = st.sidebar.number_input(
    "退休前每月可投入（元）", 0.0, CFG.retirement.monthly_saving_max, CFG.retirement.monthly_saving_default, step=CFG.retirement.monthly_saving_step, format="%.0f",
)
pre_return = st.sidebar.number_input(
    "退休前年化报酬率（%）", 0.0, CFG.retirement.pre_return_max, CFG.retirement.pre_return_default, step=CFG.retirement.pre_return_step, format="%.1f",
)

st.sidebar.divider()
st.sidebar.header("🏖️ 退休后参数")

life_expectancy = st.sidebar.number_input("预期寿命", retire_age + 1, 120, max(85, retire_age + 1))
monthly_expense = st.sidebar.number_input(
    "退休后每月生活费（今日币值，元）", CFG.retirement.monthly_expense_min, CFG.retirement.monthly_expense_max, CFG.retirement.monthly_expense_default, step=CFG.retirement.monthly_expense_step, format="%.0f",
)
pension_income = st.sidebar.number_input(
    "预期月养老金收入（元）", 0.0, CFG.retirement.pension_income_max, CFG.retirement.pension_income_default, step=CFG.retirement.pension_income_step, format="%.0f",
    help=MSG.retirement_pension_help,
)
inflation = st.sidebar.number_input(
    "年平均通胀率（%）", 0.0, CFG.retirement.inflation_max, CFG.retirement.inflation_default, step=CFG.retirement.inflation_step, format="%.1f",
)
post_return = st.sidebar.number_input(
    "退休后年化报酬率（%）", 0.0, CFG.retirement.post_return_max, CFG.retirement.post_return_default, step=CFG.retirement.post_return_step, format="%.1f",
)

scheme_manager_ui("retirement", {
    "current_age": current_age,
    "retire_age": retire_age,
    "current_assets": current_assets,
    "monthly_saving": monthly_saving,
    "pre_return": pre_return,
    "life_expectancy": life_expectancy,
    "monthly_expense": monthly_expense,
    "pension_income": pension_income,
    "inflation": inflation,
    "post_return": post_return,
})

# ══════════════════════════════════════════════════════════
#  参数验证
# ══════════════════════════════════════════════════════════

_validation_errors: list[str] = []

if retire_age <= current_age:
    _validation_errors.append(f"❌ 退休年龄（{retire_age}岁）必须大于目前年龄（{current_age}岁）。")

if life_expectancy <= retire_age:
    _validation_errors.append(f"❌ 预期寿命（{life_expectancy}岁）必须大于退休年龄（{retire_age}岁）。")

if monthly_expense <= 0:
    _validation_errors.append("❌ 退休后每月生活费必须大于 0。")

if _validation_errors:
    for _msg in _validation_errors:
        st.sidebar.error(_msg)
    st.error("⚠️ 参数有误，请在左侧修正后再计算。详见各错误提示。")
    st.stop()

# ══════════════════════════════════════════════════════════
#  执行计算
# ══════════════════════════════════════════════════════════

result = calculate_retirement(
    current_age, retire_age, life_expectancy,
    current_assets, monthly_saving, monthly_expense,
    inflation, pre_return, post_return,
)

# ── 养老金调整 ────────────────────────────────────────────
if pension_income > 0:
    _inf = inflation / 100
    future_pension = pension_income * (1 + _inf) ** result.years_to_retire
    _rp = (1 + post_return / 100) / (1 + _inf) - 1
    _rpm = (1 + _rp) ** (1/12) - 1
    _nm = result.years_in_retire * 12
    pension_pv = future_pension * ((1 - (1+_rpm)**(-_nm)) / _rpm) if _rpm > 0 else future_pension * _nm
    result_total_needed = max(0, result.total_needed_at_retire - pension_pv)
    result_gap = result_total_needed - result.projected_at_retire
    if result_gap > 0:
        _rprm = pre_return / 100 / 12; _np = result.years_to_retire * 12
        _fvf = ((1+_rprm)**_np - 1) / _rprm if _rprm > 0 else max(_np, 1)
        result_extra = result_gap / _fvf if _fvf > 0 else result_gap / max(_np, 1)
    else:
        result_extra = 0.0
else:
    future_pension = 0.0; pension_pv = 0.0
    result_total_needed = result.total_needed_at_retire
    result_gap = result.gap
    result_extra = result.extra_monthly_needed

st.session_state["dashboard_retirement"] = {
    "gap": result_gap,
    "extra_monthly": result_extra,
}

sym = get_symbol()


# ── 成功概率估计（三档） ──────────────────────────────────
def success_tag(pre_r: float, post_r: float) -> tuple[str, str]:
    r = calculate_retirement(
        current_age, retire_age, life_expectancy,
        current_assets, monthly_saving, monthly_expense,
        inflation, pre_r, post_r,
    )
    if r.gap <= 0:
        return "✅ 可达成", "off"
    return "❌ 不足", "inverse"


scenarios = {
    "保守": (max(0, pre_return - 2), max(0, post_return - 1)),
    "基准": (pre_return, post_return),
    "积极": (pre_return + 2, post_return + 1),
}

# ── 核心指标 ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 核心结果")

m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "🎯 退休所需总资产",
    fmt(result_total_needed, decimals=0),
    delta=f"退休首年月支出 {fmt(result.future_monthly_expense, decimals=0)}",
    delta_color="off",
)
m2.metric(
    "📈 当前计划可累积",
    fmt(result.projected_at_retire, decimals=0),
    delta=f"{'✅ 已充足' if result_gap <= 0 else f'缺口 {fmt(result_gap, decimals=0)}'}",
    delta_color="normal" if result_gap <= 0 else "inverse",
)
m3.metric(
    "💰 每月还需额外储蓄",
    fmt(result_extra, decimals=0) if result_gap > 0 else f"{fmt(0, decimals=0)}（已充足）",
)

prob_labels = []
for name, (pr, po) in scenarios.items():
    tag, _ = success_tag(pr, po)
    prob_labels.append(f"{name} {tag}")
m4.metric("📋 达成评估", prob_labels[1], delta=" | ".join(prob_labels), delta_color="off")

if pension_income > 0:
    st.info(MSG.retirement_pension_info.format(
        income=fmt(pension_income, decimals=0),
        future=fmt(future_pension, decimals=0),
        pv=fmt(pension_pv, decimals=0),
    ))

st.subheader("🧭 一页结论")
if result_gap <= 0:
    st.success(MSG.retirement_ok_conclusion)
    st.caption(MSG.retirement_ok_reason.format(
        projected=fmt(result.projected_at_retire, decimals=0),
        needed=fmt(result_total_needed, decimals=0),
    ))
    st.caption(MSG.retirement_ok_next)
else:
    st.warning(MSG.retirement_gap_conclusion)
    st.caption(MSG.retirement_gap_reason.format(gap=fmt(result_gap, decimals=0)))
    st.caption(MSG.retirement_gap_next.format(extra=fmt(result_extra, decimals=0)))

# ── 成长曲线 ──────────────────────────────────────────────
st.subheader("📈 资产成长曲线")

tab_acc, tab_full = st.tabs(["退休前累积阶段", "完整生命周期"])

with tab_acc:
    fig_acc = go.Figure()
    fig_acc.add_trace(go.Scatter(
        x=result.accumulation_path["年龄"],
        y=result.accumulation_path["资产"],
        mode="lines+markers", name="当前计划",
        line=dict(width=2.5, color="#636EFA"),
        hovertemplate=f"%{{x}} 岁<br>资产: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_acc.add_trace(go.Scatter(
        x=result.target_path["年龄"],
        y=result.target_path["资产"],
        mode="lines", name="目标路径",
        line=dict(width=2, dash="dash", color="#00CC96"),
        hovertemplate=f"%{{x}} 岁<br>目标: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_acc.add_hline(
        y=result.total_needed_at_retire, line_dash="dot", line_color="#EF553B",
        annotation_text=f"退休所需 {fmt(result.total_needed_at_retire, decimals=0)}",
        annotation_position="top left", annotation_font_color="#EF553B",
    )
    fig_acc.update_layout(
        **build_layout(xaxis_title="年龄", yaxis_title="资产（元）", yaxis_tickformat=","),
    )
    st.plotly_chart(fig_acc, use_container_width=True)

with tab_full:
    fig_full = go.Figure()
    full = result.full_path
    pre_phase = full[full["年龄"] <= retire_age]
    post_phase = full[full["年龄"] >= retire_age]

    fig_full.add_trace(go.Scatter(
        x=pre_phase["年龄"], y=pre_phase["资产"],
        mode="lines", name="累积阶段",
        line=dict(width=2.5, color="#636EFA"),
        hovertemplate=f"%{{x}} 岁<br>资产: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_full.add_trace(go.Scatter(
        x=post_phase["年龄"], y=post_phase["资产"],
        mode="lines", name="提领阶段",
        line=dict(width=2.5, color="#EF553B"),
        hovertemplate=f"%{{x}} 岁<br>资产: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_full.add_vline(
        x=retire_age, line_dash="dot", line_color="#FFD600",
        annotation_text=f"退休 {retire_age} 岁", annotation_font_color="#FFD600",
    )

    depleted = post_phase[post_phase["资产"] <= 0]
    if not depleted.empty:
        deplete_age = depleted.iloc[0]["年龄"]
        fig_full.add_vline(
            x=deplete_age, line_dash="dash", line_color="#ff1744",
            annotation_text=f"⚠️ 资产归零 {int(deplete_age)} 岁",
            annotation_font_color="#ff1744",
        )

    fig_full.update_layout(
        **build_layout(xaxis_title="年龄", yaxis_title="资产（元）", yaxis_tickformat=","),
    )
    st.plotly_chart(fig_full, use_container_width=True)

# ── 敏感度分析 ────────────────────────────────────────────
st.subheader("🔍 敏感度分析")

sens_rows: list[dict] = []
for d_ret in [-1.0, 0.0, 1.0]:
    for d_inf in [-0.5, 0.0, 0.5]:
        r = calculate_retirement(
            current_age, retire_age, life_expectancy,
            current_assets, monthly_saving, monthly_expense,
            inflation + d_inf, pre_return + d_ret, post_return + d_ret * 0.5,
        )
        sens_rows.append({
            "报酬率调整": f"{d_ret:+.1f}%",
            "通胀率调整": f"{d_inf:+.1f}%",
            "退休前报酬": f"{pre_return + d_ret:.1f}%",
            "通胀率": f"{inflation + d_inf:.1f}%",
            "退休所需": fmt(r.total_needed_at_retire, decimals=0),
            "可累积": fmt(r.projected_at_retire, decimals=0),
            "缺口": fmt(r.gap, decimals=0) if r.gap > 0 else "✅ 充足",
            "额外月存": fmt(r.extra_monthly_needed, decimals=0) if r.gap > 0 else fmt(0, decimals=0),
        })

sens_df = pd.DataFrame(sens_rows)
st.dataframe(sens_df, use_container_width=True, hide_index=True)

# ── 逐年明细 ──────────────────────────────────────────────
st.subheader("📋 退休前逐年累积明细")

yearly_rows: list[dict] = []
bal = current_assets
r_m = pre_return / 100 / 12
for yr in range(1, result.years_to_retire + 1):
    start = bal
    yr_interest = 0.0
    for _ in range(12):
        interest = bal * r_m
        yr_interest += interest
        bal = bal + interest + monthly_saving
    yearly_rows.append({
        "年份": f"第 {yr} 年（{current_age + yr} 岁）",
        "年初资产": fmt(start, decimals=0),
        "当年投入": fmt(monthly_saving * 12, decimals=0),
        "当年收益": fmt(yr_interest, decimals=0),
        "年末资产": fmt(bal, decimals=0),
    })

if yearly_rows:
    st.dataframe(pd.DataFrame(yearly_rows), use_container_width=True, hide_index=True, height=400)

# ── 导出报告 ──────────────────────────────────────────────
st.subheader("📤 导出报告")
def _build_ret_report() -> str:
    rh = ""; b = current_assets; rm = pre_return / 100 / 12
    for yr in range(1, result.years_to_retire + 1):
        sb = b; yi = 0.0
        for _ in range(12): i = b * rm; yi += i; b = b + i + monthly_saving
        rh += f"<tr><td>第{yr}年({current_age+yr}岁)</td><td>{sym}{sb:,.0f}</td><td>{sym}{monthly_saving*12:,.0f}</td><td>{sym}{yi:,.0f}</td><td>{sym}{b:,.0f}</td></tr>"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#222}}h1{{color:#333}}table{{border-collapse:collapse;width:100%;margin-top:12px}}th,td{{border:1px solid #ccc;padding:6px 10px;text-align:right;font-size:13px}}th{{background:#f5f5f5}}</style></head><body><h1>🏖️ 退休金估算报告</h1><p>{current_age}岁→退休{retire_age}岁→寿命{life_expectancy} | 月储蓄：{sym}{monthly_saving:,.0f}</p><table><tr><th>年份</th><th>年初</th><th>投入</th><th>收益</th><th>年末</th></tr>{rh}</table></body></html>"""

_dl_col1, _dl_col2 = st.columns(2)
_dl_col1.download_button("📥 下载报告 (HTML)", data=_build_ret_report(), file_name="退休金报告.html", mime="text/html")

if yearly_rows:
    _yearly_df_export = pd.DataFrame(yearly_rows)
    _sens_df_export = sens_df.copy()
    _xlsx_bytes = dataframes_to_excel(
        sheets=[("逐年累积明细", _yearly_df_export), ("敏感度分析", _sens_df_export)],
        title="退休金估算报告",
    )
    _dl_col2.download_button(
        "📊 下载数据 (Excel)",
        data=_xlsx_bytes,
        file_name="退休金报告.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.caption(MSG.print_hint)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption(MSG.retirement_footer)
