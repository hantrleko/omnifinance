"""Education fund planning core logic.

Simulates monthly compound growth targeted at a future education expense,
accounting for education-specific inflation rates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class EducationFundResult:
    """Result of an education fund simulation."""
    child_current_age: int
    target_age: int
    years_to_goal: int
    future_cost: float           # Education cost at target year (inflation-adjusted)
    projected_fund: float        # Projected fund value at target year
    gap: float                   # Shortfall (positive = insufficient)
    monthly_needed: float        # Monthly saving needed to close gap
    schedule: pd.DataFrame       # Year-by-year path
    scholarship_scenarios: pd.DataFrame  # Scholarship offset analysis


def calculate_education_fund(
    child_age: int,
    target_age: int,
    current_cost: float,
    education_inflation_pct: float,
    current_savings: float,
    monthly_saving: float,
    annual_return_pct: float,
    scholarship_pcts: list[float] | None = None,
) -> EducationFundResult:
    """Simulate education fund accumulation.

    Args:
        child_age: Current age of the child.
        target_age: Age when education expense starts (e.g. 18).
        current_cost: Current annual cost of education (today's money).
        education_inflation_pct: Annual education cost inflation (%).
        current_savings: Existing savings earmarked for education.
        monthly_saving: Monthly contribution to education fund.
        annual_return_pct: Expected annual investment return (%).
        scholarship_pcts: List of scholarship percentages to analyze.

    Returns:
        EducationFundResult with projections and analysis.
    """
    if scholarship_pcts is None:
        scholarship_pcts = [0, 25, 50, 75, 100]

    years = target_age - child_age
    if years <= 0:
        years = 1

    edu_inf = education_inflation_pct / 100
    r_annual = annual_return_pct / 100
    r_monthly = (1 + r_annual) ** (1 / 12) - 1

    # Future cost of education (4 years of university)
    future_annual_cost = current_cost * (1 + edu_inf) ** years
    future_total_cost = future_annual_cost * 4  # Assume 4-year program

    # Simulate monthly accumulation
    balance = current_savings
    rows: list[dict[str, Any]] = []
    rows.append({
        "年份": 0,
        "孩子年龄": child_age,
        "年初余额": balance,
        "当年投入": 0.0,
        "当年收益": 0.0,
        "年末余额": balance,
        "目标值": future_total_cost / (1 + edu_inf) ** years,
    })

    for yr in range(1, years + 1):
        start = balance
        yearly_contribution = 0.0
        yearly_interest = 0.0
        for _ in range(12):
            interest = balance * r_monthly
            balance += interest + monthly_saving
            yearly_interest += interest
            yearly_contribution += monthly_saving

        # Target value at this point (linearly interpolated)
        target_at_yr = future_total_cost * yr / years

        rows.append({
            "年份": yr,
            "孩子年龄": child_age + yr,
            "年初余额": start,
            "当年投入": yearly_contribution,
            "当年收益": yearly_interest,
            "年末余额": balance,
            "目标值": target_at_yr,
        })

    projected = balance
    gap = future_total_cost - projected

    # Calculate monthly saving needed to close gap
    if gap <= 0:
        monthly_needed = 0.0
    else:
        n_months = years * 12
        if r_monthly > 0:
            fv_factor = ((1 + r_monthly) ** n_months - 1) / r_monthly
            monthly_needed = gap / fv_factor if fv_factor > 0 else gap / max(n_months, 1)
        else:
            monthly_needed = gap / max(n_months, 1)

    # Scholarship scenarios
    scholarship_rows = []
    for pct in scholarship_pcts:
        effective_cost = future_total_cost * (1 - pct / 100)
        sc_gap = effective_cost - projected
        scholarship_rows.append({
            "奖学金比例": f"{pct}%",
            "实际费用": effective_cost,
            "资金缺口": max(0, sc_gap),
            "状态": "✅ 充足" if sc_gap <= 0 else "⚠️ 不足",
        })

    return EducationFundResult(
        child_current_age=child_age,
        target_age=target_age,
        years_to_goal=years,
        future_cost=future_total_cost,
        projected_fund=projected,
        gap=gap,
        monthly_needed=monthly_needed,
        schedule=pd.DataFrame(rows),
        scholarship_scenarios=pd.DataFrame(scholarship_rows),
    )
