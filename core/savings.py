"""Savings goal calculator core logic — monthly compound simulation."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


@dataclass
class SavingsResult:
    reached: bool           # Whether goal is already reached or achievable
    months_needed: int      # Months to reach goal (0=already reached, -1=never)
    schedule: pd.DataFrame  # Monthly detail
    yearly: pd.DataFrame    # Annual summary
    total_deposited: float  # Total principal contributed (including initial)
    total_interest: float   # Total compound interest earned


def calculate_savings_goal(
    current: float,
    goal: float,
    annual_rate_pct: float,
    monthly_deposit: float,
    max_months: int = 1200,  # Simulate up to 100 years
) -> SavingsResult:
    """Monthly compound simulation for savings goal.

    Args:
        current: Current savings balance.
        goal: Target savings amount.
        annual_rate_pct: Expected annual return rate (%).
        monthly_deposit: Fixed monthly contribution.
        max_months: Maximum months to simulate (default 1200 = 100 years).

    Returns:
        SavingsResult with full schedule and summary metrics.
    """
    # Goal already reached
    if current >= goal:
        empty = pd.DataFrame()
        return SavingsResult(
            reached=True, months_needed=0,
            schedule=empty, yearly=empty,
            total_deposited=current, total_interest=0.0,
        )

    monthly_rate = (annual_rate_pct / 100.0) / 12
    balance = current
    total_deposited = current
    months_needed = -1

    rows: list[dict] = []

    for m in range(1, max_months + 1):
        interest = balance * monthly_rate
        balance += interest + monthly_deposit
        total_deposited += monthly_deposit

        no_return_balance = current + monthly_deposit * m

        rows.append({
            "月数": m,
            "余额": balance,
            "当月利息": interest,
            "当月投入": monthly_deposit,
            "纯储蓄余额": no_return_balance,
        })

        if balance >= goal and months_needed == -1:
            months_needed = m

        # Simulate 12 more months after reaching goal for chart context
        if months_needed != -1 and m >= months_needed + 12:
            break

    schedule = pd.DataFrame(rows)

    # Annual summary
    yearly_rows: list[dict] = []
    yr_balance = current
    yr_interest_total = 0.0
    yr_deposit_total = 0.0

    for _, row in schedule.iterrows():
        yr_interest_total += row["当月利息"]
        yr_deposit_total += row["当月投入"]

        if row["月数"] % 12 == 0 or row["月数"] == len(schedule):
            year_num = math.ceil(row["月数"] / 12)
            yearly_rows.append({
                "年份": year_num,
                "年初余额": yr_balance,
                "当年利息": yr_interest_total,
                "当年投入": yr_deposit_total,
                "年末余额": row["余额"],
            })
            yr_balance = row["余额"]
            yr_interest_total = 0.0
            yr_deposit_total = 0.0

    yearly = pd.DataFrame(yearly_rows)

    # Compute metrics at the exact month of reaching goal
    total_interest = 0.0
    if months_needed > 0 and not schedule.empty:
        goal_rows = schedule[schedule["月数"] == months_needed]
        if not goal_rows.empty:
            deposited_at_goal = current + monthly_deposit * months_needed
            interest_at_goal = goal_rows.iloc[0]["余额"] - deposited_at_goal
            total_deposited = deposited_at_goal
            total_interest = interest_at_goal

    return SavingsResult(
        reached=(months_needed >= 0),
        months_needed=months_needed,
        schedule=schedule,
        yearly=yearly,
        total_deposited=total_deposited,
        total_interest=total_interest,
    )
