from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import polars as pl


class CornerLogisTransformer:
    def __init__(self, template_path: Path | None = None) -> None:
        self.template_path = template_path

    def read_shopby_excel(self, xlsx_path: Path) -> pl.DataFrame:
        return pl.read_excel(str(xlsx_path))

    def apply_sku_mapping(self, df: pl.DataFrame, mapping: Dict[str, str], sku_column: str) -> pl.DataFrame:
        if sku_column not in df.columns:
            return df
        return df.with_columns(
            pl.col(sku_column).map_elements(lambda v: mapping.get(str(v), v)).alias(sku_column)
        )

    def transform_to_cornerlogis(self, df: pl.DataFrame, column_mapping: List[Tuple[str, str]]) -> pl.DataFrame:
        # column_mapping: list of tuples (source_col, target_col)
        data = {}
        for src, tgt in column_mapping:
            data[tgt] = df.get_column(src) if src in df.columns else pl.lit(None)
        out = pl.DataFrame(data)
        return out

    def save_excel(self, df: pl.DataFrame, path: Path) -> None:
        try:
            df.write_excel(str(path))
        except Exception:
            # Fallback via pandas if polars write_excel is not available in installed version
            import pandas as pd
            pd_df = df.to_pandas()
            pd_df.to_excel(str(path), index=False)

    def transform_using_template_headers(self, df: pl.DataFrame, template_path: Path) -> pl.DataFrame:
        """
        Reads the template header row and creates an output DataFrame that matches
        the template's column order. If a template column exists in input df, copy it;
        otherwise fill with nulls.
        """
        try:
            template_df = pl.read_excel(str(template_path), n_rows=0)
            template_cols = template_df.columns
        except Exception:
            # Fallback: read headers via pandas
            import pandas as pd
            template_pd = pd.read_excel(str(template_path), nrows=0)
            template_cols = list(template_pd.columns)
        data = {}
        for col in template_cols:
            data[col] = df.get_column(col) if col in df.columns else pl.lit(None)
        return pl.DataFrame(data)

    def transform_with_mapping(self, df: pl.DataFrame, mapping: Dict[str, str], template_headers: List[str] | None = None) -> pl.DataFrame:
        """
        mapping: dict of {source_col_name: target_col_name}
        If template_headers is provided, output columns will follow that order; otherwise use mapped target order.
        Unmapped target columns become null; identity columns (same name) are auto-carried.
        """
        # Build reverse map: target -> source(s)
        target_to_source: Dict[str, str] = {}
        for src, tgt in mapping.items():
            if src in df.columns:
                target_to_source[tgt] = src

        # Auto map identity columns
        for col in df.columns:
            if col not in target_to_source and (template_headers is None or col in template_headers):
                target_to_source[col] = col

        out_cols = template_headers if template_headers else list(target_to_source.keys())
        data = {}
        for tgt in out_cols:
            src = target_to_source.get(tgt)
            data[tgt] = df.get_column(src) if src in df.columns else pl.lit(None)
        return pl.DataFrame(data)


