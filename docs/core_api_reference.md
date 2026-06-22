# Core API Reference

OmniFinance 的核心计算引擎和基础设施均位于 `core/` 目录下。本参考文档介绍了供页面调用的主要公共 API。

## 基础设施 (Infrastructure)

### `core.page_setup`
所有 Streamlit 页面都必须在顶部调用的初始化模块。

- **`init_page(title: str, icon: str, key: str)`**
  配置页面标题、图标，注入主题 CSS，并记录用户的最近访问历史。

### `core.storage`
统一的磁盘存储抽象，替代直接的 `json.dump` 和 `os.path` 操作。

- **`load_document(name: str, default: dict) -> dict`**
  从 `~/.omnifinance/documents/` 读取指定的 JSON 文档。如果文件不存在或解析失败，返回 `default`。
- **`save_document(name: str, data: dict)`**
  将字典数据安全地保存为 JSON 文档，自动创建必要的目录结构。

### `core.market_cache`
基于两级缓存（内存 LRU + 磁盘 Parquet）的市场数据获取模块。

- **`download_prices(tickers: list[str], period: str) -> pd.DataFrame`**
  批量下载多个股票的调整后收盘价。
- **`fetch_ohlcv(ticker: str, start: date, end: date) -> pd.DataFrame`**
  下载单只股票的 OHLCV 历史数据。
- **`fetch_ticker_info(ticker: str) -> dict`**
  获取股票的基本面信息（如 PE、ROE、市值等）。

---

## 业务模块 (Business Logic)

### `core.ledger_import`
收支账单的导入与解析引擎。

- **`detect_format(filename: str, header_line: str) -> str`**
  自动识别账单格式（支持 `alipay`, `wechat`, `generic`）。
- **`parse_upload(uploaded_file, existing_records) -> tuple[list, list, int]`**
  解析上传的文件，执行去重逻辑，返回新记录列表、错误信息和跳过的重复记录数。

### `core.glossary`
金融概念小白科普模块。

- **`render_glossary_sidebar(keys: list[str])`**
  在 Streamlit 侧边栏中渲染可折叠的术语解释卡片。

### `core.moat`
长期护城河评分器的纯计算逻辑。

- **`fetch_signal_scores(ticker: str) -> dict[str, float]`**
  获取客观的财务信号得分（如高 ROE 转化为护城河得分）。
- **`compute_composite(subjective: dict, objective: dict) -> float`**
  计算主客观结合的综合护城河评分。

### `core.rebalance`
资产再平衡模拟引擎。

- **`generate_monthly_returns(assets: list, horizon: int) -> np.ndarray`**
  使用蒙特卡洛方法生成对数正态分布的月度收益率矩阵。
- **`simulate_strategy(strategy: str, initial: np.ndarray, target: np.ndarray, returns: np.ndarray, ...) -> dict`**
  运行指定的再平衡策略（如定期再平衡、阈值再平衡、买入持有等）。
