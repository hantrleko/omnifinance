"""Long-term moat (economic moat) scoring engine.

This module contains all *pure* computation logic extracted from
``pages/28_长期护城河评分器.py``.  It has no Streamlit dependency and is
therefore fully unit-testable.

Public API
----------
- :func:`to_float`              — safe Any → float conversion
- :func:`score_segment`         — ratio → 0-5 score mapping
- :func:`weighted_score`        — weighted average with None-aware fallback
- :func:`fetch_signal_scores`   — pull yfinance signals and map to 0-5 scores
- :func:`compute_composite`     — combine subjective + objective scores
"""
from __future__ import annotations

import math
from typing import Any


# ── Type aliases ──────────────────────────────────────────

ScoreMap = dict[str, float | None]

# Default thresholds for _score_segment when good_if_higher=True
_DEFAULT_POINTS: tuple[float, ...] = (0.1, 0.2, 0.3, 0.45, 0.6)


# ── Pure helpers ──────────────────────────────────────────

def to_float(value: Any) -> float | None:
    """Convert any object to float safely.

    Returns ``None`` for ``None``, empty strings, ``"N/A"``, ``nan``, or
    any value that cannot be coerced to a finite float.

    Args:
        value: Any Python object.

    Returns:
        A finite ``float`` or ``None``.

    Examples::

        >>> to_float(0.25)
        0.25
        >>> to_float("0.35") is not None
        True
        >>> to_float(None) is None
        True
        >>> to_float("N/A") is None
        True
    """
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            f = float(value)
            return None if (math.isnan(f) or math.isinf(f)) else f
        text = str(value).replace(",", "").strip()
        if not text or text in {"None", "nan", "N/A", "inf", "-inf"}:
            return None
        f = float(text)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def score_segment(
    value: float | None,
    *,
    good_if_higher: bool = True,
    points: tuple[float, ...] = _DEFAULT_POINTS,
) -> float | None:
    """Convert a ratio/value to a 0-5 score according to custom thresholds.

    Args:
        value:          The numeric value to score.  ``None`` returns ``None``.
        good_if_higher: When ``True`` (default), higher values score better.
                        When ``False``, lower values score better (e.g.
                        debt-to-equity ratio).
        points:         Five ascending threshold values used when
                        ``good_if_higher=True``.  Ignored when
                        ``good_if_higher=False`` (fixed debt/equity thresholds
                        are used instead).

    Returns:
        A score in ``{1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0}`` or
        ``None`` if *value* is ``None`` / non-finite.

    Examples::

        >>> score_segment(0.5)
        5.0
        >>> score_segment(0.05)
        1.5
        >>> score_segment(0.3, good_if_higher=False)  # debt/equity
        4.0
    """
    if value is None or not isinstance(value, (int, float)):
        return None
    if math.isnan(value) or math.isinf(value):
        return None

    if not good_if_higher:
        # Debt/equity: lower is better
        if value <= 0:
            return 5.0
        if value <= 0.2:
            return 4.5
        if value <= 0.4:
            return 4.0
        if value <= 0.7:
            return 3.0
        if value <= 1.2:
            return 2.0
        return 1.0

    # Higher is better
    if value >= points[4]:
        return 5.0
    if value >= points[3]:
        return 4.0
    if value >= points[2]:
        return 3.5
    if value >= points[1]:
        return 2.5
    if value >= points[0]:
        return 1.5
    return 1.0


def weighted_score(values: list[float | None], weights: list[float]) -> float:
    """Compute a weighted average, ignoring ``None`` entries.

    When all values are ``None`` or *values* is empty, returns ``0.0``.

    Args:
        values:  List of scores (may contain ``None``).
        weights: List of weights corresponding to each score.

    Returns:
        Weighted average as a ``float``.

    Examples::

        >>> weighted_score([4.0, 5.0], [1.0, 1.0])
        4.5
        >>> weighted_score([None, 3.0], [1.0, 1.0])
        3.0
        >>> weighted_score([], [])
        0.0
    """
    if not values:
        return 0.0
    valid = [(v, w) for v, w in zip(values, weights) if v is not None]
    if not valid:
        return 0.0
    total_w = sum(w for _, w in valid)
    if total_w <= 0:
        return 0.0
    return sum(v * w for v, w in valid) / total_w


