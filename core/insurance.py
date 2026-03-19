"""Insurance product analytics for protection and savings policies."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.planning import solve_irr


@dataclass
class ProtectionMetrics:
    """Protection-dimension metrics for an insurance plan."""

    total_premium: float               # Total premiums paid over the payment period
    coverage_cost_per_10k: float       # Total premium cost per 10,000 of coverage
    break_even_claim_prob: float       # Probability of claim needed to break even
    inflation_adjusted_coverage: float # Real coverage value discounted for inflation
    alt_investment_value: float        # Terminal value if premiums were invested instead


@dataclass
class SavingsMetrics:
    """Savings-dimension metrics for an insurance plan."""

    irr_pct: float   # Internal rate of return in percent
    net_gain: float  # Maturity benefit minus total premiums paid


@dataclass
class InsuranceResult:
    """Aggregated result returned by :func:`analyze_insurance_plan`."""

    yearly_schedule: pd.DataFrame  # Year-by-year cashflow and value table
    protection: ProtectionMetrics  # Protection-value metrics
    savings: SavingsMetrics        # Savings-value metrics


def analyze_insurance_plan(
    annual_premium: float,
    pay_years: int,
    coverage_years: int,
    sum_assured: float,
    inflation_pct: float,
    alt_return_pct: float,
    maturity_benefit: float,
) -> InsuranceResult:
    """Analyze core metrics for insurance plans.

    The model combines:
    - protection value: premium efficiency and real coverage under inflation;
    - savings value: IRR/net gain if product has maturity/surrender value.
    """
    total_premium = annual_premium * pay_years
    break_even_claim_prob = (total_premium / sum_assured) if sum_assured > 0 else 0.0
    coverage_cost_per_10k = (total_premium / sum_assured * 10000) if sum_assured > 0 else 0.0

    inflation_adjusted_coverage = sum_assured / ((1 + inflation_pct / 100) ** coverage_years)

    alt_rate = alt_return_pct / 100
    alt_value = 0.0

    rows: list[dict[str, float | int]] = []
    for year in range(1, coverage_years + 1):
        premium_paid = annual_premium if year <= pay_years else 0.0
        alt_value = (alt_value + premium_paid) * (1 + alt_rate)
        rows.append(
            {
                "保单年度": year,
                "当年保费": premium_paid,
                "累计保费": annual_premium * min(year, pay_years),
                "替代投资账户": alt_value,
                "名义保额": sum_assured,
                "实际保额(折现后)": sum_assured / ((1 + inflation_pct / 100) ** year),
            }
        )

    cash_flows: list[float] = [0.0]
    for year in range(1, coverage_years + 1):
        cf = -annual_premium if year <= pay_years else 0.0
        if year == coverage_years:
            cf += maturity_benefit
        cash_flows.append(cf)
    irr_pct = solve_irr(cash_flows) * 100
    net_gain = maturity_benefit - total_premium

    return InsuranceResult(
        yearly_schedule=pd.DataFrame(rows),
        protection=ProtectionMetrics(
            total_premium=total_premium,
            coverage_cost_per_10k=coverage_cost_per_10k,
            break_even_claim_prob=break_even_claim_prob,
            inflation_adjusted_coverage=inflation_adjusted_coverage,
            alt_investment_value=alt_value,
        ),
        savings=SavingsMetrics(irr_pct=irr_pct, net_gain=net_gain),
    )
