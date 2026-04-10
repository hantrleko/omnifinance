"""多标的实时股票 / 加密货币报价面板

使用 yfinance (fast_info) + asyncio + httpx 并发获取数据，
AKShare 获取 A 股实时行情，
streamlit-autorefresh 自动刷新，Streamlit 展示。

v1.7:
- 新增 A 股支持（通过 AKShare 获取沪深两市实时行情）
- 侧边栏快捷选择新增「A股」分组
- A 股代码格式：6 位数字（如 600519、000858）
- K 线图支持 A 股历史数据（通过 AKShare）
"""

import asyncio
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import urllib.error

import httpx
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from core.theme import inject_theme
inject_theme()
import yfinance as yf
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

from core.chart_config import render_empty_state
from core.config import CFG, MSG
from core.storage import save_scheme, load_scheme, list_schemes

_logger = logging.getLogger(__name__)

_QUOTE_DISK_CACHE_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "quote_last_cache.json"


def _load_disk_cache() -> dict[str, dict]:
    if not _QUOTE_DISK_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_QUOTE_DISK_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_disk_cache(cache: dict[str, dict]) -> None:
    try:
        _QUOTE_DISK_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _QUOTE_DISK_CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        _logger.warning("无法写入磁盘报价缓存: %s", exc)


st.set_page_config(page_title="实时报价面板", page_icon="📊", layout="wide")

PRESETS: dict[str, list[str]] = {
    "A股": ["600519", "000858", "601318", "000333", "300750"],
    "美股": ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"],
    "港股": ["0700.HK", "9988.HK", "3690.HK"],
    "加密货币": ["BTC-USD", "ETH-USD", "SOL-USD"],
}
ALL_TICKERS = [t for group in PRESETS.values() for t in group]

_ASHARE_LABELS: dict[str, str] = {
    "600519": "贵州茅台",
    "000858": "五粮液",
    "601318": "中国平安",
    "000333": "美的集团",
    "300750": "宁德时代",
}

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

st.sidebar.header("📋 标的选择")

quick = st.sidebar.radio("快捷选择", ["自定义", "全选", "A股", "美股", "港股", "加密货币"], horizontal=True)
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
    format_func=lambda x: f"{x} {_ASHARE_LABELS[x]}" if x in _ASHARE_LABELS else x,
)

custom_input = st.sidebar.text_input("添加自定义代码（逗号分隔）", placeholder="如 AMZN, META, 601988")
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

st.sidebar.divider()
st.sidebar.subheader("💾 关注列表管理")

wl_name = st.sidebar.text_input("列表名称", placeholder="如 我的A股组合", key="wl_name")
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
st.sidebar.subheader("🔔 价格预警设置")
st.sidebar.caption("设置价格突破阈值时的预警提示。")

if "price_alerts" not in st.session_state:
    st.session_state["price_alerts"] = {}

pa_ticker = st.sidebar.selectbox("选择标的", options=selected if selected else [""], key="pa_ticker")
pa_col1, pa_col2 = st.sidebar.columns(2)
pa_high = pa_col1.number_input("价格上限", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="pa_high", help="当价格超过此值时发出警告（0 = 不设限）")
pa_low = pa_col2.number_input("价格下限", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="pa_low", help="当价格低于此值时发出警告（0 = 不设限）")
if st.sidebar.button("✅ 设置预警", key="pa_set"):
    if pa_ticker:
        st.session_state["price_alerts"][pa_ticker] = {"high": pa_high, "low": pa_low}
        st.sidebar.success(f"已为 {pa_ticker} 设置预警")
if st.sidebar.button("🗑️ 清除所有预警", key="pa_clear"):
    st.session_state["price_alerts"] = {}
    st.sidebar.success("已清除所有预警")

st.sidebar.divider()
st.sidebar.caption(MSG.data_source_yfinance)
st.sidebar.caption("A 股数据由 AKShare 提供，其余由 Yahoo Finance 提供。")
st.sidebar.caption(MSG.quote_ticker_hint)

st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")


# ── A 股相关工具 ──────────────────────────────────────────

