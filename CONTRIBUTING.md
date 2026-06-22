# 参与贡献 OmniFinance (Contributing Guide)

感谢你对 OmniFinance 的兴趣！无论是提交 Bug 报告、提出新功能建议，还是直接提交 Pull Request (PR)，我们都非常欢迎。

为了保证项目的代码质量和可维护性，请在贡献前花几分钟阅读以下指南。

---

## 🏗️ 架构原则 (Development Principles)

OmniFinance 已经从一个简单的 Streamlit 脚本集合，演进为具有清晰架构的工程化项目。在开发新功能时，请遵循以下核心原则：

### 1. 严格的“逻辑与 UI 分离”
- **核心计算引擎 (`core/`)**：所有的金融公式、数据处理、模拟算法和 API 请求都**必须**放在 `core/` 目录下。这里的代码应该纯粹的 Python 函数，**绝对不能**导入或依赖 `streamlit`。
- **展示层 (`pages/`)**：所有的 `st.write`、图表渲染、输入组件和布局排版都放在 `pages/` 目录下。页面代码应该尽可能“薄”，主要负责收集用户输入、调用 `core/` 中的函数，并展示结果。

### 2. 统一的基础设施
- **页面初始化**：每个新页面必须在文件开头调用 `from core.page_setup import init_page`。
- **图表渲染**：使用 `core.chart_config.apply_chart_config()` 包装所有的 Plotly 图表，以保证视觉一致性。
- **数据存储**：使用 `core.storage` 提供的 `load_document` / `save_document` 进行 JSON 数据持久化，不要在页面中手写文件读写逻辑。
- **市场数据**：使用 `core.market_cache` 提供的 API（如 `download_prices`）获取行情数据，享受内置的两级缓存，**不要**直接调用 `yfinance`。

### 3. 支持核心工作流
新功能应该服务于 OmniFinance 的核心决策工作流：
> 财务状态诊断 → 风险与机会识别 → 情景模拟 → 优先行动计划 → 报告导出与复盘

尽量避免添加孤立的、与上下文无关的简单计算器。

---

## 💻 本地开发环境设置

1. **克隆仓库并创建分支**：
   ```bash
   git clone https://github.com/hantrleko/omnifinance.git
   cd omnifinance
   git checkout -b feature/your-feature-name
   ```

2. **安装依赖**（建议使用虚拟环境）：
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **运行应用**：
   ```bash
   streamlit run app.py
   ```

---

## ✅ 提交前的检查清单 (Checks Before Committing)

在提交 PR 之前，请在本地运行以下命令，确保代码符合质量标准：

```bash
# 1. 检查是否有语法错误
python -m compileall app.py home.py pages core tests

# 2. 运行所有单元测试（必须全部通过）
pytest -q

# 3. 运行代码格式化和静态分析（Ruff）
ruff check .

# 4. 运行类型检查（针对 core 目录）
mypy core --ignore-missing-imports
```

### 测试指南 (Testing Guidelines)
- 我们要求 `core/` 目录下的所有新函数都必须配有单元测试（位于 `tests/` 目录下）。
- 测试用例应覆盖：正常输入、边界值（如零利率、极端通胀）、异常输入处理等。
- 我们使用 `pytest` 作为测试框架，可以使用 `unittest.mock.patch` 来 mock 外部依赖（如网络请求）。

---

## 📝 提交 Pull Request

1. 确保你的代码已经通过了上述的所有本地检查。
2. 将你的分支推送到 GitHub。
3. 在 GitHub 上创建一个 Pull Request，目标分支为 `main`。
4. 详细填写 PR 模板中的内容，说明你解决了什么问题、引入了什么新功能。
5. 如果你的 PR 涉及 UI 变动，**强烈建议**在 PR 描述中附上截图。

---

## 🐛 报告 Bug 与建议功能

如果你发现了 Bug 或者有好的功能建议，请使用 GitHub Issues：
- 报告 Bug 时，请提供复现步骤、预期的行为以及实际发生的行为，最好附上报错日志或截图。
- 建议功能时，请说明该功能解决了什么痛点，以及它如何融入现有的核心工作流。

再次感谢你对 OmniFinance 的支持！🚀
