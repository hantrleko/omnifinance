import datetime as _dt

import plotly.graph_objects as go
import streamlit as st

from core.action_plan import build_action_impact_plan
from core.benchmarks import BENCHMARKS
from core.brief import build_decision_brief
from core.chart_config import build_layout
from core.currency import fmt, get_symbol
from core.health import build_action_recommendations, build_health_report
from core.navigation import DASHBOARD_PROGRESS_ITEMS, get_page, pages_by_category
from core.opportunity import build_90_day_sprint, build_opportunity_radar
from core.pdf_report import generate_pdf_report, is_pdf_available
from core.persistence import export_all_data, import_all_data, restore_session_data, save_session_data
from core.reminders import add_reminder, complete_reminder, get_due_reminders, get_reminders
from core.report_generator import generate_html_report
from core.stress import build_stress_report
from core.version import VERSION

_ACTION_PROGRESS_PREFIX = "decision_action_done_"


def _action_progress_key(action_key: str) -> str:
    """Stable session key for a generated action completion state."""
    return f"{_ACTION_PROGRESS_PREFIX}{action_key}"


def _reminder_category_for_page(page_key: str) -> str:
    """Map action cards to the reminder page's existing category set."""
    if page_key in {"loan", "debt"}:
        return "还贷"
    if page_key in {"insurance"}:
        return "保费"
    if page_key in {"tax"}:
        return "税务"
    if page_key in {"portfolio", "fx", "quote", "backtest", "rebalance", "screener"}:
        return "投资"
    if page_key in {"savings", "budget", "retirement", "networth"}:
        return "储蓄"
    return "其他"


st.title(f"🌟 全能理财家 (OmniFinance) `{VERSION}`")
st.caption("✨ **Empower Your Knowledge, Enrich Your Life** | Eugene Finance 荣誉出品")

# ── 快速导航卡片 ──────────────────────────────────────────
st.markdown("### 🚀 快速开始")
st.caption("选择一个场景直接进入工具；所有页面元数据由统一导航注册表驱动，后续新增功能只需维护一处。")

_category_icons = {
    "基础理财管理": "💰",
    "资产与债务管理": "⚖️",
    "投资分析引擎": "📈",
    "高级人生规划": "🏖️",
    "分析与工具": "🔬",
    "高级工具 (v2.0)": "🆕",
}
_category_pages = [(category, pages) for category, pages in pages_by_category().items() if category != "平台概览"]
for _row_start in range(0, len(_category_pages), 3):
    _cols = st.columns(3)
    for _col, (_category, _pages) in zip(_cols, _category_pages[_row_start: _row_start + 3], strict=False):
        with _col.container(border=True):
            st.markdown(f"#### {_category_icons.get(_category, '📌')} {_category}")
            st.caption(" · ".join(page.title for page in _pages[:4]))
            for page in _pages[:2]:
                st.page_link(page.path, label=page.title, icon=page.icon, help=page.description)
            if len(_pages) > 2:
                st.caption(f"另有 {len(_pages) - 2} 个工具可在左侧导航中查看")

st.caption("👈 也可以使用左侧搜索框快速定位；搜索结果现在支持直接跳转。")