def _is_ashare(ticker_str: str) -> bool:
    """Detect A-share codes: 6-digit number with valid exchange prefix.
    
    Shanghai: 600xxx, 601xxx, 603xxx, 605xxx, 688xxx (STAR), 900xxx (B)
    Shenzhen: 000xxx, 001xxx, 002xxx, 003xxx, 300xxx (ChiNext), 301xxx, 200xxx (B)
    """
    if not (ticker_str.isdigit() and len(ticker_str) == 6):
        return False
    prefix2 = ticker_str[:2]
    prefix3 = ticker_str[:3]
    valid_sh = {"60", "68", "90"}
    valid_sz_3 = {"000", "001", "002", "003", "200", "300", "301"}
    return prefix2 in valid_sh or prefix3 in valid_sz_3


def _ashare_full_code(code: str) -> str:
    """返回带市场前缀的完整代码，用于 AKShare。"""
    if code.startswith(("6", "9")):
        return f"sh{code}"
    return f"sz{code}"


@st.cache_data(ttl=CFG.quote.quote_cache_ttl)
def fetch_ashare_quotes(codes: tuple[str, ...]) -> pd.DataFrame:
    """通过 AKShare 获取 A 股实时报价。"""
    try:
        import akshare as ak
        df_sh = ak.stock_sh_a_spot_em()
        df_sz = ak.stock_sz_a_spot_em()
        df_all = pd.concat([df_sh, df_sz], ignore_index=True)
    except Exception as exc:
        _logger.error("AKShare 获取 A 股数据失败: %s", exc, exc_info=True)
        rows = []
        for code in codes:
            base = _make_base(code)
            base["_error"] = _ERR_NETWORK
            rows.append(base)
        return pd.DataFrame(rows)

    col_map = {
        "代码": "代码",
        "最新价": "当前价格",
        "涨跌幅": "涨跌幅(%)",
        "最高": "今日最高",
        "最低": "今日最低",
        "成交量": "成交量",
    }
    rows = []
    for code in codes:
        base = _make_base(code)
        match = df_all[df_all["代码"] == code]
        if match.empty:
            base["_error"] = _ERR_NOTFOUND
            rows.append(base)
            continue
        r = match.iloc[0]
        try:
            rows.append({
                "代码": code,
                "当前价格": float(r.get("最新价", 0) or 0),
                "涨跌幅(%)": float(r.get("涨跌幅", 0) or 0),
                "今日最高": float(r.get("最高", 0) or 0),
                "今日最低": float(r.get("最低", 0) or 0),
                "成交量": float(r.get("成交量", 0) or 0),
                "_error": _ERR_OK,
            })
        except (KeyError, TypeError, ValueError) as exc:
            _logger.warning("[%s] A股数据解析错误: %s", code, exc)
            base["_error"] = _ERR_NOTFOUND
            rows.append(base)

    return pd.DataFrame(rows)


@st.cache_data(ttl=CFG.quote.kline_cache_ttl)
def fetch_ashare_kline(code: str, period: str = "daily", count: int = 120) -> pd.DataFrame:
    """通过 AKShare 获取 A 股历史 K 线数据。"""
    try:
        import akshare as ak
        end_date = datetime.now().strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(
            symbol=code,
            period=period,
            start_date="20230101",
            end_date=end_date,
            adjust="qfq",
        )
        df = df.rename(columns={
            "日期": "Date",
            "开盘": "Open",
            "收盘": "Close",
            "最高": "High",
            "最低": "Low",
            "成交量": "Volume",
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
        return df[["Open", "High", "Low", "Close", "Volume"]].tail(count)
    except Exception as exc:
        _logger.error("[%s] AKShare K线数据失败: %s", code, exc, exc_info=True)
        return pd.DataFrame()


# ── Yahoo Finance 数据获取（保持原有逻辑） ────────────────

_YF_QUOTE_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d"
_HTTPX_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_HTTPX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OmniFinance/1.5)",
    "Accept": "application/json",
}

_ERR_NETWORK = "network"
_ERR_NOTFOUND = "notfound"
_ERR_OK = "ok"


