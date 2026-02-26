import math

import pandas as pd

from core.backtest import calculate_signals, compute_metrics, simulate_trades


def test_calculate_signals_generates_buy_and_sell():
    idx = pd.date_range("2024-01-01", periods=8, freq="D")
    df = pd.DataFrame({"Close": [10, 9, 8, 9, 10, 9, 8, 7]}, index=idx)

    out = calculate_signals(df, short_window=2, long_window=3)

    assert (out["Action"] == "buy").any()
    assert (out["Action"] == "sell").any()


def test_simulate_trades_and_metrics_basic_flow():
    idx = pd.date_range("2024-01-01", periods=6, freq="D")
    df = pd.DataFrame(
        {
            "Close": [10, 10, 12, 12, 11, 11],
            "Action": ["hold", "buy", "hold", "sell", "hold", "hold"],
        },
        index=idx,
    )

    result_df, trades_df = simulate_trades(df, initial_capital=1000)

    assert "Equity" in result_df.columns
    assert "Benchmark" in result_df.columns
    assert len(trades_df) == 2
    assert trades_df.iloc[0]["操作"] == "买入"
    assert trades_df.iloc[1]["操作"] == "卖出"

    metrics = compute_metrics(result_df, trades_df, initial_capital=1000, risk_free_pct=0)
    assert "总回报率(%)" in metrics
    assert "最大回撤(%)" in metrics
    assert metrics["交易次数"] == 1
    assert math.isclose(metrics["胜率(%)"], 100.0, rel_tol=1e-9)
