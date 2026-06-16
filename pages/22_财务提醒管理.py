"""财务提醒管理器 — 设置、查看、完成财务提醒事项。"""

from datetime import date, timedelta

import streamlit as st
from core.navigation import track_recent_page
track_recent_page(st.session_state, 'reminders')

from core.theme import inject_theme

inject_theme()

from core.currency import fmt
from core.reminders import (
    add_reminder,
    complete_reminder,
    delete_reminder,
    export_reminders,
    clear_completed_reminders,
    import_reminders,
    get_due_reminders,
    get_reminders,
)

st.set_page_config(page_title="财务提醒管理", page_icon="🔔", layout="wide")
st.title("🔔 财务提醒管理器")
st.caption("集中管理所有财务提醒事项，再也不错过缴款、定投或复盘日期。")

CATEGORY_ICONS = {
    "debt": "💳 债务还款",
    "savings": "🎯 储蓄定投",
    "insurance": "🛡️ 保险缴费",
    "education": "🏫 教育基金",
    "retirement": "🏖️ 退休规划",
    "tax": "🧾 税务申报",
    "investment": "📈 投资操作",
    "portfolio": "📈 投资操作",
    "general": "📌 其他事项",
    "还贷": "💳 还贷",
    "储蓄": "🎯 储蓄",
    "保费": "🛡️ 保费",
    "税务": "🧾 税务申报",
    "投资": "📈 投资操作",
}

CATEGORY_COLORS = {
    "debt": "#EF553B",
    "savings": "#00CC96",
    "insurance": "#636EFA",
    "education": "#AB63FA",
    "retirement": "#FFA15A",
    "tax": "#19D3F3",
    "investment": "#FF6692",
    "general": "#B6E880",
    "还贷": "#EF553B",
    "储蓄": "#00CC96",
    "保费": "#636EFA",
    "税务": "#19D3F3",
    "投资": "#FF6692",
}

# ── Due alerts at top ─────────────────────────────────────
due_now = get_due_reminders()
if due_now:
    st.error(f"⚠️ 你有 **{len(due_now)}** 条提醒已到期或即将到期！")
    for r in due_now[:3]:
        icon_label = CATEGORY_ICONS.get(r.get("category", "general"), "📌 其他事项")
        amt_text = f" — {fmt(r['amount'], decimals=0)}" if r.get("amount", 0) > 0 else ""
        st.warning(f"{icon_label} **{r['title']}** 截止 `{r['due_date']}`{amt_text}")
    if len(due_now) > 3:
        st.caption(f"... 以及另外 {len(due_now) - 3} 条，请在下方查看全部。")

st.markdown("---")

# ── Reminder data management ──────────────────────────────
export_scope_cols = st.columns([1, 1, 1, 1])
export_payload_active = export_reminders(scope="active")
export_payload_completed = export_reminders(scope="completed")
export_payload_all = export_reminders(scope="all")
with export_scope_cols[0]:
    st.download_button(
        "📤 导出待处理",
        data=export_payload_active,
        file_name=f"OmniFinance_Reminders_Active_{date.today()}.json",
        mime="application/json",
        use_container_width=True,
    )
with export_scope_cols[1]:
    st.download_button(
        "📤 导出已完成",
        data=export_payload_completed,
        file_name=f"OmniFinance_Reminders_Completed_{date.today()}.json",
        key="export_completed",
        mime="application/json",
        use_container_width=True,
    )
with export_scope_cols[2]:
    st.download_button(
        "📤 导出全部",
        data=export_payload_all,
        file_name=f"OmniFinance_Reminders_All_{date.today()}.json",
        key="export_all",
        mime="application/json",
        use_container_width=True,
    )
with export_scope_cols[3]:
    if st.button("🗄️ 清理已完成提醒", use_container_width=True, type="secondary"):
        removed_count = clear_completed_reminders()
        if removed_count:
            st.success(f"已清理 {removed_count} 条已完成提醒")
        else:
            st.info("当前没有可清理的已完成提醒")
        st.rerun()

# ── Import reminders ──────────────────────────────────────
with st.expander("📥 导入提醒备份", expanded=False):
    st.caption("支持导入 JSON 备份文件，默认与现有提醒合并并按标题+日期+分类+备注去重。")
    uploaded = st.file_uploader("选择备份文件", type=["json"], key="reminder_import")
    if uploaded is not None:
        mode = st.selectbox(
            "导入策略",
            ["append", "replace"],
            format_func=lambda v: "叠加到现有" if v == "append" else "替换全部",
            key="reminder_import_mode",
        )
        import_dedupe = st.checkbox("导入时去重", value=True, key="reminder_import_dedupe")
        if st.button("开始导入", key="reminder_import_run"):
            imported = import_reminders(
                uploaded.read().decode("utf-8"),
                dedupe=import_dedupe,
                mode=mode,
            )
            if imported > 0:
                st.success(f"✅ 已导入 {imported} 条提醒")
            else:
                st.info("未导入任何提醒（文件为空或全部重复/无效）")
            st.rerun()

st.markdown("---")

