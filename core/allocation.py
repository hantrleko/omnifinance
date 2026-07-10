"""Advanced asset allocation engines — Risk Parity & Black-Litterman.

Implements the two allocation methods listed as v2.4 roadmap extensions:

1. **Risk parity** (equal risk contribution): iterative solver that finds the
   long-only weight vector where every asset contributes equally to total
   portfolio volatility.
2. **Black-Litterman**: combines market-implied equilibrium returns with
   subjective investor views to produce posterior expected returns, which are
   then fed into a max-Sharpe optimisation.

All functions are pure (NumPy / pandas / SciPy only, no Streamlit) so they
can be unit-tested and reused from any page.

Example::

    from core.allocation import risk_parity_weights, black_litterman

    rp = risk_parity_weights(cov_matrix_df)
    bl = black_litterman(
        cov_matrix=cov_matrix_df,
        market_weights={"AAPL": 0.5, "MSFT": 0.5},
        views=[View(assets={"AAPL": 1.0}, expected_return=0.10, confidence=0.6)],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize

# ══════════════════════════════════════════════════════════════════════════
#  Risk parity (Equal Risk Contribution)
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RiskParityResult:
    """Result of a risk-parity optimisation.

    Attributes:
        weights: Ticker → weight mapping (long-only, sums to 1).
        risk_contributions: Ticker → fractional risk contribution
            (each ≈ 1/n when fully converged).
        portfolio_volatility: Annualised portfolio volatility (decimal).
        converged: Whether the solver met its tolerance.
        n_iterations: Iterations used by the solver.
    """

    weights: dict[str, float]
    risk_contributions: dict[str, float]
    portfolio_volatility: float
    converged: bool
    n_iterations: int


def _portfolio_vol(w: np.ndarray, cov: np.ndarray) -> float:
    return float(np.sqrt(max(w @ cov @ w, 0.0)))


def _risk_contributions(w: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Fractional risk contribution of each asset (sums to 1)."""
    vol = _portfolio_vol(w, cov)
    if vol < 1e-12:
        return np.full_like(w, 1.0 / len(w))
    marginal = cov @ w / vol            # ∂σ/∂w_i
    contrib = w * marginal              # w_i · ∂σ/∂w_i, sums to σ
    return contrib / vol


def risk_parity_weights(
    cov_matrix: pd.DataFrame,
    *,
    risk_budget: dict[str, float] | None = None,
    max_iterations: int = 500,
    tolerance: float = 1e-10,
) -> RiskParityResult:
    """Solve for (budgeted) equal-risk-contribution weights.

    Uses SLSQP on the standard least-squares ERC objective::

        min Σ_i (RC_i - b_i·σ)²   s.t.  Σw = 1,  w ≥ 0

    Args:
        cov_matrix: Annualised covariance matrix (tickers × tickers).
        risk_budget: Optional ticker → target risk share mapping. Missing
            tickers get an equal share of the remainder; values are
            normalised to sum to 1. ``None`` = classic equal risk.
        max_iterations: SLSQP iteration cap.
        tolerance: SLSQP convergence tolerance.

    Returns:
        :class:`RiskParityResult`.

    Raises:
        ValueError: If fewer than 2 assets or the matrix is not square.
    """
    tickers = list(cov_matrix.columns)
    n = len(tickers)
    if n < 2:
        raise ValueError("风险平价至少需要 2 个资产。")
    if cov_matrix.shape[0] != cov_matrix.shape[1]:
        raise ValueError("协方差矩阵必须是方阵。")

    cov = cov_matrix.values.astype(float)

    # Build normalised risk budget vector
    if risk_budget:
        budget = np.array([max(float(risk_budget.get(t, 0.0)), 0.0) for t in tickers])
        missing = budget <= 0
        if missing.any():
            # Give unlisted assets an equal share of leftover budget
            leftover = max(1.0 - budget.sum(), 0.0)
            budget[missing] = leftover / missing.sum() if missing.sum() else 0.0
        total = budget.sum()
        if total <= 0:
            budget = np.full(n, 1.0 / n)
        else:
            budget = budget / total
    else:
        budget = np.full(n, 1.0 / n)

    def objective(w: np.ndarray) -> float:
        vol = _portfolio_vol(w, cov)
        if vol < 1e-12:
            return 1e6
        rc = w * (cov @ w) / vol        # absolute contributions, sum = σ
        target = budget * vol
        return float(np.sum((rc - target) ** 2)) * 1e4

    w0 = np.full(n, 1.0 / n)
    result = minimize(
        objective,
        w0,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
        options={"maxiter": max_iterations, "ftol": tolerance},
    )

    w = np.clip(result.x, 0.0, None)
    w = w / w.sum() if w.sum() > 0 else np.full(n, 1.0 / n)
    rc = _risk_contributions(w, cov)

    return RiskParityResult(
        weights={t: float(w[i]) for i, t in enumerate(tickers)},
        risk_contributions={t: float(rc[i]) for i, t in enumerate(tickers)},
        portfolio_volatility=_portfolio_vol(w, cov),
        converged=bool(result.success),
        n_iterations=int(result.nit),
    )


