from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


class GoogleSheetsLogger:
    """구글 시트에 상품 정보를 기록하는 클래스"""
    
    def __init__(
        self,
        spreadsheet_id: str,
        google_credentials_json: Optional[str] = None,
        google_credentials_path: Optional[str] = None
    ):
        self.spreadsheet_id = spreadsheet_id
        self.service = self._build_service(google_credentials_json, google_credentials_path)
    
    def _build_service(
        self,
        google_credentials_json: Optional[str] = None,
        google_credentials_path: Optional[str] = None
    ):
        """Google Sheets API 서비스 생성"""
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        
        if google_credentials_json:
            # 환경변수에서 JSON 직접 로드
            creds_info = json.loads(google_credentials_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        elif google_credentials_path and Path(google_credentials_path).exists():
            # 파일에서 인증 정보 로드
            creds = Credentials.from_service_account_file(google_credentials_path, scopes=scopes)
        else:
            raise ValueError("Google 인증 정보를 찾을 수 없습니다")
        
        return build('sheets', 'v4', credentials=creds)
    
    def find_next_empty_row(self, sheet_name: str = "시트1") -> int:
        """빈 행 찾기 (col_3부터 col_5까지 모두 비어있는 행)"""
        try:
            # C:E 열(col_3~col_5) 데이터 가져오기
            range_name = f"{sheet_name}!C:E"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            # 빈 행 찾기 - C, D, E 열이 모두 비어있는 첫 번째 행
            for i, row in enumerate(values):
                # 행이 완전히 비어있거나, C, D, E 열이 모두 비어있는 경우
                if len(row) == 0 or all(not str(cell).strip() for cell in row[:3]):
                    return i + 1  # 1부터 시작하는 행 번호
            
            # 모든 행이 차있다면 마지막 행 다음
            return len(values) + 1
            
        except Exception as e:
            print(f"빈 행 찾기 실패: {e}")
            # 실패시 안전하게 큰 번호 반환
            return 1000
    
    def log_products_to_sheet(
        self,
        products: List[Dict[str, Any]],
        date_str: str,
        sheet_name: str = "시트1"
    ) -> bool:
        """상품 정보를 구글 시트에 기록"""
        try:
            if not products:
                print("기록할 상품이 없습니다.")
                return True
            
            # 빈 행 찾기
            start_row = self.find_next_empty_row(sheet_name)
            
            # 데이터 준비
            values = []
            for product in products:
                product_name = product.get('productName', '')
                product_no = product.get('productNo', '') or product.get('mallProductNo', '')
                
                # [col_3(날짜), col_4(상품명), col_5(상품번호-productNo)]
                row = [date_str, product_name, product_no]
                values.append(row)
            
            # 범위 설정 (C열부터 E열까지)
            end_row = start_row + len(values) - 1
            range_name = f"{sheet_name}!C{start_row}:E{end_row}"
            
            # 시트에 데이터 쓰기
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            updated_rows = result.get('updatedRows', 0)
            print(f"구글 시트 기록 완료: {updated_rows}개 행 업데이트 (행 {start_row}~{end_row})")
            return True
            
        except Exception as e:
            print(f"구글 시트 기록 실패: {e}")
            return False
    
    def log_shopby_orders(
        self,
        shopby_orders: List[Dict[str, Any]],
        date_str: Optional[str] = None,
        sheet_name: str = "시트1"
    ) -> bool:
        """샵바이 주문에서 상품 정보 추출하여 시트에 기록"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 모든 주문에서 상품 정보 추출
        all_products = []
        
        for order in shopby_orders:
            # 배송 그룹에서 상품 정보 추출
            delivery_groups = order.get('deliveryGroups', [])
            
            for delivery_group in delivery_groups:
                order_products = delivery_group.get('orderProducts', [])
                
                for product in order_products:
                    product_info = {
                        'productName': product.get('productName', ''),
                        'productNo': product.get('mallProductNo', ''),
                        'orderNo': order.get('orderNo', ''),
                        'orderDate': order.get('orderYmdt', '')
                    }
                    
                    # 중복 상품 체크 (같은 상품번호가 이미 있는지)
                    existing_nos = [p.get('productNo') for p in all_products]
                    if product_info['productNo'] and product_info['productNo'] not in existing_nos:
                        all_products.append(product_info)
        
        print(f"추출된 고유 상품 수: {len(all_products)}개")
        
        if all_products:
            return self.log_products_to_sheet(all_products, date_str, sheet_name)
        else:
            print("기록할 상품이 없습니다.")
            return True


# 테스트 함수
def test_sheets_logger():
    """구글 시트 로거 테스트"""
    from .config import load_app_config
    
    config = load_app_config()
    
    # 테스트용 로거 생성
    logger = GoogleSheetsLogger(
        spreadsheet_id="1pXOIiSCXpEOUHQUgl_4FUDltRG9RYq0_cadJX4Cre1o",
        google_credentials_json=config.google_credentials_json,
        google_credentials_path=str(config.google_credentials_path) if config.google_credentials_path else None
    )
    
    # 테스트 데이터
    test_products = [
        {
            'productName': '테스트 상품 1',
            'productCode': 'TEST001'
        },
        {
            'productName': '테스트 상품 2', 
            'productCode': 'TEST002'
        }
    ]
    
    # 테스트 실행
    test_date = datetime.now().strftime("%Y-%m-%d")
    success = logger.log_products_to_sheet(test_products, test_date)
    
    if success:
        print("✅ 구글 시트 로거 테스트 성공!")
    else:
        print("❌ 구글 시트 로거 테스트 실패!")


if __name__ == "__main__":
    test_sheets_logger()