def fetch_signal_scores(symbol: str) -> ScoreMap:
    """Fetch a lightweight set of proxy signals from yfinance and score them.

    Pulls publicly available financial ratios and historical volatility for
    *symbol* and maps each to a 0-5 score using :func:`score_segment`.

    Args:
        symbol: Ticker symbol (e.g. ``"AAPL"``, ``"0700.HK"``).

    Returns:
        A dict mapping signal name → score (``float``) or ``None`` when data
        is unavailable.  Never raises; returns a dict of ``None`` values on
        any error.

    Notes:
        This function performs network I/O via ``yfinance``.  Cache the result
        in ``st.session_state`` when calling from Streamlit pages.
    """
    scores: ScoreMap = {
        "利润率强度": None,
        "盈利质量": None,
        "资本效率": None,
        "成长延续性": None,
        "价格弹性": None,
        "财务韧性": None,
    }
    try:
        import yfinance as yf  # noqa: PLC0415 — optional dependency

        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        gross_margin = to_float(info.get("grossMargins"))
        op_margin = to_float(info.get("operatingMargins"))
        roa = to_float(info.get("returnOnAssets"))
        if roa is None:
            roa = to_float(info.get("returnOnEquity"))
        debt_to_equity = to_float(info.get("debtToEquity"))
        revenue_growth = to_float(info.get("revenueGrowth"))

        # Normalise percentages that yfinance sometimes returns as 0-100 scale
        for val_name, val in [
            ("gross_margin", gross_margin),
            ("op_margin", op_margin),
            ("roa", roa),
        ]:
            pass  # normalisation applied inline below

        if gross_margin is not None and gross_margin > 1:
            gross_margin /= 100
        if op_margin is not None and op_margin > 1:
            op_margin /= 100
        if roa is not None and roa > 1:
            roa /= 100
        if revenue_growth is not None and abs(revenue_growth) > 1:
            revenue_growth /= 100
        if debt_to_equity is not None and debt_to_equity > 10:
            debt_to_equity /= 100

        gm_score = score_segment(gross_margin)
        om_score = score_segment(op_margin)
        scores["利润率强度"] = max(
            gm_score if gm_score is not None else 0.0,
            om_score if om_score is not None else 0.0,
        ) or None
        scores["盈利质量"] = om_score
        scores["资本效率"] = score_segment(roa, points=(0.02, 0.04, 0.08, 0.12, 0.2))
        scores["财务韧性"] = score_segment(debt_to_equity, good_if_higher=False)
        scores["成长延续性"] = score_segment(revenue_growth)

        # 价格弹性 — proxy: lower 12-month annualised volatility → stronger moat
        hist = ticker.history(period="12mo", interval="1d")
        if hist is not None and not hist.empty and "Close" in hist:
            rets = hist["Close"].pct_change().dropna()
            if len(rets) >= 40:
                ann_vol = to_float(rets.std() * math.sqrt(252))
                if ann_vol is not None:
                    if ann_vol <= 0.18:
                        scores["价格弹性"] = 5.0
                    elif ann_vol <= 0.25:
                        scores["价格弹性"] = 4.5
                    elif ann_vol <= 0.35:
                        scores["价格弹性"] = 3.5
                    elif ann_vol <= 0.45:
                        scores["价格弹性"] = 2.5
                    else:
                        scores["价格弹性"] = 1.5
    except Exception:  # noqa: BLE001 — never crash the UI
        pass

    return scores


def compute_composite(
    subjective: dict[str, float],
    objective: ScoreMap,
    *,
    subjective_weight: float = 0.5,
    objective_weight: float = 0.5,
) -> dict[str, float]:
    """Combine subjective and objective scores into a composite result.

    Args:
        subjective:         Dict of dimension name → score (1-5 scale).
        objective:          Dict of dimension name → score (0-5 scale) or
                            ``None`` for unavailable signals.
        subjective_weight:  Weight for the subjective component (default 0.5).
        objective_weight:   Weight for the objective component (default 0.5).

    Returns:
        A dict with keys:
        - ``"subjective_avg"``  — simple average of subjective scores
        - ``"objective_avg"``   — simple average of available objective scores
                                  (``None`` when no signals available)
        - ``"composite"``       — weighted blend of the two averages
        - ``"grade"``           — letter grade string (``"A+"`` … ``"D"``)

    Examples::

        >>> r = compute_composite({"品牌": 4.0, "网络效应": 3.0}, {})
        >>> r["subjective_avg"]
        3.5
    """
    sub_vals = list(subjective.values())
    sub_avg = sum(sub_vals) / len(sub_vals) if sub_vals else 0.0

    obj_vals = [v for v in objective.values() if v is not None]
    obj_avg: float | None = sum(obj_vals) / len(obj_vals) if obj_vals else None

    if obj_avg is not None:
        composite = sub_avg * subjective_weight + obj_avg * objective_weight
    else:
        composite = sub_avg

    grade = _to_grade(composite)

    return {
        "subjective_avg": sub_avg,
        "objective_avg": obj_avg,
        "composite": composite,
        "grade": grade,
    }


def _to_grade(score: float) -> str:
    """Map a 0-5 composite score to a letter grade."""
    if score >= 4.5:
        return "A+"
    if score >= 4.0:
        return "A"
    if score >= 3.5:
        return "B+"
    if score >= 3.0:
        return "B"
    if score >= 2.5:
        return "C+"
    if score >= 2.0:
        return "C"
    return "D"
