"""退休金需求估算器

双阶段模型：退休前复利累积 → 退休后提领消耗。
通胀调整 + 敏感度分析 + Plotly 可视化。

v1.4: 核心计算已下沉到 core/retirement.py；图表货币符号动态引用。
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.chart_config import build_layout
from core.currency import currency_selector, fmt, fmt_delta, get_symbol
from core.retirement import RetirementResult, calculate_retirement
from core.storage import scheme_manager_ui

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="退休金估算器", page_icon="🏖️", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .stMetric { background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 8px; padding: 14px; }
</style>
""", unsafe_allow_html=True)

st.title("🏖️ 退休金需求估算器")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("👤 退休前参数")
currency_selector()

current_age = st.sidebar.number_input("目前年龄", 18, 80, 35)
retire_age = st.sidebar.number_input("预计退休年龄", current_age + 1, 90, max(65, current_age + 1))
current_assets = st.sidebar.number_input(
    "目前已累积退休资产（元）", 0.0, 50_000_000.0, 500_000.0, step=50_000.0, format="%.0f",
)
monthly_saving = st.sidebar.number_input(
    "退休前每月可投入（元）", 0.0, 500_000.0, 10_000.0, step=1_000.0, format="%.0f",
)
pre_return = st.sidebar.number_input(
    "退休前年化报酬率（%）", 0.0, 20.0, 7.0, step=0.1, format="%.1f",
)

st.sidebar.divider()
st.sidebar.header("🏖️ 退休后参数")

life_expectancy = st.sidebar.number_input("预期寿命", retire_age + 1, 120, max(85, retire_age + 1))
monthly_expense = st.sidebar.number_input(
    "退休后每月生活费（今日币值，元）", 5_000.0, 500_000.0, 30_000.0, step=1_000.0, format="%.0f",
)
inflation = st.sidebar.number_input(
    "年平均通胀率（%）", 0.0, 10.0, 2.5, step=0.1, format="%.1f",
)
post_return = st.sidebar.number_input(
    "退休后年化报酬率（%）", 0.0, 15.0, 4.0, step=0.1, format="%.1f",
)

scheme_manager_ui("retirement", {
    "current_age": current_age,
    "retire_age": retire_age,
    "current_assets": current_assets,
    "monthly_saving": monthly_saving,
    "pre_return": pre_return,
    "life_expectancy": life_expectancy,
    "monthly_expense": monthly_expense,
    "inflation": inflation,
    "post_return": post_return,
})

# ══════════════════════════════════════════════════════════
#  执行计算
# ══════════════════════════════════════════════════════════

result = calculate_retirement(
    current_age, retire_age, life_expectancy,
    current_assets, monthly_saving, monthly_expense,
    inflation, pre_return, post_return,
)

st.session_state["dashboard_retirement"] = {
    "gap": result.gap,
    "extra_monthly": result.extra_monthly_needed,
}

sym = get_symbol()


# ── 成功概率估计（三档） ──────────────────────────────────
def success_tag(pre_r: float, post_r: float) -> tuple[str, str]:
    r = calculate_retirement(
        current_age, retire_age, life_expectancy,
        current_assets, monthly_saving, monthly_expense,
        inflation, pre_r, post_r,
    )
    if r.gap <= 0:
        return "✅ 可达成", "off"
    return "❌ 不足", "inverse"


scenarios = {
    "保守": (max(0, pre_return - 2), max(0, post_return - 1)),
    "基准": (pre_return, post_return),
    "积极": (pre_return + 2, post_return + 1),
}

# ── 核心指标 ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 核心结果")

m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "🎯 退休所需总资产",
    fmt(result.total_needed_at_retire, decimals=0),
    delta=f"退休首年月支出 {fmt(result.future_monthly_expense, decimals=0)}",
    delta_color="off",
)
m2.metric(
    "📈 当前计划可累积",
    fmt(result.projected_at_retire, decimals=0),
    delta=f"{'✅ 已充足' if result.gap <= 0 else f'缺口 {fmt(result.gap, decimals=0)}'}",
    delta_color="normal" if result.gap <= 0 else "inverse",
)
m3.metric(
    "💰 每月还需额外储蓄",
    fmt(result.extra_monthly_needed, decimals=0) if result.gap > 0 else f"{fmt(0, decimals=0)}（已充足）",
)

prob_labels = []
for name, (pr, po) in scenarios.items():
    tag, _ = success_tag(pr, po)
    prob_labels.append(f"{name} {tag}")
m4.metric("📋 达成评估", prob_labels[1], delta=" | ".join(prob_labels), delta_color="off")

st.subheader("🧭 一页结论")
if result.gap <= 0:
    st.success("结论：当前退休计划可覆盖资金需求。")
    st.caption(f"原因：预计退休时可累积 {fmt(result.projected_at_retire, decimals=0)}，高于所需 {fmt(result.total_needed_at_retire, decimals=0)}。")
    st.caption("下一步：保持定投并每年复盘通胀和收益率假设。")
else:
    st.warning("结论：当前退休计划仍有资金缺口。")
    st.caption(f"原因：预计缺口 {fmt(result.gap, decimals=0)}。")
    st.caption(f"下一步：建议每月额外增加储蓄约 {fmt(result.extra_monthly_needed, decimals=0)}，并结合延后退休年龄评估。")

