"""
코너로지스 운영 API 클라이언트
송장번호 조회 및 주문 상태 확인 전용
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp


class CornerlogisProductionClient:
    """코너로지스 운영 API 클라이언트"""
    
    def __init__(self, api_key: str = "NjBhMDk5OTctNzZhMy00NmNk"):
        self.base_url = "https://api.cornerlogis.com"
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json;charset=UTF-8",
            "Authorization": self.api_key
        }
    
    async def get_orders_with_invoices(
        self, 
        status_list: str = "COMPLETED_SHIPMENTS"
    ) -> List[Dict[str, Any]]:
        """
        송장번호가 있는 주문 목록 조회
        
        Args:
            status_list: 조회할 주문 상태 (기본값: COMPLETED_SHIPMENTS)
            
        Returns:
            주문 목록
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        url = f"{self.base_url}/api/v1/order/getOrders"
        headers = self._get_headers()
        params = {"statusList": status_list}
        
        print(f"🔍 코너로지스 운영 API 주문 조회:")
        print(f"  URL: {url}")
        print(f"  Headers: {headers}")
        print(f"  Params: {params}")
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                # 응답 구조 분석
                if isinstance(data, dict) and "data" in data and "list" in data["data"]:
                    orders = data["data"]["list"]
                    print(f"✅ 주문 조회 성공: {len(orders)}건")
                    return orders
                else:
                    print("❌ 예상하지 못한 응답 구조")
                    return []
                    
        except aiohttp.ClientError as e:
            print(f"❌ 코너로지스 주문 조회 실패: {e}")
            return []
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return []
    
    async def get_orders_with_new_invoices(self) -> List[Dict[str, Any]]:
        """
        새로 송장번호가 생긴 주문들 조회
        PROGRESSING_SHIPMENTS(출고 진행 중)와 COMPLETED_SHIPMENTS(출고 완료) 상태에서 조회
        (delivery.code가 null이 아닌 주문들)
        
        Returns:
            송장번호가 있는 주문 목록
        """
        print("📡 코너로지스에서 송장번호가 있는 주문들 조회...")
        
        # 출고 진행 중과 출고 완료 상태 모두 조회
        progressing_orders = await self.get_orders_with_invoices("PROGRESSING_SHIPMENTS")
        completed_orders = await self.get_orders_with_invoices("COMPLETED_SHIPMENTS")
        
        print(f"   📦 출고 진행 중(PROGRESSING_SHIPMENTS): {len(progressing_orders)}건")
        print(f"   📦 출고 완료(COMPLETED_SHIPMENTS): {len(completed_orders)}건")
        
        # 두 목록 합치기 (중복 제거)
        all_orders = progressing_orders + completed_orders
        
        # 중복 제거 (companyOrderId 기준)
        seen_orders = set()
        unique_orders = []
        for order in all_orders:
            company_order_id = order.get('companyOrderId', '')
            if company_order_id not in seen_orders:
                seen_orders.add(company_order_id)
                unique_orders.append(order)
        
        print(f"   📋 중복 제거 후 총: {len(unique_orders)}건")
        all_orders = unique_orders
        
        # delivery.code가 있는 주문들만 필터링
        orders_with_invoices = []
        for order in all_orders:
            if "orderItems" in order:
                for item in order["orderItems"]:
                    delivery = item.get("delivery", {})
                    if delivery.get("code"):  # 송장번호가 있으면
                        # 주문번호와 송장번호 추출
                        order_info = {
                            "cornerOrderId": order.get("cornerOrderId"),
                            "companyOrderId": order.get("companyOrderId"),
                            "orderAt": order.get("orderAt"),
                            "customer": order.get("customer"),
                            "invoiceNo": delivery.get("code"),
                            "pickupCompleteAt": delivery.get("pickupCompleteAt"),
                            "arrivalAt": delivery.get("arrivalAt"),
                            "status": item.get("status"),
                            "orderItem": item
                        }
                        orders_with_invoices.append(order_info)
                        break  # 하나의 주문에서 첫 번째 아이템만 처리
        
        print(f"📦 송장번호가 있는 주문: {len(orders_with_invoices)}건")
        return orders_with_invoices
    
    def extract_shopby_order_no(self, company_order_id: str) -> str:
        """
        companyOrderId에서 샵바이 주문번호 추출
        예: "202508141241584834 (N: 2025081427063970)" -> "202508141241584834"
        
        Args:
            company_order_id: 코너로지스 companyOrderId
            
        Returns:
            샵바이 주문번호
        """
        if " (N:" in company_order_id:
            return company_order_id.split(" (N:")[0]
        return company_order_id


# 테스트 함수
async def test_cornerlogis_production():
    """코너로지스 운영 API 테스트"""
    async with CornerlogisProductionClient() as client:
        print("🚀 코너로지스 운영 API 테스트 시작...")
        
        # 송장번호가 있는 주문들 조회
        orders = await client.get_orders_with_new_invoices()
        
        print(f"\n📊 결과 요약:")
        print(f"송장번호가 있는 주문 수: {len(orders)}")
        
        if orders:
            print(f"\n📦 첫 번째 주문 샘플:")
            sample = orders[0]
            print(f"  주문번호: {sample.get('companyOrderId')}")
            print(f"  샵바이 주문번호: {client.extract_shopby_order_no(sample.get('companyOrderId', ''))}")
            print(f"  송장번호: {sample.get('invoiceNo')}")
            print(f"  배송완료: {sample.get('arrivalAt')}")
            print(f"  상태: {sample.get('status')}")


if __name__ == "__main__":
    asyncio.run(test_cornerlogis_production())
