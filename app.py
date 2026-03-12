import streamlit as st

from core.currency import get_symbol

VERSION = "v1.4"

st.set_page_config(
    page_title="全能理财家 (OmniFinance)",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title(f"🌟 全能理财家 (OmniFinance) `{VERSION}`")
st.markdown("---")

st.markdown("""
### 欢迎使用全能理财家！

这是一个集成了多项实用金融工具的统一平台。请从左侧边栏选择您需要使用的功能：

1. **💰 1_复利计算器**：计算投资复利收益
2. **📊 2_实时报价面板**：查看实时行情 & K线图
3. **📈 3_策略回测器**：多策略回测（MA / RSI / MACD / 布林带）
4. **🏦 4_贷款计算器**：计算贷款本息
5. **🎯 5_储蓄目标计算器**：规划储蓄达成路径
6. **💡 6_预算分配建议器**：50/30/20 预算分配法则
7. **🏖️ 7_退休金估算器**：预估退休生活需求
8. **🛡️ 8_保险产品测算器**：评估保费效率与储蓄型保单 IRR
""")

with st.expander("🆕 最近更新（v1.4）", expanded=True):
    st.markdown("""
**v1.4 工程优化与全面升级**

🔧 **P0 核心修复**
- 🏗️ 退休金 & 储蓄目标核心计算逻辑下沉到 `core/retirement.py` / `core/savings.py`，页面仅负责 UI 展示，可测试性大幅提升。
- 📊 K 线图历史数据加入 `@st.cache_data(ttl=300)` 缓存，切换标的不再重复下载，速度提升显著。
- 💱 修复所有图表 `hovertemplate` 中硬编码 `¥` 的问题，现在切换货币后图表 Tooltip 也会同步更新。

⚡ **P1 性能与功能增强**
- 🚀 回测器 `simulate_trades()` 改用向量化 pandas 操作（去除 iterrows 逐行循环），回测速度大幅提升。
- 📐 回测器新增**索提诺比率**（Sortino）与**卡玛比率**（Calmar）两项风险调整指标。
- 🔄 策略对比 expander 改用 `@st.cache_data` 缓存，避免每次渲染重复计算四个策略。
- 💾 `storage.py` 加入 schema_version 版本控制与自动迁移，旧方案文件向前兼容。
- 🛡️ 保险测算器大幅强化：新增一页结论分析、通胀侵蚀警示、替代投资差距指标、CSV 导出功能。
- 📐 抽出通用 `core/chart_config.py`，消除 5 个页面中重复的 `LAYOUT_DARK` 定义。

🎨 **P2 体验优化**
- 🌐 首页仪表盘货币符号改为动态引用，切换货币后首页指标同步更新。
- ❌ 报价面板新增分级错误提示：网络异常 / 代码无效 / 限流，用户可快速定位问题。
""")

with st.expander("📋 v1.3 更新记录"):
    st.markdown("""
- 🛡️ **保险产品测算器**：新增保险保费效率、通胀折现保额、保单 IRR 与替代投资对比分析。
""")

with st.expander("📋 v1.2 更新记录"):
    st.markdown("""
- 🌍 **多货币支持**：所有工具可切换 ¥ / $ / € / £ / HK$ 等货币单位。
- 📈 **多策略回测**：回测器新增 RSI、MACD、布林带策略，支持策略对比分析。
- 📊 **K线图 & 技术指标**：实时报价面板新增蜡烛图、成交量、MA/VWAP 叠加。
- 💾 **方案管理**：各工具均支持保存/加载/删除参数方案，方便对比不同情景。
- 🔗 **跨模块联动**：首页仪表盘汇总各工具关键指标，一览财务全貌。
- ⭐ **自选股收藏夹**：报价面板支持保存和切换多组自选股列表。
""")

with st.expander("📋 v1.1 更新记录"):
    st.markdown("""
- 回测器新增手续费/滑点参数，结果更贴近真实交易。
- 贷款计算器新增提前还款模拟，可比较利息与期数变化。
- 储蓄目标与退休金页面新增一页结论卡片。
- 工程结构升级：核心计算抽离到 `core/`，并增加自动化测试与 CI。
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

has_data = any([dash_compound, dash_loan, dash_savings, dash_budget, dash_retirement, dash_insurance])

if has_data:
    cols = st.columns(6)

    if dash_compound:
        cols[0].metric("💰 复利终值", f"{sym}{dash_compound['final_balance']:,.0f}")
        cols[0].caption(f"累计收益 {sym}{dash_compound['total_interest']:,.0f}")

    if dash_loan:
        cols[1].metric("🏦 贷款总利息", f"{sym}{dash_loan['total_interest']:,.0f}")
        cols[1].caption(f"每期还款 {sym}{dash_loan['monthly_payment']:,.0f}")

    if dash_savings:
        months = dash_savings["months_needed"]
        y, m = months // 12, months % 12
        cols[2].metric("🎯 储蓄达成", f"{y}年{m}个月")
        cols[2].caption(f"复利贡献 {sym}{dash_savings['total_interest']:,.0f}")

    if dash_budget:
        cols[3].metric("💡 月储蓄额", f"{sym}{dash_budget['amt_save']:,.0f}")
        cols[3].caption(f"储蓄率 {dash_budget['pct_save']}%")

    if dash_retirement:
        gap = dash_retirement["gap"]
        if gap <= 0:
            cols[4].metric("🏖️ 退休评估", "✅ 已充足")
        else:
            cols[4].metric("🏖️ 退休缺口", f"{sym}{gap:,.0f}")
            cols[4].caption(f"需额外月存 {sym}{dash_retirement['extra_monthly']:,.0f}")

    if dash_insurance:
        cols[5].metric("🛡️ 保险总保费", f"{sym}{dash_insurance['total_premium']:,.0f}")
        cols[5].caption(f"保单 IRR {dash_insurance['irr_pct']:.2f}%")

    st.caption("💡 提示：使用各工具后，仪表盘数据会自动更新。")
else:
    st.info("👆 请先使用左侧工具进行计算，仪表盘将自动汇总各工具的关键指标。")

st.markdown("---")
st.caption("***构建您的智能化个人理财体系***")
