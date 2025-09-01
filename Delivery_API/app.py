"""
Bonibello Delivery API
송장입력, 발송처리, 발송완료처리 전용 API 서버
"""

from flask import Flask, jsonify, request
from datetime import datetime
import asyncio
import os

app = Flask(__name__)

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
            "/test": "Test workflow",
            "/execute": "전체 워크플로우 실행 (항상 dry_run=false)",
            "/scheduler/status": "스케줄러 상태 확인",
            "/scheduler/start": "스케줄러 시작 (백그라운드)",
            "/exclusions": "제외 주문 목록 조회/관리"
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

@app.route('/execute')
def execute_workflow():
    """전체 워크플로우 실행 (항상 dry_run=false)"""
    try:
        from invoice_tracker import InvoiceTracker
        
        async def run_full_workflow():
            async with InvoiceTracker() as tracker:
                # 1. 송장번호 업데이트 대상 조회
                candidates = await tracker.get_orders_needing_update()
                
                # 2. 송장번호 동기화 실행 (dry_run=false)
                sync_result = await tracker.run_full_sync(dry_run=False)
                
                # 3. 전체 워크플로우 결과 반환
                return {
                    "workflow": "full_execution",
                    "dry_run": False,
                    "candidates_count": len(candidates),
                    "sync_result": sync_result,
                    "execution_time": datetime.now().isoformat()
                }
        
        result = asyncio.run(run_full_workflow())
        
        return jsonify({
            "status": "success",
            "message": "전체 워크플로우 실행 완료 (dry_run=false)",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scheduler/status')
def scheduler_status():
    """스케줄러 상태 확인"""
    try:
        from scheduler import is_weekday_kst, is_business_hours_kst, should_run_now, get_next_run_time
        import pytz
        
        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)
        
        # 스케줄러 상태 계산
        is_weekday = is_weekday_kst()
        is_business_hours = is_business_hours_kst()
        should_run = should_run_now()
        next_run_time = get_next_run_time()
        
        status_info = {
            "current_time": now.isoformat(),
            "timezone": "Asia/Seoul",
            "is_weekday": is_weekday,
            "is_business_hours": is_business_hours,
            "should_run_now": should_run,
            "next_run_time": next_run_time.isoformat() if next_run_time else None,
            "schedule": {
                "description": "평일 9:00 ~ 19:00, 30분마다 실행",
                "business_start": "09:00",
                "business_end": "19:00",
                "interval": "30분"
            }
        }
        
        return jsonify({
            "status": "success",
            "scheduler_status": status_info,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scheduler/start', methods=['POST'])
def start_scheduler():
    """스케줄러 시작 (백그라운드에서 실행)"""
    try:
        import threading
        import asyncio
        
        def run_scheduler_in_thread():
            """별도 스레드에서 스케줄러 실행"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                from scheduler import run_continuous_scheduler
                loop.run_until_complete(run_continuous_scheduler())
            except Exception as e:
                print(f"스케줄러 스레드 오류: {e}")
        
        # 백그라운드에서 스케줄러 시작
        scheduler_thread = threading.Thread(target=run_scheduler_in_thread, daemon=True)
        scheduler_thread.start()
        
        return jsonify({
            "status": "success",
            "message": "스케줄러가 백그라운드에서 시작되었습니다",
            "thread_id": scheduler_thread.ident,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/exclusions', methods=['GET'])
def get_exclusions():
    """제외 주문 목록 조회"""
    try:
        from invoice_tracker import InvoiceTracker
        
        # InvoiceTracker 인스턴스 생성해서 제외 목록 조회
        tracker = InvoiceTracker()
        exclusions = tracker.excluded_orders
        
        return jsonify({
            "status": "success",
            "excluded_orders": exclusions,
            "count": len(exclusions),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/exclusions/<order_no>', methods=['DELETE'])
def remove_exclusion(order_no):
    """특정 주문을 제외 목록에서 제거"""
    try:
        # 실제 운영 환경에서는 데이터베이스나 파일에서 관리해야 함
        # 현재는 메모리에서만 관리되므로 서버 재시작 시 초기화됨
        return jsonify({
            "status": "info",
            "message": f"주문번호 {order_no} 제외 해제 요청을 받았습니다. 현재는 코드 수정이 필요합니다.",
            "note": "제외 목록은 invoice_tracker.py 파일에서 관리됩니다.",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 스케줄러 자동 시작
    try:
        import threading
        import asyncio
        
        def start_scheduler_background():
            """백그라운드에서 스케줄러 시작"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                from scheduler import run_continuous_scheduler
                loop.run_until_complete(run_continuous_scheduler())
            except Exception as e:
                print(f"❌ 스케줄러 백그라운드 실행 오류: {e}")
        
        # 백그라운드에서 스케줄러 시작
        scheduler_thread = threading.Thread(target=start_scheduler_background, daemon=True)
        scheduler_thread.start()
        print(f"🚀 스케줄러가 백그라운드에서 시작되었습니다 (Thread ID: {scheduler_thread.ident})")
        
    except Exception as e:
        print(f"❌ 스케줄러 시작 실패: {e}")
    
    # Flask 앱 시작
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
