from __future__ import annotations

import json
from typing import List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES_RW = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_service(google_credentials_json: str | None, google_credentials_path: str | None):
    if google_credentials_json:
        info = json.loads(google_credentials_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES_RW)
    elif google_credentials_path:
        creds = service_account.Credentials.from_service_account_file(google_credentials_path, scopes=SCOPES_RW)
    else:
        raise RuntimeError("Google credentials not provided")
    return build('sheets', 'v4', credentials=creds)


def read_header_row(service, spreadsheet_id: str, tab_name: str) -> List[str]:
    range_name = f"{tab_name}!1:1"
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    return values[0] if values else []


def append_rows(service, spreadsheet_id: str, tab_name: str, rows: List[List[str]]):
    range_name = f"{tab_name}!A:A"
    body = {"values": rows}
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()


