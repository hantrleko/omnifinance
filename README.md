# OmniFinance 全能理财家

[![CI](https://github.com/hantrleko/omnifinance/actions/workflows/ci.yml/badge.svg)](https://github.com/hantrleko/omnifinance/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)

OmniFinance 是一个基于 **Streamlit** 的个人财务规划与轻量级投资分析平台。本项目将预算管理、储蓄目标、债务清偿、保险规划、退休测算、投资组合优化、策略回测、压力测试和行动计划整合到一个连贯的多页面应用中。

> **核心理念**：财务状态诊断 → 风险与机会识别 → 情景模拟 → 优先行动计划 → 报告导出与复盘。

---

## 📸 功能概览 (Screenshots)

*（请将以下占位符替换为实际的项目截图）*

<details>
<summary>点击展开查看系统截图</summary>

| 仪表盘首页 | 投资组合优化器 |
|:---:|:---:|
| `<img src="assets/screenshot_home.png" width="400"/>` | `<img src="assets/screenshot_portfolio.png" width="400"/>` |
| 全局财务健康度、储蓄进度环与行动雷达 | 均值-方差有效前沿与风险收益散点图 |

| 长期护城河评分器 | 收支记账本与导入 |
|:---:|:---:|
| `<img src="assets/screenshot_moat.png" width="400"/>` | `<img src="assets/screenshot_ledger.png" width="400"/>` |
| 主客观结合的护城河评估模型与雷达图 | 支付宝/微信账单导入与收支流水追踪 |

</details>

---

## 🌟 核心功能模块

### 1. 个人财务诊断与行动闭环
- **仪表盘首页**：聚合展示财务健康评分、机会雷达、储蓄进度和 90 天优先行动计划。
- **决策中枢**：串联各项财务计算器，提供“推荐初始化路径”。
- **财务日记与提醒**：记录财务决策复盘情绪，管理定期财务提醒。
- **一键报告导出**：支持导出 Markdown / HTML 格式的财务体检报告。
- **复盘中心**：健康分历史趋势、行动状态看板（计划/进行中/完成/跳过）与月度复盘报告导出。

### 2. 基础理财与规划
- **预算与记账**：50/30/20 预算分配建议，支持**支付宝、微信支付账单 CSV 导入**。
- **储蓄与复利**：多目标储蓄计算器，复利终值与通胀敏感性测算。
- **资产与债务**：净值追踪、雪崩/雪球法债务清偿规划、等额本息贷款计算器。

### 3. 投资分析引擎 (Powered by yfinance & akshare)
- **投资组合优化**：基于马科维茨均值-方差模型，寻找最大夏普与最小方差组合。
- **策略回测与再平衡**：MA/RSI/MACD 策略回测，定期/阈值再平衡模拟。
- **市场数据缓存**：内置两级缓存（LRU 内存 + 磁盘 Parquet），极大提升页面加载与分析速度。
- **护城河评分器**：提取财务指标（ROE、毛利率等）结合主观评价生成护城河雷达图。
- **高级资产配置**：风险平价（含自定义风险预算）与 Black-Litterman 观点模型，三方案权重对比。
- **走查样本外检验**：回测器内置 Walk-Forward 验证，量化参数过拟合风险并给出稳健性诊断。

### 4. 高级人生规划
- **退休金估算**：退休资金缺口与提款寿命测算（安全提款率）。
- **蒙特卡洛模拟**：模拟数千条未来资产路径，评估退休计划或投资目标的达成概率。
- **小白科普侧边栏**：为核心页面提供上下文相关的金融概念解释（如复利、VaR、夏普比率等）。

---

## 🚀 快速开始

### 1. 环境准备

要求 **Python 3.10+**。推荐使用虚拟环境：

```bash
git clone https://github.com/hantrleko/omnifinance.git
cd omnifinance
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安装依赖

```bash
# 运行所需依赖
pip install -r requirements.txt

# 如果需要进行开发和测试
pip install -r requirements-dev.txt
```

### 3. 运行应用

```bash
streamlit run app.py
```

### 🎯 1 分钟体验路径

如果你是第一次接触 OmniFinance，推荐按这个最短路径开始：
1. 在左侧菜单进入 **🧭 决策中枢**，按“推荐初始化路径”完成基础数据录入（预算、资产、退休）。
2. 进入 **📒 收支记账本**，尝试导入一份支付宝或微信的 CSV 账单。
3. 进入 **📈 投资组合优化器**，输入几只你关注的股票代码（如 `AAPL, MSFT, GOOG`），查看有效前沿。
4. 回到 **🏠 仪表盘首页**，查看系统为你生成的财务健康评分与 90 天行动建议。

---

## 🏗️ 架构与工程化

OmniFinance 采用严格的 **逻辑与 UI 分离** 架构，确保金融计算模块的纯粹性与可测试性。

```text
omnifinance/
├── app.py                  # 应用入口与全局侧边栏配置
├── home.py                 # 仪表盘首页（数据聚合展示）
├── pages/                  # Streamlit 多页面 UI 模块（纯展示与交互）
├── core/                   # 核心引擎（纯 Python，无 Streamlit 依赖）
│   ├── market_cache.py     # 市场数据两级缓存层
│   ├── ledger_import.py    # 账单导入解析引擎
│   ├── moat.py             # 护城河计算引擎
│   ├── rebalance.py        # 资产再平衡模拟引擎
│   ├── allocation.py       # 风险平价 + Black-Litterman 配置引擎
│   ├── walkforward.py      # 走查样本外检验引擎
│   ├── review.py           # 健康分快照 / 行动追踪 / 月度复盘引擎
│   ├── storage.py          # 统一的 JSON/Parquet 磁盘存储抽象
│   └── theme.py            # 统一的 UI 设计 Token 与组件规范
├── tests/                  # 单元测试套件（覆盖 core/）
└── .github/workflows/      # CI/CD 自动化流水线
```

### 测试与代码质量

项目拥有 **450+ 条单元测试**，覆盖率良好。提交代码前请运行以下检查：

```bash
# 运行单元测试
pytest -q

# 代码格式化与规范检查
ruff check .

# 静态类型检查
mypy core --ignore-missing-imports
```

---

## 🤝 参与贡献 (Contributing)

我们非常欢迎社区贡献！无论是修复 Bug、增加新的计算器、优化 UI 还是完善文档，你的每一次 PR 都会让 OmniFinance 变得更好。

在开始编写代码前，请务必阅读我们的 [贡献指南 (CONTRIBUTING.md)](CONTRIBUTING.md)。

如果你发现了问题或有新功能的想法，请使用我们提供的 [Issue 模板](.github/ISSUE_TEMPLATE/) 提交。

---

## ⚠️ 免责声明

OmniFinance 仅用于学习、研究、个人财务模拟和软件开发展示。项目中的计算结果、图表、评分、回测、投资组合优化和行动建议均基于模型假设与用户输入，**不构成任何投资建议、理财建议、保险建议、税务建议或法律建议**。

历史收益不代表未来表现。使用者应自行核验数据，并在作出重大财务决策前咨询具备资质的专业人士。

---

## 📄 License

本项目采用 [MIT License](LICENSE) 开源协议。
