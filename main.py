#!/usr/bin/env python3
"""
Bonibello Trade-in 자동화 시스템
- 슬랙 메시지 → 구글시트 입력
- 구글시트 특정열 업데이트 → 슬랙 알림 + 카카오톡 알림톡
"""

import threading
import time
import os
from flask import Flask
from dotenv import load_dotenv

# 기존 모듈들 import
from slack_to_sheets import app as slack_app
from sheets_to_slack import monitor_columns, test_slack_connection

# 환경변수 로드
load_dotenv()

def run_flask_app():
    """슬랙 웹훅을 받기 위한 Flask 앱 실행"""
    print("🚀 Starting Flask webhook server...")
    port = int(os.environ.get('PORT', 5000))  # Railway는 PORT 환경변수 사용
    slack_app.run(host='0.0.0.0', port=port, debug=False)

def run_sheet_monitor():
    """구글시트 모니터링 실행"""
    print("📊 Starting Google Sheets monitor...")
    
    # 슬랙 연결 테스트
    if test_slack_connection():
        print("✅ Slack connection test successful, starting monitoring...")
        monitor_columns()  # M열과 L열 모두 모니터링
    else:
        print("❌ Slack connection test failed, please check configuration.")
        # 연결 실패 시에도 재시도 로직
        while True:
            time.sleep(300)  # 5분 대기 후 재시도
            print("🔄 Retrying Slack connection...")
            if test_slack_connection():
                print("✅ Slack connection restored, starting monitoring...")
                monitor_columns()
                break

def main():
    """메인 함수 - Flask 앱을 메인으로 실행하고 시트 모니터를 백그라운드로 실행"""
    print("=" * 60)
    print("🎯 Bonibello Trade-in 자동화 시스템 시작")
    print("=" * 60)
    print("📌 기능:")
    print("   1. 슬랙 메시지 → 구글시트 자동 입력")
    print("   2. 구글시트 M열(송장번호) 업데이트 → 슬랙 + 카카오톡 알림")
    print("   3. 구글시트 L열(물류센터 도착) 업데이트 → 슬랙 알림")
    print("=" * 60)
    
    # 환경변수 확인
    required_env_vars = [
        'SLACK_BOT_TOKEN',
        'SPREADSHEET_ID',
        'GOOGLE_APPLICATION_CREDENTIALS_JSON'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ 필수 환경변수가 누락되었습니다: {', '.join(missing_vars)}")
        return
    
    print("✅ 환경변수 확인 완료")
    
    # 시트 모니터링을 백그라운드 스레드로 실행
    monitor_thread = threading.Thread(target=run_sheet_monitor, daemon=True)
    monitor_thread.start()
    
    # Flask 앱을 메인 스레드에서 실행 (Railway 웹 서비스용)
    run_flask_app()

if __name__ == '__main__':
    main()