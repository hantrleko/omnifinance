"""多策略回测器 (Multi-Strategy Backtester)

支持 MA 交叉 / RSI / MACD / 布林带 四种策略，全仓模拟，Plotly 可视化，Streamlit 前端。
"""

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

from core.backtest import STRATEGY_NAMES, apply_strategy, simulate_trades, compute_metrics
from core.currency import currency_selector, fmt
from core.storage import scheme_manager_ui

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="策略回测器", page_icon="📈", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .time-badge {
      display: inline-block; background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color);
      border-radius: 6px; padding: 4px 12px; font-size: 13px; color: #aaa;
  }
</style>
""", unsafe_allow_html=True)

st.title("📈 策略回测器")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("⚙️ 回测参数")

currency_selector()

strategy = st.sidebar.selectbox("策略选择", STRATEGY_NAMES)

ticker = st.sidebar.text_input("标的代码", value="AAPL", help="美股 AAPL / 港股 0700.HK / 加密 BTC-USD")
col_date1, col_date2 = st.sidebar.columns(2)
start_date = col_date1.date_input("起始日期", value=date.today() - timedelta(days=5 * 365))
end_date = col_date2.date_input("结束日期", value=date.today())

# ── 策略参数 ──────────────────────────────────────────────
st.sidebar.subheader("📐 策略参数")

strategy_params: dict = {}

if strategy == "MA 交叉":
    sma_short = st.sidebar.slider("短期 SMA 天数", 5, 200, 50)
    sma_long = st.sidebar.slider("长期 SMA 天数", 50, 500, 200)
    if sma_short >= sma_long:
        st.sidebar.error("短期 SMA 必须小于长期 SMA")
        st.stop()
    strategy_params = {"short_window": sma_short, "long_window": sma_long}

elif strategy == "RSI":
    rsi_period = st.sidebar.slider("RSI 周期", 5, 50, 14)
    rsi_oversold = st.sidebar.slider("超卖阈值", 10, 40, 30)
    rsi_overbought = st.sidebar.slider("超买阈值", 60, 90, 70)
    strategy_params = {"period": rsi_period, "oversold": rsi_oversold, "overbought": rsi_overbought}

elif strategy == "MACD":
    macd_fast = st.sidebar.slider("快线周期", 5, 50, 12)
    macd_slow = st.sidebar.slider("慢线周期", 10, 100, 26)
    macd_signal = st.sidebar.slider("信号线周期", 5, 20, 9)
    strategy_params = {"fast": macd_fast, "slow": macd_slow, "signal_period": macd_signal}

elif strategy == "布林带":
    bb_period = st.sidebar.slider("布林带周期", 5, 100, 20)
    bb_std = st.sidebar.slider("标准差倍数", 1.0, 3.0, 2.0, step=0.1)
    strategy_params = {"period": bb_period, "num_std": bb_std}

initial_capital = st.sidebar.number_input("初始资金", min_value=1000.0, value=100000.0, step=10000.0, format="%.0f")
risk_free_rate = st.sidebar.number_input("无风险利率（%）", min_value=0.0, max_value=20.0, value=2.0, step=0.1)
fee_rate = st.sidebar.number_input("单边手续费（%）", min_value=0.0, max_value=2.0, value=0.05, step=0.01)
slippage_rate = st.sidebar.number_input("单边滑点（%）", min_value=0.0, max_value=2.0, value=0.03, step=0.01)

# ── 方案管理 ──────────────────────────────────────────────
current_params = {
    "strategy": strategy,
    "ticker": ticker,
    "initial_capital": initial_capital,
    "risk_free_rate": risk_free_rate,
    "fee_rate": fee_rate,
    "slippage_rate": slippage_rate,
    **strategy_params,
}
loaded = scheme_manager_ui("backtest", current_params)

st.sidebar.divider()
st.sidebar.caption("数据来源：Yahoo Finance (yfinance)")
st.sidebar.caption("免责声明：仅供学习研究，不构成投资建议。")
st.sidebar.caption("手续费/滑点说明：均为单边百分比，买入与卖出各计一次。")


# ══════════════════════════════════════════════════════════
#  核心函数
# ══════════════════════════════════════════════════════════

def get_data(ticker: str, start: date, end: date) -> pd.DataFrame | None:
    """从 yfinance 下载日线 OHLCV 数据。"""
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            return None
        # yfinance 可能返回 MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  数据加载
# ══════════════════════════════════════════════════════════

st.markdown("---")

data = None
with st.spinner(f"正在获取 {ticker} 数据…"):
    data = get_data(ticker.strip().upper(), start_date, end_date)

if data is not None and not data.empty:
    st.success(f"✅ 已加载 **{ticker.upper()}** | {data.index[0].date()} → {data.index[-1].date()} | 共 {len(data)} 个交易日")
else:
    st.warning(f"⚠️ 无法从 yfinance 获取 {ticker} 数据，请上传本地 CSV 文件。")
    uploaded = st.file_uploader("上传 CSV（列：Date, Open, High, Low, Close, Volume）", type=["csv"])
    if uploaded is not None:
        try:
            data = pd.read_csv(uploaded, parse_dates=["Date"], index_col="Date")
            data.sort_index(inplace=True)
            st.success(f"✅ 已加载上传数据 | {data.index[0].date()} → {data.index[-1].date()} | 共 {len(data)} 行")
        except Exception as e:
            st.error(f"CSV 解析失败：{e}")
            st.stop()
    else:
        st.stop()

# ══════════════════════════════════════════════════════════
#  计算信号 & 模拟交易
# ══════════════════════════════════════════════════════════

sig_df = apply_strategy(data, strategy, strategy_params)
result_df, trades_df = simulate_trades(sig_df, initial_capital, fee_rate, slippage_rate)
metrics = compute_metrics(result_df, trades_df, initial_capital, risk_free_rate)

# ── 绩效卡片 ──────────────────────────────────────────────
st.subheader("🏆 绩效概览")

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("总回报率", f"{metrics['总回报率(%)']:+.2f}%")
c2.metric("年化回报", f"{metrics['年化回报(%)']:+.2f}%")
c3.metric("最大回撤", f"{metrics['最大回撤(%)']:.2f}%")
c4.metric("夏普比率", f"{metrics['夏普比率']:.2f}")
c5.metric("交易次数", f"{metrics['交易次数']}")
c6.metric("胜率", f"{metrics['胜率(%)']:.1f}%")
c7.metric("总交易成本", fmt(metrics['总交易成本']))

if metrics["总回报率(%)"] >= 0:
    st.success(f"结论：在当前参数下，策略净值跑赢初始资金，期间总交易成本约 {fmt(metrics['总交易成本'])}。")
else:
    st.warning("结论：在当前参数下，策略回报为负；可尝试调整策略参数或降低交易成本参数。")

# ── 图表公共配置 ──────────────────────────────────────────
LAYOUT_DARK = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict()),
    margin=dict(t=30, b=40),
    hovermode="x unified",
)

# ── 价格 + 策略指标 + 信号图 ──────────────────────────────
st.subheader(f"📊 价格 & {strategy} 信号")

# 买卖信号散点
buys = result_df[result_df["Action"] == "buy"]
sells = result_df[result_df["Action"] == "sell"]

if strategy in ("RSI", "MACD"):
    # 带子图的布局
    fig_price = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        row_heights=[0.7, 0.3],
        subplot_titles=["价格 & 信号", strategy],
    )

    # 主图 - 价格
    fig_price.add_trace(go.Scatter(
        x=result_df.index, y=result_df["Close"],
        mode="lines", name="收盘价",
        line=dict(width=1.5, color="#888"),
        hovertemplate="%{x|%Y-%m-%d}<br>收盘价: %{y:,.2f}<extra></extra>",
    ), row=1, col=1)

    if not buys.empty:
        fig_price.add_trace(go.Scatter(
            x=buys.index, y=buys["Close"],
            mode="markers", name="买入",
            marker=dict(symbol="triangle-up", size=12, color="#00c853", line=dict(width=1, color="#fff")),
            hovertemplate="%{x|%Y-%m-%d}<br>买入: %{y:,.2f}<extra></extra>",
        ), row=1, col=1)
    if not sells.empty:
        fig_price.add_trace(go.Scatter(
            x=sells.index, y=sells["Close"],
            mode="markers", name="卖出",
            marker=dict(symbol="triangle-down", size=12, color="#ff1744", line=dict(width=1, color="#fff")),
            hovertemplate="%{x|%Y-%m-%d}<br>卖出: %{y:,.2f}<extra></extra>",
        ), row=1, col=1)

    # 子图 - 指标
    if strategy == "RSI":
        fig_price.add_trace(go.Scatter(
            x=result_df.index, y=result_df["RSI"],
            mode="lines", name="RSI",
            line=dict(width=2, color="#AB63FA"),
        ), row=2, col=1)
        fig_price.add_hline(y=strategy_params["oversold"], line_dash="dash", line_color="#00c853",
                            annotation_text=f"超卖 {strategy_params['oversold']}", row=2, col=1)
        fig_price.add_hline(y=strategy_params["overbought"], line_dash="dash", line_color="#ff1744",
                            annotation_text=f"超买 {strategy_params['overbought']}", row=2, col=1)
        fig_price.update_yaxes(title_text="RSI", row=2, col=1)

    elif strategy == "MACD":
        fig_price.add_trace(go.Scatter(
            x=result_df.index, y=result_df["MACD"],
            mode="lines", name="MACD",
            line=dict(width=2, color="#636EFA"),
        ), row=2, col=1)
        fig_price.add_trace(go.Scatter(
            x=result_df.index, y=result_df["MACD_Signal"],
            mode="lines", name="Signal",
            line=dict(width=2, color="#EF553B"),
        ), row=2, col=1)
        colors = ["#00c853" if v >= 0 else "#ff1744" for v in result_df["MACD_Hist"]]
        fig_price.add_trace(go.Bar(
            x=result_df.index, y=result_df["MACD_Hist"],
            name="Histogram",
            marker_color=colors,
            opacity=0.6,
        ), row=2, col=1)
        fig_price.update_yaxes(title_text="MACD", row=2, col=1)

    fig_price.update_layout(
        **LAYOUT_DARK,
        height=700,
        xaxis2_title="日期",
        yaxis_title="价格",
        yaxis_tickformat=",",
    )

else:
    # MA 交叉 / 布林带 — 单图布局
    fig_price = go.Figure()

    fig_price.add_trace(go.Scatter(
        x=result_df.index, y=result_df["Close"],
        mode="lines", name="收盘价",
        line=dict(width=1.5, color="#888"),
        hovertemplate="%{x|%Y-%m-%d}<br>收盘价: %{y:,.2f}<extra></extra>",
    ))

    if strategy == "MA 交叉":
        fig_price.add_trace(go.Scatter(
            x=result_df.index, y=result_df["SMA_Short"],
            mode="lines", name=f"SMA {strategy_params['short_window']}",
            line=dict(width=2, color="#636EFA"),
        ))
        fig_price.add_trace(go.Scatter(
            x=result_df.index, y=result_df["SMA_Long"],
            mode="lines", name=f"SMA {strategy_params['long_window']}",
            line=dict(width=2, color="#EF553B"),
        ))

    elif strategy == "布林带":
        fig_price.add_trace(go.Scatter(
            x=result_df.index, y=result_df["BB_Upper"],
            mode="lines", name="上轨",
            line=dict(width=1.5, color="#EF553B", dash="dash"),
        ))
        fig_price.add_trace(go.Scatter(
            x=result_df.index, y=result_df["BB_Mid"],
            mode="lines", name="中轨",
            line=dict(width=2, color="#636EFA"),
        ))
        fig_price.add_trace(go.Scatter(
            x=result_df.index, y=result_df["BB_Lower"],
            mode="lines", name="下轨",
            line=dict(width=1.5, color="#00CC96", dash="dash"),
            fill="tonexty",
            fillcolor="rgba(99,110,250,0.08)",
        ))

    if not buys.empty:
        fig_price.add_trace(go.Scatter(
            x=buys.index, y=buys["Close"],
            mode="markers", name="买入",
            marker=dict(symbol="triangle-up", size=12, color="#00c853", line=dict(width=1, color="#fff")),
            hovertemplate="%{x|%Y-%m-%d}<br>买入: %{y:,.2f}<extra></extra>",
        ))
    if not sells.empty:
        fig_price.add_trace(go.Scatter(
            x=sells.index, y=sells["Close"],
            mode="markers", name="卖出",
            marker=dict(symbol="triangle-down", size=12, color="#ff1744", line=dict(width=1, color="#fff")),
            hovertemplate="%{x|%Y-%m-%d}<br>卖出: %{y:,.2f}<extra></extra>",
        ))

    fig_price.update_layout(
        **LAYOUT_DARK,
        xaxis_title="日期",
        yaxis_title="价格",
        yaxis_tickformat=",",
    )

st.plotly_chart(fig_price, use_container_width=True)

# ── 股权曲线 vs 基准 ─────────────────────────────────────
st.subheader("💰 股权曲线 vs 买入持有基准")

fig_equity = go.Figure()
fig_equity.add_trace(go.Scatter(
    x=result_df.index, y=result_df["Equity"],
    mode="lines", name="策略净值",
    line=dict(width=2.5, color="#00CC96"),
    hovertemplate="%{x|%Y-%m-%d}<br>策略: " + fmt(0).replace("0.00", "") + "%{y:,.0f}<extra></extra>",
))
fig_equity.add_trace(go.Scatter(
    x=result_df.index, y=result_df["Benchmark"],
    mode="lines", name="买入持有",
    line=dict(width=2, dash="dash", color="#636EFA"),
    hovertemplate="%{x|%Y-%m-%d}<br>持有: " + fmt(0).replace("0.00", "") + "%{y:,.0f}<extra></extra>",
))

# 回撤填充区域
cummax = result_df["Equity"].cummax()
fig_equity.add_trace(go.Scatter(
    x=result_df.index, y=cummax,
    mode="lines", name="历史最高",
    line=dict(width=0),
    showlegend=False,
    hoverinfo="skip",
))
fig_equity.add_trace(go.Scatter(
    x=result_df.index, y=result_df["Equity"],
    mode="lines", name="回撤区域",
    line=dict(width=0),
    fill="tonexty",
    fillcolor="rgba(255,23,68,0.15)",
    showlegend=False,
    hoverinfo="skip",
))

fig_equity.update_layout(
    **LAYOUT_DARK,
    xaxis_title="日期",
    yaxis_title="资产净值",
    yaxis_tickformat=",",
)
st.plotly_chart(fig_equity, use_container_width=True)

# ── 策略对比 ──────────────────────────────────────────────
with st.expander("📊 策略对比"):
    DEFAULT_PARAMS = {
        "MA 交叉": {"short_window": 50, "long_window": 200},
        "RSI": {"period": 14, "oversold": 30, "overbought": 70},
        "MACD": {"fast": 12, "slow": 26, "signal_period": 9},
        "布林带": {"period": 20, "num_std": 2.0},
    }

    comparison_rows = []
    for s_name in STRATEGY_NAMES:
        s_params = DEFAULT_PARAMS[s_name]
        try:
            s_sig = apply_strategy(data, s_name, s_params)
            s_result, s_trades = simulate_trades(s_sig, initial_capital, fee_rate, slippage_rate)
            s_metrics = compute_metrics(s_result, s_trades, initial_capital, risk_free_rate)
            comparison_rows.append({
                "策略": s_name,
                "总回报率(%)": round(s_metrics["总回报率(%)"], 2),
                "年化回报(%)": round(s_metrics["年化回报(%)"], 2),
                "最大回撤(%)": round(s_metrics["最大回撤(%)"], 2),
                "夏普比率": round(s_metrics["夏普比率"], 2),
                "交易次数": s_metrics["交易次数"],
                "胜率(%)": round(s_metrics["胜率(%)"], 1),
            })
        except Exception:
            comparison_rows.append({
                "策略": s_name,
                "总回报率(%)": None,
                "年化回报(%)": None,
                "最大回撤(%)": None,
                "夏普比率": None,
                "交易次数": None,
                "胜率(%)": None,
            })

    comparison_df = pd.DataFrame(comparison_rows)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

# ── 交易明细 ──────────────────────────────────────────────
st.subheader("📋 交易明细")

if trades_df.empty:
    st.info("当前参数下未产生任何交易信号。请尝试调整策略参数或日期范围。")
else:
    display_trades = trades_df.copy()
    display_trades["日期"] = display_trades["日期"].dt.strftime("%Y-%m-%d")
    display_trades["价格"] = display_trades["价格"].apply(lambda v: f"{v:,.2f}")
    display_trades["数量"] = display_trades["数量"].apply(lambda v: f"{v:,.4f}")
    if "手续费" in display_trades.columns:
        display_trades["手续费"] = display_trades["手续费"].apply(lambda v: fmt(v))
    display_trades["盈亏"] = display_trades["盈亏"].apply(lambda v: fmt(v) if pd.notna(v) else "—")
    display_trades["盈亏率(%)"] = display_trades["盈亏率(%)"].apply(lambda v: f"{v:+.2f}%" if pd.notna(v) else "—")

    st.dataframe(display_trades, use_container_width=True, hide_index=True)

    # 导出 CSV
    csv_out = trades_df.copy()
    csv_out["日期"] = csv_out["日期"].dt.strftime("%Y-%m-%d")
    st.download_button(
        "📥 导出交易明细 CSV",
        data=csv_out.to_csv(index=False, encoding="utf-8-sig"),
        file_name=f"{ticker}_trades.csv",
        mime="text/csv",
    )

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("策略回测器 | 数据来源：Yahoo Finance | 运行：`streamlit run app.py`")
