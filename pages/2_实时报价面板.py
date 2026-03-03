"""多标的实时股票 / 加密货币报价面板

使用 yfinance (fast_info) + ThreadPoolExecutor 并行获取数据，
streamlit-autorefresh 自动刷新，Streamlit 展示。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

from core.storage import save_scheme, load_scheme, list_schemes

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="实时报价面板", page_icon="📊", layout="wide")

# ── 预设标的 ──────────────────────────────────────────────
PRESETS: dict[str, list[str]] = {
    "美股": ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"],
    "港股": ["0700.HK", "9988.HK", "3690.HK"],
    "加密货币": ["BTC-USD", "ETH-USD", "SOL-USD"],
}
ALL_TICKERS = [t for group in PRESETS.values() for t in group]

# ── 自定义样式 ────────────────────────────────────────────
st.markdown("""
<style>
  .block-container { padding-top: 1.5rem; }
  .stMetric { background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 8px; padding: 12px; }
  div[data-testid="stMetricValue"] { font-size: 1.1rem; }
  .time-badge {
      display: inline-block; background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color);
      border-radius: 6px; padding: 4px 12px; font-size: 13px; color: #aaa;
  }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ───────────────────────────────────────────────
st.sidebar.header("📋 标的选择")

quick = st.sidebar.radio("快捷选择", ["自定义", "全选", "美股", "港股", "加密货币"], horizontal=True)
if quick == "全选":
    default_tickers = ALL_TICKERS
elif quick in PRESETS:
    default_tickers = PRESETS[quick]
else:
    default_tickers = ["AAPL", "TSLA", "BTC-USD"]

selected = st.sidebar.multiselect(
    "选择标的代码",
    options=ALL_TICKERS,
    default=default_tickers,
)

custom_input = st.sidebar.text_input("添加自定义代码（逗号分隔）", placeholder="如 AMZN, META")
if custom_input:
    extras = [s.strip().upper() for s in custom_input.split(",") if s.strip()]
    selected = list(dict.fromkeys(selected + extras))

refresh_interval = st.sidebar.slider("自动刷新间隔（秒）", 30, 300, 60, step=10)

# ── 关注列表持久化 ─────────────────────────────────────────
st.sidebar.divider()
st.sidebar.subheader("💾 关注列表管理")

wl_name = st.sidebar.text_input("列表名称", placeholder="如 我的美股组合", key="wl_name")
if st.sidebar.button("💾 保存当前列表", key="wl_save_btn"):
    if wl_name.strip() and selected:
        save_scheme("watchlist", wl_name.strip(), {"tickers": selected})
        st.sidebar.success(f"已保存「{wl_name.strip()}」")
        st.rerun()
    else:
        st.sidebar.warning("请输入名称并选择至少一个标的")

saved_wls = list_schemes("watchlist")
if saved_wls:
    wl_choice = st.sidebar.selectbox("已保存列表", saved_wls, key="wl_load_sel")
    if st.sidebar.button("📂 加载列表", key="wl_load_btn"):
        loaded_wl = load_scheme("watchlist", wl_choice)
        if loaded_wl and "tickers" in loaded_wl:
            st.session_state["wl_loaded"] = loaded_wl["tickers"]
            st.rerun()

# 如果刚加载了关注列表，覆盖 selected
if "wl_loaded" in st.session_state:
    selected = st.session_state.pop("wl_loaded")

st.sidebar.divider()
st.sidebar.caption("数据来源：Yahoo Finance（yfinance）")
st.sidebar.caption("提示：港股代码格式 0700.HK，加密货币 BTC-USD")

# ── 自动刷新（streamlit-autorefresh） ─────────────────────
st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")


# ── 数据获取（ThreadPoolExecutor 并行） ──────────────────
def _fetch_one(ticker_str: str) -> dict:
    """获取单个标的的报价，仅使用 fast_info。"""
    try:
        tk = yf.Ticker(ticker_str)
        fi = tk.fast_info

        current = getattr(fi, "last_price", None)
        prev_close = getattr(fi, "previous_close", None)
        day_high = getattr(fi, "day_high", None)
        day_low = getattr(fi, "day_low", None)
        volume = getattr(fi, "last_volume", None)

        change_pct = ((current / prev_close - 1) * 100) if current and prev_close else None

        return {
            "代码": ticker_str,
            "当前价格": current,
            "涨跌幅(%)": change_pct,
            "今日最高": day_high,
            "今日最低": day_low,
            "成交量": volume,
        }
    except Exception:
        return {
            "代码": ticker_str,
            "当前价格": None,
            "涨跌幅(%)": None,
            "今日最高": None,
            "今日最低": None,
            "成交量": None,
        }


@st.cache_data(ttl=25)
def fetch_quotes(tickers: tuple[str, ...]) -> pd.DataFrame:
    """使用线程池并行获取所有标的报价。"""
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures):
            ticker_str = futures[future]
            results[ticker_str] = future.result()

    # 按原始顺序排列
    rows = [results[t] for t in tickers]
    return pd.DataFrame(rows)


# ── 涨跌幅着色函数 ────────────────────────────────────────
def style_change(val):
    """为涨跌幅单元格设置红/绿色。"""
    if pd.isna(val):
        return ""
    if val > 0:
        return "color: #00c853; font-weight: 600"
    elif val < 0:
        return "color: #ff1744; font-weight: 600"
    return "color: #888"


