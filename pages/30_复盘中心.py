"""复盘中心 — 健康分趋势、行动看板与月度复盘报告。

将"计算"变成"决策"的复盘闭环：
  - 健康分快照趋势：追踪财务健康评分的历史变化，对比上次诊断。
  - 行动看板：跟踪 90 天行动计划的执行状态（已计划/进行中/已完成/已跳过）。
  - 月度复盘：一键生成本月分数变化与行动完成情况的 Markdown 复盘报告。

逻辑全部下沉至 core/review.py，本文件仅负责 UI。
"""
from __future__ import annotations

from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from core.page_setup import init_page

init_page("复盘中心", "🔁", "review")

from core.chart_config import apply_chart_config, build_layout, render_empty_state
from core.review import (
    ACTION_STATUSES,
    STATUS_LABELS,
    action_stats,
    build_monthly_review,
    compute_snapshot_delta,
    delete_action,
    load_actions,
    load_health_history,
    monthly_review_markdown,
    recent_period_options,
    upsert_action,
)

st.title("🔁 复盘中心")
st.caption("追踪健康分变化、管理行动执行状态，并生成月度复盘报告 — 让每次计算都推动一个决策。")

tab_trend, tab_actions, tab_review = st.tabs(["📈 健康分趋势", "🗂️ 行动看板", "📆 月度复盘"])

# ══════════════════════════════════════════════════════════
# 健康分趋势
# ══════════════════════════════════════════════════════════
with tab_trend:
    history = load_health_history()
    if not history:
        render_empty_state(
            title="暂无健康分快照",
            message="访问 🏠 仪表盘首页 生成财务健康诊断后，系统会自动记录快照。",
            icon="🩺",
        )
    else:
        delta = compute_snapshot_delta(history)
        c1, c2, c3 = st.columns(3)
        c1.metric("当前健康分", delta.current if delta.current is not None else "—")
        if delta.previous is not None:
            c2.metric("上次诊断", delta.previous, delta=f"{delta.delta:+d} 分", delta_color="normal")
            c3.metric("间隔天数", f"{delta.days_between} 天" if delta.days_between is not None else "—")
        else:
            c2.metric("上次诊断", "—")
            c3.metric("间隔天数", "—")

        if delta.trend == "up":
            st.success(f"📈 相比上次诊断提升了 {delta.delta} 分，继续保持！")
        elif delta.trend == "down":
            st.warning(f"📉 相比上次诊断下降了 {abs(delta.delta or 0)} 分，建议查看是哪个维度变弱了。")

        # 趋势折线
        ts = [s["timestamp"] for s in history]
        scores = [s["overall_score"] for s in history]
        fig = go.Figure(go.Scatter(
            x=ts, y=scores, mode="lines+markers", name="健康分",
            hovertemplate="%{x}<br>健康分: %{y}<extra></extra>",
        ))
        fig.add_hline(y=80, line_dash="dot", annotation_text="优秀线 (80)")
        fig.add_hline(y=60, line_dash="dot", annotation_text="良好线 (60)")
        fig.update_layout(**build_layout(
            title="财务健康分历史趋势", height=380, yaxis_range=[0, 105],
        ))
        apply_chart_config(fig, key="health_trend")

        # 最近一次的维度明细
        latest_dims = history[-1].get("dimensions") or {}
        if latest_dims:
            st.subheader("最近一次诊断的维度得分")
            fig2 = go.Figure(go.Bar(
                x=list(latest_dims.keys()), y=list(latest_dims.values()),
                hovertemplate="%{x}: %{y} 分<extra></extra>",
            ))
            fig2.update_layout(**build_layout(height=300, yaxis_range=[0, 105]))
            apply_chart_config(fig2, key="dim_bar")

# ══════════════════════════════════════════════════════════
# 行动看板
# ══════════════════════════════════════════════════════════
with tab_actions:
    actions = load_actions()
    stats = action_stats(actions)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("行动总数", stats["total"])
    c2.metric("进行中", stats["counts"]["in_progress"])
    c3.metric("已完成", stats["counts"]["completed"])
    c4.metric("完成率", f"{stats['completion_rate_pct']:.0f}%")

    # 新增行动
    with st.expander("➕ 添加新行动", expanded=not actions), st.form("add_action_form", clear_on_submit=True):
        new_title = st.text_input("行动内容", placeholder="例如：把应急基金补足到 6 个月支出")
        fc1, fc2 = st.columns(2)
        with fc1:
            new_status = st.selectbox(
                "初始状态", ACTION_STATUSES, index=0,
                format_func=lambda s: STATUS_LABELS.get(s, s),
            )
        with fc2:
            new_note = st.text_input("备注（可选）")
        if st.form_submit_button("添加", type="primary") and new_title.strip():
            try:
                upsert_action(new_title, status=new_status, note=new_note, source="manual")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    if not actions:
        st.info("💡 还没有跟踪中的行动。可以手动添加，或在 🏠 仪表盘首页把 90 天行动计划中的建议加入看板。")
    else:
        st.markdown("---")
        for record in actions:
            title = str(record.get("title", ""))
            status = str(record.get("status", "planned"))
            with st.container(border=True):
                col_main, col_status, col_del = st.columns([3, 1.6, 0.6])
                with col_main:
                    st.markdown(f"**{title}**")
                    meta_bits = []
                    if record.get("note"):
                        meta_bits.append(f"📝 {record['note']}")
                    if record.get("completed_at"):
                        meta_bits.append(f"✅ 完成于 {str(record['completed_at'])[:10]}")
                    elif record.get("updated_at"):
                        meta_bits.append(f"🕐 更新于 {str(record['updated_at'])[:10]}")
                    if meta_bits:
                        st.caption(" · ".join(meta_bits))
                with col_status:
                    new_status = st.selectbox(
                        "状态", ACTION_STATUSES,
                        index=ACTION_STATUSES.index(status) if status in ACTION_STATUSES else 0,
                        format_func=lambda s: STATUS_LABELS.get(s, s),
                        key=f"status_{title}",
                        label_visibility="collapsed",
                    )
                    if new_status != status:
                        upsert_action(title, status=new_status, note=str(record.get("note", "")))
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{title}", help="删除此行动"):
                        delete_action(title)
                        st.rerun()

# ══════════════════════════════════════════════════════════
# 月度复盘
# ══════════════════════════════════════════════════════════
with tab_review:
    options = recent_period_options(12)
    labels = [f"{y} 年 {m} 月" for y, m in options]
    selected = st.selectbox("选择复盘月份", range(len(options)), format_func=lambda i: labels[i])
    year, month = options[selected]

    review = build_monthly_review(year, month)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "健康分变化",
        f"{review['score_change']:+d}" if review["score_change"] is not None else "—",
    )
    c2.metric("完成行动", review["actions_completed"])
    c3.metric("跳过行动", review["actions_skipped"])
    c4.metric("待办行动", review["actions_open"])

    st.subheader("本月要点")
    for highlight in review["highlights"]:
        st.markdown(f"- {highlight}")

    md = monthly_review_markdown(review)
    with st.expander("📄 预览 Markdown 报告"):
        st.code(md, language="markdown")
    st.download_button(
        "⬇️ 下载月度复盘报告 (Markdown)",
        data=md,
        file_name=f"omnifinance_review_{year}-{month:02d}.md",
        mime="text/markdown",
        type="primary",
    )

st.caption(f"🕐 当前时间：{datetime.now():%Y-%m-%d %H:%M} · 复盘数据保存在本地 ~/.omnifinance/ 目录，不会上传。")
