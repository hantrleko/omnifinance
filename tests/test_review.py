"""Unit tests for core/review.py — snapshots, action tracking, monthly review."""
from __future__ import annotations

from datetime import datetime

import pytest

from core.review import (
    ACTION_STATUSES,
    action_stats,
    build_monthly_review,
    compute_snapshot_delta,
    delete_action,
    load_actions,
    load_health_history,
    monthly_review_markdown,
    recent_period_options,
    record_health_snapshot,
    upsert_action,
)

# ─────────────────────────────────────────────────────────────
# Health snapshots
# ─────────────────────────────────────────────────────────────

class TestSnapshots:
    def test_record_appends(self):
        store: list = []
        out = record_health_snapshot(72, {"储蓄": 80}, store=store, now=datetime(2026, 7, 1, 9))
        assert len(out) == 1
        assert out[0]["overall_score"] == 72
        assert out[0]["dimensions"] == {"储蓄": 80}

    def test_none_score_skipped(self):
        out = record_health_snapshot(None, store=[])
        assert out == []

    def test_rapid_duplicate_collapsed(self):
        store: list = []
        store = record_health_snapshot(70, store=store, now=datetime(2026, 7, 1, 9, 0))
        store = record_health_snapshot(70, store=store, now=datetime(2026, 7, 1, 10, 0))
        assert len(store) == 1  # same score within 6h window → collapsed

    def test_different_score_not_collapsed(self):
        store: list = []
        store = record_health_snapshot(70, store=store, now=datetime(2026, 7, 1, 9))
        store = record_health_snapshot(75, store=store, now=datetime(2026, 7, 1, 10))
        assert len(store) == 2

    def test_spaced_same_score_kept(self):
        store: list = []
        store = record_health_snapshot(70, store=store, now=datetime(2026, 7, 1, 9))
        store = record_health_snapshot(70, store=store, now=datetime(2026, 7, 2, 9))
        assert len(store) == 2

    def test_history_bounded(self):
        store: list = []
        for i in range(450):
            store = record_health_snapshot(
                i % 100, store=store, now=datetime(2025, 1, 1) .replace(hour=0) + __import__("datetime").timedelta(days=i)
            )
        assert len(store) <= 400

    def test_load_sorted(self):
        history = [
            {"timestamp": "2026-07-02T09:00:00", "overall_score": 75},
            {"timestamp": "2026-07-01T09:00:00", "overall_score": 70},
        ]
        out = load_health_history(history)
        assert [s["overall_score"] for s in out] == [70, 75]


class TestSnapshotDelta:
    def test_empty(self):
        d = compute_snapshot_delta([])
        assert d.current is None and d.trend == "na"

    def test_single(self):
        d = compute_snapshot_delta([{"timestamp": "2026-07-01T09:00:00", "overall_score": 70}])
        assert d.current == 70 and d.previous is None and d.trend == "na"

    def test_up(self):
        d = compute_snapshot_delta([
            {"timestamp": "2026-07-01T09:00:00", "overall_score": 70},
            {"timestamp": "2026-07-05T09:00:00", "overall_score": 78},
        ])
        assert d.delta == 8 and d.trend == "up" and d.days_between == 4

    def test_down(self):
        d = compute_snapshot_delta([
            {"timestamp": "2026-07-01T09:00:00", "overall_score": 70},
            {"timestamp": "2026-07-05T09:00:00", "overall_score": 60},
        ])
        assert d.delta == -10 and d.trend == "down"

    def test_flat(self):
        d = compute_snapshot_delta([
            {"timestamp": "2026-07-01T09:00:00", "overall_score": 70},
            {"timestamp": "2026-07-05T09:00:00", "overall_score": 70},
        ])
        assert d.trend == "flat"


# ─────────────────────────────────────────────────────────────
# Action tracking
# ─────────────────────────────────────────────────────────────

