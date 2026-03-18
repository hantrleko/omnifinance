"""资产净值追踪器 — 记录各类资产与负债，计算净资产并追踪变化趋势。"""

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.chart_config import build_layout
from core.currency import currency_selector, fmt, get_symbol

st.set_page_config(page_title="资产净值追踪器", page_icon="🏠", layout="wide")
st.markdown("""<style>.block-container{padding-top:1.2rem}.stMetric{background-color:var(--secondary-background-color);border:1px solid var(--secondary-background-color);border-radius:8px;padding:14px}</style>""", unsafe_allow_html=True)
st.title("🏠 资产净值追踪器")

st.sidebar.header("📋 设置")
currency_selector()

_NW_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "networth.json"

def _load_records() -> list[dict]:
    if not _NW_PATH.exists(): return []
    try: return json.loads(_NW_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError): return []

def _save_records(records: list[dict]) -> None:
    _NW_PATH.parent.mkdir(parents=True, exist_ok=True)
    _NW_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

records = _load_records()

st.markdown("---")
st.subheader("📝 录入资产与负债")
col_a, col_l = st.columns(2)
with col_a:
    st.markdown("#### 💰 资产")
    cash = st.number_input("现金及存款", min_value=0.0, value=0.0, step=10000.0, format="%.0f", key="nw_cash")
    stocks = st.number_input("股票及基金", min_value=0.0, value=0.0, step=10000.0, format="%.0f", key="nw_stocks")
    real_estate = st.number_input("房产（市值）", min_value=0.0, value=0.0, step=100000.0, format="%.0f", key="nw_re")
    other_assets = st.number_input("其他资产", min_value=0.0, value=0.0, step=10000.0, format="%.0f", key="nw_oa")
with col_l:
    st.markdown("#### 💳 负债")
    mortgage = st.number_input("房贷余额", min_value=0.0, value=0.0, step=10000.0, format="%.0f", key="nw_mort")
    car_loan = st.number_input("车贷/消费贷", min_value=0.0, value=0.0, step=10000.0, format="%.0f", key="nw_car")
    credit_card = st.number_input("信用卡欠款", min_value=0.0, value=0.0, step=1000.0, format="%.0f", key="nw_cc")
    other_liab = st.number_input("其他负债", min_value=0.0, value=0.0, step=10000.0, format="%.0f", key="nw_ol")

total_assets = cash + stocks + real_estate + other_assets
total_liab = mortgage + car_loan + credit_card + other_liab
net_worth = total_assets - total_liab

st.markdown("---")
st.subheader("📊 资产概览")
c1, c2, c3 = st.columns(3)
c1.metric("💰 总资产", fmt(total_assets, decimals=0))
c2.metric("💳 总负债", fmt(total_liab, decimals=0))
if records:
    last_nw = records[-1].get("net_worth", 0)
    c3.metric("🏠 净资产", fmt(net_worth, decimals=0), delta=f"{'+' if net_worth-last_nw>=0 else ''}{fmt(net_worth-last_nw, decimals=0)} vs 上次")
else:
    c3.metric("🏠 净资产", fmt(net_worth, decimals=0))

if total_assets > 0:
    dr = total_liab / total_assets * 100
    if dr > 60: st.error(f"⚠️ 负债率 {dr:.1f}%，偏高！")
    elif dr > 40: st.warning(f"📌 负债率 {dr:.1f}%，中等水平。")
    else: st.success(f"✅ 负债率 {dr:.1f}%，健康。")

st.session_state["dashboard_networth"] = {"net_worth": net_worth, "total_assets": total_assets, "total_liabilities": total_liab}

st.markdown("---")
if st.button("💾 保存当前快照", type="primary"):
    records.append({"date": datetime.now().strftime("%Y-%m-%d"), "cash": cash, "stocks": stocks, "real_estate": real_estate, "other_assets": other_assets, "mortgage": mortgage, "car_loan": car_loan, "credit_card": credit_card, "other_liab": other_liab, "total_assets": total_assets, "total_liabilities": total_liab, "net_worth": net_worth})
    _save_records(records)
    st.success("✅ 快照已保存！")
    st.rerun()
