import streamlit as st
from core.currency import get_symbol, fmt

VERSION = "v1.9.9"

st.title(f"🌟 全能理财家 (OmniFinance) `{VERSION}`")
st.caption("✨ **Empower Your Knowledge, Enrich Your Life** | Eugene Finance 荣誉出品")
st.markdown("---")

st.markdown("""
### 欢迎使用全能理财家！

这是一个集成了多项实用金融工具的统一平台。我们已经将所有子功能**按类别进行了清晰的划分**，您可以从左侧边栏的专属分类中快速找到需要的工具。

**核心功能模块导览：**
- 💰 **基础理财管理**：计算投资复利收益、规划储蓄路径、50/30/20 预算分配建议、教育基金规划。
- ⚖️ **资产与债务管理**：全局跟踪资产负债净值、计算贷款本息明细、评估储蓄型保单回报率、债务还清策略。
- 📈 **投资分析引擎**：查看全球实时行情（含 A 股）、自动化策略回测对比、马科维茨投资组合优化、资产再平衡模拟、外汇对冲分析。
- 🏖️ **高级人生规划**：精准估算退休缺口、蒙特卡洛概率模拟、税务优化提款、历史回测储蓄模拟。
- 🔬 **分析与工具**：场景对比分析、财务日历时间线、跨工具数据导入导出。
""")

with st.expander("🚀 重大版本升级（v1.9.9）", expanded=True):
    st.markdown("""
**v1.9.9-UI 全局 UI/UX 系统性升级（当前版本）**

🎨 **主题系统重构**
- `core/theme.py` 新增 `inject_page_css()` 全局统一注入：所有 25 个页面的 `.block-container` 顶部间距与 `.stMetric` 卡片样式现已一键全局管理，彻底消除各页面重复 CSS 代码。
- 指标卡片新增 hover 微动效：悬停时轻微上浮 + 蓝色阴影，提升交互质感。
- 下载按钮统一加入圆角 + 过渡动效，与普通按钮视觉语言保持一致。
- 侧边栏输入标签字号收窄至 0.85rem，减少视觉拥挤感。

🧮 **科学计算器按钮视觉分层**
- 运算符（÷ × - +）：蓝色调背景，一眼识别数学运算区。
- 数学函数（sin cos tan sqrt log exp）：绿色调背景 + 较小字号，区分高级运算区。
- 清除/退格（AC ⌫）：红色调背景，危险操作区域高亮警示。
- 等号（=）：强蓝色高亮，主操作按钮优先级最高。

📌 **侧边栏版本标识**
- 所有页面侧边栏底部新增 `OmniFinance v1.9.9` 版本标注，方便用户快速识别当前版本。

🧹 **页面 CSS 标准化**
- 删除分散在 23 个页面中的重复内联 CSS 代码块，统一由 `inject_theme()` 管理，代码可维护性大幅提升。
- 实时报价面板保留 `.time-badge` 专属样式，其余冗余 CSS 全部清理。

---

**v1.9.9 实时汇率引擎 + 三大新工具 + 全面功能深化**

💱 **实时汇率引擎（core/exchange_rates.py）**
- 全新 yfinance 汇率引擎：USD / EUR / GBP / JPY / HKD 对 CNY 的实时汇率，15 分钟缓存。
- 网络断线自动回退至离线参考汇率，侧边栏「刷新汇率」按钮一键强制刷新。
- 货币选择器下方新增「汇率：实时/离线，更新于 xx:xx」提示。

💱 **新页面：货币转换器（分析与工具）**
- 实时双向换算、6×6 全量交叉汇率矩阵、近 30 天历史走势图。
- 海外购物 / 留学学费 / 工资对比三大快捷场景 + 批量换算区。

🧮 **新页面：科学金融计算器（分析与工具）**
- 科学计算区：网格按键 + 表达式输入，支持三角函数、对数、阶乘、π、e，10 条历史记录。
- 金融计算 4 Tab：复利 FV/PV 互求、年金/IRR、债券价格/久期/凸性、百分比工具（CAGR、通胀调整、折扣）。

📔 **新页面：财务日记（高级人生规划）**
- 每月记录净资产快照 + 心情标注 + 备注，JSON 本地持久化。
- 年度时间轴净资产走势图，悬停显示心情与备注。
- 「生成年度财务回顾」按钮：一键导出 HTML 年度财务年报。

💳 **债务还清规划器深化**
- 新增还清里程碑 Gantt 图：各债务还清时间段一目了然。
- 最优策略节省金额展示升级为高对比度绿色横幅，核心结论第一眼可见。
- 新增「心理动力提示」：根据雪球法最快还清的第一笔债务月数显示激励文案。

📄 **综合报告升级**
- HTML 财务诊断报告新增「汇率快照」卡片，展示生成报告时的主流货币实时汇率。

💱 **外汇对冲计算器升级**
- 侧边栏新增「获取实时 USD/CNY」按钮，一键填入最新即期汇率并显示数据时间。
""")

