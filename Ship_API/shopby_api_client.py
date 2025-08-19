from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import pytz
from config import ShopbyApiConfig


class ShopbyApiClient:
    """샵바이 API 클라이언트"""
    
    def __init__(self, config: ShopbyApiConfig):
        self.config = config
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
            "Version": self.config.version,
            "Content-Type": "application/json",
            "systemKey": self.config.system_key,
            "Authorization": f"Bearer {self.config.auth_token}"
        }
    
    async def get_orders(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        order_status: str = "PAY_DONE"
    ) -> List[Dict[str, Any]]:
        """
        결제완료 주문 목록 조회
        
        Args:
            start_date: 조회 시작일시 (None이면 오늘 00:00)
            end_date: 조회 종료일시 (None이면 현재 시간)
            order_status: 주문 상태 (기본값: PAY_DONE)
        
        Returns:
            주문 목록
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        # 기본 날짜 설정 (한국 시간 기준)
        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)
        
        if end_date is None:
            end_date = now
        
        if start_date is None:
            # 오늘 00:00부터
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 쿼리 파라미터 설정
        params = {
            "startYmdt": start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "endYmdt": end_date.strftime("%Y-%m-%d %H:%M:%S"),
            "orderRequestTypes": order_status
        }
        
        url = f"{self.config.base_url}/orders"
        headers = self._get_headers()
        
        try:
            # URL 파라미터를 수동으로 구성하여 인코딩 문제 해결
            from urllib.parse import urlencode, quote
            
            # 공백을 %20으로 인코딩 (+ 대신)
            encoded_params = urlencode(params, quote_via=quote)
            full_url = f"{url}?{encoded_params}"
            
            print(f"🔍 샵바이 API 호출 디버깅:")
            print(f"  Base URL: {url}")
            print(f"  Full URL: {full_url}")
            print(f"  Headers: {headers}")
            print(f"  Params: {params}")
            
            # params를 URL에 직접 포함시켜서 호출
            async with self.session.get(full_url, headers=headers) as response:
                print(f"  Response Status: {response.status}")
                response.raise_for_status()
                data = await response.json()
                
                # API 응답 구조에 따라 조정 필요
                if isinstance(data, dict):
                    return data.get("orders", []) or data.get("data", []) or [data]
                elif isinstance(data, list):
                    return data
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            print(f"샵바이 API 호출 실패: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"샵바이 API 응답 파싱 실패: {e}")
            raise
    
    async def get_order_detail(
        self,
        order_no: str
    ) -> Dict[str, Any]:
        """
        특정 주문의 상세 정보 조회
        
        Args:
            order_no: 주문 번호
        
        Returns:
            주문 상세 정보
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        url = f"{self.config.base_url}/orders/{order_no}"
        headers = self._get_headers()
        headers["Version"] = "1.0"  # API 요구사항
        
        try:
            print(f"🔍 샵바이 주문 상세 조회: {order_no}")
            print(f"  URL: {url}")
            print(f"  Headers: {headers}")
            
            async with self.session.get(url, headers=headers) as response:
                print(f"  Response Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ 주문 상세 조회 성공: {order_no}")
                    return result
                else:
                    error_text = await response.text()
                    print(f"❌ 주문 상세 조회 실패: {response.status}")
                    print(f"  Error Response: {error_text}")
                    
                    return {
                        "status": "error",
                        "message": f"주문 상세 조회 실패 (HTTP {response.status})",
                        "error": error_text
                    }
                    
        except aiohttp.ClientError as e:
            print(f"❌ 샵바이 API 호출 오류: {e}")
            return {
                "status": "error",
                "message": f"샵바이 API 호출 오류: {str(e)}",
                "error": str(e)
            }
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return {
                "status": "error",
                "message": f"예상치 못한 오류: {str(e)}",
                "error": str(e)
            }

    async def get_order_details(self, order_no: str) -> Optional[Dict[str, Any]]:
        """
        특정 주문의 상세 정보 조회
        
        Args:
            order_no: 주문번호
        
        Returns:
            주문 상세 정보
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        url = f"{self.config.base_url}/orders/{order_no}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 404:
                    return None
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            print(f"주문 상세 조회 실패 (주문번호: {order_no}): {e}")
            return None
    
    async def get_today_orders(self) -> List[Dict[str, Any]]:
        """
        오늘 00:00부터 현재까지의 결제완료 주문 조회
        
        Returns:
            오늘의 주문 목록
        """
        return await self.get_orders()
    
    async def get_orders_by_date_range(
        self,
        days_back: int = 1
    ) -> List[Dict[str, Any]]:
        """
        지정된 일수만큼 과거부터 현재까지의 주문 조회
        
        Args:
            days_back: 과거 몇 일간의 주문을 조회할지
        
        Returns:
            지정 기간의 주문 목록
        """
        kst = pytz.timezone("Asia/Seoul")
        end_date = datetime.now(kst)
        start_date = end_date - timedelta(days=days_back)
        
        return await self.get_orders(start_date=start_date, end_date=end_date)
    
    async def get_all_pay_done_orders(
        self,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        모든 결제완료(PAY_DONE) 주문 조회
        
        Args:
            days_back: 조회 기간 (기본 30일, 충분히 큰 값 설정 가능)
        
        Returns:
            모든 결제완료 주문 목록
        """
        # Railway 서버가 유럽 시간대일 수 있으므로 명시적으로 UTC+9 강제 적용
        import os
        os.environ['TZ'] = 'Asia/Seoul'
        
        kst = pytz.timezone("Asia/Seoul")
        
        # 현재 UTC 시간을 가져온 후 KST로 변환 (더 명확한 방법)
        utc_now = datetime.utcnow()
        end_date = utc_now.replace(tzinfo=pytz.UTC).astimezone(kst)
        start_date = end_date - timedelta(days=days_back)
        
        print(f"🌍 서버 환경 시간대 강제 설정: Asia/Seoul")
        print(f"🕐 UTC 현재 시간: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🇰🇷 KST 현재 시간: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 조회 시작일: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 조회 종료일: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔍 결제완료 주문 조회 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        return await self.get_orders(start_date=start_date, end_date=end_date, order_status="PAY_DONE")

    async def get_pay_done_orders_chunked(
        self,
        days_back: int = 30,
        chunk_days: int = 1
    ) -> List[Dict[str, Any]]:
        """
        기간을 잘게 나눠서(PAY_DONE) 주문을 합쳐 반환
        일부 환경에서 긴 기간 조회가 400을 유발하는 문제를 회피
        """
        kst = pytz.timezone("Asia/Seoul")
        utc_now = datetime.utcnow()
        end_dt_kst = utc_now.replace(tzinfo=pytz.UTC).astimezone(kst)
        start_dt_kst = end_dt_kst - timedelta(days=days_back)

        print(f"🧩 청크 조회 시작: {start_dt_kst.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_dt_kst.strftime('%Y-%m-%d %H:%M:%S')} (chunk={chunk_days}d)")

        aggregated: List[Dict[str, Any]] = []

        current_start = start_dt_kst
        while current_start < end_dt_kst:
            current_end = min(current_start + timedelta(days=chunk_days), end_dt_kst)
            try:
                chunk = await self.get_orders(start_date=current_start, end_date=current_end, order_status="PAY_DONE")
                # 응답 형태 정규화
                if isinstance(chunk, list):
                    # 일부 구현에서 [ { 'contents': [...] } ] 형태일 수 있음
                    if len(chunk) > 0 and isinstance(chunk[0], dict) and 'contents' in chunk[0]:
                        contents = chunk[0]['contents'] or []
                        aggregated.extend(contents)
                    else:
                        aggregated.extend(chunk)
                elif isinstance(chunk, dict) and 'contents' in chunk:
                    aggregated.extend(chunk['contents'] or [])
                else:
                    # 알 수 없는 형태는 스킵
                    pass
                print(f"  ✅ 청크 성공: {current_start.strftime('%Y-%m-%d')} ~ {current_end.strftime('%Y-%m-%d')} (+{len(aggregated)} 누적)")
            except Exception as e:
                print(f"  ❌ 청크 실패: {current_start} ~ {current_end} → {e}")
            current_start = current_end

        print(f"🧮 청크 합산 결과: 총 {len(aggregated)}건")
        return aggregated

    async def get_pay_done_orders_adaptive(
        self,
        days_back: int = 30,
        chunk_days: int = 1
    ) -> List[Dict[str, Any]]:
        """
        우선 단일 범위 조회를 시도하고, 실패(예: 400) 시 청크 방식으로 폴백
        """
        try:
            kst = pytz.timezone("Asia/Seoul")
            utc_now = datetime.utcnow()
            end_dt_kst = utc_now.replace(tzinfo=pytz.UTC).astimezone(kst)
            start_dt_kst = end_dt_kst - timedelta(days=days_back)
            print(f"🟢 단일 범위 조회 시도: {start_dt_kst} ~ {end_dt_kst}")
            return await self.get_orders(start_date=start_dt_kst, end_date=end_dt_kst, order_status="PAY_DONE")
        except Exception as e:
            print(f"⚠️ 단일 범위 조회 실패, 청크로 폴백: {e}")
            return await self.get_pay_done_orders_chunked(days_back=days_back, chunk_days=chunk_days)

    def extract_order_option_nos(self, order: Dict[str, Any]) -> List[int]:
        """
        주문 데이터에서 주문 옵션 번호들을 추출
        
        Args:
            order: 샵바이 주문 데이터
        
        Returns:
            주문 옵션 번호 리스트
        """
        order_option_nos = []
        
        try:
            # 주문 상품들에서 옵션 번호 추출
            delivery_groups = order.get('deliveryGroups', [])
            if not delivery_groups:
                print(f"⚠️ 주문 {order.get('orderNo', 'UNKNOWN')}에 배송 그룹이 없습니다.")
                return order_option_nos
            
            for delivery_group in delivery_groups:
                order_products = delivery_group.get('orderProducts', [])
                
                for product in order_products:
                    order_product_options = product.get('orderProductOptions', [])
                    
                    for option in order_product_options:
                        option_no = option.get('orderOptionNo')
                        if option_no is not None:
                            order_option_nos.append(option_no)
                            print(f"  📦 상품: {product.get('productName', 'UNKNOWN')} - 옵션번호: {option_no}")
            
            print(f"✅ 주문 {order.get('orderNo', 'UNKNOWN')}에서 {len(order_option_nos)}개 옵션 번호 추출 완료")
            
        except Exception as e:
            print(f"❌ 주문 옵션 번호 추출 중 오류: {e}")
        
        return order_option_nos

    async def extract_order_option_nos_from_detail(
        self,
        order_no: str
    ) -> List[int]:
        """
        주문 상세 조회를 통해 주문 옵션 번호들을 추출
        
        Args:
            order_no: 주문 번호
        
        Returns:
            주문 옵션 번호 리스트
        """
        order_option_nos = []
        
        try:
            # 주문 상세 정보 조회
            order_detail = await self.get_order_detail(order_no)
            
            if order_detail.get("status") == "error":
                print(f"❌ 주문 {order_no} 상세 조회 실패: {order_detail.get('message')}")
                return order_option_nos
            
            # 주문 상품들에서 옵션 번호 추출
            delivery_groups = order_detail.get('deliveryGroups', [])
            if not delivery_groups:
                print(f"⚠️ 주문 {order_no}에 배송 그룹이 없습니다.")
                return order_option_nos
            
            for delivery_group in delivery_groups:
                order_products = delivery_group.get('orderProducts', [])
                
                for product in order_products:
                    order_product_options = product.get('orderProductOptions', [])  # orderProductOptions 사용
                    
                    for option in order_product_options:
                        option_no = option.get('orderOptionNo')
                        if option_no is not None:
                            order_option_nos.append(option_no)
                            print(f"  📦 상품: {product.get('productName', 'UNKNOWN')} - 옵션번호: {option_no}")
            
            print(f"✅ 주문 {order_no} 상세 조회에서 {len(order_option_nos)}개 옵션 번호 추출 완료")
            
        except Exception as e:
            print(f"❌ 주문 {order_no} 상세 조회 중 옵션 번호 추출 오류: {e}")
        
        return order_option_nos

    async def prepare_delivery(
        self,
        order_option_nos: List[int]
    ) -> Dict[str, Any]:
        """
        주문 옵션들을 배송준비중 상태로 변경
        
        Args:
            order_option_nos: 배송준비중으로 변경할 주문 옵션 번호 리스트
        
        Returns:
            API 응답 결과
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        if not order_option_nos:
            raise ValueError("order_option_nos는 비어있을 수 없습니다.")
        
        url = f"{self.config.base_url}/orders/prepare-delivery"
        headers = self._get_headers()
        headers["version"] = "1.0"  # API 요구사항에 맞춰 version 헤더 추가
        
        payload = order_option_nos
        
        try:
            print(f"🚚 샵바이 배송준비중 상태 변경 요청:")
            print(f"  URL: {url}")
            print(f"  Headers: {headers}")
            print(f"  Payload: {payload}")
            print(f"  대상 옵션 수: {len(order_option_nos)}개")
            
            async with self.session.put(url, headers=headers, json=payload) as response:
                print(f"  Response Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ 배송준비중 상태 변경 성공: {len(order_option_nos)}개 옵션")
                    return {
                        "status": "success",
                        "message": f"{len(order_option_nos)}개 옵션을 배송준비중 상태로 변경했습니다.",
                        "data": result,
                        "processed_count": len(order_option_nos)
                    }
                else:
                    error_text = await response.text()
                    print(f"❌ 배송준비중 상태 변경 실패: {response.status}")
                    print(f"  Error Response: {error_text}")
                    
                    return {
                        "status": "error",
                        "message": f"배송준비중 상태 변경 실패 (HTTP {response.status})",
                        "error": error_text,
                        "processed_count": 0
                    }
                    
        except aiohttp.ClientError as e:
            print(f"❌ 샵바이 API 호출 오류: {e}")
            return {
                "status": "error",
                "message": f"샵바이 API 호출 오류: {str(e)}",
                "error": str(e),
                "processed_count": 0
            }
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return {
                "status": "error",
                "message": f"예상치 못한 오류: {str(e)}",
                "error": str(e),
                "processed_count": 0
            }


# 사용 예시 및 테스트 함수
async def test_shopby_api():
    """샵바이 API 테스트"""
    from config import load_app_config
    
    config = load_app_config()
    
    async with ShopbyApiClient(config.shopby) as client:
        print("샵바이 API 테스트 시작...")
        
        # 오늘 주문 조회
        orders = await client.get_today_orders()
        print(f"오늘 주문 수: {len(orders)}")
        
        if orders:
            print("첫 번째 주문 샘플:")
            print(json.dumps(orders[0], indent=2, ensure_ascii=False))
            
            # 첫 번째 주문의 상세 정보 조회
            if "orderNo" in orders[0]:
                details = await client.get_order_details(orders[0]["orderNo"])
                if details:
                    print("\n주문 상세 정보:")
                    print(json.dumps(details, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_shopby_api())
