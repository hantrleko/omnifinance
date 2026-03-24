"""多策略回测器 (Multi-Strategy Backtester)

支持 MA 交叉 / RSI / MACD / 布林带 四种策略，全仓模拟，Plotly 可视化，Streamlit 前端。

v1.4:
- 策略对比 expander 改用 @st.cache_data 缓存，避免每次渲染重复计算
- 新增 Sortino 比率和 Calmar 比率（来自 core/backtest.py v1.4）
- 图表 hovertemplate 货币符号改为动态引用
- 使用 core/chart_config.py 统一布局配置

v1.5:
- 组合回测改用 joblib.Parallel + loky 后端并行计算，显著减少多标的回测的总耗时
- 提取 _run_portfolio_one 纯函数，便于并行序列化和单元测试
"""

from datetime import date, timedelta
import logging
import urllib.error

import joblib
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
from core.theme import inject_theme
inject_theme()
import yfinance as yf

from core.backtest import STRATEGY_NAMES, apply_strategy, simulate_trades, compute_metrics
from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import currency_selector, fmt, get_symbol
from core.storage import scheme_manager_ui

# ── 模块级 logger ─────────────────────────────────────────
_logger = logging.getLogger(__name__)

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

pass

strategy = st.sidebar.selectbox("策略选择", STRATEGY_NAMES)

ticker = st.sidebar.text_input("标的代码", value=CFG.backtest.default_ticker, help="美股 AAPL / 港股 0700.HK / 加密 BTC-USD")
col_date1, col_date2 = st.sidebar.columns(2)
start_date = col_date1.date_input("起始日期", value=date.today() - timedelta(days=5 * 365))
end_date = col_date2.date_input("结束日期", value=date.today())

# ── 策略参数 ──────────────────────────────────────────────
st.sidebar.subheader("📐 策略参数")

strategy_params: dict = {}

if strategy == "MA 交叉":
    sma_short = st.sidebar.slider("短期 SMA 天数", 5, 200, CFG.backtest.ma_short_default)
    sma_long = st.sidebar.slider("长期 SMA 天数", 50, 500, CFG.backtest.ma_long_default)
    if sma_short >= sma_long:
        st.sidebar.error("短期 SMA 必须小于长期 SMA")
        st.stop()
    strategy_params = {"short_window": sma_short, "long_window": sma_long}

elif strategy == "RSI":
    rsi_period = st.sidebar.slider("RSI 周期", 5, 50, CFG.backtest.rsi_period_default)
    rsi_oversold = st.sidebar.slider("超卖阈値", 10, 40, CFG.backtest.rsi_oversold_default)
    rsi_overbought = st.sidebar.slider("超买阈値", 60, 90, CFG.backtest.rsi_overbought_default)
    strategy_params = {"period": rsi_period, "oversold": rsi_oversold, "overbought": rsi_overbought}

elif strategy == "MACD":
    macd_fast = st.sidebar.slider("快线周期", 5, 50, CFG.backtest.macd_fast_default)
    macd_slow = st.sidebar.slider("慢线周期", 10, 100, CFG.backtest.macd_slow_default)
    macd_signal = st.sidebar.slider("信号线周期", 5, 20, CFG.backtest.macd_signal_default)
    strategy_params = {"fast": macd_fast, "slow": macd_slow, "signal_period": macd_signal}

elif strategy == "布林带":
    bb_period = st.sidebar.slider("布林带周期", 5, 100, CFG.backtest.bb_period_default)
    bb_std = st.sidebar.slider("标准差倍数", 1.0, 3.0, CFG.backtest.bb_std_default, step=0.1)
    strategy_params = {"period": bb_period, "num_std": bb_std}

