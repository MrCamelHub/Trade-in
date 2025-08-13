"""
Ship_API Railway 배포용 메인 엔트리 포인트
기존 시스템과 분리된 독립적인 서비스
"""

import os
import asyncio
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "service": "Bonibello Ship API",
        "version": "2.0",
        "description": "샵바이 API → 코너로지스 API 자동 주문 전송",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/run": "Manual run Ship_API",
            "/test": "Test Ship_API workflow",
            "/status": "Service status",
            "/schedule": "Check schedule condition"
        },
        "schedule": "평일 13:00 KST 자동 실행"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ship-api"
    })

@app.route('/status')
def status():
    """서비스 상태 확인"""
    try:
        from main import should_run_now_kst
        from config import load_app_config
        
        config = load_app_config()
        should_run = should_run_now_kst()
        
        return jsonify({
            "service": "ship-api",
            "timestamp": datetime.now().isoformat(),
            "should_run_now": should_run,
            "config": {
                "shopby_api_url": config.shopby.base_url,
                "cornerlogis_api_url": config.cornerlogis.base_url,
                "data_dir": str(config.data_dir),
                "has_cornerlogis_api_key": bool(config.cornerlogis.api_key)
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run', methods=['POST'])
def run_ship_api():
    """Ship_API 수동 실행"""
    try:
        from Ship_API.main import run_once
        result = asyncio.run(run_once())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test')
def test_ship_api():
    """Ship_API 테스트"""
    try:
        from Ship_API.main import test_workflow
        result = asyncio.run(test_workflow())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/schedule')
def check_schedule():
    """스케줄 조건 확인"""
    try:
        from Ship_API.main import scheduled_run
        result = asyncio.run(scheduled_run())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/env', methods=['GET'])
def check_env_vars():
    """환경변수 확인 (디버깅용)"""
    try:
        import os
        
        env_vars = {
            "SHOPBY_SYSTEM_KEY": os.getenv("SHOPBY_SYSTEM_KEY", "NOT_SET")[:20] + "..." if os.getenv("SHOPBY_SYSTEM_KEY") else "NOT_SET",
            "SHOPBY_AUTH_TOKEN": os.getenv("SHOPBY_AUTH_TOKEN", "NOT_SET")[:20] + "..." if os.getenv("SHOPBY_AUTH_TOKEN") else "NOT_SET",
            "CORNERLOGIS_API_KEY": os.getenv("CORNERLOGIS_API_KEY", "NOT_SET"),
            "MAPPING_SHEET_ID": os.getenv("MAPPING_SHEET_ID", "NOT_SET"),
            "MAPPING_TAB_NAME": os.getenv("MAPPING_TAB_NAME", "NOT_SET"),
            "LOGGING_SHEET_ID": os.getenv("LOGGING_SHEET_ID", "NOT_SET"),
            "LOGGING_TAB_NAME": os.getenv("LOGGING_TAB_NAME", "NOT_SET"),
            "PYTHONPATH": os.getenv("PYTHONPATH", "NOT_SET")
        }
        
        return jsonify({
            "status": "success",
            "environment_variables": env_vars,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/ip', methods=['GET'])
def get_server_ip():
    """서버 IP 주소 조회 (샵바이 API 등록용)"""
    try:
        import requests
        
        # 여러 IP 조회 서비스를 시도
        ip_services = [
            'https://ipv4.icanhazip.com',
            'https://api.ipify.org',
            'https://checkip.amazonaws.com',
            'https://ipecho.net/plain'
        ]
        
        server_ip = None
        used_service = None
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    server_ip = response.text.strip()
                    used_service = service
                    break
            except:
                continue
        
        if server_ip:
            return jsonify({
                "status": "success",
                "server_ip": server_ip,
                "service_used": used_service,
                "message": "이 IP를 샵바이 API에 등록해주세요",
                "registration_instruction": f"샵바이 관리자 페이지에서 API 접근 허용 IP에 {server_ip} 추가",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "error": "IP 조회 실패",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Railway에서는 PORT 환경변수를 사용
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
