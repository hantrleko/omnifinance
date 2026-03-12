"""Shared Plotly chart configuration for all OmniFinance pages.

Import LAYOUT_BASE or build_layout() in each page instead of
duplicating the same dict literal across multiple files.
"""

from __future__ import annotations


# ── Base layout used by all pages ────────────────────────
LAYOUT_BASE: dict = dict(
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


def build_layout(**overrides) -> dict:
    """Return a copy of LAYOUT_BASE merged with any keyword overrides.

    Example::

        fig.update_layout(build_layout(
            xaxis_title="年份",
            yaxis_title="金额（元）",
            yaxis_tickformat=",",
        ))
    """
    layout = dict(LAYOUT_BASE)
    layout.update(overrides)
    return layout


def hover_fmt(symbol: str, value_fmt: str = ",.2f") -> str:
    """Build a Plotly hovertemplate value string with the correct currency symbol.

    Args:
        symbol: Currency symbol string returned by ``core.currency.get_symbol()``.
        value_fmt: Python format spec for the numeric value (default ``,.2f``).

    Returns:
        A string like ``"¥%{y:,.2f}"`` suitable for embedding in hovertemplate.

    Example::

        hovertemplate = f"%{{x|%Y-%m-%d}}<br>价格: {hover_fmt(sym)}%{{y:,.2f}}<extra></extra>"
        # becomes:  "%{x|%Y-%m-%d}<br>价格: ¥%{y:,.2f}<extra></extra>"
    """
    return symbol
