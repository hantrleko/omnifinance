"""Real-time exchange rate engine using yfinance.

Provides cached rate lookups with a static fallback dictionary when
network requests fail.
"""
from __future__ import annotations

import datetime
import time
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    import pandas as pd

_FALLBACK_RATES_TO_CNY: dict[str, float] = {
    "USD": 7.25,
    "EUR": 7.85,
    "GBP": 9.15,
    "JPY": 0.048,
    "HKD": 0.927,
    "CNY": 1.0,
}

_DIRECT_PAIRS = {
    "USD": "USDCNY=X",
    "EUR": "EURCNY=X",
    "GBP": "GBPCNY=X",
    "JPY": "JPYCNY=X",
}

# HKD 在 Yahoo 对应的直接票可能不稳定（HKDCNY=X），改为:
# HKDCNY = USDCNY / USDHKD
_HKD_CROSS_TICKERS = ("USDCNY=X", "USDHKD=X")

_last_updated: datetime.datetime | None = None


def _extract_latest_close(data, ticker: str) -> float | None:
    """Extract latest close price from a yfinance download payload."""
    if data is None:
        return None
    if hasattr(data, "empty") and data.empty:
        return None

    columns = getattr(data, "columns", None)
    if columns is None:
        return None

    # Prefer direct `Close` column for single ticker responses.
    if "Close" in columns:
        series = data["Close"]
    elif "close" in columns:
        # Some providers or future versions may normalize differently.
        series = data["close"]
    else:
        if len(columns) == 0:
            return None
        # MultiIndex style (e.g. field, ticker) for bulk downloads.
        if hasattr(columns, "nlevels") and columns.nlevels > 1:
            if ("Close", ticker) in columns:
                series = data[("Close", ticker)]
            elif (ticker, "Close") in columns:
                series = data[(ticker, "Close")]
            else:
                return None
        elif ticker in columns:
            series = data[ticker]
        else:
            return None

    if series is None:
        return None
    cleaned = series.dropna()
    if cleaned.empty:
        return None
    return float(cleaned.iloc[-1])


def _fetch_single_rate(yf, ticker: str, period: str = "2d", interval: str = "1d") -> float | None:
    """Fetch one exchange-rate series and return its latest close value."""
    for attempt in range(3):
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
                threads=False,
            )
            return _extract_latest_close(data, ticker)
        except Exception:  # noqa: BLE001
            if attempt < 2:
                time.sleep(0.2 * (attempt + 1))
    return None


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_rates() -> tuple[dict[str, float], bool]:
    """Fetch latest exchange rates vs CNY from yfinance.

    Returns:
        Tuple of (rates_dict, is_live) where rates_dict maps ISO code to CNY
        rate and is_live indicates whether data was fetched from the network.
    """
    try:
        import yfinance as yf

        rates: dict[str, float] = {"CNY": 1.0}
        live = False

        for code, ticker in _DIRECT_PAIRS.items():
            value = _fetch_single_rate(yf, ticker)
            if value is not None:
                rates[code] = value
                live = True
            else:
                rates[code] = _FALLBACK_RATES_TO_CNY[code]

        # HKD uses cross-rate fallback path to avoid HKDCNY=X lock/unavailable errors.
        usd_cny = _fetch_single_rate(yf, _HKD_CROSS_TICKERS[0])
        usd_hkd = _fetch_single_rate(yf, _HKD_CROSS_TICKERS[1])
        if usd_cny is not None and usd_hkd is not None and usd_hkd != 0:
            rates["HKD"] = usd_cny / usd_hkd
            live = True
        else:
            rates["HKD"] = _FALLBACK_RATES_TO_CNY["HKD"]

        if live:
            global _last_updated
            _last_updated = datetime.datetime.now()

        return rates, live
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
    source = _last_updated or datetime.datetime.now()
    return source.strftime("%H:%M:%S")


def get_historical_rates(from_code: str, to_code: str, days: int = 30) -> pd.DataFrame:
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

        data = yf.download(
            pair_key,
            period=f"{days}d",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        if data.empty:
            return pd.DataFrame()
        close = data["Close"] if "Close" in data.columns else data
        col = pair_key if pair_key in close.columns else close.columns[0]
        df = close[[col]].dropna().rename(columns={col: "rate"})
        return df
    except Exception:
        return pd.DataFrame()
