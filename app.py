import streamlit as st
from core.theme import inject_theme
from core.currency import currency_selector

# ── 页面基础配置 ───────────────────────────────────────
st.set_page_config(
    page_title="全能理财家 (OmniFinance)",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局状态持久化 ───────────────────────────────────────
if "global_dark_mode" not in st.session_state:
    st.session_state["global_dark_mode"] = True

def update_dark_mode():
    st.session_state["global_dark_mode"] = st.session_state["dark_mode_toggle"]

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
    
    st.markdown("---")
    st.markdown("### Eugene Finance")
    st.caption("✨ *Empower Your Knowledge, Enrich Your Life.*")
    st.markdown("🔗 **旗下服务矩阵**")
    st.page_link("https://financial-analysis-agent-eugenefinance02.streamlit.app/", label="Fin-Analysis", icon="🤖")
    st.page_link("https://github.com/hantrleko?tab=repositories", label="GitHub 开源生态", icon="🐙")

# ── 模块分类与导航路由 (v1.8.3) ─────────────────────────
p_home = st.Page("home.py", title="仪表盘首页", icon="🏠", default=True)

p_compound = st.Page("pages/1_复利计算器.py", title="复利计算器", icon="💰")
p_savings = st.Page("pages/5_储蓄目标计算器.py", title="储蓄目标计算器", icon="🎯")
p_budget = st.Page("pages/6_预算分配建议器.py", title="预算分配建议器", icon="💡")

p_networth = st.Page("pages/9_资产净值追踪器.py", title="资产净值追踪器", icon="🏠")
p_loan = st.Page("pages/4_贷款计算器.py", title="贷款计算器", icon="🏦")
p_insurance = st.Page("pages/8_保险产品测算器.py", title="保险产品测算器", icon="🛡️")

p_quote = st.Page("pages/2_实时报价面板.py", title="实时报价面板", icon="📊")
p_backtest = st.Page("pages/3_MA交叉回测器.py", title="策略回测器", icon="📈")
p_portfolio = st.Page("pages/11_投资组合优化器.py", title="投资组合优化器", icon="📐")

p_retirement = st.Page("pages/7_退休金估算器.py", title="退休金估算器", icon="🏖️")
p_monte = st.Page("pages/10_蒙特卡洛模拟.py", title="蒙特卡洛模拟", icon="🎲")

pg = st.navigation({
    "平台概览": [p_home],
    "基础理财管理": [p_compound, p_savings, p_budget],
    "资产与债务管理": [p_networth, p_loan, p_insurance],
    "投资分析引擎": [p_quote, p_portfolio, p_backtest],
    "高级人生规划": [p_retirement, p_monte]
})

pg.run()