def _make_base(ticker_str: str) -> dict:
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
    *,
    max_retries: int = 3,
) -> dict:
    base = _make_base(ticker_str)
    url = _YF_QUOTE_URL.format(ticker=ticker_str)
    for attempt in range(max_retries):
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data: dict = resp.json()
            return _parse_yf_response(ticker_str, data)
        except httpx.TimeoutException as exc:
            _logger.warning("[%s] 请求超时 (尝试 %d/%d): %s", ticker_str, attempt + 1, max_retries, exc)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            base["_error"] = _ERR_NETWORK
            return base
        except httpx.NetworkError as exc:
            _logger.warning("[%s] 网络错误 (尝试 %d/%d): %s", ticker_str, attempt + 1, max_retries, exc)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            base["_error"] = _ERR_NETWORK
            return base
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (404, 400):
                base["_error"] = _ERR_NOTFOUND
            elif status == 429:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                base["_error"] = _ERR_NETWORK
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                base["_error"] = _ERR_NETWORK
            return base
        except (KeyError, TypeError, ValueError) as exc:
            _logger.warning("[%s] 数据解析错误: %s", ticker_str, exc, exc_info=True)
            base["_error"] = _ERR_NOTFOUND
            return base
        except Exception as exc:  # noqa: BLE001
            _logger.error("[%s] 未预期异常: %s", ticker_str, exc, exc_info=True)
            err_str = str(exc).lower()
            is_network = any(
                kw in err_str for kw in ("connection", "timeout", "network", "ssl", "read")
            )
            if is_network and attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            base["_error"] = _ERR_NETWORK if is_network else _ERR_NOTFOUND
            return base
    base["_error"] = _ERR_NETWORK
    return base


async def _async_fetch_all(tickers: tuple[str, ...]) -> list[dict]:
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
    rows: list[dict] = asyncio.run(_async_fetch_all(tickers))
    return pd.DataFrame(rows)


