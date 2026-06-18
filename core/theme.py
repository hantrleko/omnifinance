"""OmniFinance global UI theme engine.

Design token system
-------------------
All colours, radii, shadows and spacing values are defined as Python
dataclasses at the top of this module.  ``inject_theme()`` reads
``st.session_state["global_dark_mode"]`` and emits a single ``<style>``
block that applies the correct token set.

Public API
----------
- :func:`inject_theme`        — inject full CSS theme (called by page_setup)
- :func:`inject_page_css`     — inject page-level utility CSS only
- :func:`show_error_banner`   — unified data-source error banner
- :func:`load_dark_mode_pref` / :func:`save_dark_mode_pref` — persistence
"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

import streamlit as st

# ── Persistence ───────────────────────────────────────────

_PREFS_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "preferences.json"


def load_dark_mode_pref() -> bool:
    try:
        if _PREFS_PATH.exists():
            data = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
            return bool(data.get("dark_mode", False))
    except (json.JSONDecodeError, OSError):
        pass
    return False


def save_dark_mode_pref(dark_mode: bool) -> None:
    try:
        _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if _PREFS_PATH.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                existing = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
        existing["dark_mode"] = dark_mode
        _PREFS_PATH.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


# ── Design tokens ─────────────────────────────────────────

class _DarkTokens:
    """Design tokens for dark mode."""
    bg_app        = "#0e1117"
    bg_card       = "rgba(255, 255, 255, 0.05)"
    bg_card_hover = "rgba(255, 255, 255, 0.08)"
    bg_input      = "rgba(255, 255, 255, 0.06)"
    bg_sidebar    = "rgba(14, 17, 23, 0.92)"
    text_primary   = "#f0f2f6"
    text_secondary = "#a0a8b8"
    text_muted     = "#6b7280"
    accent_primary  = "#4f8ef7"
    accent_success  = "#10b981"
    accent_warning  = "#f59e0b"
    accent_danger   = "#ef4444"
    border_default = "rgba(255, 255, 255, 0.10)"
    border_hover   = "rgba(79, 142, 247, 0.55)"
    border_focus   = "rgba(79, 142, 247, 0.80)"
    shadow_card  = "0 2px 8px rgba(0, 0, 0, 0.30)"
    shadow_hover = "0 8px 24px rgba(79, 142, 247, 0.20)"
    shadow_focus = "0 0 0 3px rgba(79, 142, 247, 0.25)"
    blur_glass = "blur(16px)"
    is_dark = True


class _LightTokens:
    """Design tokens for light mode."""
    bg_app        = "#f4f6f9"
    bg_card       = "rgba(255, 255, 255, 0.85)"
    bg_card_hover = "rgba(255, 255, 255, 0.98)"
    bg_input      = "rgba(255, 255, 255, 0.90)"
    bg_sidebar    = "rgba(248, 250, 252, 0.95)"
    text_primary   = "#111827"
    text_secondary = "#4b5563"
    text_muted     = "#9ca3af"
    accent_primary  = "#2563eb"
    accent_success  = "#059669"
    accent_warning  = "#d97706"
    accent_danger   = "#dc2626"
    border_default = "rgba(0, 0, 0, 0.08)"
    border_hover   = "rgba(37, 99, 235, 0.45)"
    border_focus   = "rgba(37, 99, 235, 0.70)"
    shadow_card  = "0 1px 4px rgba(0, 0, 0, 0.08)"
    shadow_hover = "0 6px 20px rgba(37, 99, 235, 0.14)"
    shadow_focus = "0 0 0 3px rgba(37, 99, 235, 0.18)"
    blur_glass = "blur(12px)"
    is_dark = False


# ── Page-level utility CSS (no theme dependency) ──────────

_PAGE_UTILITY_CSS = """
<style>
  .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }

  [data-testid="stMetric"] {
    border-radius: 12px !important;
    padding: 14px 16px !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  }

  [data-testid="stVerticalBlockBorderWrapper"] {
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  }
  [data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px);
  }

  [data-testid="stPageLink"] a {
    border-radius: 8px;
    padding: 0.3rem 0.45rem;
    transition: background-color 0.15s ease, transform 0.15s ease;
    text-decoration: none !important;
  }
  [data-testid="stPageLink"] a:hover {
    transform: translateX(3px);
    text-decoration: none !important;
  }

  [data-testid="stTabs"] [role="tablist"] { gap: 4px; }
  [data-testid="stTabs"] button[role="tab"] {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500;
    padding: 0.45rem 0.9rem !important;
    transition: background-color 0.15s ease;
  }

  [data-testid="stProgressBar"] > div { border-radius: 999px; }
  [data-testid="stExpander"] summary { font-weight: 500; }

  hr { margin: 1.6rem 0 !important; opacity: 0.35; }

  [data-testid="stCaptionContainer"] p {
    font-size: 0.82rem !important;
    line-height: 1.5 !important;
  }

  @media (max-width: 640px) {
    .block-container { padding-left: 0.8rem !important; padding-right: 0.8rem !important; }
    [data-testid="stSidebar"] { min-width: 240px !important; }
  }
