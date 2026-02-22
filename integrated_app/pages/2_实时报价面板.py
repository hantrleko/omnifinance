"""多标的实时股票 / 加密货币报价面板

使用 yfinance (fast_info) + ThreadPoolExecutor 并行获取数据，
streamlit-autorefresh 自动刷新，Streamlit 展示。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

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
  .stMetric { background: #0E1117; border: 1px solid #262730; border-radius: 8px; padding: 12px; }
  div[data-testid="stMetricValue"] { font-size: 1.1rem; }
  .time-badge {
      display: inline-block; background: #1a1a2e; border: 1px solid #333;
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

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption(f"自动刷新间隔：{refresh_interval} 秒 | 数据来源：Yahoo Finance | 运行命令：`streamlit run app.py`")
