from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]


def _get_drive_service(google_credentials_json: str | None, google_credentials_path: str | None):
    if google_credentials_json:
        info = json.loads(google_credentials_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif google_credentials_path:
        creds = service_account.Credentials.from_service_account_file(google_credentials_path, scopes=SCOPES)
    else:
        raise RuntimeError("Google credentials not provided for Drive API")
    return build('drive', 'v3', credentials=creds)


def upload_to_drive(google_credentials_json: str | None, google_credentials_path: str | None, folder_id: str, file_path: Path) -> str:
    service = _get_drive_service(google_credentials_json, google_credentials_path)
    media = MediaFileUpload(str(file_path), resumable=True)
    file_metadata = {
        'name': file_path.name,
        'parents': [folder_id],
    }
    created = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return created['id']


