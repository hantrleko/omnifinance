"""50/30/20 预算分配建议器

根据税后月收入，按经典 50/30/20 法则给出分配建议。
支持手动调比例、固定支出超标警示、高利债务优先还债。
"""

import json
import os
from datetime import date as _date
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from core.theme import inject_theme

inject_theme()

from core.benchmarks import benchmark_inline
from core.chart_config import build_layout
from core.config import CFG, MSG
from core.currency import currency_selector, fmt, fmt_delta, get_symbol
from core.planning import calculate_budget
from core.storage import scheme_manager_ui

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="预算分配建议器", page_icon="💡", layout="wide")


st.title("💡 50/30/20 预算分配建议器")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 收入与支出")

income = st.sidebar.number_input(
    "月收入（税后，元）",
    min_value=CFG.budget.income_min,
    max_value=CFG.budget.income_max,
    value=CFG.budget.income_default,
    step=CFG.budget.income_step,
    format="%.0f",
)
fixed_expense = st.sidebar.number_input(
    "已知固定必需支出（元）",
    min_value=0.0,
    max_value=income,
    value=0.0,
    step=CFG.budget.fixed_expense_step,
    format="%.0f",
    help=MSG.budget_fixed_help,
)
has_debt = st.sidebar.checkbox("有高利债务（信用卡/消费贷等）", value=False)

st.sidebar.divider()
st.sidebar.subheader("⚙️ 自定义比例")
st.sidebar.caption("拖动滑杆调整分配比例（三项合计须为 100%）")

pct_needs = st.sidebar.slider("必需支出占比（%）", 0, 100, int(CFG.budget.needs_ratio * 100), key="needs")
pct_wants = st.sidebar.slider("想要支出占比（%）", 0, 100, int(CFG.budget.wants_ratio * 100), key="wants")
pct_save = 100 - pct_needs - pct_wants

if pct_save < 0:
    st.sidebar.error(f"⚠️ 必需 + 想要 = {pct_needs + pct_wants}%，超过 100%！请调低。")
    pct_save = 0

st.sidebar.metric("储蓄/还债占比", f"{pct_save}%",
                   delta=f"{'✅ 合计 100%' if pct_needs + pct_wants + pct_save == 100 else '❌ 不足 100%'}",
                   delta_color="off")

scheme_manager_ui("budget", {
    "income": income,
    "fixed_expense": fixed_expense,
    "has_debt": has_debt,
    "pct_needs": pct_needs,
    "pct_wants": pct_wants,
})

# ── 计算 ──────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _cached_budget(income: float, fixed_expense: float, pct_needs: int, pct_wants: int):
    return calculate_budget(income, fixed_expense, pct_needs, pct_wants)

plan = _cached_budget(income, fixed_expense, pct_needs, pct_wants)
amt_needs = plan.amt_needs
amt_wants = plan.amt_wants
amt_save = plan.amt_save
pct_save = plan.pct_save
remaining_needs = plan.remaining_needs
fixed_pct = plan.fixed_pct

save_label = "储蓄 / 还债" if has_debt else "储蓄 / 投资"

st.session_state["dashboard_budget"] = {
    "income": income,
    "amt_save": amt_save,
    "pct_save": pct_save,
}

# ── 核心指标 ──────────────────────────────────────────────
st.markdown("---")

c1, c2, c3 = st.columns(3)
c1.metric("🏠 必需支出", fmt(amt_needs, decimals=0), delta=f"{pct_needs}%", delta_color="off")
c2.metric("🎉 想要支出", fmt(amt_wants, decimals=0), delta=f"{pct_wants}%", delta_color="off")
c3.metric(f"💰 {save_label}", fmt(amt_save, decimals=0), delta=f"{pct_save}%", delta_color="off")

benchmark_inline("monthly_income", income, label="月收入")
benchmark_inline("savings_rate", float(pct_save), label="储蓄率")

# ── 固定支出超标警示 ──────────────────────────────────────
if fixed_expense > 0:
    st.markdown("---")
    if fixed_expense > amt_needs:
        over = fixed_expense - amt_needs
        st.error(
            f"🚨 **固定必需支出（{fmt(fixed_expense, decimals=0)}）已超过必需预算（{fmt(amt_needs, decimals=0)}）** "
            f"— 超支 {fmt(over, decimals=0)}（占收入 {fixed_pct:.1f}% > {pct_needs}%）。\n\n"
            f"建议：降低固定支出、增加收入，或将必需占比上调至 {int(fixed_pct) + 5}% 以上。"
        )
    elif fixed_expense > amt_needs * 0.8:
        st.warning(
            f"⚠️ 固定支出 {fmt(fixed_expense, decimals=0)} 已占必需预算的 {fixed_expense / amt_needs * 100:.0f}%，"
            f"仅剩 {fmt(remaining_needs, decimals=0)} 用于其他必需开销（餐饮/交通等）。"
        )
    else:
        st.success(
            f"✅ 固定支出 {fmt(fixed_expense, decimals=0)} 占必需预算的 {fixed_expense / amt_needs * 100:.0f}%，"
            f"剩余 {fmt(remaining_needs, decimals=0)} 可用于其他必需开销。"
        )

