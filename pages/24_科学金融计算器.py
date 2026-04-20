"""科学 + 金融四合一计算器

科学计算区：键盘按键 + 表达式输入，支持数学函数与历史记录。
金融计算区：4 个 Tab — 复利终值/现值、年金/IRR、债券定价、百分比工具。
"""
from __future__ import annotations

import math
from typing import Any

import streamlit as st
from core.theme import inject_theme
inject_theme()

from core.currency import fmt, get_symbol
from core.planning import solve_irr

st.set_page_config(page_title="科学金融计算器", page_icon="🧮", layout="wide")
st.title("🧮 科学 + 金融计算器")
st.caption("科学计算与常用金融公式的统一工具台")

sym = get_symbol()

if "calc_expr" not in st.session_state:
    st.session_state["calc_expr"] = ""
if "calc_history" not in st.session_state:
    st.session_state["calc_history"] = []


def _safe_eval(expr: str) -> str:
    allowed_names: dict[str, Any] = {
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan,
        "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
        "log2": math.log2, "exp": math.exp, "abs": abs,
        "factorial": math.factorial, "pi": math.pi, "e": math.e,
        "pow": pow, "round": round,
    }
    try:
        result = eval(expr, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return str(result)
    except ZeroDivisionError:
        return "错误：除以零"
    except Exception as exc:
        return f"错误：{exc}"


# ── Layout: two main columns ───────────────────────────────
col_sci, col_fin = st.columns([1, 1], gap="large")

# ══════════════════════════════════════════════════════════
# SCIENTIFIC CALCULATOR
# ══════════════════════════════════════════════════════════
with col_sci:
    st.subheader("🔬 科学计算器")

    expr_display = st.text_input(
        "表达式（支持 sin/cos/tan/sqrt/log/exp/pi/e/factorial）",
        value=st.session_state["calc_expr"],
        key="expr_input",
        placeholder="例如：sin(pi/6) * sqrt(144)",
    )
    st.session_state["calc_expr"] = expr_display

    _OPERATORS = {"÷", "×", "-", "+", "(", ")", "**2", "**0.5"}
    _FUNCTIONS = {"sin(", "cos(", "tan(", "sqrt(", "log(", "log10(", "exp(", "factorial("}
    _SPECIALS = {"AC", "⌫"}
    _EQUALS = {"="}
    _CONSTANTS = {"π", "e"}

    btn_rows = [
        ["7", "8", "9", "÷", "sin(", "cos("],
        ["4", "5", "6", "×", "tan(", "sqrt("],
        ["1", "2", "3", "-", "log(", "log10("],
        ["0", ".", "(", "+", "exp(", "factorial("],
        ["π", "e", ")", "**2", "**0.5", "⌫"],
        ["AC", "="],
    ]

    def _btn_css_class(lbl: str) -> str:
        if lbl in _EQUALS:
            return "calc-btn-equals"
        if lbl in _SPECIALS:
            return "calc-btn-special"
        if lbl in _OPERATORS or lbl in _CONSTANTS:
            return "calc-btn-operator"
        if lbl in _FUNCTIONS:
            return "calc-btn-function"
        return ""

    for row in btn_rows:
        cols_btn = st.columns(len(row))
        for i, label in enumerate(row):
            css_cls = _btn_css_class(label)
            with cols_btn[i]:
                if css_cls:
                    st.markdown(f'<div class="{css_cls}">', unsafe_allow_html=True)
                clicked = st.button(label, key=f"btn_{label}_{i}", use_container_width=True)
                if css_cls:
                    st.markdown("</div>", unsafe_allow_html=True)
                if clicked:
                    if label == "AC":
                        st.session_state["calc_expr"] = ""
                    elif label == "⌫":
                        st.session_state["calc_expr"] = st.session_state["calc_expr"][:-1]
                    elif label == "=":
                        r = _safe_eval(st.session_state["calc_expr"])
                        history_entry = f"{st.session_state['calc_expr']} = {r}"
                        st.session_state["calc_history"] = [history_entry] + st.session_state["calc_history"][:9]
                        st.session_state["calc_expr"] = r if not r.startswith("错误") else st.session_state["calc_expr"]
                    elif label == "π":
                        st.session_state["calc_expr"] += "pi"
                    elif label == "×":
                        st.session_state["calc_expr"] += "*"
                    elif label == "÷":
                        st.session_state["calc_expr"] += "/"
                    else:
                        st.session_state["calc_expr"] += label
                    st.rerun()

    if st.session_state["calc_history"]:
        with st.expander("🕘 最近 10 条历史记录"):
            for h in st.session_state["calc_history"]:
                h_col1, h_col2 = st.columns([4, 1])
                h_col1.caption(h)
                if h_col2.button("复用", key=f"hist_{h}"):
                    result_part = h.split("=")[-1].strip()
                    st.session_state["calc_expr"] = result_part
                    st.rerun()

# ══════════════════════════════════════════════════════════
# FINANCIAL CALCULATOR — 4 Tabs
# ══════════════════════════════════════════════════════════
with col_fin:
    st.subheader("💹 金融计算器")

    tab1, tab2, tab3, tab4 = st.tabs(["复利终值/现值", "年金 / IRR", "债券定价", "百分比工具"])

    # ── Tab 1: FV / PV ────────────────────────────────────
    with tab1:
        st.markdown("**复利终值 / 现值互求**")
        fv_solve = st.radio("求解目标", ["终值 FV", "现值 PV", "利率 r", "期数 n"], horizontal=True, key="fv_solve")

        c1, c2 = st.columns(2)
        if fv_solve != "现值 PV":
            pv = c1.number_input("现值 PV", value=100000.0, step=1000.0, key="fv_pv")
        else:
            pv = None
        if fv_solve != "终值 FV":
            fv = c2.number_input("终值 FV", value=200000.0, step=1000.0, key="fv_fv")
        else:
            fv = None
        if fv_solve != "利率 r":
            r_pct = c1.number_input("年利率 (%)", value=8.0, step=0.1, key="fv_r")
            r = r_pct / 100
        else:
            r = None
        if fv_solve != "期数 n":
            n_yr = c2.number_input("期数 (年)", value=10, step=1, min_value=1, key="fv_n")
        else:
            n_yr = None

        if st.button("计算", key="fv_calc"):
            try:
                if fv_solve == "终值 FV" and pv is not None and r is not None and n_yr is not None:
                    res = pv * (1 + r) ** n_yr
                    st.metric("终值 FV", fmt(res))
                elif fv_solve == "现值 PV" and fv is not None and r is not None and n_yr is not None:
                    res = fv / (1 + r) ** n_yr
                    st.metric("现值 PV", fmt(res))
                elif fv_solve == "利率 r" and pv is not None and fv is not None and n_yr is not None:
                    res = (fv / pv) ** (1 / n_yr) - 1
                    st.metric("年利率 r", f"{res*100:.4f}%")
                elif fv_solve == "期数 n" and pv is not None and fv is not None and r is not None:
                    if r <= 0:
                        st.error("利率必须大于 0")
                    else:
                        res = math.log(fv / pv) / math.log(1 + r)
                        st.metric("期数 n（年）", f"{res:.2f}")
            except Exception as exc:
                st.error(f"计算错误：{exc}")

    # ── Tab 2: PMT / NPV / IRR ────────────────────────────
    with tab2:
        st.markdown("**年金计算 / NPV / IRR**")
        ann_mode = st.radio("计算模式", ["年金终值 FVA", "年金现值 PVA", "IRR 求解"], horizontal=True, key="ann_mode")

        if ann_mode in ("年金终值 FVA", "年金现值 PVA"):
            a1, a2, a3 = st.columns(3)
            pmt = a1.number_input("每期付款 PMT", value=5000.0, step=500.0, key="ann_pmt")
            r_ann_pct = a2.number_input("年利率 (%)", value=6.0, step=0.1, key="ann_r")
            n_ann = a3.number_input("期数", value=10, step=1, min_value=1, key="ann_n")
            r_ann = r_ann_pct / 100

            if st.button("计算", key="ann_calc"):
                if r_ann == 0:
                    result_ann = pmt * n_ann
                elif ann_mode == "年金终值 FVA":
                    result_ann = pmt * ((1 + r_ann) ** n_ann - 1) / r_ann
                else:
                    result_ann = pmt * (1 - (1 + r_ann) ** -n_ann) / r_ann
                st.metric(ann_mode, fmt(result_ann))

        else:
            st.caption("输入现金流序列（第 0 期通常为负的初始投入）")
            irr_text = st.text_area("现金流（每行一个数字）", value="-100000\n20000\n25000\n30000\n35000\n40000", height=140, key="irr_text")
            if st.button("计算 IRR", key="irr_calc"):
                try:
                    cfs = [float(x.strip()) for x in irr_text.strip().splitlines() if x.strip()]
                    irr_val = solve_irr(cfs) * 100
                    npv_10 = sum(cf / (1.1) ** t for t, cf in enumerate(cfs))
                    i1, i2 = st.columns(2)
                    i1.metric("IRR（每期）", f"{irr_val:.4f}%")
                    i2.metric("NPV（折现率 10%）", fmt(npv_10))
                except Exception as exc:
                    st.error(f"计算错误：{exc}")

    # ── Tab 3: Bond Pricing ───────────────────────────────
    with tab3:
        st.markdown("**债券定价 — 价格 / 久期 / 凸性**")
        b1, b2 = st.columns(2)
        face = b1.number_input("面值", value=1000.0, step=100.0, key="bond_face")
        coupon_pct = b2.number_input("票面利率 (%)", value=5.0, step=0.1, key="bond_coupon")
        b3, b4 = st.columns(2)
        ytm_pct = b3.number_input("到期收益率 YTM (%)", value=6.0, step=0.1, key="bond_ytm")
        periods = b4.number_input("剩余期数（半年）", value=10, step=1, min_value=1, key="bond_n")

        if st.button("计算债券指标", key="bond_calc"):
            c_half = face * coupon_pct / 100 / 2
            y_half = ytm_pct / 100 / 2
            n_p = int(periods)
            if y_half == 0:
                price = c_half * n_p + face
            else:
                price = sum(c_half / (1 + y_half) ** t for t in range(1, n_p + 1)) + face / (1 + y_half) ** n_p

            duration = sum(t * c_half / (1 + y_half) ** t for t in range(1, n_p + 1))
            duration += n_p * face / (1 + y_half) ** n_p
            duration /= price if price > 0 else 1

            convexity = sum(t * (t + 1) * c_half / (1 + y_half) ** (t + 2) for t in range(1, n_p + 1))
            convexity += n_p * (n_p + 1) * face / (1 + y_half) ** (n_p + 2)
            convexity /= price if price > 0 else 1

            bd1, bd2, bd3 = st.columns(3)
            bd1.metric("债券价格", fmt(price))
            bd2.metric("麦考利久期（半年）", f"{duration:.4f}")
            bd3.metric("凸性", f"{convexity:.4f}")
            mod_dur = duration / (1 + y_half)
            st.info(f"修正久期 = {mod_dur:.4f}，YTM 每变动 1%，价格约变动 {-mod_dur:.2f}%")

    # ── Tab 4: Percentage Tools ───────────────────────────
    with tab4:
        st.markdown("**百分比工具**")

        pct_mode = st.selectbox("选择计算类型", [
            "变动幅度（增幅/降幅）",
            "折扣计算",
            "CAGR（复合年增长率）",
            "通胀调整值",
        ], key="pct_mode")

        if pct_mode == "变动幅度（增幅/降幅）":
            pa, pb = st.columns(2)
            old_val = pa.number_input("原始值", value=100.0, step=1.0, key="pct_old")
            new_val = pb.number_input("新值", value=120.0, step=1.0, key="pct_new")
            if old_val != 0:
                change = (new_val - old_val) / old_val * 100
                st.metric("变动幅度", f"{change:+.4f}%")

        elif pct_mode == "折扣计算":
            pp, pd_ = st.columns(2)
            orig_price = pp.number_input("原价", value=1000.0, step=10.0, key="disc_orig")
            discount_pct = pd_.number_input("折扣 (%)", value=20.0, step=1.0, key="disc_pct")
            final_price = orig_price * (1 - discount_pct / 100)
            saved = orig_price - final_price
            dc1, dc2 = st.columns(2)
            dc1.metric("折后价格", fmt(final_price))
            dc2.metric("节省金额", fmt(saved))

        elif pct_mode == "CAGR（复合年增长率）":
            cg1, cg2, cg3 = st.columns(3)
            start_v = cg1.number_input("初始值", value=100000.0, step=1000.0, key="cagr_start")
            end_v = cg2.number_input("终止值", value=200000.0, step=1000.0, key="cagr_end")
            years_v = cg3.number_input("年数", value=5, step=1, min_value=1, key="cagr_yr")
            if start_v > 0:
                cagr = (end_v / start_v) ** (1 / years_v) - 1
                st.metric("CAGR", f"{cagr*100:.4f}%")

        elif pct_mode == "通胀调整值":
            ia1, ia2, ia3 = st.columns(3)
            nominal = ia1.number_input("名义金额", value=100000.0, step=1000.0, key="inf_nom")
            inf_pct = ia2.number_input("年通胀率 (%)", value=3.0, step=0.1, key="inf_rate")
            inf_yrs = ia3.number_input("年数", value=10, step=1, min_value=1, key="inf_yr")
            real_val = nominal / (1 + inf_pct / 100) ** inf_yrs
            ic1, ic2 = st.columns(2)
            ic1.metric("实际购买力（今日价值）", fmt(real_val))
            ic2.metric("购买力损失", fmt(nominal - real_val))

st.markdown("---")
st.caption("🧮 科学金融计算器 | 运行命令：`streamlit run app.py`")
