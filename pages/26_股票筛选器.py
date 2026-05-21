"""股票筛选器 — 基于基本面指标快速筛选股票

使用 yfinance 获取多个标的的基本面数据，支持按 PE/PB/股息率/市值过滤，
散点图与柱状图可视化，Excel 导出。
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.theme import inject_theme

inject_theme()

from core.chart_config import build_layout
from core.currency import fmt

st.set_page_config(page_title="股票筛选器", page_icon="🔎", layout="wide")

st.title("🔎 股票筛选器")
st.caption("输入多个股票代码，通过 PE/PB/股息率/市值等基本面指标快速筛选，找出符合条件的标的。")

# ── 侧边栏 ────────────────────────────────────────────────
st.sidebar.header("📋 筛选条件")

_DEFAULT_TICKERS = "AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, BRK-B, JPM, JNJ, V, PG, UNH, HD, MA"
tickers_input = st.sidebar.text_area(
    "股票代码（逗号分隔）",
    value=_DEFAULT_TICKERS,
    height=100,
    help="支持美股代码（如 AAPL, TSLA）",
)

st.sidebar.subheader("PE 市盈率")
pe_min = st.sidebar.number_input("PE 最小值", min_value=0.0, value=0.0, step=1.0, format="%.1f")
pe_max = st.sidebar.number_input("PE 最大值", min_value=0.0, value=50.0, step=1.0, format="%.1f")

st.sidebar.subheader("PB 市净率")
pb_min = st.sidebar.number_input("PB 最小值", min_value=0.0, value=0.0, step=0.1, format="%.1f")
pb_max = st.sidebar.number_input("PB 最大值", min_value=0.0, value=20.0, step=0.1, format="%.1f")

st.sidebar.subheader("股息率（%）")
div_min = st.sidebar.number_input("股息率 最小值 (%)", min_value=0.0, value=0.0, step=0.1, format="%.1f")

st.sidebar.subheader("市值（亿美元）")
mktcap_min = st.sidebar.number_input("市值 最小值（亿）", min_value=0.0, value=0.0, step=100.0, format="%.0f")
mktcap_max = st.sidebar.number_input("市值 最大值（亿）", min_value=0.0, value=100000.0, step=100.0, format="%.0f")

run_btn = st.sidebar.button("🔍 开始筛选", type="primary")

# ── 数据获取 ───────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fundamentals(tickers: tuple[str, ...]) -> pd.DataFrame:
    import yfinance as yf

    rows = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            rows.append({
                "代码": ticker,
                "公司名称": info.get("shortName") or info.get("longName") or ticker,
                "行业": info.get("sector", "—"),
                "市价（USD）": info.get("currentPrice") or info.get("regularMarketPrice"),
                "市盈率 PE": info.get("trailingPE") or info.get("forwardPE"),
                "市净率 PB": info.get("priceToBook"),
                "股息率 (%)": (info.get("dividendYield") or 0) * 100,
                "市值（亿）": (info.get("marketCap") or 0) / 1e8,
                "52周最高": info.get("fiftyTwoWeekHigh"),
                "52周最低": info.get("fiftyTwoWeekLow"),
                "ROE (%)": (info.get("returnOnEquity") or 0) * 100,
            })
        except Exception:
            rows.append({
                "代码": ticker, "公司名称": ticker, "行业": "获取失败",
                "市价（USD）": None, "市盈率 PE": None, "市净率 PB": None,
                "股息率 (%)": None, "市值（亿）": None,
                "52周最高": None, "52周最低": None, "ROE (%)": None,
            })
    return pd.DataFrame(rows)


if run_btn or "screener_df" in st.session_state:
    tickers_clean = tuple(t.strip().upper() for t in tickers_input.split(",") if t.strip())

    if not tickers_clean:
        st.warning("请输入至少一个股票代码。")
        st.stop()

    with st.spinner(f"正在获取 {len(tickers_clean)} 只股票的基本面数据…"):
        df = fetch_fundamentals(tickers_clean)

    st.session_state["screener_df"] = df

    # ── 应用筛选器 ─────────────────────────────────────────
    filtered = df.copy()

    pe_mask = pd.Series([True] * len(filtered), index=filtered.index)
    if pe_max > 0:
        pe_mask = filtered["市盈率 PE"].fillna(float("inf")).between(pe_min, pe_max)
    filtered = filtered[pe_mask]

    pb_mask = filtered["市净率 PB"].fillna(float("inf")).between(pb_min, pb_max)
    filtered = filtered[pb_mask]

    if div_min > 0:
        filtered = filtered[filtered["股息率 (%)"].fillna(0) >= div_min]

    if mktcap_max > 0:
        filtered = filtered[filtered["市值（亿）"].fillna(0).between(mktcap_min, mktcap_max)]

    # ── 结果摘要 ───────────────────────────────────────────
    st.markdown("---")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("总股票数", len(df))
    sc2.metric("符合条件", len(filtered), delta=f"{len(filtered)/max(1,len(df))*100:.0f}%")
    sc3.metric("被过滤", len(df) - len(filtered))

    if filtered.empty:
        st.warning("没有股票符合当前筛选条件，请调整过滤参数。")
    else:
        # ── 数据表格 ───────────────────────────────────────
        st.subheader("📋 筛选结果")
        display_df = filtered.copy()
        for col in ["市盈率 PE", "市净率 PB"]:
            display_df[col] = display_df[col].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
        display_df["股息率 (%)"] = display_df["股息率 (%)"].apply(lambda v: f"{v:.2f}%" if pd.notna(v) else "—")
        display_df["市值（亿）"] = display_df["市值（亿）"].apply(lambda v: f"{v:,.0f}" if pd.notna(v) else "—")
        display_df["市价（USD）"] = display_df["市价（USD）"].apply(lambda v: f"${v:,.2f}" if pd.notna(v) else "—")
        display_df["ROE (%)"] = display_df["ROE (%)"].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else "—")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # ── PE vs PB 散点图 ────────────────────────────────
        plot_df = filtered.dropna(subset=["市盈率 PE", "市净率 PB"]).copy()
        if not plot_df.empty:
            st.subheader("📈 PE vs PB 散点图")
            fig_scatter = px.scatter(
                plot_df,
                x="市净率 PB",
                y="市盈率 PE",
                size="市值（亿）",
                color="行业",
                hover_name="公司名称",
                hover_data={"代码": True, "股息率 (%)": True, "ROE (%)": True},
                text="代码",
                size_max=60,
            )
            fig_scatter.update_traces(textposition="top center")
            fig_scatter.update_layout(**build_layout(
                xaxis_title="市净率 PB",
                yaxis_title="市盈率 PE",
                height=500,
            ))
            st.plotly_chart(fig_scatter, use_container_width=True)

        # ── 股息率柱状图 ──────────────────────────────────
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
                xaxis_title="股票代码", yaxis_title="股息率 (%)",
                showlegend=False, height=350,
            ))
            st.plotly_chart(fig_div, use_container_width=True)

        # ── 市值柱状图 ────────────────────────────────────
        mc_df = filtered.dropna(subset=["市值（亿）"]).sort_values("市值（亿）", ascending=False).head(15)
        if not mc_df.empty:
            st.subheader("🏢 市值排名（Top 15）")
            fig_mc = go.Figure(go.Bar(
                x=mc_df["代码"],
                y=mc_df["市值（亿）"],
                marker_color="#636EFA",
                text=mc_df["市值（亿）"].apply(lambda v: f"{v:,.0f}亿"),
                textposition="outside",
                hovertemplate="%{x}<br>市值: %{y:,.0f} 亿美元<extra></extra>",
            ))
            fig_mc.update_layout(**build_layout(
                xaxis_title="股票代码", yaxis_title="市值（亿美元）",
                showlegend=False, height=350,
            ))
            st.plotly_chart(fig_mc, use_container_width=True)

        # ── Excel 导出 ────────────────────────────────────
        st.subheader("📤 导出结果")
        try:
            from core.export import dataframes_to_excel
            _xlsx = dataframes_to_excel(
                sheets=[("筛选结果", filtered), ("全部股票", df)],
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
            filtered.to_csv(buf, index=False, encoding="utf-8-sig")
            st.download_button("📥 下载筛选结果 (CSV)", data=buf.getvalue(), file_name="股票筛选结果.csv", mime="text/csv")

else:
    st.info("请在左侧设置筛选条件后点击「开始筛选」。")

st.divider()
st.caption("🔎 股票筛选器 | 数据由 Yahoo Finance 提供，仅供参考，不构成投资建议。")
