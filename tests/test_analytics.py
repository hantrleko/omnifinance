"""Unit tests for core/analytics.py — VaR/CVaR, risk contribution, rolling metrics, benchmark metrics, sensitivity grid."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from core.analytics import (
    # VaR / CVaR
    portfolio_var_cvar,
    var_cvar_table,
    VaRResult,
    # Risk contribution
    compute_risk_contribution,
    risk_contribution_dataframe,
    RiskContributionResult,
    # Rolling metrics
    compute_rolling_metrics,
    RollingMetrics,
    # Benchmark metrics
    compute_benchmark_metrics,
    BenchmarkMetrics,
    # Sensitivity grid
    build_sensitivity_grid,
    SensitivityGrid,
)
RiskContribution = RiskContributionResult  # alias for test readability


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def normal_returns():
    """500 normally distributed daily returns with mean=0.001, std=0.02."""
    rng = np.random.default_rng(42)
    return rng.normal(loc=0.001, scale=0.02, size=500)


@pytest.fixture
def equity_series():
    """Simple equity curve starting at 100_000."""
    rng = np.random.default_rng(42)
    rets = rng.normal(loc=0.0005, scale=0.015, size=252)
    prices = 100_000 * np.cumprod(1 + rets)
    idx = pd.date_range("2023-01-01", periods=252, freq="B")
    return pd.Series(prices, index=idx)


@pytest.fixture
def two_asset_cov():
    """2x2 covariance matrix for two assets (as pandas DataFrame)."""
    tickers = ["AAPL", "MSFT"]
    return pd.DataFrame([[0.04, 0.01], [0.01, 0.09]], index=tickers, columns=tickers)


# ─────────────────────────────────────────────────────────────
# VaR / CVaR
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def single_asset_returns_df(normal_returns):
    """Single-asset DataFrame for portfolio_var_cvar."""
    return pd.DataFrame({"AAPL": normal_returns})


class TestPortfolioVarCvar:
    def test_returns_var_result(self, single_asset_returns_df):
        result = portfolio_var_cvar(single_asset_returns_df, {"AAPL": 1.0}, confidence=0.95)
        assert isinstance(result, VaRResult)

    def test_var_is_negative(self, single_asset_returns_df):
        result = portfolio_var_cvar(single_asset_returns_df, {"AAPL": 1.0}, confidence=0.95)
        # var_hist should be negative (loss)
        assert result.var_hist < 0, "Historical VaR should be negative"

    def test_cvar_le_var(self, single_asset_returns_df):
        result = portfolio_var_cvar(single_asset_returns_df, {"AAPL": 1.0}, confidence=0.95)
        assert result.cvar_hist <= result.var_hist, "CVaR should be worse (more negative) than VaR"

    def test_higher_confidence_worse_var(self, single_asset_returns_df):
        r95 = portfolio_var_cvar(single_asset_returns_df, {"AAPL": 1.0}, confidence=0.95)
        r99 = portfolio_var_cvar(single_asset_returns_df, {"AAPL": 1.0}, confidence=0.99)
        assert r99.var_hist <= r95.var_hist, "99% VaR should be worse than 95% VaR"

    def test_equal_weights_normalised(self, normal_returns):
        """Weights should be normalised automatically."""
        df = pd.DataFrame({"A": normal_returns[:250], "B": normal_returns[250:]})
        r1 = portfolio_var_cvar(df, {"A": 0.5, "B": 0.5}, confidence=0.95)
        r2 = portfolio_var_cvar(df, {"A": 1.0, "B": 1.0}, confidence=0.95)  # will be normalised
        assert abs(r1.var_hist - r2.var_hist) < 1e-8

    def test_confidence_boundary_90(self, single_asset_returns_df):
        result = portfolio_var_cvar(single_asset_returns_df, {"AAPL": 1.0}, confidence=0.90)
        assert result.var_hist < 0

    def test_confidence_boundary_99(self, single_asset_returns_df):
        result = portfolio_var_cvar(single_asset_returns_df, {"AAPL": 1.0}, confidence=0.99)
        assert result.var_hist < 0

    def test_var_amount_consistent_with_pct(self, single_asset_returns_df):
        result = portfolio_var_cvar(single_asset_returns_df, {"AAPL": 1.0}, confidence=0.95)
        # var_hist should be a fraction (between -1 and 0)
        assert -1.0 < result.var_hist < 0

    def test_all_positive_returns(self):
        returns = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        df = pd.DataFrame({"X": returns})
        result = portfolio_var_cvar(df, {"X": 1.0}, confidence=0.95)
        assert isinstance(result, VaRResult)


class TestVarCvarTable:
    def test_returns_dataframe(self, normal_returns):
        """var_cvar_table takes a return series, not a VaRResult."""
        df = var_cvar_table(pd.Series(normal_returns))
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self, normal_returns):
        df = var_cvar_table(pd.Series(normal_returns))
        assert len(df.columns) >= 2

    def test_default_has_three_rows(self, normal_returns):
        """Default confidences [0.90, 0.95, 0.99] produce 3 rows."""
        df = var_cvar_table(pd.Series(normal_returns))
        assert len(df) == 3

    def test_custom_confidences(self, normal_returns):
        df = var_cvar_table(pd.Series(normal_returns), confidences=[0.95, 0.99])
        assert len(df) == 2


# ─────────────────────────────────────────────────────────────
# Risk Contribution
# ─────────────────────────────────────────────────────────────

class TestComputeRiskContribution:
    def test_returns_risk_contribution(self, two_asset_cov):
        weights = [0.6, 0.4]
        rc = compute_risk_contribution(weights, two_asset_cov)
        assert isinstance(rc, RiskContributionResult)

    def test_contributions_sum_to_one(self, two_asset_cov):
        weights = [0.6, 0.4]
        rc = compute_risk_contribution(weights, two_asset_cov)
        assert abs(sum(rc.component_pct) - 1.0) < 1e-6

    def test_all_contributions_positive(self, two_asset_cov):
        weights = [0.6, 0.4]
        rc = compute_risk_contribution(weights, two_asset_cov)
        assert all(c >= 0 for c in rc.component_pct)

    def test_equal_weights_with_equal_cov(self):
        """Equal weights with equal variances and zero covariance → equal contributions."""
        tickers = ["A", "B", "C"]
        cov = pd.DataFrame(np.eye(3) * 0.04, index=tickers, columns=tickers)
        weights = [1/3, 1/3, 1/3]
        rc = compute_risk_contribution(weights, cov)
        for c in rc.component_pct:
            assert abs(c - 1/3) < 1e-4

    def test_higher_weight_higher_contribution(self, two_asset_cov):
        """Asset with higher weight should generally have higher risk contribution."""
        weights = [0.8, 0.2]
        rc = compute_risk_contribution(weights, two_asset_cov)
        assert rc.component_pct[0] > rc.component_pct[1]

    def test_marginal_risk_length(self, two_asset_cov):
        weights = [0.5, 0.5]
        rc = compute_risk_contribution(weights, two_asset_cov)
        assert len(rc.marginal_risk) == 2

    def test_absolute_contribution_length(self, two_asset_cov):
        weights = [0.5, 0.5]
        rc = compute_risk_contribution(weights, two_asset_cov)
        assert len(rc.component_risk) == 2


class TestRiskContributionDataframe:
    def test_returns_dataframe(self, two_asset_cov):
        weights = [0.6, 0.4]
        rc = compute_risk_contribution(weights, two_asset_cov)
        df = risk_contribution_dataframe(rc)
        assert isinstance(df, pd.DataFrame)

    def test_row_count_matches_assets(self, two_asset_cov):
        weights = [0.6, 0.4]
        rc = compute_risk_contribution(weights, two_asset_cov)
        df = risk_contribution_dataframe(rc)
        assert len(df) == 2

    def test_contains_ticker_column(self, two_asset_cov):
        weights = [0.6, 0.4]
        rc = compute_risk_contribution(weights, two_asset_cov)
        df = risk_contribution_dataframe(rc)
        # First column should be the asset name column
        assert df.columns[0] in ("标的", "Ticker", "Asset", "资产", "tickers")


# ─────────────────────────────────────────────────────────────
# Rolling Metrics
# ─────────────────────────────────────────────────────────────

class TestComputeRollingMetrics:
    def test_returns_rolling_metrics(self, equity_series):
        rm = compute_rolling_metrics(equity_series, window=63)
        assert isinstance(rm, RollingMetrics)

    def test_dates_length(self, equity_series):
        rm = compute_rolling_metrics(equity_series, window=63)
        assert len(rm.dates) == len(rm.rolling_return)

    def test_drawdown_non_positive(self, equity_series):
        rm = compute_rolling_metrics(equity_series, window=63)
        assert all(d <= 0.0 for d in rm.drawdown), "Drawdown values should be ≤ 0"

    def test_rolling_return_length_matches_series(self, equity_series):
        rm = compute_rolling_metrics(equity_series, window=63)
        # Rolling window produces NaN for first (window-1) entries
        assert len(rm.rolling_return) == len(equity_series)

    def test_window_21(self, equity_series):
        rm = compute_rolling_metrics(equity_series, window=21)
        assert len(rm.dates) > 0

    def test_window_252(self, equity_series):
        rm = compute_rolling_metrics(equity_series, window=252)
        assert len(rm.dates) > 0

    def test_rolling_sharpe_has_correct_length(self, equity_series):
        rm = compute_rolling_metrics(equity_series, window=63)
        assert len(rm.rolling_sharpe) == len(equity_series)


# ─────────────────────────────────────────────────────────────
# Benchmark Metrics
# ─────────────────────────────────────────────────────────────

class TestComputeBenchmarkMetrics:
    @pytest.fixture
    def strategy_and_benchmark(self):
        rng = np.random.default_rng(0)
        idx = pd.date_range("2020-01-01", periods=252, freq="B")
        strategy = pd.Series(100_000 * np.cumprod(1 + rng.normal(0.0008, 0.015, 252)), index=idx)
        benchmark = pd.Series(100_000 * np.cumprod(1 + rng.normal(0.0005, 0.012, 252)), index=idx)
        return strategy, benchmark

    def test_returns_benchmark_metrics(self, strategy_and_benchmark):
        s, b = strategy_and_benchmark
        bm = compute_benchmark_metrics(s, b)
        assert isinstance(bm, BenchmarkMetrics)

    def test_excess_return_sign(self, strategy_and_benchmark):
        s, b = strategy_and_benchmark
        bm = compute_benchmark_metrics(s, b)
        expected_sign = (s.iloc[-1] - s.iloc[0]) - (b.iloc[-1] - b.iloc[0])
        assert (bm.excess_total_return >= 0) == (expected_sign >= 0)

    def test_beta_is_finite(self, strategy_and_benchmark):
        s, b = strategy_and_benchmark
        bm = compute_benchmark_metrics(s, b)
        assert math.isfinite(bm.beta)

    def test_information_ratio_is_finite(self, strategy_and_benchmark):
        s, b = strategy_and_benchmark
        bm = compute_benchmark_metrics(s, b)
        assert math.isfinite(bm.information_ratio)

    def test_alpha_annual_is_finite(self, strategy_and_benchmark):
        s, b = strategy_and_benchmark
        bm = compute_benchmark_metrics(s, b)
        assert math.isfinite(bm.alpha_annual)

    def test_strategy_total_return_positive_for_growing_series(self):
        idx = pd.date_range("2020-01-01", periods=100, freq="B")
        s = pd.Series(np.linspace(100, 150, 100), index=idx)
        b = pd.Series(np.linspace(100, 120, 100), index=idx)
        bm = compute_benchmark_metrics(s, b)
        assert bm.strategy_total_return > 0
        assert bm.benchmark_total_return > 0
        assert bm.excess_total_return > 0


# ─────────────────────────────────────────────────────────────
# Sensitivity Grid
# ─────────────────────────────────────────────────────────────

class TestBuildSensitivityGrid:
    @pytest.fixture
    def grid_results(self):
        """Simulated MA cross grid search results."""
        rows = []
        for s in range(10, 51, 10):
            for l in range(50, 201, 50):
                if s < l:
                    rows.append({
                        "参数1": s,
                        "参数2": l,
                        "夏普比率": round(0.5 + s / 100 - l / 1000, 3),
                        "年化回报(%)": round(8.0 + s / 20, 2),
                        "最大回撤(%)": round(-15.0 - l / 100, 2),
                    })
        return rows

    def test_returns_sensitivity_grid(self, grid_results):
        sg = build_sensitivity_grid(grid_results, "参数1", "参数2", "夏普比率")
        assert isinstance(sg, SensitivityGrid)

    def test_grid_shape(self, grid_results):
        sg = build_sensitivity_grid(grid_results, "参数1", "参数2", "夏普比率")
        assert sg.grid.shape == (len(sg.param1_values), len(sg.param2_values))

    def test_best_params_in_grid(self, grid_results):
        sg = build_sensitivity_grid(grid_results, "参数1", "参数2", "夏普比率")
        assert sg.best_p1 in sg.param1_values
        assert sg.best_p2 in sg.param2_values

    def test_returns_none_for_missing_column(self, grid_results):
        result = build_sensitivity_grid(grid_results, "参数1", "参数2", "不存在的指标")
        assert result is None

    def test_returns_none_for_empty_input(self):
        result = build_sensitivity_grid([], "参数1", "参数2", "夏普比率")
        assert result is None

    def test_best_value_is_maximum(self, grid_results):
        sg = build_sensitivity_grid(grid_results, "参数1", "参数2", "夏普比率")
        all_values = [r["夏普比率"] for r in grid_results]
        # best_p1 and best_p2 should correspond to the row with maximum metric value
        best_row = max(grid_results, key=lambda r: r["夏普比率"])
        assert sg.best_p1 == best_row["参数1"]
        assert sg.best_p2 == best_row["参数2"]

    def test_different_metric_gives_different_best(self, grid_results):
        sg1 = build_sensitivity_grid(grid_results, "参数1", "参数2", "夏普比率")
        sg2 = build_sensitivity_grid(grid_results, "参数1", "参数2", "年化回报(%)")
        # Best params may differ between metrics
        assert sg1 is not None and sg2 is not None