# ── 圆环图 ────────────────────────────────────────────────
st.subheader("📊 预算分配图")

labels = ["🏠 必需支出", "🎉 想要支出", f"💰 {save_label}"]
values = [amt_needs, amt_wants, amt_save]
colors = ["#636EFA", "#EF553B", "#00CC96"]

fig = go.Figure(data=[go.Pie(
    labels=labels,
    values=values,
    hole=0.55,
    marker=dict(colors=colors, line=dict(color="white", width=3)),
    textinfo="label+percent",
    textfont=dict(size=14),
    hovertemplate=f"%{{label}}<br>{get_symbol()}%{{value:,.0f}}<br>%{{percent}}<extra></extra>",
)])

fig.update_layout(
    showlegend=False,
    margin=dict(t=20, b=20, l=20, r=20),
    height=400,
    annotations=[dict(
        text=f"{fmt(income, decimals=0)}<br><span style='font-size:13px;color:#888'>月收入</span>",
        x=0.5, y=0.5, font_size=22,
        showarrow=False,
    )],
)
st.plotly_chart(fig, use_container_width=True)

# ── 明细分解 ──────────────────────────────────────────────
st.subheader("📋 分配明细")

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("#### 🏠 必需支出")
    st.markdown(f"- **预算总额：** {fmt(amt_needs, decimals=0)}")
    if fixed_expense > 0:
        st.markdown(f"- 固定支出：{fmt(fixed_expense, decimals=0)}")
        st.markdown(f"- 弹性必需：{fmt(remaining_needs, decimals=0)}")
    st.caption(MSG.budget_needs_caption)

with col_b:
    st.markdown("#### 🎉 想要支出")
    st.markdown(f"- **预算总额：** {fmt(amt_wants, decimals=0)}")
    st.caption(MSG.budget_wants_caption)

with col_c:
    st.markdown(f"#### 💰 {save_label}")
    st.markdown(f"- **预算总额：** {fmt(amt_save, decimals=0)}")
    if has_debt:
        st.markdown(f"- 🔴 优先还债：{fmt(amt_save * 0.7, decimals=0)}（建议 70%）")
        st.markdown(f"- 应急储蓄：{fmt(amt_save * 0.3, decimals=0)}（建议 30%）")
        st.caption(MSG.budget_debt_caption)
    else:
        st.markdown(f"- 应急基金：{fmt(amt_save * 0.5, decimals=0)}（建议 50%）")
        st.markdown(f"- 长期投资：{fmt(amt_save * 0.5, decimals=0)}（建议 50%）")
        st.caption(MSG.budget_emergency_caption)

# ── 个性化建议 ────────────────────────────────────────────
st.markdown("---")
st.subheader("💬 个性化建议")

tips: list[str] = []

if fixed_pct > 50:
    tips.append("📌 你的固定支出占比偏高，建议检视是否有可精简的订阅或保险，或考虑搬到租金更低的住所。")
elif fixed_pct > 40:
    tips.append("📌 固定支出接近警戒线，留意未来不要再增加固定承诺（如车贷），保持弹性空间。")

if has_debt:
    tips.append("🔴 **优先处理高利债务！** 信用卡 / 消费贷年利率通常 12–18%，远超投资回报。建议用雪球法或雪崩法集中还清。")

if pct_save >= 20:
    tips.append(f"✅ 储蓄率 {pct_save}% 很健康！坚持下去，{int(income * pct_save / 100 * 12):,} 元/年的积累会产生可观的复利效果。")
elif pct_save >= 10:
    tips.append(f"⚠️ 储蓄率 {pct_save}% 略低于建议的 20%，可以从「想要支出」中找到可削减的项目。")
else:
    tips.append(f"🚨 储蓄率仅 {pct_save}%，财务安全垫不足。建议至少提升到 10% 以建立应急基金。")

if income >= 100_000:
    tips.append("💡 高收入情况下，可考虑将储蓄比例提升至 30–40%，加速资产累积。")

if not tips:
    tips.append("👍 你的预算分配看起来很合理，继续保持！")

for tip in tips:
    st.markdown(tip)

# ── 记账本联动：本月实际支出 vs 预算 ─────────────────────
st.markdown("---")
st.subheader("🔗 本月实际支出 vs 预算")
st.caption("读取收支记账本的当月支出，与当前预算设置进行对比。请先在「收支记账本」页面录入支出记录。")

_LEDGER_PATH = Path(os.path.expanduser("~")) / ".omnifinance" / "ledger.json"

