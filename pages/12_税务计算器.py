"""税务计算器 — 中国个人所得税与投资收益税

支持：
- 综合所得个人所得税（工资、薪金等）
- 劳务报酬所得预扣预缴
- 资本利得税（股票、基金等）
- 税后实际投资收益率计算
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.benchmarks import benchmark_inline
from core.chart_config import build_layout
from core.currency import fmt, get_symbol
from core.storage import scheme_manager_ui

st.set_page_config(page_title="税务计算器", page_icon="🧾", layout="wide")


st.title("🧾 税务计算器")
st.caption("计算中国个人所得税、劳务报酬所得税及投资收益税后回报，帮助进行税务规划。")

# currency_selector() is already called globally in app.py — do not duplicate
sym = get_symbol()

# 方案管理
scheme_manager_ui("tax", {})

tab1, tab2, tab3 = st.tabs(["💼 工资薪金个税", "📋 劳务报酬预扣税", "📈 投资收益税后分析"])

# ──────────────────────────────────────────────────────────
# TAB 1: 工资薪金个人所得税（综合所得）
# ──────────────────────────────────────────────────────────
with tab1:
    st.subheader("💼 工资薪金个税计算（综合所得）")
    st.caption("基于中国 2019 年起执行的个人所得税法，采用超额累进税率计算。")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 收入来源")
        monthly_salary = st.number_input("月税前工资（元）", min_value=0.0, value=20000.0, step=500.0, format="%.0f", key="tax_salary")
        bonus_annual = st.number_input("年度奖金（元）", min_value=0.0, value=0.0, step=1000.0, format="%.0f", key="tax_bonus")
        other_income = st.number_input("其他综合所得（元/年）", min_value=0.0, value=0.0, step=1000.0, format="%.0f", key="tax_other")

    with col_b:
        st.markdown("#### 专项扣除与减免")
        social_insurance = st.number_input("月五险一金缴纳额（元）", min_value=0.0, value=round(monthly_salary * 0.105, 0), step=100.0, format="%.0f", key="tax_si", help="通常为工资的约 10.5%（养老 8%+医疗 2%+失业 0.5%）")
        deduction_children = st.number_input("子女教育专项（元/月）", min_value=0.0, value=0.0, step=500.0, format="%.0f", key="tax_child", help="每个子女 1000 元/月")
        deduction_housing = st.number_input("住房贷款利息专项（元/月）", min_value=0.0, value=0.0, step=500.0, format="%.0f", key="tax_house", help="首套房贷款利息 1000 元/月")
        deduction_rent = st.number_input("住房租金专项（元/月）", min_value=0.0, value=0.0, step=200.0, format="%.0f", key="tax_rent", help="直辖市/省会 1500 元，其余城市 1100 元")
        deduction_elderly = st.number_input("赡养老人专项（元/月）", min_value=0.0, value=0.0, step=500.0, format="%.0f", key="tax_elderly", help="独生子女 2000 元/月，非独生 1000 元/月")
        deduction_education = st.number_input("继续教育专项（元/月）", min_value=0.0, value=0.0, step=100.0, format="%.0f", key="tax_edu", help="学历教育 400 元/月，职业技能 3600 元/年")

    # 中国个税超额累进税率表（年应纳税所得额）
    TAX_BRACKETS = [
        (36000, 0.03, 0),
        (144000, 0.10, 2520),
        (300000, 0.20, 16920),
        (420000, 0.25, 31920),
        (660000, 0.30, 52920),
        (960000, 0.35, 85920),
        (float("inf"), 0.45, 181920),
    ]

    def calc_income_tax(annual_taxable: float) -> float:
        if annual_taxable <= 0:
            return 0.0
        for limit, rate, deduction in TAX_BRACKETS:
            if annual_taxable <= limit:
                return annual_taxable * rate - deduction
        return annual_taxable * 0.45 - 181920

    BASIC_DEDUCTION = 5000.0

    if deduction_housing > 0 and deduction_rent > 0:
        st.error("❌ **住房贷款利息**与**住房租金**专项扣除互斥，不可同时申报。请将其中一项清零。")

    annual_salary = monthly_salary * 12
    annual_si = social_insurance * 12
    annual_special = (deduction_children + deduction_housing + deduction_rent + deduction_elderly + deduction_education) * 12
    annual_total_income = annual_salary + bonus_annual + other_income
    annual_taxable = max(0.0, annual_total_income - BASIC_DEDUCTION * 12 - annual_si - annual_special)

    annual_tax = calc_income_tax(annual_taxable)
    monthly_tax = annual_tax / 12
    after_tax_annual = annual_total_income - annual_si - annual_tax
    after_tax_monthly = after_tax_annual / 12
    effective_rate = annual_tax / annual_total_income * 100 if annual_total_income > 0 else 0.0
    marginal_rate_info = next((f"{rate*100:.0f}%" for limit, rate, _ in TAX_BRACKETS if annual_taxable <= limit), "45%")

    st.markdown("---")
    st.subheader("📊 税务结果")
    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("年税前总收入", fmt(annual_total_income, decimals=0))
    r2.metric("应纳税所得额", fmt(annual_taxable, decimals=0))
    r3.metric("年度应缴个税", fmt(annual_tax, decimals=0), delta=f"月均 {fmt(monthly_tax, decimals=0)}", delta_color="off")
    r4.metric("实际税率", f"{effective_rate:.2f}%", delta=f"边际税率 {marginal_rate_info}", delta_color="off")
    r5.metric("税后月到手", fmt(after_tax_monthly, decimals=0), delta=f"年税后 {fmt(after_tax_annual, decimals=0)}", delta_color="off")

    st.session_state["dashboard_tax"] = {
        "annual_tax": annual_tax,
        "effective_rate": effective_rate,
        "after_tax_monthly": after_tax_monthly,
        "monthly_income_pretax": monthly_salary,
    }
    benchmark_inline("monthly_income", after_tax_monthly, label="税后月收入")

    yearly_rows = []
    monthly_rows = []
    cumulative_taxable = 0.0
    cumulative_tax = 0.0
    for month in range(1, 13):
        month_income = monthly_salary + (bonus_annual if month == 12 else 0.0)
        month_income += other_income / 12
        cumulative_taxable += max(0.0, month_income - BASIC_DEDUCTION - social_insurance - (deduction_children + deduction_housing + deduction_rent + deduction_elderly + deduction_education))
        month_tax_cumulative = calc_income_tax(cumulative_taxable)
        month_tax = month_tax_cumulative - cumulative_tax
        cumulative_tax = month_tax_cumulative
        monthly_rows.append({
            "月份": f"第{month}月",
            "当月税前收入": fmt(month_income, decimals=0),
            "当月应纳税额": fmt(max(0.0, month_tax), decimals=0),
            "税后到手": fmt(month_income - social_insurance - max(0.0, month_tax), decimals=0),
        })

    with st.expander("📋 逐月税务明细"):
        st.dataframe(pd.DataFrame(monthly_rows), use_container_width=True, hide_index=True)

    fig_tax = go.Figure()
    bracket_labels = ["0-3.6万\n3%", "3.6-14.4万\n10%", "14.4-30万\n20%", "30-42万\n25%", "42-66万\n30%", "66-96万\n35%", ">96万\n45%"]
    bracket_uppers = [36000, 144000, 300000, 420000, 660000, 960000, float("inf")]
    colors = ["#00CC96"] * 7
    active_bracket = next((i for i, (limit, _, _) in enumerate(TAX_BRACKETS) if annual_taxable <= limit), 6)
    colors[active_bracket] = "#EF553B"
    display_uppers = [36000, 108000, 156000, 120000, 240000, 300000, max(0, annual_taxable - 960000)]
    fig_tax.add_trace(go.Bar(
        x=bracket_labels[:active_bracket + 1],
        y=[min(u, max(0, annual_taxable - sum(display_uppers[:i]))) for i, u in enumerate(display_uppers[:active_bracket + 1])],
        marker_color=colors[:active_bracket + 1],
        name="各档应纳税额",
    ))
    fig_tax.update_layout(**build_layout(xaxis_title="税率档次", yaxis_title="该档应税额（元）", yaxis_tickformat=",", showlegend=False, height=300, margin=dict(t=20)))
    st.plotly_chart(fig_tax, use_container_width=True)
    st.caption(f"红色高亮表示当前所在税率档次：**{marginal_rate_info}**")

# ──────────────────────────────────────────────────────────
# TAB 2: 劳务报酬预扣税
# ──────────────────────────────────────────────────────────
with tab2:
    st.subheader("📋 劳务报酬预扣税计算")
    st.caption("劳务报酬所得采用预扣预缴方式，适用于兼职、演讲、稿酬等收入。")

    lw_income = st.number_input("单次劳务报酬收入（元）", min_value=0.0, value=10000.0, step=500.0, format="%.0f", key="lw_income")
    lw_type = st.radio("收入类型", ["劳务报酬", "稿酬（打8折）", "特许权使用费"], horizontal=True, key="lw_type")

    if lw_income <= 4000:
        lw_expense = 800.0
    else:
        lw_expense = lw_income * 0.20

    if lw_type == "稿酬（打8折）":
        lw_taxable = (lw_income - lw_expense) * 0.70
    else:
        lw_taxable = lw_income - lw_expense

    LW_BRACKETS = [
        (20000, 0.20, 0),
        (50000, 0.30, 2000),
        (float("inf"), 0.40, 7000),
    ]

    def calc_lw_tax(taxable: float) -> float:
        if taxable <= 0:
            return 0.0
        for limit, rate, quick_deduction in LW_BRACKETS:
            if taxable <= limit:
                return taxable * rate - quick_deduction
        return taxable * 0.40 - 7000

    lw_tax = calc_lw_tax(lw_taxable)
    lw_after_tax = lw_income - lw_tax
    lw_effective = lw_tax / lw_income * 100 if lw_income > 0 else 0.0

    lw_c1, lw_c2, lw_c3, lw_c4 = st.columns(4)
    lw_c1.metric("税前劳务收入", fmt(lw_income, decimals=0))
    lw_c2.metric("应纳税所得额", fmt(lw_taxable, decimals=0))
    lw_c3.metric("预扣税额", fmt(lw_tax, decimals=0))
    lw_c4.metric("税后实得", fmt(lw_after_tax, decimals=0), delta=f"实际税率 {lw_effective:.1f}%", delta_color="off")

    st.info(
        f"**计算说明**：劳务报酬所得扣除费用（{'800元' if lw_income <= 4000 else '收入的20%'}）后，"
        f"{'再按70%计入应税额（稿酬特别规定）' if lw_type == '稿酬（打8折）' else '直接作为应纳税所得额'}，"
        f"再按三档超额累进税率（20%/30%/40%）预扣税款。"
    )

# ──────────────────────────────────────────────────────────
# TAB 3: 投资收益税后分析
# ──────────────────────────────────────────────────────────
with tab3:
    st.subheader("📈 投资收益税后分析")
    st.caption("计算不同投资类型的税后实际收益率，帮助进行资产配置决策。")

    inv_col1, inv_col2 = st.columns(2)
    with inv_col1:
        inv_principal = st.number_input("投资本金（元）", min_value=1000.0, value=100000.0, step=10000.0, format="%.0f", key="inv_p")
        inv_gross_return = st.number_input("名义年化收益率（%）", min_value=0.0, max_value=100.0, value=8.0, step=0.5, format="%.1f", key="inv_r")
        inv_years = st.slider("持有年限", min_value=1, max_value=30, value=10, key="inv_y")
    with inv_col2:
        inv_type = st.selectbox("投资类型", [
            "A股股票（差价收益免税，分红20%）",
            "公募基金（持有1年以上短期/长期）",
            "债券（利息所得20%）",
            "银行存款（利息20%）",
            "房产出租（租金20%/可减费）",
            "自定义税率",
        ], key="inv_type")
        if inv_type == "自定义税率":
            custom_tax_rate = st.slider("自定义税率（%）", 0, 45, 20, key="inv_custom_rate") / 100
        else:
            custom_tax_rate = 0.0

    tax_rate_map = {
        "A股股票（差价收益免税，分红20%）": 0.0,
        "公募基金（持有1年以上短期/长期）": 0.0,
        "债券（利息所得20%）": 0.20,
        "银行存款（利息20%）": 0.20,
        "房产出租（租金20%/可减费）": 0.20,
        "自定义税率": custom_tax_rate,
    }

    effective_tax_on_return = tax_rate_map.get(inv_type, 0.0)
    after_tax_annual_rate = inv_gross_return / 100 * (1 - effective_tax_on_return)

    gross_final = inv_principal * (1 + inv_gross_return / 100) ** inv_years
    after_tax_final = inv_principal * (1 + after_tax_annual_rate) ** inv_years

    gross_gain = gross_final - inv_principal
    after_tax_gain = after_tax_final - inv_principal
    tax_drag = gross_gain - after_tax_gain
    tax_drag_pct = tax_drag / gross_gain * 100 if gross_gain > 0 else 0.0

    inv_r1, inv_r2, inv_r3, inv_r4 = st.columns(4)
    inv_r1.metric("税前终值", fmt(gross_final, decimals=0), delta=f"收益 {fmt(gross_gain, decimals=0)}", delta_color="off")
    inv_r2.metric("税后终值", fmt(after_tax_final, decimals=0), delta=f"收益 {fmt(after_tax_gain, decimals=0)}", delta_color="off")
    inv_r3.metric("税务拖累", fmt(tax_drag, decimals=0), delta=f"减少收益 {tax_drag_pct:.1f}%", delta_color="inverse")
    inv_r4.metric("税后年化收益率", f"{after_tax_annual_rate * 100:.2f}%", delta=f"税前 {inv_gross_return:.1f}%", delta_color="off")

    years_range = list(range(1, inv_years + 1))
    gross_path = [inv_principal * (1 + inv_gross_return / 100) ** y for y in years_range]
    after_tax_path = [inv_principal * (1 + after_tax_annual_rate) ** y for y in years_range]

    fig_inv = go.Figure()
    fig_inv.add_trace(go.Scatter(
        x=years_range, y=gross_path,
        mode="lines", name="税前资产",
        line=dict(width=2, color="#636EFA"),
        hovertemplate=f"第 %{{x}} 年<br>税前: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_inv.add_trace(go.Scatter(
        x=years_range, y=after_tax_path,
        mode="lines", name="税后资产",
        line=dict(width=2.5, color="#00CC96"),
        hovertemplate=f"第 %{{x}} 年<br>税后: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_inv.add_trace(go.Scatter(
        x=years_range, y=[inv_principal] * len(years_range),
        mode="lines", name="本金",
        line=dict(width=1.5, dash="dot", color="#EF553B"),
    ))
    fig_inv.update_layout(**build_layout(xaxis_title="持有年限", yaxis_title="资产（元）", yaxis_tickformat=","))
    st.plotly_chart(fig_inv, use_container_width=True)

    if effective_tax_on_return > 0:
        st.warning(
            f"税率 {effective_tax_on_return*100:.0f}% 将使 {inv_years} 年后的收益减少 **{fmt(tax_drag, decimals=0)}**（{tax_drag_pct:.1f}%）。"
            f"税后年化实际只有 {after_tax_annual_rate * 100:.2f}%（而非名义的 {inv_gross_return:.1f}%）。"
        )
    else:
        st.success(f"该投资类型（{inv_type.split('（')[0]}）在当前假设下无需缴纳所得税，税前税后收益相同。")

    st.markdown("#### 多税率对比")
    compare_rows = []
    for rate_label, rate in [("0%（免税）", 0.0), ("10%", 0.10), ("20%", 0.20), ("30%", 0.30)]:
        at_rate = inv_gross_return / 100 * (1 - rate)
        at_final = inv_principal * (1 + at_rate) ** inv_years
        compare_rows.append({
            "税率": rate_label,
            "税后年化收益率": f"{at_rate * 100:.2f}%",
            "税后终值": fmt(at_final, decimals=0),
            "税务拖累": fmt(gross_final - at_final, decimals=0),
        })
    st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)

# ── 写入仪表盘状态 ──────────────────────────────────────────
st.session_state["dashboard_tax"] = {
    "annual_tax": annual_tax,
    "effective_rate": effective_rate,
    "after_tax_monthly": after_tax_monthly,
}

# ── 导出报告 ────────────────────────────────────────────
st.subheader("📤 导出报告")
def _build_tax_report() -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#222}}h1{{color:#333}}.summary{{display:flex;gap:20px;margin:16px 0;flex-wrap:wrap}}.summary div{{background:#f9f9f9;padding:12px 20px;border-radius:6px}}.label{{font-size:12px;color:#888}}.value{{font-size:18px;font-weight:bold}}</style></head><body>
<h1>🧾 税务计算报告</h1>
<p>月税前工资：{sym}{monthly_salary:,.0f} | 年度总收入：{sym}{annual_total_income:,.0f}</p>
<div class="summary">
<div><div class="label">年应缴个税</div><div class="value">{sym}{annual_tax:,.0f}</div></div>
<div><div class="label">实际税率</div><div class="value">{effective_rate:.2f}%</div></div>
<div><div class="label">税后月到手</div><div class="value">{sym}{after_tax_monthly:,.0f}</div></div>
</div>
<p style="margin-top:24px;font-size:11px;color:#aaa">由税务计算器自动生成</p></body></html>"""

st.download_button("📥 下载税务报告 (HTML)", data=_build_tax_report(), file_name="税务报告.html", mime="text/html")

st.divider()
st.caption("🧾 税务计算器 | 基于中国现行个税法规，仅供参考，实际税务请以税务机关核定为准。")
