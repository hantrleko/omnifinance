"""Unified page initialisation helper for OmniFinance.

Every Streamlit page in ``pages/`` should call :func:`init_page` as the
**very first** statement after its module-level docstring.  This replaces
the three-line boilerplate that was previously copy-pasted into every page::

    from core.navigation import track_recent_page
    track_recent_page(st.session_state, 'page_key')
    from core.theme import inject_theme
    inject_theme()
    st.set_page_config(page_title="...", page_icon="...", layout="wide")

Usage example::

    import streamlit as st
    from core.page_setup import init_page
    init_page("复利计算器", "📈", "compound")

Design notes
------------
- ``st.set_page_config`` **must** be the first Streamlit call in a script.
  ``init_page`` therefore calls it before ``inject_theme`` and
  ``track_recent_page`` so that the order is always correct.
- The function is intentionally thin: it delegates to the existing
  ``core/theme.py`` and ``core/navigation.py`` modules, keeping each
  module's responsibility clear.
- Passing ``layout`` as a parameter allows the rare page that needs
  ``"centered"`` layout to opt out of the default ``"wide"`` setting.
"""
from __future__ import annotations

import streamlit as st

from core.navigation import track_recent_page
from core.theme import inject_theme


def init_page(
    title: str,
    icon: str,
    page_key: str,
    *,
    layout: str = "wide",
) -> None:
    """Initialise a Streamlit page with the standard OmniFinance setup.

    This function consolidates the three repeated setup steps that every
    page previously performed manually:

    1. ``st.set_page_config`` — sets the browser tab title, favicon, and
       layout mode.  **Must be called before any other Streamlit command.**
    2. :func:`core.theme.inject_theme` — injects the shared CSS (dark/light
       mode, glassmorphism cards, hover animations, etc.).
    3. :func:`core.navigation.track_recent_page` — records the current page
       in ``st.session_state`` so the sidebar "Recently Visited" widget can
       surface it.

    Args:
        title:    Human-readable page title shown in the browser tab and
                  used by Streamlit's built-in page navigation.
        icon:     Emoji or Material icon string used as the page favicon.
        page_key: Short stable key that identifies this page within the
                  navigation registry (e.g. ``"compound"``, ``"loan"``).
        layout:   Streamlit layout mode — ``"wide"`` (default) or
                  ``"centered"``.

    Example::

        import streamlit as st
        from core.page_setup import init_page

        init_page("复利计算器", "📈", "compound")
        st.title("📈 复利计算器")
    """
    st.set_page_config(page_title=title, page_icon=icon, layout=layout)
    inject_theme()
    track_recent_page(st.session_state, page_key)