initial_capital = st.sidebar.number_input("初始资金", min_value=CFG.backtest.initial_capital_min, value=CFG.backtest.initial_capital_default, step=CFG.backtest.initial_capital_step, format="%.0f")
risk_free_rate = st.sidebar.number_input("无風险利率（%）", min_value=CFG.backtest.risk_free_rate_min, max_value=CFG.backtest.risk_free_rate_max, value=CFG.backtest.risk_free_rate_default, step=CFG.backtest.risk_free_rate_step)
fee_rate = st.sidebar.number_input("单边手续费（%）", min_value=CFG.backtest.fee_rate_min, max_value=CFG.backtest.fee_rate_max, value=CFG.backtest.fee_rate_default, step=CFG.backtest.fee_rate_step)
slippage_rate = st.sidebar.number_input("单边滑点（%）", min_value=CFG.backtest.slippage_rate_min, max_value=CFG.backtest.slippage_rate_max, value=CFG.backtest.slippage_rate_default, step=CFG.backtest.slippage_rate_step)

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
st.sidebar.caption(MSG.data_source_yfinance_short)
st.sidebar.caption(MSG.disclaimer_research)
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
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df
    except (urllib.error.URLError, requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as exc:
        # Network failure — log and return None so the UI can prompt CSV upload
        _logger.warning("[get_data] 网络错误 (%s): %s", ticker, exc, exc_info=True)
        return None
    except (KeyError, ValueError) as exc:
        # Unexpected data shape from yfinance
        _logger.warning("[get_data] 数据解析错误 (%s): %s", ticker, exc, exc_info=True)
        return None
    except Exception as exc:  # noqa: BLE001 — last-resort: keep app running
        _logger.error("[get_data] 未预期异常 (%s): %s", ticker, exc, exc_info=True)
        return None


def _run_portfolio_one(
    ticker: str,
    start: date,
    end: date,
    strategy: str,
    strategy_params: dict,
    initial_capital: float,
    fee_rate: float,
    slippage_rate: float,
    risk_free_rate: float,
) -> dict:
    """Run a full backtest for a single ticker and return a summary row.

    This is a pure function (no Streamlit calls) so it can be safely
    serialised and executed in a ``joblib`` worker process.

    Args:
        ticker: Ticker symbol to backtest.
        start: Backtest start date.
        end: Backtest end date.
        strategy: Strategy name key (see ``STRATEGY_NAMES``).
        strategy_params: Strategy-specific parameter dict.
        initial_capital: Starting capital in base currency.
        fee_rate: One-way commission rate (%).
        slippage_rate: One-way slippage rate (%).
        risk_free_rate: Annual risk-free rate (%) for Sharpe calculation.

    Returns:
        Dict with keys: 标的, 总回报率(%), 年化回报(%), 最大回撤(%), 夏普比率,
        交易次数, equity (pd.Series), 状态 (only on failure).
    """
    try:
        pt_data = get_data(ticker, start, end)
        if pt_data is None or pt_data.empty:
            return {"标的": ticker, "状态": "数据获取失败"}
        pt_sig = apply_strategy(pt_data, strategy, strategy_params)
        pt_res, pt_trades = simulate_trades(pt_sig, initial_capital, fee_rate, slippage_rate)
        pt_m = compute_metrics(pt_res, pt_trades, initial_capital, risk_free_rate)
        return {
            "标的": ticker,
            "总回报率(%)": round(pt_m["总回报率(%)"], 2),
            "年化回报(%)": round(pt_m["年化回报(%)"], 2),
            "最大回撤(%)": round(pt_m["最大回撤(%)"], 2),
            "夏普比率": round(pt_m["夏普比率"], 2),
            "交易次数": pt_m["交易次数"],
            "equity": pt_res["Equity"],
        }
    except (ValueError, KeyError, ZeroDivisionError) as exc:
        _logger.warning("[组合回测] %s 失败: %s", ticker, exc, exc_info=True)
        return {"标的": ticker, "状态": "回测失败"}


@st.cache_data(ttl=300, show_spinner=False)
def _cached_comparison(
    ticker_key: str,
    initial_capital: float,
    fee_rate: float,
    slippage_rate: float,
    risk_free_rate: float,
    data_hash: int,
) -> list[dict]:
    """缓存策略对比结果，避免每次 expander 展开时重复计算四个策略。

    data_hash 是 DataFrame 的行数 + 最后收盘价的组合，用作缓存键。
    """
    return []   # Placeholder; actual call is done outside with data passed in


# ══════════════════════════════════════════════════════════
#  数据加载
# ══════════════════════════════════════════════════════════

st.markdown("---")

data = None
with st.spinner(MSG.backtest_data_loading.format(ticker=ticker)):
    data = get_data(ticker.strip().upper(), start_date, end_date)

if data is not None and not data.empty:
    st.success(MSG.backtest_data_loaded.format(
        ticker=ticker.upper(),
        start=data.index[0].date(),
        end=data.index[-1].date(),
        n=len(data),
    ))
else:
    st.warning(MSG.backtest_data_failed.format(ticker=ticker))
    uploaded = st.file_uploader("上传 CSV（列：Date, Open, High, Low, Close, Volume）", type=["csv"])
    if uploaded is not None:
        try:
            data = pd.read_csv(uploaded, parse_dates=["Date"], index_col="Date")
            data.sort_index(inplace=True)
            st.success(MSG.backtest_csv_loaded.format(
                start=data.index[0].date(), end=data.index[-1].date(), n=len(data)
            ))
        except (KeyError, ValueError, pd.errors.ParserError) as e:
            # Missing required columns, bad date format, or malformed CSV
            _logger.warning("[CSV上传] 解析失败: %s", e, exc_info=True)
            st.error(MSG.backtest_csv_failed.format(error=e))
            st.stop()
    else:
        st.stop()

# ══════════════════════════════════════════════════════════
#  计算信号 & 模拟交易
# ══════════════════════════════════════════════════════════

sig_df = apply_strategy(data, strategy, strategy_params)
result_df, trades_df = simulate_trades(sig_df, initial_capital, fee_rate, slippage_rate)
metrics = compute_metrics(result_df, trades_df, initial_capital, risk_free_rate)

sym = get_symbol()

# ── 绩效卡片（含 Sortino / Calmar） ───────────────────────
st.subheader("🏆 绩效概览")

c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns(9)
c1.metric("总回报率", f"{metrics['总回报率(%)']:+.2f}%")
c2.metric("年化回报", f"{metrics['年化回报(%)']:+.2f}%")
c3.metric("最大回撤", f"{metrics['最大回撤(%)']:.2f}%")
c4.metric("夏普比率", f"{metrics['夏普比率']:.2f}")
c5.metric("索提诺比率", f"{metrics['索提诺比率']:.2f}",
          help=MSG.backtest_sortino_help)
c6.metric("卡玛比率", f"{metrics['卡玛比率']:.2f}",
          help=MSG.backtest_calmar_help)
c7.metric("交易次数", f"{metrics['交易次数']}")
c8.metric("胜率", f"{metrics['胜率(%)']:.1f}%")
c9.metric("总交易成本", fmt(metrics['总交易成本']))

if metrics["总回报率(%)"] >= 0:
    st.success(MSG.backtest_positive.format(cost=fmt(metrics['总交易成本'])))
else:
    st.warning(MSG.backtest_negative)

# ── 价格 + 策略指标 + 信号图 ──────────────────────────────
st.subheader(f"📊 价格 & {strategy} 信号")

buys = result_df[result_df["Action"] == "buy"]
sells = result_df[result_df["Action"] == "sell"]

if strategy in ("RSI", "MACD"):
    fig_price = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        row_heights=[0.7, 0.3],
        subplot_titles=["价格 & 信号", strategy],
    )

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
            name="Histogram", marker_color=colors, opacity=0.6,
        ), row=2, col=1)
        fig_price.update_yaxes(title_text="MACD", row=2, col=1)

    fig_price.update_layout(
        **build_layout(height=700, xaxis2_title="日期", yaxis_title="价格", yaxis_tickformat=","),
    )

