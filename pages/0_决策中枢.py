import streamlit as st

import datetime as _dt

from core.action_plan import build_action_impact_plan
from core.currency import fmt
from core.health import build_health_report
from core.navigation import (
    get_page,
    get_product_journey_snapshot,
    track_recent_page,
    get_product_journey,
)
from core.opportunity import build_opportunity_radar
from core.persistence import ACTION_PROGRESS_PREFIX as _ACTION_PROGRESS_PREFIX
from core.reminders import add_reminder
from core.stress import build_stress_report
from core.version import VERSION

st.title(f"🧭 OmniFinance 决策中枢 `{VERSION}`")
st.caption("把个人财务输入转化为健康诊断、机会识别、压力测试和行动计划。")

# 体验层：记忆最近访问，支持侧边栏“最近访问”快速定位
track_recent_page(st.session_state, "decision")

if "show_decision_onboarding" not in st.session_state:
    st.session_state["show_decision_onboarding"] = True

_JOURNEY_STEPS = get_product_journey()
_journey_snapshot = get_product_journey_snapshot(st.session_state)
_next_step = _journey_snapshot.next_step
_completion_ratio = _journey_snapshot.completion_ratio

st.markdown("### 🧭 决策中枢主线导航")
nav_cols = st.columns([2, 1, 1])
with nav_cols[0]:
    st.metric("主线进度", f"{_journey_snapshot.completed}/{_journey_snapshot.total}")
with nav_cols[1]:
    st.metric("待补", f"{_journey_snapshot.pending_count}")
with nav_cols[2]:
    st.metric("完成率", f"{_journey_snapshot.completion_ratio:.0%}")
if _next_step:
    next_page = get_page(_next_step.page_key)
    st.caption(f"建议下一步：{_next_step.label}（{_next_step.minutes} 分钟）")
    st.caption(_next_step.outcome_hint)
    st.page_link(next_page.path, label=f"立即开始：{next_page.title}", icon=next_page.icon)
else:
    home_page = get_page("home")
    st.success("主线已完成，可直接进入综合分析与行动执行。")
    st.page_link(home_page.path, label="回到首页查看闭环分析", icon=home_page.icon)


_task_completion = {
    step.session_key: bool(st.session_state.get(step.session_key))
    for step in _JOURNEY_STEPS
}


def _action_progress_key(action_key: str) -> str:
    """Stable session key for an action completion checkbox."""
    return f"{_ACTION_PROGRESS_PREFIX}{action_key}"


def _reminder_category_for_page(page_key: str) -> str:
    """Map action cards to the reminder category set used in the app."""
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


def _build_action_review_markdown(
    actions,
    *,
    action_progress: dict[str, bool] | None = None,
    heading: str = "本周行动复盘清单",
) -> str:
    """Render the current action loop as markdown for one-tap export."""
    action_progress = action_progress or {}
    lines = [
        "# OmniFinance 行动复盘",
        "",
        f"**{heading}**",
        f"- 生成时间：{_dt.date.today().isoformat()}",
        "",
        "## 待执行行动",
    ]
    for idx, action in enumerate(actions, start=1):
        done = "✅ 已完成" if action_progress.get(action.key, False) else "⬜ 未完成"
        lines.extend(
            [
                f"{idx}. {done} {action.title}",
                f"   - 当前：{action.current_signal}",
                f"   - 目标：{action.target_signal}",
                f"   - 预计提升：+{action.estimated_uplift} / 努力：{action.effort}",
            ]
        )
    if not actions:
        lines.append("- 暂无可执行行动，先补齐关键输入。")
    return "\n".join(lines).strip() + "\n"


if st.session_state["show_decision_onboarding"]:
    with st.expander("🧭 任务导向新手指引", expanded=True):
        st.markdown("### 按任务先后顺序完成，越快看到完整决策闭环")
        st.progress(_completion_ratio, text=f"已完成 {_journey_snapshot.completed}/{_journey_snapshot.total} 个关键任务")
        if _next_step:
            st.info(f"建议先完成下一步：{_next_step.label}（{_next_step.minutes} 分钟），先补齐后再继续。")
        else:
            st.success("核心主线已完成，可直接查看完整决策摘要与行动计划。")

        _task_cols = st.columns(3)
        for step in _JOURNEY_STEPS:
            page = get_page(step.page_key)
            session_key = step.session_key
            done = _task_completion[session_key]
            with _task_cols[(step.step_no - 1) % 3].container(border=True):
                st.markdown(f"**第 {step.step_no} 步｜{page.title}**")
                st.caption(f"{'✅ 已完成' if done else '⬜ 待完成'} · 预计 {step.minutes} 分钟")
                st.caption(step.pending_hint)
                st.caption(step.outcome_hint)
                if not done:
                    st.page_link(page.path, label="前往填写", icon=page.icon)
                else:
                    st.page_link(page.path, label="复查数据", icon=page.icon)

        if st.button("我先跳过新手指引，直接看诊断结果"):
            st.session_state["show_decision_onboarding"] = False
            st.rerun()

