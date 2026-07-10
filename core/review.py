"""Review-loop engine — health score history, action tracking, monthly review.

Implements the v2.6 roadmap items:

- **Health snapshots**: append-only history of financial health scores so the
  dashboard can compare "previous vs current" and plot a trend line.
- **Action status tracking**: actions from the 90-day plan can be marked
  planned / in_progress / completed / skipped, with timestamps.
- **Monthly review summary**: aggregates snapshots and action activity of a
  calendar month into a compact, exportable summary.

Persistence goes through :mod:`core.storage` documents; every public function
also accepts/returns plain data structures so the logic stays unit-testable
without touching the disk (pass ``store=`` explicitly in tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from core.storage import load_document, save_document

# Document names in ~/.omnifinance/
HEALTH_HISTORY_DOC = "health_history"
ACTION_TRACKER_DOC = "action_tracker"

ACTION_STATUSES: tuple[str, ...] = ("planned", "in_progress", "completed", "skipped")

STATUS_LABELS: dict[str, str] = {
    "planned": "📋 已计划",
    "in_progress": "🚧 进行中",
    "completed": "✅ 已完成",
    "skipped": "⏭️ 已跳过",
}

MAX_SNAPSHOTS = 400  # keep history bounded


# ══════════════════════════════════════════════════════════════════════════
#  Health score snapshots
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SnapshotDelta:
    """Comparison between the two most recent health snapshots.

    Attributes:
        current: Latest overall score.
        previous: Previous overall score (None if only one snapshot).
        delta: current - previous (None when not comparable).
        trend: ``"up"`` / ``"down"`` / ``"flat"`` / ``"na"``.
        days_between: Days between the two snapshots (None if not comparable).
    """

    current: int | None
    previous: int | None
    delta: int | None
    trend: str
    days_between: int | None


def record_health_snapshot(
    overall_score: int | None,
    dimension_scores: dict[str, int] | None = None,
    *,
    store: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
    min_hours_between: float = 6.0,
) -> list[dict[str, Any]]:
    """Append a health snapshot, de-duplicating rapid repeats.

    Consecutive snapshots closer than *min_hours_between* with the same
    overall score are collapsed (the newest wins) to avoid flooding the
    history when the dashboard page is refreshed repeatedly.

    Args:
        overall_score: Overall health score 0-100 (None entries are skipped).
        dimension_scores: Optional per-dimension name → score mapping.
        store: In-memory history list (loaded from disk when omitted).
        now: Timestamp override for tests.
        min_hours_between: De-duplication window in hours.

    Returns:
        The updated snapshot list (also persisted when *store* was omitted).
    """
    persist = store is None
    history: list[dict[str, Any]] = (
        list(load_document(HEALTH_HISTORY_DOC, default=[]) or []) if persist else list(store or [])
    )
    if overall_score is None:
        return history

    ts = (now or datetime.now()).isoformat(timespec="seconds")
    snapshot = {
        "timestamp": ts,
        "overall_score": int(overall_score),
        "dimensions": {k: int(v) for k, v in (dimension_scores or {}).items()},
    }

    if history:
        last = history[-1]
        try:
            last_ts = datetime.fromisoformat(str(last.get("timestamp", "")))
            hours = abs(((now or datetime.now()) - last_ts).total_seconds()) / 3600.0
            if hours < min_hours_between and int(last.get("overall_score", -1)) == int(overall_score):
                history[-1] = snapshot  # refresh in place
                if persist:
                    save_document(HEALTH_HISTORY_DOC, history)
                return history
        except (ValueError, TypeError):
            pass

    history.append(snapshot)
    if len(history) > MAX_SNAPSHOTS:
        history = history[-MAX_SNAPSHOTS:]
    if persist:
        save_document(HEALTH_HISTORY_DOC, history)
    return history


def load_health_history(store: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Return the snapshot history sorted by timestamp ascending."""
    history = list(store) if store is not None else list(load_document(HEALTH_HISTORY_DOC, default=[]) or [])
    return sorted(history, key=lambda s: str(s.get("timestamp", "")))


