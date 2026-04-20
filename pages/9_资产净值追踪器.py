"""资产净值追踪器 — 记录各类资产与负债，计算净资产并追踪变化趋势。"""

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import currency_selector, fmt, get_symbol

st.set_page_config(page_title="资产净值追踪器", page_icon="🏠", layout="wide")
st.title("🏠 资产净值追踪器")

st.sidebar.header("📋 设置")

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
    cash = st.number_input("现金及存款", min_value=0.0, value=0.0, step=CFG.networth.asset_step, format="%.0f", key="nw_cash")
    stocks = st.number_input("股票及基金", min_value=0.0, value=0.0, step=CFG.networth.asset_step, format="%.0f", key="nw_stocks")
    real_estate = st.number_input("房产（市值）", min_value=0.0, value=0.0, step=CFG.networth.real_estate_step, format="%.0f", key="nw_re")
    other_assets = st.number_input("其他资产", min_value=0.0, value=0.0, step=CFG.networth.asset_step, format="%.0f", key="nw_oa")
with col_l:
    st.markdown("#### 💳 负债")
    mortgage = st.number_input("房贷余额", min_value=0.0, value=0.0, step=CFG.networth.asset_step, format="%.0f", key="nw_mort")
    car_loan = st.number_input("车贷/消费贷", min_value=0.0, value=0.0, step=CFG.networth.asset_step, format="%.0f", key="nw_car")
    credit_card = st.number_input("信用卡欠款", min_value=0.0, value=0.0, step=CFG.networth.credit_card_step, format="%.0f", key="nw_cc")
    other_liab = st.number_input("其他负债", min_value=0.0, value=0.0, step=CFG.networth.asset_step, format="%.0f", key="nw_ol")

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
    if dr > CFG.networth.debt_ratio_high: st.error(MSG.networth_debt_high.format(ratio=dr))
    elif dr > CFG.networth.debt_ratio_medium: st.warning(MSG.networth_debt_medium.format(ratio=dr))
    else: st.success(MSG.networth_debt_ok.format(ratio=dr))

st.session_state["dashboard_networth"] = {"net_worth": net_worth, "total_assets": total_assets, "total_liabilities": total_liab}

st.markdown("---")
if st.button("💾 保存当前快照", type="primary"):
    records.append({"date": datetime.now().strftime("%Y-%m-%d"), "cash": cash, "stocks": stocks, "real_estate": real_estate, "other_assets": other_assets, "mortgage": mortgage, "car_loan": car_loan, "credit_card": credit_card, "other_liab": other_liab, "total_assets": total_assets, "total_liabilities": total_liab, "net_worth": net_worth})
    _save_records(records)
    st.success(MSG.networth_saved)
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

    # Debt ratio trend
    st.subheader("📉 负债率趋势")
    tdf["debt_ratio"] = tdf.apply(
        lambda r: r["total_liabilities"] / r["total_assets"] * 100 if r["total_assets"] > 0 else 0.0,
        axis=1,
    )
    fig_dr = go.Figure()
    fig_dr.add_trace(go.Scatter(
        x=tdf["date"], y=tdf["debt_ratio"],
        mode="lines+markers", name="负债率",
        line=dict(width=2.5, color="#AB63FA"),
        hovertemplate="%{x|%Y-%m-%d}<br>负债率: %{y:.1f}%<extra></extra>",
    ))
    fig_dr.add_hline(y=CFG.networth.debt_ratio_medium, line_dash="dash", line_color="#FFA726",
                     annotation_text=f"警戒线 {CFG.networth.debt_ratio_medium:.0f}%", annotation_position="bottom right")
    fig_dr.add_hline(y=CFG.networth.debt_ratio_high, line_dash="dash", line_color="#EF553B",
                     annotation_text=f"危险线 {CFG.networth.debt_ratio_high:.0f}%", annotation_position="bottom right")
    fig_dr.update_layout(**build_layout(xaxis_title="日期", yaxis_title="负债率（%）"))
    st.plotly_chart(fig_dr, use_container_width=True)
elif len(records) == 1:
    st.info(MSG.networth_trend_hint)