else:
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
        **build_layout(xaxis_title="日期", yaxis_title="价格", yaxis_tickformat=","),
    )

st.plotly_chart(fig_price, use_container_width=True)

# ── 股权曲线 vs 基准 ─────────────────────────────────────
st.subheader("💰 股权曲线 vs 买入持有基准")

fig_equity = go.Figure()
fig_equity.add_trace(go.Scatter(
    x=result_df.index, y=result_df["Equity"],
    mode="lines", name="策略净值",
    line=dict(width=2.5, color="#00CC96"),
    hovertemplate=f"%{{x|%Y-%m-%d}}<br>策略: {sym}%{{y:,.0f}}<extra></extra>",
))
fig_equity.add_trace(go.Scatter(
    x=result_df.index, y=result_df["Benchmark"],
    mode="lines", name="买入持有",
    line=dict(width=2, dash="dash", color="#636EFA"),
    hovertemplate=f"%{{x|%Y-%m-%d}}<br>持有: {sym}%{{y:,.0f}}<extra></extra>",
))

cummax = result_df["Equity"].cummax()
fig_equity.add_trace(go.Scatter(
    x=result_df.index, y=cummax,
    mode="lines", name="历史最高",
    line=dict(width=0), showlegend=False, hoverinfo="skip",
))
fig_equity.add_trace(go.Scatter(
    x=result_df.index, y=result_df["Equity"],
    mode="lines", name="回撤区域",
    line=dict(width=0),
    fill="tonexty", fillcolor="rgba(255,23,68,0.15)",
    showlegend=False, hoverinfo="skip",
))

