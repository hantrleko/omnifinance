"""Centralised application configuration and UI string constants.

All hard-coded default values, limits, and user-facing messages are defined
here so that they can be changed in one place and reused across every page.

Structure
---------
- ``AppConfig``   — top-level dataclass that groups all sub-configs
- ``QuoteConfig`` — 实时报价面板 defaults
- ``BacktestConfig`` — 策略回测器 defaults
- ``CompoundConfig`` — 复利计算器 defaults
- ``LoanConfig`` — 贷款计算器 defaults
- ``SavingsConfig`` — 储蓄目标计算器 defaults
- ``BudgetConfig`` — 预算分配建议器 defaults
- ``RetirementConfig`` — 退休金估算器 defaults
- ``InsuranceConfig`` — 保险产品测算器 defaults
- ``NetWorthConfig`` — 资产净值追踪器 defaults
- ``UIMessages`` — all user-facing strings (supports future i18n)
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════════════
#  Per-page default parameter groups
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class QuoteConfig:
    """Defaults for 2_实时报价面板.py."""

    # Auto-refresh
    refresh_interval_default: int = 60       # seconds
    refresh_interval_min: int = 30
    refresh_interval_max: int = 300
    refresh_interval_step: int = 10

    # Data-fetch concurrency & caching
    thread_pool_workers: int = 10
    quote_cache_ttl: int = 25                # seconds — st.cache_data TTL for live quotes
    kline_cache_ttl: int = 300               # seconds — st.cache_data TTL for K-line history
    kline_default_period: str = "6mo"

    # Default watchlist
    default_tickers: tuple[str, ...] = ("AAPL", "TSLA", "BTC-USD")


@dataclass(frozen=True)
class BacktestConfig:
    """Defaults for 3_MA交叉回测器.py."""

    # Capital & cost
    initial_capital_default: float = 100_000.0
    initial_capital_min: float = 1_000.0
    initial_capital_step: float = 10_000.0

    risk_free_rate_default: float = 2.0      # %
    risk_free_rate_min: float = 0.0
    risk_free_rate_max: float = 20.0
    risk_free_rate_step: float = 0.1

    fee_rate_default: float = 0.05           # % one-way
    fee_rate_min: float = 0.0
    fee_rate_max: float = 2.0
    fee_rate_step: float = 0.01

    slippage_rate_default: float = 0.03      # % one-way
    slippage_rate_min: float = 0.0
    slippage_rate_max: float = 2.0
    slippage_rate_step: float = 0.01

    # MA strategy defaults
    ma_short_default: int = 50
    ma_long_default: int = 200

    # RSI strategy defaults
    rsi_period_default: int = 14
    rsi_oversold_default: int = 30
    rsi_overbought_default: int = 70

    # MACD strategy defaults
    macd_fast_default: int = 12
    macd_slow_default: int = 26
    macd_signal_default: int = 9

    # Bollinger Band strategy defaults
    bb_period_default: int = 20
    bb_std_default: float = 2.0

    # Comparison cache TTL
    comparison_cache_ttl: int = 300

    # Default portfolio tickers for multi-asset backtest
    default_portfolio: str = "AAPL, MSFT, GOOGL"

    # Default ticker
    default_ticker: str = "AAPL"


@dataclass(frozen=True)
class CompoundConfig:
    """Defaults for 1_复利计算器.py."""

    principal_default: float = 10_000.0
    principal_step: float = 1_000.0

    annual_rate_default: float = 5.0         # %
    annual_rate_max: float = 100.0
    annual_rate_step: float = 0.1

    years_default: int = 10
    years_max: int = 100

    contribution_default: float = 1_000.0
    contribution_step: float = 100.0


@dataclass(frozen=True)
class LoanConfig:
    """Defaults for 4_贷款计算器.py."""

    amount_default: float = 1_000_000.0
    amount_min: float = 100_000.0
    amount_max: float = 50_000_000.0
    amount_step: float = 10_000.0

    rate_default: float = 4.5                # % annual
    rate_min: float = 0.1
    rate_max: float = 20.0
    rate_step: float = 0.1

    years_default: int = 30
    years_min: int = 1
    years_max: int = 40

    prepay_default: float = 200_000.0
    prepay_step: float = 10_000.0
    prepay_period_default: int = 24


@dataclass(frozen=True)
class SavingsConfig:
    """Defaults for 5_储蓄目标计算器.py."""

    current_default: float = 50_000.0
    current_max: float = 5_000_000.0
    current_step: float = 10_000.0

    goal_default: float = 1_000_000.0
    goal_min: float = 100_000.0
    goal_max: float = 10_000_000.0
    goal_step: float = 50_000.0

    annual_rate_default: float = 6.0         # %
    annual_rate_max: float = 15.0
    annual_rate_step: float = 0.1

    monthly_deposit_default: float = 10_000.0
    monthly_deposit_max: float = 200_000.0
    monthly_deposit_step: float = 1_000.0

    inflation_rate_default: float = 2.5      # %
    inflation_rate_max: float = 10.0
    inflation_rate_step: float = 0.1

    # Thresholds for conclusion labels (months)
    goal_short_threshold: int = 60           # ≤ 5 years → "较短"
    goal_long_threshold: int = 180           # > 15 years → "较长"


@dataclass(frozen=True)
class BudgetConfig:
    """Defaults for 6_预算分配建议器.py."""

    income_default: float = 60_000.0
    income_min: float = 10_000.0
    income_max: float = 1_000_000.0
    income_step: float = 5_000.0

    fixed_expense_step: float = 1_000.0

    # 50/30/20 rule split ratios
    needs_ratio: float = 0.50
    wants_ratio: float = 0.30
    savings_ratio: float = 0.20


@dataclass(frozen=True)
class RetirementConfig:
    """Defaults for 7_退休金估算器.py."""

    current_assets_default: float = 500_000.0
    current_assets_max: float = 50_000_000.0
    current_assets_step: float = 50_000.0

    monthly_saving_default: float = 10_000.0
    monthly_saving_max: float = 500_000.0
    monthly_saving_step: float = 1_000.0

    pre_return_default: float = 7.0          # %
    pre_return_max: float = 20.0
    pre_return_step: float = 0.1

    monthly_expense_default: float = 30_000.0
    monthly_expense_min: float = 5_000.0
    monthly_expense_max: float = 500_000.0
    monthly_expense_step: float = 1_000.0

    pension_income_default: float = 0.0
    pension_income_max: float = 200_000.0
    pension_income_step: float = 500.0

    inflation_default: float = 2.5           # %
    inflation_max: float = 10.0
    inflation_step: float = 0.1

    post_return_default: float = 4.0         # %
    post_return_max: float = 15.0
    post_return_step: float = 0.1


@dataclass(frozen=True)
class InsuranceConfig:
    """Defaults for 8_保险产品测算器.py."""

    annual_premium_default: float = 12_000.0
    annual_premium_step: float = 500.0

    pay_years_default: int = 20
    pay_years_max: int = 50

    coverage_years_default: int = 30
    coverage_years_max: int = 80

    sum_assured_default: float = 1_000_000.0
    sum_assured_step: float = 50_000.0

    inflation_default: float = 2.5           # %
    inflation_max: float = 10.0
    inflation_step: float = 0.1

    alt_return_default: float = 4.0          # %
    alt_return_max: float = 20.0
    alt_return_step: float = 0.1

    maturity_benefit_default: float = 350_000.0
    maturity_benefit_step: float = 10_000.0

    # Thresholds for IRR conclusion
    irr_competitive_threshold: float = 0.0  # IRR >= alt_return → competitive
    inflation_warning_threshold: float = 30.0  # % erosion → show error vs warning


@dataclass(frozen=True)
class NetWorthConfig:
    """Defaults for 9_资产净值追踪器.py."""

    asset_step: float = 10_000.0
    real_estate_step: float = 100_000.0
    credit_card_step: float = 1_000.0

    # Debt-ratio thresholds
    debt_ratio_high: float = 60.0            # % → error
    debt_ratio_medium: float = 40.0          # % → warning


# ══════════════════════════════════════════════════════════════════════════════
#  UI string constants  (i18n-ready: swap this class for a locale loader)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class UIMessages:
    """All user-facing strings used across pages.

    To add multi-language support, replace this dataclass with a function
    that loads strings from a locale file (e.g. ``locales/zh_CN.toml``).
    """

    # ── Common ──────────────────────────────────────────────────────────────
    data_source_yfinance: str = "数据来源：Yahoo Finance（yfinance）"
    data_source_yfinance_short: str = "数据来源：Yahoo Finance (yfinance)"
    disclaimer_research: str = "免责声明：仅供学习研究，不构成投资建议。"
    disclaimer_insurance: str = "🛡️ 保险产品测算器 | 仅供学习参考，不构成保险或投资建议 | 运行：`streamlit run app.py`"
    disclaimer_retirement: str = "🏖️ 退休金需求估算器 | 仅供参考，不构成投资建议 | 运行：`streamlit run app.py`"
    run_hint: str = "运行命令：`streamlit run app.py`"
    print_hint: str = "提示：打开 HTML 后按 Ctrl+P 可打印为 PDF。"
    print_hint_backtest: str = "提示：打开 HTML 文件后按 Ctrl+P 可打印/另存为 PDF。"

    # ── Quote panel ─────────────────────────────────────────────────────────
    quote_ticker_hint: str = "提示：港股代码格式 0700.HK，加密货币 BTC-USD"
    quote_no_selection: str = "请在左侧面板中选择至少一个标的。"
    quote_network_error: str = "🌐 网络连接异常，以下标的数据获取失败（可能为限流或网络问题）：{tickers}"
    quote_notfound_error: str = "❌ 以下标的代码无效或已退市，请检查代码格式：{tickers}"
    quote_cached_info: str = "💾 以下标的使用上次缓存数据：{tickers}"
    quote_no_valid_data: str = "暂无有效行情数据，请检查网络连接或标的代码。"
    quote_kline_loading: str = "正在加载 {ticker} 近6个月历史数据…"
    quote_kline_failed: str = "未能获取 {ticker} 的历史数据，请稍后重试或检查代码。"
    quote_footer: str = "自动刷新间隔：{interval} 秒 | 数据来源：Yahoo Finance | 运行命令：`streamlit run app.py`"

    # ── Backtest ─────────────────────────────────────────────────────────────
    backtest_data_loading: str = "正在获取 {ticker} 数据…"
    backtest_data_loaded: str = "✅ 已加载 **{ticker}** | {start} → {end} | 共 {n} 个交易日"
    backtest_data_failed: str = "⚠️ 无法从 yfinance 获取 {ticker} 数据，请上传本地 CSV 文件。"
    backtest_csv_loaded: str = "✅ 已加载上传数据 | {start} → {end} | 共 {n} 行"
    backtest_csv_failed: str = "CSV 解析失败：{error}"
    backtest_positive: str = "结论：在当前参数下，策略净值跑赢初始资金，期间总交易成本约 {cost}。"
    backtest_negative: str = "结论：在当前参数下，策略回报为负；可尝试调整策略参数或降低交易成本参数。"
    backtest_no_trades: str = "当前参数下未产生任何交易信号。请尝试调整策略参数或日期范围。"
    backtest_grid_caption: str = "自动搜索最优参数组合（基于夏普比率）"
    backtest_grid_done: str = "搜索完成！共测试 {n} 组参数"
    backtest_grid_none: str = "未找到有效参数组合"
    backtest_portfolio_caption: str = "对多个标的运行同一策略，查看各标的表现"
    backtest_portfolio_min: str = "请输入至少两个标的代码"
    backtest_sortino_help: str = "仅统计下行波动的风险调整回报，比夏普更保守"
    backtest_calmar_help: str = "年化回报 / 最大回撤绝对值，越高越好"
    backtest_footer: str = "策略回测器 | 数据来源：Yahoo Finance | 运行：`streamlit run app.py`"

    # ── Savings ──────────────────────────────────────────────────────────────
    savings_already_reached: str = "🎉 **已达成目标！** 目前储蓄 {current} 已超过目标 {goal}"
    savings_never: str = "⚠️ 以当前参数设定，无法在 100 年内达成目标。请增加每月投入或提高报酬率。"
    savings_short_conclusion: str = "结论：目标可在较短周期内达成。"
    savings_short_next: str = "下一步：保持当前投入节奏，定期复盘收益率假设。"
    savings_medium_conclusion: str = "结论：目标可达成，但时间中等。"
    savings_medium_next: str = "下一步：若希望提前达成，可提高每月投入或下调目标金额。"
    savings_long_conclusion: str = "结论：目标可达成但周期较长。"
    savings_long_next: str = "下一步：建议优先提高月投入，其次再考虑调整收益率假设。"
    savings_inflation_warning: str = "⚠️ 考虑 {rate}% 通胀，{years:.0f} 年后实际需要 {real_goal} 才等价于今日 {goal} 的购买力。"
    savings_inflation_info: str = "💡 考虑 {rate}% 通胀，{years:.0f} 年后等价购买力约需 {real_goal}。"
    savings_inflation_help: str = "考虑通胀后的购买力折损"
    savings_footer: str = "🎯 储蓄目标达成计算器 | 运行命令：`streamlit run app.py`"

    # ── Loan ─────────────────────────────────────────────────────────────────
    loan_prepay_info: str = "结论：在第 {period} 期提前还 {amount}，预计少付利息 {saved}，并缩短 {periods} 期。"
    loan_compare_caption: str = "输入第二组贷款参数进行并列对比"
    loan_footer: str = "🏦 贷款计算器 | 运行命令：`streamlit run app.py`"

    # ── Budget ───────────────────────────────────────────────────────────────
    budget_needs_caption: str = "含：房租/房贷、水电煤、保险、交通、基本餐饮"
    budget_wants_caption: str = "含：外出餐饮、娱乐、购物、订阅、旅行"
    budget_debt_caption: str = "有高利债务时，建议将大部分储蓄用于还债"
    budget_emergency_caption: str = "建议先存满 3–6 个月应急金，再配置投资"
    budget_fixed_help: str = "如房租、房贷、保险等已确定的必需支出"
    budget_footer: str = "💡 50/30/20 预算分配建议器 | 运行命令：`streamlit run app.py`"

    # ── Retirement ───────────────────────────────────────────────────────────
    retirement_pension_help: str = "退休后每月可领取的社保养老金或企业年金（今日币值）"
    retirement_pension_info: str = (
        "💰 养老金效果：月养老金 {income}（今日币值），退休首年等效 {future}，"
        "可减少所需资产约 {pv}"
    )
    retirement_ok_conclusion: str = "结论：当前退休计划可覆盖资金需求。"
    retirement_ok_reason: str = "原因：预计退休时可累积 {projected}，高于所需 {needed}。"
    retirement_ok_next: str = "下一步：保持定投并每年复盘通胀和收益率假设。"
    retirement_gap_conclusion: str = "结论：当前退休计划仍有资金缺口。"
    retirement_gap_reason: str = "原因：预计缺口 {gap}。"
    retirement_gap_next: str = "下一步：建议每月额外增加储蓄约 {extra}，并结合延后退休年龄评估。"
    retirement_footer: str = "🏖️ 退休金需求估算器 | 仅供参考，不构成投资建议 | 运行：`streamlit run app.py`"

    # ── Insurance ────────────────────────────────────────────────────────────
    insurance_breakeven_help: str = "理赔额需达到总保费才能回本的最低赔付概率"
    insurance_irr_competitive: str = (
        "结论：保单 IRR（{irr:.2f}%）≥ 替代投资收益（{alt:.1f}%），储蓄型保险具有竞争力。"
    )
    insurance_irr_competitive_next: str = "下一步：可考虑将其作为稳健型低风险资产配置的一部分。"
    insurance_irr_low: str = (
        "结论：保单 IRR（{irr:.2f}%）低于替代投资（{alt:.1f}%），但仍为正收益。"
    )
    insurance_irr_low_note: str = "说明：选择此产品的机会成本约为 {gap}（期末与替代投资的差距）。"
    insurance_irr_low_next: str = "下一步：综合考量保障需求与流动性后再决策，不宜单纯以收益率比较。"
    insurance_irr_weak: str = (
        "结论：保单 IRR（{irr:.2f}%）偏低，储蓄属性较弱，主要价值在于保障功能。"
    )
    insurance_irr_weak_note: str = "说明：若目的为纯储蓄增值，替代投资可获得约 {gap} 的额外收益。"
    insurance_irr_weak_next: str = "下一步：评估是否有更高 IRR 的同类产品，或考虑将储蓄与保障分离配置。"
    insurance_footer: str = "🛡️ 保险产品测算器 | 仅供学习参考，不构成保险或投资建议 | 运行：`streamlit run app.py`"
    insurance_inflation_error: str = (
        "⚠️ 通胀警示：{years} 年后实际保额仅剩名义保额的 {remaining:.0f}%，"
    )
    insurance_inflation_warning: str = (
        "📉 通胀提示：{years} 年后实际保额约缩水 {erosion:.0f}%，"
    )

    # ── Net Worth ────────────────────────────────────────────────────────────
    networth_debt_high: str = "⚠️ 负债率 {ratio:.1f}%，偏高！"
    networth_debt_medium: str = "📌 负债率 {ratio:.1f}%，中等水平。"
    networth_debt_ok: str = "✅ 负债率 {ratio:.1f}%，健康。"
    networth_saved: str = "✅ 快照已保存！"
    networth_cleared: str = "已清除"
    networth_trend_hint: str = "📌 再保存一次快照后即可查看趋势图。"
    networth_footer: str = "🏠 资产净值追踪器 | 运行命令：`streamlit run app.py`"


# ══════════════════════════════════════════════════════════════════════════════
#  Top-level singleton — import this in pages
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AppConfig:
    """Root configuration object.  Import and use as::

        from core.config import CFG, MSG

        st.slider(..., value=CFG.backtest.initial_capital_default)
        st.warning(MSG.backtest_negative)
    """

    quote: QuoteConfig = field(default_factory=QuoteConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    compound: CompoundConfig = field(default_factory=CompoundConfig)
    loan: LoanConfig = field(default_factory=LoanConfig)
    savings: SavingsConfig = field(default_factory=SavingsConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    retirement: RetirementConfig = field(default_factory=RetirementConfig)
    insurance: InsuranceConfig = field(default_factory=InsuranceConfig)
    networth: NetWorthConfig = field(default_factory=NetWorthConfig)


# Module-level singletons for convenient import
CFG = AppConfig()
MSG = UIMessages()
