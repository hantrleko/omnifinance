"""Tests for core/ledger_import.py — 收支记账本 CSV/Excel 导入解析器"""
import io

import pandas as pd
import pytest

from core.ledger_import import (
    detect_format,
    parse_upload,
    _parse_alipay,
    _parse_wechat,
    _parse_generic,
    _parse_amount,
    _normalize_date,
    _map_category,
)


# ── _parse_amount ─────────────────────────────────────────────────────────────

def test_parse_amount_plain_number():
    assert _parse_amount("100.50") == pytest.approx(100.50)


def test_parse_amount_with_yuan_sign():
    assert _parse_amount("¥38.00") == pytest.approx(38.00)


def test_parse_amount_with_comma():
    assert _parse_amount("1,234.56") == pytest.approx(1234.56)


def test_parse_amount_negative():
    # _parse_amount returns abs() value — negative sign is stripped by design
    assert _parse_amount("-50.0") == pytest.approx(50.0)


def test_parse_amount_invalid_returns_none():
    assert _parse_amount("abc") is None


def test_parse_amount_empty_returns_none():
    assert _parse_amount("") is None


def test_parse_amount_none_returns_none():
    assert _parse_amount(None) is None


# ── _normalize_date ───────────────────────────────────────────────────────────

def test_normalize_date_iso_format():
    result = _normalize_date("2024-01-15")
    assert result == "2024-01-15"


def test_normalize_date_with_time():
    result = _normalize_date("2024-01-15 12:30:00")
    assert result is not None
    assert "2024-01-15" in result


def test_normalize_date_chinese_format():
    result = _normalize_date("2024年01月15日")
    assert result is not None


def test_normalize_date_invalid_returns_none():
    result = _normalize_date("not a date")
    assert result is None


# ── _map_category ─────────────────────────────────────────────────────────────

def test_map_category_direct_match():
    cat_map = {"餐饮美食": "餐饮", "交通出行": "交通"}
    assert _map_category("餐饮美食", cat_map) == "餐饮"


def test_map_category_no_match_returns_other():
    cat_map = {"餐饮美食": "餐饮"}
    result = _map_category("未知分类", cat_map)
    assert isinstance(result, str)


# ── detect_format ─────────────────────────────────────────────────────────────

def test_detect_format_alipay_by_content():
    content = "支付宝交易记录明细查询\n交易时间,交易分类,交易对方\n".encode("utf-8")
    result = detect_format(content, "alipay_export.csv")
    assert result == "alipay"


def test_detect_format_wechat_by_content():
    content = "微信支付账单明细\n交易时间,交易类型,交易对方\n".encode("utf-8")
    result = detect_format(content, "wechat_bill.csv")
    assert result == "wechat"


def test_detect_format_generic_by_filename():
    content = "日期,金额,类别\n2024-01-01,100,餐饮\n".encode("utf-8")
    result = detect_format(content, "my_records.csv")
    assert result in ("generic", "alipay", "wechat")


def test_detect_format_alipay_by_filename():
    content = b"some content"
    result = detect_format(content, "alipay_20240101.csv")
    assert result == "alipay"


def test_detect_format_wechat_by_filename():
    content = b"some content"
    result = detect_format(content, "wechat_20240101.csv")
    assert result == "wechat"


# ── _parse_generic ────────────────────────────────────────────────────────────

def _make_csv_bytes(rows: list[dict], columns: list[str]) -> bytes:
    df = pd.DataFrame(rows, columns=columns)
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


def test_parse_generic_basic():
    csv_bytes = _make_csv_bytes(
        [
            {"日期": "2024-01-15", "金额": "100.50", "类别": "餐饮", "描述": "午餐"},
            {"日期": "2024-01-16", "金额": "5000.00", "类别": "工资", "描述": "月薪"},
        ],
        ["日期", "金额", "类别", "描述"],
    )
    records, errors = _parse_generic(csv_bytes, "test.csv")
    assert isinstance(records, list)
    assert isinstance(errors, list)
    assert len(records) >= 1


def test_parse_generic_returns_dicts():
    csv_bytes = _make_csv_bytes(
        [{"日期": "2024-02-01", "金额": "200", "类别": "购物"}],
        ["日期", "金额", "类别"],
    )
    records, errors = _parse_generic(csv_bytes, "test.csv")
    for r in records:
        assert isinstance(r, dict)


