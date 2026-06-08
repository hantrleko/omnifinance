from core.stress import build_stress_report


def _fmt(value: float) -> str:
    return f"¥{value:,.0f}"


def test_stress_report_returns_empty_without_budget_or_networth():
    report = build_stress_report()

    assert report.scenarios == ()
    assert report.weakest_scenario is None
    assert report.summary == "暂无足够数据进行压力测试"


def test_stress_report_builds_income_and_expense_scenarios():
    report = build_stress_report(
        budget={"income": 20_000, "amt_save": 2_000, "pct_save": 10},
        networth={"net_worth": 40_000, "total_assets": 100_000},
        money_formatter=_fmt,
    )

    keys = {scenario.key for scenario in report.scenarios}

    assert {"income_drop", "expense_spike", "asset_drawdown"} <= keys
    assert report.monthly_expense == 18_000
    assert report.liquid_buffer == 10_000
    assert report.critical_count >= 1
    assert report.weakest_scenario is not None


def test_stress_report_adds_loan_payment_shock():
    report = build_stress_report(
        budget={"income": 30_000, "amt_save": 10_000, "pct_save": 33.3},
        loan={"monthly_payment": 8_000, "total_interest": 300_000},
        networth={"net_worth": 500_000, "total_assets": 800_000},
        money_formatter=_fmt,
    )

    loan_scenario = next(scenario for scenario in report.scenarios if scenario.key == "loan_payment_shock")

    assert loan_scenario.estimated_impact == 14_400
    assert loan_scenario.page_key == "loan"
    assert loan_scenario.status == "safe"


def test_stress_report_routes_asset_drawdown_to_retirement_when_gap_exists():
    report = build_stress_report(
        budget={"income": 18_000, "amt_save": 4_000, "pct_save": 22.2},
        retirement={"gap": 600_000, "extra_monthly": 3_000},
        networth={"net_worth": 300_000, "total_assets": 500_000},
        money_formatter=_fmt,
    )

    drawdown = next(scenario for scenario in report.scenarios if scenario.key == "asset_drawdown")

    assert drawdown.page_key == "retirement"
    assert drawdown.estimated_impact == 45_000
    assert "退休" in drawdown.narrative


def test_stress_report_summary_mentions_weakest_scenario():
    report = build_stress_report(
        budget={"income": 12_000, "amt_save": 500, "pct_save": 4.2},
        networth={"net_worth": 5_000, "total_assets": 50_000},
        money_formatter=_fmt,
    )

    assert report.weakest_scenario is not None
    assert report.weakest_scenario.title in report.summary
    assert "高压场景" in report.summary
