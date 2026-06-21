"""core/glossary.py — 金融概念小白科普模块

为每个工具页面提供上下文相关的金融术语解释，帮助初学者快速理解页面中出现的专业概念。

Usage
-----
    from core.glossary import render_glossary_sidebar

    # 在页面侧边栏中调用，传入该页面相关的术语 key 列表
    render_glossary_sidebar(["compound_interest", "annual_rate", "pv"])

Available term keys are defined in GLOSSARY dict below.
"""
from __future__ import annotations

import streamlit as st

# ── 术语库 ─────────────────────────────────────────────────────────────────────
# 每个条目：title（术语名）、emoji、body（通俗解释）、formula（可选公式）、example（可选例子）

GLOSSARY: dict[str, dict] = {

    # ── 基础概念 ──────────────────────────────────────────────────────────────
    "compound_interest": {
        "title": "复利（Compound Interest）",
        "emoji": "📈",
        "body": "复利是'利滚利'：每期利息会被加入本金，下一期再一起产生利息。时间越长，复利效果越惊人，爱因斯坦称之为'世界第八大奇迹'。",
        "formula": "终值 = 本金 × (1 + 年利率/n)^(n×年数)",
        "example": "1 万元，年利率 6%，20 年后复利终值 ≈ 3.2 万元；单利仅 2.2 万元。",
    },
    "simple_interest": {
        "title": "单利（Simple Interest）",
        "emoji": "📊",
        "body": "单利只对本金计息，利息不再产生利息。银行活期存款通常按单利计算。",
        "formula": "利息 = 本金 × 年利率 × 年数",
        "example": "1 万元，年利率 3%，存 5 年，利息 = 1万 × 3% × 5 = 1500 元。",
    },
    "annual_rate": {
        "title": "年化利率（Annual Rate）",
        "emoji": "📅",
        "body": "把任意周期的利率换算成'每年'的统一表示方式，方便不同产品横向比较。注意区分名义利率（标注值）和实际利率（考虑通胀后的真实购买力）。",
        "formula": "月利率 → 年利率：(1 + 月利率)^12 - 1",
        "example": "月利率 0.5% 的信用卡，年化实际利率 ≈ 6.17%，而非简单 × 12 = 6%。",
    },
    "pv": {
        "title": "现值（Present Value, PV）",
        "emoji": "⏮️",
        "body": "未来一笔钱在今天值多少？由于通胀和投资机会，今天的钱比未来的钱更值钱，这就是'货币的时间价值'。",
        "formula": "PV = FV / (1 + r)^n",
        "example": "5 年后的 10 万元，按年利率 5% 折现，今天的现值 ≈ 7.84 万元。",
    },
    "fv": {
        "title": "终值（Future Value, FV）",
        "emoji": "⏭️",
        "body": "今天的一笔钱，按一定利率投资，未来会变成多少？终值是现值的反向计算。",
        "formula": "FV = PV × (1 + r)^n",
        "example": "今天投入 5 万元，年化 7%，10 年后终值 ≈ 9.84 万元。",
    },
    "inflation": {
        "title": "通货膨胀（Inflation）",
        "emoji": "🎈",
        "body": "物价整体持续上涨，导致同样的钱能买到的东西越来越少。通胀率是衡量货币购买力下降速度的指标。",
        "formula": "实际利率 ≈ 名义利率 − 通胀率（费雪方程式）",
        "example": "年通胀 3%，10 年后 1 万元的购买力仅相当于今天的 7,441 元。",
    },
    "real_rate": {
        "title": "实际利率（Real Interest Rate）",
        "emoji": "🔍",
        "body": "扣除通胀后的真实回报率。如果名义利率低于通胀率，实际利率为负，意味着存钱反而在'缩水'。",
        "formula": "实际利率 ≈ 名义利率 − 通胀率",
        "example": "定期存款年利率 2%，通胀 3%，实际利率 = −1%（购买力在下降）。",
    },

    # ── 贷款相关 ──────────────────────────────────────────────────────────────
    "amortization": {
        "title": "等额还款摊销（Amortization）",
        "emoji": "🏦",
        "body": "将贷款本金和利息分摊到每期，使每期还款金额相同。前期还的利息多、本金少；后期本金占比逐渐增大。",
        "formula": "月还款额 = P × r(1+r)^n / [(1+r)^n - 1]",
        "example": "贷款 100 万，年利率 4.5%，30 年等额还款，月供约 5,067 元，总利息约 82 万。",
    },
    "ltv": {
        "title": "贷款价值比（LTV）",
        "emoji": "🏠",
        "body": "贷款金额占房产评估价值的百分比。LTV 越高，银行风险越大，通常要求更高利率或拒绝贷款。首付比例 = 1 − LTV。",
        "formula": "LTV = 贷款金额 / 房产价值 × 100%",
        "example": "房价 200 万，首付 40 万，贷款 160 万，LTV = 80%。",
    },
    "apr": {
        "title": "年化百分比利率（APR）",
        "emoji": "💳",
        "body": "贷款的真实年化成本，包含利息和各种手续费。APR 比名义利率更能反映借贷的实际成本，是比较贷款产品的关键指标。",
        "formula": "APR 包含：利率 + 手续费 + 其他费用（年化）",
        "example": "信用卡月利率 1.5%，APR = (1+1.5%)^12 - 1 ≈ 19.56%，远高于标注的 18%。",
    },

    # ── 投资相关 ──────────────────────────────────────────────────────────────
    "sharpe_ratio": {
        "title": "夏普比率（Sharpe Ratio）",
        "emoji": "⚖️",
        "body": "衡量每承担一单位风险所获得的超额回报。夏普比率越高，说明投资组合的风险调整后收益越好。大于 1 通常被认为不错，大于 2 则优秀。",
        "formula": "夏普比率 = (组合收益率 − 无风险利率) / 组合标准差",
        "example": "组合年化收益 12%，无风险利率 3%，年化波动率 15%，夏普 = (12%-3%)/15% = 0.6。",
    },
    "volatility": {
        "title": "波动率（Volatility）",
        "emoji": "〰️",
        "body": "衡量资产价格变动幅度的指标，通常用收益率的标准差表示。波动率越高，风险越大，但潜在收益也可能更高。",
        "formula": "年化波动率 = 日收益率标准差 × √252",
        "example": "某股票日收益率标准差 1.5%，年化波动率 ≈ 1.5% × √252 ≈ 23.8%。",
    },
    "diversification": {
        "title": "分散化（Diversification）",
        "emoji": "🎯",
        "body": "把资金分散投资于不同资产、行业、地区，降低单一资产暴跌对整体组合的冲击。'不要把所有鸡蛋放在一个篮子里'。",
        "formula": "组合方差 = Σ wᵢ²σᵢ² + Σ wᵢwⱼCov(i,j)（相关性越低，分散效果越好）",
        "example": "同时持有股票和债券，股市下跌时债券往往上涨，组合整体波动更小。",
    },
    "beta": {
        "title": "贝塔系数（Beta）",
        "emoji": "β",
        "body": "衡量个股相对于大盘的波动敏感度。β=1 表示与大盘同步；β>1 表示放大波动（进攻型）；β<1 表示波动更小（防御型）。",
        "formula": "β = Cov(股票收益, 市场收益) / Var(市场收益)",
        "example": "某科技股 β=1.5，大盘涨 10% 时该股通常涨 15%；大盘跌 10% 时该股通常跌 15%。",
    },
    "alpha": {
        "title": "阿尔法（Alpha）",
        "emoji": "α",
        "body": "投资组合相对于基准（如沪深300）的超额收益。正 Alpha 说明基金经理创造了价值；负 Alpha 说明跑输了基准。",
        "formula": "Alpha = 实际收益 − [无风险利率 + β × (市场收益 − 无风险利率)]",
        "example": "基准涨 10%，组合涨 13%，β=1.1，Alpha = 13% − 10% × 1.1 = 2%（跑赢基准）。",
    },
    "pe_ratio": {
        "title": "市盈率（P/E Ratio）",
        "emoji": "📊",
        "body": "股价相对于每股盈利的倍数，反映市场愿意为每 1 元利润付出多少钱。PE 越低可能越便宜，但也可能说明公司增长慢或有风险。",
        "formula": "PE = 股价 / 每股收益（EPS）",
        "example": "股价 50 元，EPS 5 元，PE = 10 倍（市场愿意为每 1 元利润付 10 元）。",
    },
    "pb_ratio": {
        "title": "市净率（P/B Ratio）",
        "emoji": "📚",
        "body": "股价相对于每股净资产的倍数。PB < 1 理论上意味着股价低于公司清算价值，常用于银行、地产等重资产行业估值。",
        "formula": "PB = 股价 / 每股净资产（BPS）",
        "example": "股价 8 元，每股净资产 10 元，PB = 0.8（低于账面价值）。",
    },
    "dividend_yield": {
        "title": "股息率（Dividend Yield）",
        "emoji": "💰",
        "body": "每股股息占股价的百分比，衡量持股的现金回报。高股息率股票适合追求稳定现金流的投资者，但也要警惕是否可持续。",
        "formula": "股息率 = 每股年度股息 / 当前股价 × 100%",
        "example": "股价 20 元，年派息 1 元，股息率 = 5%。",
    },
    "roe": {
        "title": "净资产收益率（ROE）",
        "emoji": "🏆",
        "body": "衡量公司用股东资本创造利润的效率。ROE 越高，说明公司用同样的资本赚到更多钱，是巴菲特最看重的指标之一。",
        "formula": "ROE = 净利润 / 平均股东权益 × 100%",
        "example": "净利润 2 亿，股东权益 10 亿，ROE = 20%（每 1 元股东资本创造 0.2 元利润）。",
    },

    # ── 风险管理 ──────────────────────────────────────────────────────────────
    "var": {
        "title": "风险价值（VaR, Value at Risk）",
        "emoji": "⚠️",
                "body": "在给定置信水平下，某段时间内可能发生的最大损失。例如'95% VaR = 5 万'意味着有 95% 的概率损失不超过 5 万元。",
        "formula": "VaR = μ − z × σ（正态分布假设下）",
        "example": "组合日 VaR(95%) = 2%，意味着正常情况下每天最多亏 2%（5% 概率会超过）。",
    },
    "max_drawdown": {
        "title": "最大回撤（Max Drawdown）",
        "emoji": "📉",
        "body": "从历史最高点到随后最低点的最大跌幅，衡量策略在最坏情况下的亏损程度。是评估投资风险承受能力的重要指标。",
        "formula": "最大回撤 = (谷底价值 − 峰值价值) / 峰值价值 × 100%",
        "example": "组合从 100 万涨到 150 万，再跌到 90 万，最大回撤 = (90-150)/150 = −40%。",
    },
    "monte_carlo": {
        "title": "蒙特卡洛模拟（Monte Carlo Simulation）",
        "emoji": "🎲",
        "body": "通过大量随机模拟（通常上万次）来预测未来可能的结果分布。金融中用于退休规划、期权定价、风险评估等，因为未来充满不确定性。",
        "formula": "模拟路径：S(t+1) = S(t) × exp[(μ - σ²/2)Δt + σ√Δt × Z]，Z ~ N(0,1)",
        "example": "退休规划：模拟 10,000 条资产路径，85% 的路径在 30 年后仍有余额，成功率 85%。",
    },

    # ── 护城河 ────────────────────────────────────────────────────────────────
    "moat": {
        "title": "经济护城河（Economic Moat）",
        "emoji": "🏰",
        "body": "企业抵御竞争对手侵蚀利润的持久竞争优势，如品牌、专利、网络效应、成本优势、转换成本等。巴菲特用'护城河'比喻这种保护企业城堡的壕沟。",
        "formula": "无固定公式，通过 ROE、ROIC、毛利率、市场份额等指标综合评估",
        "example": "可口可乐的品牌护城河、微软 Office 的转换成本护城河、Visa 的网络效应护城河。",
    },
    "roic": {
        "title": "投入资本回报率（ROIC）",
        "emoji": "💎",
        "body": "衡量公司每投入 1 元资本能产生多少税后利润。ROIC > 加权平均资本成本（WACC）说明公司在创造价值，是判断护城河强弱的核心指标。",
        "formula": "ROIC = 税后净营业利润（NOPAT） / 投入资本",
        "example": "ROIC = 15%，WACC = 8%，超额回报 7%，说明公司有强护城河。",
    },
    "wacc": {
        "title": "加权平均资本成本（WACC）",
        "emoji": "⚖️",
        "body": "公司融资的综合成本，包括股权成本和债务成本的加权平均。WACC 是投资项目的'门槛收益率'，项目回报必须超过 WACC 才能创造价值。",
        "formula": "WACC = (E/V) × Re + (D/V) × Rd × (1 − T)",
        "example": "股权占 60%，股权成本 10%；债务占 40%，税后债务成本 4%；WACC = 6%+1.6% = 7.6%。",
    },

    # ── 退休规划 ──────────────────────────────────────────────────────────────
    "swr": {
        "title": "安全提款率（SWR, Safe Withdrawal Rate）",
        "emoji": "🏖️",
        "body": "退休后每年从资产中取出的比例，使资产在整个退休期间不耗尽的最大比率。著名的'4% 法则'来自 Trinity Study，适用于 30 年退休期。",
        "formula": "年提款额 = 退休资产 × SWR（通常 3%~4%）",
        "example": "退休资产 500 万，按 4% SWR，每年可取 20 万，资产理论上可支撑 30 年。",
    },
    "fire": {
        "title": "财务独立提前退休（FIRE）",
        "emoji": "🔥",
        "body": "Financial Independence, Retire Early。通过高储蓄率快速积累资产，达到'25 倍年支出'的目标后即可退休（对应 4% 提款率）。",
        "formula": "FIRE 目标 = 年支出 × 25",
        "example": "年支出 20 万，FIRE 目标 = 500 万。储蓄率越高，达到 FIRE 越快。",
    },
    "sequence_risk": {
        "title": "收益顺序风险（Sequence of Returns Risk）",
        "emoji": "🎲",
        "body": "退休初期遭遇市场大跌，会严重损害资产寿命，即使长期平均收益相同。退休早期的亏损比晚期亏损危害大得多。",
        "formula": "无固定公式，通过蒙特卡洛模拟评估不同收益顺序下的资产存活率",
        "example": "同样年均 7% 收益，退休前 5 年跌 30% vs 后 5 年跌 30%，前者资产提前耗尽概率高 2 倍以上。",
    },

    # ── 税务相关 ──────────────────────────────────────────────────────────────
    "marginal_tax": {
        "title": "边际税率（Marginal Tax Rate）",
        "emoji": "🧾",
        "body": "你最后一元收入所适用的税率。中国个税采用超额累进税率，不同收入段适用不同税率，边际税率是最高那档。",
        "formula": "边际税率 = 最高应税所得区间对应的税率",
        "example": "月应税所得 3 万元，前 3000 元税率 3%，3000-12000 元税率 10%，12000-25000 元税率 20%，边际税率 = 20%。",
    },
    "effective_tax": {
        "title": "实际税率（Effective Tax Rate）",
        "emoji": "📊",
        "body": "实际缴纳税款占总收入的比例，通常低于边际税率。是衡量真实税负的指标。",
        "formula": "实际税率 = 实际缴税额 / 应税总收入 × 100%",
        "example": "年收入 20 万，实际缴税 2 万，实际税率 = 10%，但边际税率可能是 20%。",
    },

    # ── 保险相关 ──────────────────────────────────────────────────────────────
    "irr": {
        "title": "内部收益率（IRR）",
        "emoji": "📈",
        "body": "使投资净现值（NPV）等于零的折现率，代表投资的实际年化回报率。评估保险、理财产品时，IRR 比宣传的'收益率'更真实。",
        "formula": "NPV = Σ CF_t / (1+IRR)^t = 0",
        "example": "某保险产品缴费 10 年，领取 30 年，IRR = 3.2%，低于银行理财，需综合考虑保障价值。",
    },
    "insurance_leverage": {
        "title": "保险杠杆（Insurance Leverage）",
        "emoji": "🛡️",
        "body": "保额与保费的比值，衡量保险的'以小博大'效果。纯保障型保险（如定期寿险）杠杆极高；储蓄型保险杠杆较低。",
        "formula": "保险杠杆 = 保额 / 年保费",
        "example": "30 岁男性，100 万定期寿险，年保费 1000 元，杠杆 = 1000 倍。",
    },

    # ── 净资产相关 ────────────────────────────────────────────────────────────
    "net_worth": {
        "title": "净资产（Net Worth）",
        "emoji": "🏠",
        "body": "总资产减去总负债的差值，是衡量个人财富积累的最核心指标。净资产增长是财务健康的根本目标。",
        "formula": "净资产 = 总资产 − 总负债",
        "example": "房产 300 万 + 股票 50 万 + 存款 20 万 − 房贷 180 万 − 信用卡 2 万 = 净资产 188 万。",
    },
    "asset_allocation": {
        "title": "资产配置（Asset Allocation）",
        "emoji": "🥧",
        "body": "将资金按比例分配到不同资产类别（股票、债券、现金、房产等），是决定长期投资回报的最重要因素，通常比选股更重要。",
        "formula": "无固定公式，常用规则：股票比例 ≈ 100 − 年龄（保守估算）",
        "example": "30 岁：70% 股票 + 20% 债券 + 10% 现金；60 岁：40% 股票 + 50% 债券 + 10% 现金。",
    },
    "rebalancing": {
        "title": "再平衡（Rebalancing）",
        "emoji": "⚖️",
        "body": "定期将偏离目标比例的资产组合调整回目标配置。例如股票大涨后占比超标，则卖出部分股票买入债券，'高卖低买'自动执行。",
        "formula": "偏离度 = |实际权重 − 目标权重| / 目标权重",
        "example": "目标 60% 股票，股市大涨后变成 75%，需卖出 15% 的股票换成债券。",
    },

    # ── 外汇相关 ──────────────────────────────────────────────────────────────
    "exchange_rate": {
        "title": "汇率（Exchange Rate）",
        "emoji": "💱",
        "body": "两种货币之间的兑换比率。直接标价法（如 USD/CNY = 7.2）表示 1 美元可兑换 7.2 人民币。汇率受利率差、通胀差、贸易差额等影响。",
        "formula": "购买力平价（PPP）：E = P_国内 / P_国外",
        "example": "USD/CNY = 7.2，意味着 1 美元 = 7.2 人民币；1 人民币 = 1/7.2 ≈ 0.139 美元。",
    },
    "carry_trade": {
        "title": "利差交易（Carry Trade）",
        "emoji": "🌊",
        "body": "借入低利率货币，投资高利率货币，赚取利率差。风险在于汇率波动可能抹去利差收益甚至造成亏损。",
        "formula": "套利收益 ≈ 高息货币利率 − 低息货币利率 − 汇率变动",
        "example": "借入日元（利率 0.1%），换成澳元（利率 4.35%），利差 4.25%，但需承担澳元贬值风险。",
    },
}

