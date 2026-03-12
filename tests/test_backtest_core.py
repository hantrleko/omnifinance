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

    result_df, trades_df = simulate_trades(df, initial_capital=1000, fee_rate_pct=0.1, slippage_pct=0.1)

    assert "Equity" in result_df.columns
    assert "Benchmark" in result_df.columns
    assert len(trades_df) == 2
    assert trades_df.iloc[0]["操作"] == "买入"
    assert trades_df.iloc[1]["操作"] == "卖出"
    assert "手续费" in trades_df.columns

    metrics = compute_metrics(result_df, trades_df, initial_capital=1000, risk_free_pct=0)
    assert "总回报率(%)" in metrics
    assert "最大回撤(%)" in metrics
    assert metrics["交易次数"] == 1
    assert metrics["总交易成本"] > 0
    assert metrics["胜率(%)"] <= 100.0
    # v1.4: new metrics
    assert "索提诺比率" in metrics
    assert "卡玛比率" in metrics
    assert isinstance(metrics["索提诺比率"], float)
    assert isinstance(metrics["卡玛比率"], float)


def test_no_trades_zero_win_rate():
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"Close": [10, 11, 12, 13, 14], "Action": ["hold"] * 5},
        index=idx,
    )
    result_df, trades_df = simulate_trades(df, initial_capital=1000)
    metrics = compute_metrics(result_df, trades_df, initial_capital=1000, risk_free_pct=0)
    assert metrics["交易次数"] == 0
    assert metrics["胜率(%)"] == 0.0
    assert metrics["夏普比率"] == 0.0 or isinstance(metrics["夏普比率"], float)


def test_vectorised_same_result_as_before():
    """Verify vectorised simulate_trades produces correct equity curve."""
    idx = pd.date_range("2024-01-01", periods=4, freq="D")
    df = pd.DataFrame(
        {"Close": [100, 100, 200, 200], "Action": ["hold", "buy", "hold", "sell"]},
        index=idx,
    )
    result_df, trades_df = simulate_trades(df, initial_capital=1000, fee_rate_pct=0, slippage_pct=0)
    # Bought at 100 with 1000 → 10 shares; sold at 200 → 2000
    final_equity = result_df["Equity"].iloc[-1]
    assert abs(final_equity - 2000.0) < 1.0  # tolerance for rounding
