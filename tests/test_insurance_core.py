import math

from core.insurance import analyze_insurance_plan


def test_insurance_protection_metrics_basic():
    result = analyze_insurance_plan(
        annual_premium=10000,
        pay_years=20,
        coverage_years=30,
        sum_assured=1_000_000,
        inflation_pct=2.0,
        alt_return_pct=4.0,
        maturity_benefit=300000,
    )
    assert math.isclose(result.protection.total_premium, 200000)
    assert math.isclose(result.protection.coverage_cost_per_10k, 2000)
    assert math.isclose(result.protection.break_even_claim_prob, 0.2)
    assert len(result.yearly_schedule) == 30


def test_insurance_alt_investment_above_total_premium_when_return_positive():
    result = analyze_insurance_plan(
        annual_premium=12000,
        pay_years=10,
        coverage_years=20,
        sum_assured=500000,
        inflation_pct=2.5,
        alt_return_pct=5.0,
        maturity_benefit=150000,
    )
    assert result.protection.alt_investment_value > result.protection.total_premium


def test_insurance_savings_net_gain_and_irr_direction():
    result = analyze_insurance_plan(
        annual_premium=10000,
        pay_years=10,
        coverage_years=10,
        sum_assured=300000,
        inflation_pct=2.0,
        alt_return_pct=3.0,
        maturity_benefit=120000,
    )
    assert math.isclose(result.savings.net_gain, 20000)
    assert result.savings.irr_pct > 0
