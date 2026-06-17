"""Unit tests for core.moat — economic moat scoring engine.

These tests cover the pure-computation functions only; no Streamlit or
network calls are made.
"""
from __future__ import annotations

import math

import pytest

from core.moat import (
    compute_composite,
    score_segment,
    to_float,
    weighted_score,
)


# ── to_float ──────────────────────────────────────────────

class TestToFloat:
    def test_none_returns_none(self):
        assert to_float(None) is None

    def test_int(self):
        assert to_float(3) == pytest.approx(3.0)

    def test_float(self):
        assert to_float(0.25) == pytest.approx(0.25)

    def test_string_number(self):
        assert to_float("0.35") == pytest.approx(0.35)

    def test_string_with_comma(self):
        assert to_float("1,234.5") == pytest.approx(1234.5)

    def test_na_string(self):
        assert to_float("N/A") is None

    def test_none_string(self):
        assert to_float("None") is None

    def test_nan_string(self):
        assert to_float("nan") is None

    def test_float_nan(self):
        assert to_float(float("nan")) is None

    def test_float_inf(self):
        assert to_float(float("inf")) is None

    def test_empty_string(self):
        assert to_float("") is None

    def test_non_numeric_string(self):
        assert to_float("abc") is None

    def test_negative(self):
        assert to_float(-0.5) == pytest.approx(-0.5)


# ── score_segment ─────────────────────────────────────────

class TestScoreSegment:
    """Tests for the good_if_higher=True (default) path."""

    def test_none_returns_none(self):
        assert score_segment(None) is None

    def test_nan_returns_none(self):
        assert score_segment(float("nan")) is None

    def test_inf_returns_none(self):
        assert score_segment(float("inf")) is None

    def test_above_highest_threshold(self):
        assert score_segment(0.7) == pytest.approx(5.0)

    def test_at_highest_threshold(self):
        assert score_segment(0.6) == pytest.approx(5.0)

    def test_between_3_and_4(self):
        # 0.35 is between points[2]=0.30 and points[3]=0.45 → score 3.5
        assert score_segment(0.35) == pytest.approx(3.5)

    def test_between_2_and_3(self):
        # 0.25 is between points[1]=0.20 and points[2]=0.30 → score 2.5
        assert score_segment(0.25) == pytest.approx(2.5)

    def test_between_1_and_2(self):
        # 0.15 is between points[0]=0.10 and points[1]=0.20 → score 1.5
        assert score_segment(0.15) == pytest.approx(1.5)

    def test_between_0_and_1(self):
        assert score_segment(0.12) == pytest.approx(1.5)

    def test_below_lowest_threshold(self):
        assert score_segment(0.05) == pytest.approx(1.0)

    def test_zero(self):
        assert score_segment(0.0) == pytest.approx(1.0)

    def test_negative(self):
        assert score_segment(-0.1) == pytest.approx(1.0)

    def test_custom_points(self):
        # Custom thresholds: (0.02, 0.04, 0.08, 0.12, 0.20) for ROA
        assert score_segment(0.25, points=(0.02, 0.04, 0.08, 0.12, 0.20)) == pytest.approx(5.0)
        assert score_segment(0.15, points=(0.02, 0.04, 0.08, 0.12, 0.20)) == pytest.approx(4.0)
        assert score_segment(0.10, points=(0.02, 0.04, 0.08, 0.12, 0.20)) == pytest.approx(3.5)
        assert score_segment(0.05, points=(0.02, 0.04, 0.08, 0.12, 0.20)) == pytest.approx(2.5)
        assert score_segment(0.03, points=(0.02, 0.04, 0.08, 0.12, 0.20)) == pytest.approx(1.5)
        assert score_segment(0.01, points=(0.02, 0.04, 0.08, 0.12, 0.20)) == pytest.approx(1.0)


