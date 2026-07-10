"""Walk-forward out-of-sample validation for strategy backtests.

Implements the v2.4 roadmap item "walk-forward testing / out-of-sample
validation": the price history is split into rolling (train → test) windows;
for every window the strategy parameters are re-optimised on the train slice
and evaluated *unchanged* on the following unseen test slice. Aggregating
the test-slice results gives a much more honest estimate of live performance
than a single full-sample backtest, and the gap between in-sample and
out-of-sample returns is a direct overfitting indicator.

Pure engine — no Streamlit imports; reuses :mod:`core.backtest` primitives.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from core.backtest import apply_strategy, simulate_trades


@dataclass(frozen=True)
class WalkForwardWindow:
    """Result of a single walk-forward fold.

    Attributes:
        fold: 1-based fold number.
        train_start / train_end: Train slice boundary timestamps.
        test_start / test_end: Test slice boundary timestamps.
        best_params: Parameters chosen on the train slice.
        train_return_pct: In-sample total return of *best_params* (%).
        test_return_pct: Out-of-sample total return of *best_params* (%).
        test_trades: Number of trades executed in the test slice.
    """

    fold: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    best_params: dict[str, Any]
    train_return_pct: float
    test_return_pct: float
    test_trades: int


@dataclass(frozen=True)
class WalkForwardResult:
    """Aggregated walk-forward validation result.

    Attributes:
        windows: Per-fold results in chronological order.
        oos_equity: Stitched out-of-sample equity curve (normalised to the
            initial capital at the start of the first test slice).
        avg_train_return_pct: Mean in-sample return across folds (%).
        avg_test_return_pct: Mean out-of-sample return across folds (%).
        oos_total_return_pct: Compounded return of the stitched OOS curve (%).
        overfit_ratio: ``avg_test / avg_train`` when train > 0 (1.0 ≈ robust,
            « 1 ≈ overfit, NaN when not computable).
        consistency_pct: Share of folds with positive OOS return (%).
        strategy: Strategy name that was validated.
    """

    windows: tuple[WalkForwardWindow, ...]
    oos_equity: pd.Series = field(repr=False)
    avg_train_return_pct: float = 0.0
    avg_test_return_pct: float = 0.0
    oos_total_return_pct: float = 0.0
    overfit_ratio: float = float("nan")
    consistency_pct: float = 0.0
    strategy: str = ""


def _param_grid(param_grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Expand a {name: [values...]} grid into a list of parameter dicts."""
    keys = list(param_grid.keys())
    combos = []
    for values in itertools.product(*(param_grid[k] for k in keys)):
        combos.append(dict(zip(keys, values, strict=False)))
    return combos


def _is_valid_combo(strategy: str, params: dict[str, Any]) -> bool:
    """Filter out degenerate parameter combinations."""
    if strategy == "MA 交叉":
        return params.get("short_window", 1) < params.get("long_window", 2)
    if strategy == "RSI":
        return params.get("oversold", 30) < params.get("overbought", 70)
    if strategy == "MACD":
        return params.get("fast", 12) < params.get("slow", 26)
    return True


def _total_return_pct(
    df: pd.DataFrame,
    strategy: str,
    params: dict[str, Any],
    initial_capital: float,
    fee_rate_pct: float,
    slippage_pct: float,
) -> tuple[float, pd.DataFrame, pd.DataFrame]:
    """Run one backtest and return (total_return_pct, equity_df, trades_df)."""
    signals = apply_strategy(df, strategy, params)
    result_df, trades_df = simulate_trades(
        signals, initial_capital, fee_rate_pct=fee_rate_pct, slippage_pct=slippage_pct
    )
    final = float(result_df["Equity"].iloc[-1])
    return (final / initial_capital - 1.0) * 100.0, result_df, trades_df


