"""Session state persistence — save and restore all dashboard data to disk.

Extends the existing core/storage.py pattern to persist all tool results
from st.session_state, so data survives page refreshes.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

_PERSIST_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "session_data.json"

# Keys in session_state that should be persisted
DASHBOARD_KEYS = [
    "dashboard_compound", "dashboard_loan", "dashboard_savings",
    "dashboard_budget", "dashboard_retirement", "dashboard_insurance",
    "dashboard_networth", "dashboard_tax",
]


def save_session_data() -> None:
    """Persist all dashboard data from session_state to disk."""
    _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "saved_at": datetime.now().isoformat(),
        "version": "1.9.8",
    }
    for key in DASHBOARD_KEYS:
        val = st.session_state.get(key)
        if val is not None:
            data[key] = val
    _PERSIST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_session_data() -> dict[str, Any]:
    """Load persisted dashboard data from disk.

    Returns:
        Dict of key -> value pairs, empty if no saved data.
    """
    if not _PERSIST_PATH.exists():
        return {}
    try:
        data = json.loads(_PERSIST_PATH.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if k in DASHBOARD_KEYS}
    except (json.JSONDecodeError, OSError):
        return {}


def restore_session_data() -> int:
    """Restore persisted data into session_state.

    Returns:
        Number of keys restored.
    """
    data = load_session_data()
    count = 0
    for key, value in data.items():
        if key not in st.session_state:
            st.session_state[key] = value
            count += 1
    return count


def clear_session_data() -> None:
    """Delete the persisted session data file."""
    if _PERSIST_PATH.exists():
        _PERSIST_PATH.unlink()


def export_all_data() -> str:
    """Export all persisted data as a JSON string for backup."""
    data = load_session_data()
    # Also include schemes
    schemes_path = Path(os.path.expanduser("~")) / ".omnifinance"
    all_data: dict[str, Any] = {"dashboard": data, "exported_at": datetime.now().isoformat()}

    # Collect any JSON files from .omnifinance
    if schemes_path.exists():
        for f in schemes_path.glob("*.json"):
            if f.name != "session_data.json":
                try:
                    all_data[f.stem] = json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass

    return json.dumps(all_data, ensure_ascii=False, indent=2, default=str)


def import_all_data(json_str: str) -> int:
    """Import data from a JSON backup string.

    Returns:
        Number of items imported.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return 0

    count = 0
    # Restore dashboard data
    dashboard = data.get("dashboard", {})
    for key, value in dashboard.items():
        if key in DASHBOARD_KEYS:
            st.session_state[key] = value
            count += 1

    save_session_data()
    return count
