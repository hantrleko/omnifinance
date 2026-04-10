"""Locale support for multi-language UI strings.

Currently supports zh_CN (Chinese Simplified) and en_US (English).
To add more languages, extend the LOCALES dict below.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

LOCALES: dict[str, dict[str, str]] = {
    "zh_CN": {
        "app_title": "全能理财家 (OmniFinance)",
        "welcome": "欢迎使用全能理财家！",
        "dashboard": "仪表盘首页",
        "compound": "复利计算器",
        "savings": "储蓄目标计算器",
        "budget": "预算分配建议器",
        "loan": "贷款计算器",
        "networth": "资产净值追踪器",
        "insurance": "保险产品测算器",
        "quote": "实时报价面板",
        "backtest": "策略回测器",
        "portfolio": "投资组合优化器",
        "retirement": "退休金估算器",
        "montecarlo": "蒙特卡洛模拟",
        "tax": "税务计算器",
        "debt": "债务还清规划器",
        "education": "教育基金规划器",
        "realestate": "房产投资分析器",
        "fx": "外汇对冲计算器",
        "rebalance": "资产再平衡模拟器",
        "scenario": "场景对比分析器",
        "historical": "历史回测储蓄模拟",
        "withdrawal": "税务优化提款策略",
        "calendar": "财务日历",
        "settings": "全局设置",
        "currency": "货币单位",
        "dark_mode": "深色模式",
        "disclaimer": "免责声明：仅供学习研究，不构成投资建议。",
        "run_hint": "运行命令：`streamlit run app.py`",
        "export": "导出",
        "download": "下载",
        "total": "合计",
        "year": "年",
        "month": "月",
    },
    "en_US": {
        "app_title": "OmniFinance",
        "welcome": "Welcome to OmniFinance!",
        "dashboard": "Dashboard",
        "compound": "Compound Calculator",
        "savings": "Savings Goal",
        "budget": "Budget Advisor",
        "loan": "Loan Calculator",
        "networth": "Net Worth Tracker",
        "insurance": "Insurance Estimator",
        "quote": "Real-time Quotes",
        "backtest": "Strategy Backtester",
        "portfolio": "Portfolio Optimizer",
        "retirement": "Retirement Planner",
        "montecarlo": "Monte Carlo Sim",
        "tax": "Tax Calculator",
        "debt": "Debt Payoff Planner",
        "education": "Education Fund",
        "realestate": "Real Estate Analyzer",
        "fx": "FX Hedging",
        "rebalance": "Rebalancing Simulator",
        "scenario": "Scenario Analyzer",
        "historical": "Historical Backtest",
        "withdrawal": "Withdrawal Strategy",
        "calendar": "Financial Calendar",
        "settings": "Settings",
        "currency": "Currency",
        "dark_mode": "Dark Mode",
        "disclaimer": "Disclaimer: For educational purposes only. Not financial advice.",
        "run_hint": "Run: `streamlit run app.py`",
        "export": "Export",
        "download": "Download",
        "total": "Total",
        "year": "Year",
        "month": "Month",
    },
}

SUPPORTED_LOCALES = list(LOCALES.keys())
DEFAULT_LOCALE = "zh_CN"


def get_locale() -> str:
    """Get the current locale from session state."""
    return st.session_state.get("locale", DEFAULT_LOCALE)


def set_locale(locale: str) -> None:
    """Set the current locale."""
    if locale in SUPPORTED_LOCALES:
        st.session_state["locale"] = locale


def t(key: str) -> str:
    """Translate a key to the current locale string.

    Args:
        key: Translation key.

    Returns:
        Translated string, or the key itself if not found.
    """
    locale = get_locale()
    return LOCALES.get(locale, LOCALES[DEFAULT_LOCALE]).get(key, key)


def locale_selector(sidebar: bool = True) -> str:
    """Render a locale selector widget."""
    container: Any = st.sidebar if sidebar else st
    labels = {"zh_CN": "🇨🇳 中文", "en_US": "🇺🇸 English"}
    current = get_locale()
    choice = container.selectbox(
        "🌐 语言 / Language",
        SUPPORTED_LOCALES,
        index=SUPPORTED_LOCALES.index(current),
        format_func=lambda x: labels.get(x, x),
        key="_locale_selector",
    )
    set_locale(choice)
    return choice
