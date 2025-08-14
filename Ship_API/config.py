from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ShopbyApiConfig:
    """샵바이 API 설정"""
    base_url: str = "https://server-api.e-ncp.com"
    system_key: str = "b1hLbVFoS1lUeUZIM0QrZTNuNklUQT09"
    auth_token: str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwYXJ0bmVyTm8iOjEyNzk1OSwiYWRtaW5ObyI6MjE5NjI0LCJhY2Nlc3NpYmxlSXBzIjpbXSwidXNhZ2UiOiJTRVJWRVIiLCJhZG1pbklkIjoiam9zZXBoIiwiaXNzIjoiTkhOIENvbW1lcmNlIiwiYXBwTm8iOjE0ODksIm1hbGxObyI6Nzg1MjIsInNvbHV0aW9uVHlwZSI6IlNIT1BCWSIsImV4cCI6NDkwODU2MzAwMiwic2hvcE5vIjoxMDAzNzY1LCJpYXQiOjE3NTQ5NjMwMDJ9.rEYIdHOb68Pr4N47aRRPI4bdjuW4KAg_bqUDyoF49Zc"
    version: str = "1.1"


@dataclass
class CornerlogisApiConfig:
    """코너로지스 API 설정"""
    base_url: str = "https://devapi.cornerlogis.com"
    # Authorization 헤더에 들어갈 API 키
    api_key: Optional[str] = None


@dataclass
class MappingSheetConfig:
    """SKU 매핑 시트 설정"""
    spreadsheet_id: str = "1G7evb2MyxG8IBtOBn9pFmtTEyZ0uTeLZpp37XF4ntsU"
    tab_name: str = "📍위탁수거 상품정보"


@dataclass
class LoggingSheetConfig:
    """구글 시트 로깅 설정 (상품 로그)"""
    spreadsheet_id: str = "1pXOIiSCXpEOUHQUgl_4FUDltRG9RYq0_cadJX4Cre1o"
    tab_name: str = "Sheet1"


@dataclass
class AppConfig:
    """전체 앱 설정"""
    shopby: ShopbyApiConfig
    cornerlogis: CornerlogisApiConfig
    mapping: MappingSheetConfig
    logging: LoggingSheetConfig
    data_dir: Path
    google_credentials_json: Optional[str] = None
    google_credentials_path: Optional[Path] = None
    timezone: str = "Asia/Seoul"
    exclude_holidays: bool = True


def load_app_config() -> AppConfig:
    """환경변수와 기본값을 사용해 앱 설정 로드"""
    
    # 데이터 디렉토리 설정 (Railway에서는 /tmp 사용)
    if os.getenv("RAILWAY_ENVIRONMENT"):
        data_dir = Path("/tmp/ship_api")
    else:
        data_dir = Path(__file__).parent / "data"
    
    # 샵바이 API 설정 (환경변수로 오버라이드 가능)
    shopby = ShopbyApiConfig(
        base_url=os.getenv("SHOPBY_API_BASE_URL", "https://server-api.e-ncp.com"),
        system_key=os.getenv("SHOPBY_SYSTEM_KEY", "b1hLbVFoS1lUeUZIM0QrZTNuNklUQT09"),
        auth_token=os.getenv("SHOPBY_AUTH_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwYXJ0bmVyTm8iOjEyNzk1OSwiYWRtaW5ObyI6MjE5NjI0LCJhY2Nlc3NpYmxlSXBzIjpbXSwidXNhZ2UiOiJTRVJWRVIiLCJhZG1pbklkIjoiam9zZXBoIiwiaXNzIjoiTkhOIENvbW1lcmNlIiwiYXBwTm8iOjE0ODksIm1hbGxObyI6Nzg1MjIsInNvbHV0aW9uVHlwZSI6IlNIT1BCWSIsImV4cCI6NDkwODU2MzAwMiwic2hvcE5vIjoxMDAzNzY1LCJpYXQiOjE3NTQ5NjMwMDJ9.rEYIdHOb68Pr4N47aRRPI4bdjuW4KAg_bqUDyoF49Zc"),
        version=os.getenv("SHOPBY_API_VERSION", "1.1")
    )
    
    # 코너로지스 API 설정
    cornerlogis = CornerlogisApiConfig(
        base_url=os.getenv("CORNERLOGIS_API_BASE_URL", "https://devapi.cornerlogis.com"),
        api_key=os.getenv("CORNERLOGIS_API_KEY")
    )
    
    # 매핑 시트 설정
    mapping = MappingSheetConfig(
        spreadsheet_id=os.getenv("MAPPING_SPREADSHEET_ID", "1G7evb2MyxG8IBtOBn9pFmtTEyZ0uTeLZpp37XF4ntsU"),
        tab_name=os.getenv("MAPPING_TAB_NAME", "📍위탁수거 상품정보")
    )
    
    # 로깅 시트 설정
    logging_cfg = LoggingSheetConfig(
        spreadsheet_id=os.getenv("LOGGING_SPREADSHEET_ID", "1pXOIiSCXpEOUHQUgl_4FUDltRG9RYq0_cadJX4Cre1o"),
        tab_name=os.getenv("LOGGING_TAB_NAME", "Sheet1")
    )
    
    # Google 인증 설정
    google_credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    google_credentials_path_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH")
    google_credentials_path = Path(google_credentials_path_str) if google_credentials_path_str else None
    
    # 프로젝트 루트에서 Google 인증 파일 찾기
    if not google_credentials_json and (not google_credentials_path or not google_credentials_path.exists()):
        project_root = Path(__file__).parent.parent
        candidate = next((p for p in project_root.glob("*.json") if "youtube-crawling" in p.name), None)
        if candidate and candidate.exists():
            google_credentials_path = candidate
    
    return AppConfig(
        shopby=shopby,
        cornerlogis=cornerlogis,
        mapping=mapping,
        logging=logging_cfg,
        data_dir=data_dir,
        google_credentials_json=google_credentials_json,
        google_credentials_path=google_credentials_path,
        timezone=os.getenv("TIMEZONE", "Asia/Seoul"),
        exclude_holidays=os.getenv("EXCLUDE_HOLIDAYS", "true").lower() == "true"
    )


def ensure_data_dirs(data_dir: Path) -> None:
    """데이터 디렉토리 생성"""
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "downloads").mkdir(exist_ok=True)
    (data_dir / "outputs").mkdir(exist_ok=True)
    (data_dir / "logs").mkdir(exist_ok=True)
