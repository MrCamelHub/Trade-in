"""
테스트용 샵바이 주문 데이터 생성기
개발 API에서 테스트할 수 있는 dummy 주문 데이터를 생성합니다.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any


def create_test_order_1() -> Dict[str, Any]:
    """
    첫 번째 테스트 주문 (상품관리코드: 50000878, 50000879)
    """
    order_date = datetime.now()
    
    return {
        "orderNo": "TEST_ORDER_001",
        "orderDate": order_date.strftime("%Y-%m-%d %H:%M:%S"),
        "orderRequestTypes": "PAY_DONE",
        "orderStatus": "PAY_DONE",
        "customerName": "테스트고객1",
        "customerPhone": "010-1111-2222",
        "customerEmail": "test1@bonibello.com",
        "buyerName": "테스트고객1",
        "buyerPhone": "010-1111-2222",
        "buyerEmail": "test1@bonibello.com",
        "recipientName": "받는사람1",
        "recipientPhone": "010-3333-4444",
        "deliveryZipCode": "06234",
        "deliveryAddress1": "서울시 강남구 테헤란로 123",
        "deliveryAddress2": "ABC빌딩 101호",
        "deliveryMemo": "부재시 경비실에 맡겨주세요",
        "memo": "테스트 주문 1번",
        "shippingType": "일반배송",
        "shippingMethod": "STANDARD",
        "deliveryGroups": [
            {
                "receiverName": "받는사람1",
                "receiverContact1": "010-3333-4444",
                "receiverAddress": "서울시 강남구 테헤란로 123",
                "receiverDetailAddress": "ABC빌딩 101호",
                "receiverZipCd": "06234",
                "deliveryMemo": "부재시 경비실에 맡겨주세요",
                "orderProducts": [
                    {
                        "productManagementCd": "50000878",
                        "productName": "테스트상품 A",
                        "orderProductOptions": [
                            {
                                "orderCnt": 1,
                                "adjustedAmt": 25000,
                                "salePrice": 30000,
                                "optionName": "기본옵션"
                            }
                        ]
                    },
                    {
                        "productManagementCd": "50000879", 
                        "productName": "테스트상품 B",
                        "orderProductOptions": [
                            {
                                "orderCnt": 1,
                                "adjustedAmt": 15000,
                                "salePrice": 18000,
                                "optionName": "기본옵션"
                            }
                        ]
                    }
                ]
            }
        ],
        "items": [
            {
                "productCode": "50000878",
                "productManagementCd": "50000878",
                "productName": "테스트상품 A",
                "optionName": "기본옵션",
                "quantity": 1,
                "unitPrice": 25000,
                "totalPrice": 25000,
                "adjustedAmt": 25000,
                "salePrice": 30000,
                "weight": 0.5
            },
            {
                "productCode": "50000879",
                "productManagementCd": "50000879", 
                "productName": "테스트상품 B",
                "optionName": "기본옵션",
                "quantity": 1,
                "unitPrice": 15000,
                "totalPrice": 15000,
                "adjustedAmt": 15000,
                "salePrice": 18000,
                "weight": 0.3
            }
        ],
        "totalAmount": 40000,
        "createdAt": order_date.isoformat(),
        "created_at": order_date.isoformat()
    }


def create_test_order_2() -> Dict[str, Any]:
    """
    두 번째 테스트 주문 (상품관리코드: 142, 140)
    """
    order_date = datetime.now() - timedelta(minutes=30)
    
    return {
        "orderNo": "TEST_ORDER_002", 
        "orderDate": order_date.strftime("%Y-%m-%d %H:%M:%S"),
        "orderRequestTypes": "PAY_DONE",
        "orderStatus": "PAY_DONE",
        "customerName": "테스트고객2",
        "customerPhone": "010-5555-6666",
        "customerEmail": "test2@bonibello.com",
        "buyerName": "테스트고객2",
        "buyerPhone": "010-5555-6666", 
        "buyerEmail": "test2@bonibello.com",
        "recipientName": "받는사람2",
        "recipientPhone": "010-7777-8888",
        "deliveryZipCode": "13579",
        "deliveryAddress1": "경기도 성남시 분당구 판교로 100",
        "deliveryAddress2": "XYZ타워 20층",
        "deliveryMemo": "문 앞에 놓아주세요",
        "memo": "테스트 주문 2번",
        "shippingType": "일반배송",
        "shippingMethod": "STANDARD",
        "deliveryGroups": [
            {
                "receiverName": "받는사람2",
                "receiverContact1": "010-7777-8888",
                "receiverAddress": "경기도 성남시 분당구 판교로 100",
                "receiverDetailAddress": "XYZ타워 20층",
                "receiverZipCd": "13579",
                "deliveryMemo": "문 앞에 놓아주세요",
                "orderProducts": [
                    {
                        "productManagementCd": "142",
                        "productName": "테스트상품 C",
                        "orderProductOptions": [
                            {
                                "orderCnt": 1,
                                "adjustedAmt": 12000,
                                "salePrice": 15000,
                                "optionName": "화이트"
                            }
                        ]
                    },
                    {
                        "productManagementCd": "140",
                        "productName": "테스트상품 D",
                        "orderProductOptions": [
                            {
                                "orderCnt": 1,
                                "adjustedAmt": 35000,
                                "salePrice": 40000,
                                "optionName": "블랙/L"
                            }
                        ]
                    }
                ]
            }
        ],
        "items": [
            {
                "productCode": "142",
                "productManagementCd": "142",
                "productName": "테스트상품 C",
                "optionName": "화이트",
                "quantity": 1,
                "unitPrice": 12000,
                "totalPrice": 12000,
                "adjustedAmt": 12000,
                "salePrice": 15000,
                "weight": 0.2
            },
            {
                "productCode": "140",
                "productManagementCd": "140",
                "productName": "테스트상품 D",
                "optionName": "블랙/L",
                "quantity": 1,
                "unitPrice": 35000,
                "totalPrice": 35000,
                "adjustedAmt": 35000,
                "salePrice": 40000,
                "weight": 0.8
            }
        ],
        "totalAmount": 47000,
        "createdAt": order_date.isoformat(),
        "created_at": order_date.isoformat()
    }


def create_test_orders_list() -> List[Dict[str, Any]]:
    """
    테스트용 주문 리스트 생성 (샵바이 API 응답 형식에 맞춤)
    """
    orders = [create_test_order_1(), create_test_order_2()]
    
    # 샵바이 API 응답 구조에 맞게 래핑
    return [
        {
            "contents": orders,
            "totalCount": len(orders),
            "totalPages": 1,
            "currentPage": 1,
            "pageSize": 20
        }
    ]


def save_test_orders_to_file():
    """
    테스트 주문 데이터를 JSON 파일로 저장
    """
    import os
    from pathlib import Path
    
    # data/outputs 디렉토리 생성
    outputs_dir = Path("data/outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # 오늘 날짜 기준으로 파일명 생성
    today = datetime.now().strftime("%Y%m%d")
    
    # 테스트 주문 데이터 생성
    test_orders = create_test_orders_list()
    actual_orders = test_orders[0]['contents']  # 실제 주문 데이터만 추출
    
    # 파일 저장
    shopby_file = outputs_dir / f"shopby_orders_{today}.json"
    with open(shopby_file, 'w', encoding='utf-8') as f:
        json.dump(actual_orders, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ 테스트 샵바이 주문 저장: {shopby_file}")
    print(f"📦 생성된 주문 수: {len(actual_orders)}")
    
    # 주문 요약 출력
    for i, order in enumerate(actual_orders, 1):
        print(f"  주문 {i}: {order['orderNo']}")
        for item in order['items']:
            print(f"    - {item['productManagementCd']}: {item['productName']} (수량: {item['quantity']})")
    
    return shopby_file


def print_test_orders_summary():
    """
    생성할 테스트 주문 요약 출력
    """
    orders = [create_test_order_1(), create_test_order_2()]
    
    print("=" * 60)
    print("📦 테스트 주문 데이터 요약")
    print("=" * 60)
    
    for i, order in enumerate(orders, 1):
        print(f"\n🏷️  주문 {i}: {order['orderNo']}")
        print(f"   고객: {order['customerName']} ({order['customerPhone']})")
        print(f"   받는사람: {order['recipientName']} ({order['recipientPhone']})")
        print(f"   배송지: {order['deliveryAddress1']} {order['deliveryAddress2']}")
        print(f"   총 금액: {order['totalAmount']:,}원")
        print(f"   상품 목록:")
        
        for item in order['items']:
            print(f"     - {item['productManagementCd']}: {item['productName']}")
            print(f"       옵션: {item['optionName']}, 수량: {item['quantity']}, 가격: {item['totalPrice']:,}원")
    
    print("\n" + "=" * 60)
    print("💡 이 데이터를 사용하여 /run-full API 테스트를 실행합니다.")
    print("=" * 60)


if __name__ == "__main__":
    print_test_orders_summary()
    save_test_orders_to_file()
