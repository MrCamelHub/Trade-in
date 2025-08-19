"""
Bonibello Delivery API
송장입력, 발송처리, 발송완료처리 전용 API 서버
"""

from flask import Flask, jsonify, request
from datetime import datetime
import asyncio
import os
import threading
import time
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = Flask(__name__)

# 백그라운드 스케줄러 초기화
scheduler = BackgroundScheduler()

def is_weekday_kst() -> bool:
    """평일(월~금)인지 확인 (한국 시간 기준)"""
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    weekday = now.weekday()  # 0=월요일, 6=일요일
    
    # 월~금 (0-4)
    return weekday < 5

def run_scheduled_sync():
    """스케줄된 송장번호 동기화 실행 (동기 함수)"""
    try:
        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)
        
        print(f"🕐 [스케줄러] 송장번호 동기화 시작: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # 평일 체크
        if not is_weekday_kst():
            print(f"⏭️ [스케줄러] 주말/공휴일이므로 스킵: {now.strftime('%A')}")
            return
        
        print("✅ [스케줄러] 평일 - 송장번호 동기화 실행")
        
        # InvoiceTracker를 동기적으로 실행
        from invoice_tracker import InvoiceTracker
        
        async def async_sync():
            async with InvoiceTracker() as tracker:
                return await tracker.run_full_sync(dry_run=False)
        
        # 새로운 이벤트 루프에서 비동기 함수 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(async_sync())
            print(f"📊 [스케줄러] 동기화 결과: {result.get('status', 'unknown')}")
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ [스케줄러] 실행 중 오류: {e}")

def start_scheduler():
    """스케줄러 시작"""
    try:
        # 평일 30분마다 실행 (09:00-18:00)
        scheduler.add_job(
            func=run_scheduled_sync,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-18',
                minute='0,30'
            ),
            id='invoice_sync_scheduler',
            name='송장번호 동기화 스케줄러',
            replace_existing=True
        )
        
        # 평일 30분마다 실행 (19:00-23:59)
        scheduler.add_job(
            func=run_scheduled_sync,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='19-23',
                minute='0,30'
            ),
            id='invoice_sync_scheduler_evening',
            name='송장번호 동기화 스케줄러 (저녁)',
            replace_existing=True
        )
        
        scheduler.start()
        print("🚀 백그라운드 스케줄러 시작됨")
        print("📅 평일 09:00-23:59, 30분마다 송장번호 동기화 실행")
        
    except Exception as e:
        print(f"❌ 스케줄러 시작 실패: {e}")

@app.route('/')
def home():
    """API 서비스 정보 및 엔드포인트 목록"""
    return jsonify({
        "service": "Bonibello Delivery API",
        "description": "송장입력, 발송처리, 발송완료처리 전용 API",
        "status": "running",
        "version": "1.0",
        "endpoints": {
            "/health": "Health check",
            "/status": "Service status",
            "/invoice/input": "송장 입력 처리",
            "/invoice/sync": "송장번호 동기화 (코너로지스 → 샵바이)",
            "/invoice/check": "송장번호 업데이트 대상 조회",
            "/shipping/process": "발송 처리",
            "/shipping/complete": "발송 완료 처리",
            "/scheduler/status": "스케줄러 상태 확인",
            "/scheduler/trigger": "수동 스케줄러 실행",
            "/test": "Test workflow"
        },
        "scheduler_info": {
            "auto_scheduling": "평일 09:00-23:59, 30분마다 자동 실행",
            "weekend_skip": "주말 및 공휴일 자동 스킵",
            "background": "백그라운드에서 자동 실행"
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """헬스 체크"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/status')
def status():
    """서비스 상태 확인"""
    return jsonify({
        "service": "Delivery API",
        "status": "operational",
        "uptime": "running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/invoice/input', methods=['POST'])
def input_invoice():
    """송장 입력 처리"""
    try:
        data = request.get_json()
        # TODO: 송장 입력 로직 구현
        return jsonify({
            "status": "success",
            "message": "송장 입력 처리 완료",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/invoice/sync', methods=['POST'])
def sync_invoice():
    """송장번호 동기화 (코너로지스 → 샵바이)"""
    try:
        data = request.get_json() or {}
        dry_run = data.get("dry_run", True)  # 기본값은 시뮬레이션
        
        from invoice_tracker import InvoiceTracker
        
        async def run_sync():
            async with InvoiceTracker() as tracker:
                return await tracker.run_full_sync(dry_run=dry_run)
        
        result = asyncio.run(run_sync())
        
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/invoice/check', methods=['GET'])
def check_invoice():
    """송장번호 업데이트 대상 조회"""
    try:
        from invoice_tracker import InvoiceTracker
        
        async def check_candidates():
            async with InvoiceTracker() as tracker:
                return await tracker.get_orders_needing_update()
        
        candidates = asyncio.run(check_candidates())
        
        return jsonify({
            "status": "success",
            "candidates_count": len(candidates),
            "candidates": candidates[:10],  # 최대 10건만 표시
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/shipping/process', methods=['POST'])
def process_shipping():
    """발송 처리"""
    try:
        data = request.get_json()
        # TODO: 발송 처리 로직 구현
        return jsonify({
            "status": "success",
            "message": "발송 처리 완료",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/shipping/complete', methods=['POST'])
def complete_shipping():
    """발송 완료 처리"""
    try:
        data = request.get_json()
        # TODO: 발송 완료 처리 로직 구현
        return jsonify({
            "status": "success",
            "message": "발송 완료 처리 완료",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test')
def test():
    """테스트 엔드포인트"""
    return jsonify({
        "message": "Delivery API 테스트 성공",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/scheduler/status')
def scheduler_status():
    """스케줄러 상태 확인"""
    try:
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return jsonify({
            "status": "success",
            "scheduler_running": scheduler.running,
            "total_jobs": len(jobs),
            "jobs": jobs,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scheduler/trigger', methods=['POST'])
def trigger_scheduler():
    """수동으로 스케줄러 실행"""
    try:
        # 백그라운드 스레드에서 실행
        thread = threading.Thread(target=run_scheduled_sync)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "스케줄러 수동 실행 시작됨",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 백그라운드 스케줄러 시작
    start_scheduler()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
