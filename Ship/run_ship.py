from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytz
import holidays
import polars as pl

from .config import load_app_config, ensure_data_dirs
from .shopby_downloader import download_latest_excel
from .transformer import CornerLogisTransformer
from .mapping import load_sku_mapping
from .cornerlogis_uploader import upload_file
from .post_to_third_sheet import post_subset_to_third_sheet
from .column_mapping_loader import load_header_rows, build_cornerlogis_mapping, build_sheet1_mapping
from .drive_uploader import upload_to_drive


async def run_once() -> Path:
    config = load_app_config()
    ensure_data_dirs(config.data_dir)

    # 1) Download Shopby orders
    shopby_xlsx = await download_latest_excel(config)

    # 2) Load SKU mapping from Google Sheets
    sku_mapping = load_sku_mapping(
        spreadsheet_id=config.mapping.spreadsheet_id,
        tab_name=config.mapping.tab_name,
        google_credentials_json=config.google_credentials_json,
        google_credentials_path=str(config.google_credentials_path) if config.google_credentials_path else None,
    )

    # 3) Transform with polars
    transformer = CornerLogisTransformer()
    df = transformer.read_shopby_excel(shopby_xlsx)

    # Apply SKU mapping: try common SKU column names (코너로지스상품코드 생성용)
    sku_col_used = None
    for sku_col_candidate in ["SKU", "상품코드", "상품번호", "옵션코드"]:
        if sku_col_candidate in df.columns:
            df = transformer.apply_sku_mapping(df, sku_mapping, sku_col_candidate)
            sku_col_used = sku_col_candidate
            break

    # Ensure template-required column '코너로지스상품코드' exists, copied from sku_col_used
    if sku_col_used and "코너로지스상품코드" not in df.columns:
        df = df.with_columns(pl.col(sku_col_used).alias("코너로지스상품코드"))

    # Build a column mapping to CornerLogis format using header file
    headers_path = Path("/Users/mac/Bonibello/Ship/컬럼맵핑.csv")
    column_mapping = []
    sheet1_mapping_pairs = []
    if headers_path.exists():
        header_rows = load_header_rows(headers_path)
        column_mapping = build_cornerlogis_mapping(header_rows.get('shopby', []), header_rows.get('cornerlogis', []))
        sheet1_mapping_pairs = build_sheet1_mapping(header_rows.get('shopby', []), header_rows.get('sheet1', []))

    # If a CornerLogis template file path was provided in requiredinfo, prefer matching its headers
    template_hint = None
    # Try to read hint from requiredinfo by path mentioned in text
    # User provided a local template path; best-effort use if exists
    for hint_path in [
        "/Users/mac/Bonibello/Ship/cornerlogis_outbound_template_202411 (1).xlsx",
    ]:
        p = Path(hint_path)
        if p.exists():
            template_hint = p
            break

    if template_hint:
        # Use template header order, but move/match via explicit mapping first to harmonize names
        if column_mapping:
            # Convert mapping list -> dict for transform_with_mapping
            mapping_dict = {src: tgt for src, tgt in column_mapping}
            # Read template headers to enforce order
            out_df_pre = transformer.transform_with_mapping(df, mapping_dict)
            out_df = transformer.transform_using_template_headers(out_df_pre, template_hint)
        else:
            out_df = transformer.transform_using_template_headers(df, template_hint)
    else:
        out_df = df if not column_mapping else transformer.transform_to_cornerlogis(df, column_mapping)

    # 4) Save to outputs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = config.data_dir / "outputs" / f"cornerlogis_outbound_{timestamp}.xlsx"
    transformer.save_excel(out_df, out_path)

    # 4.5) Post subset of data to third Google Sheet (시트1)
    # Build mapping dict: {sheet_header: df_column}
    mapping_dict_sheet1 = {tgt: src for (src, tgt) in sheet1_mapping_pairs}
    post_subset_to_third_sheet(config, df, mapping_dict_sheet1)

    # 5) Upload to CornerLogis
    await upload_file(config, out_path)

    # 6) Upload artifact to Google Drive folder
    # Provided link: https://drive.google.com/open?id=1CFmpTRJ0XdwFXPMz9T0RLtfj4-4PGlwA&usp=drive_fs
    drive_folder_id = "1CFmpTRJ0XdwFXPMz9T0RLtfj4-4PGlwA"
    upload_to_drive(
        google_credentials_json=config.google_credentials_json,
        google_credentials_path=str(config.google_credentials_path) if config.google_credentials_path else None,
        folder_id=drive_folder_id,
        file_path=out_path,
    )

    return out_path


def should_run_now_kst() -> bool:
    config = load_app_config()
    kst = pytz.timezone(config.timezone)
    now = datetime.now(kst)
    if now.weekday() >= 5:
        return False
    # 한국 공휴일 제외
    kr_holidays = holidays.KR(years=now.year)
    if now.date() in kr_holidays:
        return False
    if now.hour == 13:  # 13:00 KST
        # TODO: Add KR holiday check if necessary using holidays package or calendar API
        return True
    return False


async def main():
    # For now, just run once. Scheduler can be added later or use Railway cron.
    await run_once()


if __name__ == "__main__":
    asyncio.run(main())