def _load_current_month_expenses() -> dict[str, float]:
    if not _LEDGER_PATH.exists():
        return {}
    try:
        data = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return {}
    except (json.JSONDecodeError, OSError):
        return {}

    today = _date.today()
    cat_totals: dict[str, float] = {}
    for entry in data:
        if entry.get("type") != "支出":
            continue
        try:
            entry_date = _date.fromisoformat(entry["date"])
        except (KeyError, ValueError):
            continue
        if entry_date.year == today.year and entry_date.month == today.month:
            cat = entry.get("category", "其他支出")
            cat_totals[cat] = cat_totals.get(cat, 0.0) + float(entry.get("amount", 0))
    return cat_totals

_actual_by_cat = _load_current_month_expenses()
_total_actual = sum(_actual_by_cat.values())

if _total_actual > 0:
    _lc1, _lc2, _lc3 = st.columns(3)
    _lc1.metric("本月实际支出", fmt(_total_actual, decimals=0))
    _lc2.metric("预算总额（必需+想要）", fmt(amt_needs + amt_wants, decimals=0))
    _budget_left = (amt_needs + amt_wants) - _total_actual
    _lc3.metric(
        "剩余预算",
        fmt(abs(_budget_left), decimals=0),
        delta="超出预算" if _budget_left < 0 else "预算内",
        delta_color="inverse" if _budget_left < 0 else "normal",
    )

    # Bar chart: actual vs budget by category
    _EXPENSE_CATS_ALL = ["餐饮", "购物", "交通", "居住", "医疗", "教育", "娱乐", "旅行", "保险", "还贷", "其他支出"]
    _cats_with_actual = sorted(_actual_by_cat.keys())

    # Per-category budget allocation: evenly distribute needs/wants by category count
    _needs_cats = ["居住", "餐饮", "交通", "医疗", "教育", "保险", "还贷"]
    _wants_cats = ["购物", "娱乐", "旅行", "其他支出"]
    _n_needs_shown = sum(1 for c in _cats_with_actual if c in _needs_cats) or 1
    _n_wants_shown = sum(1 for c in _cats_with_actual if c in _wants_cats) or 1

    _bar_cats, _bar_actual, _bar_budget, _bar_colors = [], [], [], []
    for cat in _cats_with_actual:
        actual = _actual_by_cat[cat]
        if cat in _needs_cats:
            est_budget = amt_needs / _n_needs_shown
        else:
            est_budget = amt_wants / _n_wants_shown
        _bar_cats.append(cat)
        _bar_actual.append(actual)
        _bar_budget.append(est_budget)
        _bar_colors.append("#EF553B" if actual > est_budget else "#00CC96")

    _fig_link = go.Figure()
    _fig_link.add_trace(go.Bar(
        name="实际支出",
        x=_bar_cats, y=_bar_actual,
        marker_color=_bar_colors,
        text=[fmt(v, decimals=0) for v in _bar_actual],
        textposition="outside",
        hovertemplate="%{x}<br>实际: " + sym + "%{y:,.0f}<extra></extra>",
    ))
    _fig_link.add_trace(go.Bar(
        name="参考预算",
        x=_bar_cats, y=_bar_budget,
        marker_color="rgba(100,100,200,0.3)",
        hovertemplate="%{x}<br>参考: " + sym + "%{y:,.0f}<extra></extra>",
    ))
    _fig_link.update_layout(
        barmode="overlay",
        height=320,
        margin=dict(t=30, b=20, l=20, r=20),
        showlegend=True,
        xaxis_title="类别",
        yaxis_title=f"金额（{sym}）",
        yaxis_tickformat=",",
    )
    st.plotly_chart(_fig_link, use_container_width=True)
    st.caption("参考预算以必需/想要总预算平均分配到对应类别；如需精细化设置，请在记账本页面使用月度预算功能。")
else:
    st.info("本月暂无支出记录。请在「收支记账本」页面录入本月支出后，这里将自动显示实际 vs 预算对比。")

# ── 导出报告 ──────────────────────────────────────────────
st.subheader("📤 导出报告")
def _build_bud_report() -> str:
    from core.currency import get_symbol; s = get_symbol()
    th = "".join(f"<li>{t}</li>" for t in tips)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#222}}h1{{color:#333}}ul{{line-height:2}}</style></head><body><h1>💡 预算分配报告</h1><p>月收入：{s}{income:,.0f} | 比例：{pct_needs}%/{pct_wants}%/{pct_save}%</p><p>必需：{s}{amt_needs:,.0f} | 想要：{s}{amt_wants:,.0f} | {save_label}：{s}{amt_save:,.0f}</p><h2>建议</h2><ul>{th}</ul></body></html>"""
st.download_button("📥 下载报告 (HTML)", data=_build_bud_report(), file_name="预算分配报告.html", mime="text/html")
st.caption(MSG.print_hint)

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption(MSG.budget_footer)
