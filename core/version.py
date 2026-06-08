"""Single source of truth for the OmniFinance version number.

Bump :data:`__version__` here whenever a new release is cut; all other
modules should import from this file rather than redefining the constant.
"""

from __future__ import annotations

__all__ = ["__version__", "VERSION"]

__version__: str = "2.1.0"

# Convenience alias used in user-facing UI strings (e.g. ``f"OmniFinance {VERSION}"``).
VERSION: str = f"v{__version__}"
