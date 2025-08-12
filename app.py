"""
Railway 배포용 메인 엔트리 포인트
Ship_API와 기존 시스템을 모두 지원
"""

import os
import asyncio
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "service": "Bonibello Ship API",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/run": "Manual run Ship_API",
            "/test": "Test Ship_API workflow"
        }
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/run')
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

if __name__ == '__main__':
    # Railway에서는 PORT 환경변수를 사용
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
