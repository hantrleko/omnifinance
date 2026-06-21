"""core/ledger_import.py — CSV / Excel import parser for the ledger page.

Supported formats
-----------------
1. **Alipay (支付宝)**
   Export from: 支付宝 App → 账单 → 下载账单 → CSV
   Encoding: GBK (with BOM possible)
   Key columns: 交易时间, 收/支, 交易分类, 金额（元）, 备注

2. **WeChat Pay (微信支付)**
   Export from: 微信 → 我 → 支付 → 钱包 → 账单 → 下载账单
   Encoding: UTF-8 with BOM
   Key columns: 交易时间, 收/支, 交易类型, 金额(元), 备注

3. **Generic / Universal**
   Any CSV/Excel with columns: date, type, category, amount, note
   (Chinese or English headers, flexible column detection)

Output
------
All parsers return a list of dicts matching the ledger record schema:
  {
    "id": ISO timestamp string (unique),
    "date": "YYYY-MM-DD",
    "type": "收入" | "支出",
    "category": str,
    "amount": float,
    "note": str,
  }

Usage
-----
    from core.ledger_import import parse_upload

    records, errors = parse_upload(uploaded_file_bytes, filename)
    # records: list[dict] — successfully parsed records
    # errors:  list[str] — human-readable error messages
"""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from typing import Any

import pandas as pd

_logger = logging.getLogger(__name__)

# ── Category mapping helpers ───────────────────────────────────────────────────

_ALIPAY_CAT_MAP: dict[str, str] = {
    "餐饮美食": "餐饮",
    "餐饮": "餐饮",
    "购物": "购物",
    "网络购物": "购物",
    "日用百货": "购物",
    "交通出行": "交通",
    "出行": "交通",
    "滴滴出行": "交通",
    "住房物业": "住房",
    "租房": "住房",
    "水电煤": "住房",
    "医疗健康": "医疗",
    "娱乐": "娱乐",
    "游戏": "娱乐",
    "教育培训": "教育",
    "教育": "教育",
    "转账": "转账",
    "工资": "工资",
    "理财": "投资",
    "红包": "其他",
    "其他": "其他",
}

_WECHAT_CAT_MAP: dict[str, str] = {
    "餐饮": "餐饮",
    "购物": "购物",
    "交通": "交通",
    "出行": "交通",
    "住房": "住房",
    "医疗": "医疗",
    "娱乐": "娱乐",
    "教育": "教育",
    "转账": "转账",
    "工资": "工资",
    "理财": "投资",
    "红包": "其他",
    "其他": "其他",
    "微信红包": "其他",
    "零钱通": "投资",
}

_VALID_TYPES = {"收入", "支出"}
_VALID_CATEGORIES = {
    "餐饮", "购物", "交通", "住房", "医疗", "娱乐", "教育",
    "工资", "投资", "转账", "其他",
}


def _map_category(raw: str, cat_map: dict[str, str]) -> str:
    """Map a raw category string to a canonical ledger category."""
    raw = str(raw).strip()
    for key, val in cat_map.items():
        if key in raw:
            return val
    return "其他"


def _parse_amount(raw: Any) -> float | None:
    """Parse amount from various string formats (e.g. '¥12.50', '12,345.00')."""
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("¥", "").replace("￥", "").replace(" ", "")
    try:
        return abs(float(s))
    except ValueError:
        return None


def _make_id(dt_str: str, idx: int) -> str:
    """Generate a unique record ID from datetime string and row index."""
    return f"{dt_str}_{idx:04d}"


def _normalize_date(raw: Any) -> str | None:
    """Try to parse a date/datetime string and return 'YYYY-MM-DD'."""
    if raw is None:
        return None
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d",
                "%Y年%m月%d日", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try pandas
    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


# ── Alipay parser ──────────────────────────────────────────────────────────────

