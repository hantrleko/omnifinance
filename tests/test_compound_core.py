import math

from core.compound import add_annualized_return, compute_schedule


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
