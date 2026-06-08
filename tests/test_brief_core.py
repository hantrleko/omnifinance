from datetime import date

from core.brief import build_decision_brief
from core.health import build_health_report
from core.opportunity import build_opportunity_radar
from core.stress import build_stress_report


def test_decision_brief_uses_defensive_mode_when_stress_is_critical():
    health = build_health_report(budget={"pct_save": 5}, retirement={"gap": 500_000, "extra_monthly": 6_000})
    opportunities = build_opportunity_radar(
        budget={"income": 12_000, "amt_save": 500, "pct_save": 4.2},
        retirement={"gap": 500_000, "extra_monthly": 6_000},
    )
    stress = build_stress_report(
        budget={"income": 12_000, "amt_save": 500, "pct_save": 4.2},
        networth={"net_worth": 5_000, "total_assets": 30_000},
    )

    brief = build_decision_brief(
        health_report=health,
        opportunity_report=opportunities,
        stress_report=stress,
        generated_on=date(2026, 6, 8),
    )

    assert brief.mode == "防守"
    assert brief.readiness_score is not None
    assert brief.readiness_score < 60
    assert "现金流防线" in brief.headline
    assert brief.priority_actions


def test_decision_brief_uses_growth_mode_when_base_is_healthy():
    health = build_health_report(
        budget={"pct_save": 35},
        retirement={"gap": 0, "extra_monthly": 0},
        networth={"total_assets": 2_000_000, "net_worth": 1_800_000},
        tax={"effective_rate": 4},
        insurance={"irr_pct": 4.5},
    )
    opportunities = build_opportunity_radar(
        budget={"income": 50_000, "amt_save": 18_000, "pct_save": 36},
        retirement={"gap": 0, "extra_monthly": 0},
        networth={"total_assets": 2_000_000, "net_worth": 1_800_000},
        tax={"effective_rate": 4},
        insurance={"irr_pct": 4.5, "total_premium": 30_000},
    )
    stress = build_stress_report(
        budget={"income": 50_000, "amt_save": 18_000, "pct_save": 36},
        networth={"total_assets": 2_000_000, "net_worth": 1_800_000},
    )

    brief = build_decision_brief(health_report=health, opportunity_report=opportunities, stress_report=stress)

    assert brief.mode == "增长"
    assert brief.readiness_score is not None
    assert brief.readiness_score >= 75
    assert "资产配置效率" in brief.headline


def test_decision_brief_markdown_contains_sections():
    brief = build_decision_brief(generated_on=date(2026, 6, 8))

    markdown = brief.to_markdown()

    assert "# OmniFinance 决策简报" in markdown
    assert "生成日期：2026-06-08" in markdown
    assert "## 关键发现" in markdown
    assert "## 优先行动" in markdown
    assert "不构成投资、税务或保险建议" in markdown


def test_decision_brief_deduplicates_priority_actions():
    opportunities = build_opportunity_radar(
        budget={"income": 10_000, "amt_save": 300, "pct_save": 3},
        retirement={"gap": 1_000_000, "extra_monthly": 7_000},
    )
    stress = build_stress_report(
        budget={"income": 10_000, "amt_save": 300, "pct_save": 3},
        networth={"net_worth": 2_000, "total_assets": 20_000},
    )

    brief = build_decision_brief(opportunity_report=opportunities, stress_report=stress)

    assert len(brief.priority_actions) == len(set(brief.priority_actions))
    assert len(brief.priority_actions) <= 5
