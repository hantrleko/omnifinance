"""Investment analytics engine — v2.4 risk and performance metrics.

Provides pure-Python / NumPy / pandas implementations of:
  - Historical and parametric VaR / CVaR (Expected Shortfall)
  - Marginal and component risk contribution (Euler decomposition)
  - Rolling performance metrics (return, volatility, Sharpe, drawdown)
  - Benchmark-relative metrics (alpha, beta, information ratio, tracking error)
  - Parameter sensitivity grid for strategy backtests

All functions are free of Streamlit and side-effects; they can be called
from pages or tested independently.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

# ── Type aliases ─────────────────────────────────────────────────────────────
ReturnSeries = pd.Series  # daily return series, float, DatetimeIndex
WeightArray = np.ndarray  # 1-D weight vector summing to 1


# ══════════════════════════════════════════════════════════════════════════════
#  VaR / CVaR
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class VaRResult:
    """Container for Value-at-Risk and Conditional VaR results.

    Attributes:
        confidence: Confidence level used (e.g. 0.95).
        var_hist: Historical VaR (negative number = loss threshold).
        cvar_hist: Historical CVaR / Expected Shortfall.
        var_param: Parametric (Gaussian) VaR.
        cvar_param: Parametric CVaR.
        n_obs: Number of observations used.
    """
    confidence: float
    var_hist: float
    cvar_hist: float
    var_param: float
    cvar_param: float
    n_obs: int


def compute_var_cvar(
    returns: ReturnSeries,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> VaRResult:
    """Compute historical and parametric VaR / CVaR for a return series.

    Args:
        returns: Daily return series (e.g. ``equity.pct_change().dropna()``).
        confidence: Confidence level, e.g. 0.95 for 95% VaR.
        horizon_days: Holding period in trading days (square-root-of-time scaling).

    Returns:
        :class:`VaRResult` with both historical and parametric estimates.

    Notes:
        - Historical VaR uses the empirical quantile of the return distribution.
        - Parametric VaR assumes normally distributed returns.
        - Both are scaled by ``sqrt(horizon_days)`` for multi-day horizons.
        - All loss figures are expressed as **negative** fractions
          (e.g. -0.03 means a 3% loss).
    """
    r = returns.dropna()
    n = len(r)
    if n < 10:
        return VaRResult(confidence, 0.0, 0.0, 0.0, 0.0, n)

    alpha = 1.0 - confidence
    scale = np.sqrt(horizon_days)

    # ── Historical ──
    var_hist = float(np.quantile(r, alpha)) * scale
    tail = r[r <= var_hist / scale]
    cvar_hist = float(tail.mean()) * scale if len(tail) > 0 else var_hist

    # ── Parametric (Gaussian) ──
    mu = float(r.mean())
    sigma = float(r.std(ddof=1))
    from scipy.stats import norm
    z = norm.ppf(alpha)
    var_param = (mu + z * sigma) * scale
    # CVaR = mu - sigma * phi(z) / alpha
    cvar_param = (mu - sigma * norm.pdf(z) / alpha) * scale

    return VaRResult(
        confidence=confidence,
        var_hist=var_hist,
        cvar_hist=cvar_hist,
        var_param=var_param,
        cvar_param=cvar_param,
        n_obs=n,
    )


def var_cvar_table(
    returns: ReturnSeries,
    confidences: list[float] | None = None,
    horizon_days: int = 1,
) -> pd.DataFrame:
    """Build a summary table of VaR/CVaR at multiple confidence levels.

    Args:
        returns: Daily return series.
        confidences: List of confidence levels. Defaults to [0.90, 0.95, 0.99].
        horizon_days: Holding period in trading days.

    Returns:
        DataFrame with columns: 置信度, 历史VaR, 历史CVaR, 参数VaR, 参数CVaR.
    """
    if confidences is None:
        confidences = [0.90, 0.95, 0.99]
    rows = []
    for c in confidences:
        v = compute_var_cvar(returns, c, horizon_days)
        rows.append({
            "置信度": f"{c:.0%}",
            "历史VaR": v.var_hist,
            "历史CVaR": v.cvar_hist,
            "参数VaR": v.var_param,
            "参数CVaR": v.cvar_param,
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
#  Portfolio Risk Contribution (Euler decomposition)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RiskContributionResult:
    """Marginal and component risk contribution for a portfolio.

    Attributes:
        tickers: Asset names in the same order as weights.
        weights: Portfolio weights (sum to 1).
        marginal_risk: Marginal risk contribution of each asset.
        component_risk: Component risk contribution (weight × marginal).
        component_pct: Percentage share of total portfolio risk.
        portfolio_vol: Total portfolio annualised volatility.
    """
    tickers: list[str]
    weights: np.ndarray
    marginal_risk: np.ndarray
    component_risk: np.ndarray
    component_pct: np.ndarray
    portfolio_vol: float


def compute_risk_contribution(
    weights: WeightArray | dict[str, float],
    cov_matrix: pd.DataFrame,
    annualise: bool = True,
) -> RiskContributionResult:
    """Compute Euler marginal and component risk contributions.

    Uses the Euler decomposition: the portfolio variance can be written as
    ``σ_p² = Σ_i w_i * (Σ w)_i / σ_p``, where each term is the component
    risk contribution of asset *i*.

    Args:
        weights: Either a dict ``{ticker: weight}`` or a 1-D numpy array
            aligned to the columns of *cov_matrix*.
        cov_matrix: Annualised or daily covariance matrix (pandas DataFrame).
        annualise: If True, multiply daily covariance by 252 before computing.

    Returns:
        :class:`RiskContributionResult` with per-asset risk decomposition.
    """
    tickers = list(cov_matrix.columns)

    if isinstance(weights, dict):
        w = np.array([weights.get(t, 0.0) for t in tickers])
    else:
        w = np.asarray(weights, dtype=float)

    cov = cov_matrix.values.astype(float)
    if annualise:
        # Only annualise if values look like daily covariance (< 0.01 typical)
        if cov.max() < 0.01:
            cov = cov * 252

    portfolio_var = float(w @ cov @ w)
    portfolio_vol = float(np.sqrt(max(portfolio_var, 0.0)))

    if portfolio_vol < 1e-12:
        zeros = np.zeros(len(w))
        return RiskContributionResult(tickers, w, zeros, zeros, zeros, 0.0)

    # Marginal risk contribution: ∂σ_p/∂w_i = (Σw)_i / σ_p
    marginal = (cov @ w) / portfolio_vol
    component = w * marginal
    component_pct = component / portfolio_vol if portfolio_vol > 0 else np.zeros(len(w))

    return RiskContributionResult(
        tickers=tickers,
        weights=w,
        marginal_risk=marginal,
        component_risk=component,
        component_pct=component_pct,
        portfolio_vol=portfolio_vol,
    )


def risk_contribution_dataframe(rc: RiskContributionResult) -> pd.DataFrame:
    """Convert a :class:`RiskContributionResult` to a display-ready DataFrame.

    Returns:
        DataFrame with columns: 标的, 权重, 边际风险贡献, 组件风险贡献, 风险占比.
    """
    return pd.DataFrame({
        "标的": rc.tickers,
        "权重": rc.weights,
        "边际风险贡献": rc.marginal_risk,
        "组件风险贡献": rc.component_risk,
        "风险占比": rc.component_pct,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Rolling Performance Metrics
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RollingMetrics:
    """Rolling performance metrics for an equity curve.

    Attributes:
        dates: DatetimeIndex aligned to the equity series.
        rolling_return: Rolling annualised return (fraction).
        rolling_vol: Rolling annualised volatility (fraction).
        rolling_sharpe: Rolling Sharpe ratio.
        drawdown: Drawdown series (negative fraction, 0 = at peak).
        underwater: Boolean mask — True when equity is below its peak.
    """
    dates: pd.DatetimeIndex
    rolling_return: pd.Series
    rolling_vol: pd.Series
    rolling_sharpe: pd.Series
    drawdown: pd.Series
    underwater: pd.Series


def compute_rolling_metrics(
    equity: pd.Series,
    window: int = 63,
    risk_free_annual_pct: float = 2.0,
) -> RollingMetrics:
    """Compute rolling return, volatility, Sharpe, and drawdown.

    Args:
        equity: Portfolio equity curve (absolute values, not returns).
        window: Rolling window in trading days (default 63 ≈ 1 quarter).
        risk_free_annual_pct: Annual risk-free rate in percent.

    Returns:
        :class:`RollingMetrics` with all series aligned to the equity index.
    """
    daily_returns = equity.pct_change()
    rf_daily = (risk_free_annual_pct / 100) / 252

    rolling_ret = daily_returns.rolling(window).mean() * 252
    rolling_vol = daily_returns.rolling(window).std(ddof=1) * np.sqrt(252)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rolling_sharpe = (
            (daily_returns.rolling(window).mean() - rf_daily)
            / daily_returns.rolling(window).std(ddof=1)
        ) * np.sqrt(252)

    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    underwater = drawdown < 0

    return RollingMetrics(
        dates=equity.index,
        rolling_return=rolling_ret,
        rolling_vol=rolling_vol,
        rolling_sharpe=rolling_sharpe,
        drawdown=drawdown,
        underwater=underwater,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Benchmark-relative Metrics
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BenchmarkMetrics:
    """Strategy vs benchmark performance comparison.

    Attributes:
        alpha_annual: Jensen's alpha (annualised, fraction).
        beta: Market beta.
        information_ratio: Information ratio (active return / tracking error).
        tracking_error: Annualised tracking error (fraction).
        active_return: Annualised active return (strategy − benchmark).
        correlation: Pearson correlation with benchmark.
        strategy_total_return: Total return of the strategy.
        benchmark_total_return: Total return of the benchmark.
        excess_total_return: Strategy total return minus benchmark total return.
    """
    alpha_annual: float
    beta: float
    information_ratio: float
    tracking_error: float
    active_return: float
    correlation: float
    strategy_total_return: float
    benchmark_total_return: float
    excess_total_return: float


def compute_benchmark_metrics(
    strategy_equity: pd.Series,
    benchmark_equity: pd.Series,
    risk_free_annual_pct: float = 2.0,
) -> BenchmarkMetrics:
    """Compute alpha, beta, information ratio, and tracking error.

    Args:
        strategy_equity: Strategy equity curve (absolute values).
        benchmark_equity: Benchmark equity curve (same length and index).
        risk_free_annual_pct: Annual risk-free rate in percent.

    Returns:
        :class:`BenchmarkMetrics` with all relative performance statistics.
    """
    s_ret = strategy_equity.pct_change().dropna()
    b_ret = benchmark_equity.pct_change().dropna()

    # Align on common index
    s_ret, b_ret = s_ret.align(b_ret, join="inner")

    n = len(s_ret)
    if n < 10:
        return BenchmarkMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)

    rf_daily = (risk_free_annual_pct / 100) / 252

    # Beta via OLS
    cov_mat = np.cov(s_ret.values, b_ret.values)
    beta = float(cov_mat[0, 1] / cov_mat[1, 1]) if cov_mat[1, 1] > 0 else 0.0

    # Alpha (Jensen's)
    alpha_daily = float(s_ret.mean()) - rf_daily - beta * (float(b_ret.mean()) - rf_daily)
    alpha_annual = alpha_daily * 252

    # Active return and tracking error
    active = s_ret - b_ret
    active_return = float(active.mean()) * 252
    tracking_error = float(active.std(ddof=1)) * np.sqrt(252)

    # Information ratio
    ir = active_return / tracking_error if tracking_error > 0 else 0.0

    # Correlation
    corr = float(np.corrcoef(s_ret.values, b_ret.values)[0, 1])

    # Total returns
    s_total = float(strategy_equity.iloc[-1] / strategy_equity.iloc[0] - 1)
    b_total = float(benchmark_equity.iloc[-1] / benchmark_equity.iloc[0] - 1)

    return BenchmarkMetrics(
        alpha_annual=alpha_annual,
        beta=beta,
        information_ratio=ir,
        tracking_error=tracking_error,
        active_return=active_return,
        correlation=corr,
        strategy_total_return=s_total,
        benchmark_total_return=b_total,
        excess_total_return=s_total - b_total,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Parameter Sensitivity Grid (for heatmap visualisation)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SensitivityGrid:
    """2-D parameter sensitivity results for heatmap visualisation.

    Attributes:
        param1_values: Values of the first parameter (rows).
        param2_values: Values of the second parameter (columns).
        metric_name: Name of the target metric (e.g. '夏普比率').
        grid: 2-D array of metric values, shape (len(p1), len(p2)).
        best_p1: Best param1 value (maximising metric).
        best_p2: Best param2 value (maximising metric).
        best_metric: Best metric value.
    """
    param1_values: list
    param2_values: list
    metric_name: str
    grid: np.ndarray
    best_p1: float
    best_p2: float
    best_metric: float


def build_sensitivity_grid(
    results: list[dict],
    param1_key: str,
    param2_key: str,
    metric_key: str = "夏普比率",
) -> SensitivityGrid | None:
    """Convert a flat list of grid-search results into a 2-D sensitivity grid.

    Args:
        results: List of dicts, each containing param1_key, param2_key, metric_key.
        param1_key: Key for the first parameter (will be grid rows).
        param2_key: Key for the second parameter (will be grid columns).
        metric_key: Metric to visualise (default '夏普比率').

    Returns:
        :class:`SensitivityGrid` ready for heatmap plotting, or None if
        insufficient data.
    """
    if not results:
        return None

    df = pd.DataFrame(results)
    required = {param1_key, param2_key, metric_key}
    if not required.issubset(df.columns):
        return None

    p1_vals = sorted(df[param1_key].unique())
    p2_vals = sorted(df[param2_key].unique())

    if len(p1_vals) < 2 or len(p2_vals) < 2:
        return None

    grid = np.full((len(p1_vals), len(p2_vals)), np.nan)
    p1_idx = {v: i for i, v in enumerate(p1_vals)}
    p2_idx = {v: i for i, v in enumerate(p2_vals)}

    for _, row in df.iterrows():
        i = p1_idx.get(row[param1_key])
        j = p2_idx.get(row[param2_key])
        if i is not None and j is not None and pd.notna(row[metric_key]):
            grid[i, j] = float(row[metric_key])

    # Best combination (ignoring NaN)
    valid_mask = ~np.isnan(grid)
    if not valid_mask.any():
        return None
    best_flat = int(np.nanargmax(grid))
    best_i, best_j = divmod(best_flat, len(p2_vals))

    return SensitivityGrid(
        param1_values=p1_vals,
        param2_values=p2_vals,
        metric_name=metric_key,
        grid=grid,
        best_p1=p1_vals[best_i],
        best_p2=p2_vals[best_j],
        best_metric=float(grid[best_i, best_j]),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Portfolio-level VaR from returns DataFrame
# ══════════════════════════════════════════════════════════════════════════════

def portfolio_var_cvar(
    returns_df: pd.DataFrame,
    weights: dict[str, float] | np.ndarray,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> VaRResult:
    """Compute VaR/CVaR for a weighted portfolio of assets.

    Args:
        returns_df: DataFrame of daily returns, one column per asset.
        weights: Asset weights as dict or array aligned to returns_df columns.
        confidence: Confidence level (e.g. 0.95).
        horizon_days: Holding period in trading days.

    Returns:
        :class:`VaRResult` for the combined portfolio return series.
    """
    tickers = list(returns_df.columns)
    if isinstance(weights, dict):
        w = np.array([weights.get(t, 0.0) for t in tickers])
    else:
        w = np.asarray(weights, dtype=float)

    # Normalise weights
    total = w.sum()
    if total > 0:
        w = w / total

    portfolio_returns = (returns_df[tickers] @ w).dropna()
    return compute_var_cvar(portfolio_returns, confidence, horizon_days)
