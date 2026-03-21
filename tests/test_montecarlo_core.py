"""Tests for core/montecarlo.py — Monte Carlo retirement simulation."""

import math
import pytest

from core.montecarlo import run_retirement_montecarlo, MonteCarloResult


# ── Fixtures ──────────────────────────────────────────────

BASE = dict(
    current_age=35,
    retire_age=65,
    life_expectancy=85,
    current_assets=500_000,
    monthly_saving=10_000,
    monthly_expense_today=30_000,
    inflation_pct=2.5,
    expected_annual_return_pct=7.0,
    annual_volatility_pct=15.0,
    post_return_pct=4.0,
    post_volatility_pct=8.0,
    n_simulations=500,  # Keep small for test speed
    seed=42,
)


# ── Basic sanity ──────────────────────────────────────────

def test_returns_result_type():
    r = run_retirement_montecarlo(**BASE)
    assert isinstance(r, MonteCarloResult)


def test_success_rate_between_0_and_1():
    r = run_retirement_montecarlo(**BASE)
    assert 0.0 <= r.success_rate <= 1.0


def test_n_success_consistent():
    r = run_retirement_montecarlo(**BASE)
    assert r.n_success <= r.n_simulations
    assert abs(r.n_success / r.n_simulations - r.success_rate) < 1e-9


def test_percentile_paths_shape():
    r = run_retirement_montecarlo(**BASE)
    total_years = BASE["life_expectancy"] - BASE["current_age"]
    assert len(r.percentile_paths) == total_years + 1
    assert set(r.percentile_paths.columns) == {"年龄", "p10", "p25", "p50", "p75", "p90"}


def test_percentile_ordering():
    """p10 <= p25 <= p50 <= p75 <= p90 at every age."""
    r = run_retirement_montecarlo(**BASE)
    fp = r.percentile_paths
    assert (fp["p10"] <= fp["p25"]).all()
    assert (fp["p25"] <= fp["p50"]).all()
    assert (fp["p50"] <= fp["p75"]).all()
    assert (fp["p75"] <= fp["p90"]).all()


def test_initial_balance_correct():
    """First row of percentile paths should equal current_assets (all sims start same)."""
    r = run_retirement_montecarlo(**BASE)
    first_row = r.percentile_paths.iloc[0]
    assert first_row["年龄"] == BASE["current_age"]
    # All percentiles should equal current_assets at age 0 (no variance yet)
    assert math.isclose(first_row["p50"], BASE["current_assets"], rel_tol=1e-9)


# ── Edge cases ────────────────────────────────────────────

def test_zero_volatility_deterministic():
    """Zero volatility → all percentile bands converge to the same value."""
    r = run_retirement_montecarlo(
        **{**BASE, "annual_volatility_pct": 0.0, "post_volatility_pct": 0.0}
    )
    fp = r.percentile_paths
    # At zero volatility, p10 == p90 throughout (or very close due to log-normal approx)
    assert ((fp["p90"] - fp["p10"]).abs() < 1.0).all()


def test_high_success_with_large_savings():
    r = run_retirement_montecarlo(
        **{**BASE, "monthly_saving": 100_000, "current_assets": 5_000_000}
    )
    assert r.success_rate > 0.8


def test_low_success_with_zero_savings():
    r = run_retirement_montecarlo(
        **{**BASE, "monthly_saving": 0, "current_assets": 0,
           "monthly_expense_today": 100_000}
    )
    assert r.success_rate < 0.5


def test_reproducible_with_seed():
    r1 = run_retirement_montecarlo(**BASE)
    r2 = run_retirement_montecarlo(**BASE)
    assert r1.success_rate == r2.success_rate


def test_none_seed_varies():
    """Without a fixed seed, two runs may differ (not guaranteed but very likely)."""
    r1 = run_retirement_montecarlo(**{**BASE, "seed": None, "n_simulations": 200})
    r2 = run_retirement_montecarlo(**{**BASE, "seed": None, "n_simulations": 200})
    # Can't guarantee they differ, but success rates should be in valid range
    assert 0 <= r1.success_rate <= 1
    assert 0 <= r2.success_rate <= 1


def test_median_depletion_age_nan_when_sufficient():
    r = run_retirement_montecarlo(
        **{**BASE, "monthly_saving": 50_000, "current_assets": 3_000_000,
           "expected_annual_return_pct": 8.0}
    )
    # Expect no median depletion
    import math
    assert math.isnan(r.median_depletion_age)
