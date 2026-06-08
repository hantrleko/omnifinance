from core.navigation import (
    NAVIGATION_CATEGORIES,
    PAGES,
    get_page,
    pages_by_category,
    search_pages,
)


def test_pages_are_grouped_in_declared_order():
    grouped = pages_by_category()

    assert list(grouped) == [category for category in NAVIGATION_CATEGORIES if category in grouped]
    assert grouped["平台概览"][0].default is True
    assert grouped["基础理财管理"][0].key == "compound"


def test_search_pages_matches_aliases_and_is_limited():
    results = search_pages("退休", limit=3)

    assert results
    assert results[0].key == "retirement"
    assert len(results) <= 3


def test_search_pages_supports_english_aliases():
    assert search_pages("ledger")[0].key == "ledger"
    assert search_pages("portfolio")[0].key == "portfolio"


def test_get_page_fetches_exact_key():
    page = get_page("budget")

    assert page.title == "预算分配建议器"
    assert page in PAGES
