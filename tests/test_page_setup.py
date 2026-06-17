"""Unit tests for core.page_setup.init_page.

Because init_page calls Streamlit APIs, we mock the three underlying
functions it delegates to and verify they are called with the correct
arguments.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


class TestInitPage:
    """Tests that init_page calls the right functions with the right args."""

    def _run(self, title: str, icon: str, key: str, layout: str = "wide"):
        """Helper: patch all three dependencies and call init_page."""
        with (
            patch("streamlit.set_page_config") as mock_config,
            patch("core.theme.inject_theme") as mock_theme,
            patch("core.navigation.track_recent_page") as mock_track,
        ):
            # We need to re-import inside the patch context so the module
            # picks up the mocked versions.
            import importlib
            import core.page_setup as ps
            importlib.reload(ps)

            # Provide a fake session_state
            fake_state: dict = {}
            with patch("streamlit.session_state", fake_state):
                ps.init_page(title, icon, key, layout=layout)

            return mock_config, mock_theme, mock_track

    def test_set_page_config_called(self):
        mock_config, _, _ = self._run("Test Page", "🔥", "test")
        mock_config.assert_called_once_with(
            page_title="Test Page", page_icon="🔥", layout="wide"
        )

    def test_inject_theme_called(self):
        _, mock_theme, _ = self._run("Test Page", "🔥", "test")
        mock_theme.assert_called_once()

    def test_track_recent_page_called(self):
        _, _, mock_track = self._run("Test Page", "🔥", "test_key")
        # track_recent_page receives (session_state, page_key)
        assert mock_track.call_count == 1
        _, page_key = mock_track.call_args[0]
        assert page_key == "test_key"

    def test_custom_layout(self):
        mock_config, _, _ = self._run("Centered", "📄", "c", layout="centered")
        mock_config.assert_called_once_with(
            page_title="Centered", page_icon="📄", layout="centered"
        )

    def test_default_layout_is_wide(self):
        mock_config, _, _ = self._run("Wide", "📊", "w")
        _, kwargs = mock_config.call_args
        assert kwargs.get("layout") == "wide"
