"""复利计算器 —— Streamlit 网页应用

支持两种模式：
  1. 一次性投资（Lump Sum）
  2. 定期定投（Regular Contribution）

功能：计算未来价值、生成每年余额表格、绘制余额增长曲线、
      利率误差分析、导出 CSV / PDF。
"""

import io
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.compound import add_annualized_return, compute_schedule

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="复利计算器", page_icon="💰", layout="centered")
st.title("💰 复利计算器")

# ── 侧边栏：输入参数 ──────────────────────────────────────
st.sidebar.header("📋 参数设置")

mode = st.sidebar.radio("投资模式", ["一次性投资", "定期定投"], horizontal=True)

principal = st.sidebar.number_input("本金（元）", min_value=0.0, value=10000.0, step=1000.0, format="%.2f")
annual_rate = st.sidebar.number_input("年化利率（%）", min_value=0.0, max_value=100.0, value=5.0, step=0.1, format="%.2f")
years = st.sidebar.number_input("投资年限（年）", min_value=1, max_value=100, value=10, step=1)

freq_options = {"每年 (1)": 1, "每半年 (2)": 2, "每季度 (4)": 4, "每月 (12)": 12, "每日 (365)": 365}
freq_label = st.sidebar.selectbox("复利频率", list(freq_options.keys()))
n = freq_options[freq_label]

contribution = 0.0
contrib_freq_n = 12
if mode == "定期定投":
    contribution = st.sidebar.number_input("每期定投金额（元）", min_value=0.0, value=1000.0, step=100.0, format="%.2f")
    contrib_freq_options = {"每月": 12, "每季度": 4, "每半年": 2, "每年": 1}
    contrib_freq_label = st.sidebar.selectbox("定投频率", list(contrib_freq_options.keys()))
    contrib_freq_n = contrib_freq_options[contrib_freq_label]


schedule = compute_schedule(principal, annual_rate, years, n, contribution, contrib_freq_n)
schedule = add_annualized_return(schedule)

# 误差分析：利率 ±1%
schedule_hi = compute_schedule(principal, annual_rate + 1, years, n, contribution, contrib_freq_n)
schedule_lo = compute_schedule(principal, max(0, annual_rate - 1), years, n, contribution, contrib_freq_n)

# ── 结果概览 ──────────────────────────────────────────────
final = schedule.iloc[-1]
total_interest = final["年末余额"] - final["累计投入"]

st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("最终余额", f"¥{final['年末余额']:,.2f}")
col2.metric("累计投入", f"¥{final['累计投入']:,.2f}")
col3.metric("累计收益", f"¥{total_interest:,.2f}")

# ── 增长曲线（深色主题 + 年化收益率） ─────────────────────
st.subheader("📈 余额增长曲线")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=schedule["年份"], y=schedule["年末余额"],
    mode="lines+markers", name="年末余额",
    line=dict(width=3, color="#636EFA"),
    hovertemplate="第 %{x} 年<br>余额: ¥%{y:,.2f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=schedule["年份"], y=schedule["累计投入"],
    mode="lines", name="累计投入",
    line=dict(width=2, dash="dash", color="#EF553B"),
    hovertemplate="第 %{x} 年<br>累计投入: ¥%{y:,.2f}<extra></extra>",
))
# 年化收益率放在右 Y 轴
fig.add_trace(go.Scatter(
    x=schedule["年份"], y=schedule["年化收益率(%)"],
    mode="lines+markers", name="年化收益率(%)",
    line=dict(width=2, color="#00CC96", dash="dot"),
    marker=dict(size=5),
    yaxis="y2",
    hovertemplate="第 %{x} 年<br>年化收益率: %{y:.2f}%<extra></extra>",
))
fig.update_layout(
    xaxis_title="年份",
    yaxis=dict(title="金额（元）", tickformat=",", side="left"),
    yaxis2=dict(title="年化收益率(%)", overlaying="y", side="right", showgrid=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict()),
    margin=dict(t=30, b=40),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ── 误差分析：利率 ±1% ────────────────────────────────────
st.subheader("🔍 利率敏感性分析（±1%）")

final_hi = schedule_hi.iloc[-1]["年末余额"]
final_lo = schedule_lo.iloc[-1]["年末余额"]
final_mid = final["年末余额"]

col_a, col_b, col_c = st.columns(3)
col_a.metric(
    f"利率 {max(0, annual_rate - 1):.2f}%",
    f"¥{final_lo:,.2f}",
    f"{final_lo - final_mid:+,.2f}",
    delta_color="inverse",
)
col_b.metric(
    f"利率 {annual_rate:.2f}%（当前）",
    f"¥{final_mid:,.2f}",
)
col_c.metric(
    f"利率 {annual_rate + 1:.2f}%",
    f"¥{final_hi:,.2f}",
    f"{final_hi - final_mid:+,.2f}",
)

fig_sens = go.Figure()
for label, sched, color in [
    (f"{max(0, annual_rate-1):.1f}%", schedule_lo, "#EF553B"),
    (f"{annual_rate:.1f}%（当前）", schedule, "#636EFA"),
    (f"{annual_rate+1:.1f}%", schedule_hi, "#00CC96"),
]:
    fig_sens.add_trace(go.Scatter(
        x=sched["年份"], y=sched["年末余额"],
        mode="lines", name=label,
        line=dict(width=2, color=color),
        hovertemplate="第 %{x} 年<br>余额: ¥%{y:,.2f}<extra></extra>",
    ))
fig_sens.update_layout(
    xaxis_title="年份",
    yaxis_title="金额（元）",
    yaxis_tickformat=",",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict()),
    margin=dict(t=30, b=40),
    hovermode="x unified",
)
st.plotly_chart(fig_sens, use_container_width=True)

