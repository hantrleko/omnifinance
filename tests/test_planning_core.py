import math

from core.planning import calculate_budget, calculate_loan


def test_calculate_budget_basic_split():
    plan = calculate_budget(income=10000, fixed_expense=3000, pct_needs=50, pct_wants=30)
    assert math.isclose(plan.amt_needs, 5000)
    assert math.isclose(plan.amt_wants, 3000)
    assert math.isclose(plan.amt_save, 2000)
    assert plan.pct_save == 20
    assert math.isclose(plan.remaining_needs, 2000)


def test_calculate_loan_zero_rate_equal_principal_interest():
    schedule, summary = calculate_loan(
        principal=120000,
        annual_rate_pct=0.0,
        years=1,
        periods_per_year=12,
        method="等额本息",
    )
    assert len(schedule) == 12
    assert math.isclose(summary["总还款"], 120000.0, rel_tol=1e-9)
    assert math.isclose(summary["总利息"], 0.0, abs_tol=1e-9)
