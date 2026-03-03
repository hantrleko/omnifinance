"""Core quantitative backtesting functions for multiple strategies."""

from __future__ import annotations

import numpy as np
import pandas as pd


# ── Strategy: MA Crossover ────────────────────────────────

def calculate_signals(df: pd.DataFrame, short_window: int, long_window: int) -> pd.DataFrame:
    """计算 SMA 与交叉信号。"""
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
    """计算 RSI 指标并生成买卖信号。"""
    df = df.copy()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Signal"] = 0
    df.loc[df["RSI"] < oversold, "Signal"] = 1   # oversold → buy signal
    df.loc[df["RSI"] > overbought, "Signal"] = -1  # overbought → sell signal

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
    """计算 MACD 指标并生成买卖信号。"""
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
    """计算布林带指标并生成买卖信号。"""
    df = df.copy()
    df["BB_Mid"] = df["Close"].rolling(window=period, min_periods=period).mean()
    rolling_std = df["Close"].rolling(window=period, min_periods=period).std()
    df["BB_Upper"] = df["BB_Mid"] + num_std * rolling_std
    df["BB_Lower"] = df["BB_Mid"] - num_std * rolling_std

    df["Signal"] = 0
    df.loc[df["Close"] < df["BB_Lower"], "Signal"] = 1   # below lower → buy
    df.loc[df["Close"] > df["BB_Upper"], "Signal"] = -1   # above upper → sell

    df["Action"] = "hold"
    prev_signal = df["Signal"].shift(1).fillna(0)
    df.loc[(df["Signal"] == 1) & (prev_signal != 1), "Action"] = "buy"
    df.loc[(df["Signal"] == -1) & (prev_signal != -1), "Action"] = "sell"

    return df


# ── Strategy dispatcher ──────────────────────────────────

STRATEGY_NAMES = ["MA 交叉", "RSI", "MACD", "布林带"]


def apply_strategy(df: pd.DataFrame, strategy: str, params: dict) -> pd.DataFrame:
    """Apply the named strategy with given params and return signals df."""
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


def simulate_trades(
    df: pd.DataFrame,
    initial_capital: float,
    fee_rate_pct: float = 0.0,
    slippage_pct: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """模拟全仓交易，返回 (带净值的 df, 交易明细 df)。"""
    df = df.copy()
    cash = initial_capital
    shares = 0.0
    equity_list: list[float] = []
    trades: list[dict] = []
    entry_price = 0.0
    total_costs = 0.0

    fee_rate = fee_rate_pct / 100.0
    slippage_rate = slippage_pct / 100.0

    for idx, row in df.iterrows():
        price = row["Close"]

        if row["Action"] == "buy" and shares == 0:
            buy_price = price * (1 + slippage_rate)
            gross_shares = cash / buy_price if buy_price > 0 else 0.0
            fee = gross_shares * buy_price * fee_rate
            if fee > cash:
                fee = cash
            net_cash_for_shares = cash - fee
            shares = net_cash_for_shares / buy_price if buy_price > 0 else 0.0
            entry_price = buy_price
            cash = 0.0
            total_costs += fee
            trades.append(
                {
                    "日期": idx,
                    "操作": "买入",
                    "价格": buy_price,
                    "数量": shares,
                    "手续费": fee,
                    "盈亏": None,
                    "盈亏率(%)": None,
                }
            )

        elif row["Action"] == "sell" and shares > 0:
            sell_price = price * (1 - slippage_rate)
            gross_value = shares * sell_price
            fee = gross_value * fee_rate
            cash = gross_value - fee
            pnl = (sell_price - entry_price) * shares - fee
            pnl_pct = (sell_price / entry_price - 1) * 100 if entry_price > 0 else 0.0
            total_costs += fee
            trades.append(
                {
                    "日期": idx,
                    "操作": "卖出",
                    "价格": sell_price,
                    "数量": shares,
                    "手续费": fee,
                    "盈亏": pnl,
                    "盈亏率(%)": pnl_pct,
                }
            )
            shares = 0.0

        equity = cash + shares * price
        equity_list.append(equity)

    df["Equity"] = equity_list
    df["Benchmark"] = initial_capital * (df["Close"] / df["Close"].iloc[0])

    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df.attrs["total_costs"] = float(trades_df["手续费"].sum())
    else:
        trades_df.attrs["total_costs"] = total_costs
    return df, trades_df


def compute_metrics(
    df: pd.DataFrame, trades_df: pd.DataFrame, initial_capital: float, risk_free_pct: float
) -> dict:
    """计算绩效指标。"""
    equity = df["Equity"]
    total_return = (equity.iloc[-1] / initial_capital - 1) * 100

    trading_days = len(df)
    years = trading_days / 252
    annual_return = ((equity.iloc[-1] / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0.0

    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_drawdown = drawdown.min() * 100

    daily_returns = equity.pct_change().dropna()
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        excess = daily_returns.mean() - (risk_free_pct / 100) / 252
        sharpe = (excess / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

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
        "交易次数": num_trades,
        "胜率(%)": win_rate,
        "总交易成本": total_costs,
    }
