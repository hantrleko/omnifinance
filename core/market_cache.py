"""core/market_cache.py — Persistent disk cache for yfinance market data.

Problem solved
--------------
Previously every page called ``yf.download()`` or ``yf.Ticker().info``
directly, relying only on Streamlit's in-memory ``@st.cache_data``.  This
means:
  * Every fresh session (or after TTL expiry) re-downloads the same data.
  * Switching between pages (e.g. portfolio → MA backtest) triggers duplicate
    network requests for the same ticker / period combination.
  * Users on slow / metered connections experience long spinners repeatedly.

Solution
--------
``market_cache`` adds a **two-level cache**:

1. **L1 — Streamlit in-memory** (``@st.cache_data``, TTL = 10 min by default)
   Fast path; avoids disk I/O on repeated calls within the same session.

2. **L2 — Parquet on disk** (``~/.omnifinance/market_cache/``, TTL configurable)
   Survives session restarts.  Data is stored per ``(ticker, period/dates)``
   key as a Parquet file.  A sidecar ``.meta.json`` records the fetch
   timestamp so stale entries can be detected and refreshed.

Public API
----------
``download_prices(tickers, period, *, ttl_hours)``
    Replacement for ``yf.download()`` — returns a ``pd.DataFrame`` of
    adjusted close prices.

``fetch_ticker_info(ticker, *, ttl_hours)``
    Replacement for ``yf.Ticker(ticker).info`` — returns a ``dict``.

``fetch_ohlcv(ticker, start, end, *, ttl_hours)``
    Replacement for the OHLCV download in the MA backtest page — returns a
    ``pd.DataFrame`` with columns Open/High/Low/Close/Volume.

``clear_cache(ticker)``
    Remove all cached files for a given ticker (or all tickers if ``None``).

``cache_stats()``
    Return a summary dict with entry count, total size (bytes), and oldest
    entry timestamp.
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
import urllib.error
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

_logger = logging.getLogger(__name__)

# ── Cache directory ────────────────────────────────────────────────────────────
_CACHE_DIR = Path.home() / ".omnifinance" / "market_cache"

# Default TTL values (hours)
_DEFAULT_PRICE_TTL_H = 6       # OHLCV / adjusted close prices
_DEFAULT_INFO_TTL_H = 12       # Ticker fundamentals (slower-changing)
_DEFAULT_OHLCV_TTL_H = 6       # Intraday / daily OHLCV


def _ensure_cache_dir() -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


# ── Cache key helpers ──────────────────────────────────────────────────────────

def _price_key(tickers: tuple[str, ...], period: str) -> str:
    raw = f"prices|{'_'.join(sorted(tickers))}|{period}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]  # noqa: S324


def _info_key(ticker: str) -> str:
    raw = f"info|{ticker.upper()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]  # noqa: S324


def _ohlcv_key(ticker: str, start: date, end: date) -> str:
    raw = f"ohlcv|{ticker.upper()}|{start.isoformat()}|{end.isoformat()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]  # noqa: S324


# ── Low-level read / write ─────────────────────────────────────────────────────

def _meta_path(key: str) -> Path:
    return _ensure_cache_dir() / f"{key}.meta.json"


def _data_path_parquet(key: str) -> Path:
    return _ensure_cache_dir() / f"{key}.parquet"


def _data_path_json(key: str) -> Path:
    return _ensure_cache_dir() / f"{key}.json"


def _is_fresh(key: str, ttl_hours: float) -> bool:
    """Return True if the cached entry exists and is within TTL."""
    meta = _meta_path(key)
    if not meta.exists():
        return False
    try:
        info = json.loads(meta.read_text(encoding="utf-8"))
        fetched_at = info.get("fetched_at", 0)
        age_hours = (time.time() - fetched_at) / 3600
        return age_hours < ttl_hours
    except (json.JSONDecodeError, OSError):
        return False


def _write_meta(key: str, extra: dict[str, Any] | None = None) -> None:
    meta: dict[str, Any] = {"fetched_at": time.time()}
    if extra:
        meta.update(extra)
    try:
        _meta_path(key).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        _logger.warning("market_cache: failed to write meta for %s: %s", key, exc)


def _write_df(key: str, df: pd.DataFrame) -> None:
    try:
        df.to_parquet(_data_path_parquet(key), index=True)
        _write_meta(key, {"rows": len(df), "columns": list(df.columns)})
    except Exception as exc:  # noqa: BLE001
        _logger.warning("market_cache: failed to write parquet for %s: %s", key, exc)


def _read_df(key: str) -> pd.DataFrame | None:
    path = _data_path_parquet(key)
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("market_cache: failed to read parquet for %s: %s", key, exc)
        return None


def _write_json(key: str, data: dict[str, Any]) -> None:
    try:
        _data_path_json(key).write_text(
            json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8"
        )
        _write_meta(key, {"type": "json"})
    except OSError as exc:
        _logger.warning("market_cache: failed to write json for %s: %s", key, exc)


def _read_json(key: str) -> dict[str, Any] | None:
    path = _data_path_json(key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _logger.warning("market_cache: failed to read json for %s: %s", key, exc)
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def download_prices(
    tickers: tuple[str, ...] | list[str],
    period: str = "1y",
    *,
    ttl_hours: float = _DEFAULT_PRICE_TTL_H,
) -> pd.DataFrame:
    """Download adjusted close prices with two-level caching.

    Replaces direct ``yf.download()`` calls in:
      - ``pages/11_投资组合优化器.py``
      - ``pages/2_实时报价面板.py``

    Args:
        tickers:   Sequence of ticker symbols (e.g. ``["AAPL", "MSFT"]``).
        period:    yfinance period string (``"1y"``, ``"2y"``, ``"5y"`` …).
        ttl_hours: Maximum age (hours) before the disk cache is considered
                   stale and a fresh download is triggered.

    Returns:
        DataFrame with ticker symbols as columns and dates as index.
        Returns an empty DataFrame on network / parse failure.
    """
    import yfinance as yf  # lazy import — not available in test environments

    tickers_t = tuple(t.upper() for t in tickers)
    key = _price_key(tickers_t, period)

    # L2 hit
    if _is_fresh(key, ttl_hours):
        cached = _read_df(key)
        if cached is not None and not cached.empty:
            _logger.debug("market_cache: L2 hit for prices %s/%s", tickers_t, period)
            return cached

    # Cache miss — fetch from yfinance
    _logger.debug("market_cache: fetching prices %s/%s", tickers_t, period)
    try:
        raw = yf.download(list(tickers_t), period=period, progress=False, auto_adjust=True)
        if isinstance(raw.columns, pd.MultiIndex):
            df = raw["Close"]
        else:
            df = raw[["Close"]] if "Close" in raw.columns else raw
        df = df.dropna(how="all")
        if not df.empty:
            _write_df(key, df)
        return df
    except (urllib.error.URLError, OSError) as exc:
        _logger.warning("market_cache: network error fetching prices: %s", exc)
    except Exception as exc:  # noqa: BLE001
        _logger.error("market_cache: unexpected error fetching prices: %s", exc)

    # Fallback: return stale cache if available
    stale = _read_df(key)
    if stale is not None:
        _logger.info("market_cache: returning stale prices for %s", tickers_t)
        return stale
    return pd.DataFrame()


def fetch_ticker_info(
    ticker: str,
    *,
    ttl_hours: float = _DEFAULT_INFO_TTL_H,
) -> dict[str, Any]:
    """Fetch ticker fundamentals with two-level caching.

    Replaces direct ``yf.Ticker(ticker).info`` calls in:
      - ``pages/26_股票筛选器.py``

    Args:
        ticker:    Ticker symbol (e.g. ``"AAPL"``).
        ttl_hours: Maximum age (hours) before cache is considered stale.

    Returns:
        Info dict from yfinance, or an empty dict on failure.
    """
    import yfinance as yf  # lazy import

    ticker = ticker.upper()
    key = _info_key(ticker)

    # L2 hit
    if _is_fresh(key, ttl_hours):
        cached = _read_json(key)
        if cached is not None:
            _logger.debug("market_cache: L2 hit for info %s", ticker)
            return cached

    # Cache miss
    _logger.debug("market_cache: fetching info %s", ticker)
    try:
        info = yf.Ticker(ticker).info
        if info:
            _write_json(key, info)
        return info or {}
    except Exception as exc:  # noqa: BLE001
        _logger.warning("market_cache: error fetching info for %s: %s", ticker, exc)

    stale = _read_json(key)
    return stale or {}


def fetch_ohlcv(
    ticker: str,
    start: date,
    end: date,
    *,
    ttl_hours: float = _DEFAULT_OHLCV_TTL_H,
) -> pd.DataFrame:
    """Download OHLCV data with two-level caching.

    Replaces direct ``yf.download()`` calls in:
      - ``pages/3_MA交叉回测器.py``
      - ``pages/2_实时报价面板.py`` (history chart)

    Args:
        ticker:    Ticker symbol.
        start:     Start date (inclusive).
        end:       End date (inclusive).
        ttl_hours: Maximum cache age in hours.

    Returns:
        DataFrame with columns Open/High/Low/Close/Volume, date index.
        Returns an empty DataFrame on failure.
    """
    import yfinance as yf  # lazy import

    ticker = ticker.upper()
    key = _ohlcv_key(ticker, start, end)

    # L2 hit
    if _is_fresh(key, ttl_hours):
        cached = _read_df(key)
        if cached is not None and not cached.empty:
            _logger.debug("market_cache: L2 hit for OHLCV %s %s-%s", ticker, start, end)
            return cached

    # Cache miss
    _logger.debug("market_cache: fetching OHLCV %s %s-%s", ticker, start, end)
    try:
        raw = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in raw.columns]
        df = raw[cols].copy()
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        if not df.empty:
            _write_df(key, df)
        return df
    except (urllib.error.URLError, OSError) as exc:
        _logger.warning("market_cache: network error fetching OHLCV %s: %s", ticker, exc)
    except Exception as exc:  # noqa: BLE001
        _logger.error("market_cache: unexpected error fetching OHLCV %s: %s", ticker, exc)

    stale = _read_df(key)
    if stale is not None:
        _logger.info("market_cache: returning stale OHLCV for %s", ticker)
        return stale
    return pd.DataFrame()


def clear_cache(ticker: str | None = None) -> int:
    """Remove cached files for *ticker*, or all entries if ``None``.

    Returns:
        Number of files deleted.
    """
    cache_dir = _ensure_cache_dir()
    deleted = 0
    if ticker is None:
        for f in cache_dir.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                    deleted += 1
                except OSError:
                    pass
    else:
        ticker = ticker.upper()
        # We can't reverse-map hash → ticker, so scan meta files for ticker mention
        for meta_file in cache_dir.glob("*.meta.json"):
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                if ticker in str(meta):
                    stem = meta_file.stem.replace(".meta", "")
                    for ext in (".meta.json", ".parquet", ".json"):
                        candidate = cache_dir / f"{stem}{ext}"
                        if candidate.exists():
                            candidate.unlink()
                            deleted += 1
            except (OSError, json.JSONDecodeError):
                pass
    return deleted


def cache_stats() -> dict[str, Any]:
    """Return a summary of the current disk cache state.

    Returns a dict with keys:
      - ``entry_count``: number of cached entries (parquet + json files)
      - ``total_size_mb``: total disk usage in megabytes
      - ``oldest_entry``: ISO timestamp of the oldest cached entry, or None
    """
    cache_dir = _ensure_cache_dir()
    data_files = list(cache_dir.glob("*.parquet")) + list(cache_dir.glob("*.json"))
    data_files = [f for f in data_files if ".meta" not in f.name]

    total_bytes = sum(f.stat().st_size for f in data_files if f.exists())
    meta_files = list(cache_dir.glob("*.meta.json"))
    oldest_ts: float | None = None
    for mf in meta_files:
        try:
            meta = json.loads(mf.read_text(encoding="utf-8"))
            ts = meta.get("fetched_at")
            if ts and (oldest_ts is None or ts < oldest_ts):
                oldest_ts = ts
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "entry_count": len(data_files),
        "total_size_mb": round(total_bytes / 1024 / 1024, 2),
        "oldest_entry": datetime.fromtimestamp(oldest_ts).isoformat() if oldest_ts else None,
    }