class TestScoreSegmentLower:
    """Tests for the good_if_higher=False (debt/equity) path."""

    def test_zero_or_negative(self):
        assert score_segment(0.0, good_if_higher=False) == pytest.approx(5.0)
        assert score_segment(-1.0, good_if_higher=False) == pytest.approx(5.0)

    def test_very_low(self):
        assert score_segment(0.1, good_if_higher=False) == pytest.approx(4.5)

    def test_low(self):
        assert score_segment(0.3, good_if_higher=False) == pytest.approx(4.0)

    def test_medium(self):
        assert score_segment(0.5, good_if_higher=False) == pytest.approx(3.0)

    def test_high(self):
        assert score_segment(1.0, good_if_higher=False) == pytest.approx(2.0)

    def test_very_high(self):
        assert score_segment(2.0, good_if_higher=False) == pytest.approx(1.0)


# ── weighted_score ────────────────────────────────────────

class TestWeightedScore:
    def test_empty(self):
        assert weighted_score([], []) == pytest.approx(0.0)

    def test_equal_weights(self):
        assert weighted_score([4.0, 5.0], [1.0, 1.0]) == pytest.approx(4.5)

    def test_unequal_weights(self):
        # 4.0 * 0.6 + 5.0 * 0.4 = 2.4 + 2.0 = 4.4
        assert weighted_score([4.0, 5.0], [0.6, 0.4]) == pytest.approx(4.4)

    def test_none_values_ignored(self):
        # Only 3.0 is valid; weight for None is ignored
        assert weighted_score([None, 3.0], [1.0, 1.0]) == pytest.approx(3.0)

    def test_all_none(self):
        assert weighted_score([None, None], [1.0, 1.0]) == pytest.approx(0.0)

    def test_single_value(self):
        assert weighted_score([3.5], [2.0]) == pytest.approx(3.5)

    def test_zero_weight(self):
        # zero-weight entry should not affect result
        assert weighted_score([5.0, 3.0], [0.0, 1.0]) == pytest.approx(3.0)


# ── compute_composite ─────────────────────────────────────

class TestComputeComposite:
    def test_no_objective(self):
        subj = {"品牌": 4.0, "网络效应": 3.0}
        result = compute_composite(subj, {})
        assert result["subjective_avg"] == pytest.approx(3.5)
        assert result["objective_avg"] is None
        assert result["composite"] == pytest.approx(3.5)

    def test_with_objective(self):
        subj = {"品牌": 4.0}
        obj = {"利润率": 3.0}
        result = compute_composite(subj, obj, subjective_weight=0.5, objective_weight=0.5)
        assert result["subjective_avg"] == pytest.approx(4.0)
        assert result["objective_avg"] == pytest.approx(3.0)
        assert result["composite"] == pytest.approx(3.5)

    def test_objective_with_none(self):
        subj = {"品牌": 4.0}
        obj = {"利润率": None, "盈利质量": 3.0}
        result = compute_composite(subj, obj)
        # Only 3.0 is valid
        assert result["objective_avg"] == pytest.approx(3.0)

    def test_grade_a_plus(self):
        subj = {"品牌": 5.0}
        result = compute_composite(subj, {})
        assert result["grade"] == "A+"

    def test_grade_a(self):
        subj = {"品牌": 4.2}
        result = compute_composite(subj, {})
        assert result["grade"] == "A"

    def test_grade_b_plus(self):
        subj = {"品牌": 3.7}
        result = compute_composite(subj, {})
        assert result["grade"] == "B+"

    def test_grade_b(self):
        subj = {"品牌": 3.2}
        result = compute_composite(subj, {})
        assert result["grade"] == "B"

    def test_grade_c_plus(self):
        subj = {"品牌": 2.7}
        result = compute_composite(subj, {})
        assert result["grade"] == "C+"

    def test_grade_c(self):
        subj = {"品牌": 2.2}
        result = compute_composite(subj, {})
        assert result["grade"] == "C"

    def test_grade_d(self):
        subj = {"品牌": 1.5}
        result = compute_composite(subj, {})
        assert result["grade"] == "D"
