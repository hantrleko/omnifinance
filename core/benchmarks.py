"""National average financial benchmarks for comparison.

Provides reference data for Chinese household financial metrics
to compare against user's own financial situation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import streamlit as st


@dataclass(frozen=True)
class NationalBenchmarks:
    """Chinese household financial benchmarks (approximate 2024 data).

    Sources: National Bureau of Statistics, PBOC, various reports.
    """
    # Income
    avg_monthly_income: float = 8800.0          # Urban per-capita disposable income
    median_monthly_income: float = 6500.0

    # Savings
    avg_savings_rate_pct: float = 31.0           # Household savings rate
    avg_deposit_per_capita: float = 105000.0     # Per-capita bank deposits

    # Debt
    avg_debt_ratio_pct: float = 62.0             # Household debt / GDP
    avg_mortgage_pct_income: float = 35.0        # Mortgage payment / income

    # Retirement
    avg_retirement_age: float = 60.0
    avg_pension_monthly: float = 3500.0          # Average pension
    avg_retirement_savings: float = 120000.0

    # Insurance
    avg_insurance_density: float = 3300.0        # Per-capita premium
    avg_insurance_depth_pct: float = 3.9         # Premium / GDP

    # Investment
    avg_stock_participation_pct: float = 7.0     # % of population with stock accounts
    avg_fund_aum_per_investor: float = 50000.0

    # Housing
    avg_home_price_income_ratio: float = 9.2     # National average
    tier1_home_price_income_ratio: float = 25.0  # First-tier cities

    # Education
    avg_education_annual_cost: float = 30000.0   # K-12 average
    avg_university_annual_cost: float = 20000.0  # Public university


BENCHMARKS = NationalBenchmarks()


def compare_to_benchmark(metric_name: str, user_value: float) -> dict:
    """Compare a user's metric against the national benchmark.

    Args:
        metric_name: One of the benchmark field names.
        user_value: User's value for comparison.

    Returns:
        Dict with benchmark value, percentile estimate, and verdict.
    """
    benchmark_map = {
        "savings_rate": (BENCHMARKS.avg_savings_rate_pct, "%", "higher_better"),
        "monthly_income": (BENCHMARKS.avg_monthly_income, "元/月", "higher_better"),
        "debt_ratio": (BENCHMARKS.avg_debt_ratio_pct, "%", "lower_better"),
        "mortgage_ratio": (BENCHMARKS.avg_mortgage_pct_income, "%", "lower_better"),
        "retirement_savings": (BENCHMARKS.avg_retirement_savings, "元", "higher_better"),
        "insurance_premium": (BENCHMARKS.avg_insurance_density, "元/年", "neutral"),
    }

    if metric_name not in benchmark_map:
        return {"error": f"Unknown metric: {metric_name}"}

    benchmark_val, unit, direction = benchmark_map[metric_name]

    if direction == "higher_better":
        pct = min(100, max(0, user_value / benchmark_val * 50)) if benchmark_val > 0 else 50
        verdict = "优于平均" if user_value > benchmark_val else "低于平均"
    elif direction == "lower_better":
        pct = min(100, max(0, (2 - user_value / benchmark_val) * 50)) if benchmark_val > 0 else 50
        verdict = "优于平均" if user_value < benchmark_val else "高于平均"
    else:
        pct = 50
        verdict = "接近平均" if abs(user_value - benchmark_val) / max(benchmark_val, 1) < 0.2 else "偏离平均"

    return {
        "benchmark": benchmark_val,
        "user_value": user_value,
        "unit": unit,
        "percentile": pct,
        "verdict": verdict,
    }


def benchmark_inline(
    metric_name: str,
    user_value: float,
    label: str = "",
    help_text: str = "",
) -> None:
    """Render an inline benchmark comparison bar in Streamlit.

    Args:
        metric_name: One of the benchmark keys.
        user_value: User's current value.
        label: Optional display label override.
        help_text: Optional tooltip text.
    """
    result = compare_to_benchmark(metric_name, user_value)
    if "error" in result:
        return

    benchmark_val = result["benchmark"]
    unit = result["unit"]
    verdict = result["verdict"]
    direction = {
        "savings_rate": "higher_better",
        "monthly_income": "higher_better",
        "debt_ratio": "lower_better",
        "mortgage_ratio": "lower_better",
        "retirement_savings": "higher_better",
        "insurance_premium": "neutral",
    }.get(metric_name, "neutral")

    if direction == "higher_better":
        color = "#00CC96" if user_value >= benchmark_val else "#FFA726"
        icon = "🟢" if user_value >= benchmark_val else "🟡"
    elif direction == "lower_better":
        color = "#00CC96" if user_value <= benchmark_val else "#EF553B"
        icon = "🟢" if user_value <= benchmark_val else "🔴"
    else:
        diff_pct = abs(user_value - benchmark_val) / max(benchmark_val, 1) * 100
        color = "#00CC96" if diff_pct < 20 else "#FFA726"
        icon = "🟢" if diff_pct < 20 else "🟡"

    display_label = label or metric_name
    tooltip = f"全国均值：{benchmark_val:,.0f} {unit}" + (f"\n{help_text}" if help_text else "")

    st.markdown(
        f"""<div title="{tooltip}" style="margin:4px 0; padding:6px 10px; border-radius:6px; background:rgba(128,128,128,0.08); border-left:3px solid {color}; font-size:0.85em;">
        {icon} <b>{display_label}</b>: {user_value:,.0f} {unit} &nbsp;|&nbsp; 全国均值 {benchmark_val:,.0f} {unit} &nbsp;
        <span style="color:{color}; font-weight:600;">{verdict}</span>
        </div>""",
        unsafe_allow_html=True,
    )
