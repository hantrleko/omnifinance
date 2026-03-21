"""Export utilities for OmniFinance: Excel (.xlsx) export helpers.

Usage example::

    from core.export import dataframes_to_excel

    xlsx_bytes = dataframes_to_excel(
        sheets=[
            ("逐年明细", df_yearly),
            ("敏感度分析", df_sensitivity),
        ],
        title="退休金估算报告",
    )
    st.download_button("📥 下载 Excel", data=xlsx_bytes, file_name="report.xlsx", ...)
"""

from __future__ import annotations

import io
from typing import Sequence

import pandas as pd


def dataframes_to_excel(
    sheets: Sequence[tuple[str, pd.DataFrame]],
    title: str = "",
) -> bytes:
    """Serialise one or more DataFrames into a multi-sheet Excel workbook.

    Args:
        sheets: Ordered list of ``(sheet_name, dataframe)`` pairs.  Sheet
            names are truncated to 31 characters (Excel limit).
        title: Optional workbook title stored in document properties.
            Currently embedded as a comment row on the first sheet.

    Returns:
        Raw bytes of the ``.xlsx`` file, suitable for passing directly to
        ``st.download_button(data=...)``.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:  # type: ignore[abstract]
        for sheet_name, df in sheets:
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)

        # Inject title into the top-left cell of the first sheet via openpyxl.
        # We do this after all DataFrames are written so writer.sheets is populated.
        if title and writer.sheets:
            first_ws = next(iter(writer.sheets.values()))
            first_ws.insert_rows(1)
            first_ws.cell(row=1, column=1).value = title

    return buf.getvalue()
