"""动态蒙特卡洛模拟 — 退休金规划风险评估

基于历史波动率或用户自定义分布，生成大量可能的收益路径。
展示不同置信区间（10% / 25% / 50% / 75% / 90%）下的资产变化，
使退休规划更具风险意识。
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.chart_config import build_layout, render_empty_state
from core.config import CFG, MSG
from core.currency import currency_selector, fmt, get_symbol
from core.export import dataframes_to_excel
from core.montecarlo import run_retirement_montecarlo

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="蒙特卡洛模拟", page_icon="🎲", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .stMetric { background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 8px; padding: 14px; }
</style>
""", unsafe_allow_html=True)

st.title("🎲 动态蒙特卡洛退休规划模拟")
st.caption("基于随机收益路径，量化退休资产的不确定性。置信区间宽度越宽，说明结果不确定性越高。")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("👤 基础参数")
pass

current_age = st.sidebar.number_input("目前年龄", 18, 80, 35)
retire_age = st.sidebar.number_input("预计退休年龄", current_age + 1, 90, max(65, current_age + 1))
life_expectancy = st.sidebar.number_input("预期寿命", retire_age + 1, 120, max(85, retire_age + 1))

# Validate ages
if retire_age <= current_age:
    st.sidebar.error(f"❌ 退休年龄（{retire_age}岁）必须大于目前年龄（{current_age}岁）。")
    st.stop()
if life_expectancy <= retire_age:
    st.sidebar.error(f"❌ 预期寿命（{life_expectancy}岁）必须大于退休年龄（{retire_age}岁）。")
    st.stop()

current_assets = st.sidebar.number_input(
    "目前已累积退休资产（元）",
    0.0, CFG.retirement.current_assets_max, CFG.retirement.current_assets_default,
    step=CFG.retirement.current_assets_step, format="%.0f",
)
monthly_saving = st.sidebar.number_input(
    "退休前每月可投入（元）",
    0.0, CFG.retirement.monthly_saving_max, CFG.retirement.monthly_saving_default,
    step=CFG.retirement.monthly_saving_step, format="%.0f",
)
monthly_expense = st.sidebar.number_input(
    "退休后每月生活费（今日币值，元）",
    CFG.retirement.monthly_expense_min, CFG.retirement.monthly_expense_max,
    CFG.retirement.monthly_expense_default, step=CFG.retirement.monthly_expense_step,
    format="%.0f",
)
inflation = st.sidebar.number_input(
    "年平均通胀率（%）",
    0.0, CFG.retirement.inflation_max, CFG.retirement.inflation_default,
    step=CFG.retirement.inflation_step, format="%.1f",
)

st.sidebar.divider()
st.sidebar.header("📈 收益率与波动率假设")

pre_return = st.sidebar.number_input(
    "退休前预期年化报酬率（%）",
    0.0, CFG.retirement.pre_return_max, CFG.retirement.pre_return_default,
    step=CFG.retirement.pre_return_step, format="%.1f",
)
pre_volatility = st.sidebar.number_input(
    "退休前年化波动率（%）",
    0.0, 60.0, 15.0, step=0.5, format="%.1f",
    help="年化标准差，衡量收益不确定性。股票型基金约 15–25%；债券型约 5–10%。",
)
post_return = st.sidebar.number_input(
    "退休后预期年化报酬率（%）",
    0.0, CFG.retirement.post_return_max, CFG.retirement.post_return_default,
    step=CFG.retirement.post_return_step, format="%.1f",
)
post_volatility = st.sidebar.number_input(
    "退休后年化波动率（%）",
    0.0, 40.0, 8.0, step=0.5, format="%.1f",
)

st.sidebar.divider()
st.sidebar.header("⚙️ 模拟参数")

n_simulations = st.sidebar.select_slider(
    "模拟次数",
    options=[500, 1000, 2000, 5000],
    value=2000,
    help="模拟次数越多结果越稳定，但计算耗时增加。",
)

# ── 执行模拟（带缓存，避免每次参数微调都重新运行） ────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def _cached_montecarlo(
    current_age: int,
    retire_age: int,
    life_expectancy: int,
    current_assets: float,
    monthly_saving: float,
    monthly_expense: float,
    inflation: float,
    pre_return: float,
    pre_volatility: float,
    post_return: float,
    post_volatility: float,
    n_simulations: int,
):
    return run_retirement_montecarlo(
        current_age=current_age,
        retire_age=retire_age,
        life_expectancy=life_expectancy,
        current_assets=current_assets,
        monthly_saving=monthly_saving,
        monthly_expense_today=monthly_expense,
        inflation_pct=inflation,
        expected_annual_return_pct=pre_return,
        annual_volatility_pct=pre_volatility,
        post_return_pct=post_return,
        post_volatility_pct=post_volatility,
        n_simulations=n_simulations,
    )


