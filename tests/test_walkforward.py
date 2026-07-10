"""Unit tests for core/walkforward.py — walk-forward out-of-sample validation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.walkforward import (
    WalkForwardResult,
    overfit_verdict,
    run_walk_forward,
    walk_forward_table,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

def _make_price_df(n: int = 600, seed: int = 7, drift: float = 0.0005) -> pd.DataFrame:
    """Synthetic OHLCV frame with a mild upward drift."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(loc=drift, scale=0.015, size=n)
    close = 100.0 * np.cumprod(1.0 + rets)
    idx = pd.bdate_range("2021-01-04", periods=n)
    return pd.DataFrame(
        {
            "Open": close * (1 + rng.normal(0, 0.002, n)),
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": rng.integers(1e5, 1e6, n).astype(float),
        },
        index=idx,
    )


@pytest.fixture
def price_df() -> pd.DataFrame:
    return _make_price_df()


MA_GRID = {"short_window": [5, 10], "long_window": [20, 40]}


# ─────────────────────────────────────────────────────────────
# run_walk_forward
# ─────────────────────────────────────────────────────────────

class TestRunWalkForward:
    def test_basic_run(self, price_df):
        result = run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=3)
        assert isinstance(result, WalkForwardResult)
        assert 1 <= len(result.windows) <= 3
        assert result.strategy == "MA 交叉"

    def test_windows_chronological_and_non_overlapping(self, price_df):
        result = run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=3)
        for w in result.windows:
            assert w.train_start < w.train_end < w.test_start < w.test_end
        for prev, cur in zip(result.windows, result.windows[1:], strict=False):
            assert prev.test_end <= cur.train_start or prev.fold < cur.fold

    def test_best_params_come_from_grid(self, price_df):
        result = run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=3)
        for w in result.windows:
            assert w.best_params["short_window"] in MA_GRID["short_window"]
            assert w.best_params["long_window"] in MA_GRID["long_window"]

    def test_oos_equity_positive_and_monotone_index(self, price_df):
        result = run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=3)
        assert (result.oos_equity > 0).all()
        assert result.oos_equity.index.is_monotonic_increasing

    def test_consistency_bounds(self, price_df):
        result = run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=3)
        assert 0.0 <= result.consistency_pct <= 100.0

    def test_rsi_strategy(self, price_df):
        grid = {"period": [7, 14], "oversold": [30], "overbought": [70]}
        result = run_walk_forward(price_df, "RSI", grid, n_folds=3)
        assert len(result.windows) >= 1

    def test_invalid_fold_count_raises(self, price_df):
        with pytest.raises(ValueError, match="窗口"):
            run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=1)

    def test_bad_train_ratio_raises(self, price_df):
        with pytest.raises(ValueError, match="train_ratio"):
            run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=3, train_ratio=0.3)

    def test_insufficient_data_raises(self):
        small = _make_price_df(n=100)
        with pytest.raises(ValueError, match="数据量不足"):
            run_walk_forward(small, "MA 交叉", MA_GRID, n_folds=4)

    def test_degenerate_grid_raises(self, price_df):
        bad_grid = {"short_window": [50], "long_window": [20]}  # short >= long
        with pytest.raises(ValueError, match="参数网格"):
            run_walk_forward(price_df, "MA 交叉", bad_grid, n_folds=3)

    def test_max_combos_cap(self, price_df):
        big_grid = {"short_window": list(range(3, 15)), "long_window": list(range(20, 80, 5))}
        result = run_walk_forward(price_df, "MA 交叉", big_grid, n_folds=2, max_combos=10)
        assert len(result.windows) >= 1

    def test_fees_reduce_returns(self, price_df):
        free = run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=3)
        costly = run_walk_forward(
            price_df, "MA 交叉", MA_GRID, n_folds=3, fee_rate_pct=1.0, slippage_pct=1.0
        )
        assert costly.oos_total_return_pct <= free.oos_total_return_pct + 1e-9


# ─────────────────────────────────────────────────────────────
# walk_forward_table
# ─────────────────────────────────────────────────────────────

class TestTable:
    def test_table_columns_and_rows(self, price_df):
        result = run_walk_forward(price_df, "MA 交叉", MA_GRID, n_folds=3)
        table = walk_forward_table(result)
        assert len(table) == len(result.windows)
        for col in ("窗口", "训练区间", "测试区间", "最优参数", "训练收益(%)", "测试收益(%)"):
            assert col in table.columns


# ─────────────────────────────────────────────────────────────
# overfit_verdict
# ─────────────────────────────────────────────────────────────

def _fake_result(avg_train: float, avg_test: float, consistency: float) -> WalkForwardResult:
    ratio = avg_test / avg_train if avg_train > 1e-9 else float("nan")
    return WalkForwardResult(
        windows=(),
        oos_equity=pd.Series([1.0]),
        avg_train_return_pct=avg_train,
        avg_test_return_pct=avg_test,
        oos_total_return_pct=avg_test,
        overfit_ratio=ratio,
        consistency_pct=consistency,
        strategy="MA 交叉",
    )


class TestVerdict:
    def test_good(self):
        level, msg = overfit_verdict(_fake_result(10.0, 8.0, 75.0))
        assert level == "good"
        assert msg

    def test_warning(self):
        level, _ = overfit_verdict(_fake_result(10.0, 3.0, 50.0))
        assert level == "warning"

    def test_bad(self):
        level, _ = overfit_verdict(_fake_result(20.0, 0.5, 20.0))
        assert level == "bad"

    def test_nan_ratio_positive_oos(self):
        level, _ = overfit_verdict(_fake_result(0.0, 5.0, 60.0))
        assert level == "warning"

    def test_nan_ratio_negative_oos(self):
        level, _ = overfit_verdict(_fake_result(0.0, -5.0, 10.0))
        assert level == "bad"