def _parse_alipay(content: bytes) -> tuple[list[dict], list[str]]:
    """Parse 支付宝 CSV export."""
    errors: list[str] = []
    records: list[dict] = []

    # Alipay CSV has several header lines before the actual data
    # Try GBK first, then UTF-8
    for enc in ("gbk", "gb18030", "utf-8-sig", "utf-8"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        errors.append("无法解码支付宝账单文件（尝试了 GBK / UTF-8 编码）")
        return records, errors

    lines = text.splitlines()

    # Find the header row (contains "交易时间" or "交易创建时间")
    header_idx = None
    for i, line in enumerate(lines):
        if "交易时间" in line or "交易创建时间" in line:
            header_idx = i
            break

    if header_idx is None:
        errors.append("未找到支付宝账单表头行（含'交易时间'）")
        return records, errors

    csv_text = "\n".join(lines[header_idx:])
    try:
        df = pd.read_csv(io.StringIO(csv_text), dtype=str)
    except Exception as exc:  # noqa: BLE001
        errors.append(f'解析支付宝 CSV 失败：{exc}')
        return records, errors

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    # Column name variants
    date_col = next((c for c in df.columns if "交易时间" in c or "时间" in c), None)
    type_col = next((c for c in df.columns if "收/支" in c or "收支" in c), None)
    cat_col = next((c for c in df.columns if "交易分类" in c or "分类" in c), None)
    amt_col = next((c for c in df.columns if "金额" in c), None)
    note_col = next((c for c in df.columns if "备注" in c or "商品名称" in c or "商品说明" in c), None)

    if not date_col or not amt_col:
        errors.append(f'支付宝账单缺少必要列（找到列：{list(df.columns)}）')
        return records, errors

    for idx, row in df.iterrows():
        date_str = _normalize_date(row.get(date_col))
        if not date_str:
            continue

        raw_type = str(row.get(type_col, "")).strip() if type_col else ""
        if "收入" in raw_type:
            rec_type = "收入"
        elif "支出" in raw_type or "不计收支" not in raw_type:
            rec_type = "支出"
        else:
            continue  # skip "不计收支" rows

        amount = _parse_amount(row.get(amt_col))
        if not amount or amount <= 0:
            continue

        raw_cat = str(row.get(cat_col, "")) if cat_col else ""
        category = _map_category(raw_cat, _ALIPAY_CAT_MAP)

        note = str(row.get(note_col, "")).strip() if note_col else ""
        if note in ("nan", "None", ""):
            note = raw_cat or ""

        records.append({
            "id": _make_id(date_str, int(str(idx))),
            "date": date_str,
            "type": rec_type,
            "category": category,
            "amount": round(amount, 2),
            "note": note[:100],
        })

    return records, errors


# ── WeChat Pay parser ──────────────────────────────────────────────────────────

def _parse_wechat(content: bytes) -> tuple[list[dict], list[str]]:
    """Parse 微信支付 CSV export."""
    errors: list[str] = []
    records: list[dict] = []

    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        errors.append("无法解码微信账单文件")
        return records, errors

    lines = text.splitlines()

    # WeChat header row contains "交易时间" and "交易类型"
    header_idx = None
    for i, line in enumerate(lines):
        if "交易时间" in line and ("交易类型" in line or "收/支" in line):
            header_idx = i
            break

    if header_idx is None:
        errors.append("未找到微信账单表头行（含'交易时间'和'交易类型'）")
        return records, errors

    csv_text = "\n".join(lines[header_idx:])
    try:
        df = pd.read_csv(io.StringIO(csv_text), dtype=str)
    except Exception as exc:  # noqa: BLE001
        errors.append(f'解析微信 CSV 失败：{exc}')
        return records, errors

    df.columns = [c.strip() for c in df.columns]

    date_col = next((c for c in df.columns if "交易时间" in c), None)
    type_col = next((c for c in df.columns if "收/支" in c or "收支" in c), None)
    cat_col = next((c for c in df.columns if "交易类型" in c), None)
    amt_col = next((c for c in df.columns if "金额" in c), None)
    note_col = next((c for c in df.columns if "商品" in c or "备注" in c), None)

    if not date_col or not amt_col:
        errors.append(f'微信账单缺少必要列（找到列：{list(df.columns)}）')
        return records, errors

    for idx, row in df.iterrows():
        date_str = _normalize_date(row.get(date_col))
        if not date_str:
            continue

        raw_type = str(row.get(type_col, "")).strip() if type_col else ""
        if "收入" in raw_type:
            rec_type = "收入"
        elif "支出" in raw_type:
            rec_type = "支出"
        else:
            continue

        amount = _parse_amount(row.get(amt_col))
        if not amount or amount <= 0:
            continue

        raw_cat = str(row.get(cat_col, "")).strip() if cat_col else ""
        category = _map_category(raw_cat, _WECHAT_CAT_MAP)

        note = str(row.get(note_col, "")).strip() if note_col else ""
        if note in ("nan", "None", ""):
            note = raw_cat or ""

        records.append({
            "id": _make_id(date_str, int(str(idx))),
            "date": date_str,
            "type": rec_type,
            "category": category,
            "amount": round(amount, 2),
            "note": note[:100],
        })

    return records, errors


# ── Generic / Universal parser ─────────────────────────────────────────────────

_GENERIC_DATE_ALIASES = ["date", "日期", "交易日期", "时间", "交易时间", "记录时间"]
_GENERIC_TYPE_ALIASES = ["type", "类型", "收支", "收/支", "收支类型"]
_GENERIC_CAT_ALIASES = ["category", "分类", "类别", "交易分类"]
_GENERIC_AMT_ALIASES = ["amount", "金额", "金额（元）", "金额(元)", "交易金额"]
_GENERIC_NOTE_ALIASES = ["note", "备注", "说明", "描述", "商品名称"]


def _find_col(columns: list[str], aliases: list[str]) -> str | None:
    cols_lower = [c.lower().strip() for c in columns]
    for alias in aliases:
        if alias.lower() in cols_lower:
            return columns[cols_lower.index(alias.lower())]
    return None


def _parse_generic(content: bytes, filename: str) -> tuple[list[dict], list[str]]:
    """Parse a generic CSV or Excel file."""
    errors: list[str] = []
    records: list[dict] = []

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "csv"

    try:
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            # Try multiple encodings
            for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin-1"):
                try:
                    df = pd.read_csv(io.StringIO(content.decode(enc)), dtype=str)
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            else:
                errors.append("无法解码文件（尝试了 UTF-8 / GBK / Latin-1 编码）")
                return records, errors
    except Exception as exc:  # noqa: BLE001
        errors.append(f'读取文件失败：{exc}')
        return records, errors

    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)

    date_col = _find_col(cols, _GENERIC_DATE_ALIASES)
    type_col = _find_col(cols, _GENERIC_TYPE_ALIASES)
    cat_col = _find_col(cols, _GENERIC_CAT_ALIASES)
    amt_col = _find_col(cols, _GENERIC_AMT_ALIASES)
    note_col = _find_col(cols, _GENERIC_NOTE_ALIASES)

    if not date_col:
        errors.append(f'未找到日期列（期望列名之一：{_GENERIC_DATE_ALIASES}，实际列：{cols}）')
        return records, errors
    if not amt_col:
        errors.append(f'未找到金额列（期望列名之一：{_GENERIC_AMT_ALIASES}，实际列：{cols}）')
        return records, errors

    for idx, row in df.iterrows():
        date_str = _normalize_date(row.get(date_col))
        if not date_str:
            continue

        amount = _parse_amount(row.get(amt_col))
        if amount is None or amount <= 0:
            continue

        # Determine type
        if type_col:
            raw_type = str(row.get(type_col, "")).strip()
            if "收入" in raw_type or raw_type.lower() in ("income", "in", "+"):
                rec_type = "收入"
            else:
                rec_type = "支出"
        else:
            rec_type = "支出"

        # Determine category
        if cat_col:
            raw_cat = str(row.get(cat_col, "")).strip()
            category = raw_cat if raw_cat in _VALID_CATEGORIES else "其他"
        else:
            category = "其他"

        note = str(row.get(note_col, "")).strip() if note_col else ""
        if note in ("nan", "None", ""):
            note = ""

        records.append({
            "id": _make_id(date_str, int(str(idx))),
            "date": date_str,
            "type": rec_type,
            "category": category,
            "amount": round(amount, 2),
            "note": note[:100],
        })

    return records, errors


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_format(content: bytes, filename: str) -> str:
    """Detect the file format: 'alipay', 'wechat', or 'generic'."""
    fn_lower = filename.lower()
    if "alipay" in fn_lower or "支付宝" in fn_lower:
        return "alipay"
    if "wechat" in fn_lower or "微信" in fn_lower or "wx" in fn_lower:
        return "wechat"

    # Try to detect by content
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            sample = content[:2000].decode(enc)
            if "支付宝" in sample or "alipay" in sample.lower():
                return "alipay"
            if "微信支付" in sample or "wechat" in sample.lower():
                return "wechat"
            break
        except UnicodeDecodeError:
            continue

    return "generic"