with st.expander("🚀 重大版本升级（v1.9.8）", expanded=False):
    st.markdown("""
**v1.9.8 探索式深度改进 — 6大方向全面升级**

👤 **个人财务档案系统**
- 全新 core/profile.py 模块：一次性填写姓名/年龄/城市/月收入/月支出/风险偏好/家庭状况，全局侧边栏持久化保存，后续所有工具均可引用。

🔔 **财务提醒管理器（全新页面）**
- 完整提醒 CRUD 系统上线：新增债务还款、储蓄定投、保险缴费、税务申报等 8 类提醒，支持周期标注、金额关联、逾期高亮警告。
- 6个常用场景模板一键添加，已完成提醒归档管理。

📊 **全国均值基准对比内联展示**
- 预算建议器、退休估算器、税务计算器新增全国均值对比条，实时显示月收入/储蓄率/退休储备与全国平均的差距，绿色/黄色/红色直观反映优劣。

🐛 **税务计算器 Bug 修复**
- 修复「住房贷款利息」与「住房租金」可同时勾选的逻辑漏洞（二者在现行税法下互斥），现在会即时弹出错误提示并阻止错误计算。
- 新增税后月收入与全国均值对比条，提供即时收入定位参考。

🔬 **场景对比分析器大幅扩展**
- 从 2 个维度扩展至 4 个维度：
  - 新增「贷款利率敏感度」— 分析不同利率对月还款/总利息/利息本金比的影响
  - 新增「退休年龄敏感度」— 找出最早可无缺口退休的年龄节点

🔧 **app.py 路由更新**
- 新增财务提醒管理页面（pages/22_财务提醒管理.py）到导航菜单，模块版本注释更新至 v1.9.8。
""")

with st.expander("🚀 功能精进（v1.9.7）"):
    st.markdown("""
**v1.9.7 功能精进全面升级 — 8大核心增强**

📊 **仪表盘深度升级**
- 🏥 **财务健康多维评分系统**：新增6大维度独立评分（储蓄率、退休准备度、负债水平、净资产、税务、保险），每维度单独展示评分与改善建议，汇总综合评分更精准、更具指导意义。
- 🌊 **现金流时间轴规划器**：统一时间轴叠加所有工具收支流，直观呈现每年现金流峰值/谷值，识别哪年压力最大，辅助跨工具协同决策。
- 📅 **年度财务回顾生成器**：整合所有工具数据，一键生成结构化年度财务总结报告，包含净资产变化、储蓄进度、债务减少、保险覆盖度等全维度回顾。

🛠️ **工具功能精进**
- 📈 **净资产追踪器**：新增「计划线 vs 实际线」对比图表，直观显示净资产增长是否按原计划执行，偏差一目了然。
- 🎯 **储蓄/退休敏感度双向滑杆**：新增实时交互滑杆，拖动目标额即时更新所需时间，或拖动时限即时更新所需月投入，比静态表格更直观。
- 📋 **参数预设模板**：新增「刚毕业族」「双薪家庭」「临近退休」三大场景预设，一键填入推荐参数，大幅降低新用户上手门槛。

⚙️ **基础体验优化**
- 💱 **货币切换全局记忆**：货币偏好现已持久化写入磁盘，刷新页面或重启后自动恢复上次选择，不再重置为默认货币。
""")

with st.expander("🚀 功能优化（v1.9.6.x）"):
    st.markdown("""
**v1.9.6.x 全面功能优化与工程加固**

- 🐛 **Bug 修复**：储蓄目标计算器修复"年通谀率"错别字；贷款计算器 & 预算建议器图表硬编码 ¥ 改为动态货币符号。
- 📊 **复利计算器**：月/日利息明细改用与核心引擎一致的复利频率精确计算，不再使用简化 r/12、r/365。
- 🏠 **仪表盘**：跨工具分析新增复利年化收益率 vs 保险 IRR 对比，修复 compound_rate 未使用的死代码。
- 🏖️ **退休金估算器**：4% 法则提款策略改为标准实现（首年 4% × 初始资产，后续按通胀调整），而非每年重新计算资产的 4%。
- 🎲 **蒙特卡洛模拟**：Student-t 分布改用 np.random.default_rng 统一随机数生成，告别已弃用的 scipy RandomState。
- 📐 **投资组合优化器**：修复权重约束校验逻辑（原先 raw_tickers 未定义导致约束失效），现在解析完标的后才验证。
- 🧾 **税务计算器**：全面集成到平台（仪表盘联动、方案管理、HTML 报告导出），新增独立导航分类。
- 📈 **策略回测器**：移除无用 _cached_comparison 占位函数；参数网格搜索改用 joblib 并行加速。
- 📊 **实时报价面板**：A 股代码检测升级，支持沪深交易所前缀校验（科创板 688、创业板 300 等）。
- 🎨 **图表主题**：chart_config 新增暗色/亮色模式自动适配，所有 Plotly 图表背景、字体、网格线随主题切换。
- 💾 **储蓄多目标**：多目标规划列表改用 core/storage.py 持久化存储，页面刷新不再丢失。
- 🛡️ **保险测算器**：退保场景新增"指数增长"模式，更贴近真实保单前慢后快的现金价值增长曲线。
- ⚙️ **IRR 求解器**：新增收敛检测与 scipy.optimize.brentq 回退机制，防止 Newton-Raphson 发散。
- 🔧 **报告生成器**：新增通用 build_single_report 模板函数，统一暗色适配 + 打印友好样式。
""")