def format_volume(val):
    """将成交量格式化为可读字符串。"""
    if pd.isna(val):
        return "—"
    v = int(val)
    if v >= 1_0000_0000:
        return f"{v / 1_0000_0000:.2f} 亿"
    if v >= 1_0000:
        return f"{v / 1_0000:.1f} 万"
    return f"{v:,}"


# ── 主界面 ───────────────────────────────────────────────
title_col, btn_col = st.columns([4, 1])
title_col.markdown("## 📊 实时报价面板")

if btn_col.button("🔄 手动刷新"):
    st.cache_data.clear()

now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(
    f"<span class='time-badge'>🕐 最后刷新：{now_str}</span>",
    unsafe_allow_html=True,
)

if not selected:
    st.warning("请在左侧面板中选择至少一个标的。")
    st.stop()

with st.spinner("正在获取行情数据…"):
    quotes_df = fetch_quotes(tuple(selected))

# ── 顶部指标卡片 ──────────────────────────────────────────
top_n = min(4, len(quotes_df))
cols = st.columns(top_n)
for i in range(top_n):
    row = quotes_df.iloc[i]
    price = f"{row['当前价格']:,.2f}" if pd.notna(row["当前价格"]) else "—"
    delta = f"{row['涨跌幅(%)']:.2f}%" if pd.notna(row["涨跌幅(%)"]) else None
    cols[i].metric(label=row["代码"], value=price, delta=delta)

st.markdown("---")

# ── 表格：st.dataframe + pandas Styler ───────────────────
display_df = quotes_df.copy()

# 格式化成交量为可读文本列
display_df["成交量"] = display_df["成交量"].apply(format_volume)

# 数值列格式
fmt_dict = {
    "当前价格": "{:,.2f}",
    "涨跌幅(%)": "{:+.2f}%",
    "今日最高": "{:,.2f}",
    "今日最低": "{:,.2f}",
}

styled = (
    display_df.style
    .format(fmt_dict, na_rep="—")
    .applymap(style_change, subset=["涨跌幅(%)"])
)

st.dataframe(
    styled,
    use_container_width=True,
    hide_index=True,
    height=(len(display_df) + 1) * 38 + 10,
)

# ── K线图 & 技术指标 ─────────────────────────────────────
st.markdown("---")
st.markdown("## 📈 K线图 & 技术指标")

kline_ticker = st.selectbox("选择标的", selected, key="kline_ticker")

if kline_ticker:
    with st.spinner(f"正在下载 {kline_ticker} 近6个月历史数据…"):
        hist = yf.download(kline_ticker, period="6mo", progress=False, auto_adjust=True)

    # 处理 MultiIndex 列（yfinance 返回多标的时为 MultiIndex）
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)

    if hist.empty:
        st.warning(f"未能获取 {kline_ticker} 的历史数据。")
    else:
        # 技术指标选项
        col_ma, col_vwap = st.columns(2)
        show_ma = col_ma.checkbox("显示均线（SMA 20 / SMA 60）", value=True, key="show_ma")
        has_volume = "Volume" in hist.columns and hist["Volume"].sum() > 0
        show_vwap = col_vwap.checkbox("显示 VWAP", value=False, key="show_vwap", disabled=not has_volume)

        # 构建子图：K线 + 成交量
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
        )

        # K线
        fig.add_trace(
            go.Candlestick(
                x=hist.index,
                open=hist["Open"], high=hist["High"],
                low=hist["Low"], close=hist["Close"],
                name="K线",
            ),
            row=1, col=1,
        )

        # MA 均线
        if show_ma:
            hist["SMA20"] = hist["Close"].rolling(window=20).mean()
            hist["SMA60"] = hist["Close"].rolling(window=60).mean()
            fig.add_trace(
                go.Scatter(x=hist.index, y=hist["SMA20"], mode="lines",
                           name="SMA 20", line=dict(width=1, color="#FFA726")),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(x=hist.index, y=hist["SMA60"], mode="lines",
                           name="SMA 60", line=dict(width=1, color="#42A5F5")),
                row=1, col=1,
            )

        # VWAP
        if show_vwap and has_volume:
            typical_price = (hist["High"] + hist["Low"] + hist["Close"]) / 3
            cum_tp_vol = (typical_price * hist["Volume"]).cumsum()
            cum_vol = hist["Volume"].cumsum()
            hist["VWAP"] = cum_tp_vol / cum_vol
            fig.add_trace(
                go.Scatter(x=hist.index, y=hist["VWAP"], mode="lines",
                           name="VWAP", line=dict(width=1, dash="dash", color="#AB47BC")),
                row=1, col=1,
            )

        # 成交量柱状图
        if has_volume:
            colors = [
                "#00c853" if c >= o else "#ff1744"
                for c, o in zip(hist["Close"], hist["Open"])
            ]
            fig.add_trace(
                go.Bar(x=hist.index, y=hist["Volume"], name="成交量",
                       marker_color=colors, opacity=0.6),
                row=2, col=1,
            )

        fig.update_layout(
            title=f"{kline_ticker} — 近6个月K线图",
            xaxis_rangeslider_visible=False,
            height=650,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_yaxes(title_text="价格", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption(f"自动刷新间隔：{refresh_interval} 秒 | 数据来源：Yahoo Finance | 运行命令：`streamlit run app.py`")
