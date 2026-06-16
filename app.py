import streamlit as st

from core.currency import currency_selector
from core.reminders import get_due_reminders, get_reminders
from core.navigation import (
    get_recent_pages,
    get_next_journey_step,
    get_page,
    get_product_journey_snapshot,
    pages_by_category,
    search_pages,
)
from core.runtime_checks import build_runtime_report, runtime_fingerprint
from core.theme import inject_theme, load_dark_mode_pref, save_dark_mode_pref
from core.version import VERSION

# ── 页面基础配置 ───────────────────────────────────────
st.set_page_config(
    page_title="全能理财家 (OmniFinance)",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局状态持久化 ───────────────────────────────────────
if "global_dark_mode" not in st.session_state:
    st.session_state["global_dark_mode"] = load_dark_mode_pref()


@st.cache_data(ttl=300, show_spinner=False)
def _cached_runtime_report():
    return build_runtime_report()


def update_dark_mode():
    val = st.session_state["dark_mode_toggle"]
    st.session_state["global_dark_mode"] = val
    save_dark_mode_pref(val)

# ── 注入核心主题 ───────────────────────────────────────
inject_theme()

# ── 侧边栏全局设置与品牌信息 ────────────────────────────
import os

if os.path.exists("assets/logo.png"):
    st.logo("assets/logo.png", link="https://github.com/hantrleko")

with st.sidebar:
    st.header("⚙️ 全局设置")
    currency_selector()
    st.toggle("🌙 深色模式", value=st.session_state["global_dark_mode"], key="dark_mode_toggle", on_change=update_dark_mode)

    # Language selector (i18n)
    from core.i18n import locale_selector
    locale_selector()

    # Personal profile widget
    from core.profile import profile_sidebar_widget
    profile_sidebar_widget()

    # Runtime health panel
    _runtime_report = _cached_runtime_report()
    _runtime_icons = {"ok": "✅", "warning": "⚠️", "error": "❌"}
    st.markdown("---")
    with st.expander(
        f"{_runtime_icons[_runtime_report.status]} 系统状态 · {_runtime_report.summary}",
        expanded=_runtime_report.status == "error",
    ):
        for check in _runtime_report.checks:
            st.markdown(f"- {_runtime_icons[check.status]} **{check.label}**：{check.message}")
            if check.hint and check.status != "ok":
                st.caption(check.hint)
        st.code(runtime_fingerprint(_runtime_report), language="text")

    # Global search
    st.markdown("---")
    search_query = st.text_input("🔍 快速搜索功能", placeholder="输入功能/关键词，如：退休、ETF、记账…", key="_global_search")
    recent_page_keys = get_recent_pages(st.session_state)
    if search_query:
        results = search_pages(search_query, recent_keys=recent_page_keys)
        if results:
            st.caption(f"找到 {len(results)} 个相关工具，点击即可跳转：")
            for page in results:
                st.page_link(page.path, label=page.title, icon=page.icon, help=page.description)
        else:
            st.caption("未找到匹配功能，试试输入类别或英文关键词。")

    st.markdown("---")
    recent_page_keys = get_recent_pages(st.session_state)
    if recent_page_keys:
        st.markdown("### 🕘 最近访问")
        for key in recent_page_keys[:3]:
            try:
                visited_page = get_page(key)
            except KeyError:
                continue
            st.page_link(visited_page.path, label=f"↩ {visited_page.title}", icon=visited_page.icon)
    else:
        st.caption("首次访问先从左侧主线/搜索开始吧。")

    st.markdown("---")
    journey_snapshot = get_product_journey_snapshot(st.session_state)
    journey_done, journey_total = journey_snapshot.completed, journey_snapshot.total
    st.markdown("### 🧭 本次会话进度")
    progress_cols = st.columns(3)
    with progress_cols[0]:
        st.metric("已完成", f"{journey_done}", delta=f"待补 {journey_snapshot.pending_count}")
    with progress_cols[1]:
        st.metric("主线进度", f"{journey_done}/{journey_total}")
    with progress_cols[2]:
        st.metric("完成率", f"{journey_snapshot.completion_ratio:.0%}")
    st.progress(journey_snapshot.completion_ratio)

    next_step = get_next_journey_step(st.session_state)
    if next_step:
        next_page = get_page(next_step.page_key)
        with st.container(border=True):
            st.caption(f"下一步：{next_step.label}（约 {next_step.minutes} 分钟）")
            st.caption(next_step.outcome_hint)
            st.page_link(next_page.path, label=f"继续：{next_page.title}", icon=next_page.icon)
        if journey_snapshot.pending_count <= 2:
            st.caption("只差最后几步即可进入完整决策闭环。")
    else:
        st.success("✅ 核心主线已填完，可直接查看“决策中枢”与首页的完整建议。")
        decision_page = get_page("decision")
        st.page_link(decision_page.path, label="前往决策中枢", icon=decision_page.icon)

    st.markdown("---")
    st.markdown("### ⏰ 提醒预览")
    due_reminders = get_due_reminders()
    all_reminders = get_reminders()
    if due_reminders:
        for reminder in due_reminders[:3]:
            due_date = reminder.get("due_date", "-")
            st.caption(f"⚠️ {reminder.get('title', '未命名提醒')}（{due_date}）")
            st.caption(f"{reminder.get('description', '暂无说明')}")
    else:
        if all_reminders:
            st.caption("当前无到期提醒，先留意明细提醒。")
        else:
            st.caption("暂无提醒，建议先在“财务提醒管理”创建。")
    reminder_page = get_page("reminders")
    st.page_link(reminder_page.path, label="打开提醒管理", icon=reminder_page.icon)

    st.markdown("---")
    st.markdown("### ⚡ 常用场景")
    for key in ("budget", "networth", "retirement", "loan", "insurance"):
        with st.container():
            key_page = get_page(key)
            st.page_link(key_page.path, label=key_page.title, icon=key_page.icon)

    st.markdown("---")
    st.markdown("### Eugene Finance")
    st.caption("✨ *Empower Your Knowledge, Enrich Your Life.*")
    st.markdown("🔗 **旗下服务矩阵**")
    st.page_link("https://financial-analysis-agent-eugenefinance02.streamlit.app/", label="Fin-Analysis", icon="🤖")
    st.page_link("https://github.com/hantrleko?tab=repositories", label="GitHub 开源生态", icon="🐙")
    st.caption(f"OmniFinance {VERSION}")

# ── 模块分类与导航路由 (v2.2.0) ─────────────────────────
pg = st.navigation({
    category: [st.Page(page.path, title=page.title, icon=page.icon, default=page.default) for page in pages]
    for category, pages in pages_by_category().items()
})

pg.run()
