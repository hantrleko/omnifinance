# 更新日志 (Changelog)

所有关于 OmniFinance 的显著更改都将记录在此文件中。

本项目遵循 [语义化版本控制 (Semantic Versioning)](https://semver.org/spec/v2.0.0.html)。

---

## [Unreleased]

### Added
- **市场数据缓存层 (`core/market_cache.py`)**：新增两级缓存（内存 LRU + 磁盘 Parquet/JSON），彻底消除 `yfinance` 的重复网络请求，大幅提升页面加载速度。
- **账单导入功能 (`core/ledger_import.py`)**：收支记账本现支持导入支付宝、微信支付及通用 CSV 格式的账单，并内置去重逻辑。
- **储蓄进度环 (`home.py`)**：仪表盘首页新增主目标环形进度图与多目标汇总进度条。
- **金融科普侧边栏 (`core/glossary.py`)**：为 6 个核心工具页面提供上下文感知的金融术语解释（共 35 个术语）。
- **统一页面初始化 (`core/page_setup.py`)**：新增 `init_page()` 辅助函数，替代各页面中重复的样板代码。
- **统一存储抽象 (`core/storage.py`)**：新增 `load_document` / `save_document` API，统一 JSON 数据持久化。
- **UI/UX 设计 Token 系统 (`core/theme.py`)**：引入语义化颜色变量，替代硬编码的十六进制值。
- **图表主题配置 (`core/chart_config.py`)**：新增 `apply_chart_config()`，统一所有 Plotly 图表的颜色序列与工具栏。

### Changed
- **代码结构下沉**：将护城河评分器与资产再平衡模拟器中的纯计算逻辑分别下沉至 `core/moat.py` 和 `core/rebalance.py`。
- **首页布局重构**：优化 Hero 标题，精简报告区文案，替换所有硬编码颜色。
- **侧边栏 UX 优化**：精简全局设置区，将系统状态移至底部折叠面板。

### Fixed
- 修复 `.devcontainer/devcontainer.json` 中遗留的错误路径。
- 统一了各页面的“暂无数据”空状态样式（`render_empty_state()`）。

---

## [2.3.0] - 2024-06-17

### Added
- 初始多页面架构搭建完成，包含 29 个 Streamlit 页面。
- 实现了“财务诊断 → 机会识别 → 压力测试 → 行动计划”的核心工作流。
- 集成了 `pytest` 单元测试与 GitHub Actions CI 流水线。