if records:
    st.subheader("📋 历史记录")
    hdf = pd.DataFrame(records)[["date","total_assets","total_liabilities","net_worth"]].copy()
    hdf.columns = ["日期","总资产","总负债","净资产"]
    for c in ["总资产","总负债","净资产"]: hdf[c] = hdf[c].apply(lambda v: fmt(v, decimals=0))
    st.dataframe(hdf, use_container_width=True, hide_index=True)

    with st.expander("🗑️ 管理记录"):
        col_del, col_clear = st.columns(2)
        with col_del:
            st.markdown("**删除单条记录**")
            date_options = [f"第{i+1}条 — {r['date']}" for i, r in enumerate(records)]
            del_idx = st.selectbox("选择要删除的记录", range(len(date_options)), format_func=lambda i: date_options[i], key="nw_del_idx")
            if st.button("🗑️ 删除选中记录", key="nw_del_one"):
                records.pop(del_idx)
                _save_records(records)
                st.success(f"已删除第 {del_idx + 1} 条记录")
                st.rerun()
        with col_clear:
            st.markdown("**清除所有记录**")
            if st.button("⚠️ 清除所有记录", key="nw_clear"):
                _save_records([]); st.success(MSG.networth_cleared); st.rerun()

    # CSV export
    raw_df = pd.DataFrame(records)[["date","cash","stocks","real_estate","other_assets","mortgage","car_loan","credit_card","other_liab","total_assets","total_liabilities","net_worth"]].copy()
    raw_df.columns = ["日期","现金","股票基金","房产","其他资产","房贷","车贷消费贷","信用卡","其他负债","总资产","总负债","净资产"]
    st.download_button(
        "📥 导出历史记录 CSV",
        data=raw_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name="资产净值历史.csv",
        mime="text/csv",
        key="nw_csv",
    )

st.markdown("---")
st.subheader("📐 计划线 vs 实际线对比")
st.caption("设定净资产增长计划，实时对比实际执行情况，偏差一目了然。")