def parse_upload(
    content: bytes,
    filename: str,
    *,
    dedup_existing: list[dict] | None = None,
) -> tuple[list[dict], list[str], str]:
    """Parse an uploaded file and return ledger records.

    Args:
        content:         Raw file bytes from ``st.file_uploader``.
        filename:        Original filename (used for format detection).
        dedup_existing:  Existing records to deduplicate against (by date+amount+type).

    Returns:
        A tuple of:
          - ``records``: list of parsed record dicts (ready to append to ledger)
          - ``errors``:  list of human-readable error/warning strings
          - ``fmt``:     detected format string ('alipay', 'wechat', 'generic')
    """
    fmt = detect_format(content, filename)
    _logger.info("ledger_import: detected format=%s for file=%s", fmt, filename)

    if fmt == "alipay":
        records, errors = _parse_alipay(content)
    elif fmt == "wechat":
        records, errors = _parse_wechat(content)
    else:
        records, errors = _parse_generic(content, filename)

    # Deduplication: skip records that already exist (same date + amount + type)
    if dedup_existing:
        existing_keys = {
            (r["date"], r["type"], r["amount"])
            for r in dedup_existing
        }
        before = len(records)
        records = [
            r for r in records
            if (r["date"], r["type"], r["amount"]) not in existing_keys
        ]
        skipped = before - len(records)
        if skipped > 0:
            errors.append(f'已跳过 {skipped} 条重复记录（相同日期+金额+类型）')

    return records, errors, fmt
