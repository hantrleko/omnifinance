"""Personal finance stress testing utilities.

The dashboard already explains current health and next opportunities. This module
adds a forward-looking resilience layer: what happens if income drops, expenses
spike, loan payments rise, or long-term assets draw down?
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

MoneyFormatter = Callable[[float], str]
StressStatus = Literal["safe", "watch", "critical"]
StressSeverity = Literal["温和", "中等", "严重"]


@dataclass(frozen=True)
class StressScenario:
    """One deterministic stress scenario."""

    key: str
    title: str
    severity: StressSeverity
    status: StressStatus
    resilience_score: int
    buffer_months_after: float
    liquidity_gap: float
    estimated_impact: float
    page_key: str
    narrative: str
    actions: tuple[str, ...]


@dataclass(frozen=True)
class StressReport:
    """Aggregated household resilience report."""

    scenarios: tuple[StressScenario, ...]
    monthly_income: float
    monthly_expense: float
    monthly_surplus: float
    liquid_buffer: float

    @property
    def buffer_months(self) -> float:
        if self.monthly_expense <= 0:
            return 0.0
        return self.liquid_buffer / self.monthly_expense

    @property
    def weakest_scenario(self) -> StressScenario | None:
        return self.scenarios[0] if self.scenarios else None

    @property
    def critical_count(self) -> int:
        return sum(1 for scenario in self.scenarios if scenario.status == "critical")

    @property
    def summary(self) -> str:
        if not self.scenarios:
            return "暂无足够数据进行压力测试"
        weakest = self.weakest_scenario
        assert weakest is not None
        if self.critical_count:
            return f"发现 {self.critical_count} 个高压场景；最脆弱场景：{weakest.title}"
        return f"压力测试通过基础防线；最需关注：{weakest.title}"


def _money(value: float, formatter: MoneyFormatter) -> str:
    return formatter(float(value))


def _clamp_score(value: float) -> int:
    return max(1, min(100, int(round(value))))


def _status(buffer_months_after: float, liquidity_gap: float) -> StressStatus:
    if liquidity_gap > 0 or buffer_months_after < 1:
        return "critical"
    if buffer_months_after < 3:
        return "watch"
    return "safe"


def _score(buffer_months_after: float, liquidity_gap: float, monthly_expense: float) -> int:
    gap_penalty = liquidity_gap / max(monthly_expense, 1) * 18
    return _clamp_score(35 + buffer_months_after * 13 - gap_penalty)


def _liquid_buffer(networth: Mapping[str, Any] | None, monthly_surplus: float) -> float:
    """Estimate liquid resilience from dashboard data.

    Net-worth data does not distinguish cash from illiquid assets, so the model
    conservatively treats 25% of positive net worth as accessible and falls back
    to three months of current surplus when net-worth data is missing.
    """
    if networth:
        net_worth = max(0.0, float(networth.get("net_worth", 0) or 0))
        return net_worth * 0.25
    return max(0.0, monthly_surplus) * 3


def _make_scenario(
    *,
    key: str,
    title: str,
    severity: StressSeverity,
    impact: float,
    liquid_buffer: float,
    monthly_expense: float,
    page_key: str,
    narrative: str,
    actions: tuple[str, ...],
) -> StressScenario:
    remaining = liquid_buffer - impact
    liquidity_gap = max(0.0, -remaining)
    buffer_after = max(0.0, remaining) / monthly_expense if monthly_expense > 0 else 0.0
    return StressScenario(
        key=key,
        title=title,
        severity=severity,
        status=_status(buffer_after, liquidity_gap),
        resilience_score=_score(buffer_after, liquidity_gap, monthly_expense),
        buffer_months_after=buffer_after,
        liquidity_gap=liquidity_gap,
        estimated_impact=impact,
        page_key=page_key,
        narrative=narrative,
        actions=actions,
    )


def build_stress_report(
    *,
    budget: Mapping[str, Any] | None = None,
    loan: Mapping[str, Any] | None = None,
    retirement: Mapping[str, Any] | None = None,
    networth: Mapping[str, Any] | None = None,
    money_formatter: MoneyFormatter = lambda value: f"{value:,.0f}",
) -> StressReport:
    """Run deterministic personal finance stress scenarios.

    The model is intentionally explainable rather than predictive. It estimates
    the cash impact of common shocks and compares it with a conservative liquid
    buffer estimate.
    """
    monthly_income = float((budget or {}).get("income", 0) or 0)
    monthly_surplus = float((budget or {}).get("amt_save", 0) or 0)
    monthly_expense = max(0.0, monthly_income - monthly_surplus)

    if monthly_income <= 0 and not networth:
        return StressReport((), monthly_income, monthly_expense, monthly_surplus, 0.0)

    liquid_buffer = _liquid_buffer(networth, monthly_surplus)
    scenarios: list[StressScenario] = []

    if monthly_income > 0:
        impact = monthly_income * 0.35 * 3
        scenarios.append(
            _make_scenario(
                key="income_drop",
                title="收入下降 35% 持续 3 个月",
                severity="中等",
                impact=impact,
                liquid_buffer=liquid_buffer,
                monthly_expense=max(monthly_expense, monthly_income * 0.6),
                page_key="budget",
                narrative=f"若收入短期下降 35%，三个月现金流冲击约 {_money(impact, money_formatter)}。",
                actions=(
                    "先锁定必需支出清单，区分可暂停与不可暂停项目。",
                    "将储蓄率目标拆成安全垫优先，而非立即追求高收益。",
                    "为主要收入来源设置 1 个备选收入或技能升级计划。",
                ),
            )
        )

        expense_base = max(monthly_expense, monthly_income * 0.5)
        impact = expense_base * 1.8
        scenarios.append(
            _make_scenario(
                key="expense_spike",
                title="突发支出等于 1.8 个月开销",
                severity="温和",
                impact=impact,
                liquid_buffer=liquid_buffer,
                monthly_expense=expense_base,
                page_key="networth",
                narrative=f"医疗、维修或家庭突发事项可能一次性消耗约 {_money(impact, money_formatter)}。",
                actions=(
                    "把应急金目标设为至少 3-6 个月必要支出。",
                    "将应急金与投资账户分离，避免临时卖出高波动资产。",
                    "检查保险免赔额、等待期和家庭保障缺口。",
                ),
            )
        )

    if loan:
        monthly_payment = float(loan.get("monthly_payment", 0) or 0)
        if monthly_payment > 0:
            impact = monthly_payment * 0.15 * 12
            scenarios.append(
                _make_scenario(
                    key="loan_payment_shock",
                    title="贷款月供上升 15% 持续 1 年",
                    severity="中等",
                    impact=impact,
                    liquid_buffer=liquid_buffer,
                    monthly_expense=max(monthly_expense, monthly_payment),
                    page_key="loan",
                    narrative=f"利率或还款压力变化会带来约 {_money(impact, money_formatter)} 的年度额外现金流占用。",
                    actions=(
                        "在贷款计算器中比较提前还款、缩短期限和保留现金的取舍。",
                        "确保月供收入比仍处于可承受区间。",
                        "若现金垫不足，优先提高流动性而不是激进提前还款。",
                    ),
                )
            )

    if networth:
        net_worth = max(0.0, float(networth.get("net_worth", 0) or 0))
        if net_worth > 0:
            impact = net_worth * 0.15
            retirement_gap = float((retirement or {}).get("gap", 0) or 0)
            scenarios.append(
                _make_scenario(
                    key="asset_drawdown",
                    title="可投资资产回撤 15%",
                    severity="严重",
                    impact=impact,
                    liquid_buffer=liquid_buffer,
                    monthly_expense=max(monthly_expense, monthly_surplus, 1.0),
                    page_key="portfolio" if retirement_gap <= 0 else "retirement",
                    narrative=f"若资产组合回撤 15%，净资产账面冲击约 {_money(impact, money_formatter)}，可能放大退休或长期目标压力。",
                    actions=(
                        "检查权益、债券、现金和保险保障之间的角色分工。",
                        "用组合优化器或蒙特卡洛模拟观察回撤对目标成功率的影响。",
                        "避免在压力场景中被迫卖出，先配置现金桶与防守资产。",
                    ),
                )
            )

    ranked = sorted(scenarios, key=lambda item: (item.resilience_score, -item.liquidity_gap, item.title))
    return StressReport(tuple(ranked), monthly_income, monthly_expense, monthly_surplus, liquid_buffer)
