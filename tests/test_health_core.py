from core.health import build_action_recommendations, build_health_report


def _fmt(value: float) -> str:
    return f"¥{value:,.0f}"


def test_build_health_report_scores_multiple_dimensions():
    report = build_health_report(
        budget={"pct_save": 25},
        retirement={"gap": 100_000, "extra_monthly": 3_000},
        networth={"total_assets": 500_000, "net_worth": 250_000},
        tax={"effective_rate": 18},
        insurance={"irr_pct": 2.0},
        money_formatter=_fmt,
    )

    assert report.overall_score == 53
    assert report.overall_grade == "🟠 一般"
    assert [dimension.name for dimension in report.dimensions] == [
        "💡 储蓄能力",
        "🏖️ 退休准备度",
        "💳 负债水平",
        "🏠 净资产水平",
        "🧾 税务效率",
        "🛡️ 保险效益",
    ]
    assert report.improvement_tips
    assert "¥3,000" in report.dimensions[1].tip


def test_build_health_report_handles_empty_input():
    report = build_health_report()

    assert report.dimensions == ()
    assert report.overall_score is None
    assert report.overall_grade == ""
    assert report.improvement_tips == ()


def test_action_recommendations_prioritize_low_scores():
    report = build_health_report(
        budget={"pct_save": 5},
        retirement={"gap": 300_000, "extra_monthly": 6_000},
        networth={"total_assets": 100_000, "net_worth": -20_000},
        insurance={"irr_pct": 1.0},
    )

    recommendations = build_action_recommendations(report, limit=2)

    assert len(recommendations) == 2
    assert recommendations[0].page_key == "networth"
    assert recommendations[0].priority == "高"
    assert {item.page_key for item in recommendations} <= {"budget", "retirement", "debt", "networth", "insurance"}


def test_action_recommendations_offer_growth_action_when_healthy():
    report = build_health_report(
        budget={"pct_save": 35},
        retirement={"gap": 0, "extra_monthly": 0},
        networth={"total_assets": 2_000_000, "net_worth": 1_800_000},
        tax={"effective_rate": 4},
        insurance={"irr_pct": 4.5},
    )

    recommendations = build_action_recommendations(report)

    assert len(recommendations) == 1
    assert recommendations[0].page_key == "portfolio"
    assert recommendations[0].priority == "低"