# ── 每年余额表格 ──────────────────────────────────────────
st.subheader("📊 每年余额明细")

display_df = schedule.copy()
money_cols = ["年初余额", "当年投入", "当年利息", "年末余额", "累计投入"]
for col in money_cols:
    display_df[col] = display_df[col].apply(lambda v: f"¥{v:,.2f}")
display_df["年化收益率(%)"] = display_df["年化收益率(%)"].apply(lambda v: f"{v:.2f}%")
display_df["年份"] = display_df["年份"].astype(str)

st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── 每月 & 每日利息明细 ───────────────────────────────────
st.subheader("📅 月度 & 日度利息明细")

detail_year = st.selectbox(
    "选择查看年份",
    options=list(range(1, years + 1)),
    format_func=lambda y: f"第 {y} 年",
)

# 取该年年初余额作为起始
year_start_balance = schedule.loc[schedule["年份"] == detail_year, "年初余额"].values[0]
year_contribution = schedule.loc[schedule["年份"] == detail_year, "当年投入"].values[0]
r = annual_rate / 100.0

# — 月度明细 —
monthly_rate = r / 12
monthly_contrib = year_contribution / 12 if contribution > 0 else 0.0
month_rows: list[dict] = []
bal = year_start_balance
for m in range(1, 13):
    interest_m = bal * monthly_rate
    bal += interest_m + monthly_contrib
    month_rows.append({
        "月份": f"{m} 月",
        "月初余额": bal - interest_m - monthly_contrib,
        "当月利息": interest_m,
        "当月投入": monthly_contrib,
        "月末余额": bal,
    })
monthly_df = pd.DataFrame(month_rows)

# — 日度明细 —
daily_rate = r / 365
daily_contrib = year_contribution / 365 if contribution > 0 else 0.0
day_rows: list[dict] = []
bal_d = year_start_balance
for d in range(1, 366):
    interest_d = bal_d * daily_rate
    bal_d += interest_d + daily_contrib
    day_rows.append({
        "天数": d,
        "当日利息": interest_d,
        "当日投入": daily_contrib,
        "当日余额": bal_d,
    })
daily_df = pd.DataFrame(day_rows)

tab_month, tab_day = st.tabs(["📆 月度明细", "📋 日度明细"])

with tab_month:
    fmt_monthly = monthly_df.copy()
    for c in ["月初余额", "当月利息", "当月投入", "月末余额"]:
        fmt_monthly[c] = fmt_monthly[c].apply(lambda v: f"¥{v:,.2f}")
    st.dataframe(fmt_monthly, use_container_width=True, hide_index=True)

    total_m_interest = monthly_df["当月利息"].sum()
    st.info(f"第 {detail_year} 年 — 月度利息合计：¥{total_m_interest:,.2f}")

with tab_day:
    fmt_daily = daily_df.copy()
    for c in ["当日利息", "当日投入", "当日余额"]:
        fmt_daily[c] = fmt_daily[c].apply(lambda v: f"¥{v:,.2f}")
    st.dataframe(fmt_daily, use_container_width=True, hide_index=True, height=400)

    total_d_interest = daily_df["当日利息"].sum()
    st.info(f"第 {detail_year} 年 — 日度利息合计：¥{total_d_interest:,.2f}")

