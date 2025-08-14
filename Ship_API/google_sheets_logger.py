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
            items = (
                order.get("items")
                or order.get("orderItems")
                or order.get("orderProducts")
                or []
            )
            if not isinstance(items, list):
                items = [items]
            for it in items:
                # 최소 필드만 추출
                all_products.append(
                    {
                        "productName": it.get("productName") or it.get("name") or "",
                        "productNo": it.get("productNo") or it.get("mallProductNo") or "",
                    }
                )
        if not all_products:
            return 0
        self.log_products(all_products)
        return len(all_products)


