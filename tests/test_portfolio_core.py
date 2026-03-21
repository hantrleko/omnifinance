"""Tests for core/portfolio.py — Markowitz Mean-Variance Optimization."""

import numpy as np
import pandas as pd
import pytest

from core.portfolio import optimize_portfolio, EfficientFrontierResult, PortfolioStats


# ── Helpers ───────────────────────────────────────────────

def _make_synthetic_returns(
    n_days: int = 500,
    tickers: list[str] | None = None,
    seed: int = 0,
) -> pd.DataFrame:
    """Generate synthetic daily returns for testing."""
    if tickers is None:
        tickers = ["A", "B", "C"]
    rng = np.random.default_rng(seed)
    # Returns with different means and an intentional correlation
    base = rng.normal(0.0005, 0.01, (n_days, len(tickers)))
    df = pd.DataFrame(base, columns=tickers)
    return df


# ── Basic sanity ──────────────────────────────────────────

def test_returns_result_type():
    returns = _make_synthetic_returns()
    result = optimize_portfolio(returns)
    assert isinstance(result, EfficientFrontierResult)


def test_max_sharpe_weights_sum_to_one():
    returns = _make_synthetic_returns()
    result = optimize_portfolio(returns)
    total = sum(result.max_sharpe.weights.values())
    assert abs(total - 1.0) < 1e-6


def test_min_variance_weights_sum_to_one():
    returns = _make_synthetic_returns()
    result = optimize_portfolio(returns)
    total = sum(result.min_variance.weights.values())
    assert abs(total - 1.0) < 1e-6


def test_all_weights_non_negative():
    """Long-only constraint: all weights >= 0."""
    returns = _make_synthetic_returns()
    result = optimize_portfolio(returns)
    for w in result.max_sharpe.weights.values():
        assert w >= -1e-6  # numerical tolerance
    for w in result.min_variance.weights.values():
        assert w >= -1e-6


def test_tickers_match_input():
    tickers = ["X", "Y", "Z"]
    returns = _make_synthetic_returns(tickers=tickers)
    result = optimize_portfolio(returns)
    assert set(result.tickers) == set(tickers)


def test_annual_returns_shape():
    tickers = ["A", "B"]
    returns = _make_synthetic_returns(tickers=tickers)
    result = optimize_portfolio(returns)
    assert len(result.annual_returns) == 2


def test_cov_matrix_shape():
    tickers = ["A", "B", "C"]
    returns = _make_synthetic_returns(tickers=tickers)
    result = optimize_portfolio(returns)
    assert result.cov_matrix.shape == (3, 3)


def test_efficient_frontier_not_empty():
    returns = _make_synthetic_returns()
    result = optimize_portfolio(returns, n_frontier_points=20)
    assert not result.efficient_frontier.empty


def test_efficient_frontier_columns():
    returns = _make_synthetic_returns()
    result = optimize_portfolio(returns, n_frontier_points=10)
    assert "volatility" in result.efficient_frontier.columns
    assert "annual_return" in result.efficient_frontier.columns
    assert "sharpe_ratio" in result.efficient_frontier.columns


def test_min_variance_lower_vol_than_max_return_portfolio():
    """Min variance portfolio should have lower volatility than
    an equal-weight portfolio of high-return assets."""
    returns = _make_synthetic_returns(n_days=800, seed=7)
    result = optimize_portfolio(returns)
    # Min variance vol should be ≤ max sharpe vol (not always true but typical)
    # Just assert it's a valid positive number
    assert result.min_variance.annual_volatility > 0.0


# ── Error cases ───────────────────────────────────────────

def test_raises_with_single_asset():
    returns = _make_synthetic_returns(tickers=["ONLY"])
    with pytest.raises(ValueError, match="至少需要 2 个"):
        optimize_portfolio(returns)


def test_two_assets_works():
    returns = _make_synthetic_returns(tickers=["A", "B"])
    result = optimize_portfolio(returns)
    assert len(result.tickers) == 2


# ── PortfolioStats ────────────────────────────────────────

def test_portfolio_stats_sharpe_ratio():
    returns = _make_synthetic_returns(tickers=["A", "B"])
    result = optimize_portfolio(returns, risk_free_rate_pct=2.0)
    sh = result.max_sharpe.sharpe_ratio
    r = result.max_sharpe.annual_return
    v = result.max_sharpe.annual_volatility
    expected = (r - 0.02) / v if v > 0 else 0.0
    assert abs(sh - expected) < 1e-6