with st.expander("⚙️ 设置净资产增长计划", expanded=len(records) >= 2):
    plan_col1, plan_col2 = st.columns(2)
    plan_start_nw = plan_col1.number_input(
        "计划起点净资产（元）",
        min_value=0.0, value=float(records[0].get("net_worth", 0)) if records else 0.0,
        step=10000.0, format="%.0f", key="plan_start_nw",
    )
    plan_annual_growth = plan_col2.number_input(
        "计划年增长率（%）",
        min_value=-20.0, max_value=50.0, value=10.0, step=0.5, format="%.1f", key="plan_ag",
    )

    if records:
        tdf_plan = pd.DataFrame(records)
        tdf_plan["date"] = pd.to_datetime(tdf_plan["date"])
        tdf_plan = tdf_plan.sort_values("date").reset_index(drop=True)
        start_date_plan = tdf_plan["date"].iloc[0]

        plan_values = []
        for _, row in tdf_plan.iterrows():
            years_elapsed = (row["date"] - start_date_plan).days / 365.25
            planned = plan_start_nw * (1 + plan_annual_growth / 100) ** years_elapsed
            plan_values.append(planned)

        fig_plan = go.Figure()
        sym_plan = get_symbol()
        fig_plan.add_trace(go.Scatter(
            x=tdf_plan["date"], y=tdf_plan["net_worth"],
            mode="lines+markers", name="实际净资产",
            line=dict(width=2.5, color="#00CC96"),
            hovertemplate=f"%{{x|%Y-%m-%d}}<br>实际: {sym_plan}%{{y:,.0f}}<extra></extra>",
        ))
        fig_plan.add_trace(go.Scatter(
            x=tdf_plan["date"], y=plan_values,
            mode="lines", name=f"计划线（年增 {plan_annual_growth:.1f}%）",
            line=dict(width=2, dash="dash", color="#FFD600"),
            hovertemplate=f"%{{x|%Y-%m-%d}}<br>计划: {sym_plan}%{{y:,.0f}}<extra></extra>",
        ))

        deviations = [actual - planned for actual, planned in zip(tdf_plan["net_worth"], plan_values)]
        fig_plan.add_trace(go.Bar(
            x=tdf_plan["date"], y=deviations,
            name="与计划偏差",
            marker_color=["#00CC96" if d >= 0 else "#EF553B" for d in deviations],
            opacity=0.5,
            yaxis="y2",
            hovertemplate=f"%{{x|%Y-%m-%d}}<br>偏差: {sym_plan}%{{y:,.0f}}<extra></extra>",
        ))

        fig_plan.update_layout(
            **build_layout(xaxis_title="日期", yaxis_title="净资产（元）", yaxis_tickformat=","),
            yaxis2=dict(title="偏差（元）", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(fig_plan, use_container_width=True)

        last_deviation = deviations[-1] if deviations else 0
        if last_deviation >= 0:
            st.success(f"✅ 最近一次记录**超出计划** {fmt(last_deviation, decimals=0)}，执行情况良好！")
        else:
            st.warning(f"⚠️ 最近一次记录**落后计划** {fmt(abs(last_deviation), decimals=0)}，建议检查储蓄或支出情况。")
    else:
        st.info("保存至少一条净资产快照后，将自动生成计划 vs 实际对比图。")

st.markdown("---")
st.subheader("🔮 未来净资产预测")
st.caption("基于自定义增长参数，预测未来净资产走势。")

with st.expander("⚙️ 设置预测参数", expanded=False):
    proj_col1, proj_col2, proj_col3 = st.columns(3)
    proj_asset_growth = proj_col1.number_input(
        "年资产增长率（%）",
        min_value=-20.0, max_value=50.0, value=7.0, step=0.5, format="%.1f", key="proj_ag",
        help="预期资产年化增长率（含投资收益和新增储蓄）",
    )
    proj_liab_change = proj_col2.number_input(
        "年负债变化率（%）",
        min_value=-50.0, max_value=20.0, value=-5.0, step=0.5, format="%.1f", key="proj_lc",
        help="负债每年变化比例（负数 = 逐年还清）",
    )
    proj_years = proj_col3.slider("预测年限", min_value=1, max_value=20, value=10, key="proj_yr")

    base_assets = total_assets if total_assets > 0 else (records[-1].get("total_assets", 0) if records else 0.0)
    base_liab = total_liab if total_assets > 0 else (records[-1].get("total_liabilities", 0) if records else 0.0)
    base_nw = base_assets - base_liab

    if base_assets > 0:
        from datetime import date as _date
        current_year = _date.today().year
        proj_rows = []
        _pa, _pl = base_assets, base_liab
        for yr in range(proj_years + 1):
            proj_rows.append({"年份": f"{current_year + yr}年", "预测资产": _pa, "预测负债": _pl, "预测净资产": _pa - _pl})
            _pa = _pa * (1 + proj_asset_growth / 100)
            _pl = max(0.0, _pl * (1 + proj_liab_change / 100))

        proj_df = pd.DataFrame(proj_rows)

        fig_proj = go.Figure()
        sym_proj = get_symbol()
        fig_proj.add_trace(go.Scatter(x=proj_df["年份"], y=proj_df["预测净资产"], mode="lines+markers", name="预测净资产", line=dict(width=2.5, color="#00CC96"), hovertemplate=f"%{{x}}<br>净资产: {sym_proj}%{{y:,.0f}}<extra></extra>"))
        fig_proj.add_trace(go.Scatter(x=proj_df["年份"], y=proj_df["预测资产"], mode="lines", name="预测资产", line=dict(width=2, dash="dash", color="#636EFA")))
        fig_proj.add_trace(go.Scatter(x=proj_df["年份"], y=proj_df["预测负债"], mode="lines", name="预测负债", line=dict(width=2, dash="dot", color="#EF553B")))
        fig_proj.update_layout(**build_layout(xaxis_title="年份", yaxis_title="金额", yaxis_tickformat=","))
        st.plotly_chart(fig_proj, use_container_width=True)

        proj_display = proj_df.copy()
        for col in ["预测资产", "预测负债", "预测净资产"]:
            proj_display[col] = proj_display[col].apply(lambda v: fmt(v, decimals=0))
        st.dataframe(proj_display, use_container_width=True, hide_index=True)

        final_nw = proj_df.iloc[-1]["预测净资产"]
        growth_factor = (final_nw / base_nw - 1) * 100 if base_nw > 0 else 0.0
        st.info(f"按设定增长率，{proj_years} 年后预测净资产为 **{fmt(final_nw, decimals=0)}**，较当前增长约 **{growth_factor:.1f}%**。")
    else:
        st.info("请先在上方录入资产数据，再进行预测。")

st.subheader("📤 导出报告")
def _build_nw_report() -> str:
    s = get_symbol()
    rh = "".join(f"<tr><td>{r['date']}</td><td>{s}{r['total_assets']:,.0f}</td><td>{s}{r['total_liabilities']:,.0f}</td><td>{s}{r['net_worth']:,.0f}</td></tr>" for r in records)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#222}}h1{{color:#333}}table{{border-collapse:collapse;width:100%;margin-top:12px}}th,td{{border:1px solid #ccc;padding:6px 10px;text-align:right;font-size:13px}}th{{background:#f5f5f5}}</style></head><body><h1>🏠 资产净值报告</h1><p>总资产：{s}{total_assets:,.0f} | 总负债：{s}{total_liab:,.0f} | 净资产：{s}{net_worth:,.0f}</p>{"<table><tr><th>日期</th><th>总资产</th><th>总负债</th><th>净资产</th></tr>"+rh+"</table>" if records else ""}</body></html>"""
st.download_button("📥 下载报告 (HTML)", data=_build_nw_report(), file_name="资产净值报告.html", mime="text/html")
st.caption(MSG.print_hint)

st.divider()
st.caption(MSG.networth_footer)