with st.expander("🚀 功能更新（v1.9.6）"):
    st.markdown("""
**v1.9.6 实时报价面板新增 A 股支持**

- 📊 **实时报价面板**：接入 AKShare 数据源，新增沪深两市 A 股实时行情支持。
  - 侧边栏快捷选择新增「A股」分组，预置贵州茅台、五粮液、中国平安、美的集团、宁德时代。
  - A 股实时报价（当前价格、涨跌幅、今日最高/最低、成交量）由 AKShare 提供。
  - K 线图同步支持 A 股历史数据（前复权），与美股/港股保持一致的图表体验。
  - 自定义代码输入支持直接填入 6 位 A 股代码（如 601988）。
  - 美股、港股、加密货币继续走 Yahoo Finance 通道，双数据源并行互不影响。
""")

with st.expander("🚀 功能全面升级（v1.9.5）"):
    st.markdown("""
**v1.9.5 十二项功能优化全面上线**

本次升级对全部 11 个现有工具进行了功能深化，并新增第 12 个独立工具：

- 💰 **复利计算器**：新增年通胀率输入，同步展示"实际购买力"曲线，直观对比名义收益与真实增值。
- 🎯 **储蓄目标计算器**：新增多目标管理器，可同时规划多个目标（如买房、旅行、教育），并按高/中/低优先级排序，统一展示进度。
- 🏖️ **退休金估算器**：新增三种退休提款策略对比（固定金额、4%法则、动态弹性），可视化资产耗尽风险差异。
- 🏦 **贷款计算器**：新增转贷模拟器，输入新利率/年限/手续费，自动计算净节省利息与手续费回本期数。
- 📐 **投资组合优化器**：新增权重约束（单资产最大/最小持仓比例），防止优化结果过度集中。
- 📈 **策略回测器**：新增指数基准对比（标普500、纳斯达克、沪深300等），显示策略超额收益（Alpha）。
- 🎲 **蒙特卡洛模拟**：新增学生 t 分布（厚尾）选项，更真实地反映市场极端事件发生频率。
- 🏠 **资产净值追踪器**：新增净资产未来预测模块，支持最长 20 年的增长路径可视化。
- 📊 **实时报价面板**：新增价格预警功能，可为每个标的设置涨跌触发阈值，实时提示。
- 🛡️ **保险产品测算器**：新增退保场景分析，模拟不同年份退保的现金价值、损失率和 IRR 走势。
- 🔗 **主页仪表盘**：新增跨工具综合分析，自动生成退休、债务、储蓄、净资产之间的联动洞察。
- 🧾 **新增税务计算器**（第12个工具）：支持工资薪金个税、劳务报酬预扣税、投资收益税后分析三大模块。
""")

with st.expander("📋 v1.9.0 及更早版本说明"):
    st.markdown("""
- **v1.9.0**: 一键财务诊断报告，打通所有 11 个工具状态，生成企业级 HTML 报告。
- **v1.8 ~ v1.8.5**: 模块化侧边栏导航重构、Glassmorphism 视觉升级、深色模式修复。
- **v1.7**: 新增蒙特卡洛模拟与马科维茨投资组合优化器模块，增强错误捕捉，支持 Excel 全面导出。
- **v1.6**: 并发与架构优化（涵盖 API 异步请求与多进程回测机制）。
- **v1.5**: 新增资产净值追踪，全局支持方案保存与状态联动。
- **v1.4**: 核心解耦，全面强化并发数据缓存机制。
- **v1.1 ~ v1.3**: 提供多货币支持，技术面板指标扩建，保险计算引擎迭代。
""")

# ── Session persistence: restore data on load ─────────────
from core.persistence import restore_session_data, save_session_data, export_all_data, import_all_data, clear_session_data

restored = restore_session_data()

# ── 个人财务仪表盘 ────────────────────────────────────────
st.markdown("---")
st.subheader("📊 个人财务仪表盘")

sym = get_symbol()

dash_compound = st.session_state.get("dashboard_compound")
dash_loan = st.session_state.get("dashboard_loan")
dash_savings = st.session_state.get("dashboard_savings")
dash_budget = st.session_state.get("dashboard_budget")
dash_retirement = st.session_state.get("dashboard_retirement")
dash_insurance = st.session_state.get("dashboard_insurance")
dash_networth = st.session_state.get("dashboard_networth")
dash_tax = st.session_state.get("dashboard_tax")

has_data = any([dash_compound, dash_loan, dash_savings, dash_budget, dash_retirement, dash_insurance, dash_networth, dash_tax])

