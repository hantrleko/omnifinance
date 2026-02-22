"""50/30/20 预算分配建议器

根据税后月收入，按经典 50/30/20 法则给出分配建议。
支持手动调比例、固定支出超标警示、高利债务优先还债。
"""

import plotly.graph_objects as go
import streamlit as st

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="预算分配建议器", page_icon="💡", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  .stMetric { background-color: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 8px; padding: 14px; }
</style>
""", unsafe_allow_html=True)

st.title("💡 50/30/20 预算分配建议器")

# ── 侧边栏参数 ────────────────────────────────────────────
st.sidebar.header("📋 收入与支出")

income = st.sidebar.number_input(
    "月收入（税后，元）", min_value=10_000.0, max_value=1_000_000.0,
    value=60_000.0, step=5_000.0, format="%.0f",
)
fixed_expense = st.sidebar.number_input(
    "已知固定必需支出（元）", min_value=0.0, max_value=income,
    value=0.0, step=1_000.0, format="%.0f",
    help="如房租、房贷、保险等已确定的必需支出",
)
has_debt = st.sidebar.checkbox("有高利债务（信用卡/消费贷等）", value=False)

st.sidebar.divider()
st.sidebar.subheader("⚙️ 自定义比例")
st.sidebar.caption("拖动滑杆调整分配比例（三项合计须为 100%）")

pct_needs = st.sidebar.slider("必需支出占比（%）", 0, 100, 50, key="needs")
pct_wants = st.sidebar.slider("想要支出占比（%）", 0, 100, 30, key="wants")
pct_save = 100 - pct_needs - pct_wants

if pct_save < 0:
    st.sidebar.error(f"⚠️ 必需 + 想要 = {pct_needs + pct_wants}%，超过 100%！请调低。")
    pct_save = 0

st.sidebar.metric("储蓄/还债占比", f"{pct_save}%",
                   delta=f"{'✅ 合计 100%' if pct_needs + pct_wants + pct_save == 100 else '❌ 不足 100%'}",
                   delta_color="off")

# ── 计算 ──────────────────────────────────────────────────
amt_needs = income * pct_needs / 100
amt_wants = income * pct_wants / 100
amt_save = income * pct_save / 100

remaining_needs = max(0, amt_needs - fixed_expense)
fixed_pct = (fixed_expense / income * 100) if income > 0 else 0

save_label = "储蓄 / 还债" if has_debt else "储蓄 / 投资"

# ── 核心指标 ──────────────────────────────────────────────
st.markdown("---")

c1, c2, c3 = st.columns(3)
c1.metric("🏠 必需支出", f"¥{amt_needs:,.0f}", delta=f"{pct_needs}%", delta_color="off")
c2.metric("🎉 想要支出", f"¥{amt_wants:,.0f}", delta=f"{pct_wants}%", delta_color="off")
c3.metric(f"💰 {save_label}", f"¥{amt_save:,.0f}", delta=f"{pct_save}%", delta_color="off")

# ── 固定支出超标警示 ──────────────────────────────────────
if fixed_expense > 0:
    st.markdown("---")
    if fixed_expense > amt_needs:
        over = fixed_expense - amt_needs
        st.error(
            f"🚨 **固定必需支出（¥{fixed_expense:,.0f}）已超过必需预算（¥{amt_needs:,.0f}）** "
            f"— 超支 ¥{over:,.0f}（占收入 {fixed_pct:.1f}% > {pct_needs}%）。\n\n"
            f"建议：降低固定支出、增加收入，或将必需占比上调至 {int(fixed_pct) + 5}% 以上。"
        )
    elif fixed_expense > amt_needs * 0.8:
        st.warning(
            f"⚠️ 固定支出 ¥{fixed_expense:,.0f} 已占必需预算的 {fixed_expense / amt_needs * 100:.0f}%，"
            f"仅剩 ¥{remaining_needs:,.0f} 用于其他必需开销（餐饮/交通等）。"
        )
    else:
        st.success(
            f"✅ 固定支出 ¥{fixed_expense:,.0f} 占必需预算的 {fixed_expense / amt_needs * 100:.0f}%，"
            f"剩余 ¥{remaining_needs:,.0f} 可用于其他必需开销。"
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
    hovertemplate="%{label}<br>¥%{value:,.0f}<br>%{percent}<extra></extra>",
)])

fig.update_layout(
    showlegend=False,
    margin=dict(t=20, b=20, l=20, r=20),
    height=400,
    annotations=[dict(
        text=f"¥{income:,.0f}<br><span style='font-size:13px;color:#888'>月收入</span>",
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
    st.markdown(f"- **预算总额：** ¥{amt_needs:,.0f}")
    if fixed_expense > 0:
        st.markdown(f"- 固定支出：¥{fixed_expense:,.0f}")
        st.markdown(f"- 弹性必需：¥{remaining_needs:,.0f}")
    st.caption("含：房租/房贷、水电煤、保险、交通、基本餐饮")

with col_b:
    st.markdown("#### 🎉 想要支出")
    st.markdown(f"- **预算总额：** ¥{amt_wants:,.0f}")
    st.caption("含：外出餐饮、娱乐、购物、订阅、旅行")

with col_c:
    st.markdown(f"#### 💰 {save_label}")
    st.markdown(f"- **预算总额：** ¥{amt_save:,.0f}")
    if has_debt:
        st.markdown(f"- 🔴 优先还债：¥{amt_save * 0.7:,.0f}（建议 70%）")
        st.markdown(f"- 应急储蓄：¥{amt_save * 0.3:,.0f}（建议 30%）")
        st.caption("有高利债务时，建议将大部分储蓄用于还债")
    else:
        st.markdown(f"- 应急基金：¥{amt_save * 0.5:,.0f}（建议 50%）")
        st.markdown(f"- 长期投资：¥{amt_save * 0.5:,.0f}（建议 50%）")
        st.caption("建议先存满 3–6 个月应急金，再配置投资")

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

# ── 页脚 ──────────────────────────────────────────────────
st.divider()
st.caption("💡 50/30/20 预算分配建议器 | 运行命令：`streamlit run app.py`")
