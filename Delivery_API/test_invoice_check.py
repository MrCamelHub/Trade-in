#!/usr/bin/env python3
"""
송장번호 업데이트 대상 조회 테스트 스크립트
"""

import asyncio
import json
from invoice_tracker import InvoiceTracker


async def test_invoice_check():
    """송장번호 업데이트 대상 조회 테스트"""
    print("🚀 송장번호 업데이트 대상 조회 테스트 시작...")
    print("=" * 60)
    
    try:
        async with InvoiceTracker() as tracker:
            print("📡 코너로지스 API에서 송장번호가 있는 주문 조회 중...")
            candidates = await tracker.get_orders_needing_update()
            
            print(f"\n📊 조회 결과:")
            print(f"  총 업데이트 대상: {len(candidates)}건")
            
            if candidates:
                print(f"\n📋 업데이트 대상 상세:")
                for i, candidate in enumerate(candidates, 1):
                    print(f"\n  [{i}] 주문번호: {candidate['shopby_order_no']}")
                    print(f"      배송번호: {candidate['original_delivery_no']}")
                    print(f"      송장번호: {candidate['invoice_no']}")
                    print(f"      픽업완료: {candidate['pickup_complete_at']}")
                    print(f"      도착시간: {candidate['arrival_at']}")
                    print(f"      상태: {candidate['status']}")
            else:
                print("  ✨ 업데이트가 필요한 주문이 없습니다.")
                
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_invoice_check())