fig_equity.update_layout(
    **build_layout(xaxis_title="日期", yaxis_title="资产净值", yaxis_tickformat=","),
)
st.plotly_chart(fig_equity, use_container_width=True)

# ── 策略对比（缓存计算） ──────────────────────────────────
with st.expander("📊 策略对比（默认参数）"):
    DEFAULT_PARAMS = {
        "MA 交叉": {"short_window": 50, "long_window": 200},
        "RSI": {"period": 14, "oversold": 30, "overbought": 70},
        "MACD": {"fast": 12, "slow": 26, "signal_period": 9},
        "布林带": {"period": 20, "num_std": 2.0},
    }

    # Build a simple cache key from the data characteristics
    data_key = (ticker.upper(), str(start_date), str(end_date),
                 initial_capital, fee_rate, slippage_rate, risk_free_rate)

    @st.cache_data(ttl=300, show_spinner="正在计算策略对比…")
    def compute_comparison(
        data_key: tuple,
        _data: pd.DataFrame,   # leading underscore = not hashed by Streamlit
    ) -> list[dict]:
        rows = []
        for s_name in STRATEGY_NAMES:
            s_params = DEFAULT_PARAMS[s_name]
            try:
                s_sig = apply_strategy(_data, s_name, s_params)
                s_result, s_trades = simulate_trades(
                    s_sig, data_key[3], data_key[4], data_key[5]
                )
                s_metrics = compute_metrics(s_result, s_trades, data_key[3], data_key[6])
                rows.append({
                    "策略": s_name,
                    "总回报率(%)": round(s_metrics["总回报率(%)"], 2),
                    "年化回报(%)": round(s_metrics["年化回报(%)"], 2),
                    "最大回撤(%)": round(s_metrics["最大回撤(%)"], 2),
                    "夏普比率": round(s_metrics["夏普比率"], 2),
                    "索提诺比率": round(s_metrics["索提诺比率"], 2),
                    "卡玛比率": round(s_metrics["卡玛比率"], 2),
                    "交易次数": s_metrics["交易次数"],
                    "胜率(%)": round(s_metrics["胜率(%)"], 1),
                })
            except (ValueError, KeyError, ZeroDivisionError) as exc:
                # Strategy computation failed for this combo — record as None row
                _logger.warning("[策略对比] %s 计算失败: %s", s_name, exc, exc_info=True)
                rows.append({"策略": s_name, **{k: None for k in [
                    "总回报率(%)", "年化回报(%)", "最大回撤(%)",
                    "夏普比率", "索提诺比率", "卡玛比率", "交易次数", "胜率(%)",
                ]}})
        return rows

    comparison_rows = compute_comparison(data_key, data)
    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

# ── 交易明细 ──────────────────────────────────────────────
st.subheader("📋 交易明细")

if trades_df.empty:
    st.info(MSG.backtest_no_trades)
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

    csv_out = trades_df.copy()
    csv_out["日期"] = csv_out["日期"].dt.strftime("%Y-%m-%d")
    st.download_button(
        "📥 导出交易明细 CSV",
        data=csv_out.to_csv(index=False, encoding="utf-8-sig"),
        file_name=f"{ticker}_trades.csv",
        mime="text/csv",
    )