# ── 页面预设术语组 ─────────────────────────────────────────────────────────────
PAGE_GLOSSARY_KEYS: dict[str, list[str]] = {
    "compound":      ["compound_interest", "fv", "annual_rate", "inflation", "real_rate"],
    "loan":          ["amortization", "apr", "ltv", "pv"],
    "savings":       ["compound_interest", "fv", "inflation", "real_rate", "pv"],
    "budget":        ["net_worth", "asset_allocation"],
    "retirement":    ["swr", "fire", "sequence_risk", "monte_carlo", "inflation"],
    "networth":      ["net_worth", "asset_allocation", "rebalancing"],
    "tax":           ["marginal_tax", "effective_tax"],
    "insurance":     ["irr", "insurance_leverage", "pv"],
    "portfolio":     ["sharpe_ratio", "volatility", "diversification", "beta", "alpha", "asset_allocation"],
    "backtest":      ["sharpe_ratio", "max_drawdown", "volatility", "beta", "alpha"],
    "rebalance":     ["rebalancing", "asset_allocation", "volatility"],
    "screener":      ["pe_ratio", "pb_ratio", "dividend_yield", "roe", "beta"],
    "moat":          ["moat", "roe", "roic", "wacc", "pe_ratio"],
    "montecarlo":    ["monte_carlo", "volatility", "sequence_risk", "swr"],
    "fx":            ["exchange_rate", "carry_trade", "inflation", "real_rate"],
    "ledger":        ["net_worth"],
    "diary":         ["net_worth", "asset_allocation"],
    "decision":      ["sharpe_ratio", "max_drawdown", "net_worth", "swr"],
}


