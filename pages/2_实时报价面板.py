"""多标的实时股票 / 加密货币报价面板

使用 yfinance (fast_info) + asyncio + httpx 并发获取数据，
streamlit-autorefresh 自动刷新，Streamlit 展示。

v1.5:
- 将 ThreadPoolExecutor 替换为 asyncio + httpx 异步并发获取报价
  * 每个标的通过 httpx.AsyncClient 异步请求 Yahoo Finance Query2 API
  * asyncio.gather 并发所有请求，避免线程切换开销
  * 保留 ThreadPoolExecutor 作为 yfinance K 线下载的回退方案
- K 线图历史数据保留 @st.cache_data(ttl=300) 缓存
- 报价失败保留分级错误提示（网络错误 / 代码不存在 / 限流）
"""

import asyncio
from datetime import datetime
import logging
import urllib.error

import httpx
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

from core.config import CFG, MSG
from core.storage import save_scheme, load_scheme, list_schemes

# ── 模块级 logger ─────────────────────────────────────────
_logger = logging.getLogger(__name__)

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

refresh_interval = st.sidebar.slider(
    "自动刷新间隔（秒）",
    CFG.quote.refresh_interval_min,
    CFG.quote.refresh_interval_max,
    CFG.quote.refresh_interval_default,
    step=CFG.quote.refresh_interval_step,
)

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
st.sidebar.caption(MSG.data_source_yfinance)
st.sidebar.caption(MSG.quote_ticker_hint)

# ── 自动刷新 ──────────────────────────────────────────────
st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")


# ── 数据获取（asyncio + httpx 异步并发） ─────────────────

# Yahoo Finance Query2 API endpoint for real-time quote
_YF_QUOTE_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d"
_HTTPX_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_HTTPX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OmniFinance/1.5)",
    "Accept": "application/json",
}

# Error category constants
_ERR_NETWORK = "network"
_ERR_NOTFOUND = "notfound"
_ERR_OK = "ok"


def _make_base(ticker_str: str) -> dict:
    """Return an empty result skeleton for *ticker_str*."""
    return {
        "代码": ticker_str,
        "当前价格": None,
        "涨跌幅(%)": None,
        "今日最高": None,
        "今日最低": None,
        "成交量": None,
        "_error": None,
    }


def _parse_yf_response(ticker_str: str, data: dict) -> dict:
    """Parse a Yahoo Finance chart API JSON response into a quote row.

    Args:
        ticker_str: The ticker symbol being parsed.
        data: Parsed JSON dict from the Yahoo Finance chart endpoint.

    Returns:
        A quote row dict with price, change, high, low, volume and _error fields.

    Raises:
        KeyError: If expected keys are missing from the response.
        TypeError: If values are of unexpected types.
        ValueError: If numeric conversion fails.
    """
    base = _make_base(ticker_str)
    result = data["chart"]["result"]
    if not result:
        base["_error"] = _ERR_NOTFOUND
        return base

    meta: dict = result[0]["meta"]
    current: float | None = meta.get("regularMarketPrice")
    prev_close: float | None = meta.get("previousClose") or meta.get("chartPreviousClose")
    day_high: float | None = meta.get("regularMarketDayHigh")
    day_low: float | None = meta.get("regularMarketDayLow")
    volume: int | None = meta.get("regularMarketVolume")

    if current is None and prev_close is None:
        base["_error"] = _ERR_NOTFOUND
        return base

    change_pct: float | None = (
        (current / prev_close - 1) * 100 if current and prev_close else None
    )
    return {
        **base,
        "当前价格": current,
        "涨跌幅(%)": change_pct,
        "今日最高": day_high,
        "今日最低": day_low,
        "成交量": volume,
        "_error": _ERR_OK,
    }


