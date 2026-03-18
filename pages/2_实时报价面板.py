"""多标的实时股票 / 加密货币报价面板

使用 yfinance (fast_info) + ThreadPoolExecutor 并行获取数据，
streamlit-autorefresh 自动刷新，Streamlit 展示。

v1.4:
- K 线图历史数据加入 @st.cache_data(ttl=300) 缓存，避免重复下载
- 报价失败加入分级错误提示（网络错误 / 代码不存在 / 限流）
- 货币符号改用动态引用
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

if "wl_loaded" in st.session_state:
    selected = st.session_state.pop("wl_loaded")

st.sidebar.divider()
st.sidebar.caption("数据来源：Yahoo Finance（yfinance）")
st.sidebar.caption("提示：港股代码格式 0700.HK，加密货币 BTC-USD")

# ── 自动刷新 ──────────────────────────────────────────────
st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")


# ── 数据获取（ThreadPoolExecutor 并行） ──────────────────

# Error category constants
_ERR_NETWORK = "network"
_ERR_NOTFOUND = "notfound"
_ERR_OK = "ok"


def _fetch_one(ticker_str: str) -> dict:
    """获取单个标的的报价，包含分级错误信息。"""
    base = {
        "代码": ticker_str,
        "当前价格": None,
        "涨跌幅(%)": None,
        "今日最高": None,
        "今日最低": None,
        "成交量": None,
        "_error": None,
    }
    try:
        tk = yf.Ticker(ticker_str)
        fi = tk.fast_info

        current = getattr(fi, "last_price", None)
        prev_close = getattr(fi, "previous_close", None)
        day_high = getattr(fi, "day_high", None)
        day_low = getattr(fi, "day_low", None)
        volume = getattr(fi, "last_volume", None)

        # Distinguish "symbol not found" from "got data"
        if current is None and prev_close is None:
            base["_error"] = _ERR_NOTFOUND
            return base

        change_pct = ((current / prev_close - 1) * 100) if current and prev_close else None
        return {
            **base,
            "当前价格": current,
            "涨跌幅(%)": change_pct,
            "今日最高": day_high,
            "今日最低": day_low,
            "成交量": volume,
            "_error": _ERR_OK,
        }
    except Exception as exc:
        err_str = str(exc).lower()
        if any(kw in err_str for kw in ("connection", "timeout", "network", "ssl", "read")):
            base["_error"] = _ERR_NETWORK
        else:
            base["_error"] = _ERR_NOTFOUND
        return base


@st.cache_data(ttl=25)
def fetch_quotes(tickers: tuple[str, ...]) -> pd.DataFrame:
    """使用线程池并行获取所有标的报价。"""
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures):
            ticker_str = futures[future]
            results[ticker_str] = future.result()
    rows = [results[t] for t in tickers]
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def fetch_kline_history(ticker_str: str, period: str = "6mo") -> pd.DataFrame:
    """下载 K 线历史数据，结果缓存 5 分钟，避免重复请求。"""
    try:
        hist = yf.download(ticker_str, period=period, progress=False, auto_adjust=True)
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)
        return hist
    except Exception:
        return pd.DataFrame()


# ── 涨跌幅着色函数 ────────────────────────────────────────
def style_change(val):
    if pd.isna(val):
        return ""
    if val > 0:
        return "color: #00c853; font-weight: 600"
    elif val < 0:
        return "color: #ff1744; font-weight: 600"
    return "color: #888"


def format_volume(val):
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

# ── Session 级缓存回退 ────────────────────────────────────
if "quote_cache" not in st.session_state:
    st.session_state["quote_cache"] = {}

cache = st.session_state["quote_cache"]
used_cache = False

for i, row in quotes_df.iterrows():
    ticker_code = row["代码"]
    if row["_error"] == _ERR_OK and pd.notna(row["当前价格"]):
        cache[ticker_code] = {
            "当前价格": row["当前价格"],
            "涨跌幅(%)": row["涨跌幅(%)"],
            "今日最高": row["今日最高"],
            "今日最低": row["今日最低"],
            "成交量": row["成交量"],
        }
    elif row["_error"] != _ERR_OK and ticker_code in cache:
        cached = cache[ticker_code]
        for col in ["当前价格", "涨跌幅(%)", "今日最高", "今日最低", "成交量"]:
            quotes_df.at[i, col] = cached[col]
        quotes_df.at[i, "_error"] = "cached"
        used_cache = True

# ── 分级错误提示 ──────────────────────────────────────────
network_errs = quotes_df[quotes_df["_error"] == _ERR_NETWORK]["代码"].tolist()
notfound_errs = quotes_df[quotes_df["_error"] == _ERR_NOTFOUND]["代码"].tolist()

if network_errs:
    st.warning(f"🌐 网络连接异常，以下标的数据获取失败（可能为限流或网络问题）：{', '.join(network_errs)}")
if notfound_errs:
    st.error(f"❌ 以下标的代码无效或已退市，请检查代码格式：{', '.join(notfound_errs)}")

cached_tickers = quotes_df[quotes_df["_error"] == "cached"]["代码"].tolist()
if cached_tickers:
    st.info(f"💾 以下标的使用上次缓存数据：{', '.join(cached_tickers)}")

# 仅展示成功获取的数据
display_quotes = quotes_df[quotes_df["_error"].isin([_ERR_OK, "cached"])].copy()

# ── 顶部指标卡片 ──────────────────────────────────────────
top_n = min(4, len(display_quotes))
if top_n > 0:
    cols = st.columns(top_n)
    for i in range(top_n):
        row = display_quotes.iloc[i]
        price = f"{row['当前价格']:,.2f}" if pd.notna(row["当前价格"]) else "—"
        delta = f"{row['涨跌幅(%)']:.2f}%" if pd.notna(row["涨跌幅(%)"]) else None
        cols[i].metric(label=row["代码"], value=price, delta=delta)

st.markdown("---")

# ── 表格：st.dataframe + pandas Styler ───────────────────
if not display_quotes.empty:
    table_df = display_quotes.drop(columns=["_error"]).copy()
    table_df["成交量"] = table_df["成交量"].apply(format_volume)

    fmt_dict = {
        "当前价格": "{:,.2f}",
        "涨跌幅(%)": "{:+.2f}%",
        "今日最高": "{:,.2f}",
        "今日最低": "{:,.2f}",
    }

    styled = (
        table_df.style
        .format(fmt_dict, na_rep="—")
        .applymap(style_change, subset=["涨跌幅(%)"])
    )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=(len(table_df) + 1) * 38 + 10,
    )
else:
    st.info("暂无有效行情数据，请检查网络连接或标的代码。")

# ── K线图 & 技术指标 ─────────────────────────────────────
st.markdown("---")
st.markdown("## 📈 K线图 & 技术指标")

valid_tickers = display_quotes["代码"].tolist() if not display_quotes.empty else selected
kline_ticker = st.selectbox("选择标的", valid_tickers if valid_tickers else selected, key="kline_ticker")

if kline_ticker:
    with st.spinner(f"正在加载 {kline_ticker} 近6个月历史数据…"):
        hist = fetch_kline_history(kline_ticker, period="6mo")

    if hist.empty:
        st.warning(f"未能获取 {kline_ticker} 的历史数据，请稍后重试或检查代码。")
    else:
        col_ma, col_vwap = st.columns(2)
        show_ma = col_ma.checkbox("显示均线（SMA 20 / SMA 60）", value=True, key="show_ma")
        has_volume = "Volume" in hist.columns and hist["Volume"].sum() > 0
        show_vwap = col_vwap.checkbox("显示 VWAP", value=False, key="show_vwap", disabled=not has_volume)

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
        )

        fig.add_trace(
            go.Candlestick(
                x=hist.index,
                open=hist["Open"], high=hist["High"],
                low=hist["Low"], close=hist["Close"],
                name="K线",
            ),
            row=1, col=1,
        )

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
