"""Unit tests for core.rebalance — rebalancing strategy simulation engine.

All tests are pure-computation (no Streamlit, no network).
"""
from __future__ import annotations

import numpy as np
import pytest

from core.rebalance import (
    generate_monthly_returns,
    run_all_strategies,
    simulate_strategy,
)


# ── generate_monthly_returns ──────────────────────────────

class TestGenerateMonthlyReturns:
    def test_shape(self):
        r = generate_monthly_returns([0.10], [0.20], 12)
        assert r.shape == (12, 1)

    def test_multi_asset_shape(self):
        r = generate_monthly_returns([0.10, 0.04], [0.20, 0.05], 24)
        assert r.shape == (24, 2)

    def test_deterministic_with_seed(self):
        r1 = generate_monthly_returns([0.10], [0.20], 12, seed=42)
        r2 = generate_monthly_returns([0.10], [0.20], 12, seed=42)
        np.testing.assert_array_equal(r1, r2)

    def test_different_seeds_differ(self):
        r1 = generate_monthly_returns([0.10], [0.20], 12, seed=1)
        r2 = generate_monthly_returns([0.10], [0.20], 12, seed=2)
        assert not np.array_equal(r1, r2)

    def test_zero_volatility_near_deterministic(self):
        """With near-zero vol, all monthly returns should be close to mu/12."""
        r = generate_monthly_returns([0.12], [1e-9], 12, seed=0)
        expected_monthly = np.log(1 + 0.12) / 12
        # exp(mu_m) - 1 ≈ mu_m for small values
        for val in r[:, 0]:
            assert abs(val - (np.exp(expected_monthly) - 1)) < 1e-4


# ── simulate_strategy ─────────────────────────────────────

class TestSimulateStrategy:
    """Tests for simulate_strategy with a simple deterministic return matrix."""

    @pytest.fixture
    def flat_returns(self):
        """12 months of zero returns — portfolio value stays constant."""
        return np.zeros((12, 2))

    @pytest.fixture
    def params(self):
        return {
            "initial_value": 100_000.0,
            "target_weights": [0.6, 0.4],
            "rebal_fee_pct": 0.0,
            "threshold_pct": 5.0,
        }

    def test_output_length(self, flat_returns, params):
        vals, _, _, _ = simulate_strategy("buy_and_hold", monthly_returns=flat_returns, **params)
        assert len(vals) == 13  # initial + 12 months

    def test_zero_returns_constant_value(self, flat_returns, params):
        vals, _, _, _ = simulate_strategy("buy_and_hold", monthly_returns=flat_returns, **params)
        for v in vals:
            assert v == pytest.approx(100_000.0, rel=1e-6)

    def test_buy_and_hold_no_rebalancing(self, flat_returns, params):
        _, count, fees, _ = simulate_strategy("buy_and_hold", monthly_returns=flat_returns, **params)
        assert count == 0
        assert fees == pytest.approx(0.0)

    def test_monthly_rebalances_every_month(self, flat_returns, params):
        _, count, _, _ = simulate_strategy("monthly", monthly_returns=flat_returns, **params)
        assert count == 12

    def test_quarterly_rebalances_4_times(self, flat_returns, params):
        _, count, _, _ = simulate_strategy("quarterly", monthly_returns=flat_returns, **params)
        assert count == 4

    def test_annually_rebalances_once(self, flat_returns, params):
        _, count, _, _ = simulate_strategy("annually", monthly_returns=flat_returns, **params)
        assert count == 1

    def test_fees_deducted(self):
        """With 1% fee and monthly rebalancing, fees should be non-zero."""
        returns = np.zeros((12, 1))
        _, _, fees, _ = simulate_strategy(
            "monthly",
            initial_value=100_000.0,
            target_weights=[1.0],
            monthly_returns=returns,
            rebal_fee_pct=1.0,
        )
        assert fees > 0

    def test_track_weights_length(self, flat_returns, params):
        _, _, _, wh = simulate_strategy("buy_and_hold", monthly_returns=flat_returns, track_weights=True, **params)
        assert wh is not None
        assert len(wh) == 12

    def test_track_weights_none_when_disabled(self, flat_returns, params):
        _, _, _, wh = simulate_strategy("buy_and_hold", monthly_returns=flat_returns, track_weights=False, **params)
        assert wh is None

    def test_threshold_no_rebalance_when_no_drift(self, flat_returns, params):
        """Flat returns → no drift → threshold strategy should not rebalance."""
        _, count, _, _ = simulate_strategy("threshold", monthly_returns=flat_returns, **params)
        assert count == 0

    def test_threshold_rebalances_on_drift(self):
        """Construct a return matrix that causes drift beyond 5 %."""
        # Asset 0 gains 20 % in month 1, asset 1 stays flat.
        # New weights: 0.5*1.2 / (0.5*1.2 + 0.5) = 0.6 / 1.1 ≈ 0.545
        # Drift = 0.545 - 0.5 = 0.045 < 0.05, so we need a larger gain.
        # Asset 0 gains 50 %: new weight = 0.75 / 1.25 = 0.60 → drift = 0.10 > 0.05
        returns = np.zeros((12, 2))
        returns[0, 0] = 0.50  # 50 % gain in month 1
        _, count, _, _ = simulate_strategy(
            "threshold",
            initial_value=100_000.0,
            target_weights=[0.5, 0.5],
            monthly_returns=returns,
            threshold_pct=5.0,
        )
        assert count >= 1


# ── run_all_strategies ────────────────────────────────────

class TestRunAllStrategies:
    @pytest.fixture
    def setup(self):
        returns = generate_monthly_returns([0.10, 0.04], [0.20, 0.05], 120, seed=42)
        return {
            "initial_value": 1_000_000.0,
            "target_weights": [0.6, 0.4],
            "monthly_returns": returns,
            "years": 10,
            "rebal_fee_pct": 0.1,
            "threshold_pct": 5.0,
        }

    def test_returns_five_strategies(self, setup):
        results = run_all_strategies(**setup)
        assert set(results.keys()) == {"buy_and_hold", "annually", "quarterly", "monthly", "threshold"}

    def test_each_result_has_required_keys(self, setup):
        results = run_all_strategies(**setup)
        required = {"label", "values", "rebal_count", "total_fees", "final", "total_return", "ann_return"}
        for key, data in results.items():
            assert required.issubset(data.keys()), f"Missing keys in strategy '{key}'"

    def test_final_value_positive(self, setup):
        results = run_all_strategies(**setup)
        for key, data in results.items():
            assert data["final"] > 0, f"Negative final value for strategy '{key}'"

    def test_buy_and_hold_zero_rebalances(self, setup):
        results = run_all_strategies(**setup)
        assert results["buy_and_hold"]["rebal_count"] == 0

    def test_monthly_most_rebalances(self, setup):
        results = run_all_strategies(**setup)
        assert results["monthly"]["rebal_count"] >= results["quarterly"]["rebal_count"]
        assert results["quarterly"]["rebal_count"] >= results["annually"]["rebal_count"]

    def test_ann_return_reasonable(self, setup):
        """Annualised return should be in a plausible range (-50 % to +100 %)."""
        results = run_all_strategies(**setup)
        for key, data in results.items():
            assert -50 < data["ann_return"] < 100, f"Implausible ann_return for '{key}'"