async def _async_fetch_one(
    client: httpx.AsyncClient,
    ticker_str: str,
) -> dict:
    """Asynchronously fetch a single ticker quote via Yahoo Finance chart API.

    Args:
        client: Shared ``httpx.AsyncClient`` instance.
        ticker_str: The ticker symbol to fetch.

    Returns:
        A quote row dict; ``_error`` is set to ``_ERR_NETWORK`` or
        ``_ERR_NOTFOUND`` on failure, ``_ERR_OK`` on success.
    """
    base = _make_base(ticker_str)
    url = _YF_QUOTE_URL.format(ticker=ticker_str)
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        data: dict = resp.json()
        return _parse_yf_response(ticker_str, data)
    except httpx.TimeoutException as exc:
        _logger.warning("[%s] 请求超时: %s", ticker_str, exc, exc_info=True)
        base["_error"] = _ERR_NETWORK
        return base
    except httpx.NetworkError as exc:
        _logger.warning("[%s] 网络错误: %s", ticker_str, exc, exc_info=True)
        base["_error"] = _ERR_NETWORK
        return base
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in (404, 400):
            _logger.warning("[%s] 标的不存在 (HTTP %s)", ticker_str, status)
            base["_error"] = _ERR_NOTFOUND
        else:
            _logger.warning("[%s] HTTP 错误 %s: %s", ticker_str, status, exc, exc_info=True)
            base["_error"] = _ERR_NETWORK
        return base
    except (KeyError, TypeError, ValueError) as exc:
        _logger.warning("[%s] 数据解析错误: %s", ticker_str, exc, exc_info=True)
        base["_error"] = _ERR_NOTFOUND
        return base
    except Exception as exc:  # noqa: BLE001 — last-resort: keep panel alive
        _logger.error("[%s] 未预期异常: %s", ticker_str, exc, exc_info=True)
        err_str = str(exc).lower()
        base["_error"] = _ERR_NETWORK if any(
            kw in err_str for kw in ("connection", "timeout", "network", "ssl", "read")
        ) else _ERR_NOTFOUND
        return base


async def _async_fetch_all(tickers: tuple[str, ...]) -> list[dict]:
    """Concurrently fetch all tickers using a single shared AsyncClient.

    Args:
        tickers: Tuple of ticker symbols to fetch.

    Returns:
        List of quote row dicts in the same order as *tickers*.
    """
    async with httpx.AsyncClient(
        headers=_HTTPX_HEADERS,
        timeout=_HTTPX_TIMEOUT,
        follow_redirects=True,
    ) as client:
        tasks = [_async_fetch_one(client, t) for t in tickers]
        results: list[dict] = await asyncio.gather(*tasks)
    return results


@st.cache_data(ttl=CFG.quote.quote_cache_ttl)
def fetch_quotes(tickers: tuple[str, ...]) -> pd.DataFrame:
    """Fetch real-time quotes for all *tickers* using asyncio + httpx.

    Replaces the previous ``ThreadPoolExecutor`` implementation with a
    single-event-loop ``asyncio.gather`` call, reducing thread-switching
    overhead and connection setup cost.

    Args:
        tickers: Tuple of ticker symbols (hashable for ``@st.cache_data``).

    Returns:
        DataFrame with columns: 代码, 当前价格, 涨跌幅(%), 今日最高,
        今日最低, 成交量, _error.
    """
    rows: list[dict] = asyncio.run(_async_fetch_all(tickers))
    return pd.DataFrame(rows)


@st.cache_data(ttl=CFG.quote.kline_cache_ttl)
def fetch_kline_history(ticker_str: str, period: str = CFG.quote.kline_default_period) -> pd.DataFrame:
    """下载 K 线历史数据，结果缓存 5 分钟，避免重复请求。"""
    try:
        hist = yf.download(ticker_str, period=period, progress=False, auto_adjust=True)
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)
        return hist
    except (urllib.error.URLError, requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as exc:
        # Network failure while downloading historical data
        _logger.warning("[%s] K线数据网络错误: %s", ticker_str, exc, exc_info=True)
        return pd.DataFrame()
    except (KeyError, ValueError) as exc:
        # Malformed or empty response from yfinance
        _logger.warning("[%s] K线数据解析错误: %s", ticker_str, exc, exc_info=True)
        return pd.DataFrame()
    except Exception as exc:  # noqa: BLE001 — keep UI alive on unexpected failures
        _logger.error("[%s] K线数据未预期异常: %s", ticker_str, exc, exc_info=True)
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
    st.warning(MSG.quote_no_selection)
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
    st.warning(MSG.quote_network_error.format(tickers=', '.join(network_errs)))
if notfound_errs:
    st.error(MSG.quote_notfound_error.format(tickers=', '.join(notfound_errs)))

cached_tickers = quotes_df[quotes_df["_error"] == "cached"]["代码"].tolist()
if cached_tickers:
    st.info(MSG.quote_cached_info.format(tickers=', '.join(cached_tickers)))

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
    st.info(MSG.quote_no_valid_data)

# ── K线图 & 技术指标 ─────────────────────────────────────
st.markdown("---")
st.markdown("## 📈 K线图 & 技术指标")

valid_tickers = display_quotes["代码"].tolist() if not display_quotes.empty else selected
kline_ticker = st.selectbox("选择标的", valid_tickers if valid_tickers else selected, key="kline_ticker")

if kline_ticker:
    with st.spinner(MSG.quote_kline_loading.format(ticker=kline_ticker)):
        hist = fetch_kline_history(kline_ticker)

    if hist.empty:
        st.warning(MSG.quote_kline_failed.format(ticker=kline_ticker))
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
st.caption(MSG.quote_footer.format(interval=refresh_interval))
