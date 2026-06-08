"""Financial opportunity radar and action sprint planning.

This module turns dashboard metrics into prioritized, actionable opportunities.
It complements the health score: the score answers "how am I doing?", while the
radar answers "where is the next practical upside?".
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

MoneyFormatter = Callable[[float], str]
Priority = Literal["高", "中", "低"]


@dataclass(frozen=True)
class Opportunity:
    """One actionable financial improvement opportunity."""

    key: str
    title: str
    category: str
    priority: Priority
    impact_score: int
    confidence: int
    page_key: str
    metric_label: str
    metric_value: str
    rationale: str
    actions: tuple[str, ...]


@dataclass(frozen=True)
class SprintStep:
    """One phase in a 90-day financial action sprint."""

    phase: str
    title: str
    focus: str
    page_key: str
    checklist: tuple[str, ...]


@dataclass(frozen=True)
class OpportunityReport:
    """Aggregated opportunity radar result."""

    opportunities: tuple[Opportunity, ...]

    @property
    def top_opportunity(self) -> Opportunity | None:
        return self.opportunities[0] if self.opportunities else None

    @property
    def high_priority_count(self) -> int:
        return sum(1 for opportunity in self.opportunities if opportunity.priority == "高")

    @property
    def summary(self) -> str:
        if not self.opportunities:
            return "暂无明显机会，建议继续补充数据"
        top = self.top_opportunity
        assert top is not None
        if self.high_priority_count:
            return f"发现 {len(self.opportunities)} 个机会，其中 {self.high_priority_count} 个高优先级；首要关注：{top.title}"
        return f"发现 {len(self.opportunities)} 个优化机会；首要关注：{top.title}"


def _money(value: float, formatter: MoneyFormatter) -> str:
    return formatter(float(value))


def _clamp_score(value: float, *, minimum: int = 1, maximum: int = 100) -> int:
    return max(minimum, min(maximum, int(round(value))))


def _priority(score: int) -> Priority:
    if score >= 75:
        return "高"
    if score >= 50:
        return "中"
    return "低"


def _available_monthly_saving(budget: Mapping[str, Any] | None) -> float:
    if not budget:
        return 0.0
    return float(budget.get("amt_save", 0) or 0)


def build_opportunity_radar(
    *,
    budget: Mapping[str, Any] | None = None,
    loan: Mapping[str, Any] | None = None,
    savings: Mapping[str, Any] | None = None,
    retirement: Mapping[str, Any] | None = None,
    networth: Mapping[str, Any] | None = None,
    tax: Mapping[str, Any] | None = None,
    insurance: Mapping[str, Any] | None = None,
    money_formatter: MoneyFormatter = lambda value: f"{value:,.0f}",
    limit: int = 6,
) -> OpportunityReport:
    """Build a prioritized list of opportunities from dashboard metrics.

    The heuristic intentionally uses only already-available dashboard outputs so
    it remains fast, deterministic, and testable. Each rule favors an actionable
    next step that can be completed in an existing OmniFinance tool.
    """
    opportunities: list[Opportunity] = []
    monthly_saving = _available_monthly_saving(budget)

    if budget:
        income = float(budget.get("income", 0) or 0)
        save_pct = float(budget.get("pct_save", 0) or 0)
        if income > 0 and save_pct < 20:
            target_monthly = income * 0.20
            gap = max(0.0, target_monthly - monthly_saving)
            score = _clamp_score(45 + (20 - save_pct) * 3)
            opportunities.append(
                Opportunity(
                    key="raise_savings_rate",
                    title="把储蓄率拉回 20% 健康线",
                    category="现金流",
                    priority=_priority(score),
                    impact_score=score,
                    confidence=92,
                    page_key="budget",
                    metric_label="距 20% 储蓄率",
                    metric_value=_money(gap, money_formatter) + "/月",
                    rationale=f"当前储蓄率 {save_pct:g}%，低于 20% 健康线；每月多释放 {_money(gap, money_formatter)} 可显著改善现金流韧性。",
                    actions=(
                        "复核固定支出与高频小额消费，先找出 3 项可压缩支出。",
                        "将新增结余优先分配到应急金或高息债务。",
                        "一周后回到预算工具复算储蓄率。",
                    ),
                )
            )

    if loan and budget:
        income = float(budget.get("income", 0) or 0)
        monthly_payment = float(loan.get("monthly_payment", 0) or 0)
        total_interest = float(loan.get("total_interest", 0) or 0)
        payment_ratio = monthly_payment / income * 100 if income > 0 else 0.0
        if payment_ratio > 25 or (monthly_saving > 0 and total_interest > monthly_saving * 12):
            score = _clamp_score(50 + max(payment_ratio - 25, 0) * 2 + min(total_interest / max(monthly_saving * 12, 1), 3) * 8)
            opportunities.append(
                Opportunity(
                    key="debt_acceleration",
                    title="评估提前还款与债务加速",
                    category="债务",
                    priority=_priority(score),
                    impact_score=score,
                    confidence=82,
                    page_key="loan",
                    metric_label="月供收入比",
                    metric_value=f"{payment_ratio:.1f}%",
                    rationale=f"当前月供约占收入 {payment_ratio:.1f}%，总利息 {_money(total_interest, money_formatter)}；优化还款节奏可能释放长期现金流。",
                    actions=(
                        "在贷款计算器中开启提前还款模拟，比较节省利息与流动性占用。",
                        "保留 3-6 个月支出作为安全垫后，再决定提前还款额度。",
                        "若存在多笔债务，进入债务规划器比较雪球法与雪崩法。",
                    ),
                )
            )

    if retirement:
        gap = float(retirement.get("gap", 0) or 0)
        extra_monthly = float(retirement.get("extra_monthly", 0) or 0)
        if gap > 0:
            pressure = extra_monthly / monthly_saving if monthly_saving > 0 else 2.0
            score = _clamp_score(55 + min(pressure, 2.5) * 15)
            opportunities.append(
                Opportunity(
                    key="retirement_gap",
                    title="把退休缺口拆成可执行月计划",
                    category="人生规划",
                    priority=_priority(score),
                    impact_score=score,
                    confidence=88,
                    page_key="retirement",
                    metric_label="额外月存需求",
                    metric_value=_money(extra_monthly, money_formatter),
                    rationale=f"退休缺口约 {_money(gap, money_formatter)}，需额外月存 {_money(extra_monthly, money_formatter)}；越早拆解，复利压力越小。",
                    actions=(
                        "用退休金估算器测试延迟退休、提高收益率、降低退休支出的敏感度。",
                        "将额外月存需求拆成自动定投、预算压降和收入提升三部分。",
                        "对高不确定性假设执行蒙特卡洛模拟，观察成功概率。",
                    ),
                )
            )

    if savings:
        months_needed = int(savings.get("months_needed", 0) or 0)
        if months_needed > 36:
            score = _clamp_score(45 + min((months_needed - 36) / 12, 4) * 10)
            opportunities.append(
                Opportunity(
                    key="goal_timeline",
                    title="压缩长期储蓄目标周期",
                    category="目标管理",
                    priority=_priority(score),
                    impact_score=score,
                    confidence=78,
                    page_key="savings",
                    metric_label="目标剩余时间",
                    metric_value=f"{months_needed // 12}年{months_needed % 12}个月",
                    rationale="储蓄目标周期超过 3 年，容易受通胀、收入变化和执行疲劳影响；适合重新校准目标金额与月投入。",
                    actions=(
                        "把大目标拆成 12 个月里程碑，先确认第一阶段资金缺口。",
                        "测试每月多投入 10% 与收益率提高 1 个百分点的达成时间差异。",
                        "将关键节点添加到财务提醒。",
                    ),
                )
            )

    if networth and budget:
        income = float(budget.get("income", 0) or 0)
        monthly_expense = max(0.0, income - monthly_saving)
        net_worth = float(networth.get("net_worth", 0) or 0)
        if monthly_expense > 0 and net_worth < monthly_expense * 6:
            months_buffer = max(0.0, net_worth / monthly_expense)
            score = _clamp_score(70 - months_buffer * 6)
            opportunities.append(
                Opportunity(
                    key="emergency_buffer",
                    title="建立 6 个月安全垫",
                    category="风险防御",
                    priority=_priority(score),
                    impact_score=score,
                    confidence=75,
                    page_key="networth",
                    metric_label="估算安全垫",
                    metric_value=f"{months_buffer:.1f}个月",
                    rationale=f"按当前支出估算，净资产约覆盖 {months_buffer:.1f} 个月支出；建议逐步建立 6 个月安全垫。",
                    actions=(
                        "在资产净值追踪器中区分现金、投资和长期资产。",
                        "优先把每月结余的一部分划入高流动性账户。",
                        "安全垫达标前，谨慎增加高波动投资或大额提前还款。",
                    ),
                )
            )

    if tax:
        effective_rate = float(tax.get("effective_rate", 0) or 0)
        annual_tax = float(tax.get("annual_tax", 0) or 0)
        if effective_rate > 15:
            score = _clamp_score(42 + (effective_rate - 15) * 2.2)
            opportunities.append(
                Opportunity(
                    key="tax_efficiency",
                    title="复核专项扣除与税后收益",
                    category="税务",
                    priority=_priority(score),
                    impact_score=score,
                    confidence=72,
                    page_key="tax",
                    metric_label="实际税率",
                    metric_value=f"{effective_rate:.1f}%",
                    rationale=f"当前实际税率 {effective_rate:.1f}%，年税额约 {_money(annual_tax, money_formatter)}；专项扣除和投资税后收益值得复核。",
                    actions=(
                        "检查子女教育、住房、赡养老人、继续教育和个人养老金扣除是否完整。",
                        "比较投资收益税后回报，而不是只看名义收益率。",
                        "年底前预留一次税务复盘提醒。",
                    ),
                )
            )

    if insurance:
        irr = float(insurance.get("irr_pct", 0) or 0)
        total_premium = float(insurance.get("total_premium", 0) or 0)
        if irr < 2.5 and total_premium > 0:
            score = _clamp_score(58 + max(0, 2.5 - irr) * 8)
            opportunities.append(
                Opportunity(
                    key="insurance_value",
                    title="复核保单保障效率",
                    category="保障",
                    priority=_priority(score),
                    impact_score=score,
                    confidence=68,
                    page_key="insurance",
                    metric_label="保单 IRR",
                    metric_value=f"{irr:.2f}%",
                    rationale=f"当前保单 IRR {irr:.2f}%，总保费 {_money(total_premium, money_formatter)}；需要确认保障价值是否匹配现金流占用。",
                    actions=(
                        "区分保障型与储蓄型需求，不用单一 IRR 判断全部价值。",
                        "比较现金价值、退保损失与替代保障方案。",
                        "若保障缺口明确，优先补足保障；若主要为增值目标，则比较长期投资方案。",
                    ),
                )
            )

    ranked = sorted(opportunities, key=lambda item: (-item.impact_score, item.category, item.title))
    return OpportunityReport(tuple(ranked[:limit]))


def build_90_day_sprint(report: OpportunityReport, *, limit: int = 3) -> tuple[SprintStep, ...]:
    """Convert the top opportunities into a compact 90-day execution plan."""
    phases = ("0-30 天", "31-60 天", "61-90 天")
    steps: list[SprintStep] = []
    for phase, opportunity in zip(phases, report.opportunities[:limit], strict=False):
        steps.append(
            SprintStep(
                phase=phase,
                title=opportunity.title,
                focus=opportunity.rationale,
                page_key=opportunity.page_key,
                checklist=opportunity.actions,
            )
        )
    return tuple(steps)
