import datetime as _dt

import plotly.graph_objects as go
import streamlit as st

from core.benchmarks import BENCHMARKS
from core.chart_config import build_layout
from core.currency import fmt, get_symbol
from core.pdf_report import generate_pdf_report, is_pdf_available
from core.persistence import export_all_data, import_all_data, restore_session_data, save_session_data
from core.reminders import add_reminder, complete_reminder, get_due_reminders, get_reminders
from core.report_generator import generate_html_report
from core.version import VERSION

st.title(f"🌟 全能理财家 (OmniFinance) `{VERSION}`")
st.caption("✨ **Empower Your Knowledge, Enrich Your Life** | Eugene Finance 荣誉出品")

# ── 快速导航卡片 ──────────────────────────────────────────
st.markdown("""
<style>
.nav-grid { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0 24px 0; }
.nav-card {
    flex: 1 1 180px;
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,0.15);
    border-radius: 12px;
    padding: 16px 18px;
    cursor: pointer;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    text-decoration: none;
}
.nav-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(0,120,255,0.12);
    border-color: rgba(0,120,255,0.35);
}
.nav-card-icon { font-size: 28px; margin-bottom: 6px; }
.nav-card-title { font-size: 14px; font-weight: 600; margin-bottom: 3px; }
.nav-card-desc { font-size: 12px; opacity: 0.65; line-height: 1.4; }
</style>
<div class="nav-grid">
  <div class="nav-card"><div class="nav-card-icon">💰</div><div class="nav-card-title">基础理财管理</div><div class="nav-card-desc">复利 · 储蓄目标 · 预算 · 教育金</div></div>
  <div class="nav-card"><div class="nav-card-icon">⚖️</div><div class="nav-card-title">资产与债务管理</div><div class="nav-card-desc">净值追踪 · 贷款 · 保险 · 债务规划</div></div>
  <div class="nav-card"><div class="nav-card-icon">📈</div><div class="nav-card-title">投资分析引擎</div><div class="nav-card-desc">实时报价 · 组合优化 · 回测 · 外汇</div></div>
  <div class="nav-card"><div class="nav-card-icon">🏖️</div><div class="nav-card-title">高级人生规划</div><div class="nav-card-desc">退休估算 · 蒙特卡洛 · 税务提款</div></div>
  <div class="nav-card"><div class="nav-card-icon">🔬</div><div class="nav-card-title">分析与工具</div><div class="nav-card-desc">场景对比 · 财务日历 · 税务计算</div></div>
  <div class="nav-card"><div class="nav-card-icon">🆕</div><div class="nav-card-title">高级工具 v2.0</div><div class="nav-card-desc">股票筛选器 · 收支记账本</div></div>
</div>
""", unsafe_allow_html=True)

st.caption("👈 从左侧边栏选择工具，或使用搜索框快速定位")

with st.expander("📋 版本历史", expanded=False):
    st.markdown("""
### v2.0.0 — 全平台深度升级
🎨 深色模式持久化 · 全局搜索 · 新增 4 种货币（AUD/CAD/SGD/KRW）
💡 贷款还款方式对比 · 税务大病/养老金扣除 · 10 大外汇对 · 社保养老金估算 · Black-Litterman 组合优化 · 蒙卡进度条（10,000 次）
🆕 股票筛选器（美/A/港/自定义市场）· 收支记账本（预算联动）

### v1.9.9 — UI 系统升级 + 三大新工具
全局 CSS 统一注入 · 科学计算器 · 货币转换器 · 财务日记 · 实时汇率引擎 · 债务 Gantt 图 · 自定义股票分组预设

### v1.9.8 — 探索式深度改进
个人财务档案系统 · 财务提醒管理器 · 全国均值基准对比 · 税务互斥逻辑修复 · 场景对比扩展至 4 维度

### v1.9.7 — 8 大核心增强
财务健康多维评分 · 现金流时间轴 · 年度财务回顾 · 净资产计划 vs 实际 · 货币偏好持久化

### v1.9.6.x — 全面优化与工程加固
图表货币符号修复 · 复利精确计算 · IRR 收敛保护 · joblib 并行回测 · A 股代码校验升级

### v1.9.5 — 十二项功能上线
复利通胀曲线 · 多目标储蓄 · 退休提款策略对比 · 转贷模拟 · 权重约束 · 基准 Alpha · t 分布 · 保险退保分析

### v1.9.0 及更早
v1.9.0: 企业级 HTML 诊断报告 · v1.8: Glassmorphism 主题 · v1.7: 蒙卡+组合优化 · v1.6: 并发架构 · v1.5: 净资产追踪 · v1.1–v1.4: 多货币/技术指标/引擎迭代
""")

