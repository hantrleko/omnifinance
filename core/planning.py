"""Shared planning/business logic for loan and budget tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TypedDict

import numpy as np
import pandas as pd


# ── Dataclass / TypedDict definitions ───────────────────────

@dataclass
class BudgetPlan:
    """Result of a 50/30/20-style budget allocation calculation."""

    amt_needs: float       # Absolute amount allocated to needs
    amt_wants: float       # Absolute amount allocated to wants
    amt_save: float        # Absolute amount allocated to savings
    pct_save: int          # Savings percentage (derived)
    remaining_needs: float # Needs budget remaining after fixed expenses
    fixed_pct: float       # Fixed expense as a percentage of income


class LoanSummary(TypedDict):
    """Summary metrics returned alongside the amortisation schedule."""

    首期还款: float
    末期还款: float
    总还款: float
    总利息: float
    APR: float  # key stored as "APR(%)"
    总提前还款: float
    实际期数: int


# ── Business logic ─────────────────────────────────────

def calculate_budget(income: float, fixed_expense: float, pct_needs: int, pct_wants: int) -> BudgetPlan:
    """Calculate 50/30/20-style budget allocation with custom ratios.

    Args:
        income: Gross monthly income.
        fixed_expense: Fixed monthly expenses already committed (e.g. rent).
        pct_needs: Percentage of income allocated to needs.
        pct_wants: Percentage of income allocated to wants.

    Returns:
        A :class:`BudgetPlan` dataclass with all computed allocation values.
    """
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
    """Solve for the Internal Rate of Return (IRR) via Newton-Raphson iteration.

    Args:
        cash_flows: Sequence of periodic cash flows where index 0 is the
            initial outflow (negative) and subsequent values are inflows.
        tol: Convergence tolerance for the rate change between iterations
            (default ``1e-10``).
        max_iter: Maximum number of Newton iterations (default ``1000``).

    Returns:
        The periodic IRR as a decimal (e.g. ``0.005`` for 0.5% per period).
        Returns the last computed estimate if convergence is not reached.
    """
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
    extra_payment_period: Optional[int] = None,
    extra_payment_amount: float = 0.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Calculate a loan amortisation schedule and summary metrics.

    Args:
        principal: Original loan principal amount.
        annual_rate_pct: Annual nominal interest rate in percent.
        years: Loan term in years.
        periods_per_year: Number of payment periods per year
            (e.g. ``12`` for monthly, ``1`` for annual).
        method: Repayment method; either ``"等额本息"`` (equal total payment)
            or ``"等额本金"`` (equal principal payment).
        extra_payment_period: Period number (1-indexed) at which an additional
            lump-sum payment is made. ``None`` means no extra payment.
        extra_payment_amount: Size of the extra lump-sum payment (default ``0.0``).

    Returns:
        A tuple of:
        - ``schedule``: :class:`pandas.DataFrame` with one row per payment period
          and columns ``期数``, ``每期还款``, ``本金``, ``利息``, ``提前还款``, ``剩余本金``.
        - ``summary``: dict with keys ``首期还款``, ``末期还款``, ``总还款``,
          ``总利息``, ``APR(%)``, ``总提前还款``, ``实际期数``.
    """
    n: int = years * periods_per_year
    r_period: float = (annual_rate_pct / 100.0) / periods_per_year

    rows: list[dict[str, Any]] = []
    balance = principal

    def calc_equal_payment(curr_balance: float, remain_n: int) -> float:  # noqa: ANN202
        if remain_n <= 0:
            return 0.0
        if r_period == 0:
            return curr_balance / remain_n
        return curr_balance * r_period * (1 + r_period) ** remain_n / ((1 + r_period) ** remain_n - 1)

    payment = calc_equal_payment(principal, n) if method == "等额本息" else 0.0
    principal_fixed = principal / n if method == "等额本金" else 0.0

    for i in range(1, n + 1):
        if balance <= 1e-10:
            break

        interest = balance * r_period
        extra = 0.0

        if method == "等额本息":
            principal_part = payment - interest
            if principal_part < 0:
                principal_part = 0.0
            if i == n:
                principal_part = balance
                payment = principal_part + interest
        else:
            principal_part = principal_fixed
            if principal_part > balance:
                principal_part = balance
            payment = principal_part + interest

        if extra_payment_period is not None and i == extra_payment_period and extra_payment_amount > 0:
            extra = min(extra_payment_amount, max(0.0, balance - principal_part))

        total_principal_paid = principal_part + extra
        if total_principal_paid > balance:
            total_principal_paid = balance
            principal_part = balance - extra if extra <= balance else 0.0
            if principal_part < 0:
                principal_part = 0.0
                extra = balance

        payment_actual = interest + total_principal_paid
        balance -= total_principal_paid
        if balance < 0:
            balance = 0.0

        rows.append(
            {
                "期数": i,
                "每期还款": payment_actual,
                "本金": principal_part,
                "利息": interest,
                "提前还款": extra,
                "剩余本金": balance,
            }
        )

        if method == "等额本息" and balance > 0:
            remain_n = n - i
            payment = calc_equal_payment(balance, remain_n)

    df = pd.DataFrame(rows)
    total_payment = df["每期还款"].sum()
    total_interest = df["利息"].sum()

    cash_flows = [-principal] + df["每期还款"].tolist()
    irr = solve_irr(cash_flows)
    apr = irr * periods_per_year * 100

    summary = {
        "首期还款": df["每期还款"].iloc[0],
        "末期还款": df["每期还款"].iloc[-1],
        "总还款": total_payment,
        "总利息": total_interest,
        "APR(%)": apr,
        "总提前还款": df["提前还款"].sum(),
        "实际期数": int(len(df)),
    }
    return df, summary
