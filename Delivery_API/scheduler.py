#!/usr/bin/env python3
"""
Delivery API 스케줄러
평일에만 30분마다 송장번호 동기화 실행
"""

import asyncio
import pytz
from datetime import datetime
from invoice_tracker import InvoiceTracker


def is_weekday_kst() -> bool:
    """평일(월~금)인지 확인 (한국 시간 기준)"""
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    weekday = now.weekday()  # 0=월요일, 6=일요일
    
    # 월~금 (0-4)
    return weekday < 5


async def run_scheduled_sync():
    """스케줄된 송장번호 동기화 실행"""
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    
    print(f"🕐 송장번호 동기화 스케줄러 시작: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # 평일 체크
    if not is_weekday_kst():
        print(f"⏭️ 주말/공휴일이므로 스킵: {now.strftime('%A')}")
        return {
            "status": "skipped",
            "reason": "weekend",
            "timestamp": now.isoformat()
        }
    
    print("✅ 평일 - 송장번호 동기화 실행")
    
    try:
        async with InvoiceTracker() as tracker:
            # 실제 동기화 실행 (dry_run=False)
            result = await tracker.run_full_sync(dry_run=False)
            
            print(f"📊 동기화 결과:")
            print(f"  상태: {result.get('status')}")
            print(f"  업데이트 대상: {result.get('candidates_found', 0)}건")
            
            if 'update_result' in result:
                update_result = result['update_result']
                print(f"  성공: {update_result.get('success_count', 0)}건")
                print(f"  실패: {update_result.get('failure_count', 0)}건")
            
            return result
            
    except Exception as e:
        print(f"❌ 스케줄 실행 중 오류: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": now.isoformat()
        }


async def main():
    """메인 함수"""
    print("🚀 Delivery API 스케줄러 시작")
    print("=" * 50)
    
    result = await run_scheduled_sync()
    
    print("\n" + "=" * 50)
    print(f"🏁 스케줄러 완료: {result['status']}")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())