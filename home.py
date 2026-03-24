import streamlit as st
from core.currency import get_symbol, fmt

VERSION = "v1.8.3"

st.title(f"🌟 全能理财家 (OmniFinance) `{VERSION}`")
st.markdown("---")

st.markdown("""
### 欢迎使用全能理财家！

这是一个集成了多项实用金融工具的统一平台。我们已经将所有子功能**按类别进行了清晰的划分**，您可以从左侧边栏的专属分类中快速找到需要的工具。

**核心功能模块导览：**
- 💰 **基础理财管理**：计算投资复利收益、规划储蓄路径、50/30/20 预算分配建议。
- ⚖️ **资产与债务管理**：全局跟踪资产负债净值、计算贷款本息明细、评估储蓄型保单回报率。
- 📈 **投资分析引擎**：查看全球实时行情、自动化策略回测对比、马科维茨投资组合均值-方差优化。
- 🏖️ **高级人生规划**：精准估算退休缺口、蒙特卡洛随机概率模拟防范退休破产危机。
""")

with st.expander("✨ 全新导航架构（v1.8.3）", expanded=True):
    st.markdown("""
**v1.8.3 模块化侧边栏与导航体验升级**

📌 **分类导航重构**
- 彻底抛弃了原生按文件名排序的单一冗长列表，启用了带有原生类别分组的全新侧边栏导航引擎。
- 首页名称从原有的`app`名变更为更正式的“仪表盘首页”。
- 所有子功能现已归入【基础理财管理】、【资产与债务管理】、【投资分析引擎】及【高级人生规划】四大明确的功能域中，层级更加直观清晰，极大地提升了应用专业度和使用体验。
""")

with st.expander("✨ 闪耀升级（v1.8.2）"):
    st.markdown("""
**v1.8 - 1.8.2 Premium 视觉与体验重构**

💎 **全新 Glassmorphism (玻璃拟态) 设计**
- 全局引入现代字体（Inter），排版更加优雅、专业。
- 指标卡片、折叠面板与模块均采用毛玻璃半透明材质，配以微妙的光影边框。

🌟 **动态交互与微动画**
- 为卡片与按钮增加了平滑的上浮（Hover）微动画与发光阴影特效，让界面更具沉浸感和生命力。
- 全面优化了亮色/深色模式的对比度，提供商业级数据看板的视觉体验。

🚀 **UI 无缝部署与交互修复**
- 全新视觉方案已同步至 11 个核心工具包。
- 修复侧边栏图文在深色模式下的对比度和不可见问题。
- 彻底解决多页面跳转时深浅色主题状态不持久化的 Bug。
- 修复因全局字体覆盖导致的系统自带图标（如键盘、方向箭头等）变为文本乱码的问题。
""")

with st.expander("📋 v1.7 及更早版本说明"):
    st.markdown("""
- **v1.7**: 新增蒙特卡洛模拟与马科维茨投资组合优化器模块，增强错误捕捉，支持 Excel 全面导出。
- **v1.6**: 并发与架构优化（涵盖 API 异步请求与多进程回测机制）。
- **v1.5**: 新增资产净值追踪，全局支持方案保存与状态联动。
- **v1.4**: 核心解耦，全面强化并发数据缓存机制。
- **v1.1 ~ v1.3**: 提供多货币支持，技术面板指标扩建，保险计算引擎迭代。
""")

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

has_data = any([dash_compound, dash_loan, dash_savings, dash_budget, dash_retirement, dash_insurance, dash_networth])

if has_data:
    cols = st.columns(7)

    if dash_compound:
        cols[0].metric("💰 复利终值", fmt(dash_compound['final_balance'], decimals=0))
        cols[0].caption(f"累计收益 {fmt(dash_compound['total_interest'], decimals=0)}")

    if dash_loan:
        cols[1].metric("🏦 贷款总利息", fmt(dash_loan['total_interest'], decimals=0))
        cols[1].caption(f"每期还款 {fmt(dash_loan['monthly_payment'], decimals=0)}")

    if dash_savings:
        months = dash_savings["months_needed"]
        y, m = months // 12, months % 12
        cols[2].metric("🎯 储蓄达成", f"{y}年{m}个月")
        cols[2].caption(f"复利贡献 {fmt(dash_savings['total_interest'], decimals=0)}")

    if dash_budget:
        cols[3].metric("💡 月储蓄额", fmt(dash_budget['amt_save'], decimals=0))
        cols[3].caption(f"储蓄率 {dash_budget['pct_save']}%")

    if dash_retirement:
        gap = dash_retirement["gap"]
        if gap <= 0:
            cols[4].metric("🏖️ 退休评估", "✅ 已充足")
        else:
            cols[4].metric("🏖️ 退休缺口", fmt(gap, decimals=0))
            cols[4].caption(f"需额外月存 {fmt(dash_retirement['extra_monthly'], decimals=0)}")

    if dash_insurance:
        cols[5].metric("🛡️ 保险总保费", fmt(dash_insurance['total_premium'], decimals=0))
        cols[5].caption(f"保单 IRR {dash_insurance['irr_pct']:.2f}%")

    if dash_networth:
        cols[6].metric("🏠 净资产", fmt(dash_networth['net_worth'], decimals=0))
        cols[6].caption(f"资产 {fmt(dash_networth['total_assets'], decimals=0)}")

    st.caption("💡 提示：使用各工具后，仪表盘数据会自动更新。")
else:
    st.info("👆 请先使用左侧工具进行计算，仪表盘将自动汇总各工具的关键指标。")

st.markdown("---")
st.caption("***构建您的智能化个人理财体系***")