with st.spinner(f"正在运行 {n_simulations:,} 次蒙特卡洛模拟…"):
    mc = _cached_montecarlo(
        current_age,
        retire_age,
        life_expectancy,
        current_assets,
        monthly_saving,
        monthly_expense,
        inflation,
        pre_return,
        pre_volatility,
        post_return,
        post_volatility,
        n_simulations,
    )

sym = get_symbol()

# ── 核心指标 ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 模拟结果摘要")

m1, m2, m3, m4 = st.columns(4)
success_color = "normal" if mc.success_rate >= 0.7 else "inverse"
m1.metric(
    "✅ 资产不耗尽概率",
    f"{mc.success_rate:.1%}",
    delta=f"共 {mc.n_success:,} / {mc.n_simulations:,} 条路径成功",
    delta_color="off",
)

p50_at_retire = mc.percentile_paths.loc[
    mc.percentile_paths["年龄"] == retire_age, "p50"
].values
m2.metric(
    "📈 中位数退休资产 (p50)",
    fmt(float(p50_at_retire[0]), decimals=0) if len(p50_at_retire) > 0 else "—",
    delta=f"退休年龄 {retire_age} 岁时",
    delta_color="off",
)

p10_at_retire = mc.percentile_paths.loc[
    mc.percentile_paths["年龄"] == retire_age, "p10"
].values
m3.metric(
    "⚠️ 悲观情景资产 (p10)",
    fmt(float(p10_at_retire[0]), decimals=0) if len(p10_at_retire) > 0 else "—",
    delta="10% 概率低于此值",
    delta_color="off",
)

if not pd.isna(mc.median_depletion_age):
    m4.metric(
        "🕐 中位数资产耗尽年龄",
        f"{int(mc.median_depletion_age)} 岁",
        delta="⚠️ 中位数情景下资产耗尽",
        delta_color="inverse",
    )
else:
    m4.metric("🕐 资产耗尽风险", "无（中位数全程充足）", delta="✅ 中位数情景下资产未耗尽", delta_color="off")

# ── 成功率解读 ────────────────────────────────────────────
if mc.success_rate >= 0.90:
    st.success(f"✅ **高置信度**：{mc.success_rate:.1%} 的模拟路径中资产可维持至 {life_expectancy} 岁，退休规划稳健。")
elif mc.success_rate >= 0.70:
    st.warning(f"⚠️ **中等置信度**：{mc.success_rate:.1%} 的路径可维持至 {life_expectancy} 岁，建议适当增加储蓄或降低支出预期。")
else:
    st.error(f"❌ **高风险**：仅 {mc.success_rate:.1%} 的路径可维持至 {life_expectancy} 岁，建议显著调整退休计划（增加储蓄、延后退休或降低支出）。")

# ── 置信区间曲线图 ────────────────────────────────────────
st.subheader("📈 资产变化置信区间")

fp = mc.percentile_paths

if fp.empty:
    render_empty_state(title="模拟数据为空", message="请检查输入参数后重试。", icon="🎲")
else:
    fig = go.Figure()

    # Shaded band p10–p90
    fig.add_trace(go.Scatter(
        x=pd.concat([fp["年龄"], fp["年龄"][::-1]]),
        y=pd.concat([fp["p90"], fp["p10"][::-1]]),
        fill="toself",
        fillcolor="rgba(99,110,250,0.12)",
        line=dict(color="rgba(255,255,255,0)"),
        hoverinfo="skip",
        name="p10–p90 区间",
        showlegend=True,
    ))
    # p25–p75 band
    fig.add_trace(go.Scatter(
        x=pd.concat([fp["年龄"], fp["年龄"][::-1]]),
        y=pd.concat([fp["p75"], fp["p25"][::-1]]),
        fill="toself",
        fillcolor="rgba(99,110,250,0.22)",
        line=dict(color="rgba(255,255,255,0)"),
        hoverinfo="skip",
        name="p25–p75 区间",
        showlegend=True,
    ))
    # Percentile lines
    for col, label, color, dash in [
        ("p90", "乐观 p90", "#00CC96", "dot"),
        ("p75", "p75", "#636EFA", "dash"),
        ("p50", "中位数 p50", "#636EFA", "solid"),
        ("p25", "p25", "#EF553B", "dash"),
        ("p10", "悲观 p10", "#EF553B", "dot"),
    ]:
        fig.add_trace(go.Scatter(
            x=fp["年龄"], y=fp[col],
            mode="lines",
            name=label,
            line=dict(color=color, width=1.8 if col == "p50" else 1.2, dash=dash),
            hovertemplate=f"%{{x}} 岁<br>{label}: {sym}%{{y:,.0f}}<extra></extra>",
        ))

    # Retire age vertical line
    fig.add_vline(
        x=retire_age, line_dash="dot", line_color="#FFD600",
        annotation_text=f"退休 {retire_age} 岁", annotation_font_color="#FFD600",
    )

    fig.update_layout(**build_layout(
        xaxis_title="年龄",
        yaxis_title=f"资产（{sym}）",
        yaxis_tickformat=",",
    ))
    st.plotly_chart(fig, use_container_width=True)