# ── Workflow overview ─────────────────────────────────────
st.markdown("### 1. 主工作流")
workflow_cols = st.columns(4)
_workflow = [
    ("① 建立画像", "预算、净资产、贷款、保险、退休等基础输入"),
    ("② 生成诊断", "汇总指标并形成财务健康评分"),
    ("③ 识别机会", "找出储蓄、债务、保障、退休和投资优化点"),
    ("④ 输出行动", "形成第一周步骤、90 天计划和导出报告"),
]
for col, (title, desc) in zip(workflow_cols, _workflow, strict=True):
    with col.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(desc)

# ── Data completion status ────────────────────────────────
st.markdown("---")
st.markdown("### 2. 当前资料完成度")
_status_items = [
    (step.label, step.session_key, step.page_key, step.pending_hint, step.outcome_hint)
    for step in _JOURNEY_STEPS
]
completed = _journey_snapshot.completed
completion_ratio = _journey_snapshot.completion_ratio

st.progress(completion_ratio, text=f"已完成 {completed}/{len(_status_items)} 项基础资料")

status_cols = st.columns(3)
for idx, (label, key, page_key, pending_hint, outcome_hint) in enumerate(_status_items):
    page = get_page(page_key)
    done = bool(st.session_state.get(key))
    with status_cols[idx % 3].container(border=True):
        st.markdown(f"{'✅' if done else '⬜'} **{label}**")
        st.caption(outcome_hint if done else pending_hint)
        st.page_link(page.path, label=f"打开{page.title}", icon=page.icon)

# ── Recommended starter path ──────────────────────────────
st.markdown("---")
st.markdown("### 3. 推荐初始化路径")
st.caption("第一次使用时，不要从几十个工具里随便点。先按下面顺序完成基础资料，首页的综合分析会更有价值。")

starter_steps = [
    ("第一步", _JOURNEY_STEPS[0], "确认收入、支出和可储蓄金额"),
    ("第二步", _JOURNEY_STEPS[1], "建立资产、负债和净资产基线"),
    ("第三步", _JOURNEY_STEPS[2], "估算长期退休缺口与月度补充额"),
    ("第四步", "home", "回到首页查看健康评分、机会雷达和行动计划"),
]

starter_cols = st.columns(4)
for col, (step, page_key, reason) in zip(starter_cols, starter_steps, strict=True):
    if page_key == "home":
        page = get_page(page_key)
    else:
        page = get_page(page_key.page_key)
    with col.container(border=True):
        st.caption(step)
        st.markdown(f"**{page.title}**")
        st.caption(reason)
        st.page_link(page.path, label="开始", icon=page.icon)

# ── Decision summary from existing data ───────────────────
st.markdown("---")
st.markdown("### 4. 已有数据速览")

budget = st.session_state.get("dashboard_budget")
networth = st.session_state.get("dashboard_networth")
retirement = st.session_state.get("dashboard_retirement")
loan = st.session_state.get("dashboard_loan")
insurance = st.session_state.get("dashboard_insurance")
savings = st.session_state.get("dashboard_savings")

if any([budget, networth, retirement, loan, insurance, savings]):
    summary_cols = st.columns(5)
    if budget:
        summary_cols[0].metric("月储蓄额", fmt(budget.get("amt_save", 0), decimals=0), delta=f"储蓄率 {budget.get('pct_save', 0)}%")
    else:
        summary_cols[0].metric("月储蓄额", "待填写")

    if networth:
        summary_cols[1].metric("净资产", fmt(networth.get("net_worth", 0), decimals=0))
    else:
        summary_cols[1].metric("净资产", "待填写")

    if retirement:
        gap = retirement.get("gap", 0)
        summary_cols[2].metric("退休缺口", "已充足" if gap <= 0 else fmt(gap, decimals=0))
    else:
        summary_cols[2].metric("退休缺口", "待填写")

    if loan:
        summary_cols[3].metric("贷款月供", fmt(loan.get("monthly_payment", 0), decimals=0))
    elif insurance:
        summary_cols[3].metric("保险总保费", fmt(insurance.get("total_premium", 0), decimals=0))
    else:
        summary_cols[3].metric("债务/保障", "待填写")

    if savings:
        months_needed = savings.get("months_needed", -1)
        if months_needed == 0:
            savings_label = "已达标"
        elif months_needed > 0:
            savings_label = f"{months_needed} 个月可达成"
        elif months_needed < 0:
            savings_label = "无法达成"
        else:
            savings_label = "待填写"
        summary_cols[4].metric("储蓄目标", savings_label, delta=f"月投 {fmt(savings.get('monthly_deposit', 0), decimals=0)}")
    else:
        summary_cols[4].metric("储蓄目标", "待填写")

    st.success("已有资料可以参与综合分析。建议回到首页查看完整诊断、机会雷达、压力测试和行动影响模拟。")
    st.page_link("home.py", label="回到仪表盘首页", icon="🏠")
