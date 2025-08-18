#!/usr/bin/env python3
"""
배송완료 처리 테스트
"""

import asyncio
from invoice_tracker import InvoiceTracker


async def test_delivery_completion():
    """배송완료 처리 테스트"""
    print("🚀 배송완료 처리 테스트 시작...")
    print("=" * 60)
    
    async with InvoiceTracker() as tracker:
        # 배송완료 처리가 필요한 주문들 조회
        completion_candidates = await tracker.get_orders_needing_delivery_completion()
        
        print(f"\n📊 배송완료 처리 대상: {len(completion_candidates)}건")
        
        if completion_candidates:
            print(f"\n📋 배송완료 처리 대상 상세:")
            for i, candidate in enumerate(completion_candidates, 1):
                print(f"  [{i}] 주문번호: {candidate['shopby_order_no']}")
                print(f"      배송번호: {candidate['original_delivery_no']}")
                print(f"      송장번호: {candidate['invoice_no']}")
                print(f"      배송완료: {candidate['arrival_at']}")


async def test_full_sync():
    """전체 동기화 테스트 (송장번호 업데이트 + 배송완료 처리)"""
    print("\n" + "=" * 80)
    print("🚀 전체 동기화 테스트 시작...")
    print("=" * 80)
    
    async with InvoiceTracker() as tracker:
        # DRY RUN 모드로 테스트
        result = await tracker.run_full_sync(dry_run=True)
        
        print(f"\n📊 전체 동기화 테스트 결과:")
        print(f"   상태: {result['status']}")
        print(f"   소요시간: {result.get('duration_seconds', 0):.2f}초")
        
        if 'invoice_update' in result:
            update_info = result['invoice_update']
            print(f"   송장번호 업데이트: {update_info['candidates_found']}건 대상")
            
        if 'delivery_completion' in result:
            completion_info = result['delivery_completion']
            print(f"   배송완료 처리: {completion_info['candidates_found']}건 대상")


if __name__ == "__main__":
    asyncio.run(test_delivery_completion())
    asyncio.run(test_full_sync())
