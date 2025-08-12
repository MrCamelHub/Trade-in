from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd


class ShopbyToCornerlogisTransformer:
    """샵바이 주문 데이터를 코너로지스 출고 데이터로 변환하는 클래스"""
    
    def __init__(self, sku_mapping: Optional[Dict[str, str]] = None):
        """
        Args:
            sku_mapping: SKU 매핑 딕셔너리 {shopby_sku: cornerlogis_sku}
        """
        self.sku_mapping = sku_mapping or {}
    
    def transform_order(self, shopby_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 샵바이 주문을 코너로지스 출고 데이터로 변환
        
        Args:
            shopby_order: 샵바이 주문 데이터
        
        Returns:
            코너로지스 API 형식의 출고 데이터
        """
        # 기본 주문 정보 추출
        order_no = self._extract_order_no(shopby_order)
        customer_info = self._extract_customer_info(shopby_order)
        delivery_info = self._extract_delivery_info(shopby_order)
        items = self._transform_items(shopby_order)
        
        # 코너로지스 출고 데이터 구성
        cornerlogis_data = {
            "orderNo": order_no,
            "orderDate": self._extract_order_date(shopby_order),
            "customer": customer_info,
            "delivery": delivery_info,
            "items": items,
            "totalAmount": self._calculate_total_amount(items),
            "memo": self._extract_memo(shopby_order),
            "urgency": self._determine_urgency(shopby_order),
            "shippingMethod": self._extract_shipping_method(shopby_order)
        }
        
        return cornerlogis_data
    
    def transform_orders(self, shopby_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        여러 샵바이 주문을 배치로 변환
        
        Args:
            shopby_orders: 샵바이 주문 데이터 리스트
        
        Returns:
            변환된 코너로지스 출고 데이터 리스트
        """
        transformed_orders = []
        
        for i, order in enumerate(shopby_orders):
            try:
                transformed = self.transform_order(order)
                transformed_orders.append(transformed)
                print(f"주문 변환 완료: {i+1}/{len(shopby_orders)} - {transformed['orderNo']}")
            except Exception as e:
                print(f"주문 변환 실패 ({i+1}번째): {e}")
                print(f"원본 데이터: {json.dumps(order, indent=2, ensure_ascii=False)}")
                continue
        
        return transformed_orders
    
    def _extract_order_no(self, order: Dict[str, Any]) -> str:
        """주문번호 추출"""
        return (
            order.get("orderNo") or 
            order.get("order_no") or 
            order.get("orderNumber") or 
            order.get("id") or 
            ""
        )
    
    def _extract_order_date(self, order: Dict[str, Any]) -> str:
        """주문일시 추출 및 형식 변환"""
        order_date = (
            order.get("orderDate") or 
            order.get("order_date") or 
            order.get("createdAt") or 
            order.get("created_at")
        )
        
        if order_date:
            # 다양한 날짜 형식 처리
            try:
                if isinstance(order_date, str):
                    # ISO 형식 등 파싱
                    dt = pd.to_datetime(order_date)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    return str(order_date)
            except:
                return str(order_date)
        
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _extract_customer_info(self, order: Dict[str, Any]) -> Dict[str, str]:
        """고객 정보 추출"""
        return {
            "name": (
                order.get("customerName") or 
                order.get("customer_name") or 
                order.get("buyerName") or 
                order.get("buyer_name") or 
                ""
            ),
            "phone": (
                order.get("customerPhone") or 
                order.get("customer_phone") or 
                order.get("buyerPhone") or 
                order.get("buyer_phone") or 
                ""
            ),
            "email": (
                order.get("customerEmail") or 
                order.get("customer_email") or 
                order.get("buyerEmail") or 
                order.get("buyer_email") or 
                ""
            )
        }
    
    def _extract_delivery_info(self, order: Dict[str, Any]) -> Dict[str, str]:
        """배송 정보 추출"""
        return {
            "recipientName": (
                order.get("recipientName") or 
                order.get("recipient_name") or 
                order.get("receiverName") or 
                order.get("receiver_name") or 
                order.get("customerName") or 
                ""
            ),
            "recipientPhone": (
                order.get("recipientPhone") or 
                order.get("recipient_phone") or 
                order.get("receiverPhone") or 
                order.get("receiver_phone") or 
                order.get("customerPhone") or 
                ""
            ),
            "zipCode": (
                order.get("deliveryZipCode") or 
                order.get("delivery_zip_code") or 
                order.get("zipCode") or 
                order.get("zip_code") or 
                order.get("postCode") or 
                ""
            ),
            "address1": (
                order.get("deliveryAddress1") or 
                order.get("delivery_address1") or 
                order.get("address1") or 
                order.get("baseAddress") or 
                ""
            ),
            "address2": (
                order.get("deliveryAddress2") or 
                order.get("delivery_address2") or 
                order.get("address2") or 
                order.get("detailAddress") or 
                ""
            ),
            "memo": (
                order.get("deliveryMemo") or 
                order.get("delivery_memo") or 
                order.get("shippingMemo") or 
                ""
            )
        }
    
    def _transform_items(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """주문 상품 목록 변환"""
        # 다양한 키에서 상품 목록 추출
        items_raw = (
            order.get("items") or 
            order.get("orderItems") or 
            order.get("order_items") or 
            order.get("products") or 
            order.get("orderProducts") or 
            []
        )
        
        if not isinstance(items_raw, list):
            items_raw = [items_raw]
        
        transformed_items = []
        
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            
            # SKU 추출 및 매핑
            original_sku = (
                item.get("productCode") or 
                item.get("product_code") or 
                item.get("sku") or 
                item.get("itemCode") or 
                item.get("optionCode") or 
                ""
            )
            
            # SKU 매핑 적용
            mapped_sku = self.sku_mapping.get(original_sku, original_sku)
            
            transformed_item = {
                "productCode": mapped_sku,
                "originalProductCode": original_sku,
                "productName": (
                    item.get("productName") or 
                    item.get("product_name") or 
                    item.get("itemName") or 
                    item.get("name") or 
                    ""
                ),
                "optionName": (
                    item.get("optionName") or 
                    item.get("option_name") or 
                    item.get("optionText") or 
                    ""
                ),
                "quantity": int(item.get("quantity", 1) or item.get("qty", 1) or 1),
                "unitPrice": float(item.get("unitPrice", 0) or item.get("unit_price", 0) or 0),
                "totalPrice": float(item.get("totalPrice", 0) or item.get("total_price", 0) or 0),
                "weight": float(item.get("weight", 0) or 0),
                "size": (
                    item.get("size") or 
                    item.get("dimensions") or 
                    ""
                )
            }
            
            # 총 가격이 없으면 계산
            if transformed_item["totalPrice"] == 0 and transformed_item["unitPrice"] > 0:
                transformed_item["totalPrice"] = transformed_item["unitPrice"] * transformed_item["quantity"]
            
            transformed_items.append(transformed_item)
        
        return transformed_items
    
    def _calculate_total_amount(self, items: List[Dict[str, Any]]) -> float:
        """총 주문 금액 계산"""
        return sum(item.get("totalPrice", 0) for item in items)
    
    def _extract_memo(self, order: Dict[str, Any]) -> str:
        """주문 메모 추출"""
        return (
            order.get("memo") or 
            order.get("orderMemo") or 
            order.get("customerMemo") or 
            order.get("remarks") or 
            ""
        )
    
    def _determine_urgency(self, order: Dict[str, Any]) -> str:
        """배송 긴급도 결정"""
        shipping_type = (
            order.get("shippingType") or 
            order.get("delivery_type") or 
            ""
        ).lower()
        
        if "급송" in shipping_type or "특급" in shipping_type or "express" in shipping_type:
            return "URGENT"
        elif "일반" in shipping_type or "standard" in shipping_type:
            return "NORMAL"
        else:
            return "NORMAL"  # 기본값
    
    def _extract_shipping_method(self, order: Dict[str, Any]) -> str:
        """배송 방법 추출"""
        return (
            order.get("shippingMethod") or 
            order.get("shipping_method") or 
            order.get("deliveryMethod") or 
            order.get("deliveryType") or 
            "STANDARD"
        )
    
    def validate_transformed_data(self, data: Dict[str, Any]) -> List[str]:
        """변환된 데이터 유효성 검사"""
        errors = []
        
        # 필수 필드 검사
        required_fields = ["orderNo", "customer", "delivery", "items"]
        for field in required_fields:
            if not data.get(field):
                errors.append(f"필수 필드 누락: {field}")
        
        # 고객 정보 검사
        customer = data.get("customer", {})
        if not customer.get("name"):
            errors.append("고객명이 누락되었습니다")
        if not customer.get("phone"):
            errors.append("고객 전화번호가 누락되었습니다")
        
        # 배송 정보 검사
        delivery = data.get("delivery", {})
        if not delivery.get("address1"):
            errors.append("배송 주소가 누락되었습니다")
        
        # 상품 정보 검사
        items = data.get("items", [])
        if not items:
            errors.append("주문 상품이 없습니다")
        else:
            for i, item in enumerate(items):
                if not item.get("productCode"):
                    errors.append(f"상품 {i+1}의 상품 코드가 누락되었습니다")
                if not item.get("quantity") or item.get("quantity") <= 0:
                    errors.append(f"상품 {i+1}의 수량이 올바르지 않습니다")
        
        return errors


def create_sample_data():
    """샘플 데이터 생성 (테스트용)"""
    return {
        "orderNo": "ORD20241225001",
        "orderDate": "2024-12-25 14:30:00",
        "customerName": "홍길동",
        "customerPhone": "010-1234-5678",
        "customerEmail": "hong@example.com",
        "recipientName": "김영희",
        "recipientPhone": "010-9876-5432",
        "deliveryZipCode": "06234",
        "deliveryAddress1": "서울시 강남구 테헤란로 123",
        "deliveryAddress2": "ABC빌딩 456호",
        "deliveryMemo": "부재시 경비실에 맡겨주세요",
        "items": [
            {
                "productCode": "SKU001",
                "productName": "테스트 상품 1",
                "optionName": "블랙/L",
                "quantity": 2,
                "unitPrice": 25000,
                "totalPrice": 50000,
                "weight": 0.5
            },
            {
                "productCode": "SKU002",
                "productName": "테스트 상품 2",
                "quantity": 1,
                "unitPrice": 15000,
                "totalPrice": 15000,
                "weight": 0.3
            }
        ],
        "memo": "선물포장 요청",
        "shippingType": "일반배송"
    }


# 테스트 함수
def test_transformer():
    """데이터 변환기 테스트"""
    # SKU 매핑 예시
    sku_mapping = {
        "SKU001": "CL_SKU001",
        "SKU002": "CL_SKU002"
    }
    
    transformer = ShopbyToCornerlogisTransformer(sku_mapping)
    
    # 샘플 데이터 변환
    sample_order = create_sample_data()
    print("원본 샵바이 주문 데이터:")
    print(json.dumps(sample_order, indent=2, ensure_ascii=False))
    
    transformed = transformer.transform_order(sample_order)
    print("\n변환된 코너로지스 출고 데이터:")
    print(json.dumps(transformed, indent=2, ensure_ascii=False))
    
    # 유효성 검사
    errors = transformer.validate_transformed_data(transformed)
    if errors:
        print(f"\n유효성 검사 오류: {errors}")
    else:
        print("\n유효성 검사 통과!")


if __name__ == "__main__":
    test_transformer()