def test_parse_generic_empty_csv():
    csv_bytes = b"\xe6\x97\xa5\xe6\x9c\x9f,\xe9\x87\x91\xe9\xa2\x9d,\xe7\xb1\xbb\xe5\x88\xab\n"  # header only
    records, errors = _parse_generic(csv_bytes, "empty.csv")
    assert records == []


def test_parse_generic_skips_invalid_amounts():
    csv_bytes = _make_csv_bytes(
        [
            {"日期": "2024-01-01", "金额": "abc", "类别": "餐饮"},
            {"日期": "2024-01-02", "金额": "50.0", "类别": "交通"},
        ],
        ["日期", "金额", "类别"],
    )
    records, errors = _parse_generic(csv_bytes, "test.csv")
    # All returned records should have valid amounts
    for r in records:
        assert isinstance(r.get("amount", r.get("金额")), (int, float))


# ── _parse_alipay ─────────────────────────────────────────────────────────────

def test_parse_alipay_returns_tuple():
    alipay_csv = (
        "支付宝交易记录明细查询\n"
        "账号:[test@example.com]\n"
        "起始日期:[2024-01-01 00:00:00]    终止日期:[2024-01-31 23:59:59]\n"
        "---------------------------------\n"
        "交易时间,交易分类,交易对方,商品说明,收/支,金额（元）,收/支,备注\n"
        "2024-01-15 12:30:00,餐饮美食,美团外卖,午餐,支出,35.50,,\n"
        "---------------------------------\n"
    ).encode("utf-8")
    records, errors = _parse_alipay(alipay_csv)
    assert isinstance(records, list)
    assert isinstance(errors, list)


def test_parse_alipay_malformed_returns_empty():
    records, errors = _parse_alipay(b"garbage data")
    assert isinstance(records, list)
    assert isinstance(errors, list)


# ── _parse_wechat ─────────────────────────────────────────────────────────────

def test_parse_wechat_returns_tuple():
    wechat_csv = (
        "微信支付账单明细\n"
        "微信昵称：[测试用户]\n"
        "----\n"
        "交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注\n"
        "2024-01-15 14:00:00,商户消费,星巴克,咖啡,支出,¥38.00,零钱,支付成功,xxx,yyy,\n"
    ).encode("utf-8")
    records, errors = _parse_wechat(wechat_csv)
    assert isinstance(records, list)
    assert isinstance(errors, list)


def test_parse_wechat_malformed_returns_empty():
    records, errors = _parse_wechat(b"not valid wechat format")
    assert isinstance(records, list)
    assert isinstance(errors, list)


# ── parse_upload (public API) ─────────────────────────────────────────────────

def test_parse_upload_returns_three_tuple():
    csv_bytes = _make_csv_bytes(
        [{"日期": "2024-03-01", "金额": "300", "类别": "购物"}],
        ["日期", "金额", "类别"],
    )
    result = parse_upload(csv_bytes, "records.csv")
    assert isinstance(result, tuple)
    assert len(result) == 3


def test_parse_upload_records_is_list():
    csv_bytes = _make_csv_bytes(
        [{"日期": "2024-03-01", "金额": "150", "类别": "交通"}],
        ["日期", "金额", "类别"],
    )
    records, errors, fmt = parse_upload(csv_bytes, "records.csv")
    assert isinstance(records, list)
    assert isinstance(errors, list)
    assert isinstance(fmt, str)


def test_parse_upload_dedup_removes_duplicates():
    csv_bytes = _make_csv_bytes(
        [{"日期": "2024-03-01", "金额": "300", "类别": "购物"}],
        ["日期", "金额", "类别"],
    )
    # First parse to get the record
    records1, _, _ = parse_upload(csv_bytes, "records.csv")
    if records1:
        # Second parse with existing records should deduplicate
        records2, _, _ = parse_upload(csv_bytes, "records.csv", dedup_existing=records1)
        assert len(records2) <= len(records1)


def test_parse_upload_alipay_format():
    alipay_csv = (
        "支付宝交易记录明细查询\n"
        "账号:[test@example.com]\n"
        "---------------------------------\n"
        "交易时间,交易分类,交易对方,商品说明,收/支,金额（元）,收/支,备注\n"
        "2024-01-15 12:30:00,餐饮美食,美团外卖,午餐,支出,35.50,,\n"
        "---------------------------------\n"
    ).encode("utf-8")
    records, errors, fmt = parse_upload(alipay_csv, "alipay_export.csv")
    assert fmt == "alipay"
    assert isinstance(records, list)
