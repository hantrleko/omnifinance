"""Tests for core/storage.py — scheme persistence, migration, error handling."""

import atexit
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Patch the storage directory before importing the module so tests never
# touch the real ~/.omnifinance directory.
_TMPDIR = tempfile.mkdtemp(prefix="omnifinance_test_")
_MOCK_DIR = Path(_TMPDIR)

# Clean up the temp directory when the test session exits
atexit.register(shutil.rmtree, _TMPDIR, True)

import core.storage as storage_mod

# Override the internal storage dir used by the module under test
storage_mod._STORAGE_DIR = _MOCK_DIR


# ── Helpers ────────────────────────────────────────────────

def _tool_path(tool_name: str) -> Path:
    """Return the expected file path for a tool (mirroring module logic)."""
    return _MOCK_DIR / f"{tool_name}.json"


def _cleanup(tool_name: str) -> None:
    for suffix in ("", ".lock"):
        p = _MOCK_DIR / f"{tool_name}{suffix}"
        if p.exists():
            p.unlink()


# ── Save / Load roundtrip ─────────────────────────────────

def test_save_and_load_roundtrip():
    _cleanup("test_rt")
    params = {"rate": 4.5, "years": 30, "label": "测试"}
    storage_mod.save_scheme("test_rt", "scheme1", params)
    loaded = storage_mod.load_scheme("test_rt", "scheme1")
    assert loaded == params


def test_load_returns_none_for_missing_scheme():
    _cleanup("test_missing")
    result = storage_mod.load_scheme("test_missing", "nonexistent")
    assert result is None


def test_list_schemes_returns_saved_names():
    _cleanup("test_list")
    storage_mod.save_scheme("test_list", "alpha", {"x": 1})
    storage_mod.save_scheme("test_list", "beta", {"x": 2})
    names = storage_mod.list_schemes("test_list")
    assert "alpha" in names
    assert "beta" in names


def test_delete_scheme_removes_entry():
    _cleanup("test_del")
    storage_mod.save_scheme("test_del", "to_delete", {"v": 99})
    storage_mod.delete_scheme("test_del", "to_delete")
    assert storage_mod.load_scheme("test_del", "to_delete") is None


def test_delete_nonexistent_is_noop():
    _cleanup("test_noop")
    # Should not raise
    storage_mod.delete_scheme("test_noop", "ghost")


def test_overwrite_same_scheme_name():
    _cleanup("test_overwrite")
    storage_mod.save_scheme("test_overwrite", "s1", {"v": 1})
    storage_mod.save_scheme("test_overwrite", "s1", {"v": 2})
    loaded = storage_mod.load_scheme("test_overwrite", "s1")
    assert loaded == {"v": 2}


# ── Migration (v1 → v2) ───────────────────────────────────

def test_migration_from_v1_bare_params():
    """A v1 file where entry IS the params dict (no schema_version)."""
    _cleanup("test_v1")
    path = _tool_path("test_v1")
    _MOCK_DIR.mkdir(parents=True, exist_ok=True)
    v1_data = {"old_scheme": {"rate": 3.5, "years": 20}}
    path.write_text(json.dumps(v1_data), encoding="utf-8")

    loaded = storage_mod.load_scheme("test_v1", "old_scheme")
    assert loaded == {"rate": 3.5, "years": 20}

    # After migration the file should have schema_version
    migrated = json.loads(path.read_text(encoding="utf-8"))
    assert migrated["old_scheme"]["schema_version"] == storage_mod._SCHEMA_VERSION


def test_migration_from_v1_with_params_key():
    """A v1 file where entry has a 'params' key but no schema_version."""
    _cleanup("test_v1b")
    path = _tool_path("test_v1b")
    _MOCK_DIR.mkdir(parents=True, exist_ok=True)
    v1_data = {"scheme_a": {"params": {"x": 10}, "saved_at": "2024-01-01T00:00:00"}}
    path.write_text(json.dumps(v1_data), encoding="utf-8")

    loaded = storage_mod.load_scheme("test_v1b", "scheme_a")
    assert loaded == {"x": 10}


# ── Corrupt file handling ─────────────────────────────────

def test_corrupt_json_returns_empty_dict():
    """Corrupt JSON should not raise; should return empty dict."""
    _cleanup("test_corrupt")
    path = _tool_path("test_corrupt")
    _MOCK_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text("{invalid json!!!", encoding="utf-8")

    # Suppress the st.warning call (Streamlit not active in tests)
    with mock.patch("core.storage.st") as mock_st:
        result = storage_mod._load_all("test_corrupt")
    assert result == {}


def test_corrupt_json_triggers_warning():
    """Corrupt JSON should attempt to call st.warning."""
    _cleanup("test_corrupt_warn")
    path = _tool_path("test_corrupt_warn")
    _MOCK_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text("not valid json", encoding="utf-8")

    with mock.patch("core.storage.st") as mock_st:
        storage_mod._load_all("test_corrupt_warn")
        mock_st.warning.assert_called_once()


# ── Multiple scheme persistence ───────────────────────────

def test_multiple_schemes_persist_independently():
    _cleanup("test_multi")
    storage_mod.save_scheme("test_multi", "a", {"k": 1})
    storage_mod.save_scheme("test_multi", "b", {"k": 2})
    storage_mod.save_scheme("test_multi", "c", {"k": 3})

    assert storage_mod.load_scheme("test_multi", "a") == {"k": 1}
    assert storage_mod.load_scheme("test_multi", "b") == {"k": 2}
    assert storage_mod.load_scheme("test_multi", "c") == {"k": 3}


def test_list_schemes_empty_for_new_tool():
    _cleanup("test_new_tool")
    assert storage_mod.list_schemes("test_new_tool") == []


# ── Saved_at timestamp ────────────────────────────────────

def test_saved_at_is_stored():
    _cleanup("test_ts")
    storage_mod.save_scheme("test_ts", "ts_scheme", {"v": 1})
    path = _tool_path("test_ts")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "saved_at" in raw["ts_scheme"]