# ── Add new reminder ──────────────────────────────────────
with st.expander("➕ 添加新提醒", expanded=len(get_reminders()) == 0):
    col1, col2 = st.columns(2)
    with col1:
        new_title = st.text_input("提醒标题 *", placeholder="如：房贷月供到期、基金定投日", key="rm_title")
        new_category = st.selectbox(
            "类别",
            list(CATEGORY_ICONS.keys()),
            format_func=lambda k: CATEGORY_ICONS[k],
            key="rm_cat",
        )
        new_amount = st.number_input("关联金额（元，可选）", min_value=0.0, value=0.0, step=100.0, format="%.0f", key="rm_amt")
    with col2:
        new_desc = st.text_area("备注说明", placeholder="可留空", height=100, key="rm_desc")
        new_due = st.date_input("截止日期", value=date.today() + timedelta(days=30), key="rm_due")
        new_recur = st.selectbox("周期重复（仅记录用）", ["不重复", "每月", "每季度", "每年"], key="rm_recur")

    if st.button("✅ 添加提醒", type="primary", disabled=not new_title.strip(), key="rm_add"):
        desc_full = new_desc.strip()
        if new_recur != "不重复":
            desc_full = f"[{new_recur}] " + desc_full
        added = add_reminder(
            title=new_title.strip(),
            description=desc_full,
            due_date=str(new_due),
            category=new_category,
            amount=new_amount,
            dedupe=True,
        )
        if added:
            st.success(f"已添加提醒：{new_title.strip()}")
            st.rerun()
        else:
            st.info("相同提醒已存在，未重复添加。")

st.markdown("---")

# ── Active reminders ──────────────────────────────────────
tab_active, tab_done = st.tabs(["📋 待处理提醒", "✅ 已完成提醒"])

with tab_active:
    active = get_reminders(include_completed=False)
    if not active:
        st.info("暂无待处理提醒，点击上方「添加新提醒」创建第一条。")
    else:
        today_str = str(date.today())
        filter_cat = st.selectbox(
            "按类别筛选",
            ["全部"] + list(CATEGORY_ICONS.keys()),
            format_func=lambda k: "全部" if k == "全部" else CATEGORY_ICONS[k],
            key="rm_filter",
        )
        if filter_cat != "全部":
            active = [r for r in active if r.get("category") == filter_cat]

        for r in active:
            due = r.get("due_date", "")
            is_overdue = due < today_str
            is_soon = today_str <= due <= str(date.today() + timedelta(days=7))
            icon_label = CATEGORY_ICONS.get(r.get("category", "general"), "📌 其他事项")
            amt_text = f" | {fmt(r['amount'], decimals=0)}" if r.get("amount", 0) > 0 else ""
            status_badge = " 🔴 已逾期" if is_overdue else (" 🟡 即将到期" if is_soon else "")

            with st.container(border=True):
                cols = st.columns([5, 1, 1])
                with cols[0]:
                    st.markdown(f"**{icon_label}** — {r['title']}{status_badge}")
                    st.caption(f"截止：`{due}`{amt_text}")
                    if r.get("description"):
                        st.caption(r["description"])
                with cols[1]:
                    if st.button("✅ 完成", key=f"rm_done_{r['id']}", use_container_width=True):
                        complete_reminder(r["id"])
                        st.rerun()
                with cols[2]:
                    if st.button("🗑️ 删除", key=f"rm_del_{r['id']}", use_container_width=True):
                        delete_reminder(r["id"])
                        st.rerun()

        # Stats
        st.markdown("---")
        overdue_count = sum(1 for r in active if r.get("due_date", "") < today_str)
        c1, c2, c3 = st.columns(3)
        c1.metric("待处理总计", f"{len(active)} 条")
        c2.metric("已逾期", f"{overdue_count} 条", delta=f"-{overdue_count}" if overdue_count else "全部正常", delta_color="inverse" if overdue_count else "off")
        c3.metric("7天内到期", f"{sum(1 for r in active if today_str <= r.get('due_date','') <= str(date.today() + timedelta(days=7)))} 条")

with tab_done:
    done = [r for r in get_reminders(include_completed=True) if r.get("completed")]
    if not done:
        st.info("暂无已完成提醒。")
    else:
        filter_done = st.selectbox(
            "按类别筛选",
            ["全部"] + list(CATEGORY_ICONS.keys()),
            format_func=lambda k: "全部" if k == "全部" else CATEGORY_ICONS[k],
            key="rm_filter_done",
        )
        if filter_done != "全部":
            done = [r for r in done if r.get("category") == filter_done]

        for r in reversed(done[-20:]):
            icon_label = CATEGORY_ICONS.get(r.get("category", "general"), "📌 其他事项")
            st.markdown(f"~~{icon_label} {r['title']}~~ `{r.get('due_date', '')}`")

        if st.button("🗑️ 清除全部已完成提醒", key="rm_clear_done"):
            removed = clear_completed_reminders()
            st.success(f"已清除 {removed} 条已完成提醒")
            st.rerun()

# ── Quick add templates ───────────────────────────────────
st.markdown("---")
st.subheader("⚡ 快速添加常用提醒")
st.caption("一键添加高频财务事项提醒。")

templates = [
    ("房贷月供", "debt", "每月按时还款", 5000.0),
    ("基金定投日", "savings", "每月定期定额投入", 2000.0),
    ("保险年缴日", "insurance", "年度保险费到期缴纳", 8000.0),
    ("季度税款申报", "tax", "个税或营业税季度申报", 0.0),
    ("年度财务复盘", "general", "回顾年度财务目标完成情况", 0.0),
    ("债务还清里程碑", "debt", "某笔债务预计还清", 0.0),
]

tpl_cols = st.columns(3)
for idx, (title, cat, desc, amt) in enumerate(templates):
    with tpl_cols[idx % 3]:
        if st.button(f"{CATEGORY_ICONS[cat].split()[0]} {title}", key=f"tpl_{idx}", use_container_width=True):
            added = add_reminder(
                title=title,
                description=desc,
                due_date=str(date.today() + timedelta(days=30)),
                category=cat,
                amount=amt,
                dedupe=True,
            )
            if added:
                st.success(f"已添加「{title}」提醒（截止日期：30天后），请在上方调整。")
                st.rerun()
            else:
                st.info("相同提醒已存在，未重复添加。")