st.caption(f"已保存 {len(records)} 条记录")

if total_assets > 0:
    st.subheader("📊 资产配置")
    items = [("现金", cash, "#636EFA"), ("股票基金", stocks, "#00CC96"), ("房产", real_estate, "#EF553B"), ("其他", other_assets, "#AB63FA")]
    al, av, ac = zip(*[(l, v, c) for l, v, c in items if v > 0]) if any(v > 0 for _, v, _ in items) else ([], [], [])
    if al:
        fig_pie = go.Figure(data=[go.Pie(labels=list(al), values=list(av), hole=0.5, marker=dict(colors=list(ac), line=dict(color="white", width=3)), textinfo="label+percent")])
        fig_pie.update_layout(showlegend=False, margin=dict(t=20,b=20,l=20,r=20), height=380)
        st.plotly_chart(fig_pie, use_container_width=True)

if len(records) >= 2:
    st.subheader("📈 净资产趋势")
    tdf = pd.DataFrame(records)
    tdf["date"] = pd.to_datetime(tdf["date"])
    tdf = tdf.sort_values("date")
    sym = get_symbol()
    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(x=tdf["date"], y=tdf["net_worth"], mode="lines+markers", name="净资产", line=dict(width=2.5, color="#00CC96"), hovertemplate=f"%{{x|%Y-%m-%d}}<br>净资产: {sym}%{{y:,.0f}}<extra></extra>"))
    fig_t.add_trace(go.Scatter(x=tdf["date"], y=tdf["total_assets"], mode="lines", name="总资产", line=dict(width=2, dash="dash", color="#636EFA")))
    fig_t.add_trace(go.Scatter(x=tdf["date"], y=tdf["total_liabilities"], mode="lines", name="总负债", line=dict(width=2, dash="dot", color="#EF553B")))
    fig_t.update_layout(**build_layout(xaxis_title="日期", yaxis_title="金额", yaxis_tickformat=","))
    st.plotly_chart(fig_t, use_container_width=True)
elif len(records) == 1:
    st.info("📌 再保存一次快照后即可查看趋势图。")

if records:
    st.subheader("📋 历史记录")
    hdf = pd.DataFrame(records)[["date","total_assets","total_liabilities","net_worth"]].copy()
    hdf.columns = ["日期","总资产","总负债","净资产"]
    for c in ["总资产","总负债","净资产"]: hdf[c] = hdf[c].apply(lambda v: fmt(v, decimals=0))
    st.dataframe(hdf, use_container_width=True, hide_index=True)
    with st.expander("🗑️ 管理记录"):
        if st.button("清除所有记录", key="nw_clear"):
            _save_records([]); st.success("已清除"); st.rerun()

st.subheader("📤 导出报告")
def _build_nw_report() -> str:
    s = get_symbol()
    rh = "".join(f"<tr><td>{r['date']}</td><td>{s}{r['total_assets']:,.0f}</td><td>{s}{r['total_liabilities']:,.0f}</td><td>{s}{r['net_worth']:,.0f}</td></tr>" for r in records)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#222}}h1{{color:#333}}table{{border-collapse:collapse;width:100%;margin-top:12px}}th,td{{border:1px solid #ccc;padding:6px 10px;text-align:right;font-size:13px}}th{{background:#f5f5f5}}</style></head><body><h1>🏠 资产净值报告</h1><p>总资产：{s}{total_assets:,.0f} | 总负债：{s}{total_liab:,.0f} | 净资产：{s}{net_worth:,.0f}</p>{"<table><tr><th>日期</th><th>总资产</th><th>总负债</th><th>净资产</th></tr>"+rh+"</table>" if records else ""}</body></html>"""
st.download_button("📥 下载报告 (HTML)", data=_build_nw_report(), file_name="资产净值报告.html", mime="text/html")
st.caption("提示：打开 HTML 后按 Ctrl+P 可打印为 PDF。")

st.divider()
st.caption("🏠 资产净值追踪器 | 运行命令：`streamlit run app.py`")
