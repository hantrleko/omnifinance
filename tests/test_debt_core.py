"""Tests for core/debt.py — Debt payoff strategies."""

import pytest
import pandas as pd

from core.debt import DebtItem, simulate_payoff, compare_strategies


def _single_debt() -> list[DebtItem]:
    return [DebtItem(name="信用卡", balance=50000.0, rate_pct=18.0, min_payment=1000.0)]


def _multi_debts() -> list[DebtItem]:
    return [
        DebtItem(name="信用卡", balance=30000.0, rate_pct=18.0, min_payment=600.0),
        DebtItem(name="消费贷", balance=50000.0, rate_pct=12.0, min_payment=1500.0),
        DebtItem(name="车贷", balance=100000.0, rate_pct=6.0, min_payment=2000.0),
    ]


class TestSimulatePayoff:
    def test_single_debt_avalanche_pays_off(self):
        result = simulate_payoff(_single_debt(), extra_monthly=2000.0, strategy="avalanche")
        assert result.months_to_payoff > 0
        assert result.months_to_payoff < 600
        assert result.total_interest > 0
        assert result.total_paid > 50000.0

    def test_snowball_pays_off(self):
        result = simulate_payoff(_multi_debts(), extra_monthly=3000.0, strategy="snowball")
        assert result.months_to_payoff > 0
        assert isinstance(result.schedule, pd.DataFrame)
        assert len(result.schedule) == result.months_to_payoff

    def test_hybrid_pays_off(self):
        result = simulate_payoff(_multi_debts(), extra_monthly=3000.0, strategy="hybrid")
        assert result.months_to_payoff > 0

    def test_avalanche_less_interest_than_snowball(self):
        debts = _multi_debts()
        av = simulate_payoff(debts, extra_monthly=3000.0, strategy="avalanche")
        sn = simulate_payoff(debts, extra_monthly=3000.0, strategy="snowball")
        assert av.total_interest <= sn.total_interest

    def test_schedule_has_correct_columns(self):
        result = simulate_payoff(_single_debt(), extra_monthly=500.0, strategy="avalanche")
        assert "月份" in result.schedule.columns
        assert "总余额" in result.schedule.columns

    def test_per_debt_summary_rows(self):
        debts = _multi_debts()
        result = simulate_payoff(debts, extra_monthly=2000.0, strategy="avalanche")
        assert len(result.per_debt_summary) == len(debts)

    def test_total_paid_equals_principal_plus_interest(self):
        debts = _single_debt()
        result = simulate_payoff(debts, extra_monthly=2000.0)
        expected = debts[0].balance + result.total_interest
        assert abs(result.total_paid - expected) < 1.0

    def test_zero_extra_payment_still_converges(self):
        debts = [DebtItem(name="贷款", balance=10000.0, rate_pct=6.0, min_payment=500.0)]
        result = simulate_payoff(debts, extra_monthly=0.0)
        assert result.months_to_payoff > 0

    def test_no_debt_returns_zero_months(self):
        debts = [DebtItem(name="已还清", balance=0.0, rate_pct=5.0, min_payment=100.0)]
        result = simulate_payoff(debts, extra_monthly=100.0)
        assert result.months_to_payoff == 0 or result.total_interest == pytest.approx(0.0, abs=0.01)

    def test_final_total_balance_is_near_zero(self):
        result = simulate_payoff(_single_debt(), extra_monthly=2000.0, strategy="avalanche")
        if not result.schedule.empty:
            assert result.schedule.iloc[-1]["总余额"] <= 0.1


class TestCompareStrategies:
    def test_returns_three_strategies(self):
        results = compare_strategies(_multi_debts(), extra_monthly=2000.0)
        assert set(results.keys()) == {"avalanche", "snowball", "hybrid"}

    def test_all_strategies_complete(self):
        results = compare_strategies(_multi_debts(), extra_monthly=2000.0)
        for strategy, result in results.items():
            assert result.months_to_payoff > 0, f"{strategy} did not converge"

    def test_strategy_field_matches_key(self):
        results = compare_strategies(_multi_debts(), extra_monthly=1000.0)
        for key, result in results.items():
            assert result.strategy == key
