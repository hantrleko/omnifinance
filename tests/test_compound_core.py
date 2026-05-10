"""Unit tests for :mod:`core.compound`.

Covers happy paths plus boundary / robustness cases:
- Zero / one-year horizons
- Inflation column toggling
- Mismatched compound vs contribution frequencies
- Annualised-return helper edge cases
"""

import math

import pandas as pd
import pytest

from core.compound import add_annualized_return, compute_schedule

# ── Happy paths ─────────────────────────────────────────────

def test_lump_sum_one_year_annual_compound():
    schedule = compute_schedule(principal=1000, annual_rate_pct=10, years=1, compound_freq=1)
    final_balance = schedule.iloc[-1]["年末余额"]
    assert math.isclose(final_balance, 1100.0, rel_tol=1e-9)


def test_regular_contribution_monthly_no_interest():
    schedule = compute_schedule(
        principal=0,
        annual_rate_pct=0,
        years=1,
        compound_freq=12,
        contribution=100,
        contrib_freq=12,
    )
    final = schedule.iloc[-1]
    assert math.isclose(final["累计投入"], 1200.0, rel_tol=1e-9)
    assert math.isclose(final["年末余额"], 1200.0, rel_tol=1e-9)


def test_add_annualized_return_column_exists_and_value():
    schedule = compute_schedule(principal=1000, annual_rate_pct=10, years=1, compound_freq=1)
    schedule = add_annualized_return(schedule)
    assert "年化收益率(%)" in schedule.columns
    assert math.isclose(schedule.iloc[-1]["年化收益率(%)"], 10.0, rel_tol=1e-9)


# ── Schedule shape ──────────────────────────────────────────

def test_schedule_has_year_zero_and_n_rows():
    """Schedule should always include the year-0 baseline row."""
    schedule = compute_schedule(principal=1000, annual_rate_pct=5, years=10, compound_freq=12)
    assert len(schedule) == 11  # year 0 .. year 10
    assert schedule.iloc[0]["年份"] == 0
    assert math.isclose(schedule.iloc[0]["年末余额"], 1000.0, rel_tol=1e-12)


def test_inflation_column_only_appears_when_nonzero():
    """`实际购买力` column should be omitted when inflation is 0."""
    no_inflation = compute_schedule(
        principal=1000, annual_rate_pct=5, years=5, compound_freq=12, inflation_pct=0.0
    )
    with_inflation = compute_schedule(
        principal=1000, annual_rate_pct=5, years=5, compound_freq=12, inflation_pct=3.0
    )
    assert "实际购买力" not in no_inflation.columns
    assert "实际购买力" in with_inflation.columns
    # Real purchasing power should be strictly less than nominal balance after inflation
    final_row = with_inflation.iloc[-1]
    assert final_row["实际购买力"] < final_row["年末余额"]


# ── Boundary / edge cases ───────────────────────────────────

def test_zero_principal_zero_contribution_returns_zeros():
    schedule = compute_schedule(
        principal=0, annual_rate_pct=10, years=5, compound_freq=12, contribution=0
    )
    assert math.isclose(schedule.iloc[-1]["年末余额"], 0.0, abs_tol=1e-12)
    assert math.isclose(schedule.iloc[-1]["累计投入"], 0.0, abs_tol=1e-12)


def test_zero_year_horizon_returns_baseline_only():
    """A 0-year horizon should still return the year-0 baseline row."""
    schedule = compute_schedule(principal=500, annual_rate_pct=5, years=0, compound_freq=12)
    assert len(schedule) == 1
    assert math.isclose(schedule.iloc[0]["年末余额"], 500.0, rel_tol=1e-12)


def test_quarterly_contribution_with_monthly_compounding():
    """Quarterly contribution + monthly compounding: 4 contribs/year of $100 = $400."""
    schedule = compute_schedule(
        principal=0,
        annual_rate_pct=0,
        years=1,
        compound_freq=12,
        contribution=100,
        contrib_freq=4,
    )
    final = schedule.iloc[-1]
    assert math.isclose(final["累计投入"], 400.0, rel_tol=1e-9)
    assert math.isclose(final["年末余额"], 400.0, rel_tol=1e-9)


def test_annual_contribution_with_annual_compounding():
    """Annual contribution + annual compounding sanity check."""
    schedule = compute_schedule(
        principal=0,
        annual_rate_pct=0,
        years=3,
        compound_freq=1,
        contribution=1000,
        contrib_freq=1,
    )
    assert math.isclose(schedule.iloc[-1]["累计投入"], 3000.0, rel_tol=1e-9)
    assert math.isclose(schedule.iloc[-1]["年末余额"], 3000.0, rel_tol=1e-9)


def test_total_contributions_monotonic_non_decreasing():
    """Cumulative contribution must never decrease year-over-year."""
    schedule = compute_schedule(
        principal=1000,
        annual_rate_pct=5,
        years=10,
        compound_freq=12,
        contribution=200,
        contrib_freq=12,
    )
    cum = schedule["累计投入"].tolist()
    assert all(cum[i] <= cum[i + 1] for i in range(len(cum) - 1))


def test_balance_grows_with_positive_rate():
    """With positive rate and zero contributions, end balance must exceed principal."""
    schedule = compute_schedule(
        principal=1000, annual_rate_pct=5, years=10, compound_freq=12
    )
    assert schedule.iloc[-1]["年末余额"] > 1000.0


# ── add_annualized_return edge cases ────────────────────────

def test_annualized_return_year_zero_is_zero():
    """The baseline year-0 row should have a 0 annualised return."""
    schedule = compute_schedule(principal=1000, annual_rate_pct=10, years=3, compound_freq=1)
    schedule = add_annualized_return(schedule)
    assert math.isclose(schedule.iloc[0]["年化收益率(%)"], 0.0, abs_tol=1e-12)


def test_annualized_return_does_not_mutate_input():
    """`add_annualized_return` must return a copy — input must be untouched."""
    schedule = compute_schedule(principal=1000, annual_rate_pct=5, years=3, compound_freq=12)
    cols_before = list(schedule.columns)
    _ = add_annualized_return(schedule)
    assert list(schedule.columns) == cols_before


def test_annualized_return_handles_zero_starting_basis():
    """A zero-basis year must safely report 0% rather than dividing by zero."""
    df = pd.DataFrame(
        [
            {"年份": 0, "年初余额": 0.0, "当年投入": 0.0, "当年利息": 0.0, "年末余额": 0.0, "累计投入": 0.0},
            {"年份": 1, "年初余额": 0.0, "当年投入": 0.0, "当年利息": 0.0, "年末余额": 0.0, "累计投入": 0.0},
        ]
    )
    out = add_annualized_return(df)
    assert math.isclose(out.iloc[1]["年化收益率(%)"], 0.0, abs_tol=1e-12)


# ── Numerical robustness ────────────────────────────────────

@pytest.mark.parametrize("freq", [1, 2, 4, 12])
def test_no_negative_balance_for_supported_freqs(freq):
    schedule = compute_schedule(
        principal=10_000,
        annual_rate_pct=8,
        years=5,
        compound_freq=freq,
        contribution=500,
        contrib_freq=freq,
    )
    assert (schedule["年末余额"] >= 0).all()
