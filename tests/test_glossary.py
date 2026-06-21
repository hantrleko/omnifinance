"""Tests for core/glossary.py — 金融概念小白科普模块"""
import pytest
from unittest.mock import MagicMock, patch


# ── Import guard (no streamlit at test time) ─────────────────────────────────
def test_glossary_module_importable():
    """glossary module can be imported without streamlit running."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        import importlib
        import sys
        # Remove cached module if present
        sys.modules.pop("core.glossary", None)
        import core.glossary as g
        assert hasattr(g, "GLOSSARY")
        assert hasattr(g, "PAGE_GLOSSARY_KEYS")
        assert hasattr(g, "render_glossary_sidebar")


def test_glossary_has_expected_terms():
    """GLOSSARY contains all expected core terms."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import GLOSSARY
        expected_keys = [
            "compound_interest", "sharpe_ratio", "volatility", "beta", "alpha",
            "pe_ratio", "pb_ratio", "roe", "roic", "moat", "var", "max_drawdown",
            "monte_carlo", "swr", "fire", "net_worth", "rebalancing",
        ]
        for key in expected_keys:
            assert key in GLOSSARY, f"Missing term: {key}"


def test_glossary_term_structure():
    """Every term has required fields: title, emoji, body."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import GLOSSARY
        for key, term in GLOSSARY.items():
            assert "title" in term, f"{key} missing 'title'"
            assert "emoji" in term, f"{key} missing 'emoji'"
            assert "body" in term, f"{key} missing 'body'"
            assert len(term["body"]) > 10, f"{key} body too short"


def test_page_glossary_keys_reference_valid_terms():
    """All keys in PAGE_GLOSSARY_KEYS reference valid GLOSSARY entries."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import GLOSSARY, PAGE_GLOSSARY_KEYS
        for page, keys in PAGE_GLOSSARY_KEYS.items():
            for key in keys:
                assert key in GLOSSARY, f"Page '{page}' references unknown term '{key}'"


def test_page_glossary_covers_key_pages():
    """PAGE_GLOSSARY_KEYS covers all major tool pages."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import PAGE_GLOSSARY_KEYS
        expected_pages = ["portfolio", "moat", "rebalance", "screener", "montecarlo", "backtest"]
        for page in expected_pages:
            assert page in PAGE_GLOSSARY_KEYS, f"Missing page preset: {page}"


def test_render_glossary_sidebar_no_keys_does_nothing():
    """render_glossary_sidebar with no keys and no page_key returns silently."""
    mock_st = MagicMock()
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import render_glossary_sidebar
        render_glossary_sidebar()  # should not raise
        mock_st.sidebar.expander.assert_not_called()


def test_render_glossary_sidebar_with_valid_page_key():
    """render_glossary_sidebar with valid page_key calls st.sidebar.expander."""
    mock_st = MagicMock()
    mock_expander = MagicMock()
    mock_expander.__enter__ = MagicMock(return_value=mock_expander)
    mock_expander.__exit__ = MagicMock(return_value=False)
    mock_st.sidebar.expander.return_value = mock_expander
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import render_glossary_sidebar
        render_glossary_sidebar(page_key="portfolio")
        mock_st.sidebar.expander.assert_called_once()


def test_render_glossary_sidebar_with_explicit_keys():
    """render_glossary_sidebar with explicit keys list works."""
    mock_st = MagicMock()
    mock_expander = MagicMock()
    mock_expander.__enter__ = MagicMock(return_value=mock_expander)
    mock_expander.__exit__ = MagicMock(return_value=False)
    mock_st.sidebar.expander.return_value = mock_expander
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import render_glossary_sidebar
        render_glossary_sidebar(keys=["compound_interest", "fv"])
        mock_st.sidebar.expander.assert_called_once()


def test_render_glossary_sidebar_invalid_keys_filtered():
    """render_glossary_sidebar silently ignores unknown keys."""
    mock_st = MagicMock()
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import render_glossary_sidebar
        # All invalid keys → nothing to show → expander not called
        render_glossary_sidebar(keys=["nonexistent_term_xyz"])
        mock_st.sidebar.expander.assert_not_called()


def test_render_glossary_sidebar_max_terms_respected():
    """render_glossary_sidebar respects max_terms limit: expander is shown."""
    mock_st = MagicMock()
    mock_expander = MagicMock()
    mock_expander.__enter__ = MagicMock(return_value=mock_expander)
    mock_expander.__exit__ = MagicMock(return_value=False)
    mock_st.sidebar.expander.return_value = mock_expander
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        import sys
        sys.modules.pop("core.glossary", None)
        from core.glossary import render_glossary_sidebar
        # Pass 6 valid keys but max_terms=2
        render_glossary_sidebar(
            keys=["compound_interest", "fv", "pv", "inflation", "beta", "alpha"],
            max_terms=2,
        )
        # The sidebar expander should be called once (terms are shown inside)
        mock_st.sidebar.expander.assert_called_once()