# ══════════════════════════════════════════════════════════════════════════
#  Black-Litterman
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class View:
    """A single investor view for the Black-Litterman model.

    Attributes:
        assets: Ticker → pick coefficient. ``{"AAPL": 1.0}`` is an absolute
            view ("AAPL will return X"); ``{"AAPL": 1.0, "MSFT": -1.0}``
            is a relative view ("AAPL will outperform MSFT by X").
        expected_return: Annualised expected return of the view (decimal,
            e.g. ``0.10`` = 10%).
        confidence: View confidence in (0, 1]. Higher = tighter view
            uncertainty and a stronger tilt toward the view.
    """

    assets: dict[str, float]
    expected_return: float
    confidence: float = 0.5


@dataclass(frozen=True)
class BlackLittermanResult:
    """Result of a Black-Litterman posterior computation.

    Attributes:
        posterior_returns: Ticker → posterior expected annual return.
        equilibrium_returns: Ticker → market-implied prior return.
        weights: Max-Sharpe weights computed from posterior returns.
        posterior_cov: Posterior covariance DataFrame.
        risk_aversion: The δ used to back out equilibrium returns.
    """

    posterior_returns: dict[str, float]
    equilibrium_returns: dict[str, float]
    weights: dict[str, float]
    posterior_cov: pd.DataFrame = field(repr=False, default=None)  # type: ignore[assignment]
    risk_aversion: float = 2.5


def implied_equilibrium_returns(
    cov_matrix: pd.DataFrame,
    market_weights: dict[str, float],
    risk_aversion: float = 2.5,
) -> pd.Series:
    """Back out market-implied returns: ``π = δ · Σ · w_mkt``.

    Args:
        cov_matrix: Annualised covariance matrix.
        market_weights: Ticker → market-cap (or benchmark) weight.
        risk_aversion: Market risk-aversion coefficient δ (typical 2–3).

    Returns:
        Series of implied annual returns indexed by ticker.
    """
    tickers = list(cov_matrix.columns)
    w = np.array([float(market_weights.get(t, 0.0)) for t in tickers])
    total = w.sum()
    if total <= 0:
        w = np.full(len(tickers), 1.0 / len(tickers))
    else:
        w = w / total
    pi = risk_aversion * cov_matrix.values @ w
    return pd.Series(pi, index=tickers)


def _max_sharpe_weights(
    mu: np.ndarray,
    cov: np.ndarray,
    risk_free: float,
) -> np.ndarray:
    """Long-only max-Sharpe weights via SLSQP."""
    n = len(mu)

    def neg_sharpe(w: np.ndarray) -> float:
        ret = float(w @ mu)
        vol = _portfolio_vol(w, cov)
        return -(ret - risk_free) / vol if vol > 1e-9 else 0.0

    result = minimize(
        neg_sharpe,
        np.full(n, 1.0 / n),
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
        options={"maxiter": 500},
    )
    w = np.clip(result.x, 0.0, None)
    return w / w.sum() if w.sum() > 0 else np.full(n, 1.0 / n)


