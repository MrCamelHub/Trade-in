from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import aiohttp
from .config import CornerlogisApiConfig


class CornerlogisApiClient:
    """코너로지스 API 클라이언트"""
    
    def __init__(self, config: CornerlogisApiConfig):
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
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json"
        }
        
        # API 키가 있다면 Authorization 헤더에 추가
        if self.config.api_key:
            headers["Authorization"] = self.config.api_key
        
        return headers
    
    async def create_outbound_order(
        self,
        order_data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        코너로지스 출고 주문 생성
        
        Args:
            order_data: 출고 주문 데이터 리스트 (API 스펙에 따라 배열로 전송)
        
        Returns:
            생성된 출고 주문 정보
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        url = f"{self.config.base_url}/api/v1/outbound/saveOutbound"
        headers = self._get_headers()
        
        try:
            async with self.session.post(
                url, 
                headers=headers, 
                json=order_data
            ) as response:
                response.raise_for_status()
                result = await response.json()
                print(f"코너로지스 출고 주문 생성 성공: {result}")
                return result
                
        except aiohttp.ClientError as e:
            print(f"코너로지스 API 호출 실패: {e}")
            # 응답 내용 출력 (디버깅용)
            try:
                error_text = await response.text()
                print(f"에러 응답: {error_text}")
            except:
                pass
            raise
        except json.JSONDecodeError as e:
            print(f"코너로지스 API 응답 파싱 실패: {e}")
            raise
    
    async def create_bulk_outbound_orders(
        self,
        orders_data: List[Dict[str, Any]]
    ) -> List[Optional[Dict[str, Any]]]:
        """
        여러 출고 주문을 배치로 생성
        
        Args:
            orders_data: 출고 주문 데이터 리스트
        
        Returns:
            생성 결과 리스트
        """
        results = []
        
        for i, order_data in enumerate(orders_data):
            try:
                print(f"출고 주문 생성 중... ({i+1}/{len(orders_data)})")
                result = await self.create_outbound_order(order_data)
                results.append(result)
                
                # API 호출 간격 조절 (API 제한 방지)
                if i < len(orders_data) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                print(f"출고 주문 생성 실패 ({i+1}번째): {e}")
                results.append(None)
        
        return results
    
    async def get_outbound_status(
        self, 
        outbound_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        출고 주문 상태 조회
        
        Args:
            outbound_id: 출고 주문 ID
        
        Returns:
            출고 주문 상태 정보
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        url = f"{self.config.base_url}/api/outbound/{outbound_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 404:
                    return None
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            print(f"출고 상태 조회 실패 (ID: {outbound_id}): {e}")
            return None
    
    def prepare_outbound_data(
        self,
        shopby_order: Dict[str, Any],
        sku_mapping: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        샵바이 주문 데이터를 코너로지스 출고 데이터로 변환
        
        Args:
            shopby_order: 샵바이 주문 데이터
            sku_mapping: SKU 매핑 딕셔너리
        
        Returns:
            코너로지스 API 형식의 출고 데이터 리스트
        """
        # 주문 상품 처리 - 각 상품별로 별도 출고 요청 생성
        items = shopby_order.get("items", []) or shopby_order.get("orderItems", [])
        outbound_data_list = []
        
        for item in items:
            original_sku = item.get("productCode", "") or item.get("sku", "")
            
            # SKU 매핑 적용하여 goodsId 찾기
            goods_id = None
            if sku_mapping and original_sku in sku_mapping:
                # 매핑된 값이 숫자라면 goodsId로 사용
                try:
                    goods_id = int(sku_mapping[original_sku])
                except (ValueError, TypeError):
                    # 매핑된 값이 숫자가 아니라면 기본값 사용
                    goods_id = 799109  # 기본 goodsId
            else:
                goods_id = 799109  # 기본 goodsId
            
            # 코너로지스 API 스펙에 맞는 데이터 구조
            outbound_item = {
                "companyOrderId": shopby_order.get("orderNo", ""),
                "companyMemo": f"샵바이 주문 - {item.get('productName', '')}",
                "orderAt": self._format_order_date(shopby_order.get("orderDate")),
                "receiverName": shopby_order.get("recipientName", "") or shopby_order.get("customerName", ""),
                "receiverPhone": shopby_order.get("recipientPhone", "") or shopby_order.get("customerPhone", ""),
                "receiverAddress": self._format_address(shopby_order),
                "receiverZipcode": shopby_order.get("deliveryZipCode", "") or shopby_order.get("zipCode", ""),
                "receiverMemo": shopby_order.get("deliveryMemo", "") or shopby_order.get("memo", ""),
                "price": int(item.get("totalPrice", 0) or item.get("unitPrice", 0) or 0),
                "goodsId": goods_id
            }
            
            outbound_data_list.append(outbound_item)
        
        return outbound_data_list
    
    def _format_order_date(self, order_date) -> str:
        """주문일시를 코너로지스 형식으로 변환"""
        if not order_date:
            from datetime import datetime
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 다양한 날짜 형식 처리
        try:
            if isinstance(order_date, str):
                import pandas as pd
                dt = pd.to_datetime(order_date)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return str(order_date)
        except:
            from datetime import datetime
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _format_address(self, shopby_order: Dict[str, Any]) -> str:
        """주소를 한 줄로 합쳐서 반환"""
        address1 = shopby_order.get("deliveryAddress1", "") or shopby_order.get("address1", "")
        address2 = shopby_order.get("deliveryAddress2", "") or shopby_order.get("address2", "")
        
        if address1 and address2:
            return f"{address1} {address2}".strip()
        elif address1:
            return address1
        elif address2:
            return address2
        else:
            return ""


# 사용 예시 및 테스트 함수
async def test_cornerlogis_api():
    """코너로지스 API 테스트"""
    from .config import load_app_config
    
    config = load_app_config()
    
    # 테스트 데이터 (코너로지스 API 스펙 예시와 동일)
    test_order = {
        "orderNo": "202501028568638",
        "orderDate": "2025-01-05 00:00:00",
        "customerName": "홍길동",
        "customerPhone": "010-1234-5678",
        "recipientName": "홍길동",
        "recipientPhone": "010-1234-5678",
        "deliveryZipCode": "11192",
        "deliveryAddress1": "경기도 포천시 내촌면 금강로 2223번길 24",
        "deliveryAddress2": "",
        "deliveryMemo": "경비실에 맡겨주세요.",
        "memo": "네이버 쇼핑 유입",
        "items": [
            {
                "productCode": "SKU001",
                "productName": "테스트상품",
                "quantity": 1,
                "unitPrice": 25000,
                "totalPrice": 25000
            }
        ]
    }
    
    async with CornerlogisApiClient(config.cornerlogis) as client:
        print("코너로지스 API 테스트 시작...")
        
        # 출고 데이터 준비
        outbound_data = client.prepare_outbound_data(test_order)
        print("준비된 출고 데이터:")
        print(json.dumps(outbound_data, indent=2, ensure_ascii=False))
        
        # API 호출 테스트 (실제 호출하지 않음)
        print("\n실제 API 호출은 주석 처리됨 (테스트 목적)")
        # result = await client.create_outbound_order(outbound_data)
        # print(f"생성 결과: {result}")


if __name__ == "__main__":
    asyncio.run(test_cornerlogis_api())
