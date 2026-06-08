import streamlit as st

from core.currency import currency_selector
from core.navigation import pages_by_category, search_pages
from core.theme import inject_theme, load_dark_mode_pref, save_dark_mode_pref

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

    # Global search
    st.markdown("---")
    search_query = st.text_input("🔍 快速搜索功能", placeholder="输入功能/关键词，如：退休、ETF、记账…", key="_global_search")
    if search_query:
        results = search_pages(search_query)
        if results:
            st.caption(f"找到 {len(results)} 个相关工具，点击即可跳转：")
            for page in results:
                st.page_link(page.path, label=page.title, icon=page.icon, help=page.description)
        else:
            st.caption("未找到匹配功能，试试输入类别或英文关键词。")

    st.markdown("---")
    st.markdown("### Eugene Finance")
    st.caption("✨ *Empower Your Knowledge, Enrich Your Life.*")
    st.markdown("🔗 **旗下服务矩阵**")
    st.page_link("https://financial-analysis-agent-eugenefinance02.streamlit.app/", label="Fin-Analysis", icon="🤖")
    st.page_link("https://github.com/hantrleko?tab=repositories", label="GitHub 开源生态", icon="🐙")
    from core.theme import VERSION as _VER
    st.caption(f"OmniFinance {_VER}")

# ── 模块分类与导航路由 (v2.0.0) ─────────────────────────
pg = st.navigation({
    category: [st.Page(page.path, title=page.title, icon=page.icon, default=page.default) for page in pages]
    for category, pages in pages_by_category().items()
})

pg.run()
