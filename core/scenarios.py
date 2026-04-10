"""Scenario comparison engine for cross-tool what-if analysis.

Provides a unified framework to run the same parameter variation across
multiple financial tools simultaneously and compare outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.compound import compute_schedule
from core.retirement import calculate_retirement
from core.savings import calculate_savings_goal


@dataclass
class ScenarioResult:
    """Result of a multi-tool scenario comparison."""
    parameter_name: str
    values: list[float]
    compound_finals: list[float]
    savings_months: list[int]
    retirement_gaps: list[float]
    summary: pd.DataFrame


def run_inflation_scenarios(
    inflation_values: list[float],
    # Compound params
    compound_principal: float = 100000,
    compound_rate: float = 6.0,
    compound_years: int = 20,
    # Savings params
    savings_current: float = 50000,
    savings_goal: float = 1000000,
    savings_rate: float = 6.0,
    savings_deposit: float = 10000,
    # Retirement params
    current_age: int = 35,
    retire_age: int = 65,
    life_expectancy: int = 85,
    current_assets: float = 500000,
    monthly_saving: float = 10000,
    monthly_expense: float = 30000,
    pre_return: float = 7.0,
    post_return: float = 4.0,
) -> ScenarioResult:
    """Run inflation sensitivity analysis across compound, savings, and retirement.

    Args:
        inflation_values: List of inflation rates (%) to test.
        Other params: Default parameters for each tool.

    Returns:
        ScenarioResult with cross-tool comparison.
    """
    compound_finals = []
    savings_months_list = []
    retirement_gaps = []

    for inf in inflation_values:
        # Compound: real purchasing power
        sched = compute_schedule(
            principal=compound_principal, annual_rate_pct=compound_rate,
            years=compound_years, compound_freq=12, inflation_pct=inf,
        )
        if "实际购买力" in sched.columns:
            compound_finals.append(sched.iloc[-1]["实际购买力"])
        else:
            compound_finals.append(sched.iloc[-1]["年末余额"])

        # Savings: effective real rate = nominal - inflation
        real_rate = max(0.1, savings_rate - inf)
        sr = calculate_savings_goal(
            current=savings_current, goal=savings_goal,
            annual_rate_pct=real_rate, monthly_deposit=savings_deposit,
        )
        savings_months_list.append(sr.months_needed)

        # Retirement: gap under different inflation
        rr = calculate_retirement(
            current_age=current_age, retire_age=retire_age,
            life_expectancy=life_expectancy, current_assets=current_assets,
            monthly_saving=monthly_saving, monthly_expense_today=monthly_expense,
            inflation_pct=inf, pre_return_pct=pre_return, post_return_pct=post_return,
        )
        retirement_gaps.append(rr.gap)

    rows = []
    for i, inf in enumerate(inflation_values):
        rows.append({
            "通胀率(%)": inf,
            "复利实际终值": compound_finals[i],
            "储蓄达成月数": savings_months_list[i],
            "退休缺口": retirement_gaps[i],
        })

    return ScenarioResult(
        parameter_name="通胀率(%)",
        values=inflation_values,
        compound_finals=compound_finals,
        savings_months=savings_months_list,
        retirement_gaps=retirement_gaps,
        summary=pd.DataFrame(rows),
    )


def run_return_scenarios(
    return_values: list[float],
    compound_principal: float = 100000,
    compound_years: int = 20,
    savings_current: float = 50000,
    savings_goal: float = 1000000,
    savings_deposit: float = 10000,
    current_age: int = 35,
    retire_age: int = 65,
    life_expectancy: int = 85,
    current_assets: float = 500000,
    monthly_saving: float = 10000,
    monthly_expense: float = 30000,
    inflation: float = 2.5,
) -> ScenarioResult:
    """Run return rate sensitivity across tools."""
    compound_finals = []
    savings_months_list = []
    retirement_gaps = []

    for ret in return_values:
        sched = compute_schedule(
            principal=compound_principal, annual_rate_pct=ret,
            years=compound_years, compound_freq=12,
        )
        compound_finals.append(sched.iloc[-1]["年末余额"])

        sr = calculate_savings_goal(
            current=savings_current, goal=savings_goal,
            annual_rate_pct=ret, monthly_deposit=savings_deposit,
        )
        savings_months_list.append(sr.months_needed)

        post_ret = max(1.0, ret - 3.0)
        rr = calculate_retirement(
            current_age=current_age, retire_age=retire_age,
            life_expectancy=life_expectancy, current_assets=current_assets,
            monthly_saving=monthly_saving, monthly_expense_today=monthly_expense,
            inflation_pct=inflation, pre_return_pct=ret, post_return_pct=post_ret,
        )
        retirement_gaps.append(rr.gap)

    rows = []
    for i, ret in enumerate(return_values):
        rows.append({
            "收益率(%)": ret,
            "复利终值": compound_finals[i],
            "储蓄达成月数": savings_months_list[i],
            "退休缺口": retirement_gaps[i],
        })

    return ScenarioResult(
        parameter_name="收益率(%)",
        values=return_values,
        compound_finals=compound_finals,
        savings_months=savings_months_list,
        retirement_gaps=retirement_gaps,
        summary=pd.DataFrame(rows),
    )
