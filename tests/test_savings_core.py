"""Tests for core/savings.py — monthly compound savings goal simulation."""

import pytest

from core.savings import calculate_savings_goal, SavingsResult


# ── Basic sanity ──────────────────────────────────────────

def test_returns_result_type():
    r = calculate_savings_goal(50_000, 1_000_000, 6.0, 10_000)
    assert isinstance(r, SavingsResult)


def test_goal_already_reached():
    r = calculate_savings_goal(1_000_000, 500_000, 6.0, 10_000)
    assert r.reached is True
    assert r.months_needed == 0
    assert r.total_deposited == 1_000_000
    assert r.total_interest == 0.0


def test_goal_reachable():
    r = calculate_savings_goal(50_000, 1_000_000, 6.0, 10_000)
    assert r.reached is True
    assert r.months_needed > 0


def test_never_reachable():
    """Zero deposit and zero rate → impossible to reach goal."""
    r = calculate_savings_goal(0, 1_000_000, 0.0, 0.0)
    assert r.reached is False
    assert r.months_needed == -1


def test_months_positive_and_reasonable():
    r = calculate_savings_goal(0, 120_000, 0.0, 10_000)
    # With no interest, pure saving: 12 months exactly
    assert r.months_needed == 12


def test_schedule_not_empty():
    r = calculate_savings_goal(50_000, 1_000_000, 6.0, 10_000)
    assert not r.schedule.empty
    assert not r.yearly.empty


def test_schedule_columns():
    r = calculate_savings_goal(50_000, 1_000_000, 6.0, 10_000)
    assert set(["月数", "余额", "当月利息", "当月投入", "纯储蓄余额"]).issubset(r.schedule.columns)


# ── Compound effect ───────────────────────────────────────

def test_higher_rate_reaches_faster():
    r_low = calculate_savings_goal(50_000, 1_000_000, 2.0, 10_000)
    r_high = calculate_savings_goal(50_000, 1_000_000, 10.0, 10_000)
    assert r_high.months_needed < r_low.months_needed


def test_higher_deposit_reaches_faster():
    r_low = calculate_savings_goal(50_000, 1_000_000, 6.0, 5_000)
    r_high = calculate_savings_goal(50_000, 1_000_000, 6.0, 20_000)
    assert r_high.months_needed < r_low.months_needed


def test_interest_positive_when_rate_positive():
    r = calculate_savings_goal(0, 100_000, 6.0, 10_000)
    assert r.total_interest > 0


def test_zero_interest_no_interest_earned():
    r = calculate_savings_goal(0, 120_000, 0.0, 10_000)
    assert r.total_interest == pytest.approx(0.0, abs=1e-6)


# ── Edge: high starting balance ───────────────────────────

def test_large_initial_close_to_goal():
    # 99% of goal already saved
    r = calculate_savings_goal(990_000, 1_000_000, 6.0, 10_000)
    assert r.reached is True
    assert r.months_needed <= 3  # should reach very quickly


# ── Yearly summary ────────────────────────────────────────

def test_yearly_summary_has_data():
    r = calculate_savings_goal(50_000, 200_000, 6.0, 5_000)
    assert len(r.yearly) >= 1


def test_yearly_balance_increases():
    r = calculate_savings_goal(0, 500_000, 5.0, 5_000)
    balances = r.yearly["年末余额"].tolist()
    for i in range(1, len(balances)):
        assert balances[i] >= balances[i - 1]
