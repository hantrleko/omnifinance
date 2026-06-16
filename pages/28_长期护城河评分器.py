"""长期护城河评分器

用户可输入代码或名称（优先代码）获得“护城河”指标化分解。
页面采用“主观判断 + 财务/价格代理指标”双输入模型，输出 0-5 分评分与可执行下一步。
"""
from __future__ import annotations

import math
from typing import Any

import streamlit as st
import yfinance as yf

from core.currency import fmt
from core.navigation import track_recent_page

track_recent_page(st.session_state, "moat")

from core.theme import inject_theme

inject_theme()

st.set_page_config(page_title="长期护城河评分器", page_icon="🛡️", layout="wide")
st.title("🛡️ 长期护城河评分器")
st.caption("用主观判断补齐定性，结合公开财务与波动指标形成更稳定的护城河评估。")


def _to_float(value: Any) -> float | None:
    """Convert any object to float safely."""
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace(",", "").strip()
        if not text or text in {"None", "nan", "N/A", "inf", "-inf"}:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _score_segment(value: float | None, *, good_if_higher: bool = True, points: tuple[float, ...] = (0.1, 0.2, 0.3, 0.45, 0.6)) -> float | None:
    """Convert a ratio/value to 0-5 score according to custom thresholds."""
    if value is None or not isinstance(value, (int, float)):
        return None
    if math.isnan(value) or math.isinf(value):
        return None

    if not good_if_higher:
        # e.g. debt/equity is better when lower.
        if value <= 0:
            return 5.0
        if value <= 0.2:
            return 4.5
        if value <= 0.4:
            return 4.0
        if value <= 0.7:
            return 3.0
        if value <= 1.2:
            return 2.0
        return 1.0

    # Better when higher.
    if value >= points[4]:
        return 5.0
    if value >= points[3]:
        return 4.0
    if value >= points[2]:
        return 3.5
    if value >= points[1]:
        return 2.5
    if value >= points[0]:
        return 1.5
    return 1.0


def _fetch_signal_scores(symbol: str) -> dict[str, float | None]:
    """Fetch a lightweight set of proxy signals from yfinance."""
    scores: dict[str, float | None] = {
        "利润率强度": None,
        "盈利质量": None,
        "资本效率": None,
        "成长延续性": None,
        "价格弹性": None,
        "财务韧性": None,
    }
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        gross_margin = _to_float(info.get("grossMargins"))
        op_margin = _to_float(info.get("operatingMargins"))
        roa = _to_float(info.get("returnOnAssets"))
        roa = roa if roa is not None else _to_float(info.get("returnOnEquity"))
        debt_to_equity = _to_float(info.get("debtToEquity"))
        revenue_growth = _to_float(info.get("revenueGrowth"))

        if gross_margin is None:
            gross_margin = _to_float(info.get("grossMargins", None))
        if gross_margin is not None and gross_margin > 1:
            gross_margin = gross_margin / 100

        if op_margin is not None and op_margin > 1:
            op_margin = op_margin / 100
        if roa is not None and roa > 1:
            roa = roa / 100
        if revenue_growth is not None and abs(revenue_growth) > 1:
            revenue_growth = revenue_growth / 100

        scores["利润率强度"] = max(_score_segment(gross_margin), _score_segment(op_margin) or 0.0)
        scores["盈利质量"] = _score_segment(op_margin)
        scores["资本效率"] = _score_segment(roa, points=(0.02, 0.04, 0.08, 0.12, 0.2))
        if debt_to_equity is not None and debt_to_equity > 2:
            # yfinance may return ratio as % in some locales; normalize roughly.
            if debt_to_equity > 10:
                debt_to_equity /= 100
        scores["财务韧性"] = _score_segment(debt_to_equity, good_if_higher=False)
        scores["成长延续性"] = _score_segment(revenue_growth)

        # 价格弹性：优先用历史收盘波动作为 proxy，越稳定越容易形成可持续优势
        hist = ticker.history(period="12mo", interval="1d")
        if hist is not None and not hist.empty and "Close" in hist:
            rets = hist["Close"].pct_change().dropna()
            if len(rets) >= 40:
                ann_vol = _to_float((rets.std() * math.sqrt(252))) if not rets.empty else None
                if ann_vol is not None:
                    if ann_vol <= 0.18:
                        scores["价格弹性"] = 5.0
                    elif ann_vol <= 0.25:
                        scores["价格弹性"] = 4.5
                    elif ann_vol <= 0.35:
                        scores["价格弹性"] = 3.5
                    elif ann_vol <= 0.45:
                        scores["价格弹性"] = 2.5
                    else:
                        scores["价格弹性"] = 1.5
        return scores
    except Exception:
        return scores