class TestActions:
    def test_upsert_creates(self):
        tracker = upsert_action("建立应急基金", store={}, now=datetime(2026, 7, 1))
        assert len(tracker) == 1
        rec = next(iter(tracker.values()))
        assert rec["status"] == "planned"
        assert rec["created_at"]

    def test_upsert_updates_same_title(self):
        tracker = upsert_action("建立应急基金", store={}, now=datetime(2026, 7, 1))
        tracker = upsert_action("建立 应急基金", status="completed", store=tracker, now=datetime(2026, 7, 2))
        assert len(tracker) == 1  # whitespace-insensitive identity
        rec = next(iter(tracker.values()))
        assert rec["status"] == "completed"
        assert rec["completed_at"].startswith("2026-07-02")

    def test_reopen_clears_completed_at(self):
        tracker = upsert_action("A", status="completed", store={}, now=datetime(2026, 7, 1))
        tracker = upsert_action("A", status="in_progress", store=tracker, now=datetime(2026, 7, 3))
        rec = next(iter(tracker.values()))
        assert "completed_at" not in rec

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="状态"):
            upsert_action("A", status="done", store={})

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="标题"):
            upsert_action("   ", store={})

    def test_delete(self):
        tracker = upsert_action("A", store={})
        tracker = delete_action("A", store=tracker)
        assert tracker == {}

    def test_load_sorted_active_first(self):
        tracker: dict = {}
        tracker = upsert_action("done", status="completed", store=tracker, now=datetime(2026, 7, 5))
        tracker = upsert_action("doing", status="in_progress", store=tracker, now=datetime(2026, 7, 1))
        tracker = upsert_action("todo", status="planned", store=tracker, now=datetime(2026, 7, 2))
        out = load_actions(tracker)
        assert [r["status"] for r in out] == ["in_progress", "planned", "completed"]

    def test_all_statuses_accepted(self):
        for status in ACTION_STATUSES:
            tracker = upsert_action("X", status=status, store={})
            assert next(iter(tracker.values()))["status"] == status


class TestActionStats:
    def test_empty(self):
        stats = action_stats([])
        assert stats["total"] == 0 and stats["completion_rate_pct"] == 0.0

    def test_counts_and_rate(self):
        actions = [
            {"status": "completed"}, {"status": "completed"},
            {"status": "planned"}, {"status": "skipped"},
        ]
        stats = action_stats(actions)
        assert stats["total"] == 4
        assert stats["counts"]["completed"] == 2
        assert stats["completion_rate_pct"] == 50.0
        assert stats["open_count"] == 1


# ─────────────────────────────────────────────────────────────
# Monthly review
# ─────────────────────────────────────────────────────────────

class TestMonthlyReview:
    def _history(self):
        return [
            {"timestamp": "2026-07-01T09:00:00", "overall_score": 65},
            {"timestamp": "2026-07-15T09:00:00", "overall_score": 70},
            {"timestamp": "2026-07-28T09:00:00", "overall_score": 74},
            {"timestamp": "2026-06-20T09:00:00", "overall_score": 60},
        ]

    def _actions(self):
        return [
            {"title": "建立应急基金", "status": "completed", "completed_at": "2026-07-10T12:00:00", "updated_at": "2026-07-10T12:00:00"},
            {"title": "梳理保单", "status": "skipped", "updated_at": "2026-07-12T12:00:00"},
            {"title": "调整资产配置", "status": "planned", "updated_at": "2026-07-13T12:00:00"},
        ]

    def test_score_change(self):
        review = build_monthly_review(2026, 7, history=self._history(), actions=self._actions())
        assert review["score_start"] == 65
        assert review["score_end"] == 74
        assert review["score_change"] == 9
        assert review["snapshot_count"] == 3

    def test_action_counts(self):
        review = build_monthly_review(2026, 7, history=self._history(), actions=self._actions())
        assert review["actions_completed"] == 1
        assert review["actions_skipped"] == 1
        assert review["actions_open"] == 1

    def test_empty_month(self):
        review = build_monthly_review(2026, 1, history=self._history(), actions=[])
        assert review["score_start"] is None
        assert review["snapshot_count"] == 0
        assert any("暂无健康分快照" in h for h in review["highlights"])

    def test_invalid_month_raises(self):
        with pytest.raises(ValueError, match="月份"):
            build_monthly_review(2026, 13, history=[], actions=[])

    def test_markdown_render(self):
        review = build_monthly_review(2026, 7, history=self._history(), actions=self._actions())
        md = monthly_review_markdown(review)
        assert "2026 年 7 月财务复盘" in md
        assert "| 月末健康分 | 74 |" in md
        assert "+9" in md

    def test_markdown_handles_missing(self):
        review = build_monthly_review(2026, 1, history=[], actions=[])
        md = monthly_review_markdown(review)
        assert "—" in md


class TestPeriodOptions:
    def test_count_and_order(self):
        opts = recent_period_options(3, now=datetime(2026, 7, 10))
        assert opts == [(2026, 7), (2026, 6), (2026, 5)]

    def test_year_boundary(self):
        opts = recent_period_options(3, now=datetime(2026, 1, 15))
        assert opts == [(2026, 1), (2025, 12), (2025, 11)]