with st.expander("📋 版本历史", expanded=False):
    st.markdown("""
### v2.2.0 — 行动影响模拟器
🧪 What-if 行动模拟 · 执行动能评分 · 第一周行动清单 · Markdown 行动计划
把「知道问题」升级为「比较行动影响」，帮助用户判断本周最值得推进的财务动作。

### v2.1.0 — 智能决策中枢升级
🧠 决策简报 · 🛰️ 财务机会雷达 · 🧯 压力测试实验室 · 90 天行动冲刺 · 运行时自检
把健康评分、机会识别、风险压力和行动清单串成完整闭环，并支持 Markdown 简报导出。

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

dashboard_keys = ("dashboard_compound", *(item.session_key for item in DASHBOARD_PROGRESS_ITEMS))
has_data = any(st.session_state.get(key) for key in dashboard_keys)

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

    health_report = build_health_report(
        budget=dash_budget,
        retirement=dash_retirement,
        networth=dash_networth,
        tax=dash_tax,
        insurance=dash_insurance,
        money_formatter=lambda value: fmt(value, decimals=0),
    )
    dim_scores = [(dimension.name, dimension.score, dimension.tip, dimension.grade) for dimension in health_report.dimensions]
    overall_score = health_report.overall_score
    overall_grade = health_report.overall_grade

    if health_report.dimensions and overall_score is not None:
        st.metric("💯 综合财务健康评分", f"{overall_score}/100", delta=overall_grade)

        _n_dim_cols = min(3, len(health_report.dimensions))
        dim_cols = st.columns(_n_dim_cols)
        for idx, dimension in enumerate(health_report.dimensions):
            with dim_cols[idx % _n_dim_cols]:
                st.metric(dimension.name, f"{dimension.score}/100", delta=dimension.grade)
                st.caption(dimension.tip)

        if health_report.improvement_tips:
            with st.expander("📋 改善建议详情"):
                for tip in health_report.improvement_tips:
                    st.markdown(f"- {tip}")

        action_recommendations = build_action_recommendations(health_report)
        if action_recommendations:
            st.markdown("#### 🧭 下一步行动建议")
            action_cols = st.columns(len(action_recommendations))
            for action_col, action in zip(action_cols, action_recommendations, strict=True):
                page = get_page(action.page_key)
                with action_col.container(border=True):
                    st.caption(f"优先级：{action.priority}")
                    st.markdown(f"**{action.title}**")
                    st.caption(action.reason)
                    st.page_link(page.path, label=page.title, icon=page.icon)
    else:
        st.caption("使用更多工具后，这里将展示各维度的精细评分与改善建议。")

    # ── Opportunity Radar ─────────────────────────────────
    st.markdown("---")
    st.subheader("🛰️ 财务机会雷达")
    st.caption("把预算、债务、退休、税务、保障等结果转译为可执行的机会清单，帮助你找到下一步最值得优化的杠杆点。")

    opportunity_report = build_opportunity_radar(
        budget=dash_budget,
        loan=dash_loan,
        savings=dash_savings,
        retirement=dash_retirement,
        networth=dash_networth,
        tax=dash_tax,
        insurance=dash_insurance,
        money_formatter=lambda value: fmt(value, decimals=0),
    )

    if opportunity_report.opportunities:
        top_opportunity = opportunity_report.top_opportunity
        radar_cols = st.columns(3)
        radar_cols[0].metric("发现机会", f"{len(opportunity_report.opportunities)} 个", delta=f"高优先级 {opportunity_report.high_priority_count} 个")
        radar_cols[1].metric("首要机会", top_opportunity.title if top_opportunity else "-", delta=f"影响力 {top_opportunity.impact_score}/100" if top_opportunity else None)
        radar_cols[2].metric("执行方式", "90 天冲刺", delta="按月拆解行动")
        st.info(opportunity_report.summary)

        fig_opp = go.Figure(go.Bar(
            x=[opportunity.impact_score for opportunity in opportunity_report.opportunities],
            y=[opportunity.title for opportunity in opportunity_report.opportunities],
            orientation="h",
            marker_color=["#EF553B" if opportunity.priority == "高" else "#FECB52" if opportunity.priority == "中" else "#00CC96" for opportunity in opportunity_report.opportunities],
            text=[f"{opportunity.priority} · {opportunity.impact_score}" for opportunity in opportunity_report.opportunities],
            textposition="auto",
            hovertemplate="%{y}<br>影响力: %{x}/100<extra></extra>",
        ))
        fig_opp.update_layout(
            **build_layout(xaxis_title="机会影响力评分", yaxis_title="", showlegend=False, height=320),
            xaxis=dict(range=[0, 100]),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_opp, use_container_width=True)

        st.markdown("#### 🎯 推荐机会卡")
        opportunity_cols = st.columns(min(3, len(opportunity_report.opportunities)))
        for opportunity_col, opportunity in zip(opportunity_cols, opportunity_report.opportunities[:3], strict=False):
            page = get_page(opportunity.page_key)
            with opportunity_col.container(border=True):
                st.caption(f"{opportunity.category} · 优先级 {opportunity.priority} · 置信度 {opportunity.confidence}%")
                st.markdown(f"**{opportunity.title}**")
                st.metric(opportunity.metric_label, opportunity.metric_value)
                st.caption(opportunity.rationale)
                st.page_link(page.path, label=f"进入{page.title}", icon=page.icon)

        sprint_steps = build_90_day_sprint(opportunity_report)
        if sprint_steps:
            with st.expander("🧭 90 天行动冲刺计划", expanded=False):
                for step in sprint_steps:
                    page = get_page(step.page_key)
                    st.markdown(f"**{step.phase}｜{step.title}**")
                    st.caption(step.focus)
                    for item in step.checklist:
                        st.markdown(f"- {item}")
                    st.page_link(page.path, label=f"打开{page.title}", icon=page.icon)
    else:
        st.success("✅ 暂未发现明显短板。建议继续补充更多工具数据，或进入投资组合优化器探索资产配置效率。")

    # ── Stress Test Lab ───────────────────────────────────
    st.markdown("---")
    st.subheader("🧯 财务压力测试实验室")
    st.caption("把收入下降、突发支出、贷款月供上升和资产回撤转化为可量化冲击，提前查看家庭财务防线是否足够。")

    stress_report = build_stress_report(
        budget=dash_budget,
        loan=dash_loan,
        retirement=dash_retirement,
        networth=dash_networth,
        money_formatter=lambda value: fmt(value, decimals=0),
    )

    if stress_report.scenarios:
        weakest_scenario = stress_report.weakest_scenario
        stress_cols = st.columns(4)
        stress_cols[0].metric("估算安全垫", f"{stress_report.buffer_months:.1f} 个月", delta=fmt(stress_report.liquid_buffer, decimals=0))
        stress_cols[1].metric("月结余", fmt(stress_report.monthly_surplus, decimals=0), delta=f"月支出 {fmt(stress_report.monthly_expense, decimals=0)}")
        stress_cols[2].metric("高压场景", f"{stress_report.critical_count} 个", delta="需优先处理" if stress_report.critical_count else "基础防线通过")
        stress_cols[3].metric("最弱场景", weakest_scenario.title if weakest_scenario else "-", delta=f"韧性 {weakest_scenario.resilience_score}/100" if weakest_scenario else None)
        st.info(stress_report.summary)

        _stress_colors = {"safe": "#00CC96", "watch": "#FECB52", "critical": "#EF553B"}
        fig_stress = go.Figure(go.Bar(
            x=[scenario.title for scenario in stress_report.scenarios],
            y=[scenario.buffer_months_after for scenario in stress_report.scenarios],
            marker_color=[_stress_colors[scenario.status] for scenario in stress_report.scenarios],
            text=[f"{scenario.buffer_months_after:.1f}月" for scenario in stress_report.scenarios],
            textposition="outside",
            hovertemplate="%{x}<br>冲击后安全垫: %{y:.1f}个月<extra></extra>",
        ))
        fig_stress.add_hline(y=3, line_dash="dash", line_color="gray", annotation_text="3 个月基础线")
        fig_stress.update_layout(**build_layout(xaxis_title="压力场景", yaxis_title="冲击后安全垫（月）", showlegend=False, height=340))
        st.plotly_chart(fig_stress, use_container_width=True)

        scenario_cols = st.columns(min(3, len(stress_report.scenarios)))
        for scenario_col, scenario in zip(scenario_cols, stress_report.scenarios[:3], strict=False):
            page = get_page(scenario.page_key)
            status_label = {"safe": "安全", "watch": "关注", "critical": "高压"}[scenario.status]
            with scenario_col.container(border=True):
                st.caption(f"{scenario.severity}压力 · {status_label} · 韧性 {scenario.resilience_score}/100")
                st.markdown(f"**{scenario.title}**")
                st.metric("估算冲击", fmt(scenario.estimated_impact, decimals=0), delta=f"缺口 {fmt(scenario.liquidity_gap, decimals=0)}" if scenario.liquidity_gap else "无流动性缺口")
                st.caption(scenario.narrative)
                with st.expander("行动清单", expanded=scenario.status == "critical"):
                    for action in scenario.actions:
                        st.markdown(f"- {action}")
                st.page_link(page.path, label=f"打开{page.title}", icon=page.icon)
    else:
        st.caption("填写预算或资产净值数据后，将自动生成家庭财务压力测试。")

    # ── Executive Decision Brief ──────────────────────────
    st.markdown("---")
    st.subheader("🧠 个人财务决策简报")
    st.caption("自动整合健康评分、机会雷达与压力测试，生成可下载的本地规则化决策摘要，不依赖外部 AI 服务。")

    decision_brief = build_decision_brief(
        health_report=health_report,
        opportunity_report=opportunity_report,
        stress_report=stress_report,
        generated_on=_dt.date.today(),
    )
    brief_cols = st.columns(3)
    brief_cols[0].metric("决策模式", decision_brief.mode)
    brief_cols[1].metric("准备度评分", f"{decision_brief.readiness_score}/100" if decision_brief.readiness_score is not None else "暂无")
    brief_cols[2].metric("优先行动", f"{len(decision_brief.priority_actions)} 项")
    st.info(f"**{decision_brief.headline}**\n\n{decision_brief.summary}")

    brief_tab_findings, brief_tab_actions, brief_tab_export = st.tabs(["关键发现", "优先行动", "简报导出"])
    with brief_tab_findings:
        for finding in decision_brief.key_findings:
            st.markdown(f"- {finding}")
        if decision_brief.watchlist:
            st.markdown("**观察清单**")
            for watch in decision_brief.watchlist:
                st.markdown(f"- {watch}")
    with brief_tab_actions:
        for idx, action in enumerate(decision_brief.priority_actions, start=1):
            st.markdown(f"**{idx}. {action}**")
        st.caption("建议把优先行动拆到本周待办，并在月末回到首页复盘。")
    with brief_tab_export:
        brief_markdown = decision_brief.to_markdown()
        st.download_button(
            "📥 下载 Markdown 决策简报",
            data=brief_markdown,
            file_name=f"OmniFinance_Decision_Brief_{decision_brief.generated_on}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        with st.expander("预览 Markdown"):
            st.code(brief_markdown, language="markdown")

    # ── Action Impact Simulator ───────────────────────────
    st.markdown("---")
    st.subheader("🧪 行动影响模拟器")
    st.caption("把机会、压力和健康评分转化为可比较的 what-if 行动，估算执行后可能带来的动能提升。")

    action_plan = build_action_impact_plan(
        budget=dash_budget,
        loan=dash_loan,
        retirement=dash_retirement,
        networth=dash_networth,
        health_report=health_report,
        opportunity_report=opportunity_report,
        stress_report=stress_report,
        money_formatter=lambda value: fmt(value, decimals=0),
    )

    if action_plan.actions:
        action_cols = st.columns(4)
        action_cols[0].metric("基线评分", f"{action_plan.baseline_score}/100" if action_plan.baseline_score is not None else "暂无")
        action_cols[1].metric("执行动能", f"{action_plan.momentum_score}/100" if action_plan.momentum_score is not None else "暂无")
        action_cols[2].metric("预计总提升", f"+{action_plan.total_estimated_uplift}")
        action_cols[3].metric("高优先级", f"{action_plan.high_priority_count} 项")
        st.info(action_plan.summary)

        fig_action = go.Figure(go.Bar(
            x=[action.estimated_uplift for action in action_plan.actions],
            y=[action.title for action in action_plan.actions],
            orientation="h",
            marker_color=["#EF553B" if action.priority == "高" else "#FECB52" if action.priority == "中" else "#00CC96" for action in action_plan.actions],
            text=[f"+{action.estimated_uplift} · {action.effort}努力" for action in action_plan.actions],
            textposition="auto",
            hovertemplate="%{y}<br>预计提升: +%{x}<extra></extra>",
        ))
        fig_action.update_layout(
            **build_layout(xaxis_title="预计动能提升", yaxis_title="", showlegend=False, height=320),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_action, use_container_width=True)

        action_tabs = st.tabs(["行动卡", "第一周步骤", "计划导出"])
        with action_tabs[0]:
            card_cols = st.columns(min(3, len(action_plan.actions)))
            for card_col, action in zip(card_cols, action_plan.actions[:3], strict=False):
                page = get_page(action.page_key)
                with card_col.container(border=True):
                    st.caption(f"{action.category} · 优先级 {action.priority} · {action.horizon_days} 天")
                    st.markdown(f"**{action.title}**")
                    st.metric("预计提升", f"+{action.estimated_uplift}", delta=f"努力度 {action.effort}")
                    st.caption(action.rationale)
                    st.page_link(page.path, label=f"打开{page.title}", icon=page.icon)
        with action_tabs[1]:
            for idx, action in enumerate(action_plan.actions[:5], start=1):
                st.markdown(f"**{idx}. {action.title}**")
                st.caption(f"当前：{action.current_signal} → 目标：{action.target_signal}")
                for step in action.first_week_steps:
                    st.markdown(f"- {step}")
        with action_tabs[2]:
            action_markdown = action_plan.to_markdown()
            st.download_button(
                "📥 下载 Markdown 行动计划",
                data=action_markdown,
                file_name="OmniFinance_Action_Impact_Plan.md",
                mime="text/markdown",
                use_container_width=True,
            )
            with st.expander("预览 Markdown"):
                st.code(action_markdown, language="markdown")

        st.markdown("#### ✅ 行动闭环")
        with st.expander("🧾 为行动建立复盘闭环", expanded=True):
            for idx, action in enumerate(action_plan.actions, start=1):
                with st.container(border=True):
                    cols = st.columns([4, 1, 1.8])
                    with cols[0]:
                        st.caption(f"行动 {idx}")
                        st.markdown(f"**{action.title}**")
                        st.caption(f"目标：{action.current_signal} -> {action.target_signal}")
                    done_key = _action_progress_key(action.key)
                    with cols[1]:
                        st.checkbox(
                            "已完成",
                            value=bool(st.session_state.get(done_key, False)),
                            key=done_key,
                        )
                    with cols[2]:
                        if st.button("📆 7 天提醒", key=f"action_reminder_{action.key}", use_container_width=True):
                            due = str(_dt.date.today() + _dt.timedelta(days=7))
                            add_reminder(
                                title=f"行动回顾：{action.title}",
                                description=f"建议在 {due} 复盘：{action.current_signal} -> {action.target_signal}。",
                                due_date=due,
                                category=_reminder_category_for_page(action.page_key),
                            )
                            st.success("✅ 已写入提醒")

            action_done_count = sum(
                1 for action in action_plan.actions if st.session_state.get(_action_progress_key(action.key), False)
            )
            st.progress(
                action_done_count / len(action_plan.actions),
                text=f"本周完成度：{action_done_count}/{len(action_plan.actions)} 个行动",
            )
    else:
        st.caption("继续补充预算、净资产、贷款或退休数据后，将自动生成行动影响模拟。")

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
        savings_monthly = dash_savings.get("monthly_deposit", 0)
        if savings_monthly > 0:
            cf_has_data = True
        for i in range(30):
            yr_start_month = i * 12
            if yr_start_month < months_left:
                active_months = min(12, months_left - yr_start_month)
                cf_expense[i] += savings_monthly * active_months

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
        st.info("👆 这是一个“先算数据，再看结论”的工作流。建议按以下步骤先补 3 个核心资料，再回到决策中枢获取行动清单。")
        starter_pages = [get_page("budget"), get_page("networth"), get_page("retirement"), get_page("decision")]
        st.markdown("#### 新手建议")
        st.caption("第一次使用时，不要急着点所有功能：先完成这 4 步，能最快看到有价值的建议。")
        _starter_cols = st.columns(3)
        _starter_pages = starter_pages[:3]
        _labels = ["第一步", "第二步", "第三步"]
        for idx, _col in enumerate(_starter_cols):
            _page = _starter_pages[idx]
            _label = _labels[idx]
            with _col.container(border=True):
                st.caption(_label)
                st.markdown(f"### {_page.icon}")
                st.markdown(f"**{_page.title}**")
                st.caption(_page.description)
                st.page_link(_page.path, label="开始", icon="➡️")

        st.markdown("#### 接着去决策中枢")
        with st.container(border=True):
            decision_page = get_page("decision")
            st.caption("第四步")
            st.markdown(f"### {decision_page.icon} {decision_page.title}")
            st.caption("完成基础配置后，进入决策中枢查看健康评分、机会雷达与 90 天行动建议。")
            st.page_link(decision_page.path, label="打开决策中枢", icon="🧭")

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
