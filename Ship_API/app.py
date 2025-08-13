"""
Ship_API Flask 웹 서버
샵바이 API → 코너로지스 API 자동 주문 전송 서비스
"""

import os
import asyncio
import json
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    """서비스 메인 페이지"""
    return jsonify({
        "service": "Bonibello Ship API",
        "version": "2.0",
        "description": "샵바이 API → 코너로지스 API 자동 주문 전송",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/run-shopby": "Manual run Shopby order fetch",
            "/run-cornerlogis": "Manual run Cornerlogis upload",
            "/run-full": "Manual run full workflow",
            "/test": "Test workflow",
            "/status": "Service status",
            "/schedule": "Check schedule condition"
        },
        "schedule": {
            "shopby": "평일 13:00 KST - 샵바이 주문 조회",
            "cornerlogis": "평일 13:30 KST - 코너로지스 업로드"
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """헬스체크 엔드포인트"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ship-api"
    })

@app.route('/status')
def status():
    """서비스 상태 확인"""
    try:
        from main import should_run_shopby_now_kst, should_run_cornerlogis_now_kst
        from config import load_app_config
        
        config = load_app_config()
        should_run_shopby = should_run_shopby_now_kst()
        should_run_cornerlogis = should_run_cornerlogis_now_kst()
        
        return jsonify({
            "service": "ship-api",
            "timestamp": datetime.now().isoformat(),
            "schedule": {
                "should_run_shopby_now": should_run_shopby,
                "should_run_cornerlogis_now": should_run_cornerlogis
            },
            "config": {
                "shopby_api_url": config.shopby.base_url,
                "cornerlogis_api_url": config.cornerlogis.base_url,
                "data_dir": str(config.data_dir),
                "has_shopby_credentials": bool(config.shopby.client_id and config.shopby.client_secret),
                "has_cornerlogis_api_key": bool(config.cornerlogis.api_key),
                "has_google_credentials": os.path.exists("youtube-crawling-457503-4fae546ec5fc.json")
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-shopby', methods=['POST'])
def run_shopby():
    """샵바이 주문 조회 수동 실행"""
    try:
        from main import process_shopby_orders
        result = asyncio.run(process_shopby_orders())
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-cornerlogis', methods=['POST'])
def run_cornerlogis():
    """코너로지스 업로드 수동 실행"""
    try:
        from main import process_cornerlogis_upload
        result = asyncio.run(process_cornerlogis_upload())
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-full', methods=['POST'])
def run_full():
    """전체 워크플로우 수동 실행"""
    try:
        from main import run_full_workflow
        result = asyncio.run(run_full_workflow())
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test')
def test():
    """워크플로우 테스트"""
    try:
        from main import test_connections
        result = asyncio.run(test_connections())
        return jsonify({
            "status": "test_completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/debug-shopby')
def debug_shopby():
    """샵바이 API 디버깅"""
    try:
        import asyncio
        from config import load_app_config
        from shopby_api_client import ShopbyApiClient
        
        async def debug_headers():
            config = load_app_config()
            
            debug_info = {
                "config": {
                    "base_url": config.shopby.base_url,
                    "system_key": config.shopby.system_key[:20] + "...",
                    "auth_token": config.shopby.auth_token[:50] + "...",
                    "version": config.shopby.version
                },
                "env_vars": {
                    "SHOPBY_API_BASE_URL": os.getenv("SHOPBY_API_BASE_URL"),
                    "SHOPBY_SYSTEM_KEY": os.getenv("SHOPBY_SYSTEM_KEY", "")[:20] + "..." if os.getenv("SHOPBY_SYSTEM_KEY") else None,
                    "SHOPBY_AUTH_TOKEN": os.getenv("SHOPBY_AUTH_TOKEN", "")[:50] + "..." if os.getenv("SHOPBY_AUTH_TOKEN") else None,
                    "SHOPBY_API_VERSION": os.getenv("SHOPBY_API_VERSION")
                }
            }
            
            # 헤더 생성 테스트
            async with ShopbyApiClient(config.shopby) as client:
                headers = client._get_headers()
                debug_info["headers"] = headers
                
                try:
                    # 간단한 API 호출 시도
                    orders = await client.get_all_pay_done_orders(days_back=1)
                    debug_info["api_call"] = "success"
                    debug_info["orders_count"] = len(orders) if orders else 0
                except Exception as api_error:
                    debug_info["api_call"] = "failed"
                    debug_info["api_error"] = str(api_error)
            
            return debug_info
        
        result = asyncio.run(debug_headers())
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/schedule-shopby', methods=['POST'])
def schedule_shopby():
    """스케줄된 샵바이 작업 실행"""
    try:
        from main import scheduled_shopby_run
        result = asyncio.run(scheduled_shopby_run())
        return jsonify({
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/schedule-cornerlogis', methods=['POST'])
def schedule_cornerlogis():
    """스케줄된 코너로지스 작업 실행"""
    try:
        from main import scheduled_cornerlogis_run
        result = asyncio.run(scheduled_cornerlogis_run())
        return jsonify({
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/env')
def debug_env():
    """환경변수 디버깅"""
    config = load_app_config()
    
    return jsonify({
        "shopby": {
            "base_url": config.shopby.base_url,
            "system_key": config.shopby.system_key,
            "auth_token": config.shopby.auth_token,
            "version": config.shopby.version
        },
        "cornerlogis": {
            "base_url": config.cornerlogis.base_url,
            "api_key": config.cornerlogis.api_key if config.cornerlogis.api_key else None
        },
        "timezone": config.timezone,
        "data_dir": config.data_dir,
        "raw_env": {
            "SHOPBY_API_BASE_URL": os.getenv("SHOPBY_API_BASE_URL"),
            "SHOPBY_SYSTEM_KEY": os.getenv("SHOPBY_SYSTEM_KEY"),
            "SHOPBY_AUTH_TOKEN": os.getenv("SHOPBY_AUTH_TOKEN"),
            "SHOPBY_API_VERSION": os.getenv("SHOPBY_API_VERSION"),
            "CORNERLOGIS_API_BASE_URL": os.getenv("CORNERLOGIS_API_BASE_URL"),
            "CORNERLOGIS_API_KEY": os.getenv("CORNERLOGIS_API_KEY"),
            "TZ": os.getenv("TZ")
        }
    })

@app.route('/logs')
def get_logs():
    """최근 로그 조회"""
    try:
        logs_dir = "data/logs"
        if not os.path.exists(logs_dir):
            return jsonify({"logs": [], "message": "No logs found"})
        
        log_files = []
        for file in os.listdir(logs_dir):
            if file.endswith('.log'):
                file_path = os.path.join(logs_dir, file)
                file_stat = os.stat(file_path)
                log_files.append({
                    "file": file,
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })
        
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            "logs": log_files[:10],  # 최근 10개 파일
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Railway에서는 PORT 환경변수를 사용
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
