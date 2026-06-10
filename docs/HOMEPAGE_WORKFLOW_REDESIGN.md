# Homepage Workflow Redesign

This document defines the next homepage redesign for OmniFinance. The goal is to make the homepage feel like a decision center instead of a directory of independent tools.

## Current Problem

The current homepage already includes many valuable modules:

- dashboard metrics;
- financial health score;
- opportunity radar;
- stress test lab;
- decision brief;
- action impact simulator;
- goal-based allocation;
- benchmark comparison;
- cross-tool insights;
- cash-flow timeline;
- annual review;
- report export;
- data management;
- reminders.

However, the top section still starts like a tool catalog. Users may see many calculators before understanding the main workflow.

The homepage should first answer three questions:

1. Where am I financially?
2. What is the most important issue or opportunity?
3. What should I do next?

## Target Positioning

The homepage should be positioned as:

> OmniFinance Decision Center: a single page that turns personal finance inputs into diagnosis, risk signals, priority actions, and exportable reports.

## Target Workflow

```text
1. Build financial profile
   - Budget
   - Net worth
   - Retirement
   - Debt
   - Insurance

2. Diagnose current state
   - Financial health score
   - Key metrics
   - Weak dimensions

3. Identify opportunities
   - Opportunity radar
   - Priority cards
   - 90-day sprint

4. Test downside risk
   - Emergency buffer
   - Income shock
   - Expense shock
   - Asset drawdown

5. Choose actions
   - What-if action simulator
   - First-week checklist
   - Action impact score

6. Export and review
   - Markdown brief
   - HTML/PDF report
   - Annual review
   - Reminder loop
```

## Proposed Homepage Structure

### 1. Hero Section

Replace the current simple title and quick-start block with a clearer hero message.

Suggested copy:

```python
st.title(f"🌟 OmniFinance Decision Center `{VERSION}`")
st.caption("把个人财务数据转化为诊断、机会、压力测试和行动计划。")
st.info("建议先完成预算、净资产和退休三个基础输入，首页会自动生成健康评分、机会雷达和行动建议。")
```

Add four workflow cards:

- ① 建立财务画像
- ② 生成健康诊断
- ③ 识别机会与风险
- ④ 输出行动计划

### 2. Starter Path

Instead of listing all categories first, show a recommended path for first-time users:

1. Budget Planner
2. Net Worth Tracker
3. Retirement Estimator
4. Action Impact Simulator

The full tool catalog can remain, but should be placed inside an expander named "全部工具".

### 3. Progress Strip

Add a simple progress indicator based on available dashboard data:

- Budget completed
- Net worth completed
- Retirement completed
- Debt completed
- Insurance completed
- Tax completed

This helps users understand what data is missing.

### 4. Decision Summary First

When data exists, show a top summary before detailed modules:

- overall health score;
- number of opportunities;
- number of stress scenarios requiring attention;
- number of priority actions;
- next best action.

This should appear before charts and long sections.

### 5. Make Advanced Sections Collapsible

The homepage currently becomes long once data exists. Keep the decision chain visible, but collapse secondary modules by default:

Recommended default expanded:

- dashboard metrics;
- health score;
- opportunity radar;
- action impact simulator.

Recommended default collapsed:

- national benchmark comparison;
- cash-flow timeline;
- annual review;
- data management;
- reminders;
- version history.

### 6. Report Export Section

Rename the report section to a more direct user-facing phrase:

Current:

```text
个人财务全景诊断归档
```

Suggested:

```text
报告导出与复盘
```

Suggested copy:

```text
导出当前仪表盘、健康评分、机会识别和行动计划，用于离线归档、月度复盘或进一步讨论。
```

Avoid overly promotional wording such as "企业级" or "熔铸". A clean product tone is more credible.

## Implementation Checklist

### Low-risk changes

- [ ] Update homepage title and subtitle.
- [ ] Add workflow cards.
- [ ] Add recommended starter path.
- [ ] Move full tool catalog into an expander.
- [ ] Rename report export section.
- [ ] Replace overly promotional copy with clearer product copy.

### Medium-risk changes

- [ ] Add profile completion progress strip.
- [ ] Add top decision summary when dashboard data exists.
- [ ] Collapse secondary sections by default.

### Higher-risk changes

- [ ] Split homepage into helper functions.
- [ ] Move repeated UI card logic into `core/ui.py`.
- [ ] Add tests for dashboard summary generation.
- [ ] Create a `core/dashboard.py` module for homepage-level aggregation.

## Suggested First Code Commit

The safest first code commit should only edit the top of `home.py`:

- title;
- subtitle;
- first-time guidance;
- recommended starter path;
- full tool catalog expander.

Do not change calculations in the first homepage refactor commit.

## Suggested Future Module Extraction

The current homepage can later be split into smaller functions:

```python
def render_hero():
    ...

def render_starter_path():
    ...

def render_tool_catalog():
    ...

def render_dashboard_metrics(...):
    ...

def render_health_section(...):
    ...

def render_opportunity_section(...):
    ...

def render_stress_section(...):
    ...

def render_action_plan_section(...):
    ...
```

This will reduce file length and make future homepage changes safer.

## Success Criteria

The redesign is successful if a new visitor can understand the product in 30 seconds:

- what OmniFinance does;
- what they should input first;
- what output they will receive;
- which action they should take next.
