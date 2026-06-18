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


def _safe_page_link(page_key: str, *, label: str, icon: str) -> None:
    """Render a safe page link with graceful fallback for mapping errors."""
    page_obj = _PAGE_LINK_PAGES.get(page_key)
    if page_obj is not None:
        try:
            st.page_link(page_obj, label=label, icon=icon)
            return
        except Exception:
            pass

    try:
        page = get_page(page_key)
    except KeyError:
        st.caption(f"页面未注册：{page_key}")
        return
    try:
        st.page_link(page.path, label=label, icon=icon)
    except Exception:
        st.caption(f"当前环境暂不支持直接跳转：{page.title}")


# ── 注入核心主题 ───────────────────────────────────────
inject_theme()

# ── 侧边栏全局设置与品牌信息 ────────────────────────────
import os

_PAGE_LINK_PAGES: dict[str, st.Page] = {}

if os.path.exists("assets/logo.png"):
    st.logo("assets/logo.png", link="https://github.com/hantrleko")

with st.sidebar:
    # ── 全局设置 ─────────────────────────────────────
    st.markdown("**⚙️ 全局设置**")
    _setting_col1, _setting_col2 = st.columns([3, 2])
    with _setting_col1:
        currency_selector()
    with _setting_col2:
        st.toggle(
            "🌙 深色",
            value=st.session_state["global_dark_mode"],
            key="dark_mode_toggle",
            on_change=update_dark_mode,
            help="切换深色 / 浅色模式",
        )

    # Language selector (i18n)
    from core.i18n import locale_selector
    locale_selector()

    # Personal profile widget
    from core.profile import profile_sidebar_widget
    profile_sidebar_widget()

    # ── 全局搜索 ─────────────────────────────────────
    st.markdown("---")
    search_query = st.text_input(
        "🔍 搜索功能",
        placeholder="退休 / ETF / 记账…",
        key="_global_search",
        label_visibility="collapsed",
    )
    if search_query:
        results = search_pages(search_query, recent_keys=get_recent_pages(st.session_state))
        if results:
            st.caption(f"找到 {len(results)} 个工具：")
            for page in results:
                _safe_page_link(page.key, label=page.title, icon=page.icon)
        else:
            st.caption("未找到，试试其他关键词。")

    # ── 最近访问 ─────────────────────────────────────
    recent_page_keys = get_recent_pages(st.session_state)
    if recent_page_keys:
        st.markdown("---")
        st.markdown("**🕘 最近访问**")
        for key in recent_page_keys[:3]:
            try:
                visited_page = get_page(key)
            except KeyError:
                continue
            _safe_page_link(visited_page.key, label=visited_page.title, icon=visited_page.icon)

    # ── 主线进度 ─────────────────────────────────────
    st.markdown("---")
    journey_snapshot = get_product_journey_snapshot(st.session_state)
    journey_done, journey_total = journey_snapshot.completed, journey_snapshot.total
    _ratio = journey_snapshot.completion_ratio
    st.markdown("**🧭 主线进度**")
    st.progress(_ratio, text=f"{journey_done}/{journey_total} · {_ratio:.0%}")

    next_step = get_next_journey_step(st.session_state)
    if next_step:
        next_page = get_page(next_step.page_key)
        with st.container(border=True):
            st.caption(f"下一步：{next_step.label}（约 {next_step.minutes} 分钟）")
            _safe_page_link(next_step.page_key, label=f"继续：{next_page.title}", icon=next_page.icon)
        if journey_snapshot.pending_count <= 2:
            st.caption("🎯 只差最后几步即可完成主线！")
    else:
        st.success("🎉 主线已完成！")
        decision_page = get_page("decision")
        _safe_page_link(decision_page.key, label="前往决策中枢", icon=decision_page.icon)

    # ── 到期提醒 ─────────────────────────────────────
    due_reminders = get_due_reminders()
    if due_reminders:
        st.markdown("---")
        st.markdown(f"**⏰ 到期提醒** `{len(due_reminders)}`")
        for reminder in due_reminders[:2]:
            with st.container(border=True):
                st.caption(f"📌 {reminder.get('title', '未命名')}")
                st.caption(f"到期：{reminder.get('due_date', '-')}")
        reminder_page = get_page("reminders")
        _safe_page_link(reminder_page.key, label="查看全部提醒", icon=reminder_page.icon)

    # ── 常用场景 ─────────────────────────────────────
    st.markdown("---")
    st.markdown("**⚡ 常用场景**")
    for key in ("budget", "networth", "retirement", "loan", "insurance"):
        key_page = get_page(key)
        _safe_page_link(key_page.key, label=key_page.title, icon=key_page.icon)

    # ── 系统状态（折叠） ──────────────────────────────
    st.markdown("---")
    _runtime_report = _cached_runtime_report()
    _runtime_icons = {"ok": "✅", "warning": "⚠️", "error": "❌"}
    with st.expander(
        f"{_runtime_icons[_runtime_report.status]} 系统状态",
        expanded=_runtime_report.status == "error",
    ):
        for check in _runtime_report.checks:
            st.caption(f"{_runtime_icons[check.status]} {check.label}：{check.message}")
            if check.hint and check.status != "ok":
                st.caption(f"  ↳ {check.hint}")

    # ── 品牌区 ───────────────────────────────────────
    st.markdown("---")
    st.page_link("https://financial-analysis-agent-eugenefinance02.streamlit.app/", label="Fin-Analysis Agent", icon="🤖")
    st.page_link("https://github.com/hantrleko?tab=repositories", label="GitHub 开源生态", icon="🐙")
    st.caption(f"OmniFinance {VERSION} · Eugene Finance")

# ── 模块分类与导航路由 (v2.2.0) ─────────────────────────
_navigation_categories = pages_by_category()
_navigation_pages: dict[str, list[st.Page]] = {}
for _category, _pages in _navigation_categories.items():
    _navigation_pages[_category] = []
    for _page in _pages:
        _page_link_obj = st.Page(_page.path, title=_page.title, icon=_page.icon, default=_page.default)
        _navigation_pages[_category].append(_page_link_obj)
        _PAGE_LINK_PAGES[_page.key] = _page_link_obj


pg = st.navigation(_navigation_pages)

pg.run()