</style>
"""


def inject_page_css() -> None:
    """Inject page-level utility CSS (no theme dependency)."""
    st.markdown(_PAGE_UTILITY_CSS, unsafe_allow_html=True)


# ── Error banner ──────────────────────────────────────────

def show_error_banner(message: str, kind: str = "warning") -> None:
    """Show a unified banner for data source failures."""
    fn = {"warning": st.warning, "error": st.error, "info": st.info}.get(kind, st.warning)
    fn(f"⚠️ 数据源暂时不可用：{message}。已使用缓存数据，结果仅供参考。")


# ── Theme injection ───────────────────────────────────────

def inject_theme() -> None:
    """Inject the full OmniFinance CSS theme into the current Streamlit page.

    Reads ``st.session_state["global_dark_mode"]`` (default ``True``) and
    emits a single ``<style>`` block using the appropriate design token set.
    """
    dark_mode: bool = st.session_state.get("global_dark_mode", True)
    t = _DarkTokens if dark_mode else _LightTokens

    css = f"""
    <style>
        /* ── Typography ─────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="st-"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            -webkit-font-smoothing: antialiased;
        }}
        .material-symbols-rounded,
        [data-testid="stIconMaterial"],
        .stIcon {{
            font-family: 'Material Symbols Rounded' !important;
        }}

        h1 {{ font-size: 1.75rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.2; }}
        h2 {{ font-size: 1.35rem; font-weight: 700; letter-spacing: -0.025em; line-height: 1.3; }}
        h3 {{ font-size: 1.10rem; font-weight: 600; letter-spacing: -0.02em; line-height: 1.4; }}
        h4 {{ font-size: 0.95rem; font-weight: 600; letter-spacing: -0.01em; }}
        p  {{ line-height: 1.65; }}

        /* ── App background & text ──────────────────────── */
        [data-testid="stAppViewContainer"] {{
            background-color: {t.bg_app};
            color: {t.text_primary};
            transition: background-color 0.25s ease;
        }}
        [data-testid="stAppViewContainer"] p,
        [data-testid="stAppViewContainer"] span,
        [data-testid="stAppViewContainer"] label {{
            color: {t.text_primary};
        }}

        /* ── Sidebar ────────────────────────────────────── */
        [data-testid="stSidebar"] {{
            background-color: {t.bg_sidebar};
            backdrop-filter: {t.blur_glass};
            -webkit-backdrop-filter: {t.blur_glass};
            border-right: 1px solid {t.border_default};
        }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebarNav"] span {{
            color: {t.text_primary} !important;
        }}
        [data-testid="stSidebarNav"] svg {{
            fill: {t.text_secondary} !important;
            stroke: {t.text_secondary} !important;
        }}
        [data-testid="stSidebar"] .stNumberInput label,
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stSlider label,
        [data-testid="stSidebar"] .stTextInput label {{
            font-size: 0.82rem;
            color: {t.text_secondary} !important;
            font-weight: 500;
        }}

        /* ── Cards ──────────────────────────────────────── */
        [data-testid="stMetric"] {{
            background-color: {t.bg_card} !important;
            backdrop-filter: {t.blur_glass};
            -webkit-backdrop-filter: {t.blur_glass};
            border: 1px solid {t.border_default} !important;
            border-radius: 12px !important;
            box-shadow: {t.shadow_card};
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }}
        [data-testid="stMetric"]:hover {{
            transform: translateY(-3px);
            box-shadow: {t.shadow_hover};
            border-color: {t.border_hover} !important;
        }}
        [data-testid="stMetric"] [data-testid="stMetricLabel"] {{
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: {t.text_secondary} !important;
        }}
        [data-testid="stMetric"] [data-testid="stMetricValue"] {{
            font-size: 1.45rem !important;
            font-weight: 700 !important;
            color: {t.text_primary} !important;
        }}
        [data-testid="stMetric"] [data-testid="stMetricDelta"] {{
            font-size: 0.80rem !important;
        }}

        .stDataFrame {{
            background-color: {t.bg_card} !important;
            border: 1px solid {t.border_default} !important;
            border-radius: 12px !important;
            box-shadow: {t.shadow_card};
            overflow: hidden;
        }}
        [data-testid="stExpander"] {{
            background-color: {t.bg_card} !important;
            border: 1px solid {t.border_default} !important;
            border-radius: 12px !important;
            box-shadow: {t.shadow_card};
        }}

        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: {t.border_default} !important;
            border-radius: 12px !important;
        }}
        [data-testid="stVerticalBlockBorderWrapper"]:hover {{
            box-shadow: {t.shadow_hover};
            border-color: {t.border_hover} !important;
        }}

        /* ── Buttons ────────────────────────────────────── */
        div.stButton > button {{
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            padding: 0.45rem 1rem !important;
            border: 1px solid {t.border_default} !important;
            color: {t.text_primary} !important;
            background-color: {t.bg_card} !important;
            transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        div.stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: {t.shadow_hover};
            border-color: {t.border_hover} !important;
            background-color: {t.bg_card_hover} !important;
        }}
        div.stButton > button:focus-visible {{
            outline: none !important;
            box-shadow: {t.shadow_focus} !important;
            border-color: {t.border_focus} !important;
        }}

        div.stDownloadButton > button {{
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            border: 1px solid {t.border_default} !important;
            transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        div.stDownloadButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: {t.shadow_hover};
            border-color: {t.border_hover} !important;
        }}

        /* ── Inputs ─────────────────────────────────────── */
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {{
            background-color: {t.bg_input} !important;
            border: 1px solid {t.border_default} !important;
            border-radius: 8px !important;
            color: {t.text_primary} !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }}
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {{
            border-color: {t.border_focus} !important;
            box-shadow: {t.shadow_focus} !important;
            outline: none !important;
        }}
        [data-testid="stSelectbox"] > div > div {{
            background-color: {t.bg_input} !important;
            border: 1px solid {t.border_default} !important;
            border-radius: 8px !important;
        }}

        /* ── Tabs ───────────────────────────────────────── */
        [data-testid="stTabs"] button[role="tab"] {{
            font-weight: 500;
            color: {t.text_secondary} !important;
        }}
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
            color: {t.accent_primary} !important;
            font-weight: 600 !important;
        }}

        /* ── Alerts ─────────────────────────────────────── */
        [data-testid="stAlert"] {{
            border-radius: 10px !important;
            border-left-width: 4px !important;
        }}

        /* ── Header ─────────────────────────────────────── */
        header {{ background-color: transparent !important; }}

        /* ── Page-link hover ────────────────────────────── */
        [data-testid="stPageLink"] a:hover {{
            background-color: {"rgba(79,142,247,0.10)" if dark_mode else "rgba(37,99,235,0.08)"};
        }}

        /* ── Scrollbar ──────────────────────────────────── */
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{
            background: {t.border_default};
            border-radius: 999px;
        }}
        ::-webkit-scrollbar-thumb:hover {{ background: {t.border_hover}; }}

        /* ── Calculator button categories ───────────────── */
        .calc-btn-operator > div > button {{
            background-color: {"rgba(79,142,247,0.18)" if dark_mode else "rgba(37,99,235,0.10)"} !important;
            border-color: {"rgba(79,142,247,0.40)" if dark_mode else "rgba(37,99,235,0.30)"} !important;
        }}
        .calc-btn-function > div > button {{
            background-color: {"rgba(16,185,129,0.18)" if dark_mode else "rgba(5,150,105,0.10)"} !important;
            border-color: {"rgba(16,185,129,0.40)" if dark_mode else "rgba(5,150,105,0.30)"} !important;
            font-size: 0.80rem !important;
        }}
        .calc-btn-special > div > button {{
            background-color: {"rgba(239,68,68,0.18)" if dark_mode else "rgba(220,38,38,0.10)"} !important;
            border-color: {"rgba(239,68,68,0.40)" if dark_mode else "rgba(220,38,38,0.30)"} !important;
        }}
        .calc-btn-equals > div > button {{
            background-color: {t.accent_primary} !important;
            border-color: {t.accent_primary} !important;
            color: #ffffff !important;
            font-weight: 700 !important;
        }}
        .calc-btn-equals > div > button:hover {{ filter: brightness(1.12); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    inject_page_css()
