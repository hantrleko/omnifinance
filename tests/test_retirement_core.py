"""Tests for core/retirement.py — dual-phase retirement calculation."""

import math
import pytest

from core.retirement import calculate_retirement, RetirementResult


# ── Fixtures ──────────────────────────────────────────────

BASE = dict(
    current_age=35,
    retire_age=65,
    life_expectancy=85,
    current_assets=500_000,
    monthly_saving=10_000,
    monthly_expense_today=30_000,
    inflation_pct=2.5,
    pre_return_pct=7.0,
    post_return_pct=4.0,
)


# ── Basic sanity ──────────────────────────────────────────

def test_returns_result_type():
    r = calculate_retirement(**BASE)
    assert isinstance(r, RetirementResult)


def test_years_computed_correctly():
    r = calculate_retirement(**BASE)
    assert r.years_to_retire == BASE["retire_age"] - BASE["current_age"]
    assert r.years_in_retire == BASE["life_expectancy"] - BASE["retire_age"]


def test_projected_positive():
    r = calculate_retirement(**BASE)
    assert r.projected_at_retire > 0


def test_total_needed_positive():
    r = calculate_retirement(**BASE)
    assert r.total_needed_at_retire > 0


def test_accumulation_path_length():
    r = calculate_retirement(**BASE)
    expected_rows = BASE["retire_age"] - BASE["current_age"] + 1  # inclusive of year 0
    assert len(r.accumulation_path) == expected_rows


def test_full_path_covers_lifespan():
    r = calculate_retirement(**BASE)
    max_age = r.full_path["年龄"].max()
    assert max_age == BASE["life_expectancy"]


# ── Gap & extra_monthly logic ─────────────────────────────

def test_gap_positive_when_insufficient():
    # Very low saving → should have a gap
    r = calculate_retirement(**{**BASE, "monthly_saving": 0, "current_assets": 0})
    assert r.gap > 0
    assert r.extra_monthly_needed > 0


def test_no_extra_monthly_when_sufficient():
    # Very high saving → no gap
    r = calculate_retirement(**{**BASE, "monthly_saving": 100_000, "current_assets": 5_000_000})
    assert r.gap <= 0
    assert r.extra_monthly_needed == 0.0


# ── Edge cases ────────────────────────────────────────────

def test_zero_return_rates():
    r = calculate_retirement(**{**BASE, "pre_return_pct": 0.0, "post_return_pct": 0.0})
    assert r.projected_at_retire > 0


def test_zero_inflation():
    r = calculate_retirement(**{**BASE, "inflation_pct": 0.0})
    assert r.future_monthly_expense == pytest.approx(BASE["monthly_expense_today"])


def test_inflation_increases_future_expense():
    r_low = calculate_retirement(**{**BASE, "inflation_pct": 0.0})
    r_high = calculate_retirement(**{**BASE, "inflation_pct": 5.0})
    assert r_high.future_monthly_expense > r_low.future_monthly_expense


def test_higher_return_lowers_gap():
    r_low = calculate_retirement(**{**BASE, "pre_return_pct": 3.0})
    r_high = calculate_retirement(**{**BASE, "pre_return_pct": 10.0})
    assert r_high.gap < r_low.gap


def test_retire_one_year_ahead():
    """Edge: only 1 year to retirement."""
    r = calculate_retirement(**{**BASE, "current_age": 64, "retire_age": 65})
    assert r.years_to_retire == 1
    assert r.projected_at_retire > 0


def test_paths_not_empty():
    r = calculate_retirement(**BASE)
    assert not r.accumulation_path.empty
    assert not r.target_path.empty
    assert not r.full_path.empty