# ── 退休时资产分布直方图 ──────────────────────────────────
st.subheader("📊 退休时资产分布说明")
st.caption(
    f"各百分位数反映了 {n_simulations:,} 次模拟中，在退休年龄（{retire_age}岁）时的资产累积范围。"
    f"p10 代表最悲观的 10% 情景，p90 代表最乐观的 10% 情景。"
)

dist_rows = []
_PERCENTILE_LABELS = [
    ("p10", "p10（悲观）"),
    ("p25", "p25"),
    ("p50", "p50（中位数）"),
    ("p75", "p75"),
    ("p90", "p90（乐观）"),
]
_age_mask = fp["年龄"] == retire_age
for col, label in _PERCENTILE_LABELS:
    val = fmt(float(fp.loc[_age_mask, col].iloc[0]), decimals=0) if _age_mask.any() else "—"
    dist_rows.append({"百分位": label, "退休时资产": val})
st.dataframe(pd.DataFrame(dist_rows), use_container_width=True, hide_index=True)

# ── 逐年中位数资产明细 ────────────────────────────────────
with st.expander("📋 逐年百分位数明细"):
    display_fp = fp.copy()
    for col in ["p10", "p25", "p50", "p75", "p90"]:
        display_fp[col] = display_fp[col].apply(lambda v: fmt(v, decimals=0))
    display_fp = display_fp.rename(columns={
        "年龄": "年龄",
        "p10": "悲观 p10",
        "p25": "p25",
        "p50": "中位数 p50",
        "p75": "p75",
        "p90": "乐观 p90",
    })
    st.dataframe(display_fp, use_container_width=True, hide_index=True, height=400)

# ── 导出 ─────────────────────────────────────────────────
st.subheader("📤 导出数据")
_xlsx_bytes = dataframes_to_excel(
    sheets=[("置信区间路径", fp), ("分布汇总", pd.DataFrame(dist_rows))],
    title=f"蒙特卡洛退休模拟 — {n_simulations:,} 次",
)
st.download_button(
    "📊 下载数据 (Excel)",
    data=_xlsx_bytes,
    file_name="蒙特卡洛模拟.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── 参数假设说明 ──────────────────────────────────────────
with st.expander("ℹ️ 方法论说明"):
    st.markdown(f"""
**模拟方法**：对数正态随机收益路径（Log-normal Monthly Returns）

- 退休前年化期望收益：**{pre_return:.1f}%**，年化波动率：**{pre_volatility:.1f}%**
- 退休后年化期望收益：**{post_return:.1f}%**，年化波动率：**{post_volatility:.1f}%**
- 每个月的随机收益 $r_t$ 服从正态分布 $N(\\mu_m, \\sigma_m)$，其中
  $\\mu_m = \\ln(1 + r_{{annual}}) / 12$，$\\sigma_m = \\sigma_{{annual}} / \\sqrt{{12}}$
- 共运行 **{n_simulations:,}** 条独立路径
- 成功定义：在预期寿命（{life_expectancy}岁）时资产余额仍大于零

**注意事项**：
1. 本模拟基于参数假设，实际市场波动可能更极端（厚尾风险）。
2. 未考虑税收、通胀以外的流动性风险、重大支出冲击等。
3. 仅供参考，不构成投资建议。
""")

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("🎲 蒙特卡洛退休规划模拟 | 仅供参考，不构成投资建议 | 运行：`streamlit run app.py`")
