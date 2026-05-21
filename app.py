import streamlit as st

from core.currency import currency_selector
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
    search_query = st.text_input("🔍 快速搜索功能", placeholder="输入功能名称…", key="_global_search")
    if search_query:
        _all_pages = {
            "复利计算器": "pages/1_复利计算器.py",
            "实时报价面板": "pages/2_实时报价面板.py",
            "MA交叉回测器": "pages/3_MA交叉回测器.py",
            "贷款计算器": "pages/4_贷款计算器.py",
            "储蓄目标计算器": "pages/5_储蓄目标计算器.py",
            "预算分配建议器": "pages/6_预算分配建议器.py",
            "退休金估算器": "pages/7_退休金估算器.py",
            "保险产品测算器": "pages/8_保险产品测算器.py",
            "资产净值追踪器": "pages/9_资产净值追踪器.py",
            "蒙特卡洛模拟": "pages/10_蒙特卡洛模拟.py",
            "投资组合优化器": "pages/11_投资组合优化器.py",
            "税务计算器": "pages/12_税务计算器.py",
            "债务还清规划器": "pages/13_债务还清规划器.py",
            "教育基金规划器": "pages/14_教育基金规划器.py",
            "房产投资分析器": "pages/15_房产投资分析器.py",
            "外汇对冲计算器": "pages/16_外汇对冲计算器.py",
            "资产再平衡模拟器": "pages/17_资产再平衡模拟器.py",
            "场景对比分析器": "pages/18_场景对比分析器.py",
            "历史回测储蓄模拟": "pages/19_历史回测储蓄模拟.py",
            "税务优化提款策略": "pages/20_税务优化提款策略.py",
            "财务日历": "pages/21_财务日历.py",
            "财务提醒管理": "pages/22_财务提醒管理.py",
            "货币转换器": "pages/23_货币转换器.py",
            "科学金融计算器": "pages/24_科学金融计算器.py",
            "财务日记": "pages/25_财务日记.py",
            "股票筛选器": "pages/26_股票筛选器.py",
            "收支记账本": "pages/27_收支记账本.py",
        }
        results = [name for name in _all_pages if search_query in name]
        if results:
            for r in results:
                st.caption(f"📄 {r}")
        else:
            st.caption("未找到匹配功能")

    st.markdown("---")
    st.markdown("### Eugene Finance")
    st.caption("✨ *Empower Your Knowledge, Enrich Your Life.*")
    st.markdown("🔗 **旗下服务矩阵**")
    st.page_link("https://financial-analysis-agent-eugenefinance02.streamlit.app/", label="Fin-Analysis", icon="🤖")
    st.page_link("https://github.com/hantrleko?tab=repositories", label="GitHub 开源生态", icon="🐙")
    from core.theme import VERSION as _VER
    st.caption(f"OmniFinance {_VER}")

# ── 模块分类与导航路由 (v2.0.0) ─────────────────────────
p_home = st.Page("home.py", title="仪表盘首页", icon="🏠", default=True)

# 基础理财管理
p_compound = st.Page("pages/1_复利计算器.py", title="复利计算器", icon="💰")
p_savings = st.Page("pages/5_储蓄目标计算器.py", title="储蓄目标计算器", icon="🎯")
p_budget = st.Page("pages/6_预算分配建议器.py", title="预算分配建议器", icon="💡")
p_education = st.Page("pages/14_教育基金规划器.py", title="教育基金规划器", icon="🏫")

# 资产与债务管理
p_networth = st.Page("pages/9_资产净值追踪器.py", title="资产净值追踪器", icon="🏠")
p_loan = st.Page("pages/4_贷款计算器.py", title="贷款计算器", icon="🏦")
p_insurance = st.Page("pages/8_保险产品测算器.py", title="保险产品测算器", icon="🛡️")
p_debt = st.Page("pages/13_债务还清规划器.py", title="债务还清规划器", icon="💳")
p_realestate = st.Page("pages/15_房产投资分析器.py", title="房产投资分析器", icon="🏘️")

# 投资分析引擎
p_quote = st.Page("pages/2_实时报价面板.py", title="实时报价面板", icon="📊")
p_backtest = st.Page("pages/3_MA交叉回测器.py", title="策略回测器", icon="📈")
p_portfolio = st.Page("pages/11_投资组合优化器.py", title="投资组合优化器", icon="📐")
p_rebalance = st.Page("pages/17_资产再平衡模拟器.py", title="资产再平衡模拟器", icon="⚖️")
p_fx = st.Page("pages/16_外汇对冲计算器.py", title="外汇对冲计算器", icon="💱")

# 高级人生规划
p_retirement = st.Page("pages/7_退休金估算器.py", title="退休金估算器", icon="🏖️")
p_monte = st.Page("pages/10_蒙特卡洛模拟.py", title="蒙特卡洛模拟", icon="🎲")
p_withdrawal = st.Page("pages/20_税务优化提款策略.py", title="税务优化提款策略", icon="🏦")
p_historical = st.Page("pages/19_历史回测储蓄模拟.py", title="历史回测储蓄模拟", icon="📜")
p_diary = st.Page("pages/25_财务日记.py", title="财务日记", icon="📔")

# 分析与工具
p_tax = st.Page("pages/12_税务计算器.py", title="税务计算器", icon="🧾")
p_scenario = st.Page("pages/18_场景对比分析器.py", title="场景对比分析器", icon="🔬")
p_calendar = st.Page("pages/21_财务日历.py", title="财务日历", icon="📅")
p_reminders = st.Page("pages/22_财务提醒管理.py", title="财务提醒管理", icon="🔔")
p_currency = st.Page("pages/23_货币转换器.py", title="货币转换器", icon="💱")
p_calculator = st.Page("pages/24_科学金融计算器.py", title="科学金融计算器", icon="🧮")

# 高级工具 (v2.0)
p_screener = st.Page("pages/26_股票筛选器.py", title="股票筛选器", icon="🔎")
p_ledger = st.Page("pages/27_收支记账本.py", title="收支记账本", icon="📒")

pg = st.navigation({
    "平台概览": [p_home],
    "基础理财管理": [p_compound, p_savings, p_budget, p_education],
    "资产与债务管理": [p_networth, p_loan, p_insurance, p_debt, p_realestate],
    "投资分析引擎": [p_quote, p_portfolio, p_backtest, p_rebalance, p_fx],
    "高级人生规划": [p_retirement, p_monte, p_withdrawal, p_historical, p_diary],
    "分析与工具": [p_tax, p_scenario, p_calendar, p_reminders, p_currency, p_calculator],
    "高级工具 (v2.0)": [p_screener, p_ledger],
})

pg.run()
