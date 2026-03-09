import streamlit as st

VERSION = "v1.2"

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

with st.expander("🆕 最近更新（v1.2）", expanded=True):
    st.markdown("""
**v1.2 新功能**
- 🌍 **多货币支持**：所有工具可切换 ¥ / $ / € / £ / HK$ 等货币单位。
- 📈 **多策略回测**：回测器新增 RSI、MACD、布林带策略，支持策略对比分析。
- 📊 **K线图 & 技术指标**：实时报价面板新增蜡烛图、成交量、MA/VWAP 叠加。
- 💾 **方案管理**：各工具均支持保存/加载/删除参数方案，方便对比不同情景。
- 🔗 **跨模块联动**：首页仪表盘汇总各工具关键指标，一览财务全貌。
- ⭐ **自选股收藏夹**：报价面板支持保存和切换多组自选股列表。

**v1.1 回顾**
- 回测器手续费/滑点参数、贷款提前还款模拟、一页结论卡片、CI 自动化测试。
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
        cols[0].metric("💰 复利终值", f"¥{dash_compound['final_balance']:,.0f}")
        cols[0].caption(f"累计收益 ¥{dash_compound['total_interest']:,.0f}")

    if dash_loan:
        cols[1].metric("🏦 贷款总利息", f"¥{dash_loan['total_interest']:,.0f}")
        cols[1].caption(f"每期还款 ¥{dash_loan['monthly_payment']:,.0f}")

    if dash_savings:
        months = dash_savings["months_needed"]
        y, m = months // 12, months % 12
        cols[2].metric("🎯 储蓄达成", f"{y}年{m}个月")
        cols[2].caption(f"复利贡献 ¥{dash_savings['total_interest']:,.0f}")

    if dash_budget:
        cols[3].metric("💡 月储蓄额", f"¥{dash_budget['amt_save']:,.0f}")
        cols[3].caption(f"储蓄率 {dash_budget['pct_save']}%")

    if dash_retirement:
        gap = dash_retirement["gap"]
        if gap <= 0:
            cols[4].metric("🏖️ 退休评估", "✅ 已充足")
        else:
            cols[4].metric("🏖️ 退休缺口", f"¥{gap:,.0f}")
            cols[4].caption(f"需额外月存 ¥{dash_retirement['extra_monthly']:,.0f}")

    if dash_insurance:
        cols[5].metric("🛡️ 保险总保费", f"¥{dash_insurance['total_premium']:,.0f}")
        cols[5].caption(f"保单 IRR {dash_insurance['irr_pct']:.2f}%")

    st.caption("💡 提示：使用各工具后，仪表盘数据会自动更新。")
else:
    st.info("👆 请先使用左侧工具进行计算，仪表盘将自动汇总各工具的关键指标。")

st.markdown("---")
st.caption("***构建您的智能化个人理财体系***")