else:
    st.warning("当前还没有可用于综合诊断的资料。请先按推荐初始化路径完成基础输入。")

# ── Action impact loop ────────────────────────────────
st.markdown("---")
st.markdown("### 5. 行动影响与复盘")
if any([budget, networth, retirement, loan, insurance, savings]):
    st.caption("基于当前资料生成可执行行动建议，并支持完成打勾、7 天复盘提醒，形成闭环。")

    health_report = build_health_report(
        budget=budget,
        retirement=retirement,
        networth=networth,
        tax=st.session_state.get("dashboard_tax"),
        insurance=insurance,
        money_formatter=lambda value: fmt(value, decimals=0),
    )
    opportunity_report = build_opportunity_radar(
        budget=budget,
        loan=loan,
        savings=savings,
        retirement=retirement,
        networth=networth,
        tax=st.session_state.get("dashboard_tax"),
        insurance=insurance,
        money_formatter=lambda value: fmt(value, decimals=0),
    )
    stress_report = build_stress_report(
        budget=budget,
        loan=loan,
        retirement=retirement,
        networth=networth,
        money_formatter=lambda value: fmt(value, decimals=0),
    )

    action_plan = build_action_impact_plan(
        budget=budget,
        loan=loan,
        retirement=retirement,
        networth=networth,
        health_report=health_report,
        opportunity_report=opportunity_report,
        stress_report=stress_report,
        money_formatter=lambda value: fmt(value, decimals=0),
    )

    if action_plan.actions:
        for idx, action in enumerate(action_plan.actions, start=1):
            with st.container(border=True):
                cols = st.columns([4, 1, 1.8])
                with cols[0]:
                    st.caption(f"行动 {idx}")
                    st.markdown(f"**{action.title}**")
                    st.caption(f"目标：{action.current_signal} -> {action.target_signal}")
                    st.caption(action.rationale)
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
                        added = add_reminder(
                            title=f"行动回顾：{action.title}",
                            description=f"建议在 {due} 复盘：{action.current_signal} -> {action.target_signal}。",
                            due_date=due,
                            category=_reminder_category_for_page(action.page_key),
                            dedupe=True,
                        )
                        if added:
                            st.success("✅ 已写入提醒")
                        else:
                            st.info("ℹ️ 已存在相同提醒，已跳过重复添加。")

        action_done_count = sum(
            1 for action in action_plan.actions if st.session_state.get(_action_progress_key(action.key), False)
        )
        action_progress = {
            action.key: bool(st.session_state.get(_action_progress_key(action.key), False))
            for action in action_plan.actions
        }
        action_review_markdown = _build_action_review_markdown(
            action_plan.actions,
            action_progress=action_progress,
            heading="决策中枢行动闭环复盘",
        )
        st.download_button(
            "📥 导出本周行动复盘",
            data=action_review_markdown,
            file_name=f"OmniFinance_Action_Review_Decision_{_dt.date.today()}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.progress(
            action_done_count / len(action_plan.actions),
            text=f"本周完成度：{action_done_count}/{len(action_plan.actions)} 个行动",
        )
        if st.button("🔄 重置本周行动状态", key="action_reset_decision", use_container_width=True):
            for action in action_plan.actions:
                st.session_state[_action_progress_key(action.key)] = False
            st.success("✅ 已重置本周行动状态")
            st.rerun()
    else:
        st.info("请补充预算、净资产、退休等输入后查看可执行行动建议。")
else:
    st.caption("先补充基础资料后，系统会自动生成行动建议。")

# ── Tool groups ───────────────────────────────────────────
st.markdown("---")
with st.expander("查看全部工具入口", expanded=False):
    tool_groups = [
        ("基础理财", ["compound", "savings", "budget", "education"]),
        ("资产与债务", ["networth", "loan", "insurance", "debt", "realestate"]),
        ("投资分析", ["quote", "portfolio", "backtest", "rebalance", "fx"]),
        ("人生规划", ["retirement", "montecarlo", "withdrawal", "historical"]),
        ("分析工具", ["tax", "scenario", "calendar", "reminders", "currency", "calculator"]),
    ]
    for group_name, page_keys in tool_groups:
        st.markdown(f"#### {group_name}")
        cols = st.columns(3)
        for idx, page_key in enumerate(page_keys):
            page = get_page(page_key)
            with cols[idx % 3]:
                st.page_link(page.path, label=page.title, icon=page.icon, help=page.description)

st.markdown("---")
st.caption("OmniFinance 用于学习、研究和个人财务场景模拟。所有结果依赖输入假设和数据质量，请自行核验关键参数。")
