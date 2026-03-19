"""Currency formatting and selection utilities."""
from __future__ import annotations

from typing import Any, TypedDict

import streamlit as st


# ── TypedDict definition ──────────────────────────────────

class CurrencyInfo(TypedDict):
    """Metadata for a single supported currency."""

    symbol: str
    name: str


# ── Currency registry ─────────────────────────────────────

CURRENCIES: dict[str, CurrencyInfo] = {
    "CNY": CurrencyInfo(symbol="¥", name="人民币"),
    "USD": CurrencyInfo(symbol="$", name="美元"),
    "EUR": CurrencyInfo(symbol="€", name="欧元"),
    "GBP": CurrencyInfo(symbol="£", name="英镑"),
    "JPY": CurrencyInfo(symbol="¥", name="日元"),
    "HKD": CurrencyInfo(symbol="HK$", name="港币"),
}

DEFAULT_CURRENCY: str = "CNY"


# ── Public helpers ────────────────────────────────────────

def get_symbol(code: str = "") -> str:
    """Return the currency symbol for a given ISO code.

    Args:
        code: ISO 4217 currency code (e.g. ``"CNY"``). When empty the value
            stored in ``st.session_state["currency"]`` is used, falling back
            to :data:`DEFAULT_CURRENCY`.

    Returns:
        The currency symbol string (e.g. ``"¥"`` or ``"HK$"``).
    """
    if not code:
        code = st.session_state.get("currency", DEFAULT_CURRENCY)
    return CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])["symbol"]


def fmt(value: float, code: str = "", decimals: int = 2) -> str:
    """Format a monetary value with the appropriate currency symbol.

    Args:
        value: Numeric amount to format.
        code: ISO 4217 currency code. Defaults to the session currency.
        decimals: Number of decimal places (default ``2``).

    Returns:
        Formatted string such as ``"¥1,234.56"``.
    """
    symbol = get_symbol(code)
    return f"{symbol}{value:,.{decimals}f}"


def fmt_delta(value: float, code: str = "", decimals: int = 2) -> str:
    """Format a monetary delta value with an explicit +/- sign.

    Args:
        value: Signed numeric amount to format.
        code: ISO 4217 currency code. Defaults to the session currency.
        decimals: Number of decimal places (default ``2``).

    Returns:
        Formatted string such as ``"¥+500.00"`` or ``"¥-200.00"``.
    """
    symbol = get_symbol(code)
    return f"{symbol}{value:+,.{decimals}f}"


def currency_selector(sidebar: bool = True) -> str:
    """Render a currency selector widget and persist the choice to session state.

    Args:
        sidebar: When ``True`` (default) the widget is placed in the sidebar;
            otherwise it is rendered inline on the main page.

    Returns:
        The selected ISO 4217 currency code string (e.g. ``"USD"``).
    """
    options: list[str] = list(CURRENCIES.keys())
    labels: list[str] = [
        f"{CURRENCIES[c]['symbol']} {CURRENCIES[c]['name']} ({c})"
        for c in options
    ]
    container: Any = st.sidebar if sidebar else st
    idx: int = container.selectbox(
        "💱 货币单位",
        range(len(options)),
        format_func=lambda i: labels[i],
        index=options.index(st.session_state.get("currency", DEFAULT_CURRENCY)),
        key="_currency_selector",
    )
    code: str = options[idx]
    st.session_state["currency"] = code
    return codee
