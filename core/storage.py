"""Lightweight JSON-based scheme persistence for parameter presets.

v1.4: Added schema_version field and forward-compatible migration mechanism.
      Old files without version field are automatically treated as v1 and migrated.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, TypedDict

import streamlit as st

_STORAGE_DIR = Path(os.path.expanduser("~")) / ".omnifinance"
_SCHEMA_VERSION = 2   # bump this whenever the stored format changes


# ── TypedDict definitions ─────────────────────────────────

class SchemeEntry(TypedDict):
    """A single saved parameter scheme entry stored on disk."""

    params: dict[str, Any]
    saved_at: str
    schema_version: int


# Alias for the top-level mapping: scheme_name -> SchemeEntry
SchemeStore = dict[str, SchemeEntry]


# ── Internal helpers ──────────────────────────────────────

def _ensure_dir() -> Path:
    """Create the storage directory if it does not exist and return its path."""
    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return _STORAGE_DIR


def _tool_path(tool_name: str) -> Path:
    """Return the JSON file path for *tool_name*."""
    return _ensure_dir() / f"{tool_name}.json"


def _migrate(data: dict[str, Any]) -> tuple[SchemeStore, bool]:
    """Migrate stored data to the latest schema version in-place.

    Migration rules:
      v1 -> v2: wrap bare-dict entries into {params, saved_at, schema_version}.

    Returns:
        A tuple of (migrated_data, was_migrated) where *was_migrated* is True
        when at least one entry was updated.
    """
    migrated = False
    for key, entry in list(data.items()):
        # v1 format: entry is a dict without schema_version
        if isinstance(entry, dict) and "schema_version" not in entry:
            if "params" not in entry:
                # Very old format: the whole entry IS the params dict
                data[key] = SchemeEntry(
                    params=entry,
                    saved_at=datetime.now().isoformat(),
                    schema_version=_SCHEMA_VERSION,
                )
            else:
                entry["schema_version"] = _SCHEMA_VERSION
            migrated = True
    return data, migrated  # type: ignore[return-value]


def _load_all(tool_name: str) -> SchemeStore:
    """Load all saved schemes for *tool_name* from disk.

    Returns an empty dict when the file does not exist or is corrupt.
    """
    path = _tool_path(tool_name)
    if not path.exists():
        return {}
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        data, migrated = _migrate(raw)
        if migrated:
            # Persist migrated data transparently
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data  # type: ignore[return-value]
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(tool_name: str, data: SchemeStore) -> None:
    """Persist *data* for *tool_name* to disk."""
    path = _tool_path(tool_name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Public API ────────────────────────────────────────────

def save_scheme(tool_name: str, scheme_name: str, params: dict[str, Any]) -> None:
    """Save a named parameter scheme for a given tool.

    Args:
        tool_name: Identifier for the tool (e.g. ``"compound"``).
        scheme_name: Human-readable name chosen by the user.
        params: Arbitrary dict of parameter key/value pairs to persist.
    """
    data = _load_all(tool_name)
    data[scheme_name] = SchemeEntry(
        params=params,
        saved_at=datetime.now().isoformat(),
        schema_version=_SCHEMA_VERSION,
    )
    _save_all(tool_name, data)


def load_scheme(tool_name: str, scheme_name: str) -> Optional[dict[str, Any]]:
    """Load a named parameter scheme.

    Args:
        tool_name: Identifier for the tool.
        scheme_name: Name of the scheme to load.

    Returns:
        The ``params`` dict if found, otherwise ``None``.
    """
    data = _load_all(tool_name)
    entry = data.get(scheme_name)
    return entry["params"] if entry else None


def list_schemes(tool_name: str) -> list[str]:
    """List all saved scheme names for a tool.

    Args:
        tool_name: Identifier for the tool.

    Returns:
        Ordered list of scheme name strings.
    """
    return list(_load_all(tool_name).keys())


def delete_scheme(tool_name: str, scheme_name: str) -> None:
    """Delete a saved scheme.

    Args:
        tool_name: Identifier for the tool.
        scheme_name: Name of the scheme to delete. No-op if not found.
    """
    data = _load_all(tool_name)
    data.pop(scheme_name, None)
    _save_all(tool_name, data)


def scheme_manager_ui(
    tool_name: str,
    current_params: dict[str, Any],
    apply_callback: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Optional[dict[str, Any]]:
    """Render a save/load/delete UI in the sidebar.

    Args:
        tool_name: Identifier for the tool (used as storage key).
        current_params: The parameter dict currently active in the UI.
        apply_callback: Optional callable invoked with the loaded params dict
            when the user clicks "Load". Useful for side-effects beyond the
            return value.

    Returns:
        The loaded ``params`` dict if the user clicked "Load", otherwise ``None``.
    """
    st.sidebar.divider()
    st.sidebar.subheader("💾 方案管理")
    schemes = list_schemes(tool_name)

    # Save
    with st.sidebar.expander("保存当前方案"):
        name = st.text_input("方案名称", key=f"_scheme_save_{tool_name}")
        if st.button("💾 保存", key=f"_scheme_save_btn_{tool_name}"):
            if name.strip():
                save_scheme(tool_name, name.strip(), current_params)
                st.success(f"已保存方案「{name.strip()}」")
                st.rerun()
            else:
                st.warning("请输入方案名称")

    # Load / Delete
    loaded: Optional[dict[str, Any]] = None
    if schemes:
        with st.sidebar.expander("加载 / 删除方案"):
            selected: str = st.selectbox("选择方案", schemes, key=f"_scheme_load_{tool_name}")
            col_load, col_del = st.columns(2)
            if col_load.button("📂 加载", key=f"_scheme_load_btn_{tool_name}"):
                loaded = load_scheme(tool_name, selected)
                if loaded:
                    if apply_callback is not None:
                        apply_callback(loaded)
                    st.success(f"已加载方案「{selected}」")
            if col_del.button("🗑️ 删除", key=f"_scheme_del_btn_{tool_name}"):
                delete_scheme(tool_name, selected)
                st.success(f"已删除方案「{selected}」")
                st.rerun()

    return loaded
