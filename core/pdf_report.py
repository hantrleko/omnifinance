"""PDF report generation utility.

Wraps the HTML report generator with optional PDF conversion using
weasyprint (if available) or falls back to HTML-only output.
"""

from __future__ import annotations

from typing import Any

from core.report_generator import generate_html_report, build_single_report


def generate_pdf_report(metrics_dict: dict[str, Any]) -> bytes | None:
    """Generate a PDF report from dashboard metrics.

    Uses weasyprint to convert the HTML report to PDF.
    Returns None if weasyprint is not available.

    Args:
        metrics_dict: Dashboard metrics dictionary.

    Returns:
        PDF bytes if weasyprint is available, else None.
    """
    html_content = generate_html_report(metrics_dict)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except ImportError:
        return None
    except Exception:
        return None


def generate_single_pdf(title: str, subtitle: str, body_html: str) -> bytes | None:
    """Generate a PDF from a single-page report.

    Args:
        title: Report title.
        subtitle: Report subtitle.
        body_html: Inner HTML content.

    Returns:
        PDF bytes if weasyprint is available, else None.
    """
    html_content = build_single_report(title, subtitle, body_html)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except ImportError:
        return None
    except Exception:
        return None


def is_pdf_available() -> bool:
    """Check if PDF generation is available (weasyprint installed)."""
    try:
        import weasyprint  # noqa: F401
        return True
    except ImportError:
        return False