if has_data:
    cols = st.columns(7)

    if dash_compound:
        cols[0].metric("💰 复利终值", fmt(dash_compound['final_balance'], decimals=0))
        cols[0].caption(f"累计收益 {fmt(dash_compound['total_interest'], decimals=0)}")

    if dash_loan:
        cols[1].metric("🏦 贷款总利息", fmt(dash_loan['total_interest'], decimals=0))
        cols[1].caption(f"每期还款 {fmt(dash_loan['monthly_payment'], decimals=0)}")

    if dash_savings:
        months = dash_savings["months_needed"]
        y, m = months // 12, months % 12
        cols[2].metric("🎯 储蓄达成", f"{y}年{m}个月")
        cols[2].caption(f"复利贡献 {fmt(dash_savings['total_interest'], decimals=0)}")

    if dash_budget:
        cols[3].metric("💡 月储蓄额", fmt(dash_budget['amt_save'], decimals=0))
        cols[3].caption(f"储蓄率 {dash_budget['pct_save']}%")

    if dash_retirement:
        gap = dash_retirement["gap"]
        if gap <= 0:
            cols[4].metric("🏖️ 退休评估", "✅ 已充足")
        else:
            cols[4].metric("🏖️ 退休缺口", fmt(gap, decimals=0))
            cols[4].caption(f"需额外月存 {fmt(dash_retirement['extra_monthly'], decimals=0)}")

    if dash_insurance:
        cols[5].metric("🛡️ 保险总保费", fmt(dash_insurance['total_premium'], decimals=0))
        cols[5].caption(f"保单 IRR {dash_insurance['irr_pct']:.2f}%")

    if dash_networth:
        cols[6].metric("🏠 净资产", fmt(dash_networth['net_worth'], decimals=0))
        cols[6].caption(f"资产 {fmt(dash_networth['total_assets'], decimals=0)}")

    if dash_tax:
        st.columns(1)  # spacer
        tax_col = st.columns(3)
        tax_col[0].metric("🧾 年应缴个税", fmt(dash_tax['annual_tax'], decimals=0))
        tax_col[1].metric("🧾 实际税率", f"{dash_tax['effective_rate']:.2f}%")
        tax_col[2].metric("🧾 税后月到手", fmt(dash_tax['after_tax_monthly'], decimals=0))

    st.caption("💡 提示：使用各工具后，仪表盘数据会自动更新。")

    # ── Multi-Dimensional Health Score (#1) ───────────────
    st.markdown("---")
    st.subheader("🏥 财务健康多维评分")

    dim_scores: list[tuple[str, int, str, str]] = []

    # Savings rate dimension
    if dash_budget:
        save_pct = dash_budget.get("pct_save", 0)
        if save_pct >= 30:
            s, tip, grade = 100, f"储蓄率 {save_pct}%，远超全国均值，表现卓越", "🟢"
        elif save_pct >= 20:
            s, tip, grade = 75, f"储蓄率 {save_pct}%，处于健康水平", "🟡"
        elif save_pct >= 10:
            s, tip, grade = 50, f"储蓄率 {save_pct}%，建议提升至 20% 以上", "🟠"
        else:
            s, tip, grade = 20, f"储蓄率 {save_pct}%，偏低，需要大幅改善", "🔴"
        dim_scores.append(("💡 储蓄能力", s, tip, grade))

    # Retirement readiness dimension
    if dash_retirement:
        gap = dash_retirement.get("gap", 0)
        extra = dash_retirement.get("extra_monthly", 0)
        if gap <= 0:
            s, tip, grade = 100, "退休资金已充足，无需额外储蓄", "🟢"
        elif extra < 2000:
            s, tip, grade = 70, f"退休缺口可控，每月仅需额外补充 {fmt(extra, decimals=0)}", "🟡"
        elif extra < 5000:
            s, tip, grade = 45, f"退休缺口较大，需每月额外储蓄 {fmt(extra, decimals=0)}", "🟠"
        else:
            s, tip, grade = 20, f"退休缺口严峻，需每月额外储蓄 {fmt(extra, decimals=0)}，请尽早行动", "🔴"
        dim_scores.append(("🏖️ 退休准备度", s, tip, grade))

    # Debt level dimension
    if dash_networth:
        total_assets_nw = dash_networth.get("total_assets", 0)
        total_liab_nw = total_assets_nw - dash_networth.get("net_worth", 0)
        dr = (total_liab_nw / total_assets_nw * 100) if total_assets_nw > 0 else 0
        if dr <= 20:
            s, tip, grade = 100, f"负债率 {dr:.1f}%，资产结构健康", "🟢"
        elif dr <= 40:
            s, tip, grade = 75, f"负债率 {dr:.1f}%，处于合理区间", "🟡"
        elif dr <= 60:
            s, tip, grade = 45, f"负债率 {dr:.1f}%，偏高，建议加速还款", "🟠"
        else:
            s, tip, grade = 15, f"负债率 {dr:.1f}%，过高，存在较大财务风险", "🔴"
        dim_scores.append(("💳 负债水平", s, tip, grade))

    # Net worth dimension
    if dash_networth:
        nw = dash_networth.get("net_worth", 0)
        if nw > 1000000:
            s, tip, grade = 100, f"净资产 {fmt(nw, decimals=0)}，资产积累丰厚", "🟢"
        elif nw > 200000:
            s, tip, grade = 70, f"净资产 {fmt(nw, decimals=0)}，处于正常成长阶段", "🟡"
        elif nw > 0:
            s, tip, grade = 50, f"净资产 {fmt(nw, decimals=0)}，尚在起步阶段，持续积累", "🟠"
        else:
            s, tip, grade = 10, f"净资产为负（{fmt(nw, decimals=0)}），需优先降低负债", "🔴"
        dim_scores.append(("🏠 净资产水平", s, tip, grade))

    # Tax efficiency dimension
    if dash_tax:
        eff_rate = dash_tax.get("effective_rate", 0)
        if eff_rate <= 5:
            s, tip, grade = 100, f"实际税率 {eff_rate:.1f}%，税务负担轻", "🟢"
        elif eff_rate <= 15:
            s, tip, grade = 75, f"实际税率 {eff_rate:.1f}%，属正常水平", "🟡"
        elif eff_rate <= 25:
            s, tip, grade = 50, f"实际税率 {eff_rate:.1f}%，可考虑税务优化策略", "🟠"
        else:
            s, tip, grade = 30, f"实际税率 {eff_rate:.1f}%，建议使用税务优化工具", "🔴"
        dim_scores.append(("🧾 税务效率", s, tip, grade))

    # Insurance dimension
    if dash_insurance:
        irr = dash_insurance.get("irr_pct", 0)
        if irr >= 4:
            s, tip, grade = 100, f"保险 IRR {irr:.2f}%，保单回报优质", "🟢"
        elif irr >= 2.5:
            s, tip, grade = 65, f"保险 IRR {irr:.2f}%，收益一般，关注保障覆盖", "🟡"
        else:
            s, tip, grade = 35, f"保险 IRR 仅 {irr:.2f}%，建议评估保单性价比", "🟠"
        dim_scores.append(("🛡️ 保险效益", s, tip, grade))

    if dim_scores:
        overall_score = int(sum(s for _, s, _, _ in dim_scores) / len(dim_scores))
        overall_grade = "🟢 优秀" if overall_score >= 80 else ("🟡 良好" if overall_score >= 60 else ("🟠 一般" if overall_score >= 40 else "🔴 需改善"))

        st.metric("💯 综合财务健康评分", f"{overall_score}/100", delta=overall_grade)

        _n_dim_cols = min(3, len(dim_scores))
        dim_cols = st.columns(_n_dim_cols)
        for idx, (name, score_v, tip, grade) in enumerate(dim_scores):
            with dim_cols[idx % _n_dim_cols]:
                st.metric(name, f"{score_v}/100", delta=grade)
                st.caption(tip)

        improvement_tips = [tip for _, score_v, tip, _ in dim_scores if score_v < 70]
        if improvement_tips:
            with st.expander("📋 改善建议详情"):
                for tip in improvement_tips:
                    st.markdown(f"- {tip}")
    else:
        st.caption("使用更多工具后，这里将展示各维度的精细评分与改善建议。")

    # ── Goal-Based Allocation (#6) ────────────────────────
    st.markdown("---")
    st.subheader("🎯 目标导向资金分配建议")

    goals_exist = False
    allocation_suggestions = []
    total_monthly_available = 0.0

    if dash_budget:
        total_monthly_available = dash_budget.get("amt_save", 0)

    if total_monthly_available > 0:
        if dash_retirement and dash_retirement.get("gap", 0) > 0:
            extra = dash_retirement.get("extra_monthly", 0)
            ratio = min(0.5, extra / total_monthly_available) if total_monthly_available > 0 else 0.3
            allocation_suggestions.append(("🏖️ 退休缺口补充", ratio, extra))
            goals_exist = True

        if dash_savings and dash_savings.get("months_needed", 0) > 0:
            # Allocate 30% or remaining
            remaining = 1.0 - sum(a[1] for a in allocation_suggestions)
            ratio = min(0.3, remaining)
            allocation_suggestions.append(("🎯 储蓄目标", ratio, total_monthly_available * ratio))
            goals_exist = True

        if dash_loan:
            remaining = 1.0 - sum(a[1] for a in allocation_suggestions)
            ratio = min(0.2, remaining)
            allocation_suggestions.append(("🏦 加速还贷", ratio, total_monthly_available * ratio))
            goals_exist = True

        # Allocate remainder
        used_ratio = sum(a[1] for a in allocation_suggestions)
        if used_ratio < 1.0:
            remaining_ratio = 1.0 - used_ratio
            allocation_suggestions.append(("💰 投资增值", remaining_ratio, total_monthly_available * remaining_ratio))

        if goals_exist:
            st.caption(f"基于您的月储蓄 {fmt(total_monthly_available, decimals=0)} 的推荐分配方案：")
            alloc_cols = st.columns(len(allocation_suggestions))
            for idx, (name, ratio, amount) in enumerate(allocation_suggestions):
                with alloc_cols[idx]:
                    st.metric(name, fmt(amount, decimals=0))
                    st.caption(f"占比 {ratio*100:.0f}%")
        else:
            st.caption("设置储蓄目标或退休参数后，将自动推荐资金分配方案。")
    else:
        st.caption("请先使用预算分配建议器设置收入，以获取资金分配建议。")

    # ── National Benchmark Comparison (#15) ───────────────
    st.markdown("---")
    st.subheader("📊 全国基准对比")

    from core.benchmarks import BENCHMARKS
    has_benchmark_data = False

    if dash_budget:
        has_benchmark_data = True
        save_rate = dash_budget.get("pct_save", 0)
        benchmark_save = BENCHMARKS.avg_savings_rate_pct
        delta = save_rate - benchmark_save
        bcol1, bcol2, bcol3 = st.columns(3)
        bcol1.metric("您的储蓄率", f"{save_rate}%", delta=f"{'高于' if delta >= 0 else '低于'}全国均值 {abs(delta):.1f}pp")
        bcol2.metric("全国平均储蓄率", f"{benchmark_save}%")
        bcol3.metric("全国人均存款", fmt(BENCHMARKS.avg_deposit_per_capita, decimals=0))

    if dash_networth:
        has_benchmark_data = True
        nw = dash_networth.get("net_worth", 0)
        total_assets = dash_networth.get("total_assets", 0)
        total_liab = total_assets - nw
        debt_ratio = (total_liab / total_assets * 100) if total_assets > 0 else 0
        benchmark_debt = BENCHMARKS.avg_debt_ratio_pct
        dcol1, dcol2 = st.columns(2)
        dcol1.metric("您的负债率", f"{debt_ratio:.1f}%", delta=f"{'低于' if debt_ratio <= benchmark_debt else '高于'}基准 {abs(debt_ratio - benchmark_debt):.1f}pp", delta_color="inverse")
        dcol2.metric("全国家庭负债率基准", f"{benchmark_debt}%")

    if not has_benchmark_data:
        st.caption("使用预算或净值工具后，将自动对比全国平均水平。")

    # Cross-tool insights
    st.markdown("---")
    st.subheader("🔗 跨工具综合分析")
    insights = []

    if dash_retirement and dash_savings:
        gap = dash_retirement.get("gap", 0)
        months = dash_savings.get("months_needed", 0)
        if gap > 0 and months > 0:
            insights.append(f"🏖️💰 **联动分析**：退休缺口约 {fmt(gap, decimals=0)}，而您的储蓄目标还需 {months // 12} 年达成。建议优先补齐退休缺口（额外月存 {fmt(dash_retirement.get('extra_monthly', 0), decimals=0)}），同时维持储蓄计划。")

    if dash_loan and dash_budget:
        loan_interest = dash_loan.get("total_interest", 0)
        savings_amt = dash_budget.get("amt_save", 0)
        if loan_interest > 0 and savings_amt > 0:
            loan_payment = dash_loan.get("monthly_payment", 0)
            insights.append(f"🏦💡 **债务 vs 储蓄**：当前月贷款还款 {fmt(loan_payment, decimals=0)}，月储蓄 {fmt(savings_amt, decimals=0)}。债务成本优先偿还可节省总利息 {fmt(loan_interest, decimals=0)}。")

    if dash_networth and dash_retirement:
        nw = dash_networth.get("net_worth", 0)
        gap = dash_retirement.get("gap", 0)
        if nw > 0 and gap > 0:
            coverage_pct = min(100.0, nw / gap * 100)
            insights.append(f"🏠🏖️ **净资产覆盖率**：当前净资产 {fmt(nw, decimals=0)} 可覆盖退休缺口的 **{coverage_pct:.1f}%**。{'建议继续增加投资资产。' if coverage_pct < 100 else '净资产已足以覆盖退休缺口，财务状况良好！'}")

    if dash_insurance and dash_compound:
        irr = dash_insurance.get("irr_pct", 0)
        compound_interest = dash_compound.get("total_interest", 0)
        final_balance = dash_compound.get("final_balance", 0)
        compound_annualized = (compound_interest / final_balance * 100) if final_balance > 0 and compound_interest > 0 else 0.0
        if irr > 0 and compound_annualized > 0:
            if irr < compound_annualized:
                insights.append(f"🛡️💰 **保险效率提示**：当前保单 IRR 为 {irr:.2f}%，低于复利投资年化收益约 {compound_annualized:.1f}%。若理财目标以增值为主，可考虑将部分保险支出转向复利投资。")
            else:
                insights.append(f"🛡️💰 **保险回报良好**：保单 IRR {irr:.2f}% 与复利投资收益相当，兼顾保障与收益。")
        elif irr > 0 and irr < 3:
            insights.append(f"🛡️💰 **保险效率提示**：当前保单 IRR 为 {irr:.2f}%，属于低收益型。若理财目标以增值为主，可考虑将保险支出转向复利投资。")

    if insights:
        for insight in insights:
            st.info(insight)
    else:
        st.caption("使用更多工具后，这里将显示跨工具的综合分析洞察。")

    # ── Cash Flow Timeline (#2) ────────────────────────────
    st.markdown("---")
    st.subheader("🌊 现金流时间轴规划器")
    st.caption("将所有工具的年度收支流叠加到统一时间轴，识别未来哪年现金流最紧张。")

    cf_years = list(range(1, 31))
    cf_income = [0.0] * 30
    cf_expense = [0.0] * 30
    cf_net = [0.0] * 30
    cf_has_data = False

    if dash_budget and dash_budget.get("amt_save", 0) > 0:
        monthly_save = dash_budget.get("amt_save", 0)
        for i in range(30):
            cf_income[i] += monthly_save * 12
        cf_has_data = True

    if dash_loan and dash_loan.get("monthly_payment", 0) > 0:
        monthly_pmt = dash_loan.get("monthly_payment", 0)
        for i in range(30):
            cf_expense[i] += monthly_pmt * 12
        cf_has_data = True

    if dash_retirement:
        gap = dash_retirement.get("gap", 0)
        extra = dash_retirement.get("extra_monthly", 0)
        if extra > 0:
            for i in range(30):
                cf_expense[i] += extra * 12
        cf_has_data = True

    if dash_savings and dash_savings.get("months_needed", 0) > 0:
        months_left = dash_savings.get("months_needed", 0)
        for i in range(30):
            yr_start_month = i * 12
            yr_end_month = (i + 1) * 12
            if yr_start_month < months_left:
                active_months = min(12, months_left - yr_start_month)
                monthly_deposit_sav = dash_savings.get("total_interest", 0)
        cf_has_data = True

    if cf_has_data:
        import plotly.graph_objects as go
        for i in range(30):
            cf_net[i] = cf_income[i] - cf_expense[i]

        current_year_cf = __import__("datetime").date.today().year
        years_labels = [str(current_year_cf + i) for i in range(30)]

        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(
            x=years_labels, y=cf_income,
            name="年度可用收入/储蓄",
            marker_color="#00CC96",
            opacity=0.75,
        ))
        fig_cf.add_trace(go.Bar(
            x=years_labels, y=[-v for v in cf_expense],
            name="年度支出/还款",
            marker_color="#EF553B",
            opacity=0.75,
        ))
        fig_cf.add_trace(go.Scatter(
            x=years_labels, y=cf_net,
            name="净现金流",
            mode="lines+markers",
            line=dict(width=2.5, color="#636EFA"),
            hovertemplate="%{x}<br>净现金流: " + sym + "%{y:,.0f}<extra></extra>",
        ))
        fig_cf.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)

        from core.chart_config import build_layout
        fig_cf.update_layout(
            **build_layout(xaxis_title="年份", yaxis_title=f"金额（{sym}）", yaxis_tickformat=","),
            barmode="relative",
        )
        st.plotly_chart(fig_cf, use_container_width=True)

        tightest_year_idx = cf_net.index(min(cf_net))
        if cf_net[tightest_year_idx] < 0:
            st.warning(f"⚠️ **{years_labels[tightest_year_idx]}年** 现金流压力最大，净现金流约 **{fmt(cf_net[tightest_year_idx], decimals=0)}**，建议提前做好资金储备。")
        else:
            best_year_idx = cf_net.index(max(cf_net))
            st.success(f"✅ 未来 30 年现金流整体为正。**{years_labels[best_year_idx]}年** 富余最多，约 **{fmt(cf_net[best_year_idx], decimals=0)}**。")
    else:
        st.caption("使用预算、贷款、储蓄等工具后，将在此自动生成跨工具现金流时间轴。")

    # ── Annual Financial Review (#5) ──────────────────────
    st.markdown("---")
    st.subheader("📅 年度财务回顾")
    st.caption("整合所有工具数据，生成结构化年度财务总结。")

    import datetime as _dt
    current_year_str = str(_dt.date.today().year)

    review_sections: list[str] = []

    if dash_networth:
        nw_val = dash_networth.get("net_worth", 0)
        total_a = dash_networth.get("total_assets", 0)
        total_l = total_a - nw_val
        review_sections.append(f"**资产负债状况**：总资产 {fmt(total_a, decimals=0)}，总负债 {fmt(total_l, decimals=0)}，净资产 {fmt(nw_val, decimals=0)}")

    if dash_budget:
        save_rate = dash_budget.get("pct_save", 0)
        save_amt = dash_budget.get("amt_save", 0)
        review_sections.append(f"**储蓄执行**：月储蓄 {fmt(save_amt, decimals=0)}，储蓄率 {save_rate}%")

    if dash_savings:
        months_left = dash_savings.get("months_needed", 0)
        if months_left > 0:
            review_sections.append(f"**储蓄目标进度**：距达成目标还需 {months_left // 12} 年 {months_left % 12} 个月")

    if dash_retirement:
        gap_ret = dash_retirement.get("gap", 0)
        extra_ret = dash_retirement.get("extra_monthly", 0)
        if gap_ret <= 0:
            review_sections.append("**退休规划**：退休资金已充足，计划执行良好")
        else:
            review_sections.append(f"**退休规划**：退休缺口 {fmt(gap_ret, decimals=0)}，需每月额外储蓄 {fmt(extra_ret, decimals=0)}")

    if dash_loan:
        review_sections.append(f"**债务管理**：贷款月还款 {fmt(dash_loan.get('monthly_payment', 0), decimals=0)}，累计利息支出 {fmt(dash_loan.get('total_interest', 0), decimals=0)}")

    if dash_insurance:
        review_sections.append(f"**保险保障**：年保费 {fmt(dash_insurance.get('total_premium', 0), decimals=0)}，保单 IRR {dash_insurance.get('irr_pct', 0):.2f}%")

    if dash_tax:
        review_sections.append(f"**税务情况**：年应缴税 {fmt(dash_tax.get('annual_tax', 0), decimals=0)}，实际税率 {dash_tax.get('effective_rate', 0):.1f}%，税后月到手 {fmt(dash_tax.get('after_tax_monthly', 0), decimals=0)}")

    if review_sections:
        st.markdown(f"### {current_year_str} 年度财务回顾")
        for section in review_sections:
            st.markdown(f"- {section}")

        if dim_scores:
            st.markdown(f"**综合健康评分**：{overall_score}/100 — {overall_grade}")

        review_text = f"{current_year_str} 年度财务回顾\n\n" + "\n".join(f"• {s}" for s in review_sections)
        if dim_scores:
            review_text += f"\n\n综合健康评分：{overall_score}/100"

        st.download_button(
            "📥 下载年度财务回顾 (TXT)",
            data=review_text,
            file_name=f"财务年度回顾_{current_year_str}.txt",
            mime="text/plain",
            use_container_width=False,
        )
    else:
        st.caption("使用各工具计算后，这里将自动汇总生成年度财务回顾报告。")

    # Auto-save session data
    save_session_data()

