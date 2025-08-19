#!/usr/bin/env python3
"""
Delivery API 스케줄러
평일 9시부터 저녁 7시까지 30분마다 송장번호 동기화 실행
"""

import asyncio
import pytz
from datetime import datetime, time, timedelta
from invoice_tracker import InvoiceTracker


def is_weekday_kst() -> bool:
    """평일(월~금)인지 확인 (한국 시간 기준)"""
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    weekday = now.weekday()  # 0=월요일, 6=일요일
    
    # 월~금 (0-4)
    return weekday < 5


def is_business_hours_kst() -> bool:
    """평일 9시부터 저녁 7시까지인지 확인 (한국 시간 기준)"""
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    
    # 평일이 아니면 False
    if not is_weekday_kst():
        return False
    
    # 9:00 ~ 19:00 (저녁 7시) 체크
    business_start = time(9, 0)   # 9:00
    business_end = time(19, 0)    # 19:00 (저녁 7시)
    current_time = now.time()
    
    return business_start <= current_time <= business_end


def should_run_now() -> bool:
    """현재 실행해야 하는지 확인 (30분 간격)"""
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    
    # 평일 9시~19시가 아니면 False
    if not is_business_hours_kst():
        return False
    
    # 30분 간격 체크 (0분 또는 30분)
    minute = now.minute
    return minute in [0, 30]


async def run_scheduled_sync():
    """스케줄된 송장번호 동기화 실행"""
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    
    print(f"🕐 송장번호 동기화 스케줄러 실행: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # 실행 조건 체크
    if not is_weekday_kst():
        print(f"⏭️ 주말/공휴일이므로 스킵: {now.strftime('%A')}")
        return {
            "status": "skipped",
            "reason": "weekend",
            "timestamp": now.isoformat()
        }
    
    if not is_business_hours_kst():
        print(f"⏭️ 업무시간이 아니므로 스킵: {now.strftime('%H:%M')}")
        return {
            "status": "skipped",
            "reason": "outside_business_hours",
            "timestamp": now.isoformat()
        }
    
    print("✅ 평일 업무시간 - 송장번호 동기화 실행")
    
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


async def run_continuous_scheduler():
    """지속적으로 실행되는 스케줄러"""
    print("🚀 Delivery API 연속 스케줄러 시작")
    print("=" * 60)
    print("📅 스케줄: 평일 9:00 ~ 19:00, 30분마다 실행")
    print("=" * 60)
    
    while True:
        try:
            kst = pytz.timezone("Asia/Seoul")
            now = datetime.now(kst)
            
            # 현재 실행해야 하는지 확인
            if should_run_now():
                print(f"\n🔄 실행 조건 만족: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                result = await run_scheduled_sync()
                print(f"✅ 실행 완료: {result['status']}")
            else:
                # 다음 실행 시간 계산
                next_run = get_next_run_time()
                if next_run:
                    print(f"⏳ 다음 실행: {next_run.strftime('%H:%M')} (현재: {now.strftime('%H:%M')})")
            
            # 1분 대기
            await asyncio.sleep(60)
            
        except KeyboardInterrupt:
            print("\n🛑 사용자에 의해 스케줄러 중단됨")
            break
        except Exception as e:
            print(f"❌ 스케줄러 오류: {e}")
            await asyncio.sleep(60)  # 오류 발생 시 1분 대기


def get_next_run_time():
    """다음 실행 시간 계산"""
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    
    # 평일이 아니면 None
    if not is_weekday_kst():
        return None
    
    # 업무시간이 아니면 다음 평일 9시
    if not is_business_hours_kst():
        if now.time() < time(9, 0):
            # 오늘 9시
            return now.replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            # 다음 평일 9시
            days_ahead = (7 - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_weekday = now + timedelta(days=days_ahead)
            return next_weekday.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # 업무시간 내에서 다음 30분 간격
    current_minute = now.minute
    if current_minute < 30:
        next_minute = 30
    else:
        next_minute = 0
        next_hour = now.hour + 1
    
    if next_minute == 0:
        return now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    else:
        return now.replace(minute=next_minute, second=0, microsecond=0)


async def main():
    """메인 함수 (단일 실행)"""
    print("🚀 Delivery API 스케줄러 시작 (단일 실행)")
    print("=" * 50)
    
    result = await run_scheduled_sync()
    
    print("\n" + "=" * 50)
    print(f"🏁 스케줄러 완료: {result['status']}")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        # 연속 실행 모드
        asyncio.run(run_continuous_scheduler())
    else:
        # 단일 실행 모드
        asyncio.run(main())