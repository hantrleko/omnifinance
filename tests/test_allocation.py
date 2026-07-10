"""Unit tests for core/allocation.py — risk parity & Black-Litterman."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.allocation import (
    BlackLittermanResult,
    RiskParityResult,
    View,
    allocation_comparison_table,
    black_litterman,
    implied_equilibrium_returns,
    risk_parity_weights,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def cov_3assets() -> pd.DataFrame:
    """Annualised covariance for 3 assets with distinct vol levels."""
    tickers = ["LOW", "MID", "HIGH"]
    vols = np.array([0.08, 0.16, 0.32])
    corr = np.array([
        [1.0, 0.3, 0.2],
        [0.3, 1.0, 0.4],
        [0.2, 0.4, 1.0],
    ])
    cov = np.outer(vols, vols) * corr
    return pd.DataFrame(cov, index=tickers, columns=tickers)


@pytest.fixture
def cov_2assets() -> pd.DataFrame:
    tickers = ["A", "B"]
    cov = np.array([[0.04, 0.0], [0.0, 0.09]])
    return pd.DataFrame(cov, index=tickers, columns=tickers)


# ─────────────────────────────────────────────────────────────
# Risk parity
# ─────────────────────────────────────────────────────────────

class TestRiskParity:
    def test_weights_sum_to_one_and_nonnegative(self, cov_3assets):
        result = risk_parity_weights(cov_3assets)
        assert isinstance(result, RiskParityResult)
        total = sum(result.weights.values())
        assert total == pytest.approx(1.0, abs=1e-6)
        assert all(w >= -1e-9 for w in result.weights.values())

    def test_equal_risk_contributions(self, cov_3assets):
        result = risk_parity_weights(cov_3assets)
        contribs = list(result.risk_contributions.values())
        for rc in contribs:
            assert rc == pytest.approx(1.0 / 3.0, abs=0.02)

    def test_low_vol_asset_gets_higher_weight(self, cov_3assets):
        result = risk_parity_weights(cov_3assets)
        assert result.weights["LOW"] > result.weights["MID"] > result.weights["HIGH"]

    def test_two_uncorrelated_assets_inverse_vol(self, cov_2assets):
        # With zero correlation, ERC weights ∝ 1/σ: σ_A=0.2, σ_B=0.3 → 0.6/0.4
        result = risk_parity_weights(cov_2assets)
        assert result.weights["A"] == pytest.approx(0.6, abs=0.02)
        assert result.weights["B"] == pytest.approx(0.4, abs=0.02)

    def test_custom_risk_budget(self, cov_2assets):
        result = risk_parity_weights(cov_2assets, risk_budget={"A": 0.8, "B": 0.2})
        # A should carry more risk → even higher weight than ERC
        assert result.risk_contributions["A"] == pytest.approx(0.8, abs=0.05)
        assert result.weights["A"] > 0.6

    def test_portfolio_volatility_positive(self, cov_3assets):
        result = risk_parity_weights(cov_3assets)
        assert result.portfolio_volatility > 0

    def test_single_asset_raises(self):
        cov = pd.DataFrame([[0.04]], index=["A"], columns=["A"])
        with pytest.raises(ValueError):
            risk_parity_weights(cov)

    def test_converges(self, cov_3assets):
        result = risk_parity_weights(cov_3assets)
        assert result.converged
        assert result.n_iterations > 0


# ─────────────────────────────────────────────────────────────
# Implied equilibrium returns
# ─────────────────────────────────────────────────────────────

class TestImpliedReturns:
    def test_pi_formula(self, cov_2assets):
        pi = implied_equilibrium_returns(cov_2assets, {"A": 0.5, "B": 0.5}, risk_aversion=2.0)
        # π = δ Σ w → A: 2*0.04*0.5 = 0.04 ; B: 2*0.09*0.5 = 0.09
        assert pi["A"] == pytest.approx(0.04)
        assert pi["B"] == pytest.approx(0.09)

    def test_weights_normalised(self, cov_2assets):
        pi1 = implied_equilibrium_returns(cov_2assets, {"A": 1.0, "B": 1.0})
        pi2 = implied_equilibrium_returns(cov_2assets, {"A": 0.5, "B": 0.5})
        pd.testing.assert_series_equal(pi1, pi2)

    def test_zero_weights_fall_back_to_equal(self, cov_2assets):
        pi = implied_equilibrium_returns(cov_2assets, {})
        assert (pi > 0).all()


# ─────────────────────────────────────────────────────────────
# Black-Litterman
# ─────────────────────────────────────────────────────────────

class TestBlackLitterman:
    def test_no_views_equals_prior(self, cov_3assets):
        mkt = {"LOW": 0.4, "MID": 0.35, "HIGH": 0.25}
        result = black_litterman(cov_3assets, mkt, views=None)
        assert isinstance(result, BlackLittermanResult)
        for t in cov_3assets.columns:
            assert result.posterior_returns[t] == pytest.approx(result.equilibrium_returns[t], abs=1e-9)

    def test_weights_sum_to_one(self, cov_3assets):
        mkt = {"LOW": 0.4, "MID": 0.35, "HIGH": 0.25}
        result = black_litterman(cov_3assets, mkt)
        assert sum(result.weights.values()) == pytest.approx(1.0, abs=1e-6)

    def test_bullish_view_raises_posterior_return(self, cov_3assets):
        mkt = {"LOW": 0.4, "MID": 0.35, "HIGH": 0.25}
        base = black_litterman(cov_3assets, mkt)
        bullish = black_litterman(
            cov_3assets,
            mkt,
            views=[View(assets={"MID": 1.0}, expected_return=0.50, confidence=0.9)],
        )
        assert bullish.posterior_returns["MID"] > base.posterior_returns["MID"]

    def test_bullish_view_increases_weight(self, cov_3assets):
        mkt = {"LOW": 0.4, "MID": 0.35, "HIGH": 0.25}
        base = black_litterman(cov_3assets, mkt)
        bullish = black_litterman(
            cov_3assets,
            mkt,
            views=[View(assets={"MID": 1.0}, expected_return=0.50, confidence=0.9)],
        )
        assert bullish.weights["MID"] > base.weights["MID"]

    def test_higher_confidence_stronger_tilt(self, cov_3assets):
        mkt = {"LOW": 0.4, "MID": 0.35, "HIGH": 0.25}
        weak = black_litterman(
            cov_3assets, mkt,
            views=[View(assets={"MID": 1.0}, expected_return=0.50, confidence=0.1)],
        )
        strong = black_litterman(
            cov_3assets, mkt,
            views=[View(assets={"MID": 1.0}, expected_return=0.50, confidence=0.95)],
        )
        assert strong.posterior_returns["MID"] > weak.posterior_returns["MID"]

    def test_relative_view(self, cov_3assets):
        mkt = {"LOW": 0.4, "MID": 0.35, "HIGH": 0.25}
        rel = black_litterman(
            cov_3assets, mkt,
            views=[View(assets={"LOW": 1.0, "HIGH": -1.0}, expected_return=0.10, confidence=0.8)],
        )
        base = black_litterman(cov_3assets, mkt)
        spread_rel = rel.posterior_returns["LOW"] - rel.posterior_returns["HIGH"]
        spread_base = base.posterior_returns["LOW"] - base.posterior_returns["HIGH"]
        assert spread_rel > spread_base

    def test_unknown_ticker_view_ignored(self, cov_3assets):
        mkt = {"LOW": 0.4, "MID": 0.35, "HIGH": 0.25}
        result = black_litterman(
            cov_3assets, mkt,
            views=[View(assets={"UNKNOWN": 1.0}, expected_return=0.5, confidence=0.9)],
        )
        for t in cov_3assets.columns:
            assert result.posterior_returns[t] == pytest.approx(result.equilibrium_returns[t], abs=1e-9)

    def test_single_asset_raises(self):
        cov = pd.DataFrame([[0.04]], index=["A"], columns=["A"])
        with pytest.raises(ValueError):
            black_litterman(cov, {"A": 1.0})

    def test_posterior_cov_shape(self, cov_3assets):
        mkt = {"LOW": 0.4, "MID": 0.35, "HIGH": 0.25}
        result = black_litterman(
            cov_3assets, mkt,
            views=[View(assets={"MID": 1.0}, expected_return=0.2, confidence=0.5)],
        )
        assert result.posterior_cov.shape == (3, 3)


# ─────────────────────────────────────────────────────────────
# Comparison table
# ─────────────────────────────────────────────────────────────

class TestComparisonTable:
    def test_basic(self):
        df = allocation_comparison_table({
            "方案A": {"AAPL": 0.6, "MSFT": 0.4},
            "方案B": {"AAPL": 0.3, "GOOG": 0.7},
        })
        assert set(df.index) == {"AAPL", "GOOG", "MSFT"}
        assert df.loc["GOOG", "方案A"] == 0.0
        assert df.loc["GOOG", "方案B"] == pytest.approx(0.7)

    def test_empty(self):
        assert allocation_comparison_table({}).empty
