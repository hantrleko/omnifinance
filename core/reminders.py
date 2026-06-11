"""Financial notification and reminder system.

Stores user-defined financial reminders/alerts with persistence.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

_REMINDERS_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "reminders.json"
ReminderScope = Literal["all", "active", "completed"]
ImportMode = Literal["append", "replace"]


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
    dedupe: bool = False,
) -> bool:
    """Add a new reminder.

    Returns:
        True when a new reminder was added, False when dedupe skipped it.
    """
    if dedupe and has_duplicate_reminder(
        title=title,
        due_date=due_date,
        category=category,
        description=description,
    ):
        return False

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
    return True


def has_duplicate_reminder(
    *,
    title: str,
    due_date: str,
    category: str | None = None,
    description: str | None = None,
) -> bool:
    """Return whether an active reminder with similar signature already exists."""
    reminders = get_reminders(include_completed=False)
    for reminder in reminders:
        if reminder.get("title") != title:
            continue
        if reminder.get("due_date") != due_date:
            continue
        if category is not None and reminder.get("category") != category:
            continue
        if description is not None and reminder.get("description") != description:
            continue
        return True
    return False


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


def clear_completed_reminders() -> int:
    """Clear completed reminders and return how many were removed."""
    reminders = _load_reminders()
    remaining = [r for r in reminders if not r.get("completed", False)]
    removed = len(reminders) - len(remaining)
    if removed:
        _save_reminders(remaining)
    return removed


def export_reminders(*, scope: ReminderScope = "all") -> str:
    """Export reminders as a JSON string for backup or migration."""
    reminders = _load_reminders()
    if scope == "active":
        reminders = [r for r in reminders if not r.get("completed", False)]
    elif scope == "completed":
        reminders = [r for r in reminders if r.get("completed", False)]

    payload = {
        "version": "1.0",
        "scope": scope,
        "exported_at": datetime.now().isoformat(),
        "reminders": reminders,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def import_reminders(json_payload: str, *, dedupe: bool = True, mode: ImportMode = "append") -> int:
    """Import reminders from a JSON backup payload.

    Returns:
        Number of imported reminders.
    """
    try:
        data = json.loads(json_payload)
    except json.JSONDecodeError:
        return 0

    source = data.get("reminders", data) if isinstance(data, dict) else data
    if not isinstance(source, list):
        return 0

    incoming = []
    for item in source:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        due_date = item.get("due_date")
        description = item.get("description", "")
        category = item.get("category", "general")
        amount = float(item.get("amount", 0) or 0)
        completed = bool(item.get("completed", False))
        if not title or not due_date:
            continue
        incoming.append(
            {
                "title": str(title),
                "due_date": str(due_date),
                "description": str(description),
                "category": str(category),
                "amount": amount,
                "completed": completed,
            }
        )

    if mode == "replace":
        base = []
    else:
        base = _load_reminders()

    if dedupe:
        existing_keyed = {(r.get("title"), r.get("due_date"), r.get("category"), r.get("description")) for r in base}
    else:
        existing_keyed = None

    imported_count = 0
    for item in incoming:
        key = (item["title"], item["due_date"], item["category"], item["description"])
        if existing_keyed is not None and key in existing_keyed:
            continue

        item = dict(item)
        item["id"] = len(base) + 1
        item["created_at"] = datetime.now().isoformat()
        base.append(item)
        imported_count += 1
        if existing_keyed is not None:
            existing_keyed.add(key)

    if mode == "append" and imported_count == 0 and not incoming:
        return 0

    _save_reminders(base)
    return imported_count
