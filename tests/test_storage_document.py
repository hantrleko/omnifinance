"""Unit tests for the document-store API added to core.storage in v1.6.

Tests cover load_document, save_document, and delete_document using a
temporary directory so no real ~/.omnifinance files are touched.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import core.storage as storage


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path):
    """Redirect the storage directory to a temporary path for every test."""
    with patch.object(storage, "_STORAGE_DIR", tmp_path):
        yield tmp_path


# ── load_document ─────────────────────────────────────────

class TestLoadDocument:
    def test_returns_default_when_file_missing(self):
        assert storage.load_document("nonexistent") is None

    def test_returns_custom_default_when_file_missing(self):
        assert storage.load_document("nonexistent", default=[]) == []

    def test_loads_list(self, isolated_storage: Path):
        data = [{"a": 1}, {"b": 2}]
        (isolated_storage / "mylist.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        assert storage.load_document("mylist") == data

    def test_loads_dict(self, isolated_storage: Path):
        data = {"key": "value", "num": 42}
        (isolated_storage / "mydict.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        assert storage.load_document("mydict") == data

    def test_returns_default_on_corrupt_json(self, isolated_storage: Path):
        (isolated_storage / "corrupt.json").write_text("NOT JSON", encoding="utf-8")
        assert storage.load_document("corrupt", default="fallback") == "fallback"

    def test_returns_default_on_empty_file(self, isolated_storage: Path):
        (isolated_storage / "empty.json").write_text("", encoding="utf-8")
        assert storage.load_document("empty", default=42) == 42


# ── save_document ─────────────────────────────────────────

class TestSaveDocument:
    def test_saves_list(self, isolated_storage: Path):
        data = [1, 2, 3]
        storage.save_document("nums", data)
        saved = json.loads((isolated_storage / "nums.json").read_text(encoding="utf-8"))
        assert saved == data

    def test_saves_dict(self, isolated_storage: Path):
        data = {"hello": "world"}
        storage.save_document("greeting", data)
        saved = json.loads((isolated_storage / "greeting.json").read_text(encoding="utf-8"))
        assert saved == data

    def test_overwrites_existing(self, isolated_storage: Path):
        storage.save_document("item", {"v": 1})
        storage.save_document("item", {"v": 2})
        saved = json.loads((isolated_storage / "item.json").read_text(encoding="utf-8"))
        assert saved == {"v": 2}

    def test_roundtrip(self, isolated_storage: Path):
        original = [{"date": "2024-01-01", "amount": 1000.0}]
        storage.save_document("diary", original)
        loaded = storage.load_document("diary", default=[])
        assert loaded == original

    def test_creates_directory_if_missing(self, tmp_path: Path):
        nested = tmp_path / "deep" / "nested"
        with patch.object(storage, "_STORAGE_DIR", nested):
            storage.save_document("x", {"ok": True})
        assert (nested / "x.json").exists()

    def test_unicode_preserved(self, isolated_storage: Path):
        data = {"note": "你好，世界！"}
        storage.save_document("unicode_test", data)
        loaded = storage.load_document("unicode_test")
        assert loaded == data


# ── delete_document ───────────────────────────────────────

class TestDeleteDocument:
    def test_returns_true_when_deleted(self, isolated_storage: Path):
        storage.save_document("todel", {"x": 1})
        assert storage.delete_document("todel") is True
        assert not (isolated_storage / "todel.json").exists()

    def test_returns_false_when_not_found(self):
        assert storage.delete_document("ghost") is False

    def test_file_gone_after_delete(self, isolated_storage: Path):
        storage.save_document("gone", [1, 2])
        storage.delete_document("gone")
        assert storage.load_document("gone", default="missing") == "missing"


# ── Integration: save → load → delete cycle ───────────────

class TestCycle:
    def test_full_cycle(self, isolated_storage: Path):
        name = "cycle_test"
        payload = {"entries": [{"id": 1, "val": 99}]}

        # Save
        storage.save_document(name, payload)

        # Load
        loaded = storage.load_document(name, default={})
        assert loaded == payload

        # Delete
        deleted = storage.delete_document(name)
        assert deleted is True

        # After deletion, default is returned
        assert storage.load_document(name, default="gone") == "gone"
