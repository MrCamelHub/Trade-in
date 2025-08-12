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
            
            # 샵바이 productManagementCd 추출 (기본 goodsId로 사용)
            product_management_cd = (
                item.get("productManagementCd") or 
                item.get("product_management_cd") or 
                item.get("productCode") or 
                item.get("sku") or 
                799109  # 최후 기본값
            )
            
            # SKU 매핑 적용하여 goodsId 결정
            goods_id = product_management_cd  # 기본적으로 productManagementCd 사용
            
            if sku_mapping and original_sku in sku_mapping:
                mapped_value = str(sku_mapping[original_sku]).strip()
                
                # 경우 1: AAAAAA0000 형식인지 확인 (6자리 대문자 + 4자리 숫자)
                import re
                if re.match(r'^[A-Z]{6}\d{4}$', mapped_value):
                    goods_id = mapped_value  # 경우 1이면 매핑값 사용
                else:
                    # 경우 1이 아니면 샵바이 productManagementCd 그대로 사용
                    goods_id = int(product_management_cd) if str(product_management_cd).isdigit() else product_management_cd
            
            # 코너로지스 API 스펙에 맞는 데이터 구조 (완전 매핑)
            outbound_item = {
                "companyOrderId": self._extract_company_order_id(shopby_order),
                "companyMemo": self._extract_company_memo(shopby_order, item),
                "orderAt": self._extract_order_at(shopby_order),
                "receiverName": self._extract_receiver_name(shopby_order),
                "receiverPhone": self._extract_receiver_phone(shopby_order),
                "receiverAddress": self._extract_receiver_address(shopby_order),
                "receiverZipcode": self._extract_receiver_zipcode(shopby_order),
                "receiverMemo": self._extract_receiver_memo(shopby_order),
                "price": self._extract_price(item),
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
    
    def _extract_company_order_id(self, shopby_order: Dict[str, Any]) -> str:
        """주문번호 추출"""
        return (
            shopby_order.get("orderNo") or 
            shopby_order.get("order_no") or 
            shopby_order.get("orderNumber") or 
            ""
        )
    
    def _extract_company_memo(self, shopby_order: Dict[str, Any], item: Dict[str, Any]) -> str:
        """회사 메모 생성"""
        # 주문 경로/채널 정보 추출
        channel_info = ""
        
        # 결제 방식 정보
        pay_type = shopby_order.get("payType", "")
        if pay_type == "NAVER_PAY":
            channel_info = "네이버페이"
        elif pay_type:
            channel_info = pay_type
        
        # 플랫폼 정보
        platform = shopby_order.get("platformType", "")
        if platform == "MOBILE_WEB":
            platform_info = "모바일"
        elif platform == "PC":
            platform_info = "PC"
        else:
            platform_info = platform
        
        # 상품명
        product_name = item.get("productName", "")
        
        # 메모 조합
        memo_parts = []
        if channel_info:
            memo_parts.append(channel_info)
        if platform_info:
            memo_parts.append(platform_info)
        if product_name:
            memo_parts.append(product_name)
        
        if memo_parts:
            return " - ".join(memo_parts)
        else:
            return "샵바이 주문"
    
    def _extract_order_at(self, shopby_order: Dict[str, Any]) -> str:
        """주문일시 추출 및 형식 변환"""
        order_date = (
            shopby_order.get("orderYmdt") or 
            shopby_order.get("orderDate") or 
            shopby_order.get("order_date") or 
            shopby_order.get("createdAt") or 
            shopby_order.get("created_at")
        )
        
        if order_date:
            try:
                if isinstance(order_date, str):
                    import pandas as pd
                    dt = pd.to_datetime(order_date)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    return str(order_date)
            except:
                return str(order_date)
        
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _extract_receiver_name(self, shopby_order: Dict[str, Any]) -> str:
        """수령인명 추출"""
        return (
            shopby_order.get("recipientName") or 
            shopby_order.get("receiver_name") or 
            shopby_order.get("receiverName") or 
            shopby_order.get("customerName") or 
            shopby_order.get("ordererName") or 
            ""
        )
    
    def _extract_receiver_phone(self, shopby_order: Dict[str, Any]) -> str:
        """수령인 전화번호 추출"""
        phone = (
            shopby_order.get("recipientPhone") or 
            shopby_order.get("recipient_phone") or 
            shopby_order.get("receiverPhone") or 
            shopby_order.get("receiverContact1") or 
            shopby_order.get("customerPhone") or 
            shopby_order.get("ordererContact1") or 
            ""
        )
        
        # 전화번호 형식 정리
        if phone:
            # 숫자만 추출 후 하이픈 추가
            import re
            numbers = re.sub(r'[^\d]', '', str(phone))
            if len(numbers) == 11 and numbers.startswith('010'):
                return f"{numbers[:3]}-{numbers[3:7]}-{numbers[7:]}"
            elif len(numbers) == 10:
                return f"{numbers[:3]}-{numbers[3:6]}-{numbers[6:]}"
            else:
                return phone
        
        return ""
    
    def _extract_receiver_address(self, shopby_order: Dict[str, Any]) -> str:
        """수령인 주소 추출 및 통합"""
        address1 = (
            shopby_order.get("deliveryAddress1") or 
            shopby_order.get("address1") or 
            shopby_order.get("receiverAddress") or 
            ""
        )
        
        address2 = (
            shopby_order.get("deliveryAddress2") or 
            shopby_order.get("address2") or 
            shopby_order.get("receiverDetailAddress") or 
            ""
        )
        
        # 주소 통합
        if address1 and address2:
            return f"{address1} {address2}".strip()
        elif address1:
            return address1
        elif address2:
            return address2
        else:
            return ""
    
    def _extract_receiver_zipcode(self, shopby_order: Dict[str, Any]) -> str:
        """우편번호 추출"""
        zipcode = (
            shopby_order.get("deliveryZipCode") or 
            shopby_order.get("zipCode") or 
            shopby_order.get("zip_code") or 
            shopby_order.get("receiverZipCd") or 
            shopby_order.get("postCode") or 
            ""
        )
        
        # 우편번호 형식 정리 (숫자만)
        if zipcode:
            import re
            return re.sub(r'[^\d]', '', str(zipcode))
        
        return ""
    
    def _extract_receiver_memo(self, shopby_order: Dict[str, Any]) -> str:
        """배송 메모 추출"""
        memo = (
            shopby_order.get("deliveryMemo") or 
            shopby_order.get("delivery_memo") or 
            shopby_order.get("receiverMemo") or 
            shopby_order.get("shippingMemo") or 
            shopby_order.get("orderMemo") or 
            shopby_order.get("memo") or 
            ""
        )
        
        # 메모 길이 제한 (100자)
        if memo and len(str(memo)) > 100:
            return str(memo)[:100] + "..."
        
        return str(memo) if memo else ""
    
    def _extract_price(self, item: Dict[str, Any]) -> int:
        """상품 가격 추출"""
        price = (
            item.get("totalPrice") or 
            item.get("total_price") or 
            item.get("adjustedAmt") or 
            item.get("salePrice") or 
            item.get("unitPrice") or 
            item.get("unit_price") or 
            0
        )
        
        try:
            return int(float(price))
        except (ValueError, TypeError):
            return 0


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
