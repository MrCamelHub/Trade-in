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
                 base_url: str = "https://server-api.e-ncp.com",
                 system_key: str = "b1hLbVFoS1lUeUZIM0QrZTNuNklUQT09",
                 auth_token: str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwYXJ0bmVyTm8iOjEyNzk1OSwiYWRtaW5ObyI6MjE5NjI0LCJhY2Nlc3NpYmxlSXBzIjpbXSwidXNhZ2UiOiJTRVJWRVIiLCJhZG1pbklkIjoiam9zZXBoIiwiaXNzIjoiTkhOIENvbW1lcmNlIiwiYXBwTm8iOjE0ODksIm1hbGxObyI6Nzg1MjIsInNvbHV0aW9uVHlwZSI6IlNIT1BCWSIsImV4cCI6NDkwODY2ODU0MSwic2hvcE5vIjoxMDAzNzY1LCJpYXQiOjE3NTUwNjg1NDF9.-aTwbWRNYrCDm-tNCyd-LzUxmKuv766QtQWeuLvoTtI",
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
    
    def _get_headers(self, version: str = None) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        api_version = version or self.version
        return {
            "Version": api_version,
            "Content-Type": "application/json",
            "systemKey": self.system_key,
            # mallKey 제거 - 에러 원인으로 확인됨
            "Authorization": f"Bearer {self.auth_token}"
        }
    
    async def get_order_details(self, order_no: str) -> Optional[Dict[str, Any]]:
        """
        특정 주문의 상세 정보 조회 (originalDeliveryNo 포함)
        주문 목록에서 해당 주문을 찾아서 반환
        
        Args:
            order_no: 주문번호
        
        Returns:
            주문 상세 정보 (originalDeliveryNo 포함)
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        print(f"🔍 샵바이 주문 상세 조회 (목록에서 검색):")
        print(f"  주문번호: {order_no}")
        
        try:
            # 주문번호에서 날짜 추출 (예: 202508141241584834 -> 2025-08-14)
            from datetime import datetime, timedelta
            import pytz
            from urllib.parse import urlencode, quote
            
            # 주문번호 앞 8자리에서 날짜 추출
            if len(order_no) >= 8:
                order_date_str = order_no[:8]  # 20250814
                try:
                    order_date = datetime.strptime(order_date_str, "%Y%m%d")
                    kst = pytz.timezone("Asia/Seoul")
                    
                    # 해당 날짜 하루 범위로 검색
                    start_date = kst.localize(order_date.replace(hour=0, minute=0, second=0))
                    end_date = kst.localize(order_date.replace(hour=23, minute=59, second=59))
                    
                except ValueError:
                    # 날짜 파싱 실패시 최근 30일 검색
                    kst = pytz.timezone("Asia/Seoul")
                    end_date = datetime.now(kst)
                    start_date = end_date - timedelta(days=30)
            else:
                # 주문번호 형식이 예상과 다를 때 최근 30일 검색
                kst = pytz.timezone("Asia/Seoul")
                end_date = datetime.now(kst)
                start_date = end_date - timedelta(days=30)
            
            print(f"  검색 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
            
            # 주문 목록에서 검색
            params = {
                "startYmdt": start_date.strftime("%Y-%m-%d %H:%M:%S"),
                "endYmdt": end_date.strftime("%Y-%m-%d %H:%M:%S"),
                "pageNumber": 1,
                "pageSize": 100  # 충분히 큰 페이지 크기
            }
            
            encoded_params = urlencode(params, quote_via=quote)
            url = f"{self.base_url}/orders?{encoded_params}"
            headers = self._get_headers(version="1.1")  # 주문 조회는 1.1
            
            async with self.session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                
                # 주문 목록에서 해당 주문 찾기
                orders = data.get("contents", []) or data.get("orders", [])
                print(f"  조회된 주문 수: {len(orders)}건")
                
                for order in orders:
                    if order.get("orderNo") == order_no:
                        # shippings 배열에서 shippingNo 우선 사용
                        shippings = order.get("shippings", [])
                        shipping_no = None
                        
                        print(f"  🔍 shippings 구조 분석:")
                        print(f"    shippings 배열 길이: {len(shippings)}")
                        if shippings:
                            print(f"    shippings[0] 전체: {json.dumps(shippings[0], indent=4, ensure_ascii=False)}")
                            shipping_no = shippings[0].get("shippingNo")
                            print(f"    shippings[0].shippingNo: {shipping_no}")
                        else:
                            print(f"    shippings 배열이 비어있음")
                        
                        # 기존 방식 (백업용)
                        original_delivery_no = order.get("originalDeliveryNo")
                        
                        # 없으면 deliveryGroups에서 deliveryNo 사용
                        if not shipping_no and not original_delivery_no:
                            delivery_groups = order.get("deliveryGroups", [])
                            if delivery_groups:
                                original_delivery_no = delivery_groups[0].get("deliveryNo")
                        
                        # 최종 배송번호 결정 (shippings.shippingNo 우선)
                        final_shipping_no = shipping_no or original_delivery_no
                        
                        print(f"✅ 주문 조회 성공: {order_no}")
                        print(f"  배송번호 비교:")
                        print(f"    shippings[0].shippingNo: {shipping_no}")
                        print(f"    originalDeliveryNo: {original_delivery_no}")
                        print(f"    최종 사용 배송번호: {final_shipping_no}")
                        print(f"    두 값이 동일한가?: {shipping_no == original_delivery_no}")
                        print(f"  주문상태: {order.get('orderStatusType', 'N/A')}")
                        print(f"  결제상태: {order.get('paymentStatusType', 'N/A')}")
                        
                        # 최종 배송번호로 필드 업데이트
                        order["originalDeliveryNo"] = final_shipping_no
                        
                        return order
                
                print(f"❌ 주문을 찾을 수 없음: {order_no}")
                return None
                
        except aiohttp.ClientResponseError as e:
            print(f"❌ HTTP 오류: {e.status} - {e.message}")
            return None
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
        delivery_company_type: str = "LOTTE",
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
        headers = self._get_headers(version="1.0")  # 상태 변경은 1.0
        
        payload = {
            "changeStatusList": [
                {
                    "shippingNo": shipping_no,  # 원본 타입 그대로 사용 (int 변환 제거)
                    "deliveryCompanyType": delivery_company_type,
                    "invoiceNo": invoice_no
                }
            ],
            "orderStatusType": order_status_type
        }
        
        print(f"🚚 샵바이 주문 상태 변경:")
        print(f"  URL: {url}")
        print(f"  배송번호: {shipping_no}")
        print(f"  송장번호: {invoice_no}")
        print(f"  택배사: {delivery_company_type}")
        print(f"  변경 상태: {order_status_type}")
        print(f"  요청 페이로드: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        try:
            async with self.session.put(url, headers=headers, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                
                print(f"📋 API 응답:")
                print(f"  {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # 실제 API 응답에서 성공/실패 확인
                success_count = result.get("successCount", 0)
                fail_count = result.get("failCount", 0)
                failures = result.get("failures", [])
                
                if success_count > 0 and fail_count == 0:
                    print(f"✅ 주문 상태 변경 성공: {success_count}건 성공")
                    return True
                else:
                    print(f"❌ 주문 상태 변경 실패: {fail_count}건 실패")
                    for failure in failures:
                        error_code = failure.get("errorCode", "N/A")
                        error_message = failure.get("errorMessage", "N/A")
                        print(f"  오류 코드: {error_code}")
                        print(f"  오류 메시지: {error_message}")
                    return False
                
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
            #                 print(f"상태 변경 결과: {success}")


async def test_check_order_202508261018087924():
    """주문번호 202508261018087924 상태 확인 테스트"""
    async with ShopbyDeliveryClient() as client:
        print("🚀 주문번호 202508261018087924 상태 확인 테스트 시작...")
        print("=" * 60)
        
        # 주문번호 202508261018087924으로 주문 상세 조회
        order_no = "202508261018087924"
        
        print(f"📦 조회할 주문 정보:")
        print(f"  주문번호: {order_no}")
        print(f"  예상 배송번호: 75526782")
        print("=" * 60)
        
        # 주문 상세 조회
        order_details = await client.get_order_details(order_no)
        
        if order_details:
            print(f"✅ 주문 조회 성공!")
            print(f"📋 주문 상세 정보:")
            print(f"  주문번호: {order_details.get('orderNo', 'N/A')}")
            print(f"  배송번호(originalDeliveryNo): {order_details.get('originalDeliveryNo', 'N/A')}")
            print(f"  결제방법: {order_details.get('payType', 'N/A')}")
            
            # 배송 그룹 정보
            delivery_groups = order_details.get('deliveryGroups', [])
            if delivery_groups:
                print(f"📦 배송 그룹 정보:")
                for i, group in enumerate(delivery_groups):
                    print(f"  그룹 {i+1}:")
                    print(f"    송장번호: {group.get('invoiceNo', 'N/A')}")
                    
                    # 주문 상품 정보
                    order_products = group.get('orderProducts', [])
                    if order_products:
                        for j, product in enumerate(order_products):
                            print(f"    상품 {j+1}:")
                            options = product.get('orderProductOptions', [])
                            if options:
                                for k, option in enumerate(options):
                                    print(f"      옵션 {k+1}:")
                                    print(f"        주문상태: {option.get('orderStatusType', 'N/A')}")
                                    print(f"        배송상태: {option.get('deliveryStatusType', 'N/A')}")
        else:
            print(f"❌ 주문 조회 실패!")
        
        return order_details


if __name__ == "__main__":
    # asyncio.run(test_shopby_delivery())
    asyncio.run(test_check_order_202508261018087924())
