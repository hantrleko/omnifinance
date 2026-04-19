"""Tests for core/scenarios.py — Cross-tool scenario analysis."""

import pytest
import pandas as pd

from core.scenarios import ScenarioResult, run_inflation_scenarios, run_return_scenarios


class TestRunInflationScenarios:
    def test_returns_correct_type(self):
        result = run_inflation_scenarios([1.0, 2.0, 3.0])
        assert isinstance(result, ScenarioResult)

    def test_parameter_name(self):
        result = run_inflation_scenarios([1.0, 2.0])
        assert result.parameter_name == "通胀率(%)"

    def test_values_match_input(self):
        inflations = [0.5, 2.0, 5.0]
        result = run_inflation_scenarios(inflations)
        assert result.values == inflations

    def test_lengths_match(self):
        inflations = [1.0, 2.0, 3.0, 4.0]
        result = run_inflation_scenarios(inflations)
        assert len(result.compound_finals) == len(inflations)
        assert len(result.savings_months) == len(inflations)
        assert len(result.retirement_gaps) == len(inflations)

    def test_summary_dataframe_shape(self):
        inflations = [1.0, 2.0, 3.0]
        result = run_inflation_scenarios(inflations)
        assert isinstance(result.summary, pd.DataFrame)
        assert len(result.summary) == 3

    def test_summary_columns(self):
        result = run_inflation_scenarios([2.0])
        cols = set(result.summary.columns)
        assert "通胀率(%)" in cols
        assert "复利实际终值" in cols
        assert "储蓄达成月数" in cols
        assert "退休缺口" in cols

    def test_higher_inflation_reduces_compound_real_value(self):
        result = run_inflation_scenarios([1.0, 5.0])
        assert result.compound_finals[0] >= result.compound_finals[1]

    def test_single_inflation_value(self):
        result = run_inflation_scenarios([3.0])
        assert len(result.compound_finals) == 1

    def test_zero_inflation(self):
        result = run_inflation_scenarios([0.0])
        assert result.compound_finals[0] > 0


class TestRunReturnScenarios:
    def test_returns_correct_type(self):
        result = run_return_scenarios([4.0, 6.0, 8.0])
        assert isinstance(result, ScenarioResult)

    def test_parameter_name(self):
        result = run_return_scenarios([5.0])
        assert result.parameter_name == "收益率(%)"

    def test_lengths_match(self):
        returns = [3.0, 5.0, 7.0, 9.0]
        result = run_return_scenarios(returns)
        assert len(result.compound_finals) == len(returns)
        assert len(result.savings_months) == len(returns)
        assert len(result.retirement_gaps) == len(returns)

    def test_summary_dataframe(self):
        result = run_return_scenarios([6.0, 8.0])
        assert isinstance(result.summary, pd.DataFrame)
        assert len(result.summary) == 2

    def test_summary_columns(self):
        result = run_return_scenarios([5.0])
        cols = set(result.summary.columns)
        assert "收益率(%)" in cols
        assert "复利终值" in cols
        assert "储蓄达成月数" in cols
        assert "退休缺口" in cols

    def test_higher_return_increases_compound_final(self):
        result = run_return_scenarios([3.0, 8.0])
        assert result.compound_finals[1] > result.compound_finals[0]

    def test_higher_return_reduces_savings_months(self):
        result = run_return_scenarios([2.0, 10.0])
        assert result.savings_months[1] <= result.savings_months[0]

    def test_higher_return_reduces_retirement_gap(self):
        result = run_return_scenarios([3.0, 9.0])
        assert result.retirement_gaps[1] <= result.retirement_gaps[0]
