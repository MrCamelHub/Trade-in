from __future__ import annotations

from typing import Dict, List
from pathlib import Path

import polars as pl

from .google_sheets_utils import get_sheets_service, read_header_row, append_rows
from .config import AppConfig


THIRD_SHEET_ID = "1pXOIiSCXpEOUHQUgl_4FUDltRG9RYq0_cadJX4Cre1o"
THIRD_SHEET_TAB = "시트1"


def dataframe_to_sheet_rows(df: pl.DataFrame, headers: List[str], mapping: Dict[str, str] | None = None) -> List[List[str]]:
    """
    Convert polars DataFrame to rows matching provided header order.
    mapping: optional dict {sheet_header: df_column_name}
    If a sheet header has no mapping and same-named df column exists, use it; else blank.
    """
    rows: List[List[str]] = []
    if mapping is None:
        mapping = {}

    # Build per-header source column name
    source_for_header: Dict[str, str] = {}
    for h in headers:
        if h in mapping:
            source_for_header[h] = mapping[h]
        elif h in df.columns:
            source_for_header[h] = h
        else:
            source_for_header[h] = None  # blank

    for i in range(df.height):
        row_vals: List[str] = []
        for h in headers:
            src = source_for_header[h]
            if src and src in df.columns:
                val = df[src][i]
                row_vals.append("" if val is None else str(val))
            else:
                row_vals.append("")
        rows.append(row_vals)
    return rows


def post_subset_to_third_sheet(config: AppConfig, df: pl.DataFrame, mapping: Dict[str, str] | None = None) -> None:
    service = get_sheets_service(
        google_credentials_json=config.google_credentials_json,
        google_credentials_path=str(config.google_credentials_path) if config.google_credentials_path else None,
    )
    headers = read_header_row(service, THIRD_SHEET_ID, THIRD_SHEET_TAB)
    rows = dataframe_to_sheet_rows(df, headers, mapping)
    append_rows(service, THIRD_SHEET_ID, THIRD_SHEET_TAB, rows)