def _weighted_score(values: list[float], weights: list[float]) -> float:
    """Weighted average with fallback support."""
    if not values:
        return 0.0
    ws = [w for v, w in zip(values, weights) if v is not None]
    vs = [v for v in values if v is not None]
    if not vs:
        return 0.0
    total_w = sum(w for v, w in zip(values, weights) if v is not None)
    if total_w <= 0:
        return 0.0
    return sum((v or 0.0) * w for v, w in zip(values, weights) if v is not None) / total_w


with st.expander("🎯 先打主观分（1-5，5分更强）", expanded=True):
    q1 = st.slider("品牌粘性与定价能力", 1, 5, 3, help="价格更容易保持/提高、客户更难转移到竞品")
    q2 = st.slider("网络效应", 1, 5, 3, help="用户/生态是否形成正反馈，规模越大越强")
    q3 = st.slider("规模与成本优势", 1, 5, 3, help="固定成本、供应链与效率是否形成长期成本压制")
    q4 = st.slider("监管与准入壁垒", 1, 5, 3, help="许可证、牌照、标准、技术复杂度等进入门槛")
    q5 = st.slider("资本配置纪律", 1, 5, 3, help="是否能持续复投到高效率赛道并控制过度扩张")

subjective_scores = {
    "品牌与定价能力": q1,
    "网络效应": q2,
    "规模/成本优势": q3,
    "准入壁垒": q4,
    "资本纪律": q5,
}
sub_total = sum(subjective_scores.values()) / len(subjective_scores)

with st.expander("📈 输入公司标的（可选）", expanded=True):
    symbol = st.text_input(
        "公司代码（美股/港股优先输入代码，如 AAPL、NVDA、0700.HK）",
        placeholder="留空则仅用主观评分",
    ).strip()

if symbol:
    st.subheader("🔍 自动信号")
    with st.spinner("正在抓取公开数据..."):
        auto_scores = _fetch_signal_scores(symbol)
    valid_auto = [v for v in auto_scores.values() if isinstance(v, (int, float))]
    if valid_auto:
        auto_total = sum(valid_auto) / len(valid_auto)
        st.caption("已提取可用的公开代理指标；若某些项缺失则不计入该项权重。")
    else:
        auto_total = None
        st.caption("当前市场数据未返回有效指标，已回退到主观评分。")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**主观评分明细**")
        for name, value in subjective_scores.items():
            st.metric(name, f"{value:.1f}/5")
    with col_b:
        st.markdown("**数据评分明细（0-5）**")
        for name, value in auto_scores.items():
            if value is None:
                st.metric(name, "—")
            else:
                st.metric(name, f"{value:.1f}/5")
else:
    auto_total = None
    auto_scores = {}
    st.caption("未填写代码时，系统仅使用主观评分。")

if auto_total is not None:
    moat_total = _weighted_score([sub_total, auto_total], [0.6, 0.4])
    detail = "主观 60% + 数据 40%"
else:
    moat_total = sub_total
    detail = "仅主观评分"

if moat_total >= 4.3:
    level = "🛡️ 强护城河"
    color = "success"
elif moat_total >= 3.3:
    level = "⚖️ 中等护城河"
    color = "warning"
else:
    level = "⚠️ 护城河较弱"
    color = "error"

st.markdown("---")
st.subheader("🧭 结果")
st.metric("长期护城河总分（0-5）", f"{moat_total:.2f}", delta=detail)

if color == "success":
    st.success(f"{level}：企业在长期竞争中更容易稳定现金流与议价权。")
elif color == "warning":
    st.warning(f"{level}：护城河存在，但受行业波动与估值节奏影响较大。")
else:
    st.error(f"{level}：缺少稳定护城河特征，建议优先核验商业模式与财务真实性。")

st.markdown("### 📊 分维打分建议")
left, right = st.columns(2)
with left:
    st.caption("主观维度平均")
    st.progress(sub_total / 5)
    st.write(f"{sub_total:.2f}/5")
    for name, value in subjective_scores.items():
        st.markdown(f"- **{name}**：{value:.1f}")
with right:
    if auto_scores:
        st.caption("数据维度平均")
        st.progress((auto_total or 0.0) / 5)
        st.write(f"{auto_total:.2f}/5" if auto_total is not None else "—")
        for name, value in auto_scores.items():
            if value is not None:
                st.markdown(f"- **{name}**：{value:.1f}")

if symbol:
    st.markdown("### 🧭 后续动作")
    st.write(
        "- 对比同业同规模企业：让该分数相对位置更重要，单只样本不能直接下结论。"
    )
    st.write("- 把“价格弹性 / 波动率”与财务韧性放在第一优先级观察，出现结构性下滑时优先降权。")
    st.write("- 若关键指标与现金流趋势不一致（例如毛利下滑却仍高估），延后 3-6 个月再复评。")
else:
    st.markdown("### 🧭 后续动作")
    st.write("- 护城河不是一次性结论，建议每个财报季重新打分。")
    st.write("- 将主观分作为行业判断锚，结合估值与估值修复情况再做最终仓位决策。")

st.caption("说明：本工具不构成投资建议，计算过程仅用于个人财务学习与决策体验。")
