"""Tests for core/education.py — Education fund planning."""

import pytest
import pandas as pd

from core.education import EducationFundResult, calculate_education_fund


def _default_params() -> dict:
    return dict(
        child_age=5,
        target_age=18,
        current_cost=80000.0,
        education_inflation_pct=5.0,
        current_savings=50000.0,
        monthly_saving=3000.0,
        annual_return_pct=6.0,
    )


class TestCalculateEducationFund:
    def test_returns_result_type(self):
        result = calculate_education_fund(**_default_params())
        assert isinstance(result, EducationFundResult)

    def test_years_to_goal_correct(self):
        result = calculate_education_fund(**_default_params())
        assert result.years_to_goal == 13

    def test_future_cost_higher_than_current(self):
        p = _default_params()
        result = calculate_education_fund(**p)
        current_total = p["current_cost"] * 4
        assert result.future_cost > current_total

    def test_future_cost_matches_inflation(self):
        p = _default_params()
        result = calculate_education_fund(**p)
        expected = p["current_cost"] * (1 + p["education_inflation_pct"] / 100) ** 13 * 4
        assert abs(result.future_cost - expected) < 1.0

    def test_gap_positive_when_savings_insufficient(self):
        p = _default_params()
        p["current_savings"] = 0.0
        p["monthly_saving"] = 100.0
        result = calculate_education_fund(**p)
        assert result.gap > 0

    def test_gap_zero_when_savings_sufficient(self):
        p = _default_params()
        p["current_savings"] = 2_000_000.0
        p["monthly_saving"] = 20000.0
        result = calculate_education_fund(**p)
        assert result.gap <= 0

    def test_monthly_needed_zero_when_surplus(self):
        p = _default_params()
        p["current_savings"] = 2_000_000.0
        p["monthly_saving"] = 20000.0
        result = calculate_education_fund(**p)
        assert result.monthly_needed == pytest.approx(0.0)

    def test_monthly_needed_positive_when_gap(self):
        p = _default_params()
        p["current_savings"] = 0.0
        p["monthly_saving"] = 0.0
        result = calculate_education_fund(**p)
        assert result.monthly_needed > 0

    def test_schedule_length(self):
        result = calculate_education_fund(**_default_params())
        assert len(result.schedule) == result.years_to_goal + 1

    def test_schedule_columns(self):
        result = calculate_education_fund(**_default_params())
        expected_cols = {"年份", "孩子年龄", "年初余额", "当年投入", "当年收益", "年末余额", "目标值"}
        assert expected_cols.issubset(set(result.schedule.columns))

    def test_scholarship_scenarios_default(self):
        result = calculate_education_fund(**_default_params())
        assert len(result.scholarship_scenarios) == 5
        assert "奖学金比例" in result.scholarship_scenarios.columns

    def test_scholarship_scenarios_custom(self):
        result = calculate_education_fund(**_default_params(), scholarship_pcts=[0, 50, 100])
        assert len(result.scholarship_scenarios) == 3

    def test_child_age_equals_target_uses_one_year(self):
        p = _default_params()
        p["child_age"] = 18
        p["target_age"] = 18
        result = calculate_education_fund(**p)
        assert result.years_to_goal == 1

    def test_zero_inflation(self):
        p = _default_params()
        p["education_inflation_pct"] = 0.0
        result = calculate_education_fund(**p)
        expected_cost = p["current_cost"] * 4
        assert abs(result.future_cost - expected_cost) < 1.0

    def test_zero_return_rate(self):
        p = _default_params()
        p["annual_return_pct"] = 0.0
        result = calculate_education_fund(**p)
        assert result.projected_fund > 0
