from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


def load_sku_mapping_from_sheets(
    spreadsheet_id: str,
    tab_name: str,
    google_credentials_json: Optional[str] = None,
    google_credentials_path: Optional[str] = None,
    shopby_sku_col: str = "J",
    cornerlogis_sku_col: str = "I"
) -> Dict[str, str]:
    """
    Google Sheets에서 SKU 매핑 로드
    
    Args:
        spreadsheet_id: Google Sheets ID
        tab_name: 시트 탭 이름
        google_credentials_json: Google 인증 JSON (환경변수)
        google_credentials_path: Google 인증 파일 경로
        shopby_sku_col: 샵바이 SKU 컬럼 (기본: J열)
        cornerlogis_sku_col: 코너로지스 SKU 컬럼 (기본: I열)
    
    Returns:
        {shopby_sku: cornerlogis_sku} 매핑 딕셔너리
    """
    try:
        # Google 인증 설정
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        
        if google_credentials_json:
            # 환경변수에서 JSON 직접 로드
            creds_info = json.loads(google_credentials_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        elif google_credentials_path and Path(google_credentials_path).exists():
            # 파일에서 인증 정보 로드
            creds = Credentials.from_service_account_file(google_credentials_path, scopes=scopes)
        else:
            print("Google 인증 정보를 찾을 수 없습니다")
            return {}
        
        # Google Sheets API 서비스 생성
        service = build('sheets', 'v4', credentials=creds)
        
        # 시트 데이터 조회
        range_name = f"{tab_name}!{shopby_sku_col}:{cornerlogis_sku_col}"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # SKU 매핑 딕셔너리 생성
        sku_mapping = {}
        
        for i, row in enumerate(values):
            if len(row) >= 2 and i > 0:  # 헤더 행 건너뛰기
                shopby_sku = str(row[0]).strip() if row[0] else ""
                cornerlogis_sku = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                
                if shopby_sku and cornerlogis_sku:
                    sku_mapping[shopby_sku] = cornerlogis_sku
        
        print(f"SKU 매핑 로드 완료: {len(sku_mapping)}개 항목")
        return sku_mapping
        
    except Exception as e:
        print(f"SKU 매핑 로드 실패: {e}")
        return {}


def load_sku_mapping_from_csv(
    csv_path: Path,
    shopby_sku_col: str = "SKU",
    cornerlogis_sku_col: str = "그룹"
) -> Dict[str, str]:
    """
    CSV 파일에서 SKU 매핑 로드
    
    Args:
        csv_path: CSV 파일 경로
        shopby_sku_col: 샵바이 SKU 컬럼명
        cornerlogis_sku_col: 코너로지스 SKU 컬럼명
    
    Returns:
        {shopby_sku: cornerlogis_sku} 매핑 딕셔너리
    """
    try:
        if not csv_path.exists():
            print(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
            return {}
        
        df = pd.read_csv(csv_path)
        
        # 컬럼 존재 확인
        if shopby_sku_col not in df.columns or cornerlogis_sku_col not in df.columns:
            print(f"필요한 컬럼을 찾을 수 없습니다: {shopby_sku_col}, {cornerlogis_sku_col}")
            print(f"사용 가능한 컬럼: {list(df.columns)}")
            return {}
        
        # SKU 매핑 딕셔너리 생성
        sku_mapping = {}
        
        for _, row in df.iterrows():
            shopby_sku = str(row[shopby_sku_col]).strip() if pd.notna(row[shopby_sku_col]) else ""
            cornerlogis_sku = str(row[cornerlogis_sku_col]).strip() if pd.notna(row[cornerlogis_sku_col]) else ""
            
            if shopby_sku and cornerlogis_sku:
                sku_mapping[shopby_sku] = cornerlogis_sku
        
        print(f"CSV SKU 매핑 로드 완료: {len(sku_mapping)}개 항목")
        return sku_mapping
        
    except Exception as e:
        print(f"CSV SKU 매핑 로드 실패: {e}")
        return {}


def get_sku_mapping(config) -> Dict[str, str]:
    """
    설정에 따라 적절한 방법으로 SKU 매핑 로드
    
    Args:
        config: 앱 설정 객체
    
    Returns:
        SKU 매핑 딕셔너리
    """
    # 먼저 Google Sheets에서 시도
    if config.mapping.spreadsheet_id:
        mapping = load_sku_mapping_from_sheets(
            spreadsheet_id=config.mapping.spreadsheet_id,
            tab_name=config.mapping.tab_name,
            google_credentials_json=config.google_credentials_json,
            google_credentials_path=str(config.google_credentials_path) if config.google_credentials_path else None
        )
        if mapping:
            return mapping
    
    # Google Sheets 실패시 로컬 CSV 파일에서 시도
    csv_paths = [
        config.data_dir / "sku_mapping.csv",
        Path(__file__).parent.parent / "Ship" / "컬럼맵핑.csv",
        Path(__file__).parent / "sku_mapping.csv"
    ]
    
    for csv_path in csv_paths:
        if csv_path.exists():
            mapping = load_sku_mapping_from_csv(csv_path)
            if mapping:
                return mapping
    
    print("SKU 매핑을 로드할 수 없습니다. 빈 매핑을 사용합니다.")
    return {}


def save_sku_mapping_to_csv(
    sku_mapping: Dict[str, str],
    csv_path: Path,
    shopby_sku_col: str = "SKU",
    cornerlogis_sku_col: str = "그룹"
) -> None:
    """
    SKU 매핑을 CSV 파일로 저장
    
    Args:
        sku_mapping: SKU 매핑 딕셔너리
        csv_path: 저장할 CSV 파일 경로
        shopby_sku_col: 샵바이 SKU 컬럼명
        cornerlogis_sku_col: 코너로지스 SKU 컬럼명
    """
    try:
        df = pd.DataFrame(list(sku_mapping.items()), columns=[shopby_sku_col, cornerlogis_sku_col])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"SKU 매핑 저장 완료: {csv_path}")
    except Exception as e:
        print(f"SKU 매핑 저장 실패: {e}")


def validate_sku_mapping(sku_mapping: Dict[str, str]) -> Dict[str, any]:
    """
    SKU 매핑 유효성 검사
    
    Args:
        sku_mapping: SKU 매핑 딕셔너리
    
    Returns:
        검사 결과 딕셔너리
    """
    result = {
        "total_mappings": len(sku_mapping),
        "empty_shopby_skus": [],
        "empty_cornerlogis_skus": [],
        "duplicate_shopby_skus": [],
        "duplicate_cornerlogis_skus": []
    }
    
    # 빈 값 검사
    for shopby_sku, cornerlogis_sku in sku_mapping.items():
        if not shopby_sku.strip():
            result["empty_shopby_skus"].append(shopby_sku)
        if not cornerlogis_sku.strip():
            result["empty_cornerlogis_skus"].append(shopby_sku)
    
    # 중복 검사
    shopby_values = list(sku_mapping.keys())
    cornerlogis_values = list(sku_mapping.values())
    
    for sku in set(shopby_values):
        if shopby_values.count(sku) > 1:
            result["duplicate_shopby_skus"].append(sku)
    
    for sku in set(cornerlogis_values):
        if cornerlogis_values.count(sku) > 1:
            result["duplicate_cornerlogis_skus"].append(sku)
    
    return result


# 테스트 함수
def test_sku_mapping():
    """SKU 매핑 기능 테스트"""
    from .config import load_app_config
    
    print("SKU 매핑 테스트 시작...")
    
    # 설정 로드
    config = load_app_config()
    
    # SKU 매핑 로드
    sku_mapping = get_sku_mapping(config)
    print(f"로드된 SKU 매핑 수: {len(sku_mapping)}")
    
    if sku_mapping:
        # 첫 몇 개 매핑 출력
        print("샘플 매핑:")
        for i, (shopby_sku, cornerlogis_sku) in enumerate(list(sku_mapping.items())[:5]):
            print(f"  {shopby_sku} -> {cornerlogis_sku}")
        
        # 유효성 검사
        validation = validate_sku_mapping(sku_mapping)
        print(f"\n유효성 검사 결과:")
        print(f"  총 매핑 수: {validation['total_mappings']}")
        print(f"  빈 샵바이 SKU: {len(validation['empty_shopby_skus'])}")
        print(f"  빈 코너로지스 SKU: {len(validation['empty_cornerlogis_skus'])}")
        print(f"  중복 샵바이 SKU: {len(validation['duplicate_shopby_skus'])}")
        print(f"  중복 코너로지스 SKU: {len(validation['duplicate_cornerlogis_skus'])}")


if __name__ == "__main__":
    test_sku_mapping()
