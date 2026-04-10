"""Debt payoff strategies: Snowball, Avalanche, and Hybrid.

Provides simulation for multiple debts with minimum payments, extra budget
allocation, and strategy comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class DebtItem:
    """A single debt obligation."""
    name: str
    balance: float
    rate_pct: float       # Annual interest rate in %
    min_payment: float    # Minimum monthly payment


@dataclass
class DebtPayoffResult:
    """Result of a debt payoff simulation."""
    strategy: str
    months_to_payoff: int
    total_interest: float
    total_paid: float
    schedule: pd.DataFrame        # Monthly detail
    per_debt_summary: pd.DataFrame  # Per-debt payoff summary


def simulate_payoff(
    debts: list[DebtItem],
    extra_monthly: float,
    strategy: str = "avalanche",
    max_months: int = 600,
) -> DebtPayoffResult:
    """Simulate debt payoff using a given strategy.

    Args:
        debts: List of DebtItem objects.
        extra_monthly: Extra cash available above all minimum payments.
        strategy: ``"avalanche"`` (highest rate first), ``"snowball"``
            (smallest balance first), or ``"hybrid"`` (highest rate among
            debts below the median balance).
        max_months: Maximum months to simulate.

    Returns:
        DebtPayoffResult with full schedule and summary.
    """
    # Deep copy balances
    balances = [d.balance for d in debts]
    names = [d.name for d in debts]
    rates_m = [d.rate_pct / 100 / 12 for d in debts]
    mins = [d.min_payment for d in debts]

    rows: list[dict[str, Any]] = []
    interest_paid = [0.0] * len(debts)
    payoff_months = [0] * len(debts)
    total_months = 0

    for month in range(1, max_months + 1):
        if all(b <= 0.01 for b in balances):
            break
        total_months = month

        # Calculate interest
        month_interest = [balances[i] * rates_m[i] if balances[i] > 0 else 0.0 for i in range(len(debts))]

        # Apply interest
        for i in range(len(debts)):
            balances[i] += month_interest[i]
            interest_paid[i] += month_interest[i]

        # Pay minimums first
        payments = [0.0] * len(debts)
        for i in range(len(debts)):
            if balances[i] <= 0.01:
                continue
            pay = min(mins[i], balances[i])
            payments[i] = pay
            balances[i] -= pay

        # Allocate extra to target debt based on strategy
        extra_left = extra_monthly
        # Add freed-up minimums from paid-off debts
        for i in range(len(debts)):
            if balances[i] <= 0.01 and payoff_months[i] > 0:
                pass  # already counted

        # Determine priority order
        active = [(i, balances[i], debts[i].rate_pct) for i in range(len(debts)) if balances[i] > 0.01]

        if strategy == "avalanche":
            active.sort(key=lambda x: -x[2])  # Highest rate first
        elif strategy == "snowball":
            active.sort(key=lambda x: x[1])   # Smallest balance first
        else:  # hybrid
            if active:
                median_bal = sorted([a[1] for a in active])[len(active) // 2]
                below_median = [a for a in active if a[1] <= median_bal]
                above_median = [a for a in active if a[1] > median_bal]
                below_median.sort(key=lambda x: -x[2])
                above_median.sort(key=lambda x: -x[2])
                active = below_median + above_median

        for idx, _, _ in active:
            if extra_left <= 0:
                break
            pay = min(extra_left, balances[idx])
            payments[idx] += pay
            balances[idx] -= pay
            extra_left -= pay

        # Record payoff months
        for i in range(len(debts)):
            if balances[i] <= 0.01 and payoff_months[i] == 0 and debts[i].balance > 0:
                payoff_months[i] = month

        row: dict[str, Any] = {"月份": month, "总余额": sum(balances)}
        for i in range(len(debts)):
            row[f"{names[i]}_还款"] = payments[i]
            row[f"{names[i]}_余额"] = max(0, balances[i])
        rows.append(row)

    schedule = pd.DataFrame(rows)
    total_interest_sum = sum(interest_paid)
    total_paid_sum = sum(d.balance for d in debts) + total_interest_sum

    # Per-debt summary
    summary_rows = []
    for i in range(len(debts)):
        summary_rows.append({
            "债务名称": names[i],
            "初始余额": debts[i].balance,
            "年利率(%)": debts[i].rate_pct,
            "还清月数": payoff_months[i] if payoff_months[i] > 0 else total_months,
            "累计利息": interest_paid[i],
        })

    return DebtPayoffResult(
        strategy=strategy,
        months_to_payoff=total_months,
        total_interest=total_interest_sum,
        total_paid=total_paid_sum,
        schedule=schedule,
        per_debt_summary=pd.DataFrame(summary_rows),
    )


def compare_strategies(
    debts: list[DebtItem],
    extra_monthly: float,
) -> dict[str, DebtPayoffResult]:
    """Run all three strategies and return results keyed by strategy name."""
    results = {}
    for s in ("avalanche", "snowball", "hybrid"):
        results[s] = simulate_payoff(debts, extra_monthly, strategy=s)
    return results
