"""Rebalancing strategy simulation engine.

This module contains all *pure* computation logic extracted from
``pages/17_资产再平衡模拟器.py``.  It has no Streamlit dependency and is
therefore fully unit-testable.

Public API
----------
- :func:`generate_monthly_returns`  — Monte-Carlo log-normal return matrix
- :func:`simulate_strategy`         — run one rebalancing strategy
- :func:`run_all_strategies`        — convenience wrapper for all strategies
"""
from __future__ import annotations

from typing import Any

import numpy as np


# ── Type aliases ──────────────────────────────────────────

SimResult = dict[str, Any]
"""Result dict returned by :func:`simulate_strategy`."""


# ── Return generation ─────────────────────────────────────

def generate_monthly_returns(
    expected_annual_returns: list[float],
    annual_volatilities: list[float],
    n_months: int,
    *,
    seed: int = 42,
) -> np.ndarray:
    """Generate a matrix of monthly log-normal returns.

    Args:
        expected_annual_returns: List of annualised expected returns (as
                                 decimals, e.g. ``0.10`` for 10 %).
        annual_volatilities:     List of annualised volatilities (same length).
        n_months:                Number of monthly periods to simulate.
        seed:                    Random seed for reproducibility.

    Returns:
        NumPy array of shape ``(n_months, n_assets)`` containing monthly
        arithmetic returns (i.e. ``exp(log_return) - 1``).

    Examples::

        >>> r = generate_monthly_returns([0.10], [0.20], 12)
        >>> r.shape
        (12, 1)
    """
    n_assets = len(expected_annual_returns)
    rng = np.random.default_rng(seed)
    mu_m = [np.log(1 + r) / 12 for r in expected_annual_returns]
    sig_m = [v / np.sqrt(12) for v in annual_volatilities]
    monthly = np.zeros((n_months, n_assets))
    for i in range(n_assets):
        monthly[:, i] = np.exp(rng.normal(mu_m[i], sig_m[i], n_months)) - 1
    return monthly


# ── Strategy simulation ───────────────────────────────────

def simulate_strategy(
    strategy: str,
    *,
    initial_value: float,
    target_weights: list[float],
    monthly_returns: np.ndarray,
    rebal_fee_pct: float = 0.1,
    threshold_pct: float = 5.0,
    track_weights: bool = False,
) -> tuple[list[float], int, float, list[list[float]] | None]:
    """Simulate a single rebalancing strategy over a monthly return matrix.

    Args:
        strategy:        One of ``"buy_and_hold"``, ``"annually"``,
                         ``"quarterly"``, ``"monthly"``, ``"threshold"``.
        initial_value:   Starting portfolio value.
        target_weights:  Target allocation weights (must sum to 1.0).
        monthly_returns: Return matrix of shape ``(n_months, n_assets)``
                         as produced by :func:`generate_monthly_returns`.
        rebal_fee_pct:   Transaction cost per rebalancing event as a
                         percentage of portfolio value (default 0.1 %).
        threshold_pct:   Drift threshold (in percentage points) that triggers
                         a rebalancing event when ``strategy="threshold"``.
        track_weights:   When ``True``, record the weight vector after each
                         month.

    Returns:
        A 4-tuple of:
        - ``portfolio_values`` — list of end-of-month portfolio values
          (length ``n_months + 1``, first element is *initial_value*).
        - ``rebal_count``      — number of rebalancing events executed.
        - ``total_fees``       — cumulative fees paid.
        - ``weight_history``   — list of weight vectors (or ``None`` when
          *track_weights* is ``False``).

    Examples::

        >>> import numpy as np
        >>> r = generate_monthly_returns([0.10], [0.20], 12)
        >>> vals, cnt, fees, _ = simulate_strategy(
        ...     "buy_and_hold",
        ...     initial_value=100_000,
        ...     target_weights=[1.0],
        ...     monthly_returns=r,
        ... )
        >>> len(vals)
        13
    """
    n_months, n_assets = monthly_returns.shape
    allocations = np.array([initial_value * w for w in target_weights])
    portfolio_values: list[float] = [initial_value]
    rebal_count = 0
    total_fees = 0.0
    weight_history: list[list[float]] | None = [] if track_weights else None

    for m in range(n_months):
        # Apply monthly returns
        for i in range(n_assets):
            allocations[i] *= 1 + monthly_returns[m, i]
        total = float(allocations.sum())

        # Determine whether to rebalance
        should_rebal = False
        if strategy == "monthly":
            should_rebal = True
        elif strategy == "quarterly" and (m + 1) % 3 == 0:
            should_rebal = True
        elif strategy == "annually" and (m + 1) % 12 == 0:
            should_rebal = True
        elif strategy == "threshold":
            if total > 0:
                current_weights = allocations / total
                max_drift = max(
                    abs(current_weights[i] - target_weights[i])
                    for i in range(n_assets)
                )
                if max_drift >= threshold_pct / 100:
                    should_rebal = True

        if should_rebal and strategy != "buy_and_hold":
            fee = total * rebal_fee_pct / 100
            total -= fee
            total_fees += fee
            allocations = np.array([total * w for w in target_weights])
            rebal_count += 1

        portfolio_values.append(float(allocations.sum()))

        if track_weights:
            t = float(allocations.sum())
            weight_history.append(  # type: ignore[union-attr]
                (allocations / t).tolist() if t > 0 else list(target_weights)
            )

    return portfolio_values, rebal_count, total_fees, weight_history