def compute_snapshot_delta(history: list[dict[str, Any]]) -> SnapshotDelta:
    """Compare the two most recent snapshots in *history*."""
    ordered = sorted(history, key=lambda s: str(s.get("timestamp", "")))
    if not ordered:
        return SnapshotDelta(None, None, None, "na", None)
    current = int(ordered[-1].get("overall_score", 0))
    if len(ordered) < 2:
        return SnapshotDelta(current, None, None, "na", None)
    previous = int(ordered[-2].get("overall_score", 0))
    delta = current - previous
    trend = "up" if delta > 0 else "down" if delta < 0 else "flat"
    days: int | None = None
    try:
        t1 = datetime.fromisoformat(str(ordered[-2]["timestamp"]))
        t2 = datetime.fromisoformat(str(ordered[-1]["timestamp"]))
        days = abs((t2 - t1).days)
    except (KeyError, ValueError, TypeError):
        pass
    return SnapshotDelta(current, previous, delta, trend, days)


# ══════════════════════════════════════════════════════════════════════════
#  Action status tracking
# ══════════════════════════════════════════════════════════════════════════

def _normalise_action_id(title: str) -> str:
    """Stable id from an action title (whitespace-insensitive)."""
    return "".join(str(title).split()).lower()


def upsert_action(
    title: str,
    *,
    status: str = "planned",
    note: str = "",
    source: str = "action_plan",
    store: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create or update a tracked action.

    Args:
        title: Human-readable action title (identity key after whitespace
            normalisation).
        status: One of :data:`ACTION_STATUSES`.
        note: Optional free-form note.
        source: Where the action originated (``"action_plan"``, ``"manual"`` …).
        store: In-memory tracker dict (loaded from disk when omitted).
        now: Timestamp override for tests.

    Returns:
        The updated tracker mapping ``action_id → record``.

    Raises:
        ValueError: If *status* is not a recognised status or title is empty.
    """
    if status not in ACTION_STATUSES:
        raise ValueError(f"未知的行动状态：{status}，应为 {ACTION_STATUSES} 之一。")
    if not str(title).strip():
        raise ValueError("行动标题不能为空。")

    persist = store is None
    tracker: dict[str, Any] = (
        dict(load_document(ACTION_TRACKER_DOC, default={}) or {}) if persist else dict(store or {})
    )

    action_id = _normalise_action_id(title)
    ts = (now or datetime.now()).isoformat(timespec="seconds")
    record = dict(tracker.get(action_id, {}))
    is_new = not record

    record.update(
        {
            "title": str(title).strip(),
            "status": status,
            "note": str(note) if note else record.get("note", ""),
            "source": record.get("source", source),
            "updated_at": ts,
        }
    )
    if is_new:
        record["created_at"] = ts
    if status == "completed" and not record.get("completed_at"):
        record["completed_at"] = ts
    if status != "completed":
        record.pop("completed_at", None)

    tracker[action_id] = record
    if persist:
        save_document(ACTION_TRACKER_DOC, tracker)
    return tracker


def delete_action(title: str, *, store: dict[str, Any] | None = None) -> dict[str, Any]:
    """Remove a tracked action by title; returns the updated tracker."""
    persist = store is None
    tracker: dict[str, Any] = (
        dict(load_document(ACTION_TRACKER_DOC, default={}) or {}) if persist else dict(store or {})
    )
    tracker.pop(_normalise_action_id(title), None)
    if persist:
        save_document(ACTION_TRACKER_DOC, tracker)
    return tracker


def load_actions(store: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return tracked actions sorted: active first, then by update time desc."""
    tracker = dict(store) if store is not None else dict(load_document(ACTION_TRACKER_DOC, default={}) or {})
    order = {"in_progress": 0, "planned": 1, "completed": 2, "skipped": 3}
    records = [dict(r) for r in tracker.values() if isinstance(r, dict)]
    return sorted(
        records,
        key=lambda r: (order.get(str(r.get("status", "planned")), 9), str(r.get("updated_at", ""))),
    )


def action_stats(actions: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate counts and completion rate for a list of action records."""
    counts = {status: 0 for status in ACTION_STATUSES}
    for record in actions:
        status = str(record.get("status", "planned"))
        if status in counts:
            counts[status] += 1
    total = sum(counts.values())
    decided = counts["completed"] + counts["skipped"]
    completion = counts["completed"] / total * 100.0 if total else 0.0
    return {
        "total": total,
        "counts": counts,
        "completion_rate_pct": round(completion, 1),
        "open_count": total - decided,
    }


# ══════════════════════════════════════════════════════════════════════════
#  Monthly review summary
# ══════════════════════════════════════════════════════════════════════════

def _in_month(ts: str, year: int, month: int) -> bool:
    try:
        dt = datetime.fromisoformat(str(ts))
    except (ValueError, TypeError):
        return False
    return dt.year == year and dt.month == month


def build_monthly_review(
    year: int,
    month: int,
    *,
    history: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a monthly review summary for *year*/*month*.

    Args:
        year: Calendar year, e.g. 2026.
        month: Calendar month 1-12.
        history: Snapshot list (loaded from disk when omitted).
        actions: Action record list (loaded from disk when omitted).

    Returns:
        Dict with keys ``year``, ``month``, ``score_start``, ``score_end``,
        ``score_change``, ``snapshot_count``, ``actions_completed``,
        ``actions_skipped``, ``actions_open``, ``highlights`` (list of
        human-readable strings).

    Raises:
        ValueError: If *month* is outside 1-12.
    """
    if not 1 <= month <= 12:
        raise ValueError("月份必须在 1-12 之间。")

    snaps = [
        s for s in load_health_history(history)
        if _in_month(str(s.get("timestamp", "")), year, month)
    ]
    acts = actions if actions is not None else load_actions()

    score_start: int | None = None
    score_end: int | None = None
    change: int | None = None
    if snaps:
        score_start = int(snaps[0]["overall_score"])
        score_end = int(snaps[-1]["overall_score"])
        change = score_end - score_start

    completed = [
        a for a in acts
        if str(a.get("status")) == "completed" and _in_month(str(a.get("completed_at", "")), year, month)
    ]
    skipped = [
        a for a in acts
        if str(a.get("status")) == "skipped" and _in_month(str(a.get("updated_at", "")), year, month)
    ]
    open_actions = [a for a in acts if str(a.get("status")) in ("planned", "in_progress")]

    highlights: list[str] = []
    if change is not None:
        if change > 0:
            highlights.append(f"财务健康分本月提升 {change} 分（{score_start} → {score_end}）。")
        elif change < 0:
            highlights.append(f"财务健康分本月下降 {abs(change)} 分（{score_start} → {score_end}），建议复盘原因。")
        else:
            highlights.append(f"财务健康分本月保持在 {score_end} 分。")
    else:
        highlights.append("本月暂无健康分快照，建议访问仪表盘生成诊断。")

    if completed:
        highlights.append(f"完成了 {len(completed)} 项行动：" + "、".join(str(a.get("title", "")) for a in completed[:5]))
    if skipped:
        highlights.append(f"跳过了 {len(skipped)} 项行动，可在复盘中心确认是否需要重新安排。")
    if open_actions:
        highlights.append(f"还有 {len(open_actions)} 项行动待推进。")
    if not completed and not skipped:
        highlights.append("本月没有行动状态更新，建议每周至少检查一次行动看板。")

    return {
        "year": year,
        "month": month,
        "score_start": score_start,
        "score_end": score_end,
        "score_change": change,
        "snapshot_count": len(snaps),
        "actions_completed": len(completed),
        "actions_skipped": len(skipped),
        "actions_open": len(open_actions),
        "highlights": highlights,
    }


def monthly_review_markdown(review: dict[str, Any]) -> str:
    """Render a monthly review dict as exportable Markdown."""
    lines = [
        f"# 📆 {review['year']} 年 {review['month']} 月财务复盘",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| 月初健康分 | {review['score_start'] if review['score_start'] is not None else '—'} |",
        f"| 月末健康分 | {review['score_end'] if review['score_end'] is not None else '—'} |",
        f"| 分数变化 | {format(review['score_change'], '+d') if review['score_change'] is not None else '—'} |",
        f"| 快照次数 | {review['snapshot_count']} |",
        f"| 完成行动 | {review['actions_completed']} |",
        f"| 跳过行动 | {review['actions_skipped']} |",
        f"| 待办行动 | {review['actions_open']} |",
        "",
        "## 本月要点",
        "",
    ]
    lines += [f"- {h}" for h in review.get("highlights", [])]
    lines += ["", "> 由 OmniFinance 复盘中心自动生成，仅供个人复盘参考，不构成投资建议。"]
    return "\n".join(lines)


def recent_period_options(n_months: int = 12, *, now: datetime | None = None) -> list[tuple[int, int]]:
    """Return the last *n_months* (year, month) tuples, newest first."""
    current = (now or datetime.now()).replace(day=1)
    options: list[tuple[int, int]] = []
    for _ in range(max(n_months, 1)):
        options.append((current.year, current.month))
        current = (current - timedelta(days=1)).replace(day=1)
    return options
