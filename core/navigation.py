"""Central navigation registry for OmniFinance.

Keeping page metadata in one place avoids duplicated lists in the app shell,
sidebar search, and dashboard quick-start UI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PageInfo:
    """Metadata for one Streamlit page."""

    key: str
    title: str
    icon: str
    path: str
    category: str
    description: str
    aliases: tuple[str, ...] = ()
    default: bool = False

    @property
    def label(self) -> str:
        return f"{self.icon} {self.title}"


@dataclass(frozen=True)
class DashboardProgressItem:
    """Data contract for pages that can complete dashboard/decision readiness."""

    label: str
    session_key: str
    page_key: str
    ready_hint: str = "已完成，可参与综合诊断"
    pending_hint: str = "待补充，建议优先填写"


SEARCH_SYNONYMS: dict[str, tuple[str, ...]] = {
    "养老金": ("退休", "退休金", "养老", "养老金规划"),
    "退休": ("养老金", "养老", "退休金", "养老金规划"),
    "退休金": ("退休", "养老", "养老金"),
    "个税": ("税务", "税", "薪资税", "专项附加扣除"),
    "税": ("税务", "个税", "税收", "退税"),
    "贷款": ("房贷", "车贷", "分期", "按揭"),
    "储蓄": ("存钱", "存款", "目标存款"),
    "预算": ("现金流", "开销", "收支", "月度预算"),
    "净值": ("净资产", "总资产", "资产负债"),
    "资产": ("净值", "财富", "总资产"),
    "保险": ("保单", "保障", "保险费"),
    "理财": ("投资", "财务"),
    "记账": ("收支", "账本", "账务"),
    "模拟": ("蒙卡", "蒙特卡洛", "回测"),
}

NAVIGATION_POPULARITY: dict[str, int] = {
    "decision": 90,
    "home": 85,
    "budget": 80,
    "networth": 78,
    "retirement": 75,
    "savings": 70,
    "loan": 68,
    "insurance": 66,
    "tax": 64,
    "portfolio": 62,
    "scenario": 56,
    "reminders": 52,
    "compound": 50,
}


NAVIGATION_CATEGORIES: tuple[str, ...] = (
    "平台概览",
    "基础理财管理",
    "资产与债务管理",
    "投资分析引擎",
    "高级人生规划",
    "分析与工具",
    "高级工具 (v2.0)",
)

PAGES: tuple[PageInfo, ...] = (
    PageInfo("decision", "决策中枢", "🧭", "pages/0_决策中枢.py", "平台概览", "按财务画像、健康诊断、机会识别和行动计划组织使用路径", ("决策", "中枢", "workflow", "decision"), True),
    PageInfo("home", "仪表盘首页", "🏠", "home.py", "平台概览", "全局汇总、健康评分、报告导出与提醒管理", ("首页", "dashboard", "home")),
    PageInfo("compound", "复利计算器", "💰", "pages/1_复利计算器.py", "基础理财管理", "测算长期复利、通胀影响与收益敏感性", ("复利", "compound")),
    PageInfo("savings", "储蓄目标计算器", "🎯", "pages/5_储蓄目标计算器.py", "基础理财管理", "反推目标金额所需时间、月存额与复利贡献", ("目标", "储蓄", "saving")),
    PageInfo("budget", "预算分配建议器", "💡", "pages/6_预算分配建议器.py", "基础理财管理", "基于收入支出生成预算结构与储蓄率建议", ("预算", "50/30/20", "budget")),
    PageInfo("education", "教育基金规划器", "🏫", "pages/14_教育基金规划器.py", "基础理财管理", "规划教育费用、通胀和资金缺口", ("教育", "education")),
    PageInfo("networth", "资产净值追踪器", "🏠", "pages/9_资产净值追踪器.py", "资产与债务管理", "记录资产负债并追踪净资产趋势", ("净资产", "资产", "负债", "net worth")),
    PageInfo("loan", "贷款计算器", "🏦", "pages/4_贷款计算器.py", "资产与债务管理", "比较贷款方案、总利息和提前还款效果", ("贷款", "房贷", "loan")),
    PageInfo("insurance", "保险产品测算器", "🛡️", "pages/8_保险产品测算器.py", "资产与债务管理", "分析保费效率、现金价值与保单 IRR", ("保险", "保单", "insurance")),
    PageInfo("debt", "债务还清规划器", "💳", "pages/13_债务还清规划器.py", "资产与债务管理", "制定雪球法/雪崩法债务偿还计划", ("债务", "还债", "debt")),
    PageInfo("realestate", "房产投资分析器", "🏘️", "pages/15_房产投资分析器.py", "资产与债务管理", "评估租金收益、现金流和房产投资回报", ("房产", "房地产", "real estate")),
    PageInfo("quote", "实时报价面板", "📊", "pages/2_实时报价面板.py", "投资分析引擎", "查看股票/ETF 价格、走势与关键指标", ("行情", "股票", "quote")),
    PageInfo("portfolio", "投资组合优化器", "📐", "pages/11_投资组合优化器.py", "投资分析引擎", "优化资产权重、风险收益与有效前沿", ("组合", "投资组合", "portfolio")),
    PageInfo("backtest", "策略回测器", "📈", "pages/3_MA交叉回测器.py", "投资分析引擎", "回测均线策略并考虑费用、滑点与基准", ("回测", "策略", "MA", "backtest")),
    PageInfo("rebalance", "资产再平衡模拟器", "⚖️", "pages/17_资产再平衡模拟器.py", "投资分析引擎", "模拟定期再平衡、偏离阈值与交易影响", ("再平衡", "rebalance")),
    PageInfo("fx", "外汇对冲计算器", "💱", "pages/16_外汇对冲计算器.py", "投资分析引擎", "评估汇率风险、对冲成本与敞口管理", ("外汇", "汇率", "对冲", "fx")),
    PageInfo("retirement", "退休金估算器", "🏖️", "pages/7_退休金估算器.py", "高级人生规划", "估算退休缺口、月存需求与敏感度", ("退休", "养老", "retirement")),
    PageInfo("montecarlo", "蒙特卡洛模拟", "🎲", "pages/10_蒙特卡洛模拟.py", "高级人生规划", "用随机模拟评估目标达成概率与风险分布", ("蒙卡", "模拟", "monte carlo")),
    PageInfo("withdrawal", "税务优化提款策略", "🏦", "pages/20_税务优化提款策略.py", "高级人生规划", "比较退休提款顺序、税务影响与资金寿命", ("提款", "税务提款", "withdrawal")),
    PageInfo("historical", "历史回测储蓄模拟", "📜", "pages/19_历史回测储蓄模拟.py", "高级人生规划", "用历史市场数据验证储蓄和投资路径", ("历史", "储蓄回测", "historical")),
    PageInfo("diary", "财务日记", "📔", "pages/25_财务日记.py", "高级人生规划", "记录财务决策、复盘和情绪标签", ("日记", "记录", "diary")),
    PageInfo("tax", "税务计算器", "🧾", "pages/12_税务计算器.py", "分析与工具", "估算个税、专项扣除和税后收入", ("个税", "税", "tax")),
    PageInfo("scenario", "场景对比分析器", "🔬", "pages/18_场景对比分析器.py", "分析与工具", "并排对比不同收入、收益率和目标假设", ("场景", "对比", "scenario")),
    PageInfo("calendar", "财务日历", "📅", "pages/21_财务日历.py", "分析与工具", "集中管理账单、还款、保费和投资日期", ("日历", "calendar")),
    PageInfo("reminders", "财务提醒管理", "🔔", "pages/22_财务提醒管理.py", "分析与工具", "创建提醒并跟踪待办财务事项", ("提醒", "待办", "reminder")),
    PageInfo("currency", "货币转换器", "💱", "pages/23_货币转换器.py", "分析与工具", "查询汇率并进行多币种换算", ("货币", "汇率", "currency")),
    PageInfo("calculator", "科学金融计算器", "🧮", "pages/24_科学金融计算器.py", "分析与工具", "提供常用科学计算与金融公式快捷计算", ("计算器", "科学", "calculator")),
    PageInfo("screener", "股票筛选器", "🔎", "pages/26_股票筛选器.py", "高级工具 (v2.0)", "按市场、指标和自定义条件筛选标的", ("筛选", "选股", "screener")),
    PageInfo("ledger", "收支记账本", "📒", "pages/27_收支记账本.py", "高级工具 (v2.0)", "记录收入支出并联动预算分析", ("记账", "收支", "ledger")),
)

DASHBOARD_PROGRESS_ITEMS: tuple[DashboardProgressItem, ...] = (
    DashboardProgressItem("预算", "dashboard_budget", "budget"),
    DashboardProgressItem("净资产", "dashboard_networth", "networth"),
    DashboardProgressItem("退休", "dashboard_retirement", "retirement"),
    DashboardProgressItem("贷款", "dashboard_loan", "loan"),
    DashboardProgressItem("保险", "dashboard_insurance", "insurance"),
    DashboardProgressItem("储蓄", "dashboard_savings", "savings"),
    DashboardProgressItem("税务", "dashboard_tax", "tax"),
)


def pages_by_category() -> dict[str, list[PageInfo]]:
    """Return pages grouped by navigation category in display order."""
    grouped = {category: [] for category in NAVIGATION_CATEGORIES}
    for page in PAGES:
        grouped.setdefault(page.category, []).append(page)
    return {category: pages for category, pages in grouped.items() if pages}


def _normalize_text(value: str) -> str:
    """Normalize query-like text for matching."""
    return re.sub(r"\s+", "", value.strip().lower())


def _normalize_query(query: str) -> tuple[str, ...]:
    """Return normalized search candidates."""
    normalized = _normalize_text(query)
    if not normalized:
        return ()

    candidates = {normalized}
    for synonym, mapped in SEARCH_SYNONYMS.items():
        normalized_synonym = synonym.lower()
        if normalized_synonym == normalized:
            candidates.update(mapped)
        elif normalized_synonym in normalized or normalized in normalized_synonym:
            candidates.add(normalized_synonym)
            candidates.update(mapped)

    return tuple(dict.fromkeys(candidates))


def _score_page(page: PageInfo, terms: tuple[str, ...]) -> int | None:
    """Compute search rank for a page, where smaller score is better."""
    haystacks = tuple(_normalize_text(field) for field in (page.title, page.category, page.key, page.path, *page.aliases))
    title_normalized = _normalize_text(page.title)
    key_normalized = _normalize_text(page.key)

    if not haystacks:
        return None

    best: int | None = None
    for term in terms:
        if not term:
            continue
        if term in haystacks:
            best = 0
            break
        if title_normalized.startswith(term) or key_normalized.startswith(term):
            best = min(best, 1) if best is not None else 1
        elif any(term in field for field in haystacks):
            best = min(best, 2) if best is not None else 2

    return best


def search_pages(query: str, *, limit: int = 8, recent_keys: tuple[str, ...] | None = None) -> list[PageInfo]:
    """Search pages by title, category, key, path or aliases."""
    terms = _normalize_query(query)
    if not terms:
        return []

    recent_rank = {key: idx for idx, key in enumerate(recent_keys or ())}
    scored: list[tuple[int, int, int, int, PageInfo]] = []
    for position, page in enumerate(PAGES):
        score = _score_page(page, terms)
        if score is None:
            continue
        scored.append((score, recent_rank.get(page.key, len(recent_rank) + 1), -NAVIGATION_POPULARITY.get(page.key, 0), position, page))

    return [page for _, _, _, _, page in sorted(scored, key=lambda item: item[:4])[:limit]]


def get_page(key: str) -> PageInfo:
    """Fetch a page by key."""
    for page in PAGES:
        if page.key == key:
            return page
    raise KeyError(key)
