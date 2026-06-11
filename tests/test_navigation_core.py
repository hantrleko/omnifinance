from core.navigation import (
    DASHBOARD_PROGRESS_ITEMS,
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


def test_search_pages_uses_synonyms():
    # Chinese synonyms should still resolve to the right page
    assert search_pages("养老金")[0].key == "retirement"
    assert search_pages("税务")[0].key == "tax"


def test_get_page_fetches_exact_key():
    page = get_page("budget")

    assert page.title == "预算分配建议器"
    assert page in PAGES


def test_decision_center_registered_under_platform_overview():
    grouped = pages_by_category()
    decision_page = get_page("decision")

    assert decision_page in grouped["平台概览"]
    assert decision_page.title == "决策中枢"
    assert decision_page.path == "pages/0_决策中枢.py"


def test_decision_center_is_searchable_by_chinese_and_english_aliases():
    decision_page = get_page("decision")

    assert decision_page in search_pages("决策")
    assert decision_page in search_pages("decision")


def test_decision_center_is_the_default_landing_page():
    default_pages = [page for page in PAGES if page.default]

    assert len(default_pages) == 1
    assert default_pages[0].key == "decision"
    assert get_page("home").default is False


def test_decision_center_progress_items_cover_expected_data_sources():
    expected = {"dashboard_budget", "dashboard_networth", "dashboard_retirement", "dashboard_loan", "dashboard_insurance", "dashboard_savings", "dashboard_tax"}
    actual = {item.session_key for item in DASHBOARD_PROGRESS_ITEMS}

    assert expected == expected.intersection(actual)
