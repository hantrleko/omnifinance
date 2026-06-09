from core.action_plan import build_action_impact_plan
from core.health import build_health_report
from core.opportunity import build_opportunity_radar
from core.stress import build_stress_report


def test_action_plan_prioritizes_emergency_buffer_when_stress_is_weak():
    budget = {"income": 12_000, "amt_save": 400, "pct_save": 3.3}
    networth = {"net_worth": 4_000, "total_assets": 25_000}
    health = build_health_report(budget=budget, networth=networth)
    stress = build_stress_report(budget=budget, networth=networth)

    plan = build_action_impact_plan(budget=budget, networth=networth, health_report=health, stress_report=stress)

    assert plan.actions
    assert plan.top_action is not None
    assert plan.top_action.key == "emergency_buffer_sprint"
    assert plan.top_action.priority == "高"
    assert plan.momentum_score is not None
    assert plan.momentum_score > plan.baseline_score


def test_action_plan_generates_savings_and_debt_actions():
    budget = {"income": 20_000, "amt_save": 2_000, "pct_save": 10}
    loan = {"monthly_payment": 6_000, "total_interest": 300_000}
    health = build_health_report(budget=budget)

    plan = build_action_impact_plan(budget=budget, loan=loan, health_report=health)
    keys = {action.key for action in plan.actions}

    assert "savings_rate_lift" in keys
    assert "debt_acceleration_test" in keys
    assert plan.total_estimated_uplift > 0


def test_action_plan_falls_back_to_growth_review_for_healthy_base():
    health = build_health_report(
        budget={"pct_save": 35},
        retirement={"gap": 0, "extra_monthly": 0},
        networth={"total_assets": 2_000_000, "net_worth": 1_800_000},
        tax={"effective_rate": 4},
        insurance={"irr_pct": 4.5},
    )

    plan = build_action_impact_plan(health_report=health)

    assert plan.actions
    assert plan.top_action is not None
    assert plan.top_action.key == "growth_review"
    assert plan.top_action.priority == "低"
    assert plan.momentum_score is not None


def test_action_plan_can_use_opportunity_fallback_and_export_markdown():
    opportunities = build_opportunity_radar(
        budget={"income": 10_000, "amt_save": 500, "pct_save": 5},
        retirement={"gap": 600_000, "extra_monthly": 5_500},
    )

    plan = build_action_impact_plan(opportunity_report=opportunities)
    markdown = plan.to_markdown()

    assert plan.actions
    assert plan.top_action is not None
    assert plan.top_action.key.startswith("opportunity_")
    assert "# OmniFinance 行动影响模拟" in markdown
    assert "## 推荐行动" in markdown
    assert "预计总提升" in markdown
