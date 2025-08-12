from __future__ import annotations

import json
from typing import Dict

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _get_credentials(google_credentials_json: str | None, google_credentials_path: str | None):
    if google_credentials_json:
        info = json.loads(google_credentials_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    if google_credentials_path:
        return service_account.Credentials.from_service_account_file(google_credentials_path, scopes=SCOPES)
    raise RuntimeError("Google credentials not provided")


def load_sku_mapping(spreadsheet_id: str, tab_name: str, google_credentials_json: str | None, google_credentials_path: str | None) -> Dict[str, str]:
    credentials = _get_credentials(google_credentials_json, google_credentials_path)
    service = build('sheets', 'v4', credentials=credentials)
    # Assuming columns: J (SHOPBY_SKU) and I (GROUP) per required info
    # We will read a wider range and compute mapping from J to I
    range_name = f"{tab_name}!A:K"
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    mapping: Dict[str, str] = {}
    for row in values:
        j_val = row[9] if len(row) > 9 else None  # J index 9
        i_val = row[8] if len(row) > 8 else None  # I index 8
        if j_val:
            # If target is empty, keep source per policy
            mapping[str(j_val)] = str(i_val) if i_val else str(j_val)
    return mapping


