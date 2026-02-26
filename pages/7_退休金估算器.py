"""退休金需求估算器

双阶段模型：退休前复利累积 → 退休后提领消耗。
通胀调整 + 敏感度分析 + Plotly 可视化。
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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


# ══════════════════════════════════════════════════════════
#  核心计算
# ══════════════════════════════════════════════════════════

@dataclass
class RetirementResult:
    # 关键数值
    years_to_retire: int
    years_in_retire: int
    future_monthly_expense: float    # 退休首年月生活费（通胀调整后）
    total_needed_at_retire: float    # 退休当天所需总资产
    projected_at_retire: float       # 按当前计划退休时累积的资产
    gap: float                       # 缺口（正=不足）
    extra_monthly_needed: float      # 每月还需额外储蓄
    # 逐年数据
    accumulation_path: pd.DataFrame  # 退休前累积路径
    target_path: pd.DataFrame        # 达成目标所需路径
    full_path: pd.DataFrame          # 退休前+退休后完整路径


def calculate_retirement(
    current_age: int,
    retire_age: int,
    life_expectancy: int,
    current_assets: float,
    monthly_saving: float,
    monthly_expense_today: float,
    inflation_pct: float,
    pre_return_pct: float,
    post_return_pct: float,
) -> RetirementResult:
    """双阶段退休金计算。"""

    years_to_retire = retire_age - current_age
    years_in_retire = life_expectancy - retire_age
    inf = inflation_pct / 100
    r_pre_m = pre_return_pct / 100 / 12   # 退休前月利率
    r_post = post_return_pct / 100         # 退休后年利率

    # ── 退休首年月生活费（通胀调整） ──
    future_monthly = monthly_expense_today * (1 + inf) ** years_to_retire

    # ── 退休当天所需总资产（年金现值） ──
    # 退休后实际利率 = (1+名义报酬)/(1+通胀) - 1
    real_post = (1 + r_post) / (1 + inf) - 1
    real_post_m = (1 + real_post) ** (1 / 12) - 1  # 月实际利率
    n_months_retire = years_in_retire * 12

    if real_post_m > 0:
        # PV of annuity（以退休首年月费为基准，实际利率折现）
        pv_factor = (1 - (1 + real_post_m) ** (-n_months_retire)) / real_post_m
    else:
        pv_factor = n_months_retire

    total_needed = future_monthly * pv_factor

    # ── 退休前按当前计划可累积的资产 ──
    n_months_pre = years_to_retire * 12
    balance = current_assets
    acc_rows: list[dict] = []

    for yr in range(years_to_retire + 1):
        age = current_age + yr
        if yr == 0:
            acc_rows.append({"年龄": age, "资产": balance, "类型": "当前计划"})
            continue
        for _ in range(12):
            balance = balance * (1 + r_pre_m) + monthly_saving
        acc_rows.append({"年龄": age, "资产": balance, "类型": "当前计划"})

    projected = balance
    gap = total_needed - projected

    # ── 每月额外需储蓄 ──
    if gap <= 0:
        extra_monthly = 0.0
    else:
        if r_pre_m > 0:
            # FV of annuity = PMT × [((1+r)^n - 1) / r]
            fv_factor = ((1 + r_pre_m) ** n_months_pre - 1) / r_pre_m
            extra_monthly = gap / fv_factor if fv_factor > 0 else gap / n_months_pre
        else:
            extra_monthly = gap / n_months_pre if n_months_pre > 0 else gap

    # ── 目标路径（需要的累积曲线） ──
    target_rows: list[dict] = []
    total_monthly_needed = monthly_saving + extra_monthly
    bal_target = current_assets
    for yr in range(years_to_retire + 1):
        age = current_age + yr
        if yr == 0:
            target_rows.append({"年龄": age, "资产": bal_target, "类型": "目标路径"})
            continue
        for _ in range(12):
            bal_target = bal_target * (1 + r_pre_m) + total_monthly_needed
        target_rows.append({"年龄": age, "资产": bal_target, "类型": "目标路径"})

    # ── 退休后提领路径 ──
    full_rows = list(acc_rows)  # 复制当前计划
    bal_post = projected
    r_post_m = (1 + r_post) ** (1 / 12) - 1
    for yr in range(1, years_in_retire + 1):
        age = retire_age + yr
        # 该年月生活费（持续通胀）
        expense_m = future_monthly * (1 + inf) ** yr
        for _ in range(12):
            bal_post = bal_post * (1 + r_post_m) - expense_m
            if bal_post < 0:
                bal_post = 0
        full_rows.append({"年龄": age, "资产": bal_post, "类型": "当前计划"})

    acc_df = pd.DataFrame(acc_rows)
    target_df = pd.DataFrame(target_rows)
    full_df = pd.DataFrame(full_rows)

    return RetirementResult(
        years_to_retire=years_to_retire,
        years_in_retire=years_in_retire,
        future_monthly_expense=future_monthly,
        total_needed_at_retire=total_needed,
        projected_at_retire=projected,
        gap=gap,
        extra_monthly_needed=extra_monthly,
        accumulation_path=acc_df,
        target_path=target_df,
        full_path=full_df,
    )


# ══════════════════════════════════════════════════════════
#  执行计算
# ══════════════════════════════════════════════════════════

result = calculate_retirement(
    current_age, retire_age, life_expectancy,
    current_assets, monthly_saving, monthly_expense,
    inflation, pre_return, post_return,
)

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
    f"¥{result.total_needed_at_retire:,.0f}",
    delta=f"退休首年月支出 ¥{result.future_monthly_expense:,.0f}",
    delta_color="off",
)
m2.metric(
    "📈 当前计划可累积",
    f"¥{result.projected_at_retire:,.0f}",
    delta=f"{'✅ 已充足' if result.gap <= 0 else f'缺口 ¥{result.gap:,.0f}'}",
    delta_color="normal" if result.gap <= 0 else "inverse",
)
m3.metric(
    "💰 每月还需额外储蓄",
    f"¥{result.extra_monthly_needed:,.0f}" if result.gap > 0 else "¥0（已充足）",
)

# 三档成功概率
prob_labels = []
for name, (pr, po) in scenarios.items():
    tag, _ = success_tag(pr, po)
    prob_labels.append(f"{name} {tag}")
m4.metric("📋 达成评估", prob_labels[1], delta=" | ".join(prob_labels), delta_color="off")

st.subheader("🧭 一页结论")
if result.gap <= 0:
    st.success("当前退休计划可覆盖退休资金需求，建议继续保持并定期复盘。")
else:
    st.warning(
        f"当前计划预计仍有缺口 ¥{result.gap:,.0f}，建议每月额外增加储蓄约 ¥{result.extra_monthly_needed:,.0f}。"
    )

# ── 成长曲线 ──────────────────────────────────────────────
st.subheader("📈 资产成长曲线")

LAYOUT_DARK = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict()),
    margin=dict(t=30, b=40),
    hovermode="x unified",
)

tab_acc, tab_full = st.tabs(["退休前累积阶段", "完整生命周期"])

with tab_acc:
    fig_acc = go.Figure()
    fig_acc.add_trace(go.Scatter(
        x=result.accumulation_path["年龄"],
        y=result.accumulation_path["资产"],
        mode="lines+markers", name="当前计划",
        line=dict(width=2.5, color="#636EFA"),
        hovertemplate="%{x} 岁<br>资产: ¥%{y:,.0f}<extra></extra>",
    ))
    fig_acc.add_trace(go.Scatter(
        x=result.target_path["年龄"],
        y=result.target_path["资产"],
        mode="lines", name="目标路径",
        line=dict(width=2, dash="dash", color="#00CC96"),
        hovertemplate="%{x} 岁<br>目标: ¥%{y:,.0f}<extra></extra>",
    ))
    fig_acc.add_hline(
        y=result.total_needed_at_retire, line_dash="dot", line_color="#EF553B",
        annotation_text=f"退休所需 ¥{result.total_needed_at_retire:,.0f}",
        annotation_position="top left", annotation_font_color="#EF553B",
    )
    fig_acc.update_layout(**LAYOUT_DARK, xaxis_title="年龄", yaxis_title="资产（元）", yaxis_tickformat=",")
    st.plotly_chart(fig_acc, use_container_width=True)

with tab_full:
    fig_full = go.Figure()
    full = result.full_path
    # 累积阶段
    pre_phase = full[full["年龄"] <= retire_age]
    post_phase = full[full["年龄"] >= retire_age]

    fig_full.add_trace(go.Scatter(
        x=pre_phase["年龄"], y=pre_phase["资产"],
        mode="lines", name="累积阶段",
        line=dict(width=2.5, color="#636EFA"),
        hovertemplate="%{x} 岁<br>资产: ¥%{y:,.0f}<extra></extra>",
    ))
    fig_full.add_trace(go.Scatter(
        x=post_phase["年龄"], y=post_phase["资产"],
        mode="lines", name="提领阶段",
        line=dict(width=2.5, color="#EF553B"),
        hovertemplate="%{x} 岁<br>资产: ¥%{y:,.0f}<extra></extra>",
    ))
    fig_full.add_vline(
        x=retire_age, line_dash="dot", line_color="#FFD600",
        annotation_text=f"退休 {retire_age} 岁", annotation_font_color="#FFD600",
    )

    # 资产归零警示
    depleted = post_phase[post_phase["资产"] <= 0]
    if not depleted.empty:
        deplete_age = depleted.iloc[0]["年龄"]
        fig_full.add_vline(
            x=deplete_age, line_dash="dash", line_color="#ff1744",
            annotation_text=f"⚠️ 资产归零 {int(deplete_age)} 岁",
            annotation_font_color="#ff1744",
        )

    fig_full.update_layout(**LAYOUT_DARK, xaxis_title="年龄", yaxis_title="资产（元）", yaxis_tickformat=",")
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
            "退休所需": f"¥{r.total_needed_at_retire:,.0f}",
            "可累积": f"¥{r.projected_at_retire:,.0f}",
            "缺口": f"¥{r.gap:,.0f}" if r.gap > 0 else "✅ 充足",
            "额外月存": f"¥{r.extra_monthly_needed:,.0f}" if r.gap > 0 else "¥0",
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
        "年初资产": f"¥{start:,.0f}",
        "当年投入": f"¥{monthly_saving * 12:,.0f}",
        "当年收益": f"¥{yr_interest:,.0f}",
        "年末资产": f"¥{bal:,.0f}",
    })

if yearly_rows:
    st.dataframe(pd.DataFrame(yearly_rows), use_container_width=True, hide_index=True, height=400)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("🏖️ 退休金需求估算器 | 仅供参考，不构成投资建议 | 运行：`streamlit run app.py`")
