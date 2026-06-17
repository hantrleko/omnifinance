"""Lightweight JSON-based persistence for OmniFinance.

Two distinct storage APIs are provided:

1. **Scheme store** (``save_scheme`` / ``load_scheme`` / …)
   Stores named parameter presets per tool (e.g. "我的激进方案").
   Files are stored as ``~/.omnifinance/<tool_name>.json``.

2. **Document store** (``load_document`` / ``save_document``)
   General-purpose key-value store for arbitrary JSON-serialisable data.
   Each logical document lives in its own file:
   ``~/.omnifinance/<document_name>.json``.

   This replaces the repeated copy-paste of ``_load_xxx`` / ``_save_xxx``
   helpers that previously appeared in several ``pages/`` files.

Changelog
---------
v1.4: Added schema_version field and forward-compatible migration mechanism.
      Old files without version field are automatically treated as v1 and migrated.
v1.5: Added file-level locking (fcntl on POSIX, msvcrt on Windows) to prevent
      data corruption under concurrent access.  Corrupt JSON now surfaces a
      user-visible warning instead of silently returning an empty dict.
v1.6: Added generic :func:`load_document` / :func:`save_document` API so that
      individual pages no longer need to duplicate JSON read/write helpers.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

import streamlit as st

_STORAGE_DIR = Path(os.path.expanduser("~")) / ".omnifinance"
_SCHEMA_VERSION = 2   # bump this whenever the stored format changes
_logger = logging.getLogger(__name__)


# ── TypedDict definitions ─────────────────────────────────

class SchemeEntry(TypedDict):
    """A single saved parameter scheme entry stored on disk."""

    params: dict[str, Any]
    saved_at: str
    schema_version: int


# Alias for the top-level mapping: scheme_name -> SchemeEntry
SchemeStore = dict[str, SchemeEntry]


# ── File locking ──────────────────────────────────────────

@contextmanager
def _file_lock(path: Path) -> Generator[None, None, None]:
    """Acquire an exclusive advisory lock on *path* for the duration of the block.

    Uses ``fcntl.flock`` on POSIX systems and ``msvcrt.locking`` on Windows.
    Falls back to a no-op on platforms where neither is available.
    """
    lock_path = path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fh = lock_path.open("a+b")  # binary mode required for msvcrt.locking
    try:
        if sys.platform == "win32":
            import msvcrt  # noqa: PLC0415
            try:
                lock_fh.seek(0)
                msvcrt.locking(lock_fh.fileno(), msvcrt.LK_LOCK, 0x7FFFFFFF)
            except OSError:
                # Best-effort: proceed without lock if acquisition fails
                pass
        else:
            import fcntl  # noqa: PLC0415
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if sys.platform == "win32":
            import msvcrt  # noqa: PLC0415
            try:
                lock_fh.seek(0)
                msvcrt.locking(lock_fh.fileno(), msvcrt.LK_UNLCK, 0x7FFFFFFF)
            except OSError:
                pass
        else:
            import fcntl  # noqa: PLC0415
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        lock_fh.close()


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

    Returns an empty dict when the file does not exist.
    If the file is corrupt, shows a Streamlit warning and returns an empty dict.
    """
    path = _tool_path(tool_name)
    if not path.exists():
        return {}
    try:
        with _file_lock(path):
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        data, migrated = _migrate(raw)
        if migrated:
            # Persist migrated data transparently
            with _file_lock(path):
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data  # type: ignore[return-value]
    except json.JSONDecodeError:
        # Streamlit may not be active in tests; suppress any UI failure.
        import contextlib

        with contextlib.suppress(Exception):
            st.warning(
                f"⚠️ 方案文件 `{path.name}` 已损坏（JSON 格式错误），已跳过加载。"
                "若问题持续，可删除该文件后重新保存方案。"
            )
        return {}
    except OSError:
        return {}


def _save_all(tool_name: str, data: SchemeStore) -> None:
    """Persist *data* for *tool_name* to disk (with exclusive file lock)."""
    path = _tool_path(tool_name)
    with _file_lock(path):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Scheme store public API ───────────────────────────────

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


def load_scheme(tool_name: str, scheme_name: str) -> dict[str, Any] | None:
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
    apply_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any] | None:
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
    loaded: dict[str, Any] | None = None
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


# ── Document store public API ─────────────────────────────
# Replaces the repeated _load_xxx / _save_xxx helpers in pages/.
# Each "document" is a single JSON file in ~/.omnifinance/<name>.json.

def _document_path(name: str) -> Path:
    """Return the storage path for a named document."""
    return _ensure_dir() / f"{name}.json"


def _default_json_serialiser(obj: Any) -> str:
    """Fallback serialiser for types not handled by the standard library."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


def load_document(name: str, default: Any = None) -> Any:
    """Load a JSON document from ``~/.omnifinance/<name>.json``.

    This is the canonical replacement for the ``_load_xxx()`` helpers that
    were previously duplicated across multiple ``pages/`` files.

    Args:
        name:    Document name (without ``.json`` extension), e.g.
                 ``"diary"``, ``"ledger"``, ``"networth"``.
        default: Value returned when the file does not exist or is corrupt.
                 Defaults to ``None``.

    Returns:
        The deserialised JSON value, or *default* on any error.

    Example::

        entries: list[dict] = load_document("diary", default=[])
    """
    path = _document_path(name)
    if not path.exists():
        return default
    try:
        with _file_lock(path):
            data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError) as exc:
        _logger.warning("load_document(%r) failed: %s", name, exc)
        return default


def save_document(name: str, data: Any) -> None:
    """Persist *data* as ``~/.omnifinance/<name>.json``.

    This is the canonical replacement for the ``_save_xxx()`` helpers that
    were previously duplicated across multiple ``pages/`` files.

    Args:
        name: Document name (without ``.json`` extension).
        data: Any JSON-serialisable value (dict, list, str, …).
              ``datetime`` objects are automatically converted to ISO strings.

    Raises:
        Nothing — all errors are logged at WARNING level and silently ignored
        so that a storage failure never crashes the Streamlit UI.

    Example::

        save_document("diary", entries)
    """
    path = _document_path(name)
    try:
        with _file_lock(path):
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=_default_json_serialiser),
                encoding="utf-8",
            )
    except OSError as exc:
        _logger.warning("save_document(%r) failed: %s", name, exc)


def delete_document(name: str) -> bool:
    """Delete ``~/.omnifinance/<name>.json`` if it exists.

    Args:
        name: Document name (without ``.json`` extension).

    Returns:
        ``True`` if the file was deleted, ``False`` if it did not exist.
    """
    path = _document_path(name)
    if path.exists():
        try:
            path.unlink()
            return True
        except OSError as exc:
            _logger.warning("delete_document(%r) failed: %s", name, exc)
    return False