# ── Session persistence: restore data on load ─────────────
restored = restore_session_data()

# ── 个人财务仪表盘 ────────────────────────────────────────
st.markdown("---")
st.subheader("📊 个人财务仪表盘")

sym = get_symbol()

dash_compound = st.session_state.get("dashboard_compound")
dash_loan = st.session_state.get("dashboard_loan")
dash_savings = st.session_state.get("dashboard_savings")
dash_budget = st.session_state.get("dashboard_budget")
dash_retirement = st.session_state.get("dashboard_retirement")
dash_insurance = st.session_state.get("dashboard_insurance")
dash_networth = st.session_state.get("dashboard_networth")
dash_tax = st.session_state.get("dashboard_tax")

has_data = any([dash_compound, dash_loan, dash_savings, dash_budget, dash_retirement, dash_insurance, dash_networth, dash_tax])

if has_data:
    # Collect active metrics into a flat list, then display in 3-column grid
    _dash_metrics: list[tuple[str, str, str]] = []

    if dash_compound:
        _dash_metrics.append(("💰 复利终值", fmt(dash_compound['final_balance'], decimals=0), f"累计收益 {fmt(dash_compound['total_interest'], decimals=0)}"))
    if dash_loan:
        _dash_metrics.append(("🏦 贷款总利息", fmt(dash_loan['total_interest'], decimals=0), f"每期还款 {fmt(dash_loan['monthly_payment'], decimals=0)}"))
    if dash_savings:
        _months = dash_savings["months_needed"]
        _y, _m = _months // 12, _months % 12
        _dash_metrics.append(("🎯 储蓄达成", f"{_y}年{_m}个月", f"复利贡献 {fmt(dash_savings['total_interest'], decimals=0)}"))
    if dash_budget:
        _dash_metrics.append(("💡 月储蓄额", fmt(dash_budget['amt_save'], decimals=0), f"储蓄率 {dash_budget['pct_save']}%"))
    if dash_retirement:
        _gap = dash_retirement["gap"]
        if _gap <= 0:
            _dash_metrics.append(("🏖️ 退休评估", "✅ 已充足", "退休资金充裕"))
        else:
            _dash_metrics.append(("🏖️ 退休缺口", fmt(_gap, decimals=0), f"需额外月存 {fmt(dash_retirement['extra_monthly'], decimals=0)}"))
    if dash_insurance:
        _dash_metrics.append(("🛡️ 保险总保费", fmt(dash_insurance['total_premium'], decimals=0), f"保单 IRR {dash_insurance['irr_pct']:.2f}%"))
    if dash_networth:
        _dash_metrics.append(("🏠 净资产", fmt(dash_networth['net_worth'], decimals=0), f"总资产 {fmt(dash_networth['total_assets'], decimals=0)}"))
    if dash_tax:
        _dash_metrics.append(("🧾 年应缴个税", fmt(dash_tax['annual_tax'], decimals=0), f"实际税率 {dash_tax['effective_rate']:.2f}%"))
        _dash_metrics.append(("🧾 税后月到手", fmt(dash_tax['after_tax_monthly'], decimals=0), "税后实际到手"))

    _n_cols = 3
    for _row_start in range(0, len(_dash_metrics), _n_cols):
        _row = _dash_metrics[_row_start: _row_start + _n_cols]
        _cols = st.columns(_n_cols)
        for _ci, (label, value, caption) in enumerate(_row):
            _cols[_ci].metric(label, value)
            _cols[_ci].caption(caption)

    st.caption("💡 提示：使用各工具后，仪表盘数据会自动更新。")

    # ── Multi-Dimensional Health Score (#1) ───────────────
    st.markdown("---")
    st.subheader("🏥 财务健康多维评分")

    dim_scores: list[tuple[str, int, str, str]] = []

    # Savings rate dimension
    if dash_budget:
        save_pct = dash_budget.get("pct_save", 0)
        if save_pct >= 30:
            s, tip, grade = 100, f"储蓄率 {save_pct}%，远超全国均值，表现卓越", "🟢"
        elif save_pct >= 20:
            s, tip, grade = 75, f"储蓄率 {save_pct}%，处于健康水平", "🟡"
        elif save_pct >= 10:
            s, tip, grade = 50, f"储蓄率 {save_pct}%，建议提升至 20% 以上", "🟠"
        else:
            s, tip, grade = 20, f"储蓄率 {save_pct}%，偏低，需要大幅改善", "🔴"
        dim_scores.append(("💡 储蓄能力", s, tip, grade))

    # Retirement readiness dimension
    if dash_retirement:
        gap = dash_retirement.get("gap", 0)
        extra = dash_retirement.get("extra_monthly", 0)
        if gap <= 0:
            s, tip, grade = 100, "退休资金已充足，无需额外储蓄", "🟢"
        elif extra < 2000:
            s, tip, grade = 70, f"退休缺口可控，每月仅需额外补充 {fmt(extra, decimals=0)}", "🟡"
        elif extra < 5000:
            s, tip, grade = 45, f"退休缺口较大，需每月额外储蓄 {fmt(extra, decimals=0)}", "🟠"
        else:
            s, tip, grade = 20, f"退休缺口严峻，需每月额外储蓄 {fmt(extra, decimals=0)}，请尽早行动", "🔴"
        dim_scores.append(("🏖️ 退休准备度", s, tip, grade))

    # Debt level dimension
    if dash_networth:
        total_assets_nw = dash_networth.get("total_assets", 0)
        total_liab_nw = total_assets_nw - dash_networth.get("net_worth", 0)
        dr = (total_liab_nw / total_assets_nw * 100) if total_assets_nw > 0 else 0
        if dr <= 20:
            s, tip, grade = 100, f"负债率 {dr:.1f}%，资产结构健康", "🟢"
        elif dr <= 40:
            s, tip, grade = 75, f"负债率 {dr:.1f}%，处于合理区间", "🟡"
        elif dr <= 60:
            s, tip, grade = 45, f"负债率 {dr:.1f}%，偏高，建议加速还款", "🟠"
        else:
            s, tip, grade = 15, f"负债率 {dr:.1f}%，过高，存在较大财务风险", "🔴"
        dim_scores.append(("💳 负债水平", s, tip, grade))

    # Net worth dimension
    if dash_networth:
        nw = dash_networth.get("net_worth", 0)
        if nw > 1000000:
            s, tip, grade = 100, f"净资产 {fmt(nw, decimals=0)}，资产积累丰厚", "🟢"
        elif nw > 200000:
            s, tip, grade = 70, f"净资产 {fmt(nw, decimals=0)}，处于正常成长阶段", "🟡"
        elif nw > 0:
            s, tip, grade = 50, f"净资产 {fmt(nw, decimals=0)}，尚在起步阶段，持续积累", "🟠"
        else:
            s, tip, grade = 10, f"净资产为负（{fmt(nw, decimals=0)}），需优先降低负债", "🔴"
        dim_scores.append(("🏠 净资产水平", s, tip, grade))

    # Tax efficiency dimension
    if dash_tax:
        eff_rate = dash_tax.get("effective_rate", 0)
        if eff_rate <= 5:
            s, tip, grade = 100, f"实际税率 {eff_rate:.1f}%，税务负担轻", "🟢"
        elif eff_rate <= 15:
            s, tip, grade = 75, f"实际税率 {eff_rate:.1f}%，属正常水平", "🟡"
        elif eff_rate <= 25:
            s, tip, grade = 50, f"实际税率 {eff_rate:.1f}%，可考虑税务优化策略", "🟠"
        else:
            s, tip, grade = 30, f"实际税率 {eff_rate:.1f}%，建议使用税务优化工具", "🔴"
        dim_scores.append(("🧾 税务效率", s, tip, grade))

    # Insurance dimension
    if dash_insurance:
        irr = dash_insurance.get("irr_pct", 0)
        if irr >= 4:
            s, tip, grade = 100, f"保险 IRR {irr:.2f}%，保单回报优质", "🟢"
        elif irr >= 2.5:
            s, tip, grade = 65, f"保险 IRR {irr:.2f}%，收益一般，关注保障覆盖", "🟡"
        else:
            s, tip, grade = 35, f"保险 IRR 仅 {irr:.2f}%，建议评估保单性价比", "🟠"
        dim_scores.append(("🛡️ 保险效益", s, tip, grade))

    if dim_scores:
        overall_score = int(sum(s for _, s, _, _ in dim_scores) / len(dim_scores))
        overall_grade = "🟢 优秀" if overall_score >= 80 else ("🟡 良好" if overall_score >= 60 else ("🟠 一般" if overall_score >= 40 else "🔴 需改善"))

        st.metric("💯 综合财务健康评分", f"{overall_score}/100", delta=overall_grade)

        _n_dim_cols = min(3, len(dim_scores))
        dim_cols = st.columns(_n_dim_cols)
        for idx, (name, score_v, tip, grade) in enumerate(dim_scores):
            with dim_cols[idx % _n_dim_cols]:
                st.metric(name, f"{score_v}/100", delta=grade)
                st.caption(tip)

        improvement_tips = [tip for _, score_v, tip, _ in dim_scores if score_v < 70]
        if improvement_tips:
            with st.expander("📋 改善建议详情"):
                for tip in improvement_tips:
                    st.markdown(f"- {tip}")
    else:
        st.caption("使用更多工具后，这里将展示各维度的精细评分与改善建议。")

    # ── Goal-Based Allocation (#6) ────────────────────────
    st.markdown("---")
    st.subheader("🎯 目标导向资金分配建议")

    goals_exist = False
    allocation_suggestions = []
    total_monthly_available = 0.0

    if dash_budget:
        total_monthly_available = dash_budget.get("amt_save", 0)

    if total_monthly_available > 0:
        if dash_retirement and dash_retirement.get("gap", 0) > 0:
            extra = dash_retirement.get("extra_monthly", 0)
            ratio = min(0.5, extra / total_monthly_available) if total_monthly_available > 0 else 0.3
            allocation_suggestions.append(("🏖️ 退休缺口补充", ratio, extra))
            goals_exist = True

        if dash_savings and dash_savings.get("months_needed", 0) > 0:
            # Allocate 30% or remaining
            remaining = 1.0 - sum(a[1] for a in allocation_suggestions)
            ratio = min(0.3, remaining)
            allocation_suggestions.append(("🎯 储蓄目标", ratio, total_monthly_available * ratio))
            goals_exist = True

        if dash_loan:
            remaining = 1.0 - sum(a[1] for a in allocation_suggestions)
            ratio = min(0.2, remaining)
            allocation_suggestions.append(("🏦 加速还贷", ratio, total_monthly_available * ratio))
            goals_exist = True

        # Allocate remainder
        used_ratio = sum(a[1] for a in allocation_suggestions)
        if used_ratio < 1.0:
            remaining_ratio = 1.0 - used_ratio
            allocation_suggestions.append(("💰 投资增值", remaining_ratio, total_monthly_available * remaining_ratio))

        if goals_exist:
            st.caption(f"基于您的月储蓄 {fmt(total_monthly_available, decimals=0)} 的推荐分配方案：")
            alloc_cols = st.columns(len(allocation_suggestions))
            for idx, (name, ratio, amount) in enumerate(allocation_suggestions):
                with alloc_cols[idx]:
                    st.metric(name, fmt(amount, decimals=0))
                    st.caption(f"占比 {ratio*100:.0f}%")
        else:
            st.caption("设置储蓄目标或退休参数后，将自动推荐资金分配方案。")
    else:
        st.caption("请先使用预算分配建议器设置收入，以获取资金分配建议。")

    # ── National Benchmark Comparison (#15) ───────────────
    st.markdown("---")
    st.subheader("📊 全国基准对比")

    has_benchmark_data = False

    if dash_budget:
        has_benchmark_data = True
        save_rate = dash_budget.get("pct_save", 0)
        benchmark_save = BENCHMARKS.avg_savings_rate_pct
        delta = save_rate - benchmark_save
        bcol1, bcol2, bcol3 = st.columns(3)
        bcol1.metric("您的储蓄率", f"{save_rate}%", delta=f"{'高于' if delta >= 0 else '低于'}全国均值 {abs(delta):.1f}pp")
        bcol2.metric("全国平均储蓄率", f"{benchmark_save}%")
        bcol3.metric("全国人均存款", fmt(BENCHMARKS.avg_deposit_per_capita, decimals=0))

    if dash_networth:
        has_benchmark_data = True
        nw = dash_networth.get("net_worth", 0)
        total_assets = dash_networth.get("total_assets", 0)
        total_liab = total_assets - nw
        debt_ratio = (total_liab / total_assets * 100) if total_assets > 0 else 0
        benchmark_debt = BENCHMARKS.avg_debt_ratio_pct
        dcol1, dcol2 = st.columns(2)
        dcol1.metric("您的负债率", f"{debt_ratio:.1f}%", delta=f"{'低于' if debt_ratio <= benchmark_debt else '高于'}基准 {abs(debt_ratio - benchmark_debt):.1f}pp", delta_color="inverse")
        dcol2.metric("全国家庭负债率基准", f"{benchmark_debt}%")

    if not has_benchmark_data:
        st.caption("使用预算或净值工具后，将自动对比全国平均水平。")

    # Cross-tool insights
    st.markdown("---")
    st.subheader("🔗 跨工具综合分析")
    insights = []

    if dash_retirement and dash_savings:
        gap = dash_retirement.get("gap", 0)
        months = dash_savings.get("months_needed", 0)
        if gap > 0 and months > 0:
            insights.append(f"🏖️💰 **联动分析**：退休缺口约 {fmt(gap, decimals=0)}，而您的储蓄目标还需 {months // 12} 年达成。建议优先补齐退休缺口（额外月存 {fmt(dash_retirement.get('extra_monthly', 0), decimals=0)}），同时维持储蓄计划。")

    if dash_loan and dash_budget:
        loan_interest = dash_loan.get("total_interest", 0)
        savings_amt = dash_budget.get("amt_save", 0)
        if loan_interest > 0 and savings_amt > 0:
            loan_payment = dash_loan.get("monthly_payment", 0)
            insights.append(f"🏦💡 **债务 vs 储蓄**：当前月贷款还款 {fmt(loan_payment, decimals=0)}，月储蓄 {fmt(savings_amt, decimals=0)}。债务成本优先偿还可节省总利息 {fmt(loan_interest, decimals=0)}。")

    if dash_networth and dash_retirement:
        nw = dash_networth.get("net_worth", 0)
        gap = dash_retirement.get("gap", 0)
        if nw > 0 and gap > 0:
            coverage_pct = min(100.0, nw / gap * 100)
            insights.append(f"🏠🏖️ **净资产覆盖率**：当前净资产 {fmt(nw, decimals=0)} 可覆盖退休缺口的 **{coverage_pct:.1f}%**。{'建议继续增加投资资产。' if coverage_pct < 100 else '净资产已足以覆盖退休缺口，财务状况良好！'}")

    if dash_insurance and dash_compound:
        irr = dash_insurance.get("irr_pct", 0)
        compound_interest = dash_compound.get("total_interest", 0)
        final_balance = dash_compound.get("final_balance", 0)
        compound_annualized = (compound_interest / final_balance * 100) if final_balance > 0 and compound_interest > 0 else 0.0
        if irr > 0 and compound_annualized > 0:
            if irr < compound_annualized:
                insights.append(f"🛡️💰 **保险效率提示**：当前保单 IRR 为 {irr:.2f}%，低于复利投资年化收益约 {compound_annualized:.1f}%。若理财目标以增值为主，可考虑将部分保险支出转向复利投资。")
            else:
                insights.append(f"🛡️💰 **保险回报良好**：保单 IRR {irr:.2f}% 与复利投资收益相当，兼顾保障与收益。")
        elif irr > 0 and irr < 3:
            insights.append(f"🛡️💰 **保险效率提示**：当前保单 IRR 为 {irr:.2f}%，属于低收益型。若理财目标以增值为主，可考虑将保险支出转向复利投资。")

    if insights:
        for insight in insights:
            st.info(insight)
    else:
        st.caption("使用更多工具后，这里将显示跨工具的综合分析洞察。")

    # ── Cash Flow Timeline (#2) ────────────────────────────
    st.markdown("---")
    st.subheader("🌊 现金流时间轴规划器")
    st.caption("将所有工具的年度收支流叠加到统一时间轴，识别未来哪年现金流最紧张。")

    cf_years = list(range(1, 31))
    cf_income = [0.0] * 30
    cf_expense = [0.0] * 30
    cf_net = [0.0] * 30
    cf_has_data = False

    if dash_budget and dash_budget.get("amt_save", 0) > 0:
        monthly_save = dash_budget.get("amt_save", 0)
        for i in range(30):
            cf_income[i] += monthly_save * 12
        cf_has_data = True

    if dash_loan and dash_loan.get("monthly_payment", 0) > 0:
        monthly_pmt = dash_loan.get("monthly_payment", 0)
        for i in range(30):
            cf_expense[i] += monthly_pmt * 12
        cf_has_data = True

    if dash_retirement:
        gap = dash_retirement.get("gap", 0)
        extra = dash_retirement.get("extra_monthly", 0)
        if extra > 0:
            for i in range(30):
                cf_expense[i] += extra * 12
        cf_has_data = True

    if dash_savings and dash_savings.get("months_needed", 0) > 0:
        months_left = dash_savings.get("months_needed", 0)
        for i in range(30):
            yr_start_month = i * 12
            yr_end_month = (i + 1) * 12
            if yr_start_month < months_left:
                active_months = min(12, months_left - yr_start_month)
                monthly_deposit_sav = dash_savings.get("total_interest", 0)
        cf_has_data = True

    if cf_has_data:
        for i in range(30):
            cf_net[i] = cf_income[i] - cf_expense[i]

        current_year_cf = __import__("datetime").date.today().year
        years_labels = [str(current_year_cf + i) for i in range(30)]

        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(
            x=years_labels, y=cf_income,
            name="年度可用收入/储蓄",
            marker_color="#00CC96",
            opacity=0.75,
        ))
        fig_cf.add_trace(go.Bar(
            x=years_labels, y=[-v for v in cf_expense],
            name="年度支出/还款",
            marker_color="#EF553B",
            opacity=0.75,
        ))
        fig_cf.add_trace(go.Scatter(
            x=years_labels, y=cf_net,
            name="净现金流",
            mode="lines+markers",
            line=dict(width=2.5, color="#636EFA"),
            hovertemplate="%{x}<br>净现金流: " + sym + "%{y:,.0f}<extra></extra>",
        ))
        fig_cf.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)

        fig_cf.update_layout(
            **build_layout(xaxis_title="年份", yaxis_title=f"金额（{sym}）", yaxis_tickformat=","),
            barmode="relative",
        )
        st.plotly_chart(fig_cf, use_container_width=True)

        tightest_year_idx = cf_net.index(min(cf_net))
        if cf_net[tightest_year_idx] < 0:
            st.warning(f"⚠️ **{years_labels[tightest_year_idx]}年** 现金流压力最大，净现金流约 **{fmt(cf_net[tightest_year_idx], decimals=0)}**，建议提前做好资金储备。")
        else:
            best_year_idx = cf_net.index(max(cf_net))
            st.success(f"✅ 未来 30 年现金流整体为正。**{years_labels[best_year_idx]}年** 富余最多，约 **{fmt(cf_net[best_year_idx], decimals=0)}**。")
    else:
        st.caption("使用预算、贷款、储蓄等工具后，将在此自动生成跨工具现金流时间轴。")

    # ── Annual Financial Review (#5) ──────────────────────
    st.markdown("---")
    st.subheader("📅 年度财务回顾")
    st.caption("整合所有工具数据，生成结构化年度财务总结。")

    current_year_str = str(_dt.date.today().year)

    review_sections: list[str] = []

    if dash_networth:
        nw_val = dash_networth.get("net_worth", 0)
        total_a = dash_networth.get("total_assets", 0)
        total_l = total_a - nw_val
        review_sections.append(f"**资产负债状况**：总资产 {fmt(total_a, decimals=0)}，总负债 {fmt(total_l, decimals=0)}，净资产 {fmt(nw_val, decimals=0)}")

    if dash_budget:
        save_rate = dash_budget.get("pct_save", 0)
        save_amt = dash_budget.get("amt_save", 0)
        review_sections.append(f"**储蓄执行**：月储蓄 {fmt(save_amt, decimals=0)}，储蓄率 {save_rate}%")

    if dash_savings:
        months_left = dash_savings.get("months_needed", 0)
        if months_left > 0:
            review_sections.append(f"**储蓄目标进度**：距达成目标还需 {months_left // 12} 年 {months_left % 12} 个月")

    if dash_retirement:
        gap_ret = dash_retirement.get("gap", 0)
        extra_ret = dash_retirement.get("extra_monthly", 0)
        if gap_ret <= 0:
            review_sections.append("**退休规划**：退休资金已充足，计划执行良好")
        else:
            review_sections.append(f"**退休规划**：退休缺口 {fmt(gap_ret, decimals=0)}，需每月额外储蓄 {fmt(extra_ret, decimals=0)}")

    if dash_loan:
        review_sections.append(f"**债务管理**：贷款月还款 {fmt(dash_loan.get('monthly_payment', 0), decimals=0)}，累计利息支出 {fmt(dash_loan.get('total_interest', 0), decimals=0)}")

    if dash_insurance:
        review_sections.append(f"**保险保障**：年保费 {fmt(dash_insurance.get('total_premium', 0), decimals=0)}，保单 IRR {dash_insurance.get('irr_pct', 0):.2f}%")

    if dash_tax:
        review_sections.append(f"**税务情况**：年应缴税 {fmt(dash_tax.get('annual_tax', 0), decimals=0)}，实际税率 {dash_tax.get('effective_rate', 0):.1f}%，税后月到手 {fmt(dash_tax.get('after_tax_monthly', 0), decimals=0)}")

    if review_sections:
        st.markdown(f"### {current_year_str} 年度财务回顾")
        for section in review_sections:
            st.markdown(f"- {section}")

        if dim_scores:
            st.markdown(f"**综合健康评分**：{overall_score}/100 — {overall_grade}")

        review_text = f"{current_year_str} 年度财务回顾\n\n" + "\n".join(f"• {s}" for s in review_sections)
        if dim_scores:
            review_text += f"\n\n综合健康评分：{overall_score}/100"

        st.download_button(
            "📥 下载年度财务回顾 (TXT)",
            data=review_text,
            file_name=f"财务年度回顾_{current_year_str}.txt",
            mime="text/plain",
            use_container_width=False,
        )
    else:
        st.caption("使用各工具计算后，这里将自动汇总生成年度财务回顾报告。")

    # Auto-save session data
    save_session_data()