def render_glossary_sidebar(
    keys: list[str] | None = None,
    *,
    page_key: str | None = None,
    max_terms: int = 4,
    expanded: bool = False,
) -> None:
    """Render a "小白科普" expander in the Streamlit sidebar.

    Args:
        keys:       Explicit list of GLOSSARY term keys to show.
        page_key:   Page identifier to look up preset keys from PAGE_GLOSSARY_KEYS.
                    Used when ``keys`` is None.
        max_terms:  Maximum number of terms to display (default 4).
        expanded:   Whether the expander is open by default (default False).
    """
    if keys is None:
        if page_key and page_key in PAGE_GLOSSARY_KEYS:
            keys = PAGE_GLOSSARY_KEYS[page_key]
        else:
            return  # nothing to show

    # Filter to valid keys only
    valid_keys = [k for k in keys if k in GLOSSARY][:max_terms]
    if not valid_keys:
        return

    with st.sidebar.expander("📖 小白科普：名词解释", expanded=expanded):
        st.caption("点击展开了解本页面涉及的金融概念。")
        for key in valid_keys:
            term = GLOSSARY[key]
            st.markdown(f"**{term['emoji']} {term['title']}**")
            st.caption(term["body"])
            if term.get("formula"):
                st.code(term["formula"], language=None)
            if term.get("example"):
                st.caption(f"💡 例子：{term['example']}")
            st.divider()