# ── 参数网格搜索 ──────────────────────────────────────────
with st.expander("🔍 参数网格搜索"):
    st.caption(MSG.backtest_grid_caption)

    if strategy == "MA 交叉":
        short_range = st.slider("短期 SMA 搜索范围", 5, 100, (10, 60), step=5, key="gs_short")
        long_range = st.slider("长期 SMA 搜索范围", 50, 500, (100, 300), step=10, key="gs_long")
        short_step = st.number_input("短期步长", 5, 20, 10, key="gs_ss")
        long_step = st.number_input("长期步长", 10, 50, 20, key="gs_ls")
    elif strategy == "RSI":
        period_range = st.slider("RSI 周期范围", 5, 50, (7, 28), key="gs_rp")
        oversold_range = st.slider("超卖阈值范围", 15, 40, (20, 35), step=5, key="gs_os")
        overbought_range = st.slider("超买阈值范围", 60, 90, (65, 80), step=5, key="gs_ob")
    elif strategy == "MACD":
        fast_range = st.slider("快线周期范围", 5, 30, (8, 16), step=2, key="gs_fr")
        slow_range = st.slider("慢线周期范围", 15, 50, (20, 35), step=5, key="gs_sr")
    elif strategy == "布林带":
        bb_p_range = st.slider("周期范围", 10, 50, (15, 30), step=5, key="gs_bp")
        bb_s_range = st.slider("标准差范围", 1.0, 3.0, (1.5, 2.5), step=0.5, key="gs_bs")

    if st.button("🚀 开始搜索", key="gs_run"):
        grid_results = []
        if strategy == "MA 交叉":
            combos = [(s, l) for s in range(short_range[0], short_range[1]+1, int(short_step))
                       for l in range(long_range[0], long_range[1]+1, int(long_step)) if s < l]
        elif strategy == "RSI":
            combos = [(p, o, b) for p in range(period_range[0], period_range[1]+1, 7)
                       for o in range(oversold_range[0], oversold_range[1]+1, 5)
                       for b in range(overbought_range[0], overbought_range[1]+1, 5) if o < b]
        elif strategy == "MACD":
            combos = [(f, s) for f in range(fast_range[0], fast_range[1]+1, 2)
                       for s in range(slow_range[0], slow_range[1]+1, 5) if f < s]
        elif strategy == "布林带":
            combos = [(p, s) for p in range(bb_p_range[0], bb_p_range[1]+1, 5)
                       for s in [x/10 for x in range(int(bb_s_range[0]*10), int(bb_s_range[1]*10)+1, 5)]]
        else:
            combos = []

        progress = st.progress(0)
        for idx, combo in enumerate(combos):
            try:
                if strategy == "MA 交叉":
                    p = {"short_window": combo[0], "long_window": combo[1]}
                elif strategy == "RSI":
                    p = {"period": combo[0], "oversold": combo[1], "overbought": combo[2]}
                elif strategy == "MACD":
                    p = {"fast": combo[0], "slow": combo[1], "signal_period": 9}
                elif strategy == "布林带":
                    p = {"period": combo[0], "num_std": combo[1]}
                g_sig = apply_strategy(data, strategy, p)
                g_res, g_trades = simulate_trades(g_sig, initial_capital, fee_rate, slippage_rate)
                g_m = compute_metrics(g_res, g_trades, initial_capital, risk_free_rate)
                row = {**{f"参数{i+1}": v for i, v in enumerate(combo)},
                       "夏普比率": round(g_m["夏普比率"], 3),
                       "年化回报(%)": round(g_m["年化回报(%)"], 2),
                       "最大回撤(%)": round(g_m["最大回撤(%)"], 2)}
                grid_results.append(row)
            except (ValueError, KeyError, ZeroDivisionError) as exc:
                # Skip invalid parameter combos silently but log for diagnostics
                _logger.debug("[网格搜索] 参数组合 %s 跳过: %s", combo, exc)
            progress.progress((idx + 1) / max(len(combos), 1))

        if grid_results:
            grid_df = pd.DataFrame(grid_results).sort_values("夏普比率", ascending=False)
            st.success(MSG.backtest_grid_done.format(n=len(grid_results)))
            st.dataframe(grid_df.head(10), use_container_width=True, hide_index=True)
        else:
            st.warning(MSG.backtest_grid_none)