def run_walk_forward(
    df: pd.DataFrame,
    strategy: str,
    param_grid: dict[str, list[Any]],
    *,
    n_folds: int = 4,
    train_ratio: float = 0.7,
    initial_capital: float = 100_000.0,
    fee_rate_pct: float = 0.0,
    slippage_pct: float = 0.0,
    max_combos: int = 60,
) -> WalkForwardResult:
    """Run anchored-window walk-forward validation.

    The sample is divided into ``n_folds`` equal segments. Fold *k* trains on
    the first ``train_ratio`` share of segment *k* and tests on the remaining
    share, then the window rolls forward one segment.

    Args:
        df: OHLCV DataFrame with a DatetimeIndex and ``Close`` column.
        strategy: One of the names accepted by
            :func:`core.backtest.apply_strategy` (e.g. ``"MA 交叉"``).
        param_grid: Parameter name → candidate values, e.g.
            ``{"short_window": [5, 10], "long_window": [20, 30, 60]}``.
        n_folds: Number of rolling folds (≥ 2).
        train_ratio: Train share of each fold window, in (0.5, 0.95).
        initial_capital: Capital for each simulated slice.
        fee_rate_pct: Per-trade fee in percent.
        slippage_pct: Per-trade slippage in percent.
        max_combos: Safety cap on grid size (largest grids are subsampled
            deterministically).

    Returns:
        :class:`WalkForwardResult`.

    Raises:
        ValueError: On insufficient data, bad fold counts, or an empty /
            fully degenerate parameter grid.
    """
    if n_folds < 2:
        raise ValueError("走查检验至少需要 2 个窗口 (n_folds ≥ 2)。")
    if not 0.5 < train_ratio < 0.95:
        raise ValueError("train_ratio 需在 (0.5, 0.95) 区间内。")

    data = df.dropna(subset=["Close"]).copy()
    n = len(data)
    window_len = n // n_folds
    min_window = 60  # need enough bars for indicators on both slices
    if window_len < min_window:
        raise ValueError(
            f"数据量不足：{n} 根K线分为 {n_folds} 个窗口后每窗仅 {window_len} 根，"
            f"至少需要每窗 {min_window} 根。请拉长数据区间或减少窗口数。"
        )

    combos = [c for c in _param_grid(param_grid) if _is_valid_combo(strategy, c)]
    if not combos:
        raise ValueError("参数网格为空或全部组合无效（例如短均线 ≥ 长均线）。")
    if len(combos) > max_combos:
        step = len(combos) / max_combos
        combos = [combos[int(i * step)] for i in range(max_combos)]

    windows: list[WalkForwardWindow] = []
    oos_pieces: list[pd.Series] = []

    for fold in range(n_folds):
        seg = data.iloc[fold * window_len: (fold + 1) * window_len]
        split = int(len(seg) * train_ratio)
        train, test = seg.iloc[:split], seg.iloc[split:]
        if len(train) < 30 or len(test) < 10:
            continue

        # ── Optimise on train slice ──
        best_params: dict[str, Any] | None = None
        best_ret = -np.inf
        for params in combos:
            try:
                ret, _, _ = _total_return_pct(
                    train, strategy, params, initial_capital, fee_rate_pct, slippage_pct
                )
            except (ValueError, KeyError, IndexError):
                continue
            if ret > best_ret:
                best_ret, best_params = ret, params

        if best_params is None:
            continue

        # ── Evaluate unchanged on test slice ──
        try:
            test_ret, test_df, test_trades = _total_return_pct(
                test, strategy, best_params, initial_capital, fee_rate_pct, slippage_pct
            )
        except (ValueError, KeyError, IndexError):
            continue

        windows.append(
            WalkForwardWindow(
                fold=fold + 1,
                train_start=train.index[0],
                train_end=train.index[-1],
                test_start=test.index[0],
                test_end=test.index[-1],
                best_params=best_params,
                train_return_pct=float(best_ret),
                test_return_pct=float(test_ret),
                test_trades=int(len(test_trades)),
            )
        )
        oos_pieces.append(test_df["Equity"] / initial_capital)

    if not windows:
        raise ValueError("所有走查窗口均无法完成回测，请检查数据与参数网格。")

    # ── Stitch OOS equity: chain-multiply normalised slices ──
    stitched: list[pd.Series] = []
    level = 1.0
    for piece in oos_pieces:
        stitched.append(piece * level)
        level = float(stitched[-1].iloc[-1])
    oos_equity = pd.concat(stitched) * initial_capital

    train_rets = np.array([w.train_return_pct for w in windows])
    test_rets = np.array([w.test_return_pct for w in windows])
    avg_train = float(train_rets.mean())
    avg_test = float(test_rets.mean())
    overfit = avg_test / avg_train if avg_train > 1e-9 else float("nan")

    return WalkForwardResult(
        windows=tuple(windows),
        oos_equity=oos_equity,
        avg_train_return_pct=avg_train,
        avg_test_return_pct=avg_test,
        oos_total_return_pct=(level - 1.0) * 100.0,
        overfit_ratio=float(overfit),
        consistency_pct=float((test_rets > 0).mean() * 100.0),
        strategy=strategy,
    )


def walk_forward_table(result: WalkForwardResult) -> pd.DataFrame:
    """Convert a :class:`WalkForwardResult` into a display-ready DataFrame."""
    rows = []
    for w in result.windows:
        rows.append(
            {
                "窗口": w.fold,
                "训练区间": f"{w.train_start:%Y-%m-%d} ~ {w.train_end:%Y-%m-%d}",
                "测试区间": f"{w.test_start:%Y-%m-%d} ~ {w.test_end:%Y-%m-%d}",
                "最优参数": ", ".join(f"{k}={v}" for k, v in w.best_params.items()),
                "训练收益(%)": round(w.train_return_pct, 2),
                "测试收益(%)": round(w.test_return_pct, 2),
                "测试交易数": w.test_trades,
            }
        )
    return pd.DataFrame(rows)


def overfit_verdict(result: WalkForwardResult) -> tuple[str, str]:
    """Return a (level, message) robustness verdict for UI display.

    Levels: ``"good"`` / ``"warning"`` / ``"bad"``.
    """
    ratio = result.overfit_ratio
    consistency = result.consistency_pct

    if np.isnan(ratio):
        if result.avg_test_return_pct > 0:
            return "warning", "训练期平均收益接近 0，无法计算过拟合比率；样本外为正但证据不足。"
        return "bad", "训练期收益接近 0 且样本外表现不佳，该参数区间缺乏可用信号。"
    if ratio >= 0.5 and consistency >= 60:
        return "good", (
            f"样本外收益保留了训练期的 {ratio:.0%}，且 {consistency:.0f}% 的窗口为正收益，"
            "策略稳健性较好。"
        )
    if ratio >= 0.2 or consistency >= 50:
        return "warning", (
            f"样本外收益仅为训练期的 {ratio:.0%}（正收益窗口 {consistency:.0f}%），"
            "存在一定过拟合迹象，建议缩小参数网格或延长数据区间。"
        )
    return "bad", (
        f"样本外收益大幅衰减（仅为训练期的 {ratio:.0%}，正收益窗口 {consistency:.0f}%），"
        "参数很可能过拟合历史数据，不建议按此参数实盘。"
    )