# ── Convenience wrapper ───────────────────────────────────

_STRATEGY_LABELS: dict[str, str] = {
    "buy_and_hold": "📦 买入持有",
    "annually":     "📅 年度再平衡",
    "quarterly":    "📅 季度再平衡",
    "monthly":      "📅 月度再平衡",
    "threshold":    "🎯 阈值再平衡",
}


def run_all_strategies(
    *,
    initial_value: float,
    target_weights: list[float],
    monthly_returns: np.ndarray,
    years: int,
    rebal_fee_pct: float = 0.1,
    threshold_pct: float = 5.0,
) -> dict[str, SimResult]:
    """Run all five strategies and return a dict of result dicts.

    Each result dict contains:
    - ``"label"``        — human-readable strategy name
    - ``"values"``       — list of monthly portfolio values
    - ``"rebal_count"``  — number of rebalancing events
    - ``"total_fees"``   — cumulative fees paid
    - ``"final"``        — final portfolio value
    - ``"total_return"`` — total return in percent
    - ``"ann_return"``   — annualised return in percent

    Args:
        initial_value:   Starting portfolio value.
        target_weights:  Target allocation weights.
        monthly_returns: Monthly return matrix.
        years:           Investment horizon in years (used for annualisation).
        rebal_fee_pct:   Transaction cost per rebalancing event (%).
        threshold_pct:   Drift threshold for threshold strategy (%).

    Returns:
        Dict mapping strategy key → result dict.
    """
    results: dict[str, SimResult] = {}
    for key in _STRATEGY_LABELS:
        values, count, fees, _ = simulate_strategy(
            key,
            initial_value=initial_value,
            target_weights=target_weights,
            monthly_returns=monthly_returns,
            rebal_fee_pct=rebal_fee_pct,
            threshold_pct=threshold_pct,
        )
        final = values[-1]
        total_return = (final / initial_value - 1) * 100
        ann_return = ((final / initial_value) ** (1 / years) - 1) * 100 if years > 0 else 0.0
        label = _STRATEGY_LABELS[key]
        if key == "threshold":
            label = f"🎯 阈值再平衡 (±{threshold_pct:.0f}%)"
        results[key] = {
            "label": label,
            "values": values,
            "rebal_count": count,
            "total_fees": fees,
            "final": final,
            "total_return": total_return,
            "ann_return": ann_return,
        }
    return results
