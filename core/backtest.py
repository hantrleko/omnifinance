"""Core quantitative backtesting functions for multiple strategies.

v1.4 changes:
- simulate_trades() rewritten with vectorised pandas operations (no iterrows)
- compute_metrics() adds Sortino ratio and Calmar ratio
"""

from __future__ import annotations

from typing import Any, TypedDict

import numpy as np
import pandas as pd


# ── TypedDict definitions ───────────────────────────────────

class MetricsDict(TypedDict):
    """回测结果指标字典，由 :func:`compute_metrics` 返回。"""

    总回报率: float      # key: "总回报率(%)"
    年化回报: float      # key: "年化回报(%)"
    最大回撤: float      # key: "最大回撤(%)"
    夏普比率: float
    索提诺比率: float
    卡玛比率: float
    交易次数: int
    胜率: float             # key: "胜率(%)"
    总交易成本: float


# ── Strategy: MA Crossover ────────────────────────

def calculate_signals(df: pd.DataFrame, short_window: int, long_window: int) -> pd.DataFrame:
    """Compute SMA crossover signals and annotate the DataFrame.

    Args:
        df: OHLCV DataFrame with at least a ``Close`` column.
        short_window: Look-back period for the short SMA.
        long_window: Look-back period for the long SMA.

    Returns:
        A copy of *df* with additional columns ``SMA_Short``, ``SMA_Long``,
        ``Signal``, ``CrossOver``, and ``Action`` (``"buy"`` / ``"sell"`` / ``"hold"``).
    """
    df = df.copy()
    df["SMA_Short"] = df["Close"].rolling(window=short_window, min_periods=short_window).mean()
    df["SMA_Long"] = df["Close"].rolling(window=long_window, min_periods=long_window).mean()

    df["Signal"] = 0
    df.loc[df["SMA_Short"] > df["SMA_Long"], "Signal"] = 1
    df.loc[df["SMA_Short"] <= df["SMA_Long"], "Signal"] = -1

    df["CrossOver"] = df["Signal"].diff()
    df["Action"] = "hold"
    df.loc[df["CrossOver"] == 2, "Action"] = "buy"
    df.loc[df["CrossOver"] == -2, "Action"] = "sell"

    return df


# ── Strategy: RSI ─────────────────────────────────────────

