import streamlit as st

st.set_page_config(
    page_title="全能理财家 (OmniFinance)",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌟 全能理财家 (OmniFinance) `v1.0`")
st.markdown("---")

st.markdown("""
### 欢迎使用全能理财家！

这是一个集成了多项实用金融工具的统一平台。请从左侧边栏选择您需要使用的功能：

1. **💰 1_复利计算器**：计算投资复利收益
2. **📊 2_实时报价面板**：查看股票实时数据
3. **📈 3_MA交叉回测器**：测试均线交易策略
4. **🏦 4_贷款计算器**：计算贷款本息
5. **🎯 5_储蓄目标计算器**：规划储蓄达成路径
6. **💡 6_预算分配建议器**：50/30/20 预算分配法则
7. **🏖️ 7_退休金估算器**：预估退休生活需求

---
***构建您的智能化个人理财体系***
""")