else:
    if restored > 0:
        st.success(f"✅ 已从磁盘恢复 {restored} 项仪表盘数据。")
        st.rerun()
    else:
        st.info("👆 请先使用左侧工具进行计算，仪表盘将自动汇总各工具的关键指标。")

# ── 综合财务诊断报告生成引擎 ─────────────────────────────────────
st.markdown("---")
st.subheader("📄 个人财务全景诊断归档")
st.write("一键全维扫描您的交互记录，提取所有核心指标并瞬间熔铸，为您秒级生成可脱机离线查阅的专属企业级 HTML 视觉财报。特别适配深浅明暗多主题无感切换；极度推荐查阅时按下 `Ctrl/Cmd + P` 轻松转储为纯矢量高清 PDF。")

from core.report_generator import generate_html_report

metrics_dict = {}
if dash_compound: metrics_dict["compound"] = dash_compound
if dash_loan: metrics_dict["loan"] = dash_loan
if dash_savings: metrics_dict["savings"] = dash_savings
if dash_budget: metrics_dict["budget"] = dash_budget
if dash_retirement: metrics_dict["retirement"] = dash_retirement
if dash_insurance: metrics_dict["insurance"] = dash_insurance
if dash_networth: metrics_dict["networth"] = dash_networth
if dash_tax: metrics_dict["tax"] = dash_tax

