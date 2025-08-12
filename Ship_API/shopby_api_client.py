from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import pytz
from .config import ShopbyApiConfig


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
            async with self.session.get(url, headers=headers, params=params) as response:
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


# 사용 예시 및 테스트 함수
async def test_shopby_api():
    """샵바이 API 테스트"""
    from .config import load_app_config
    
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
