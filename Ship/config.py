from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_DATA_DIR = PROJECT_ROOT / "Ship" / "data"
DEFAULT_RUNTIME_DATA_DIR = Path(os.environ.get("SHIP_RUNTIME_DIR", str(DEFAULT_LOCAL_DATA_DIR)))


@dataclass
class ShopbyConfig:
    login_url: str
    orders_url: str
    username: str
    password: str
    export_button_xpath: str


@dataclass
class CornerLogisConfig:
    portal_url: str
    username: str
    password: str
    file_input_xpath: str
    upload_button_xpath: str


@dataclass
class MappingSheetConfig:
    spreadsheet_id: str
    tab_name: str


@dataclass
class AppConfig:
    data_dir: Path
    timezone: str
    exclude_kr_holidays: bool
    keep_artifacts: bool
    # Google credentials: supports either JSON string in env or path to json file
    google_credentials_json: Optional[str]
    google_credentials_path: Optional[Path]
    # Sub-configs
    shopby: ShopbyConfig
    cornerlogis: CornerLogisConfig
    mapping: MappingSheetConfig


def _read_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is not None:
        return value
    return default


def load_config_from_required_info(required_info_path: Path) -> AppConfig:
    """Parses the provided requiredinfo.txt and builds an AppConfig.

    Notes:
      - Secrets in this file are for local use only. In production, prefer env vars.
    """
    text = required_info_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]

    def _extract(prefix: str, sep: str = "=") -> Optional[str]:
        for line in lines:
            if prefix in line:
                # take substring after sep
                try:
                    return line.split(sep, 1)[1].strip()
                except Exception:
                    continue
        return None

    # Shopby
    shopby_login_url = _extract("로그인 URL") or "https://accounts.nhn-commerce.com/login"
    shopby_orders_url = _extract("주문목록 페이지 URL") or "https://service.shopby.co.kr/order/list/pay-done"
    # Credentials
    # Line like: "아이디/비번만인가요?... rehiresale / Rehi2025!@"
    shopby_creds = _extract("아이디/비번만") or _extract("로그인 방식") or ""
    if "/" in shopby_creds:
        parts = [p.strip() for p in shopby_creds.split("/")]
        shopby_username = parts[0]
        shopby_password = parts[1] if len(parts) > 1 else ""
    else:
        shopby_username = _extract("샵바이 아이디") or ""
        shopby_password = _extract("샵바이 비번") or ""

    export_xpath = _extract("엑셀 내보내기 경로/버튼") or _extract("XPATH") or "//*[@id=\"root\"]/div[2]/section/div/div[1]/div[1]/div[2]/span[4]/button"

    shopby = ShopbyConfig(
        login_url=shopby_login_url,
        orders_url=shopby_orders_url,
        username=shopby_username,
        password=shopby_password,
        export_button_xpath=export_xpath,
    )

    # CornerLogis
    corner_url = _extract("포털 주소") or "https://admin.cornerlogis.com/"
    corner_id = _extract("아이디/비번") or ""
    if "/" in corner_id:
        parts = [p.strip() for p in corner_id.split("/")]
        corner_username = parts[0]
        corner_password = parts[1] if len(parts) > 1 else ""
    else:
        corner_username = _extract("코너로지스 아이디") or ""
        corner_password = _extract("코너로지스 비번") or ""

    file_input_xpath = _extract("파일찾기") or "//*[@id=\"excelFile\"]"
    upload_button_xpath = _extract("업로드") or "//*[@id=\"btn_upload\"]"

    cornerlogis = CornerLogisConfig(
        portal_url=corner_url,
        username=corner_username,
        password=corner_password,
        file_input_xpath=file_input_xpath,
        upload_button_xpath=upload_button_xpath,
    )

    # Mapping sheet
    spreadsheet_id = _extract("SPREADSHEET_ID") or _extract("매핑 시트 SPREADSHEET_ID")
    if not spreadsheet_id:
        # The line in the file seems to contain id and tab name in one line
        raw = _extract("매핑 시트 SPREADSHEET_ID와 탭 이름") or ""
        # split by comma
        if "," in raw:
            spreadsheet_id = raw.split(",", 1)[0].strip()
    tab_name = _extract("탭이름") or "📍위탁수거 상품정보"
    mapping = MappingSheetConfig(spreadsheet_id=spreadsheet_id or "", tab_name=tab_name)

    # App level
    data_dir = DEFAULT_RUNTIME_DATA_DIR
    tz = "Asia/Seoul"
    exclude_holidays = True
    keep_artifacts = True

    # Google credentials: env first
    google_json_env = _read_env("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    google_json_path_str = _extract("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    google_json_path = Path(google_json_path_str) if google_json_path_str else None
    # Fallback: probe common credential file in project root
    if not google_json_env and (google_json_path is None or not google_json_path.exists()):
        candidate = next((p for p in PROJECT_ROOT.glob("*.json") if "youtube-crawling" in p.name), None)
        if candidate:
            google_json_path = candidate

    return AppConfig(
        data_dir=data_dir,
        timezone=tz,
        exclude_kr_holidays=exclude_holidays,
        keep_artifacts=keep_artifacts,
        google_credentials_json=google_json_env,
        google_credentials_path=google_json_path,
        shopby=shopby,
        cornerlogis=cornerlogis,
        mapping=mapping,
    )


def ensure_data_dirs(base: Path) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    (base / "downloads").mkdir(parents=True, exist_ok=True)
    (base / "outputs").mkdir(parents=True, exist_ok=True)
    (base / "logs").mkdir(parents=True, exist_ok=True)
    return base


def load_app_config() -> AppConfig:
    required_info_path = PROJECT_ROOT / "Ship" / "requiredinfo.txt"
    return load_config_from_required_info(required_info_path)


