"""Currency formatting and selection utilities."""

from __future__ import annotations

import streamlit as st

CURRENCIES: dict[str, dict] = {
    "CNY": {"symbol": "¥", "name": "人民币"},
    "USD": {"symbol": "$", "name": "美元"},
    "EUR": {"symbol": "€", "name": "欧元"},
    "GBP": {"symbol": "£", "name": "英镑"},
    "JPY": {"symbol": "¥", "name": "日元"},
    "HKD": {"symbol": "HK$", "name": "港币"},
}

DEFAULT_CURRENCY = "CNY"


def get_symbol(code: str = "") -> str:
    """Return the currency symbol for a given code."""
    if not code:
        code = st.session_state.get("currency", DEFAULT_CURRENCY)
    return CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])["symbol"]


def fmt(value: float, code: str = "", decimals: int = 2) -> str:
    """Format a monetary value with the appropriate currency symbol."""
    symbol = get_symbol(code)
    return f"{symbol}{value:,.{decimals}f}"


def fmt_delta(value: float, code: str = "", decimals: int = 2) -> str:
    """Format a monetary delta (with +/- sign)."""
    symbol = get_symbol(code)
    return f"{symbol}{value:+,.{decimals}f}"


def currency_selector(sidebar: bool = True) -> str:
    """Render a currency selector widget and return the selected code."""
    options = list(CURRENCIES.keys())
    labels = [f"{CURRENCIES[c]['symbol']} {CURRENCIES[c]['name']} ({c})" for c in options]
    container = st.sidebar if sidebar else st
    idx = container.selectbox(
        "💱 货币单位",
        range(len(options)),
        format_func=lambda i: labels[i],
        index=options.index(st.session_state.get("currency", DEFAULT_CURRENCY)),
        key="_currency_selector",
    )
    code = options[idx]
    st.session_state["currency"] = code
    return code