# ── 成长曲线 ──────────────────────────────────────────────
st.subheader("📈 资产成长曲线")

tab_acc, tab_full = st.tabs(["退休前累积阶段", "完整生命周期"])

with tab_acc:
    fig_acc = go.Figure()
    fig_acc.add_trace(go.Scatter(
        x=result.accumulation_path["年龄"],
        y=result.accumulation_path["资产"],
        mode="lines+markers", name="当前计划",
        line=dict(width=2.5, color="#636EFA"),
        hovertemplate=f"%{{x}} 岁<br>资产: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_acc.add_trace(go.Scatter(
        x=result.target_path["年龄"],
        y=result.target_path["资产"],
        mode="lines", name="目标路径",
        line=dict(width=2, dash="dash", color="#00CC96"),
        hovertemplate=f"%{{x}} 岁<br>目标: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_acc.add_hline(
        y=result.total_needed_at_retire, line_dash="dot", line_color="#EF553B",
        annotation_text=f"退休所需 {fmt(result.total_needed_at_retire, decimals=0)}",
        annotation_position="top left", annotation_font_color="#EF553B",
    )
    fig_acc.update_layout(
        **build_layout(xaxis_title="年龄", yaxis_title="资产（元）", yaxis_tickformat=","),
    )
    st.plotly_chart(fig_acc, use_container_width=True)

with tab_full:
    fig_full = go.Figure()
    full = result.full_path
    pre_phase = full[full["年龄"] <= retire_age]
    post_phase = full[full["年龄"] >= retire_age]

    fig_full.add_trace(go.Scatter(
        x=pre_phase["年龄"], y=pre_phase["资产"],
        mode="lines", name="累积阶段",
        line=dict(width=2.5, color="#636EFA"),
        hovertemplate=f"%{{x}} 岁<br>资产: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_full.add_trace(go.Scatter(
        x=post_phase["年龄"], y=post_phase["资产"],
        mode="lines", name="提领阶段",
        line=dict(width=2.5, color="#EF553B"),
        hovertemplate=f"%{{x}} 岁<br>资产: {sym}%{{y:,.0f}}<extra></extra>",
    ))
    fig_full.add_vline(
        x=retire_age, line_dash="dot", line_color="#FFD600",
        annotation_text=f"退休 {retire_age} 岁", annotation_font_color="#FFD600",
    )

    depleted = post_phase[post_phase["资产"] <= 0]
    if not depleted.empty:
        deplete_age = depleted.iloc[0]["年龄"]
        fig_full.add_vline(
            x=deplete_age, line_dash="dash", line_color="#ff1744",
            annotation_text=f"⚠️ 资产归零 {int(deplete_age)} 岁",
            annotation_font_color="#ff1744",
        )

    fig_full.update_layout(
        **build_layout(xaxis_title="年龄", yaxis_title="资产（元）", yaxis_tickformat=","),
    )
    st.plotly_chart(fig_full, use_container_width=True)

# ── 敏感度分析 ────────────────────────────────────────────
st.subheader("🔍 敏感度分析")

sens_rows: list[dict] = []
for d_ret in [-1.0, 0.0, 1.0]:
    for d_inf in [-0.5, 0.0, 0.5]:
        r = calculate_retirement(
            current_age, retire_age, life_expectancy,
            current_assets, monthly_saving, monthly_expense,
            inflation + d_inf, pre_return + d_ret, post_return + d_ret * 0.5,
        )
        sens_rows.append({
            "报酬率调整": f"{d_ret:+.1f}%",
            "通胀率调整": f"{d_inf:+.1f}%",
            "退休前报酬": f"{pre_return + d_ret:.1f}%",
            "通胀率": f"{inflation + d_inf:.1f}%",
            "退休所需": fmt(r.total_needed_at_retire, decimals=0),
            "可累积": fmt(r.projected_at_retire, decimals=0),
            "缺口": fmt(r.gap, decimals=0) if r.gap > 0 else "✅ 充足",
            "额外月存": fmt(r.extra_monthly_needed, decimals=0) if r.gap > 0 else fmt(0, decimals=0),
        })

sens_df = pd.DataFrame(sens_rows)
st.dataframe(sens_df, use_container_width=True, hide_index=True)

# ── 逐年明细 ──────────────────────────────────────────────
st.subheader("📋 退休前逐年累积明细")

yearly_rows: list[dict] = []
bal = current_assets
r_m = pre_return / 100 / 12
for yr in range(1, result.years_to_retire + 1):
    start = bal
    yr_interest = 0.0
    for _ in range(12):
        interest = bal * r_m
        yr_interest += interest
        bal = bal + interest + monthly_saving
    yearly_rows.append({
        "年份": f"第 {yr} 年（{current_age + yr} 岁）",
        "年初资产": fmt(start, decimals=0),
        "当年投入": fmt(monthly_saving * 12, decimals=0),
        "当年收益": fmt(yr_interest, decimals=0),
        "年末资产": fmt(bal, decimals=0),
    })

if yearly_rows:
    st.dataframe(pd.DataFrame(yearly_rows), use_container_width=True, hide_index=True, height=400)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("🏖️ 退休金需求估算器 | 仅供参考，不构成投资建议 | 运行：`streamlit run app.py`")