def black_litterman(
    cov_matrix: pd.DataFrame,
    market_weights: dict[str, float],
    views: list[View] | None = None,
    *,
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    risk_free_rate_pct: float = 2.0,
) -> BlackLittermanResult:
    """Run the Black-Litterman model and derive max-Sharpe weights.

    Posterior mean (master formula)::

        E[R] = [(τΣ)⁻¹ + Pᵀ Ω⁻¹ P]⁻¹ [(τΣ)⁻¹ π + Pᵀ Ω⁻¹ Q]

    View uncertainty Ω is diagonal with
    ``Ω_kk = (p_k τ Σ p_kᵀ) · (1 - c_k) / c_k`` so that confidence ``c → 1``
    collapses the view variance toward 0 (view fully trusted).

    Args:
        cov_matrix: Annualised covariance matrix (tickers × tickers).
        market_weights: Ticker → market weight for the equilibrium prior.
        views: Optional list of :class:`View`. Views referencing unknown
            tickers are ignored; with no valid views the posterior equals
            the equilibrium prior.
        risk_aversion: δ used for the implied prior.
        tau: Prior uncertainty scalar (typical 0.01–0.1).
        risk_free_rate_pct: Annual risk-free rate in percent for the final
            max-Sharpe step.

    Returns:
        :class:`BlackLittermanResult`.

    Raises:
        ValueError: If fewer than 2 assets are provided.
    """
    tickers = list(cov_matrix.columns)
    n = len(tickers)
    if n < 2:
        raise ValueError("Black-Litterman 至少需要 2 个资产。")

    cov = cov_matrix.values.astype(float)
    pi = implied_equilibrium_returns(cov_matrix, market_weights, risk_aversion).values

    valid_views = [
        v for v in (views or [])
        if v.assets and all(t in tickers for t in v.assets) and 0.0 < v.confidence <= 1.0
    ]

    if valid_views:
        k = len(valid_views)
        P = np.zeros((k, n))
        Q = np.zeros(k)
        omega_diag = np.zeros(k)
        tau_cov = tau * cov

        for row, view in enumerate(valid_views):
            for t, coef in view.assets.items():
                P[row, tickers.index(t)] = float(coef)
            Q[row] = float(view.expected_return)
            base_var = float(P[row] @ tau_cov @ P[row])
            conf = min(max(view.confidence, 1e-4), 1.0 - 1e-6)
            omega_diag[row] = max(base_var * (1.0 - conf) / conf, 1e-12)

        omega_inv = np.diag(1.0 / omega_diag)
        tau_cov_inv = np.linalg.pinv(tau_cov)

        a = tau_cov_inv + P.T @ omega_inv @ P
        b = tau_cov_inv @ np.asarray(pi, dtype=float) + P.T @ omega_inv @ Q
        posterior_mu = np.linalg.solve(a, b)
        posterior_cov_arr = cov + np.linalg.pinv(a)
    else:
        posterior_mu = pi.copy()
        posterior_cov_arr = cov * (1.0 + tau)

    risk_free = risk_free_rate_pct / 100.0
    weights_arr = _max_sharpe_weights(posterior_mu, posterior_cov_arr, risk_free)

    return BlackLittermanResult(
        posterior_returns={t: float(posterior_mu[i]) for i, t in enumerate(tickers)},
        equilibrium_returns={t: float(pi[i]) for i, t in enumerate(tickers)},
        weights={t: float(weights_arr[i]) for i, t in enumerate(tickers)},
        posterior_cov=pd.DataFrame(posterior_cov_arr, index=tickers, columns=tickers),
        risk_aversion=risk_aversion,
    )


# ══════════════════════════════════════════════════════════════════════════
#  Comparison helper
# ══════════════════════════════════════════════════════════════════════════

def allocation_comparison_table(
    allocations: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Build a tidy comparison DataFrame from multiple allocation schemes.

    Args:
        allocations: Scheme label → (ticker → weight) mapping, e.g.
            ``{"风险平价": {...}, "最大夏普": {...}}``.

    Returns:
        DataFrame indexed by ticker with one column per scheme (weights as
        decimals). Missing tickers are filled with 0.
    """
    if not allocations:
        return pd.DataFrame()
    all_tickers: list[str] = sorted({t for w in allocations.values() for t in w})
    data = {
        label: [float(weights.get(t, 0.0)) for t in all_tickers]
        for label, weights in allocations.items()
    }
    return pd.DataFrame(data, index=all_tickers)