# ── 导出功能 ──────────────────────────────────────────────
st.subheader("💾 导出数据")

col_dl1, col_dl2 = st.columns(2)

# CSV 导出
csv_buffer = io.StringIO()
schedule.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
col_dl1.download_button(
    label="📥 下载 CSV",
    data=csv_buffer.getvalue(),
    file_name="复利计算结果.csv",
    mime="text/csv",
)

# PDF 导出（纯 HTML → PDF，无需额外依赖）
def build_pdf_html(schedule_df: pd.DataFrame, params: dict) -> str:
    """用 HTML 构建一份可打印的报告，浏览器 / weasyprint 均可渲染。"""
    rows_html = ""
    for _, r in schedule_df.iterrows():
        rows_html += (
            f"<tr><td>{int(r['年份'])}</td>"
            f"<td>¥{r['年初余额']:,.2f}</td>"
            f"<td>¥{r['当年投入']:,.2f}</td>"
            f"<td>¥{r['当年利息']:,.2f}</td>"
            f"<td>¥{r['年末余额']:,.2f}</td>"
            f"<td>¥{r['累计投入']:,.2f}</td>"
            f"<td>{r['年化收益率(%)']:.2f}%</td></tr>"
        )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: "Microsoft YaHei", "SimHei", sans-serif; padding: 30px; color: #222; }}
  h1 {{ color: #333; }} h2 {{ color: #555; margin-top: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: right; font-size: 13px; }}
  th {{ background: #f5f5f5; }}
  .summary {{ display: flex; gap: 40px; margin: 16px 0; }}
  .summary div {{ background: #f9f9f9; padding: 12px 20px; border-radius: 6px; }}
  .label {{ font-size: 12px; color: #888; }} .value {{ font-size: 20px; font-weight: bold; }}
</style></head><body>
<h1>💰 复利计算报告</h1>
<p>投资模式：{params['mode']} | 本金：¥{params['principal']:,.2f} | 年化利率：{params['rate']:.2f}%
 | 年限：{params['years']}年 | 复利频率：{params['freq']}</p>
{"<p>定投：每期 ¥" + f"{params['contribution']:,.2f}" + f" × {params['contrib_freq']}次/年</p>" if params['contribution'] > 0 else ""}
<div class="summary">
  <div><div class="label">最终余额</div><div class="value">¥{params['final']:,.2f}</div></div>
  <div><div class="label">累计投入</div><div class="value">¥{params['total_in']:,.2f}</div></div>
  <div><div class="label">累计收益</div><div class="value">¥{params['interest']:,.2f}</div></div>
</div>
<h2>利率敏感性（±1%）</h2>
<p>利率 {max(0,params['rate']-1):.2f}% → ¥{params['lo']:,.2f} &nbsp;|&nbsp;
   当前 {params['rate']:.2f}% → ¥{params['final']:,.2f} &nbsp;|&nbsp;
   利率 {params['rate']+1:.2f}% → ¥{params['hi']:,.2f}</p>
<h2>每年余额明细</h2>
<table>
<tr><th>年份</th><th>年初余额</th><th>当年投入</th><th>当年利息</th><th>年末余额</th><th>累计投入</th><th>年化收益率</th></tr>
{rows_html}
</table>
<p style="margin-top:24px;font-size:11px;color:#aaa;">由复利计算器自动生成</p>
</body></html>"""

pdf_html = build_pdf_html(schedule, {
    "mode": mode,
    "principal": principal,
    "rate": annual_rate,
    "years": years,
    "freq": freq_label,
    "contribution": contribution,
    "contrib_freq": contrib_freq_n,
    "final": final["年末余额"],
    "total_in": final["累计投入"],
    "interest": total_interest,
    "lo": final_lo,
    "hi": final_hi,
})

col_dl2.download_button(
    label="📥 下载报告 (HTML/打印PDF)",
    data=pdf_html,
    file_name="复利计算报告.html",
    mime="text/html",
)
st.caption("提示：打开下载的 HTML 文件后，按 Ctrl+P 即可打印/另存为 PDF。")

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("提示：在左侧面板调整参数后结果会自动更新。运行命令：`streamlit run app.py`")
