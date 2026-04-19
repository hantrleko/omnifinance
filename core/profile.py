"""Personal Financial Profile — single source of truth for user identity & key figures.

Stores name, age, income and city in ~/.omnifinance/profile.json.
All tools read from this module to pre-populate common inputs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypedDict

import streamlit as st

_PROFILE_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "profile.json"

CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "重庆", "其他"]

_DEFAULTS: dict = {
    "name": "",
    "age": 30,
    "city": "上海",
    "monthly_income": 15000.0,
    "monthly_expense": 8000.0,
    "risk_level": "稳健型",
    "family_status": "单身",
}

RISK_LEVELS = ["保守型", "稳健型", "平衡型", "进取型", "激进型"]
FAMILY_STATUSES = ["单身", "已婚无子女", "已婚有子女", "已婚多子女"]


class ProfileData(TypedDict):
    name: str
    age: int
    city: str
    monthly_income: float
    monthly_expense: float
    risk_level: str
    family_status: str


def load_profile() -> ProfileData:
    try:
        if _PROFILE_PATH.exists():
            raw = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
            merged = {**_DEFAULTS, **raw}
            return ProfileData(**{k: merged[k] for k in ProfileData.__annotations__})
    except (json.JSONDecodeError, OSError, TypeError, KeyError):
        pass
    return ProfileData(**_DEFAULTS)


def save_profile(data: ProfileData) -> None:
    try:
        _PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PROFILE_PATH.write_text(json.dumps(dict(data), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def get_profile() -> ProfileData:
    if "user_profile" not in st.session_state:
        st.session_state["user_profile"] = load_profile()
    return st.session_state["user_profile"]


def profile_sidebar_widget() -> ProfileData:
    profile = get_profile()

    with st.sidebar.expander("👤 我的财务档案", expanded=False):
        name = st.text_input("姓名/昵称", value=profile["name"], key="_profile_name", placeholder="可选，仅本地显示")
        age = st.number_input("年龄", min_value=18, max_value=80, value=profile["age"], step=1, key="_profile_age")
        city = st.selectbox("所在城市", CITIES, index=CITIES.index(profile["city"]) if profile["city"] in CITIES else 0, key="_profile_city")
        monthly_income = st.number_input(
            "月收入（税后，元）", min_value=0.0, max_value=500000.0,
            value=profile["monthly_income"], step=500.0, format="%.0f", key="_profile_income",
        )
        monthly_expense = st.number_input(
            "月固定支出（元）", min_value=0.0, max_value=500000.0,
            value=profile["monthly_expense"], step=500.0, format="%.0f", key="_profile_expense",
        )
        risk_level = st.selectbox(
            "风险偏好", RISK_LEVELS,
            index=RISK_LEVELS.index(profile["risk_level"]) if profile["risk_level"] in RISK_LEVELS else 1,
            key="_profile_risk",
        )
        family_status = st.selectbox(
            "家庭状况", FAMILY_STATUSES,
            index=FAMILY_STATUSES.index(profile["family_status"]) if profile["family_status"] in FAMILY_STATUSES else 0,
            key="_profile_family",
        )

        if st.button("💾 保存档案", key="_profile_save", use_container_width=True):
            updated: ProfileData = ProfileData(
                name=name, age=age, city=city,
                monthly_income=monthly_income, monthly_expense=monthly_expense,
                risk_level=risk_level, family_status=family_status,
            )
            save_profile(updated)
            st.session_state["user_profile"] = updated
            st.success("档案已保存")
            st.rerun()

    return get_profile()
