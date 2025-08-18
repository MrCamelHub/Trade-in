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
            "/test": "Test workflow"
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
