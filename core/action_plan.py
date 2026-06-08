"""Action impact simulation for the OmniFinance dashboard.

This module turns the dashboard's current state into a short list of "what-if"
actions. Unlike the opportunity radar, which identifies weak areas, the action
plan estimates the likely impact, effort, and first-week execution steps for each
candidate action. The rules are deterministic, private, and intentionally easy to
explain in the UI.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

MoneyFormatter = Callable[[float], str]
Priority = Literal["高", "中", "低"]
Effort = Literal["低", "中", "高"]


@dataclass(frozen=True)
class ActionImpact:
    """One simulated action and its expected dashboard impact."""

    key: str
    title: str
    category: str
    priority: Priority
    effort: Effort
    horizon_days: int
    estimated_uplift: int
    page_key: str
    current_signal: str
    target_signal: str
    rationale: str
    first_week_steps: tuple[str, ...]


@dataclass(frozen=True)
class ActionImpactPlan:
    """Ranked action impact plan for the next execution cycle."""

    actions: tuple[ActionImpact, ...]
    baseline_score: int | None
    momentum_score: int | None

    @property
    def top_action(self) -> ActionImpact | None:
        return self.actions[0] if self.actions else None

    @property
    def total_estimated_uplift(self) -> int:
        return sum(action.estimated_uplift for action in self.actions)

    @property
    def high_priority_count(self) -> int:
        return sum(1 for action in self.actions if action.priority == "高")

    @property
    def summary(self) -> str:
        if not self.actions:
            return "暂无足够数据生成行动影响模拟，请先补充预算、净资产或退休测算。"
        top = self.top_action
        assert top is not None
        momentum = "暂无" if self.momentum_score is None else f"{self.momentum_score}/100"
        return f"发现 {len(self.actions)} 个可模拟行动；首要行动：{top.title}；执行后动能评分约 {momentum}。"

    def to_markdown(self) -> str:
        """Render the action plan as Markdown for copying into a weekly plan."""
        baseline = "暂无" if self.baseline_score is None else f"{self.baseline_score}/100"
        momentum = "暂无" if self.momentum_score is None else f"{self.momentum_score}/100"
        sections = [
            "# OmniFinance 行动影响模拟",
            "",
            f"- 基线评分：{baseline}",
            f"- 执行动能评分：{momentum}",
            f"- 预计总提升：+{self.total_estimated_uplift}",
            "",
            "## 推荐行动",
        ]
        for action in self.actions:
            sections.extend(
                [
                    f"### {action.title}",
                    f"- 类别：{action.category}",
                    f"- 优先级：{action.priority}",
                    f"- 预计提升：+{action.estimated_uplift}",
                    f"- 当前信号：{action.current_signal}",
                    f"- 目标信号：{action.target_signal}",
                    "- 第一周步骤：",
                    *(f"  - {step}" for step in action.first_week_steps),
                    "",
                ]
            )
        return "\n".join(sections).strip() + "\n"


def _clamp(value: float, *, minimum: int = 1, maximum: int = 100) -> int:
    return max(minimum, min(maximum, int(round(value))))


def _money(value: float, formatter: MoneyFormatter) -> str:
    return formatter(float(value))


def _priority(uplift: int) -> Priority:
    if uplift >= 16:
        return "高"
    if uplift >= 9:
        return "中"
    return "低"


def _effort(horizon_days: int, uplift: int) -> Effort:
    if horizon_days <= 14 and uplift >= 10:
        return "低"
    if horizon_days <= 45:
        return "中"
    return "高"


def _append_action(
    actions: list[ActionImpact],
    *,
    key: str,
    title: str,
    category: str,
    horizon_days: int,
    estimated_uplift: int,
    page_key: str,
    current_signal: str,
    target_signal: str,
    rationale: str,
    first_week_steps: tuple[str, ...],
) -> None:
    uplift = _clamp(estimated_uplift, minimum=3, maximum=30)
    actions.append(
        ActionImpact(
            key=key,
            title=title,
            category=category,
            priority=_priority(uplift),
            effort=_effort(horizon_days, uplift),
            horizon_days=horizon_days,
            estimated_uplift=uplift,
            page_key=page_key,
            current_signal=current_signal,
            target_signal=target_signal,
            rationale=rationale,
            first_week_steps=first_week_steps,
        )
    )


def build_action_impact_plan(
    *,
    budget: Mapping[str, Any] | None = None,
    loan: Mapping[str, Any] | None = None,
    retirement: Mapping[str, Any] | None = None,
    networth: Mapping[str, Any] | None = None,
    health_report: Any | None = None,
    opportunity_report: Any | None = None,
    stress_report: Any | None = None,
    money_formatter: MoneyFormatter = lambda value: f"{value:,.0f}",
    limit: int = 5,
) -> ActionImpactPlan:
    """Build a ranked set of simulated next actions.

    The returned uplift is not a financial forecast. It is a normalized impact
    estimate used to compare actions on the dashboard and prioritize execution.
    """
    actions: list[ActionImpact] = []
    baseline_score = getattr(health_report, "overall_score", None)

    monthly_income = float((budget or {}).get("income", 0) or 0)
    monthly_saving = float((budget or {}).get("amt_save", 0) or 0)
    save_pct = float((budget or {}).get("pct_save", 0) or 0)
    monthly_expense = max(0.0, monthly_income - monthly_saving)

    stress_buffer_months = getattr(stress_report, "buffer_months", None)
    liquid_buffer = float(getattr(stress_report, "liquid_buffer", 0.0) or 0.0)
    if stress_buffer_months is not None and monthly_expense > 0 and stress_buffer_months < 3:
        target_buffer = monthly_expense * 3
        gap = max(0.0, target_buffer - liquid_buffer)
        _append_action(
            actions,
            key="emergency_buffer_sprint",
            title="30 天应急金冲刺",
            category="风险防御",
            horizon_days=30,
            estimated_uplift=18 + max(0, 3 - int(stress_buffer_months)) * 3,
            page_key="networth",
            current_signal=f"安全垫约 {stress_buffer_months:.1f} 个月",
            target_signal=f"先补到 3 个月必要支出（缺口 {_money(gap, money_formatter)}）",
            rationale="压力测试显示现金防线不足，先建立流动性缓冲可同时降低收入下降和突发支出的脆弱性。",
            first_week_steps=(
                "把资产净值追踪器中的现金、货基、活期与长期投资分开记录。",
                "从本月结余中先划转一笔固定金额到应急金账户。",
                "暂停非必要大额支出，直到安全垫超过 3 个月。",
            ),
        )

    if monthly_income > 0 and save_pct < 20:
        target_saving = monthly_income * 0.20
        gap = max(0.0, target_saving - monthly_saving)
        _append_action(
            actions,
            key="savings_rate_lift",
            title="把储蓄率拉回 20% 健康线",
            category="现金流",
            horizon_days=21,
            estimated_uplift=10 + int((20 - save_pct) * 0.7),
            page_key="budget",
            current_signal=f"当前储蓄率 {save_pct:g}%",
            target_signal=f"每月多释放 {_money(gap, money_formatter)}，达到 20% 储蓄率",
            rationale="储蓄率是所有长期目标的燃料，提升到 20% 后可同时支持应急金、退休缺口和投资计划。",
            first_week_steps=(
                "在预算工具中标记前三类可压缩支出。",
                "把新增结余设置为自动转账，避免月底剩余法失效。",
                "一周后复盘实际支出，确认新预算是否可持续。",
            ),
        )

    if loan:
        monthly_payment = float(loan.get("monthly_payment", 0) or 0)
        total_interest = float(loan.get("total_interest", 0) or 0)
        if monthly_payment > 0 and total_interest > 0 and monthly_saving > 0:
            extra_payment = monthly_saving * 0.20
            _append_action(
                actions,
                key="debt_acceleration_test",
                title="提前还款影响测试",
                category="债务优化",
                horizon_days=14,
                estimated_uplift=8 + min(12, int(total_interest / max(monthly_saving * 12, 1) * 4)),
                page_key="loan",
                current_signal=f"剩余总利息约 {_money(total_interest, money_formatter)}",
                target_signal=f"测试每月额外还款 {_money(extra_payment, money_formatter)} 的节息效果",
                rationale="在不破坏安全垫的前提下，提前还款可降低长期利息并改善未来现金流。",
                first_week_steps=(
                    "在贷款计算器中复制当前贷款参数作为基线。",
                    "加入 20% 月结余作为额外还款，比较总利息和还清时间。",
                    "若安全垫低于 3 个月，先降低提前还款额度。",
                ),
            )

    if retirement:
        gap = float(retirement.get("gap", 0) or 0)
        extra_monthly = float(retirement.get("extra_monthly", 0) or 0)
        if gap > 0:
            coverage = monthly_saving / extra_monthly if extra_monthly > 0 else 0.0
            _append_action(
                actions,
                key="retirement_gap_bridge",
                title="退休缺口桥接计划",
                category="长期规划",
                horizon_days=60,
                estimated_uplift=9 + (0 if coverage >= 1 else min(15, int((1 - coverage) * 12))),
                page_key="retirement",
                current_signal=f"退休缺口约 {_money(gap, money_formatter)}",
                target_signal=f"将额外月存 {_money(extra_monthly, money_formatter)} 拆成预算、投资和退休年龄三类变量",
                rationale="退休缺口通常不是单一月存问题，同时调整支出、收益率和退休时间能显著降低执行压力。",
                first_week_steps=(
                    "在退休金估算器中分别测试收益率、退休年龄和退休支出三组敏感度。",
                    "把额外月存需求拆成自动定投与支出压降两部分。",
                    "记录最容易执行的一组假设，作为下月复盘基线。",
                ),
            )

    if networth:
        total_assets = float(networth.get("total_assets", 0) or 0)
        net_worth = float(networth.get("net_worth", 0) or 0)
        if total_assets > 0:
            debt_ratio = max(0.0, (total_assets - net_worth) / total_assets * 100)
            if debt_ratio > 45:
                _append_action(
                    actions,
                    key="debt_ratio_reset",
                    title="负债率降档路线图",
                    category="资产负债表",
                    horizon_days=45,
                    estimated_uplift=10 + min(12, int((debt_ratio - 45) / 3)),
                    page_key="networth",
                    current_signal=f"负债率约 {debt_ratio:.1f}%",
                    target_signal="先降到 45% 以下，再追求投资增长",
                    rationale="负债率偏高会放大收入波动、利率变化和资产回撤的压力，适合优先做结构修复。",
                    first_week_steps=(
                        "按利率、余额和月供列出所有债务。",
                        "优先处理高息或现金流压力最大的债务。",
                        "每月更新净资产表，跟踪负债率是否下降。",
                    ),
                )

    if not actions and opportunity_report is not None and getattr(opportunity_report, "opportunities", None):
        top = opportunity_report.top_opportunity
        _append_action(
            actions,
            key=f"opportunity_{top.key}",
            title=f"执行机会雷达首要项：{top.title}",
            category=top.category,
            horizon_days=30,
            estimated_uplift=max(6, int(top.impact_score * 0.18)),
            page_key=top.page_key,
            current_signal=top.metric_value,
            target_signal="完成首个可验证动作并在首页复盘",
            rationale=top.rationale,
            first_week_steps=top.actions[:3],
        )

    if not actions and baseline_score is not None and baseline_score >= 75:
        _append_action(
            actions,
            key="growth_review",
            title="增长型资产配置复盘",
            category="增长优化",
            horizon_days=30,
            estimated_uplift=7,
            page_key="portfolio",
            current_signal=f"健康评分 {baseline_score}/100",
            target_signal="用组合优化或蒙特卡洛确认风险收益是否匹配长期目标",
            rationale="当前基础盘较稳，下一步重点不是修补短板，而是提高资金使用效率和长期增长确定性。",
            first_week_steps=(
                "整理当前主要资产类别和目标权重。",
                "进入投资组合优化器比较风险、收益和回撤。",
                "把年度再平衡规则写入财务日历。",
            ),
        )

    ranked = sorted(actions, key=lambda item: (-item.estimated_uplift, item.horizon_days, item.title))[:limit]
    if baseline_score is None:
        momentum_score = None if not ranked else _clamp(50 + sum(action.estimated_uplift for action in ranked) * 0.5)
    else:
        momentum_score = _clamp(baseline_score + sum(action.estimated_uplift for action in ranked) * 0.45)

    return ActionImpactPlan(tuple(ranked), baseline_score, momentum_score)