else:
    if restored > 0:
        st.success(f"✅ 已从磁盘恢复 {restored} 项仪表盘数据。")
        st.rerun()
    else:
        st.info("👆 请先使用左侧工具进行计算，仪表盘将自动汇总各工具的关键指标。")

# ── 综合财务诊断报告生成引擎 ─────────────────────────────────────
st.markdown("---")
st.subheader("📄 个人财务全景诊断归档")
st.write("一键全维扫描您的交互记录，提取所有核心指标并瞬间熔铸，为您秒级生成可脱机离线查阅的专属企业级 HTML 视觉财报。特别适配深浅明暗多主题无感切换；极度推荐查阅时按下 `Ctrl/Cmd + P` 轻松转储为纯矢量高清 PDF。")

metrics_dict = {}
if dash_compound:
    metrics_dict["compound"] = dash_compound
if dash_loan:
    metrics_dict["loan"] = dash_loan
if dash_savings:
    metrics_dict["savings"] = dash_savings
if dash_budget:
    metrics_dict["budget"] = dash_budget
if dash_retirement:
    metrics_dict["retirement"] = dash_retirement
if dash_insurance:
    metrics_dict["insurance"] = dash_insurance
if dash_networth:
    metrics_dict["networth"] = dash_networth
if dash_tax:
    metrics_dict["tax"] = dash_tax

