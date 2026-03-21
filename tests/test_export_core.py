"""Tests for core/export.py — Excel export utilities."""

import io

import pandas as pd
import pytest

from core.export import dataframes_to_excel


# ── Basic sanity ──────────────────────────────────────────

def test_returns_bytes():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    result = dataframes_to_excel([("Sheet1", df)])
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_valid_xlsx_bytes():
    """The returned bytes should be parseable as a valid Excel file."""
    df = pd.DataFrame({"x": [10, 20, 30]})
    raw = dataframes_to_excel([("Data", df)])
    wb = pd.read_excel(io.BytesIO(raw), sheet_name=None)
    assert "Data" in wb


def test_multi_sheet():
    df1 = pd.DataFrame({"col": [1, 2]})
    df2 = pd.DataFrame({"val": [3, 4, 5]})
    raw = dataframes_to_excel([("Sheet1", df1), ("Sheet2", df2)])
    wb = pd.read_excel(io.BytesIO(raw), sheet_name=None)
    assert "Sheet1" in wb
    assert "Sheet2" in wb


def test_data_preserved():
    df = pd.DataFrame({"name": ["Alice", "Bob"], "score": [95, 87]})
    raw = dataframes_to_excel([("Results", df)])
    # No title passed → row 1 is the header, data follows directly.
    loaded = pd.read_excel(io.BytesIO(raw), sheet_name="Results")
    assert list(loaded.columns) == ["name", "score"]
    assert loaded["name"].tolist() == ["Alice", "Bob"]
    assert loaded["score"].tolist() == [95, 87]


def test_sheet_name_truncated():
    """Sheet names longer than 31 chars should be silently truncated."""
    long_name = "A" * 40
    df = pd.DataFrame({"v": [1]})
    raw = dataframes_to_excel([(long_name, df)])
    wb = pd.read_excel(io.BytesIO(raw), sheet_name=None)
    expected_name = long_name[:31]
    assert expected_name in wb


def test_empty_dataframe():
    """An empty DataFrame should not raise an error."""
    df = pd.DataFrame()
    raw = dataframes_to_excel([("Empty", df)])
    assert isinstance(raw, bytes)
    assert len(raw) > 0


def test_title_injected():
    """When title is provided it should appear as the first cell."""
    import openpyxl
    df = pd.DataFrame({"col": [1, 2]})
    title = "My Report Title"
    raw = dataframes_to_excel([("Sheet1", df)], title=title)
    wb = openpyxl.load_workbook(io.BytesIO(raw))
    ws = wb.active
    assert ws.cell(row=1, column=1).value == title
