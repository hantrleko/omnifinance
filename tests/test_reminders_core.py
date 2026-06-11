"""Tests for reminder creation and deduplication."""

from __future__ import annotations

from pathlib import Path

from core import reminders


def test_add_reminder_and_deduplicate(monkeypatch: object, tmp_path: Path) -> None:
    reminder_path = tmp_path / "reminders.json"
    monkeypatch.setattr(reminders, "_REMINDERS_PATH", reminder_path)

    assert reminders.add_reminder(
        title="月度复盘",
        description="复盘上月预算与净值",
        due_date="2026-06-20",
        category="general",
        amount=0.0,
    )
    assert reminders.add_reminder(
        title="月度复盘",
        description="复盘上月预算与净值",
        due_date="2026-06-20",
        category="general",
        amount=0.0,
        dedupe=True,
    ) is False

    all_reminders = reminders.get_reminders(include_completed=True)
    assert len(all_reminders) == 1
    reminder = all_reminders[0]
    assert reminder["title"] == "月度复盘"
    assert reminder["due_date"] == "2026-06-20"


def test_clear_completed_reminders(monkeypatch: object, tmp_path: Path) -> None:
    reminder_path = tmp_path / "reminders.json"
    monkeypatch.setattr(reminders, "_REMINDERS_PATH", reminder_path)

    reminders.add_reminder(title="任务1", description="", due_date="2026-06-20", category="general", amount=0.0)
    reminders.add_reminder(title="任务2", description="", due_date="2026-06-21", category="general", amount=0.0)

    all_reminders = reminders.get_reminders(include_completed=True)
    assert len(all_reminders) == 2
    reminders.complete_reminder(all_reminders[0]["id"])

    removed = reminders.clear_completed_reminders()
    assert removed == 1
    assert len(reminders.get_reminders(include_completed=True)) == 1
