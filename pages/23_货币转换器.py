"""货币转换器 — 实时汇率换算、历史走势与批量换算

支持 CNY / USD / EUR / GBP / JPY / HKD 6 种货币的实时与离线换算。
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.currency import CURRENCIES, get_symbol
from core.exchange_rates import (
    get_all_rates,
    get_historical_rates,
    get_last_updated_str,
    get_rate,
    is_live,
)
from core.storage import scheme_manager_ui

st.set_page_config(page_title="货币转换器", page_icon="💱", layout="wide")
st.title("💱 货币转换器")

live = is_live()
status_label = "实时" if live else "离线参考"
st.caption(f"汇率来源：{status_label}数据，更新于 {get_last_updated_str()}")
if not live:
    st.warning("当前使用离线参考汇率，数据可能不是最新。")

CODES = list(CURRENCIES.keys())


def _label(code: str) -> str:
    c = CURRENCIES[code]
    return f"{c['symbol']} {c['name']} ({code})"


# ── Sidebar ────────────────────────────────────────────────
st.sidebar.header("📋 参数设置")

default_from = st.sidebar.selectbox("源货币", CODES, index=CODES.index("USD"), format_func=_label, key="cv_from")
default_to = st.sidebar.selectbox("目标货币", CODES, index=CODES.index("CNY"), format_func=_label, key="cv_to")
amount_input = st.sidebar.number_input("换算金额", min_value=0.0, value=1000.0, step=100.0)

if st.sidebar.button("🔄 刷新实时汇率"):
    st.cache_data.clear()
    st.rerun()

scheme_manager_ui("currency_converter", {"from": default_from, "to": default_to, "amount": amount_input})

st.sidebar.markdown("---")
st.sidebar.caption("数据来源：Yahoo Finance，15 分钟缓存。仅供参考，不构成投资建议。")

# ── Main converter ─────────────────────────────────────────
rate = get_rate(default_from, default_to)
result = amount_input * rate

col_left, col_mid, col_right = st.columns([2, 1, 2])
with col_left:
    st.metric(f"{_label(default_from)}", f"{CURRENCIES[default_from]['symbol']}{amount_input:,.2f}")
with col_mid:
    st.markdown(f"<div style='text-align:center;font-size:2rem;padding-top:1.5rem;'>→</div>", unsafe_allow_html=True)
with col_right:
    st.metric(f"{_label(default_to)}", f"{CURRENCIES[default_to]['symbol']}{result:,.4f}")

st.markdown(f"**1 {default_from} = {rate:.6f} {default_to}**  |  **1 {default_to} = {1/rate:.6f} {default_from}**" if rate != 0 else "")

# ── Cross-rate matrix ──────────────────────────────────────
st.markdown("---")
st.subheader("📊 全量交叉汇率矩阵")
st.caption("6×6 主流货币两两汇率（行 → 列）")

rates = get_all_rates()
matrix_data: dict[str, list] = {}
for from_c in CODES:
    row = []
    for to_c in CODES:
        r = get_rate(from_c, to_c)
        row.append(round(r, 4) if from_c != to_c else "—")
    matrix_data[from_c] = row

matrix_df = pd.DataFrame(matrix_data, index=CODES).T
matrix_df.columns = CODES
st.dataframe(matrix_df, use_container_width=True)

# ── Historical chart ───────────────────────────────────────
st.markdown("---")
st.subheader("📈 近 30 天汇率走势")

hist_df = get_historical_rates(default_from, default_to, days=30)
if not hist_df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_df.index, y=hist_df["rate"],
        mode="lines+markers", name=f"{default_from}/{default_to}",
        line=dict(width=2.5, color="#2563eb"),
        marker=dict(size=4),
        hovertemplate="%{x|%Y-%m-%d}<br>汇率: %{y:.4f}<extra></extra>",
    ))
    fig.update_layout(**build_layout(
        title=f"{default_from} → {default_to} 近30天走势",
        xaxis_title="日期",
        yaxis_title=f"汇率 ({default_to})",
    ))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("暂无历史数据（网络不可用时显示离线汇率，无法绘制历史图表）。")

# ── Quick scenarios ────────────────────────────────────────
st.markdown("---")
st.subheader("⚡ 常用场景快捷换算")

sc1, sc2, sc3 = st.columns(3)
with sc1:
    st.markdown("**海外购物**")
    shop_usd = st.number_input("商品美元价格 (USD)", min_value=0.0, value=299.0, step=10.0, key="sc_shop")
    shop_cny = shop_usd * get_rate("USD", "CNY")
    st.metric("折合人民币", f"¥{shop_cny:,.2f}")

with sc2:
    st.markdown("**留学学费**")
    tuition_gbp = st.number_input("学费英镑 (GBP)", min_value=0.0, value=15000.0, step=500.0, key="sc_tuition")
    tuition_cny = tuition_gbp * get_rate("GBP", "CNY")
    st.metric("折合人民币", f"¥{tuition_cny:,.2f}")

with sc3:
    st.markdown("**工资对比**")
    salary_usd = st.number_input("月薪美元 (USD)", min_value=0.0, value=5000.0, step=100.0, key="sc_salary")
    salary_cny = salary_usd * get_rate("USD", "CNY")
    st.metric("折合人民币", f"¥{salary_cny:,.2f}")

# ── Batch conversion ───────────────────────────────────────
st.markdown("---")
st.subheader("📋 批量换算")
st.caption("输入多个金额（换行分隔），一次输出全部换算结果")

batch_from = st.selectbox("源货币", CODES, index=CODES.index("USD"), format_func=_label, key="batch_from")
batch_to = st.selectbox("目标货币", CODES, index=CODES.index("CNY"), format_func=_label, key="batch_to")
batch_text = st.text_area("金额列表（每行一个）", value="100\n500\n1000\n5000\n10000", height=120)

if batch_text.strip():
    batch_rate = get_rate(batch_from, batch_to)
    batch_rows = []
    for line in batch_text.strip().splitlines():
        try:
            val = float(line.strip().replace(",", ""))
            converted = val * batch_rate
            batch_rows.append({
                f"源金额 ({batch_from})": f"{CURRENCIES[batch_from]['symbol']}{val:,.2f}",
                f"换算结果 ({batch_to})": f"{CURRENCIES[batch_to]['symbol']}{converted:,.2f}",
            })
        except ValueError:
            continue
    if batch_rows:
        st.dataframe(pd.DataFrame(batch_rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("💱 货币转换器 | 运行命令：`streamlit run app.py`")
