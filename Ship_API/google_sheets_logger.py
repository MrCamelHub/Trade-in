from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


class GoogleSheetsLogger:
    """샵바이 주문 상품 정보를 구글시트에 기록"""

    def __init__(
        self,
        spreadsheet_id: str,
        tab_name: str,
        google_credentials_json: Optional[str] = None,
        google_credentials_path: Optional[str] = None,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.tab_name = tab_name
        self.google_credentials_json = google_credentials_json
        self.google_credentials_path = google_credentials_path
        self.service = self._build_service()

    def _build_service(self):
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds: Optional[Credentials] = None
        if self.google_credentials_json:
            # 환경변수 JSON 문자열
            creds_info = json.loads(self.google_credentials_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        elif self.google_credentials_path:
            creds = Credentials.from_service_account_file(self.google_credentials_path, scopes=scopes)
        else:
            raise RuntimeError("Google credentials not provided")
        return build("sheets", "v4", credentials=creds)

    def log_products(self, products: List[Dict[str, Any]], at: Optional[datetime] = None) -> bool:
        """상품 리스트를 [날짜, 상품명, 상품번호]로 기록"""
        if not products:
            return True
        ts = (at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        values: List[List[Any]] = []
        for p in products:
            product_name = p.get("productName", "") or p.get("name", "")
            product_no = p.get("productNo", "") or p.get("mallProductNo", "")
            values.append([ts, product_name, product_no])
        body = {"values": values}
        # 시트1의 C열부터 기록한다고 했던 요구사항: 여기서는 고정 컬럼이 아닌 단순 append로 처리
        rng = f"{self.tab_name}!C:E"
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=rng,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return True

    def log_from_shopby_orders(self, shopby_orders: List[Dict[str, Any]]) -> int:
        """샵바이 주문 응답에서 상품 정보 추출하여 기록"""
        all_products: List[Dict[str, Any]] = []
        for order in shopby_orders:
            # 샵바이 API 구조: orderSheetInfo.payProducts에 상품 정보가 있음
            order_sheet_info = order.get("orderSheetInfo", {})
            pay_products = order_sheet_info.get("payProducts", [])
            
            # 기존 구조도 지원 (하위 호환성)
            if not pay_products:
                items = (
                    order.get("items")
                    or order.get("orderItems") 
                    or order.get("orderProducts")
                    or order.get("deliveryGroups", [])
                )
                # deliveryGroups 처리
                if items and isinstance(items, list) and len(items) > 0:
                    if "orderProducts" in items[0]:
                        for delivery_group in items:
                            for product in delivery_group.get("orderProducts", []):
                                pay_products.append({
                                    "productNo": product.get("productNo"),
                                    "productName": product.get("productName"),
                                })
                else:
                    pay_products = items if isinstance(items, list) else [items] if items else []
            
            for product in pay_products:
                if isinstance(product, dict):
                    product_name = product.get("productName", "") or product.get("name", "")
                    product_no = str(product.get("productNo", "") or product.get("mallProductNo", ""))
                    
                    if product_name or product_no:
                        all_products.append({
                            "productName": product_name,
                            "productNo": product_no,
                        })
        
        if not all_products:
            print("🔍 추출된 상품이 없습니다. 샵바이 데이터 구조를 확인해주세요.")
            return 0
        
        print(f"🔍 추출된 상품: {len(all_products)}개")
        for i, product in enumerate(all_products[:3]):  # 처음 3개만 표시
            print(f"  {i+1}. {product['productName']} (상품번호: {product['productNo']})")
        
        self.log_products(all_products)
        return len(all_products)


