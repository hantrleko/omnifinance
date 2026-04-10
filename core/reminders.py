"""Financial notification and reminder system.

Stores user-defined financial reminders/alerts with persistence.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

_REMINDERS_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "reminders.json"


def _load_reminders() -> list[dict[str, Any]]:
    """Load reminders from disk."""
    if not _REMINDERS_PATH.exists():
        return []
    try:
        return json.loads(_REMINDERS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_reminders(reminders: list[dict[str, Any]]) -> None:
    """Save reminders to disk."""
    _REMINDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REMINDERS_PATH.write_text(
        json.dumps(reminders, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def add_reminder(
    title: str,
    description: str,
    due_date: str,
    category: str = "general",
    amount: float = 0.0,
) -> None:
    """Add a new reminder."""
    reminders = _load_reminders()
    reminders.append({
        "id": len(reminders) + 1,
        "title": title,
        "description": description,
        "due_date": due_date,
        "category": category,
        "amount": amount,
        "created_at": datetime.now().isoformat(),
        "completed": False,
    })
    _save_reminders(reminders)


def get_reminders(include_completed: bool = False) -> list[dict[str, Any]]:
    """Get all reminders, optionally including completed ones."""
    reminders = _load_reminders()
    if not include_completed:
        reminders = [r for r in reminders if not r.get("completed", False)]
    return sorted(reminders, key=lambda r: r.get("due_date", ""))


def complete_reminder(reminder_id: int) -> None:
    """Mark a reminder as completed."""
    reminders = _load_reminders()
    for r in reminders:
        if r.get("id") == reminder_id:
            r["completed"] = True
            break
    _save_reminders(reminders)


def delete_reminder(reminder_id: int) -> None:
    """Delete a reminder."""
    reminders = _load_reminders()
    reminders = [r for r in reminders if r.get("id") != reminder_id]
    _save_reminders(reminders)


def get_due_reminders() -> list[dict[str, Any]]:
    """Get reminders that are due today or overdue."""
    today = datetime.now().strftime("%Y-%m-%d")
    reminders = get_reminders(include_completed=False)
    return [r for r in reminders if r.get("due_date", "") <= today]


def clear_all_reminders() -> None:
    """Remove all reminders."""
    _save_reminders([])
