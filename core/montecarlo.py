"""Monte Carlo simulation for retirement and savings planning.

Simulates thousands of random return paths based on a log-normal distribution
(parameterised by expected annual return and annual volatility) to provide
probability-weighted outcome bands for retirement projections.

Example usage::

    from core.montecarlo import run_retirement_montecarlo, MonteCarloResult

    result = run_retirement_montecarlo(
        current_age=35,
        retire_age=65,
        life_expectancy=85,
        current_assets=500_000,
        monthly_saving=10_000,
        monthly_expense_today=30_000,
        inflation_pct=2.5,
        expected_annual_return_pct=7.0,
        annual_volatility_pct=15.0,
        post_return_pct=4.0,
        post_volatility_pct=8.0,
        n_simulations=2000,
        seed=42,
    )
    # result.percentile_paths  — DataFrame with columns: 年龄, p10, p25, p50, p75, p90
    # result.success_rate       — fraction of simulations where assets never hit zero
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MonteCarloResult:
    """Output of a Monte Carlo retirement simulation."""

    # Percentile paths: DataFrame with columns 年龄, p10, p25, p50, p75, p90
    percentile_paths: pd.DataFrame
    # Fraction of simulations where balance stays positive through life_expectancy
    success_rate: float
    # Number of simulations that completed with assets > 0
    n_success: int
    # Total number of simulations run
    n_simulations: int
    # Age at which median (p50) simulation first goes to zero (NaN if never)
    median_depletion_age: float


def run_retirement_montecarlo(
    current_age: int,
    retire_age: int,
    life_expectancy: int,
    current_assets: float,
    monthly_saving: float,
    monthly_expense_today: float,
    inflation_pct: float,
    expected_annual_return_pct: float,
    annual_volatility_pct: float,
    post_return_pct: float,
    post_volatility_pct: float,
    n_simulations: int = 2000,
    seed: int | None = 42,
    return_distribution: str = "normal",
    t_df: float = 5.0,
) -> MonteCarloResult:
    """Run a Monte Carlo retirement simulation.

    Supports both log-normal (normal) and Student-t fat-tail return distributions.

    Accumulation phase: each month the balance grows by a random return drawn
    from the selected distribution, then ``monthly_saving`` is added.

    Drawdown phase: each month a random return is applied and
    ``monthly_expense_today * (1+inflation)^year`` is withdrawn.

    Args:
        current_age: Current age in full years.
        retire_age: Target retirement age.
        life_expectancy: Expected lifespan.
        current_assets: Current savings/investments.
        monthly_saving: Monthly contribution before retirement.
        monthly_expense_today: Monthly living cost in today's money.
        inflation_pct: Annual inflation rate (%).
        expected_annual_return_pct: Mean annual portfolio return, pre-retirement (%).
        annual_volatility_pct: Annual portfolio volatility (std dev), pre-retirement (%).
        post_return_pct: Mean annual portfolio return, post-retirement (%).
        post_volatility_pct: Annual portfolio volatility, post-retirement (%).
        n_simulations: Number of Monte Carlo paths to simulate.
        seed: Random seed for reproducibility (``None`` for non-deterministic).
        return_distribution: ``"normal"`` for log-normal (default) or ``"t"`` for
            Student-t fat-tail distribution that better captures extreme market events.
        t_df: Degrees of freedom for the Student-t distribution (default 5).
            Lower values = fatter tails; typical range 3–10.

    Returns:
        :class:`MonteCarloResult` with percentile paths and success rate.
    """
    from scipy.stats import t as scipy_t

    rng = np.random.default_rng(seed)

    years_pre = retire_age - current_age
    years_post = life_expectancy - retire_age
    total_years = years_pre + years_post
    inflation = inflation_pct / 100

    # ── Convert annual params to monthly log-normal parameters ──
    # For a log-normal monthly return: mu_m = ln(1+r_annual)/12, sigma_m = sigma_annual/sqrt(12)
    mu_pre = np.log(1 + expected_annual_return_pct / 100) / 12
    sig_pre = (annual_volatility_pct / 100) / np.sqrt(12)
    mu_post = np.log(1 + post_return_pct / 100) / 12
    sig_post = (post_volatility_pct / 100) / np.sqrt(12)

    n_months_pre = years_pre * 12
    n_months_post = years_post * 12

    # Draw all random returns at once for performance
    # Shape: (n_simulations, n_months_pre) and (n_simulations, n_months_post)
    if return_distribution == "t" and t_df > 0:
        scale_factor = np.sqrt((t_df - 2) / t_df) if t_df > 2 else 1.0
        pre_z = scipy_t.rvs(df=t_df, size=(n_simulations, n_months_pre), random_state=int(seed) if seed is not None else None)
        post_z = scipy_t.rvs(df=t_df, size=(n_simulations, n_months_post), random_state=int(seed) + 1 if seed is not None else None)
        pre_returns = mu_pre + sig_pre / scale_factor * pre_z
        post_returns = mu_post + sig_post / scale_factor * post_z
    else:
        pre_returns = rng.normal(mu_pre, sig_pre, size=(n_simulations, n_months_pre))
        post_returns = rng.normal(mu_post, sig_post, size=(n_simulations, n_months_post))

    # ── Track yearly balances (shape: n_simulations × total_years+1) ──
    balances = np.zeros((n_simulations, total_years + 1))
    balances[:, 0] = current_assets

    # Accumulation phase — simulate month by month, snapshot each year
    bal = np.full(n_simulations, float(current_assets))
    for yr in range(years_pre):
        for m in range(12):
            bal = bal * (1 + pre_returns[:, yr * 12 + m]) + monthly_saving
        balances[:, yr + 1] = bal

    # Drawdown phase
    bal_post = balances[:, years_pre].copy()
    for yr in range(years_post):
        monthly_expense = monthly_expense_today * (1 + inflation) ** (years_pre + yr)
        for m in range(12):
            bal_post = bal_post * (1 + post_returns[:, yr * 12 + m]) - monthly_expense
            bal_post = np.maximum(bal_post, 0.0)
        balances[:, years_pre + yr + 1] = bal_post

    # ── Compute percentile paths ──────────────────────────────
    ages = np.arange(current_age, life_expectancy + 1)
    p10 = np.percentile(balances, 10, axis=0)
    p25 = np.percentile(balances, 25, axis=0)
    p50 = np.percentile(balances, 50, axis=0)
    p75 = np.percentile(balances, 75, axis=0)
    p90 = np.percentile(balances, 90, axis=0)

    percentile_paths = pd.DataFrame({
        "年龄": ages,
        "p10": p10,
        "p25": p25,
        "p50": p50,
        "p75": p75,
        "p90": p90,
    })

    # ── Success rate ──────────────────────────────────────────
    # A simulation "succeeds" if balance at life_expectancy > 0
    final_balances = balances[:, -1]
    n_success = int(np.sum(final_balances > 0))
    success_rate = n_success / n_simulations

    # ── Median depletion age ──────────────────────────────────
    zero_mask = p50 <= 0
    if zero_mask.any():
        median_depletion_age = float(ages[zero_mask][0])
    else:
        median_depletion_age = float("nan")

    return MonteCarloResult(
        percentile_paths=percentile_paths,
        success_rate=success_rate,
        n_success=n_success,
        n_simulations=n_simulations,
        median_depletion_age=median_depletion_age,
    )