html_content = generate_html_report(metrics_dict)

report_cols = st.columns(2)
with report_cols[0]:
    st.download_button(
        label="📥 下载 HTML 财务诊断报告",
        data=html_content,
        file_name="OmniFinance_Health_Report.html",
        mime="text/html",
        type="primary",
        use_container_width=True,
    )

with report_cols[1]:
    from core.pdf_report import generate_pdf_report, is_pdf_available
    if is_pdf_available():
        pdf_bytes = generate_pdf_report(metrics_dict)
        if pdf_bytes:
            st.download_button(
                label="📥 下载 PDF 财务诊断报告",
                data=pdf_bytes,
                file_name="OmniFinance_Health_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        st.caption("💡 安装 weasyprint 可启用原生 PDF 导出")

# ── Data Persistence & Export Hub (#11, #16) ──────────────
st.markdown("---")
st.subheader("💾 数据管理")

pcol1, pcol2, pcol3 = st.columns(3)
with pcol1:
    if st.button("💾 保存仪表盘数据", use_container_width=True):
        save_session_data()
        st.success("✅ 数据已保存！")

with pcol2:
    export_data = export_all_data()
    st.download_button(
        label="📤 导出全部数据 (JSON)",
        data=export_data,
        file_name="OmniFinance_Backup.json",
        mime="application/json",
        use_container_width=True,
    )

with pcol3:
    uploaded = st.file_uploader("📥 导入数据备份", type=["json"], key="import_backup")
    if uploaded is not None:
        count = import_all_data(uploaded.read().decode("utf-8"))
        if count > 0:
            st.success(f"✅ 已导入 {count} 项数据！")
        else:
            st.warning("⚠️ 未找到有效数据。")

# ── Reminders (#12) ──────────────────────────────────────
st.markdown("---")
st.subheader("🔔 财务提醒")

from core.reminders import get_due_reminders, get_reminders, add_reminder, complete_reminder

due = get_due_reminders()
if due:
    for r in due:
        st.warning(f"⏰ **{r['title']}** — {r.get('description', '')} (到期: {r['due_date']})")

all_reminders = get_reminders()
if all_reminders:
    for r in all_reminders:
        rcol1, rcol2 = st.columns([4, 1])
        rcol1.caption(f"📌 {r['title']} — {r.get('due_date', '')} | {r.get('category', '')}")
        if rcol2.button("✅", key=f"rem_done_{r['id']}"):
            complete_reminder(r["id"])
            st.rerun()
else:
    st.caption("暂无提醒。可在下方添加新的财务提醒。")

with st.expander("➕ 添加新提醒"):
    rem_title = st.text_input("标题", key="rem_title")
    rem_desc = st.text_input("描述", key="rem_desc")
    rem_date = st.date_input("到期日", key="rem_date")
    rem_cat = st.selectbox("类别", ["还贷", "保费", "储蓄", "投资", "税务", "其他"], key="rem_cat")
    if st.button("添加提醒"):
        if rem_title:
            add_reminder(rem_title, rem_desc, str(rem_date), rem_cat)
            st.success("✅ 提醒已添加！")
            st.rerun()

st.markdown("---")
st.caption("***Eugene Finance 核心架构驱动 | Empower Your Knowledge, Enrich Your Life***")
