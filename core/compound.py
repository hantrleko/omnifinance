"""Core finance functions for compound interest calculations."""

from __future__ import annotations

from typing import Any

import pandas as pd


def compute_schedule(
    principal: float,
    annual_rate_pct: float,
    years: int,
    compound_freq: int,
    contribution: float = 0.0,
    contrib_freq: int = 12,
    inflation_pct: float = 0.0,
) -> pd.DataFrame:
    """Compute a year-by-year compound-interest schedule.

    Args:
        principal: Initial lump-sum investment amount.
        annual_rate_pct: Annual interest rate in percent (e.g. ``6.0`` for 6%).
        years: Total number of years to simulate.
        compound_freq: Number of compounding periods per year
            (e.g. ``12`` for monthly, ``1`` for annual).
        contribution: Periodic contribution amount added at each
            *contrib_freq* interval (default ``0.0``).
        contrib_freq: Number of contribution payments per year
            (default ``12`` for monthly).
        inflation_pct: Annual inflation rate in percent (default ``0.0``).
            When non-zero, an additional ``实际购买力`` column is appended.

    Returns:
        A :class:`pandas.DataFrame` with one row per year (year 0 through
        *years*) and columns: ``年份``, ``年初余额``, ``当年投入``,
        ``当年利息``, ``年末余额``, ``累计投入``, and optionally ``实际购买力``.
    """
    r: float = annual_rate_pct / 100.0
    rate_per_period: float = r / compound_freq
    inflation: float = inflation_pct / 100.0

    rows: list[dict[str, Any]] = []
    balance = principal
    total_contributions = principal

    for year in range(0, years + 1):
        if year == 0:
            rows.append(
                {
                    "年份": year,
                    "年初余额": balance,
                    "当年投入": 0.0,
                    "当年利息": 0.0,
                    "年末余额": balance,
                    "累计投入": total_contributions,
                    "实际购买力": balance,
                }
            )
            continue

        start_balance = balance
        interest_year = 0.0
        yearly_contribution = 0.0

        for period in range(1, compound_freq + 1):
            interest = balance * rate_per_period
            balance += interest
            interest_year += interest

            if contribution > 0 and compound_freq > 0:
                periods_per_contrib = compound_freq / contrib_freq
                if periods_per_contrib >= 1:
                    if period % max(1, round(periods_per_contrib)) == 0:
                        balance += contribution
                        yearly_contribution += contribution
                else:
                    contribs_this_period = round(contrib_freq / compound_freq)
                    balance += contribution * contribs_this_period
                    yearly_contribution += contribution * contribs_this_period

        total_contributions += yearly_contribution

        real_purchasing_power = balance / ((1 + inflation) ** year) if inflation > 0 else balance
        rows.append(
            {
                "年份": year,
                "年初余额": start_balance,
                "当年投入": yearly_contribution,
                "当年利息": interest_year,
                "年末余额": balance,
                "累计投入": total_contributions,
                "实际购买力": real_purchasing_power,
            }
        )

    if inflation == 0.0:
        df = pd.DataFrame(rows)
        df.drop(columns=["实际购买力"], inplace=True)
        return df
    return pd.DataFrame(rows)


def add_annualized_return(schedule: pd.DataFrame) -> pd.DataFrame:
    """Append an annualised-return column to a compound schedule DataFrame.

    Args:
        schedule: A DataFrame previously returned by :func:`compute_schedule`.

    Returns:
        A copy of *schedule* with an additional ``年化收益率(%)`` column.
    """
    schedule = schedule.copy()
    schedule["年化收益率(%)"] = 0.0
    for i in range(1, len(schedule)):
        begin = schedule.loc[i, "年初余额"] + schedule.loc[i, "当年投入"]
        if begin > 0:
            schedule.loc[i, "年化收益率(%)"] = (
                schedule.loc[i, "年末余额"] / begin - 1
            ) * 100
    return schedule
