"""Lightweight JSON-based scheme persistence for parameter presets."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

_STORAGE_DIR = Path(os.path.expanduser("~")) / ".omnifinance"


def _ensure_dir() -> Path:
    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return _STORAGE_DIR


def _tool_path(tool_name: str) -> Path:
    return _ensure_dir() / f"{tool_name}.json"


def _load_all(tool_name: str) -> dict[str, dict]:
    path = _tool_path(tool_name)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(tool_name: str, data: dict[str, dict]) -> None:
    path = _tool_path(tool_name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_scheme(tool_name: str, scheme_name: str, params: dict) -> None:
    """Save a named parameter scheme for a given tool."""
    data = _load_all(tool_name)
    data[scheme_name] = {
        "params": params,
        "saved_at": datetime.now().isoformat(),
    }
    _save_all(tool_name, data)


def load_scheme(tool_name: str, scheme_name: str) -> dict | None:
    """Load a named parameter scheme. Returns params dict or None."""
    data = _load_all(tool_name)
    entry = data.get(scheme_name)
    return entry["params"] if entry else None


def list_schemes(tool_name: str) -> list[str]:
    """List all saved scheme names for a tool."""
    return list(_load_all(tool_name).keys())


def delete_scheme(tool_name: str, scheme_name: str) -> None:
    """Delete a saved scheme."""
    data = _load_all(tool_name)
    data.pop(scheme_name, None)
    _save_all(tool_name, data)


def scheme_manager_ui(tool_name: str, current_params: dict, apply_callback=None) -> dict | None:
    """Render a save/load/delete UI in the sidebar. Returns loaded params or None."""
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

    # Load
    loaded = None
    if schemes:
        with st.sidebar.expander("加载 / 删除方案"):
            selected = st.selectbox("选择方案", schemes, key=f"_scheme_load_{tool_name}")
            col_load, col_del = st.columns(2)
            if col_load.button("📂 加载", key=f"_scheme_load_btn_{tool_name}"):
                loaded = load_scheme(tool_name, selected)
                if loaded:
                    st.success(f"已加载方案「{selected}」")
            if col_del.button("🗑️ 删除", key=f"_scheme_del_btn_{tool_name}"):
                delete_scheme(tool_name, selected)
                st.success(f"已删除方案「{selected}」")
                st.rerun()

    return loaded
