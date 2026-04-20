"""Real-time exchange rate engine using yfinance.

Provides cached rate lookups with a static fallback dictionary when
network requests fail.
"""
from __future__ import annotations

import datetime
from typing import Optional

import streamlit as st

_FALLBACK_RATES_TO_CNY: dict[str, float] = {
    "USD": 7.25,
    "EUR": 7.85,
    "GBP": 9.15,
    "JPY": 0.048,
    "HKD": 0.927,
    "CNY": 1.0,
}

_PAIRS = {
    "USD": "USDCNY=X",
    "EUR": "EURCNY=X",
    "GBP": "GBPCNY=X",
    "JPY": "JPYCNY=X",
    "HKD": "HKDCNY=X",
}

_last_updated: Optional[datetime.datetime] = None


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_rates() -> tuple[dict[str, float], bool]:
    """Fetch latest exchange rates vs CNY from yfinance.

    Returns:
        Tuple of (rates_dict, is_live) where rates_dict maps ISO code to CNY
        rate and is_live indicates whether data was fetched from the network.
    """
    try:
        import yfinance as yf

        tickers = list(_PAIRS.values())
        data = yf.download(tickers, period="2d", interval="1d", progress=False, auto_adjust=True)
        close = data["Close"] if "Close" in data.columns else data

        rates: dict[str, float] = {"CNY": 1.0}
        for code, ticker in _PAIRS.items():
            col = ticker if ticker in close.columns else None
            if col is not None and not close[col].dropna().empty:
                rates[code] = float(close[col].dropna().iloc[-1])
            else:
                rates[code] = _FALLBACK_RATES_TO_CNY[code]

        return rates, True
    except Exception:
        return dict(_FALLBACK_RATES_TO_CNY), False


def get_all_rates() -> dict[str, float]:
    """Return a dict mapping each supported ISO code to its CNY equivalent."""
    rates, _ = _fetch_rates()
    return rates


def is_live() -> bool:
    """Return True when the last rate fetch was from the network."""
    _, live = _fetch_rates()
    return live


def get_rate(from_code: str, to_code: str) -> float:
    """Return the exchange rate from *from_code* to *to_code*.

    Args:
        from_code: Source ISO 4217 currency code (e.g. ``"USD"``).
        to_code: Target ISO 4217 currency code (e.g. ``"CNY"``).

    Returns:
        Float exchange rate. Returns 1.0 if both codes are the same.
    """
    if from_code == to_code:
        return 1.0
    rates = get_all_rates()
    from_to_cny = rates.get(from_code, 1.0)
    to_to_cny = rates.get(to_code, 1.0)
    if to_to_cny == 0:
        return 1.0
    return from_to_cny / to_to_cny


def get_last_updated_str() -> str:
    """Return a human-readable string of when rates were last refreshed."""
    return datetime.datetime.now().strftime("%H:%M:%S")


def get_historical_rates(from_code: str, to_code: str, days: int = 30) -> "import pandas; pandas.DataFrame":  # type: ignore[return]
    """Fetch historical daily close rates between two currencies.

    Args:
        from_code: Source ISO 4217 currency code.
        to_code: Target ISO 4217 currency code.
        days: Number of historical calendar days to fetch (default ``30``).

    Returns:
        DataFrame with DatetimeIndex and a single ``"rate"`` column.
        Returns an empty DataFrame on failure.
    """
    import pandas as pd

    pair_key = f"{from_code}{to_code}=X"
    try:
        import yfinance as yf

        data = yf.download(pair_key, period=f"{days}d", interval="1d", progress=False, auto_adjust=True)
        if data.empty:
            return pd.DataFrame()
        close = data["Close"] if "Close" in data.columns else data
        col = pair_key if pair_key in close.columns else close.columns[0]
        df = close[[col]].dropna().rename(columns={col: "rate"})
        return df
    except Exception:
        return pd.DataFrame()
