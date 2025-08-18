"""
샵바이 배송 관리 API 클라이언트
주문 상세 조회 및 상태 변경 전용
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp


class ShopbyDeliveryClient:
    """샵바이 배송 관리 API 클라이언트"""
    
    def __init__(self, 
                 base_url: str = "https://bonibello.godo.co.kr/adm-api",
                 system_key: str = "b1hLbVFoS1lUeUZIM0QrZTNuNklUQT09",
                 auth_token: str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwYXJ0bmVyTm8iOjEyNzk1OSwiYWRtaW5ObyI6MjE5NjI0LCJhY2Nlc3NpYmxlSXBzIjpbXSwidXNhZ2UiOiJTRVJWRVIiLCJhZG1pbklkIjoiam9zZXBoIiwiaXNzIjoiTkhOIENvbW1lcmNlIiwiYXBwTm8iOjE0ODksIm1hbGxObyI6Nzg1MjIsInNvbHV0aW9uVHlwZSI6IlNIT1BCWSIsImV4cCI6NDkwODU2MzAwMiwic2hvcE5vIjoxMDAzNzY1LCJpYXQiOjE3NTQ5NjMwMDJ9.rEYIdHOb68Pr4N47aRRPI4bdjuW4KAg_bqUDyoF49Zc",
                 version: str = "1.1"):
        self.base_url = base_url
        self.system_key = system_key
        self.auth_token = auth_token
        self.version = version
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
            "Version": self.version,
            "Content-Type": "application/json",
            "systemKey": self.system_key,
            "Authorization": f"Bearer {self.auth_token}"
        }
    
    async def get_order_details(self, order_no: str) -> Optional[Dict[str, Any]]:
        """
        특정 주문의 상세 정보 조회 (originalDeliveryNo 포함)
        
        Args:
            order_no: 주문번호
        
        Returns:
            주문 상세 정보 (originalDeliveryNo 포함)
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        url = f"{self.base_url}/orders/{order_no}"
        headers = self._get_headers()
        
        print(f"🔍 샵바이 주문 상세 조회:")
        print(f"  URL: {url}")
        print(f"  주문번호: {order_no}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 404:
                    print(f"❌ 주문을 찾을 수 없음: {order_no}")
                    return None
                response.raise_for_status()
                data = await response.json()
                
                # originalDeliveryNo 확인
                original_delivery_no = data.get("originalDeliveryNo")
                print(f"✅ 주문 조회 성공: {order_no}")
                print(f"  배송번호(originalDeliveryNo): {original_delivery_no}")
                
                return data
                
        except aiohttp.ClientError as e:
            print(f"❌ 주문 상세 조회 실패 (주문번호: {order_no}): {e}")
            return None
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return None
    
    async def change_order_status_by_shipping_no(
        self,
        shipping_no: str,
        invoice_no: str,
        delivery_company_type: str = "POST",
        order_status_type: str = "DELIVERY_ING"
    ) -> bool:
        """
        배송번호로 주문 상태 일괄 변경
        
        Args:
            shipping_no: 배송번호 (originalDeliveryNo)
            invoice_no: 송장번호 (코너로지스 delivery.code)
            delivery_company_type: 택배사 (기본값: POST)
            order_status_type: 변경할 주문상태 (기본값: DELIVERY_ING)
        
        Returns:
            성공 여부
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        url = f"{self.base_url}/orders/change-status/by-shipping-no"
        headers = self._get_headers()
        
        payload = {
            "shippingNo": shipping_no,
            "deliveryCompanyType": delivery_company_type,
            "invoiceNo": invoice_no,
            "orderStatusType": order_status_type
        }
        
        print(f"🚚 샵바이 주문 상태 변경:")
        print(f"  URL: {url}")
        print(f"  배송번호: {shipping_no}")
        print(f"  송장번호: {invoice_no}")
        print(f"  택배사: {delivery_company_type}")
        print(f"  변경 상태: {order_status_type}")
        
        try:
            async with self.session.put(url, headers=headers, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                
                print(f"✅ 주문 상태 변경 성공:")
                print(f"  응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                return True
                
        except aiohttp.ClientError as e:
            print(f"❌ 주문 상태 변경 실패: {e}")
            if hasattr(e, 'response') and e.response:
                try:
                    error_detail = await e.response.json()
                    print(f"  오류 상세: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
                except:
                    error_text = await e.response.text()
                    print(f"  오류 응답: {error_text}")
            return False
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return False


# 테스트 함수
async def test_shopby_delivery():
    """샵바이 배송 API 테스트"""
    async with ShopbyDeliveryClient() as client:
        print("🚀 샵바이 배송 API 테스트 시작...")
        
        # 테스트용 주문번호 (실제 주문번호로 교체 필요)
        test_order_no = "202508141241584834"  # 코너로지스에서 확인된 주문
        
        # 주문 상세 조회
        order_details = await client.get_order_details(test_order_no)
        
        if order_details:
            original_delivery_no = order_details.get("originalDeliveryNo")
            print(f"\n📦 주문 정보:")
            print(f"  주문번호: {test_order_no}")
            print(f"  배송번호: {original_delivery_no}")
            
            # 상태 변경 테스트 (실제로는 실행하지 않음)
            print(f"\n⚠️ 상태 변경 테스트는 주석 처리됨 (실제 데이터 보호)")
            # if original_delivery_no:
            #     success = await client.change_order_status_by_shipping_no(
            #         shipping_no=original_delivery_no,
            #         invoice_no="6896724069501"  # 테스트 송장번호
            #     )
            #     print(f"상태 변경 결과: {success}")


if __name__ == "__main__":
    asyncio.run(test_shopby_delivery())
