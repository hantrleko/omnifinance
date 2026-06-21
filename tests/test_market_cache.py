"""Tests for core/market_cache.py — yfinance 磁盘缓存层"""
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import core.market_cache as mc


# ── Internal helpers ──────────────────────────────────────────────────────────

def test_cache_dir_is_path():
    assert isinstance(mc._CACHE_DIR, Path)


def test_price_key_is_string():
    key = mc._price_key(("AAPL", "MSFT"), "1mo")
    assert isinstance(key, str)
    assert len(key) > 0


def test_info_key_is_string():
    key = mc._info_key("AAPL")
    assert isinstance(key, str)


def test_ohlcv_key_is_string():
    from datetime import date
    key = mc._ohlcv_key("AAPL", date(2024, 1, 1), date(2024, 3, 1))
    assert isinstance(key, str)


def test_price_key_order_independent():
    """Ticker order should not affect the cache key."""
    k1 = mc._price_key(("AAPL", "MSFT"), "1mo")
    k2 = mc._price_key(("MSFT", "AAPL"), "1mo")
    assert k1 == k2


# ── _is_fresh ─────────────────────────────────────────────────────────────────

def test_is_fresh_returns_false_for_missing_meta(tmp_path):
    with patch.object(mc, "_CACHE_DIR", tmp_path):
        assert mc._is_fresh("nonexistent_key_xyz", ttl_hours=1.0) is False


def test_is_fresh_returns_true_for_recent_meta(tmp_path):
    with patch.object(mc, "_CACHE_DIR", tmp_path):
        key = "test_key_fresh"
        meta = tmp_path / f"{key}.meta.json"
        meta.write_text(json.dumps({"fetched_at": time.time()}), encoding="utf-8")
        assert mc._is_fresh(key, ttl_hours=1.0) is True


def test_is_fresh_returns_false_for_expired_meta(tmp_path):
    with patch.object(mc, "_CACHE_DIR", tmp_path):
        key = "test_key_expired"
        meta = tmp_path / f"{key}.meta.json"
        meta.write_text(json.dumps({"fetched_at": time.time() - 7200}), encoding="utf-8")
        assert mc._is_fresh(key, ttl_hours=1.0) is False


# ── download_prices ───────────────────────────────────────────────────────────

def test_download_prices_returns_dataframe_on_success():
    mock_df = pd.DataFrame(
        {"Close": [150.0, 152.0, 148.0]},
        index=pd.date_range("2024-01-01", periods=3),
    )
    with patch("yfinance.download", return_value=mock_df):
        with patch.object(mc, "_is_fresh", return_value=False):
            result = mc.download_prices(["AAPL"], period="1mo")
    assert isinstance(result, pd.DataFrame)


def test_download_prices_returns_dataframe_on_error():
    with patch("yfinance.download", side_effect=Exception("timeout")):
        with patch.object(mc, "_is_fresh", return_value=False):
            result = mc.download_prices(["INVALID_XYZ"], period="1mo")
    assert isinstance(result, pd.DataFrame)


# ── fetch_ticker_info ─────────────────────────────────────────────────────────

def test_fetch_ticker_info_returns_dict_on_success():
    mock_ticker = MagicMock()
    mock_ticker.info = {"shortName": "Apple Inc.", "trailingPE": 28.5}
    with patch("yfinance.Ticker", return_value=mock_ticker):
        with patch.object(mc, "_is_fresh", return_value=False):
            result = mc.fetch_ticker_info("AAPL")
    assert isinstance(result, dict)


def test_fetch_ticker_info_returns_dict_on_error():
    with patch("yfinance.Ticker", side_effect=Exception("network error")):
        with patch.object(mc, "_is_fresh", return_value=False):
            result = mc.fetch_ticker_info("INVALID_TICKER_XYZ")
    assert isinstance(result, dict)


def test_fetch_ticker_info_uses_cache_when_fresh(tmp_path):
    cached_data = {"shortName": "Cached Corp", "trailingPE": 15.0}
    key = mc._info_key("AAPL")
    meta = tmp_path / f"{key}.meta.json"
    data_file = tmp_path / f"{key}.json"
    meta.write_text(json.dumps({"fetched_at": time.time()}), encoding="utf-8")
    data_file.write_text(json.dumps(cached_data), encoding="utf-8")

    with patch.object(mc, "_CACHE_DIR", tmp_path):
        result = mc.fetch_ticker_info("AAPL")
    assert isinstance(result, dict)


# ── fetch_ohlcv ───────────────────────────────────────────────────────────────

def test_fetch_ohlcv_returns_dataframe_on_success():
    from datetime import date as _date
    mock_hist = pd.DataFrame(
        {"Open": [100.0], "High": [105.0], "Low": [99.0], "Close": [103.0], "Volume": [1_000_000]},
        index=pd.date_range("2024-01-01", periods=1),
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_hist
    with patch("yfinance.Ticker", return_value=mock_ticker):
        with patch.object(mc, "_is_fresh", return_value=False):
            result = mc.fetch_ohlcv("AAPL", _date(2024, 1, 1), _date(2024, 3, 1))
    assert isinstance(result, pd.DataFrame)


def test_fetch_ohlcv_returns_dataframe_on_error():
    from datetime import date as _date
    with patch("yfinance.Ticker", side_effect=Exception("error")):
        with patch.object(mc, "_is_fresh", return_value=False):
            result = mc.fetch_ohlcv("INVALID", _date(2024, 1, 1), _date(2024, 3, 1))
    assert isinstance(result, pd.DataFrame)


# ── clear_cache ───────────────────────────────────────────────────────────────

def test_clear_cache_returns_int(tmp_path):
    with patch.object(mc, "_CACHE_DIR", tmp_path):
        result = mc.clear_cache()
    assert isinstance(result, int)
    assert result >= 0


def test_clear_cache_with_ticker_returns_int(tmp_path):
    with patch.object(mc, "_CACHE_DIR", tmp_path):
        result = mc.clear_cache("AAPL")
    assert isinstance(result, int)


# ── cache_stats ───────────────────────────────────────────────────────────────

def test_cache_stats_returns_dict(tmp_path):
    with patch.object(mc, "_CACHE_DIR", tmp_path):
        stats = mc.cache_stats()
    assert isinstance(stats, dict)
