import streamlit as st

from core.currency import fmt
from core.navigation import DASHBOARD_PROGRESS_ITEMS, get_page
from core.version import VERSION

st.title(f"🧭 OmniFinance 决策中枢 `{VERSION}`")
st.caption("把个人财务输入转化为健康诊断、机会识别、压力测试和行动计划。")

st.info(
    "建议先完成预算、净资产和退休三个基础输入。完成后，首页会自动汇总关键指标，生成财务健康评分、机会雷达、压力测试和行动计划。"
)

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
    (_item.label, _item.session_key, _item.page_key, _item.ready_hint, _item.pending_hint)
    for _item in DASHBOARD_PROGRESS_ITEMS
]
completed = sum(1 for _, key, _, _, _ in _status_items if st.session_state.get(key))
completion_ratio = completed / len(_status_items)

st.progress(completion_ratio, text=f"已完成 {completed}/{len(_status_items)} 项基础资料")

status_cols = st.columns(3)
for idx, (label, key, page_key, ready_hint, pending_hint) in enumerate(_status_items):
    page = get_page(page_key)
    done = bool(st.session_state.get(key))
    with status_cols[idx % 3].container(border=True):
        st.markdown(f"{'✅' if done else '⬜'} **{label}**")
        st.caption(ready_hint if done else pending_hint)
        st.page_link(page.path, label=f"打开{page.title}", icon=page.icon)

# ── Recommended starter path ──────────────────────────────
st.markdown("---")
st.markdown("### 3. 推荐初始化路径")
st.caption("第一次使用时，不要从几十个工具里随便点。先按下面顺序完成基础资料，首页的综合分析会更有价值。")

starter_steps = [
    ("第一步", "budget", "确认收入、支出和可储蓄金额"),
    ("第二步", "networth", "建立资产、负债和净资产基线"),
    ("第三步", "retirement", "估算长期退休缺口与月度补充额"),
    ("第四步", "home", "回到首页查看健康评分、机会雷达和行动计划"),
]

starter_cols = st.columns(4)
for col, (step, page_key, reason) in zip(starter_cols, starter_steps, strict=True):
    page = get_page(page_key)
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
