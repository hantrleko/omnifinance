"""Executive decision brief generation for the dashboard.

The brief converts diagnostics (health score), opportunity radar, and stress
scenarios into a short, exportable decision memo. It is deterministic and does
not call an LLM, so it remains fast, private, and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

DecisionMode = Literal["防守", "修复", "增长", "观察"]


@dataclass(frozen=True)
class DecisionBrief:
    """A concise dashboard decision memo."""

    generated_on: str
    readiness_score: int | None
    mode: DecisionMode
    headline: str
    summary: str
    key_findings: tuple[str, ...]
    priority_actions: tuple[str, ...]
    watchlist: tuple[str, ...]

    def to_markdown(self) -> str:
        """Render the brief as portable Markdown for download or sharing."""
        score_text = "暂无" if self.readiness_score is None else f"{self.readiness_score}/100"
        sections = [
            "# OmniFinance 决策简报",
            "",
            f"- 生成日期：{self.generated_on}",
            f"- 决策模式：{self.mode}",
            f"- 准备度评分：{score_text}",
            "",
            f"## {self.headline}",
            "",
            self.summary,
            "",
            "## 关键发现",
            *(f"- {item}" for item in self.key_findings),
            "",
            "## 优先行动",
            *(f"- {item}" for item in self.priority_actions),
            "",
            "## 观察清单",
            *(f"- {item}" for item in self.watchlist),
            "",
            "> 本简报由本地规则生成，仅用于学习与个人规划参考，不构成投资、税务或保险建议。",
        ]
        return "\n".join(sections)


def _clamp_score(value: float) -> int:
    return max(1, min(100, int(round(value))))


def _readiness_score(health_report: Any | None, opportunity_report: Any | None, stress_report: Any | None) -> int | None:
    components: list[tuple[float, float]] = []

    health_score = getattr(health_report, "overall_score", None)
    if health_score is not None:
        components.append((float(health_score), 0.45))

    if opportunity_report is not None and getattr(opportunity_report, "opportunities", None):
        top_opportunity = opportunity_report.top_opportunity
        opportunity_score = 100 - float(top_opportunity.impact_score if top_opportunity else 0)
        components.append((opportunity_score, 0.25))
    elif opportunity_report is not None:
        components.append((88.0, 0.25))

    if stress_report is not None and getattr(stress_report, "scenarios", None):
        weakest = stress_report.weakest_scenario
        stress_score = float(weakest.resilience_score if weakest else 70)
        components.append((stress_score, 0.30))
    elif stress_report is not None:
        components.append((55.0, 0.30))

    if not components:
        return None

    weighted_score = sum(score * weight for score, weight in components) / sum(weight for _, weight in components)
    return _clamp_score(weighted_score)


def _decision_mode(score: int | None, opportunity_report: Any | None, stress_report: Any | None) -> DecisionMode:
    critical_count = getattr(stress_report, "critical_count", 0) if stress_report is not None else 0
    high_priority_count = getattr(opportunity_report, "high_priority_count", 0) if opportunity_report is not None else 0

    if critical_count:
        return "防守"
    if high_priority_count or (score is not None and score < 60):
        return "修复"
    if score is not None and score >= 75:
        return "增长"
    return "观察"


def _headline(mode: DecisionMode, score: int | None) -> str:
    if mode == "防守":
        return "先稳住现金流防线，再推进增长目标"
    if mode == "修复":
        return "优先修复最短板，释放下一阶段增长空间"
    if mode == "增长":
        return "基础盘较稳，可以把重点转向资产配置效率"
    if score is None:
        return "继续补充数据，生成更完整的决策视图"
    return "保持观察，按月复盘关键指标"


def build_decision_brief(
    *,
    health_report: Any | None = None,
    opportunity_report: Any | None = None,
    stress_report: Any | None = None,
    generated_on: date | None = None,
) -> DecisionBrief:
    """Build an executive brief from dashboard analytics objects."""
    score = _readiness_score(health_report, opportunity_report, stress_report)
    mode = _decision_mode(score, opportunity_report, stress_report)
    headline = _headline(mode, score)

    key_findings: list[str] = []
    priority_actions: list[str] = []
    watchlist: list[str] = []

    if health_report is not None and getattr(health_report, "overall_score", None) is not None:
        key_findings.append(f"综合财务健康评分为 {health_report.overall_score}/100（{health_report.overall_grade}）。")
        key_findings.extend(str(tip) for tip in getattr(health_report, "improvement_tips", ())[:2])
    else:
        watchlist.append("继续使用预算、净资产、退休等核心工具，以补齐健康评分数据。")

    if opportunity_report is not None and getattr(opportunity_report, "opportunities", None):
        top = opportunity_report.top_opportunity
        key_findings.append(f"机会雷达首要关注：{top.title}（影响力 {top.impact_score}/100）。")
        priority_actions.extend(top.actions[:2])
        for opportunity in opportunity_report.opportunities[1:3]:
            watchlist.append(f"观察机会：{opportunity.title}。")
    elif opportunity_report is not None:
        key_findings.append("机会雷达暂未发现明显短板，可继续探索组合优化或长期增长策略。")

    if stress_report is not None and getattr(stress_report, "scenarios", None):
        weakest = stress_report.weakest_scenario
        key_findings.append(f"压力测试最弱场景：{weakest.title}，冲击后安全垫约 {weakest.buffer_months_after:.1f} 个月。")
        if weakest.status == "critical":
            priority_actions.extend(weakest.actions[:2])
        else:
            watchlist.append(f"压力测试关注：{weakest.title}。")
    elif stress_report is not None:
        watchlist.append("补充预算或资产净值数据后，可生成压力测试场景。")

    if not priority_actions:
        priority_actions.append("本月完成一次数据复盘，确认收入、支出、净资产和退休假设是否仍然有效。")
    if not watchlist:
        watchlist.append("每月复核一次储蓄率、负债率、退休缺口和应急金月数。")

    score_text = "暂无完整评分" if score is None else f"准备度 {score}/100"
    summary = f"当前建议采用「{mode}」模式：{headline}（{score_text}）。"

    return DecisionBrief(
        generated_on=(generated_on or date.today()).isoformat(),
        readiness_score=score,
        mode=mode,
        headline=headline,
        summary=summary,
        key_findings=tuple(key_findings[:5]),
        priority_actions=tuple(dict.fromkeys(priority_actions[:5])),
        watchlist=tuple(dict.fromkeys(watchlist[:5])),
    )
