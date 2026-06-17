"""股票筛选器 — 基于基本面指标筛选任意股票

支持：
- A 股、美股、港股、其他市场分 Tab 操作
- 自由输入任意股票代码（不限于预设池）
- PE / PB / 股息率 / 市值过滤
- 散点图与柱状图可视化
- Excel 导出
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.page_setup import init_page
init_page("股票筛选器", "🔎", "screener")
from core.chart_config import build_layout

st.title("🔎 股票筛选器")
st.caption("自由输入任意股票代码，通过 PE/PB/股息率/市值等基本面指标快速筛选，找出符合条件的标的。")

# ── 市场分 Tab ─────────────────────────────────────────────
tab_us, tab_cn, tab_hk, tab_custom = st.tabs(["🇺🇸 美股", "🇨🇳 A股", "🇭🇰 港股", "✏️ 自定义"])

_MARKET_SUGGESTIONS = {
    "us": {
        "desc": "纳斯达克 / 纽交所股票代码，如 AAPL、TSLA、NVDA",
        "placeholder": "AAPL, MSFT, NVDA, TSLA, META, GOOGL, AMZN, BRK-B, JPM, V",
        "hint": "直接输入股票代码（Ticker Symbol），多个用逗号分隔",
        "suffix": "",
    },
    "cn": {
        "desc": "沪深 A 股 6 位代码，如 600519（贵州茅台）、000858（五粮液）",
        "placeholder": "600519, 000858, 601318, 000333, 300750, 002594, 601888",
        "hint": "输入 6 位 A 股代码，系统会自动添加沪深后缀（.SS / .SZ）供 yfinance 查询",
        "suffix": "auto",
    },
    "hk": {
        "desc": "港交所代码，如 0700.HK（腾讯）、9988.HK（阿里）",
        "placeholder": "0700.HK, 9988.HK, 3690.HK, 1299.HK, 0005.HK",
        "hint": "港股代码请加 .HK 后缀",
        "suffix": ".HK",
    },
    "custom": {
        "desc": "任意市场代码（Yahoo Finance 格式）",
        "placeholder": "AAPL, 0700.HK, 600519.SS, MSFT, 7203.T",
        "hint": "支持任意 Yahoo Finance 格式代码，市场不限",
        "suffix": "",
    },
}

def _normalize_cn_code(code: str) -> str:
    code = code.strip()
    if not (code.isdigit() and len(code) == 6):
        return code
    if code.startswith(("6", "9", "5")):
        return f"{code}.SS"
    return f"{code}.SZ"

def _get_tickers_from_input(raw: str, market: str) -> list[str]:
    parts = [p.strip().upper() for p in raw.replace("，", ",").split(",") if p.strip()]
    if market == "cn":
        return [_normalize_cn_code(p) for p in parts]
    return parts

# ── 输入区域 ───────────────────────────────────────────────
active_market = None
active_tickers_raw = ""

with tab_us:
    info = _MARKET_SUGGESTIONS["us"]
    st.caption(info["hint"])
    us_input = st.text_area("股票代码（逗号分隔）", value=info["placeholder"], height=80, key="us_input", help=info["desc"])
    if st.button("🔍 筛选美股", key="run_us", type="primary"):
        active_market = "us"
        active_tickers_raw = us_input

with tab_cn:
    info = _MARKET_SUGGESTIONS["cn"]
    st.caption(info["hint"])
    cn_input = st.text_area("A 股代码（6 位数字，逗号分隔）", value=info["placeholder"], height=80, key="cn_input", help=info["desc"])
    if st.button("🔍 筛选 A 股", key="run_cn", type="primary"):
        active_market = "cn"
        active_tickers_raw = cn_input

with tab_hk:
    info = _MARKET_SUGGESTIONS["hk"]
    st.caption(info["hint"])
    hk_input = st.text_area("港股代码（逗号分隔）", value=info["placeholder"], height=80, key="hk_input", help=info["desc"])
    if st.button("🔍 筛选港股", key="run_hk", type="primary"):
        active_market = "hk"
        active_tickers_raw = hk_input

with tab_custom:
    info = _MARKET_SUGGESTIONS["custom"]
    st.caption(info["hint"])
    custom_input = st.text_area("任意代码（Yahoo Finance 格式）", value=info["placeholder"], height=80, key="custom_input", help=info["desc"])
    if st.button("🔍 开始筛选", key="run_custom", type="primary"):
        active_market = "custom"
        active_tickers_raw = custom_input

# ── 筛选条件 ──────────────────────────────────────────────
with st.expander("⚙️ 筛选条件", expanded=True):
    f1, f2, f3, f4 = st.columns(4)
    pe_enabled = f1.checkbox("启用 PE 过滤", value=False, key="pe_enabled")
    pe_min = f1.number_input("PE 最小值", min_value=0.0, value=0.0, step=1.0, format="%.1f", disabled=not pe_enabled, key="pe_min")
    pe_max = f1.number_input("PE 最大值", min_value=0.0, value=30.0, step=1.0, format="%.1f", disabled=not pe_enabled, key="pe_max")

    pb_enabled = f2.checkbox("启用 PB 过滤", value=False, key="pb_enabled")
    pb_min = f2.number_input("PB 最小值", min_value=0.0, value=0.0, step=0.1, format="%.1f", disabled=not pb_enabled, key="pb_min")
    pb_max = f2.number_input("PB 最大值", min_value=0.0, value=5.0, step=0.1, format="%.1f", disabled=not pb_enabled, key="pb_max")

    div_enabled = f3.checkbox("股息率下限", value=False, key="div_enabled")
    div_min = f3.number_input("股息率 ≥ (%)", min_value=0.0, value=1.0, step=0.1, format="%.1f", disabled=not div_enabled, key="div_min")

    mktcap_enabled = f4.checkbox("启用市值过滤（亿）", value=False, key="mktcap_enabled")
    mktcap_min = f4.number_input("市值 ≥（亿）", min_value=0.0, value=0.0, step=100.0, format="%.0f", disabled=not mktcap_enabled, key="mktcap_min")
    mktcap_max = f4.number_input("市值 ≤（亿）", min_value=0.0, value=50000.0, step=100.0, format="%.0f", disabled=not mktcap_enabled, key="mktcap_max")

# ── 数据获取 ──────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fundamentals(tickers: tuple[str, ...]) -> pd.DataFrame:
    import yfinance as yf

    rows = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("regularMarketPreviousClose")
            mktcap = info.get("marketCap")
            div_yield = info.get("dividendYield")
            rows.append({
                "代码": ticker,
                "公司名称": info.get("shortName") or info.get("longName") or ticker,
                "行业": info.get("sector") or info.get("industry") or "—",
                "市价": price,
                "市盈率 PE": info.get("trailingPE") or info.get("forwardPE"),
                "市净率 PB": info.get("priceToBook"),
                "股息率 (%)": round(div_yield * 100, 2) if div_yield else 0.0,
                "市值（亿）": round(mktcap / 1e8, 1) if mktcap else None,
                "52周最高": info.get("fiftyTwoWeekHigh"),
                "52周最低": info.get("fiftyTwoWeekLow"),
                "ROE (%)": round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None,
                "_ok": True,
            })
        except Exception as e:
            rows.append({
                "代码": ticker, "公司名称": ticker, "行业": f"获取失败: {e}",
                "市价": None, "市盈率 PE": None, "市净率 PB": None,
                "股息率 (%)": None, "市值（亿）": None,
                "52周最高": None, "52周最低": None, "ROE (%)": None,
                "_ok": False,
            })
    return pd.DataFrame(rows)


# ── 执行筛选 ──────────────────────────────────────────────
if active_market and active_tickers_raw.strip():
    tickers = tuple(_get_tickers_from_input(active_tickers_raw, active_market))
    if not tickers:
        st.warning("请输入至少一个有效代码。")
        st.stop()

    with st.spinner(f"正在获取 {len(tickers)} 只股票的基本面数据，请稍候…"):
        df = fetch_fundamentals(tickers)

    st.session_state["screener_df"] = df
    st.session_state["screener_market"] = active_market

elif "screener_df" in st.session_state:
    df = st.session_state["screener_df"]
else:
    st.info("请在上方选择市场，输入股票代码后点击「筛选」按钮。")
    st.stop()

# ── 数据质量提示 ──────────────────────────────────────────
failed = df[~df["_ok"]] if "_ok" in df.columns else pd.DataFrame()
ok_df = df[df["_ok"]].copy() if "_ok" in df.columns else df.copy()

if not failed.empty:
    st.warning(f"以下代码获取失败（共 {len(failed)} 只）：{', '.join(failed['代码'].tolist()[:10])}")

if ok_df.empty:
    st.error("所有代码均获取失败，请检查代码格式是否正确。")
    st.stop()

# ── 应用筛选器 ────────────────────────────────────────────
filtered = ok_df.copy()

if pe_enabled and pe_max > pe_min:
    # Only filter rows where PE is not null; exclude rows with missing PE if filter is active
    pe_series = filtered["市盈率 PE"]
    filtered = filtered[pe_series.notna() & pe_series.between(pe_min, pe_max)]

if pb_enabled and pb_max > pb_min:
    pb_series = filtered["市净率 PB"]
    filtered = filtered[pb_series.notna() & pb_series.between(pb_min, pb_max)]

if div_enabled and div_min > 0:
    filtered = filtered[filtered["股息率 (%)"].fillna(0.0) >= div_min]

if mktcap_enabled:
    mc_series = filtered["市值（亿）"]
    filtered = filtered[mc_series.notna() & mc_series.between(mktcap_min, mktcap_max)]

# ── 结果摘要 ──────────────────────────────────────────────
st.markdown("---")
sc1, sc2, sc3 = st.columns(3)
sc1.metric("总有效股票数", len(ok_df))
sc2.metric("符合条件", len(filtered))
pct_pass = len(filtered) / max(1, len(ok_df)) * 100
sc3.metric("通过率", f"{pct_pass:.0f}%")

if filtered.empty:
    st.warning("没有股票符合当前筛选条件，请调整过滤参数。")
    st.stop()

# ── 数据表格 ──────────────────────────────────────────────
st.subheader("📋 筛选结果")

def _fmt_num(v, fmt_str):
    return fmt_str.format(v) if pd.notna(v) and v is not None else "—"

display_df = filtered.drop(columns=["_ok"], errors="ignore").copy()
display_df["市盈率 PE"] = display_df["市盈率 PE"].apply(lambda v: _fmt_num(v, "{:.2f}"))
display_df["市净率 PB"] = display_df["市净率 PB"].apply(lambda v: _fmt_num(v, "{:.2f}"))
display_df["股息率 (%)"] = display_df["股息率 (%)"].apply(lambda v: _fmt_num(v, "{:.2f}%"))
display_df["市值（亿）"] = display_df["市值（亿）"].apply(lambda v: _fmt_num(v, "{:,.0f}"))
display_df["市价"] = display_df["市价"].apply(lambda v: _fmt_num(v, "{:,.2f}"))
display_df["ROE (%)"] = display_df["ROE (%)"].apply(lambda v: _fmt_num(v, "{:.1f}%"))
display_df["52周最高"] = display_df["52周最高"].apply(lambda v: _fmt_num(v, "{:,.2f}"))
display_df["52周最低"] = display_df["52周最低"].apply(lambda v: _fmt_num(v, "{:,.2f}"))

st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── PE vs PB 散点图 ────────────────────────────────────────
plot_df = filtered.dropna(subset=["市盈率 PE", "市净率 PB"]).copy()
if not plot_df.empty:
    st.subheader("📈 PE vs PB 散点图")
    bubble_size = plot_df["市值（亿）"].fillna(plot_df["市值（亿）"].median() or 100)
    fig_scatter = px.scatter(
        plot_df,
        x="市净率 PB",
        y="市盈率 PE",
        size=bubble_size,
        color="行业",
        hover_name="公司名称",
        hover_data={"代码": True, "股息率 (%)": True, "ROE (%)": True, "市值（亿）": True},
        text="代码",
        size_max=60,
    )
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.update_layout(**build_layout(
        xaxis_title="市净率 PB", yaxis_title="市盈率 PE", height=500,
    ))
    st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.caption("PE/PB 数据不足，无法绘制散点图。")

# ── 股息率柱状图 ──────────────────────────────────────────
div_df = filtered[filtered["股息率 (%)"].fillna(0) > 0].sort_values("股息率 (%)", ascending=False)
if not div_df.empty:
    st.subheader("💰 股息率排名")
    fig_div = go.Figure(go.Bar(
        x=div_df["代码"],
        y=div_df["股息率 (%)"],
        marker_color="#00CC96",
        text=div_df["股息率 (%)"].apply(lambda v: f"{v:.2f}%"),
        textposition="outside",
        hovertemplate="%{x}<br>股息率: %{y:.2f}%<extra></extra>",
    ))
    fig_div.update_layout(**build_layout(
        xaxis_title="股票代码", yaxis_title="股息率 (%)", showlegend=False, height=350,
    ))
    st.plotly_chart(fig_div, use_container_width=True)

# ── 市值柱状图 ────────────────────────────────────────────
mc_df = filtered.dropna(subset=["市值（亿）"]).sort_values("市值（亿）", ascending=False).head(20)
if not mc_df.empty:
    st.subheader("🏢 市值排名（Top 20）")
    fig_mc = go.Figure(go.Bar(
        x=mc_df["代码"],
        y=mc_df["市值（亿）"],
        marker_color="#636EFA",
        text=mc_df["市值（亿）"].apply(lambda v: f"{v:,.0f}亿"),
        textposition="outside",
        hovertemplate="%{x}<br>市值: %{y:,.0f} 亿<extra></extra>",
    ))
    fig_mc.update_layout(**build_layout(
        xaxis_title="股票代码", yaxis_title="市值（亿）", showlegend=False, height=350,
    ))
    st.plotly_chart(fig_mc, use_container_width=True)

# ── 导出 ──────────────────────────────────────────────────
st.subheader("📤 导出结果")
try:
    from core.export import dataframes_to_excel
    _export_filtered = filtered.drop(columns=["_ok"], errors="ignore")
    _export_all = ok_df.drop(columns=["_ok"], errors="ignore")
    _xlsx = dataframes_to_excel(
        sheets=[("筛选结果", _export_filtered), ("全部股票", _export_all)],
        title="股票筛选报告",
    )
    st.download_button(
        "📊 下载筛选报告 (Excel)",
        data=_xlsx,
        file_name="股票筛选结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
except Exception:
    buf = io.StringIO()
    filtered.drop(columns=["_ok"], errors="ignore").to_csv(buf, index=False, encoding="utf-8-sig")
    st.download_button("📥 下载筛选结果 (CSV)", data=buf.getvalue(), file_name="股票筛选结果.csv", mime="text/csv")

st.divider()
st.caption("🔎 股票筛选器 | 数据由 Yahoo Finance 提供，A股需加 .SS/.SZ 后缀 | 仅供参考，不构成投资建议。")

