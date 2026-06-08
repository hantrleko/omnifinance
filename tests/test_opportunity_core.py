from core.opportunity import build_90_day_sprint, build_opportunity_radar


def _fmt(value: float) -> str:
    return f"¥{value:,.0f}"


def test_opportunity_radar_prioritizes_retirement_pressure():
    report = build_opportunity_radar(
        budget={"income": 20_000, "amt_save": 2_000, "pct_save": 10},
        retirement={"gap": 1_200_000, "extra_monthly": 6_000},
        money_formatter=_fmt,
    )

    assert report.opportunities
    assert report.top_opportunity is not None
    assert report.top_opportunity.key == "retirement_gap"
    assert report.top_opportunity.priority == "高"
    assert "退休缺口" in report.summary


def test_opportunity_radar_detects_low_savings_gap():
    report = build_opportunity_radar(
        budget={"income": 10_000, "amt_save": 800, "pct_save": 8},
        money_formatter=_fmt,
    )

    savings_opportunity = next(item for item in report.opportunities if item.key == "raise_savings_rate")

    assert savings_opportunity.metric_value == "¥1,200/月"
    assert savings_opportunity.page_key == "budget"
    assert savings_opportunity.confidence == 92


def test_opportunity_radar_detects_debt_and_tax_opportunities():
    report = build_opportunity_radar(
        budget={"income": 15_000, "amt_save": 2_000, "pct_save": 13.3},
        loan={"monthly_payment": 5_000, "total_interest": 400_000},
        tax={"effective_rate": 22, "annual_tax": 80_000},
        money_formatter=_fmt,
    )

    keys = {item.key for item in report.opportunities}

    assert "debt_acceleration" in keys
    assert "tax_efficiency" in keys
    assert report.high_priority_count >= 1


def test_opportunity_radar_returns_empty_report_when_no_signals():
    report = build_opportunity_radar(
        budget={"income": 30_000, "amt_save": 9_000, "pct_save": 30},
        retirement={"gap": 0, "extra_monthly": 0},
        tax={"effective_rate": 8, "annual_tax": 20_000},
        insurance={"irr_pct": 4.0, "total_premium": 30_000},
    )

    assert report.opportunities == ()
    assert report.top_opportunity is None
    assert report.summary == "暂无明显机会，建议继续补充数据"


def test_build_90_day_sprint_uses_top_three_opportunities():
    report = build_opportunity_radar(
        budget={"income": 12_000, "amt_save": 600, "pct_save": 5},
        loan={"monthly_payment": 4_500, "total_interest": 300_000},
        savings={"months_needed": 84, "total_interest": 20_000},
        retirement={"gap": 800_000, "extra_monthly": 5_000},
        networth={"net_worth": 10_000, "total_assets": 100_000},
        tax={"effective_rate": 25, "annual_tax": 100_000},
        insurance={"irr_pct": 1.5, "total_premium": 120_000},
    )

    sprint = build_90_day_sprint(report)

    assert len(sprint) == 3
    assert [step.phase for step in sprint] == ["0-30 天", "31-60 天", "61-90 天"]
    assert all(step.checklist for step in sprint)
    assert [step.page_key for step in sprint] == [item.page_key for item in report.opportunities[:3]]
