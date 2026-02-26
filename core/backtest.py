"""Core quantitative backtesting functions for MA crossover strategy."""

from __future__ import annotations

import numpy as np
import pandas as pd


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