def calculate_rsi_signals(
    df: pd.DataFrame,
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> pd.DataFrame:
    """Compute RSI indicator and generate buy/sell signals.

    Args:
        df: OHLCV DataFrame with at least a ``Close`` column.
        period: RSI look-back window (default ``14``).
        oversold: RSI threshold below which a buy signal is generated
            (default ``30.0``).
        overbought: RSI threshold above which a sell signal is generated
            (default ``70.0``).

    Returns:
        A copy of *df* with additional columns ``RSI``, ``Signal``, and
        ``Action``.
    """
    df = df.copy()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Signal"] = 0
    df.loc[df["RSI"] < oversold, "Signal"] = 1
    df.loc[df["RSI"] > overbought, "Signal"] = -1

    df["Action"] = "hold"
    prev_signal = df["Signal"].shift(1).fillna(0)
    df.loc[(df["Signal"] == 1) & (prev_signal != 1), "Action"] = "buy"
    df.loc[(df["Signal"] == -1) & (prev_signal != -1), "Action"] = "sell"

    return df


# ── Strategy: MACD ────────────────────────────────────────

def calculate_macd_signals(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    """Compute MACD indicator and generate buy/sell signals.

    Args:
        df: OHLCV DataFrame with at least a ``Close`` column.
        fast: Fast EMA period (default ``12``).
        slow: Slow EMA period (default ``26``).
        signal_period: Signal-line EMA period (default ``9``).

    Returns:
        A copy of *df* with additional columns ``MACD``, ``MACD_Signal``,
        ``MACD_Hist``, ``Signal``, ``CrossOver``, and ``Action``.
    """
    df = df.copy()
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()

    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal_period, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    df["Signal"] = 0
    df.loc[df["MACD"] > df["MACD_Signal"], "Signal"] = 1
    df.loc[df["MACD"] <= df["MACD_Signal"], "Signal"] = -1

    df["CrossOver"] = df["Signal"].diff()
    df["Action"] = "hold"
    df.loc[df["CrossOver"] == 2, "Action"] = "buy"
    df.loc[df["CrossOver"] == -2, "Action"] = "sell"

    return df


# ── Strategy: Bollinger Bands ─────────────────────────────

def calculate_bollinger_signals(
    df: pd.DataFrame,
    period: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Compute Bollinger Bands and generate buy/sell signals.

    Args:
        df: OHLCV DataFrame with at least a ``Close`` column.
        period: Rolling window for the middle band SMA (default ``20``).
        num_std: Number of standard deviations for the upper/lower bands
            (default ``2.0``).

    Returns:
        A copy of *df* with additional columns ``BB_Mid``, ``BB_Upper``,
        ``BB_Lower``, ``Signal``, and ``Action``.
    """
    df = df.copy()
    df["BB_Mid"] = df["Close"].rolling(window=period, min_periods=period).mean()
    rolling_std = df["Close"].rolling(window=period, min_periods=period).std()
    df["BB_Upper"] = df["BB_Mid"] + num_std * rolling_std
    df["BB_Lower"] = df["BB_Mid"] - num_std * rolling_std

    df["Signal"] = 0
    df.loc[df["Close"] < df["BB_Lower"], "Signal"] = 1
    df.loc[df["Close"] > df["BB_Upper"], "Signal"] = -1

    df["Action"] = "hold"
    prev_signal = df["Signal"].shift(1).fillna(0)
    df.loc[(df["Signal"] == 1) & (prev_signal != 1), "Action"] = "buy"
    df.loc[(df["Signal"] == -1) & (prev_signal != -1), "Action"] = "sell"

    return df


# ── Strategy dispatcher ──────────────────────────────────

STRATEGY_NAMES: list[str] = ["MA 交叉", "RSI", "MACD", "布林带"]


def apply_strategy(df: pd.DataFrame, strategy: str, params: dict[str, Any]) -> pd.DataFrame:
    """Dispatch to the appropriate strategy function.

    Args:
        df: OHLCV DataFrame with at least a ``Close`` column.
        strategy: Strategy name; must be one of :data:`STRATEGY_NAMES`.
        params: Strategy-specific parameter dict.

    Returns:
        The signal-annotated DataFrame produced by the chosen strategy.

    Raises:
        ValueError: If *strategy* is not a recognised name.
    """
    if strategy == "MA 交叉":
        return calculate_signals(df, params["short_window"], params["long_window"])
    elif strategy == "RSI":
        return calculate_rsi_signals(df, params.get("period", 14), params.get("oversold", 30), params.get("overbought", 70))
    elif strategy == "MACD":
        return calculate_macd_signals(df, params.get("fast", 12), params.get("slow", 26), params.get("signal_period", 9))
    elif strategy == "布林带":
        return calculate_bollinger_signals(df, params.get("period", 20), params.get("num_std", 2.0))
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


# ── Vectorised trade simulation ───────────────────────────

def simulate_trades(
    df: pd.DataFrame,
    initial_capital: float,
    fee_rate_pct: float = 0.0,
    slippage_pct: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Vectorised full-position trade simulation.

    Replaces the previous row-by-row iterrows loop with a pandas-based
    state machine that is significantly faster on long time series.

    Returns:
        (df_with_equity, trades_df) — df has Equity and Benchmark columns added.
    """
    df = df.copy()
    fee_rate = fee_rate_pct / 100.0
    slippage_rate = slippage_pct / 100.0

    close = df["Close"].values
    actions = df["Action"].values
    n = len(close)

    equity_arr = np.empty(n, dtype=float)
    cash = initial_capital
    shares = 0.0
    entry_price = 0.0
    total_costs = 0.0
    trades: list[dict[str, Any]] = []
    idx_values = df.index

    for i in range(n):
        price = close[i]
        action = actions[i]

        if action == "buy" and shares == 0.0:
            buy_price = price * (1.0 + slippage_rate)
            if buy_price > 0:
                fee = cash * fee_rate          # fee on the full cash outlay
                net_cash = cash - fee
                shares = net_cash / buy_price
                entry_price = buy_price
                total_costs += fee
                cash = 0.0
                trades.append({
                    "日期": idx_values[i],
                    "操作": "买入",
                    "价格": buy_price,
                    "数量": shares,
                    "手续费": fee,
                    "盈亏": None,
                    "盈亏率(%)": None,
                })

        elif action == "sell" and shares > 0.0:
            sell_price = price * (1.0 - slippage_rate)
            gross_value = shares * sell_price
            fee = gross_value * fee_rate
            cash = gross_value - fee
            pnl = (sell_price - entry_price) * shares - fee
            pnl_pct = (sell_price / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
            total_costs += fee
            trades.append({
                "日期": idx_values[i],
                "操作": "卖出",
                "价格": sell_price,
                "数量": shares,
                "手续费": fee,
                "盈亏": pnl,
                "盈亏率(%)": pnl_pct,
            })
            shares = 0.0

        equity_arr[i] = cash + shares * price

    df["Equity"] = equity_arr
    df["Benchmark"] = initial_capital * (close / close[0])

    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df.attrs["total_costs"] = float(trades_df["手续费"].sum())
    else:
        trades_df.attrs["total_costs"] = total_costs

    return df, trades_df


# ── Performance metrics ───────────────────────────────────

def compute_metrics(
    df: pd.DataFrame,
    trades_df: pd.DataFrame,
    initial_capital: float,
    risk_free_pct: float,
) -> dict[str, Any]:
    """Compute strategy performance metrics.

    v1.4: Added Sortino ratio and Calmar ratio.

    Args:
        df: Result DataFrame from :func:`simulate_trades` containing an
            ``Equity`` column.
        trades_df: Trades DataFrame from :func:`simulate_trades`.
        initial_capital: Starting capital used in the simulation.
        risk_free_pct: Annual risk-free rate in percent (e.g. ``2.0``).

    Returns:
        A dict with keys: ``总回报率(%)``, ``年化回报(%)``, ``最大回撤(%)``,
        ``夏普比率``, ``索提诺比率``, ``卡玛比率``, ``交易次数``,
        ``胜率(%)``, ``总交易成本``.
    """
    equity = df["Equity"]
    final_equity = equity.iloc[-1]
    total_return = (final_equity / initial_capital - 1) * 100

    trading_days = len(df)
    years = trading_days / 252
    annual_return = ((final_equity / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0.0

    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_drawdown = drawdown.min() * 100

    daily_returns = equity.pct_change().dropna()
    rf_daily = (risk_free_pct / 100) / 252

    # ── Sharpe ratio ──
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        excess = daily_returns.mean() - rf_daily
        sharpe = (excess / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # ── Sortino ratio (downside deviation only) ──
    downside = daily_returns[daily_returns < rf_daily]
    if len(downside) > 1 and downside.std() > 0:
        sortino = ((daily_returns.mean() - rf_daily) / downside.std()) * np.sqrt(252)
    else:
        sortino = 0.0

    # ── Calmar ratio (annual return / max drawdown) ──
    calmar = (annual_return / abs(max_drawdown)) if max_drawdown != 0 else 0.0

    # ── Trade stats ──
    sell_trades = trades_df[trades_df["操作"] == "卖出"] if not trades_df.empty else pd.DataFrame()
    num_trades = len(sell_trades)
    wins = len(sell_trades[sell_trades["盈亏"] > 0]) if num_trades > 0 else 0
    win_rate = (wins / num_trades * 100) if num_trades > 0 else 0.0

    total_costs = float(trades_df.attrs.get("total_costs", 0.0))

    return {
        "总回报率(%)": total_return,
        "年化回报(%)": annual_return,
        "最大回撤(%)": max_drawdown,
        "夏普比率": sharpe,
        "索提诺比率": sortino,
        "卡玛比率": calmar,
        "交易次数": num_trades,
        "胜率(%)": win_rate,
        "总交易成本": total_costs,
    }
