"""Shared planning/business logic for loan and budget tools."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BudgetPlan:
    amt_needs: float
    amt_wants: float
    amt_save: float
    pct_save: int
    remaining_needs: float
    fixed_pct: float


def calculate_budget(income: float, fixed_expense: float, pct_needs: int, pct_wants: int) -> BudgetPlan:
    """Calculate 50/30/20-style budget allocation with custom ratios."""
    pct_save = max(0, 100 - pct_needs - pct_wants)
    amt_needs = income * pct_needs / 100
    amt_wants = income * pct_wants / 100
    amt_save = income * pct_save / 100
    remaining_needs = max(0.0, amt_needs - fixed_expense)
    fixed_pct = (fixed_expense / income * 100) if income > 0 else 0.0
    return BudgetPlan(
        amt_needs=amt_needs,
        amt_wants=amt_wants,
        amt_save=amt_save,
        pct_save=pct_save,
        remaining_needs=remaining_needs,
        fixed_pct=fixed_pct,
    )


def solve_irr(cash_flows: list[float], tol: float = 1e-10, max_iter: int = 1000) -> float:
    """Solve IRR via Newton iteration."""
    rate = 0.005
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if abs(dnpv) < 1e-14:
            break
        rate_new = rate - npv / dnpv
        if abs(rate_new - rate) < tol:
            return rate_new
        rate = rate_new
    return rate


def calculate_loan(
    principal: float,
    annual_rate_pct: float,
    years: int,
    periods_per_year: int,
    method: str,
) -> tuple[pd.DataFrame, dict]:
    """Calculate amortization schedule and summary metrics."""
    n = years * periods_per_year
    r_period = (annual_rate_pct / 100.0) / periods_per_year

    rows: list[dict] = []
    balance = principal

    if method == "等额本息":
        if r_period == 0:
            payment = principal / n
        else:
            payment = principal * r_period * (1 + r_period) ** n / ((1 + r_period) ** n - 1)

        for i in range(1, n + 1):
            interest = balance * r_period
            principal_part = payment - interest
            if i == n:
                principal_part = balance
                payment = principal_part + interest
            balance -= principal_part
            if balance < 0:
                balance = 0.0
            rows.append({"期数": i, "每期还款": payment, "本金": principal_part, "利息": interest, "剩余本金": balance})
    else:
        principal_fixed = principal / n
        for i in range(1, n + 1):
            interest = balance * r_period
            pmt = principal_fixed + interest
            if i == n:
                principal_fixed = balance
                pmt = principal_fixed + interest
            balance -= principal_fixed
            if balance < 0:
                balance = 0.0
            rows.append({"期数": i, "每期还款": pmt, "本金": principal_fixed, "利息": interest, "剩余本金": balance})

    df = pd.DataFrame(rows)
    total_payment = df["每期还款"].sum()
    total_interest = df["利息"].sum()

    cash_flows = [-principal] + df["每期还款"].tolist()
    try:
        irr = np.irr(cash_flows) if hasattr(np, "irr") else np.nan
    except Exception:
        irr = np.nan
    if np.isnan(irr):
        irr = solve_irr(cash_flows)
    apr = irr * periods_per_year * 100 if not np.isnan(irr) else annual_rate_pct

    summary = {
        "首期还款": df["每期还款"].iloc[0],
        "末期还款": df["每期还款"].iloc[-1],
        "总还款": total_payment,
        "总利息": total_interest,
        "APR(%)": apr,
    }
    return df, summary
