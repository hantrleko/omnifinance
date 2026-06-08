"""Financial health scoring and next-action recommendations.

This module keeps dashboard scoring rules independent from Streamlit so the
business logic can be tested and evolved without touching the UI layer.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

MoneyFormatter = Callable[[float], str]


@dataclass(frozen=True)
class HealthDimension:
    """One scored financial health dimension."""

    name: str
    score: int
    tip: str
    grade: str
    action_key: str


@dataclass(frozen=True)
class HealthReport:
    """Aggregated financial health result."""

    dimensions: tuple[HealthDimension, ...]
    overall_score: int | None
    overall_grade: str

    @property
    def improvement_tips(self) -> tuple[str, ...]:
        return tuple(dimension.tip for dimension in self.dimensions if dimension.score < 70)


@dataclass(frozen=True)
class ActionRecommendation:
    """A dashboard next action that links a weak dimension to a tool."""

    page_key: str
    title: str
    reason: str
    priority: str


def _money(value: float, formatter: MoneyFormatter) -> str:
    return formatter(float(value))


def _overall_grade(score: int | None) -> str:
    if score is None:
        return ""
    if score >= 80:
        return "🟢 优秀"
    if score >= 60:
        return "🟡 良好"
    if score >= 40:
        return "🟠 一般"
    return "🔴 需改善"


def build_health_report(
    *,
    budget: Mapping[str, Any] | None = None,
    retirement: Mapping[str, Any] | None = None,
    networth: Mapping[str, Any] | None = None,
    tax: Mapping[str, Any] | None = None,
    insurance: Mapping[str, Any] | None = None,
    money_formatter: MoneyFormatter = lambda value: f"{value:,.0f}",
) -> HealthReport:
    """Build a multi-dimensional financial health report from dashboard metrics."""
    dimensions: list[HealthDimension] = []

    if budget:
        save_pct = float(budget.get("pct_save", 0) or 0)
        if save_pct >= 30:
            score, tip, grade = 100, f"储蓄率 {save_pct:g}%，远超全国均值，表现卓越", "🟢"
        elif save_pct >= 20:
            score, tip, grade = 75, f"储蓄率 {save_pct:g}%，处于健康水平", "🟡"
        elif save_pct >= 10:
            score, tip, grade = 50, f"储蓄率 {save_pct:g}%，建议提升至 20% 以上", "🟠"
        else:
            score, tip, grade = 20, f"储蓄率 {save_pct:g}%，偏低，需要大幅改善", "🔴"
        dimensions.append(HealthDimension("💡 储蓄能力", score, tip, grade, "budget"))

    if retirement:
        gap = float(retirement.get("gap", 0) or 0)
        extra = float(retirement.get("extra_monthly", 0) or 0)
        if gap <= 0:
            score, tip, grade = 100, "退休资金已充足，无需额外储蓄", "🟢"
        elif extra < 2000:
            score, tip, grade = 70, f"退休缺口可控，每月仅需额外补充 {_money(extra, money_formatter)}", "🟡"
        elif extra < 5000:
            score, tip, grade = 45, f"退休缺口较大，需每月额外储蓄 {_money(extra, money_formatter)}", "🟠"
        else:
            score, tip, grade = 20, f"退休缺口严峻，需每月额外储蓄 {_money(extra, money_formatter)}，请尽早行动", "🔴"
        dimensions.append(HealthDimension("🏖️ 退休准备度", score, tip, grade, "retirement"))

    if networth:
        total_assets = float(networth.get("total_assets", 0) or 0)
        net_worth = float(networth.get("net_worth", 0) or 0)
        total_liabilities = total_assets - net_worth
        debt_ratio = (total_liabilities / total_assets * 100) if total_assets > 0 else 0
        if debt_ratio <= 20:
            score, tip, grade = 100, f"负债率 {debt_ratio:.1f}%，资产结构健康", "🟢"
        elif debt_ratio <= 40:
            score, tip, grade = 75, f"负债率 {debt_ratio:.1f}%，处于合理区间", "🟡"
        elif debt_ratio <= 60:
            score, tip, grade = 45, f"负债率 {debt_ratio:.1f}%，偏高，建议加速还款", "🟠"
        else:
            score, tip, grade = 15, f"负债率 {debt_ratio:.1f}%，过高，存在较大财务风险", "🔴"
        dimensions.append(HealthDimension("💳 负债水平", score, tip, grade, "debt"))

        if net_worth > 1_000_000:
            score, tip, grade = 100, f"净资产 {_money(net_worth, money_formatter)}，资产积累丰厚", "🟢"
        elif net_worth > 200_000:
            score, tip, grade = 70, f"净资产 {_money(net_worth, money_formatter)}，处于正常成长阶段", "🟡"
        elif net_worth > 0:
            score, tip, grade = 50, f"净资产 {_money(net_worth, money_formatter)}，尚在起步阶段，持续积累", "🟠"
        else:
            score, tip, grade = 10, f"净资产为负（{_money(net_worth, money_formatter)}），需优先降低负债", "🔴"
        dimensions.append(HealthDimension("🏠 净资产水平", score, tip, grade, "networth"))

    if tax:
        effective_rate = float(tax.get("effective_rate", 0) or 0)
        if effective_rate <= 5:
            score, tip, grade = 100, f"实际税率 {effective_rate:.1f}%，税务负担轻", "🟢"
        elif effective_rate <= 15:
            score, tip, grade = 75, f"实际税率 {effective_rate:.1f}%，属正常水平", "🟡"
        elif effective_rate <= 25:
            score, tip, grade = 50, f"实际税率 {effective_rate:.1f}%，可考虑税务优化策略", "🟠"
        else:
            score, tip, grade = 30, f"实际税率 {effective_rate:.1f}%，建议使用税务优化工具", "🔴"
        dimensions.append(HealthDimension("🧾 税务效率", score, tip, grade, "tax"))

    if insurance:
        irr = float(insurance.get("irr_pct", 0) or 0)
        if irr >= 4:
            score, tip, grade = 100, f"保险 IRR {irr:.2f}%，保单回报优质", "🟢"
        elif irr >= 2.5:
            score, tip, grade = 65, f"保险 IRR {irr:.2f}%，收益一般，关注保障覆盖", "🟡"
        else:
            score, tip, grade = 35, f"保险 IRR 仅 {irr:.2f}%，建议评估保单性价比", "🟠"
        dimensions.append(HealthDimension("🛡️ 保险效益", score, tip, grade, "insurance"))

    overall_score = int(sum(dimension.score for dimension in dimensions) / len(dimensions)) if dimensions else None
    return HealthReport(tuple(dimensions), overall_score, _overall_grade(overall_score))


def build_action_recommendations(report: HealthReport, *, limit: int = 3) -> tuple[ActionRecommendation, ...]:
    """Turn weak dimensions into concise next-step recommendations."""
    action_copy = {
        "budget": ("优化预算结构", "储蓄能力偏弱，先检查收入分配和可压缩支出。"),
        "retirement": ("补齐退休缺口", "退休准备度仍有缺口，建议重新测算目标和月存方案。"),
        "debt": ("制定还债路径", "负债水平偏高，优先比较雪球法与雪崩法。"),
        "networth": ("完善资产负债表", "净资产仍在起步区间，建议持续追踪资产与负债变化。"),
        "tax": ("检查税务优化项", "实际税率偏高，可复核专项扣除和优化策略。"),
        "insurance": ("复核保单性价比", "保险收益或保障效率一般，建议重新评估保障覆盖。"),
    }

    weak_dimensions = sorted((dimension for dimension in report.dimensions if dimension.score < 70), key=lambda item: item.score)
    recommendations: list[ActionRecommendation] = []
    for dimension in weak_dimensions[:limit]:
        title, reason = action_copy.get(dimension.action_key, ("继续完善数据", dimension.tip))
        priority = "高" if dimension.score < 40 else "中"
        recommendations.append(ActionRecommendation(dimension.action_key, title, reason, priority))

    if not recommendations and report.overall_score is not None:
        recommendations.append(ActionRecommendation("portfolio", "探索组合优化", "健康评分较好，可以进一步优化资产配置效率。", "低"))

    return tuple(recommendations)
