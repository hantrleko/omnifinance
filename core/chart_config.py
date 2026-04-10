"""Shared Plotly chart configuration for all OmniFinance pages.

Import LAYOUT_BASE or build_layout() in each page instead of
duplicating the same dict literal across multiple files.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


# ── Base layout used by all pages ────────────────────────
LAYOUT_BASE: dict[str, Any] = dict(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(),
    ),
    margin=dict(t=30, b=40),
    hovermode="x unified",
)


def build_layout(**overrides: Any) -> dict[str, Any]:
    """Return a copy of LAYOUT_BASE merged with any keyword overrides.

    Automatically adapts chart background and font colors based on the
    current dark/light mode stored in ``st.session_state["global_dark_mode"]``.

    Args:
        **overrides: Any Plotly layout keyword arguments to merge on top of
            :data:`LAYOUT_BASE` (e.g. ``xaxis_title``, ``yaxis_tickformat``).

    Returns:
        A new ``dict`` suitable for passing to ``fig.update_layout()``.

    Example::

        fig.update_layout(build_layout(
            xaxis_title="年份",
            yaxis_title="金额（元）",
            yaxis_tickformat=",",
        ))
    """
    layout: dict[str, Any] = dict(LAYOUT_BASE)

    # Dynamic theme-aware colors
    is_dark = st.session_state.get("global_dark_mode", True)
    if is_dark:
        layout["paper_bgcolor"] = "rgba(0,0,0,0)"
        layout["plot_bgcolor"] = "rgba(0,0,0,0)"
        layout["font"] = dict(color="#fafafa")
        layout.setdefault("legend", {}).update({"font": {"color": "#fafafa"}})
        layout["xaxis"] = {**layout.get("xaxis", {}), "gridcolor": "rgba(255,255,255,0.08)"}
        layout["yaxis"] = {**layout.get("yaxis", {}), "gridcolor": "rgba(255,255,255,0.08)"}
    else:
        layout["paper_bgcolor"] = "rgba(0,0,0,0)"
        layout["plot_bgcolor"] = "rgba(0,0,0,0)"
        layout["font"] = dict(color="#1a1a1a")
        layout.setdefault("legend", {}).update({"font": {"color": "#1a1a1a"}})
        layout["xaxis"] = {**layout.get("xaxis", {}), "gridcolor": "rgba(0,0,0,0.08)"}
        layout["yaxis"] = {**layout.get("yaxis", {}), "gridcolor": "rgba(0,0,0,0.08)"}

    layout.update(overrides)
    return layout


def render_empty_state(
    title: str = "暂无数据",
    message: str = "当前没有可显示的数据，请检查数据源或调整参数后重试。",
    icon: str = "📭",
) -> None:
    """Render a centered empty-state placeholder inside a chart area.

    Call this instead of silently hiding a chart or showing a bare error
    string when data is unavailable.

    Args:
        title: Short heading shown in the empty state (default: ``"暂无数据"``).
        message: Descriptive hint text shown below the title.
        icon: Emoji icon shown above the title (default: ``"📭"``).
    """
    st.markdown(
        f"""
        <div style="
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; padding: 48px 24px;
            border: 1.5px dashed var(--secondary-background-color, #555);
            border-radius: 12px; text-align: center; color: #888;
        ">
            <div style="font-size: 2.8rem; margin-bottom: 10px;">{icon}</div>
            <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 6px;">{title}</div>
            <div style="font-size: 0.9rem;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hover_fmt(symbol: str, value_fmt: str = ",.2f") -> str:
    """Return the currency symbol for embedding in a Plotly hovertemplate.

    Args:
        symbol: Currency symbol string returned by ``core.currency.get_symbol()``.
        value_fmt: Python format spec for the numeric value (default ``,.2f``).
            Currently unused but kept for API compatibility.

    Returns:
        The *symbol* string unchanged, e.g. ``"¥"`` or ``"$"``.
        Embed it directly before the ``%{y:...}`` placeholder in a template.

    Example::

        hovertemplate = f"%{{x|%Y-%m-%d}}<br>价格: {hover_fmt(sym)}%{{y:,.2f}}<extra></extra>"
        # becomes:  "%{x|%Y-%m-%d}<br>价格: ¥%{y:,.2f}<extra></extra>"
    """
    return symbol
