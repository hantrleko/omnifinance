"""Shared Plotly chart configuration for all OmniFinance pages.

Usage
-----
Import :func:`build_layout` or :data:`PALETTE` in each page instead of
duplicating the same dict literals across multiple files.

Key exports
-----------
- :data:`PALETTE`         — brand colour sequence (10 colours, dark-safe)
- :data:`PALETTE_LIGHT`   — lighter variant for light mode
- :data:`COLORS`          — semantic named colours (positive/negative/neutral…)
- :func:`build_layout`    — theme-aware Plotly layout dict
- :func:`get_palette`     — return correct palette for current theme
- :func:`render_empty_state` — centered empty-state placeholder
- :func:`hover_fmt`       — currency symbol for hovertemplate
- :func:`apply_chart_config` — apply uniform config_dict to st.plotly_chart
"""
from __future__ import annotations

from typing import Any

import streamlit as st

# ── Brand colour palettes ─────────────────────────────────

# 10-colour sequence — works on both dark and light backgrounds
PALETTE: list[str] = [
    "#4f8ef7",  # blue (primary)
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#ef4444",  # red
    "#8b5cf6",  # violet
    "#06b6d4",  # cyan
    "#f97316",  # orange
    "#ec4899",  # pink
    "#84cc16",  # lime
    "#6366f1",  # indigo
]

# Slightly muted variant for light mode
PALETTE_LIGHT: list[str] = [
    "#2563eb",  # blue
    "#059669",  # green
    "#d97706",  # amber
    "#dc2626",  # red
    "#7c3aed",  # violet
    "#0891b2",  # cyan
    "#ea580c",  # orange
    "#db2777",  # pink
    "#65a30d",  # lime
    "#4f46e5",  # indigo
]

# Semantic colours (theme-independent references)
class COLORS:
    """Semantic colour constants for consistent chart encoding."""
    POSITIVE = "#10b981"   # green — gains, surplus, good
    NEGATIVE = "#ef4444"   # red   — losses, deficit, bad
    NEUTRAL  = "#6b7280"   # gray  — neutral / zero line
    WARNING  = "#f59e0b"   # amber — caution
    PRIMARY  = "#4f8ef7"   # blue  — primary series / highlight
    SECONDARY = "#8b5cf6"  # violet — secondary series

    # Priority encoding
    HIGH   = "#ef4444"
    MEDIUM = "#f59e0b"
    LOW    = "#10b981"


# ── Plotly config dict ────────────────────────────────────

#: Pass to ``st.plotly_chart(..., config=PLOTLY_CONFIG)`` for a clean toolbar.
PLOTLY_CONFIG: dict[str, Any] = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d",
        "hoverClosestCartesian", "hoverCompareCartesian",
        "toggleSpikelines",
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "omnifinance_chart",
        "height": 600,
        "width": 1200,
        "scale": 2,
    },
}


# ── Base layout ───────────────────────────────────────────

_LAYOUT_BASE: dict[str, Any] = dict(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=12),
    ),
    margin=dict(t=36, b=44, l=8, r=8),
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="rgba(0,0,0,0.75)",
        font_size=12,
        font_family="Inter, sans-serif",
        bordercolor="rgba(255,255,255,0.15)",
    ),
)


def get_palette() -> list[str]:
    """Return the correct colour palette for the current theme.

    Returns :data:`PALETTE` in dark mode and :data:`PALETTE_LIGHT` in light mode.
    """
    is_dark = st.session_state.get("global_dark_mode", True)
    return PALETTE if is_dark else PALETTE_LIGHT