@st.cache_data(ttl=CFG.quote.kline_cache_ttl)
def fetch_kline_history(ticker_str: str, period: str = CFG.quote.kline_default_period) -> pd.DataFrame:
    try:
        hist = yf.download(ticker_str, period=period, progress=False, auto_adjust=True)
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)
        return hist
    except (urllib.error.URLError, requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as exc:
        _logger.warning("[%s] K线数据网络错误: %s", ticker_str, exc, exc_info=True)
        return pd.DataFrame()
    except (KeyError, ValueError) as exc:
        _logger.warning("[%s] K线数据解析错误: %s", ticker_str, exc, exc_info=True)
        return pd.DataFrame()
    except Exception as exc:  # noqa: BLE001
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

# ── 分拣 A 股和非 A 股 ────────────────────────────────────
ashare_codes = tuple(t for t in selected if _is_ashare(t))
other_tickers = tuple(t for t in selected if not _is_ashare(t))

with st.spinner("正在获取行情数据…"):
    frames = []
    if other_tickers:
        frames.append(fetch_quotes(other_tickers))
    if ashare_codes:
        frames.append(fetch_ashare_quotes(ashare_codes))
    if frames:
        quotes_df = pd.concat(frames, ignore_index=True)
    else:
        quotes_df = pd.DataFrame(columns=["代码", "当前价格", "涨跌幅(%)", "今日最高", "今日最低", "成交量", "_error"])

# ── Session 级缓存回退 ────────────────────────────────────
if "quote_cache" not in st.session_state:
    st.session_state["quote_cache"] = {}

cache = st.session_state["quote_cache"]
used_cache = False

if "quote_disk_cache" not in st.session_state:
    st.session_state["quote_disk_cache"] = _load_disk_cache()
disk_cache = st.session_state["quote_disk_cache"]
disk_cache_dirty = False

for i, row in quotes_df.iterrows():
    ticker_code = row["代码"]
    if row["_error"] == _ERR_OK and pd.notna(row["当前价格"]):
        entry = {
            "当前价格": row["当前价格"],
            "涨跌幅(%)": row["涨跌幅(%)"],
            "今日最高": row["今日最高"],
            "今日最低": row["今日最低"],
            "成交量": row["成交量"],
        }
        cache[ticker_code] = entry
        disk_cache[ticker_code] = {**entry, "cached_at": datetime.now().isoformat()}
        disk_cache_dirty = True
    elif row["_error"] != _ERR_OK:
        fallback = cache.get(ticker_code) or disk_cache.get(ticker_code)
        if fallback:
            for col in ["当前价格", "涨跌幅(%)", "今日最高", "今日最低", "成交量"]:
                quotes_df.at[i, col] = fallback[col]
            quotes_df.at[i, "_error"] = "cached"
            used_cache = True

if disk_cache_dirty:
    _save_disk_cache(disk_cache)

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

display_quotes = quotes_df[quotes_df["_error"].isin([_ERR_OK, "cached"])].copy()

# ── 顶部指标卡片 ──────────────────────────────────────────
top_n = min(4, len(display_quotes))
if top_n > 0:
    cols = st.columns(top_n)
    for i in range(top_n):
        row = display_quotes.iloc[i]
        price = f"{row['当前价格']:,.2f}" if pd.notna(row["当前价格"]) else "—"
        delta = f"{row['涨跌幅(%)']:.2f}%" if pd.notna(row["涨跌幅(%)"]) else None
        label = f"{row['代码']} {_ASHARE_LABELS[row['代码']]}" if row["代码"] in _ASHARE_LABELS else row["代码"]
        cols[i].metric(label=label, value=price, delta=delta)

st.markdown("---")

# ── 价格预警检查 ─────────────────────────────────────────
if st.session_state.get("price_alerts") and not display_quotes.empty:
    triggered_alerts = []
    for _, row in display_quotes.iterrows():
        t_code = row["代码"]
        alert = st.session_state["price_alerts"].get(t_code)
        if alert and pd.notna(row["当前价格"]):
            price_val = float(row["当前价格"])
            if alert["high"] > 0 and price_val > alert["high"]:
                triggered_alerts.append(f"⬆️ **{t_code}** 当前价格 {price_val:,.2f} 突破上限 {alert['high']:,.2f}")
            if alert["low"] > 0 and price_val < alert["low"]:
                triggered_alerts.append(f"⬇️ **{t_code}** 当前价格 {price_val:,.2f} 跌破下限 {alert['low']:,.2f}")

    if triggered_alerts:
        for alert_msg in triggered_alerts:
            st.warning(f"🔔 价格预警：{alert_msg}")
    elif st.session_state["price_alerts"]:
        active_alerts = [f"{t}（上限:{v['high']:.2f}/下限:{v['low']:.2f}）" for t, v in st.session_state["price_alerts"].items()]
        st.success(f"✅ 已监控 {len(active_alerts)} 个预警条件，当前均未触发：{', '.join(active_alerts)}")

# ── 表格 ──────────────────────────────────────────────────
if not display_quotes.empty:
    table_df = display_quotes.drop(columns=["_error"]).copy()
    table_df["成交量"] = table_df["成交量"].apply(format_volume)
    table_df["代码"] = table_df["代码"].apply(
        lambda x: f"{x} {_ASHARE_LABELS[x]}" if x in _ASHARE_LABELS else x
    )

    fmt_dict = {
        "当前价格": "{:,.2f}",
        "涨跌幅(%)": "{:+.2f}%",
        "今日最高": "{:,.2f}",
        "今日最低": "{:,.2f}",
    }

    styled = (
        table_df.style
        .format(fmt_dict, na_rep="—")
        .map(style_change, subset=["涨跌幅(%)"])
    )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=(len(table_df) + 1) * 38 + 10,
    )
else:
    render_empty_state(
        title="暂无有效报价",
        message=MSG.quote_no_valid_data,
        icon="📡",
    )

# ── K线图 & 技术指标 ─────────────────────────────────────
st.markdown("---")
st.markdown("## 📈 K线图 & 技术指标")

valid_tickers = display_quotes["代码"].str.split(" ").str[0].tolist() if not display_quotes.empty else selected
kline_ticker = st.selectbox(
    "选择标的",
    valid_tickers if valid_tickers else selected,
    key="kline_ticker",
    format_func=lambda x: f"{x} {_ASHARE_LABELS[x]}" if x in _ASHARE_LABELS else x,
)

if kline_ticker:
    with st.spinner(MSG.quote_kline_loading.format(ticker=kline_ticker)):
        if _is_ashare(kline_ticker):
            hist = fetch_ashare_kline(kline_ticker)
        else:
            hist = fetch_kline_history(kline_ticker)

    if hist.empty:
        render_empty_state(
            title=f"无法加载 {kline_ticker} 的历史数据",
            message=MSG.quote_kline_failed.format(ticker=kline_ticker),
            icon="📉",
        )
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

        title_label = f"{kline_ticker} {_ASHARE_LABELS[kline_ticker]}" if kline_ticker in _ASHARE_LABELS else kline_ticker
        fig.update_layout(
            title=f"{title_label} — 近6个月K线图",
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
