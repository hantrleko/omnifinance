"""Retirement planning core logic — dual-phase model.

Phase 1: Accumulation (pre-retirement compound growth with monthly saving)
Phase 2: Drawdown (post-retirement withdrawals adjusted for inflation)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RetirementResult:
    """Aggregated result of a dual-phase retirement calculation."""

    # Key scalars
    years_to_retire: int
    years_in_retire: int
    future_monthly_expense: float    # Inflation-adjusted monthly expense at retirement
    total_needed_at_retire: float    # Total assets needed at retirement (annuity PV)
    projected_at_retire: float       # Projected assets under current plan
    gap: float                       # Shortfall (positive = insufficient)
    extra_monthly_needed: float      # Additional monthly saving required
    # Annual paths
    accumulation_path: pd.DataFrame  # Pre-retirement accumulation
    target_path: pd.DataFrame        # Path required to hit target
    full_path: pd.DataFrame          # Full lifecycle (accumulation + drawdown)


def calculate_retirement(
    current_age: int,
    retire_age: int,
    life_expectancy: int,
    current_assets: float,
    monthly_saving: float,
    monthly_expense_today: float,
    inflation_pct: float,
    pre_return_pct: float,
    post_return_pct: float,
) -> RetirementResult:
    """Dual-phase retirement calculation.

    Args:
        current_age: Current age in years.
        retire_age: Target retirement age.
        life_expectancy: Expected lifespan in years.
        current_assets: Current retirement savings.
        monthly_saving: Monthly contribution before retirement.
        monthly_expense_today: Monthly living expense in today's money.
        inflation_pct: Annual inflation rate (%).
        pre_return_pct: Annual return rate before retirement (%).
        post_return_pct: Annual return rate after retirement (%).

    Returns:
        RetirementResult dataclass with all computed values and paths.
    """
    years_to_retire: int = retire_age - current_age
    years_in_retire: int = life_expectancy - retire_age
    inf: float = inflation_pct / 100
    r_pre_m: float = pre_return_pct / 100 / 12     # Monthly pre-retirement rate
    r_post: float = post_return_pct / 100          # Annual post-retirement rate

    # ── Phase 1: Inflation-adjusted monthly expense at retirement ──
    future_monthly = monthly_expense_today * (1 + inf) ** years_to_retire

    # ── Phase 1: Total assets needed at retirement (annuity PV) ──
    # Real post-retirement rate = (1+nominal) / (1+inflation) - 1
    real_post: float = (1 + r_post) / (1 + inf) - 1
    real_post_m: float = (1 + real_post) ** (1 / 12) - 1   # Monthly real rate
    n_months_retire: int = years_in_retire * 12

    if real_post_m > 0:
        pv_factor = (1 - (1 + real_post_m) ** (-n_months_retire)) / real_post_m
    else:
        pv_factor = n_months_retire

    total_needed = future_monthly * pv_factor

    # ── Phase 1: Accumulation path under current plan ──
    n_months_pre: int = years_to_retire * 12
    balance: float = current_assets
    acc_rows: list[dict[str, float | int | str]] = []

    for yr in range(years_to_retire + 1):
        age = current_age + yr
        if yr == 0:
            acc_rows.append({"年龄": age, "资产": balance, "类型": "当前计划"})
            continue
        for _ in range(12):
            balance = balance * (1 + r_pre_m) + monthly_saving
        acc_rows.append({"年龄": age, "资产": balance, "类型": "当前计划"})

    projected = balance
    gap = total_needed - projected

    # ── Extra monthly saving needed to close the gap ──
    if gap <= 0:
        extra_monthly = 0.0
    else:
        if r_pre_m > 0:
            fv_factor = ((1 + r_pre_m) ** n_months_pre - 1) / r_pre_m
            extra_monthly = gap / fv_factor if fv_factor > 0 else gap / max(n_months_pre, 1)
        else:
            extra_monthly = gap / max(n_months_pre, 1)

    # ── Target path (if extra saving is added) ──
    target_rows: list[dict[str, float | int | str]] = []
    total_monthly_needed = monthly_saving + extra_monthly
    bal_target = current_assets
    for yr in range(years_to_retire + 1):
        age = current_age + yr
        if yr == 0:
            target_rows.append({"年龄": age, "资产": bal_target, "类型": "目标路径"})
            continue
        for _ in range(12):
            bal_target = bal_target * (1 + r_pre_m) + total_monthly_needed
        target_rows.append({"年龄": age, "资产": bal_target, "类型": "目标路径"})

    # ── Phase 2: Drawdown path ──
    full_rows: list[dict[str, float | int | str]] = list(acc_rows)
    bal_post = projected
    r_post_m = (1 + r_post) ** (1 / 12) - 1
    for yr in range(1, years_in_retire + 1):
        age = retire_age + yr
        expense_m = future_monthly * (1 + inf) ** yr
        for _ in range(12):
            bal_post = bal_post * (1 + r_post_m) - expense_m
            if bal_post < 0:
                bal_post = 0
        full_rows.append({"年龄": age, "资产": bal_post, "类型": "当前计划"})

    return RetirementResult(
        years_to_retire=years_to_retire,
        years_in_retire=years_in_retire,
        future_monthly_expense=future_monthly,
        total_needed_at_retire=total_needed,
        projected_at_retire=projected,
        gap=gap,
        extra_monthly_needed=extra_monthly,
        accumulation_path=pd.DataFrame(acc_rows),
        target_path=pd.DataFrame(target_rows),
        full_path=pd.DataFrame(full_rows),
    )