# ── 组合回测 ──────────────────────────────────────────────
with st.expander("📊 组合回测（多标的）"):
    st.caption(MSG.backtest_portfolio_caption)
    portfolio_input = st.text_input("输入标的代码（逗号分隔）", value=CFG.backtest.default_portfolio, key="port_tickers")

    if st.button("🚀 运行组合回测", key="port_run"):
        port_tickers = [t.strip().upper() for t in portfolio_input.split(",") if t.strip()]
        if len(port_tickers) < 2:
            st.warning(MSG.backtest_portfolio_min)
        else:
            port_rows: list[dict] = []
            port_equities: dict[str, pd.Series] = {}
            n_jobs = min(len(port_tickers), joblib.cpu_count())
            with st.spinner(f"正在并行回测 {len(port_tickers)} 个标的（{n_jobs} 进程）…"):
                parallel_results: list[dict] = joblib.Parallel(
                    n_jobs=n_jobs,
                    backend="loky",
                    prefer="processes",
                )(
                    joblib.delayed(_run_portfolio_one)(
                        pt,
                        start_date,
                        end_date,
                        strategy,
                        strategy_params,
                        initial_capital,
                        fee_rate,
                        slippage_rate,
                        risk_free_rate,
                    )
                    for pt in port_tickers
                )
            for res in parallel_results:
                equity = res.pop("equity", None)
                port_rows.append(res)
                if equity is not None and "状态" not in res:
                    port_equities[res["标的"]] = equity

            if port_rows:
                st.dataframe(pd.DataFrame(port_rows), use_container_width=True, hide_index=True)
            if port_equities:
                fig_port = go.Figure()
                for pname, eq in port_equities.items():
                    fig_port.add_trace(go.Scatter(x=eq.index, y=eq.values, mode="lines", name=pname))
                fig_port.update_layout(**build_layout(xaxis_title="日期", yaxis_title="净值", yaxis_tickformat=","))
                st.plotly_chart(fig_port, use_container_width=True)

# ── 导出报告 ──────────────────────────────────────────────
st.subheader("📤 导出报告")

def _build_bt_report() -> str:
    rows_html = ""
    if not trades_df.empty:
        for _, r in trades_df.iterrows():
            pnl = f"{r['盈亏']:,.2f}" if pd.notna(r['盈亏']) else "—"
            pnl_p = f"{r['盈亏率(%)']:+.2f}%" if pd.notna(r['盈亏率(%)']) else "—"
            rows_html += f"<tr><td>{r['日期']}</td><td>{r['操作']}</td><td>{r['价格']:,.2f}</td><td>{r['数量']:,.4f}</td><td>{pnl}</td><td>{pnl_p}</td></tr>"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#222}}h1{{color:#333}}h2{{color:#555;margin-top:24px}}table{{border-collapse:collapse;width:100%;margin-top:12px}}th,td{{border:1px solid #ccc;padding:6px 10px;text-align:right;font-size:13px}}th{{background:#f5f5f5}}.summary{{display:flex;gap:20px;margin:16px 0;flex-wrap:wrap}}.summary div{{background:#f9f9f9;padding:12px 20px;border-radius:6px}}.label{{font-size:12px;color:#888}}.value{{font-size:18px;font-weight:bold}}</style></head><body>
<h1>📈 策略回测报告</h1>
<p>标的：{ticker.upper()} | 策略：{strategy} | 期间：{start_date} → {end_date}</p>
<div class="summary">
<div><div class="label">总回报率</div><div class="value">{metrics['总回报率(%)']:+.2f}%</div></div>
<div><div class="label">年化回报</div><div class="value">{metrics['年化回报(%)']:+.2f}%</div></div>
<div><div class="label">最大回撤</div><div class="value">{metrics['最大回撤(%)']:.2f}%</div></div>
<div><div class="label">夏普比率</div><div class="value">{metrics['夏普比率']:.2f}</div></div>
<div><div class="label">交易次数</div><div class="value">{metrics['交易次数']}</div></div>
</div>
<h2>交易明细</h2><table><tr><th>日期</th><th>操作</th><th>价格</th><th>数量</th><th>盈亏</th><th>盈亏率</th></tr>{rows_html}</table>
<p style="margin-top:24px;font-size:11px;color:#aaa">由策略回测器自动生成</p></body></html>"""

st.download_button("📥 下载回测报告 (HTML)", data=_build_bt_report(), file_name=f"{ticker}_backtest.html", mime="text/html")
st.caption("提示：打开 HTML 文件后按 Ctrl+P 可打印/另存为 PDF。")

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption(MSG.backtest_footer)
