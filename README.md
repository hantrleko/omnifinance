# OmniFinance 全能理财家

一个基于 Streamlit 的多页面理财工具集合，覆盖复利、实时报价、策略回测、贷款、储蓄目标、预算分配、退休金估算等场景。

## 功能概览

- 💰 复利计算器（含利率敏感性）
- 📊 实时报价面板（yfinance）
- 📈 MA 交叉回测器（支持手续费/滑点）
- 🏦 贷款计算器（支持提前还款模拟）
- 🎯 储蓄目标计算器（含一页结论）
- 💡 预算分配建议器（50/30/20）
- 🏖️ 退休金估算器（含一页结论与敏感度分析）
- 🛡️ 保险产品测算器（保费效率、通胀折现保额、保单 IRR）

## 快速开始

> 请在**仓库根目录**执行以下命令。

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 测试与校验

```bash
python -m compileall app.py pages core tests
pytest -q
```

## 项目结构

- `app.py`：应用入口（版本与更新说明）
- `pages/`：各功能页面
- `core/`：共享业务逻辑层
- `tests/`：核心逻辑测试
- `.github/workflows/ci.yml`：CI 配置

## 数据与免责声明

- 行情数据主要来源于 Yahoo Finance（`yfinance`）。
- 本项目仅用于学习和研究，不构成任何投资建议。
