"""Markowitz Mean-Variance Portfolio Optimizer.

Computes the efficient frontier and key optimal portfolios:
  - Maximum Sharpe Ratio (tangency portfolio)
  - Minimum Variance portfolio
  - Maximum Return for a given volatility target

All weights returned sum to 1 and are long-only (≥ 0) by default.

Example::

    from core.portfolio import optimize_portfolio, EfficientFrontierResult

    result = optimize_portfolio(
        returns_df=daily_returns_df,   # DataFrame: columns = ticker, rows = daily returns
        risk_free_rate_pct=2.0,
        n_frontier_points=50,
    )
    print(result.max_sharpe_weights)   # dict {ticker: weight}
    print(result.efficient_frontier)   # DataFrame with cols: volatility, return, sharpe
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class PortfolioStats:
    """Statistics for a single portfolio allocation."""

    weights: dict[str, float]          # ticker -> weight (sum = 1)
    annual_return: float               # Expected annual return (decimal)
    annual_volatility: float           # Annual standard deviation (decimal)
    sharpe_ratio: float                # Sharpe ratio


@dataclass
class EfficientFrontierResult:
    """Result of efficient frontier optimisation."""

    max_sharpe: PortfolioStats
    min_variance: PortfolioStats
    efficient_frontier: pd.DataFrame   # cols: volatility, annual_return, sharpe_ratio
    tickers: list[str]
    # Annualised return and covariance matrix (for reference)
    annual_returns: pd.Series
    cov_matrix: pd.DataFrame


def _portfolio_stats(
    weights: np.ndarray,
    annual_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free: float,
) -> tuple[float, float, float]:
    """Compute (return, volatility, sharpe) for a weight vector."""
    ret = float(np.dot(weights, annual_returns))
    vol = float(np.sqrt(weights @ cov_matrix @ weights))
    sharpe = (ret - risk_free) / vol if vol > 1e-9 else 0.0
    return ret, vol, sharpe


def optimize_portfolio(
    returns_df: pd.DataFrame,
    risk_free_rate_pct: float = 2.0,
    n_frontier_points: int = 50,
    trading_days_per_year: int = 252,
) -> EfficientFrontierResult:
    """Run Markowitz mean-variance optimisation on *returns_df*.

    Args:
        returns_df: DataFrame of **periodic** (e.g. daily) simple returns.
            Columns are asset tickers; rows are time periods.  Missing values
            are dropped.
        risk_free_rate_pct: Annual risk-free rate in percent (e.g. ``2.0``).
        n_frontier_points: Number of points along the efficient frontier.
        trading_days_per_year: Used to annualise daily statistics
            (default 252).

    Returns:
        :class:`EfficientFrontierResult` with optimised portfolios and the
        efficient frontier DataFrame.

    Raises:
        ValueError: If fewer than 2 assets remain after cleaning, or if
            the optimisation fails for all frontier points.
    """
    df = returns_df.dropna()
    tickers = list(df.columns)
    n = len(tickers)

    if n < 2:
        raise ValueError("至少需要 2 个有效标的才能进行组合优化。")

    risk_free = risk_free_rate_pct / 100

    # Annualise
    mu = df.mean().values * trading_days_per_year       # shape (n,)
    cov = df.cov().values * trading_days_per_year       # shape (n, n)

    bounds = tuple((0.0, 1.0) for _ in range(n))
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    w0 = np.ones(n) / n  # equal-weight starting point

    # ── Max Sharpe ────────────────────────────────────────────
    def neg_sharpe(w: np.ndarray) -> float:
        _, _, sh = _portfolio_stats(w, mu, cov, risk_free)
        return -sh

    res_sharpe = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints,
                          options={"ftol": 1e-9, "maxiter": 1000})
    w_sharpe = res_sharpe.x if res_sharpe.success else w0
    r_sh, v_sh, sh_sh = _portfolio_stats(w_sharpe, mu, cov, risk_free)
    max_sharpe = PortfolioStats(
        weights={t: float(w_sharpe[i]) for i, t in enumerate(tickers)},
        annual_return=r_sh,
        annual_volatility=v_sh,
        sharpe_ratio=sh_sh,
    )

    # ── Min Variance ─────────────────────────────────────────
    def portfolio_variance(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    res_minvar = minimize(portfolio_variance, w0, method="SLSQP", bounds=bounds,
                          constraints=constraints, options={"ftol": 1e-9, "maxiter": 1000})
    w_mv = res_minvar.x if res_minvar.success else w0
    r_mv, v_mv, sh_mv = _portfolio_stats(w_mv, mu, cov, risk_free)
    min_variance = PortfolioStats(
        weights={t: float(w_mv[i]) for i, t in enumerate(tickers)},
        annual_return=r_mv,
        annual_volatility=v_mv,
        sharpe_ratio=sh_mv,
    )

    # ── Efficient Frontier ────────────────────────────────────
    # Sweep target returns from min-variance return to max-return (100% best asset)
    r_min_ef = r_mv
    r_max_ef = float(np.max(mu))
    target_returns = np.linspace(r_min_ef, r_max_ef, n_frontier_points)

    frontier_rows: list[dict] = []
    for target_r in target_returns:
        constraints_ef = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, tr=target_r: np.dot(w, mu) - tr},
        ]
        res_ef = minimize(portfolio_variance, w0, method="SLSQP", bounds=bounds,
                          constraints=constraints_ef, options={"ftol": 1e-9, "maxiter": 1000})
        if res_ef.success:
            w_ef = res_ef.x
            _, v_ef, sh_ef = _portfolio_stats(w_ef, mu, cov, risk_free)
            frontier_rows.append({
                "volatility": v_ef,
                "annual_return": target_r,
                "sharpe_ratio": sh_ef,
                "weights": {t: float(w_ef[i]) for i, t in enumerate(tickers)},
            })

    frontier_df = pd.DataFrame(frontier_rows)

    return EfficientFrontierResult(
        max_sharpe=max_sharpe,
        min_variance=min_variance,
        efficient_frontier=frontier_df,
        tickers=tickers,
        annual_returns=pd.Series(mu, index=tickers),
        cov_matrix=pd.DataFrame(cov, index=tickers, columns=tickers),
    )