def build_layout(**overrides: Any) -> dict[str, Any]:
    """Return a theme-aware Plotly layout dict merged with any keyword overrides.

    Automatically adapts ``paper_bgcolor``, ``plot_bgcolor``, ``font``,
    grid-line colours, and legend font based on
    ``st.session_state["global_dark_mode"]``.

    Args:
        **overrides: Any Plotly layout keyword arguments to merge on top of
            the base layout (e.g. ``xaxis_title``, ``yaxis_tickformat``).

    Returns:
        A new ``dict`` suitable for passing to ``fig.update_layout(**...)``.

    Example::

        fig.update_layout(build_layout(
            xaxis_title="年份",
            yaxis_title="金额（元）",
            yaxis_tickformat=",",
        ))
    """
    layout: dict[str, Any] = {k: (v.copy() if isinstance(v, dict) else v)
                               for k, v in _LAYOUT_BASE.items()}

    is_dark = st.session_state.get("global_dark_mode", True)

    if is_dark:
        text_color   = "#f0f2f6"
        grid_color   = "rgba(255, 255, 255, 0.07)"
        zero_color   = "rgba(255, 255, 255, 0.18)"
        hover_bg     = "rgba(14, 17, 23, 0.88)"
    else:
        text_color   = "#111827"
        grid_color   = "rgba(0, 0, 0, 0.07)"
        zero_color   = "rgba(0, 0, 0, 0.20)"
        hover_bg     = "rgba(255, 255, 255, 0.92)"

    layout["paper_bgcolor"] = "rgba(0,0,0,0)"
    layout["plot_bgcolor"]  = "rgba(0,0,0,0)"
    layout["font"]          = dict(
        color=text_color,
        family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        size=12,
    )
    layout["legend"] = {
        **layout.get("legend", {}),
        "font": {"color": text_color, "size": 12},
        "bgcolor": "rgba(0,0,0,0)",
    }
    layout["hoverlabel"] = {
        **layout.get("hoverlabel", {}),
        "bgcolor": hover_bg,
        "font_color": text_color,
    }
    layout["xaxis"] = {
        **layout.get("xaxis", {}),
        "gridcolor": grid_color,
        "zerolinecolor": zero_color,
        "linecolor": grid_color,
        "tickfont": {"color": text_color, "size": 11},
        "title_font": {"color": text_color, "size": 12},
    }
    layout["yaxis"] = {
        **layout.get("yaxis", {}),
        "gridcolor": grid_color,
        "zerolinecolor": zero_color,
        "linecolor": grid_color,
        "tickfont": {"color": text_color, "size": 11},
        "title_font": {"color": text_color, "size": 12},
    }

    layout.update(overrides)
    return layout


def apply_chart_config(
    fig: Any,
    *,
    use_container_width: bool = True,
    key: str | None = None,
) -> None:
    """Render a Plotly figure with the standard OmniFinance chart config.

    This is a thin wrapper around ``st.plotly_chart`` that always passes
    :data:`PLOTLY_CONFIG` so callers don't need to repeat it.

    Args:
        fig: A ``plotly.graph_objects.Figure`` instance.
        use_container_width: Whether to stretch the chart to container width.
        key: Optional Streamlit widget key for the chart.
    """
    st.plotly_chart(
        fig,
        use_container_width=use_container_width,
        config=PLOTLY_CONFIG,
        key=key,
    )


# ── Empty state ───────────────────────────────────────────

def render_empty_state(
    title: str = "暂无数据",
    message: str = "当前没有可显示的数据，请检查数据源或调整参数后重试。",
    icon: str = "📭",
) -> None:
    """Render a centered empty-state placeholder inside a chart area.

    Call this instead of silently hiding a chart or showing a bare error
    string when data is unavailable.

    Args:
        title:   Short heading shown in the empty state.
        message: Descriptive hint text shown below the title.
        icon:    Emoji icon shown above the title.
    """
    st.markdown(
        f"""
        <div style="
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; padding: 52px 24px;
            border: 1.5px dashed rgba(128,128,128,0.30);
            border-radius: 14px; text-align: center;
            color: #9ca3af;
        ">
            <div style="font-size: 2.6rem; margin-bottom: 12px; opacity: 0.85;">{icon}</div>
            <div style="font-size: 1.05rem; font-weight: 600; margin-bottom: 6px;">{title}</div>
            <div style="font-size: 0.88rem; line-height: 1.55; max-width: 360px;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Hover format helper ───────────────────────────────────

def hover_fmt(symbol: str, value_fmt: str = ",.2f") -> str:  # noqa: ARG001
    """Return the currency symbol for embedding in a Plotly hovertemplate.

    Args:
        symbol:    Currency symbol string returned by ``core.currency.get_symbol()``.
        value_fmt: Python format spec for the numeric value (kept for API compat).

    Returns:
        The *symbol* string unchanged, e.g. ``"¥"`` or ``"$"``.

    Example::

        hovertemplate = f"%{{x|%Y-%m-%d}}<br>价格: {hover_fmt(sym)}%{{y:,.2f}}<extra></extra>"
    """
    return symbol


# ── Priority colour helper ────────────────────────────────

def priority_color(priority: str) -> str:
    """Map a Chinese priority label to a semantic colour.

    Args:
        priority: One of ``"高"``, ``"中"``, ``"低"``.

    Returns:
        A hex colour string from :class:`COLORS`.
    """
    return {
        "高": COLORS.HIGH,
        "中": COLORS.MEDIUM,
        "低": COLORS.LOW,
    }.get(priority, COLORS.NEUTRAL)