html_content = generate_html_report(metrics_dict)

report_cols = st.columns(2)
with report_cols[0]:
    st.download_button(
        label="📥 下载 HTML 财务诊断报告",
        data=html_content,
        file_name="OmniFinance_Health_Report.html",
        mime="text/html",
        type="primary",
        use_container_width=True,
    )

with report_cols[1]:
    if is_pdf_available():
        pdf_bytes = generate_pdf_report(metrics_dict)
        if pdf_bytes:
            st.download_button(
                label="📥 下载 PDF 财务诊断报告",
                data=pdf_bytes,
                file_name="OmniFinance_Health_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        st.caption("💡 安装 weasyprint 可启用原生 PDF 导出")

# ── Data Persistence & Export Hub (#11, #16) ──────────────
st.markdown("---")
st.subheader("💾 数据管理")

pcol1, pcol2, pcol3, pcol4 = st.columns(4)
with pcol1:
    if st.button("💾 保存仪表盘数据", use_container_width=True):
        save_session_data()
        st.success("✅ 数据已保存！")

with pcol2:
    export_data = export_all_data()
    st.download_button(
        label="📤 导出全部数据 (JSON)",
        data=export_data,
        file_name="OmniFinance_Backup.json",
        mime="application/json",
        use_container_width=True,
    )

with pcol3:
    st.download_button(
        label="📄 下载 HTML 仪表盘报告",
        data=html_content,
        file_name="OmniFinance_Dashboard.html",
        mime="text/html",
        use_container_width=True,
    )

with pcol4:
    if is_pdf_available():
        _pdf_bytes = generate_pdf_report(metrics_dict)
        if _pdf_bytes:
            st.download_button(
                label="📑 下载 PDF 仪表盘报告",
                data=_pdf_bytes,
                file_name="OmniFinance_Dashboard.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("📑 PDF 生成失败", disabled=True, use_container_width=True)
    else:
        st.button("📑 PDF（需安装 weasyprint）", disabled=True, use_container_width=True)

_import_col = st.columns(1)[0]
with _import_col:
    uploaded = st.file_uploader("📥 导入数据备份", type=["json"], key="import_backup")
    if uploaded is not None:
        count = import_all_data(uploaded.read().decode("utf-8"))
        if count > 0:
            st.success(f"✅ 已导入 {count} 项数据！")
        else:
            st.warning("⚠️ 未找到有效数据。")

# ── Reminders (#12) ──────────────────────────────────────
st.markdown("---")
st.subheader("🔔 财务提醒")

due = get_due_reminders()
if due:
    for r in due:
        st.warning(f"⏰ **{r['title']}** — {r.get('description', '')} (到期: {r['due_date']})")

all_reminders = get_reminders()
if all_reminders:
    for r in all_reminders:
        rcol1, rcol2 = st.columns([4, 1])
        rcol1.caption(f"📌 {r['title']} — {r.get('due_date', '')} | {r.get('category', '')}")
        if rcol2.button("✅", key=f"rem_done_{r['id']}"):
            complete_reminder(r["id"])
            st.rerun()
else:
    st.caption("暂无提醒。可在下方添加新的财务提醒。")

with st.expander("➕ 添加新提醒"):
    rem_title = st.text_input("标题", key="rem_title")
    rem_desc = st.text_input("描述", key="rem_desc")
    rem_date = st.date_input("到期日", key="rem_date")
    rem_cat = st.selectbox("类别", ["还贷", "保费", "储蓄", "投资", "税务", "其他"], key="rem_cat")
    if st.button("添加提醒") and rem_title:
        add_reminder(rem_title, rem_desc, str(rem_date), rem_cat)
        st.success("✅ 提醒已添加！")
        st.rerun()

st.markdown("---")
st.caption("***Eugene Finance 核心架构驱动 | Empower Your Knowledge, Enrich Your Life***")
