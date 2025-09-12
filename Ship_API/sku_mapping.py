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
            # 환경변수에서 JSON 직접 로드 (강화된 파싱 로직)
            creds_info = None
            last_error = None
            raw = google_credentials_json
            
            # 1) 직접 로드 시도
            try:
                creds_info = json.loads(raw)
                print("  📋 Google 인증: 직접 파싱 성공")
            except Exception as e:
                last_error = e
                print(f"  📋 Google 인증: 직접 파싱 실패 - {e}")
            
            # 2) 감싸진 따옴표/전후 잡음 제거 후 { ... } 부분만 추출
            if creds_info is None:
                try:
                    start = raw.find('{')
                    end = raw.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        sliced = raw[start:end+1]
                        creds_info = json.loads(sliced)
                        print("  📋 Google 인증: 슬라이싱 파싱 성공")
                except Exception as e:
                    last_error = e
                    print(f"  📋 Google 인증: 슬라이싱 파싱 실패 - {e}")
            
            # 3) 이스케이프된 개행 복구 후 로드
            if creds_info is None:
                try:
                    normalized = raw.replace('\\n', '\n')
                    creds_info = json.loads(normalized)
                    print("  📋 Google 인증: 정규화 파싱 성공")
                except Exception as e:
                    last_error = e
                    print(f"  📋 Google 인증: 정규화 파싱 실패 - {e}")
            
            # 4) base64 가능성 (드물지만 지원)
            if creds_info is None:
                try:
                    import base64
                    decoded = base64.b64decode(raw).decode('utf-8', 'ignore')
                    creds_info = json.loads(decoded)
                    print("  📋 Google 인증: base64 파싱 성공")
                except Exception as e:
                    last_error = e
                    print(f"  📋 Google 인증: base64 파싱 실패 - {e}")
            
            if creds_info is None:
                raise ValueError(f"Google 인증 JSON 파싱 실패: {last_error}")
            
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        elif google_credentials_path and Path(google_credentials_path).exists():
            # 파일에서 인증 정보 로드
            creds = Credentials.from_service_account_file(google_credentials_path, scopes=scopes)
        else:
            print("Google 인증 정보를 찾을 수 없습니다")
            return {}
        
        # Google Sheets API 서비스 생성
        service = build('sheets', 'v4', credentials=creds)
        
        # 시트 데이터 조회 - 동적으로 행 수 확인
        # 먼저 시트의 전체 행 수를 확인
        try:
            # 시트 메타데이터 조회
            sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = sheet_metadata.get('sheets', [])
            target_sheet = None
            for sheet in sheets:
                if sheet['properties']['title'] == tab_name:
                    target_sheet = sheet
                    break
            
            if target_sheet:
                max_rows = target_sheet['properties']['gridProperties']['rowCount']
                print(f"📊 시트 '{tab_name}'의 총 행 수: {max_rows}")
            else:
                max_rows = 10000  # 기본값
                print(f"📊 시트 '{tab_name}'을 찾을 수 없음. 기본값 10000 사용")
        except Exception as e:
            max_rows = 10000  # 기본값
            print(f"📊 시트 메타데이터 조회 실패: {e}. 기본값 10000 사용")
        
        # 실제 데이터 조회
        range_name = f"{tab_name}!{cornerlogis_sku_col}1:{shopby_sku_col}{max_rows}"
        print(f"📊 구글 시트 조회: {range_name}")
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            majorDimension='ROWS'
        ).execute()
        
        values = result.get('values', [])
        print(f"📋 조회된 행 수: {len(values)}개")
        
        # SKU 매핑 딕셔너리 생성
        # 사용자 요청: col_10(J열) = shopby_sku, col_9(I열) = cornerlogis_goodsId
        sku_mapping = {}
        
        for i, row in enumerate(values):
            if i == 0:  # 헤더 행 건너뛰기
                continue
                
            # 행이 비어있거나 너무 짧은 경우도 처리
            if len(row) == 0:
                continue
            elif len(row) == 1:
                # I열만 있는 경우
                cornerlogis_goods_id = str(row[0]).strip() if row[0] else ""
                shopby_sku = ""
            else:
                # I열, J열 모두 있는 경우
                cornerlogis_goods_id = str(row[0]).strip() if row[0] else ""
                shopby_sku = str(row[1]).strip() if row[1] else ""
            
            # 둘 다 값이 있을 때만 매핑에 추가
            if shopby_sku and cornerlogis_goods_id:
                sku_mapping[shopby_sku] = cornerlogis_goods_id
        
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
    from config import load_app_config
    
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
