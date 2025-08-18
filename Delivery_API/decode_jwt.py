#!/usr/bin/env python3
"""
JWT 토큰 디코드 및 만료시간 확인
"""

import base64
import json
from datetime import datetime

def decode_jwt_payload(token):
    """JWT 토큰의 payload 부분을 디코드"""
    try:
        # JWT는 header.payload.signature 형식
        parts = token.split('.')
        if len(parts) != 3:
            print("❌ 잘못된 JWT 형식")
            return None
        
        # payload 부분 디코드 (base64url)
        payload = parts[1]
        # base64url을 base64로 변환 (패딩 추가)
        payload += '=' * (4 - len(payload) % 4)
        payload = payload.replace('-', '+').replace('_', '/')
        
        decoded = base64.b64decode(payload)
        return json.loads(decoded.decode('utf-8'))
        
    except Exception as e:
        print(f"❌ JWT 디코드 실패: {e}")
        return None

def main():
    # 현재 사용 중인 토큰
    current_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwYXJ0bmVyTm8iOjEyNzk1OSwiYWRtaW5ObyI6MjE5NjI0LCJhY2Nlc3NpYmxlSXBzIjpbXSwidXNhZ2UiOiJTRVJWRVIiLCJhZG1pbklkIjoiam9zZXBoIiwiaXNzIjoiTkhOIENvbW1lcmNlIiwiYXBwTm8iOjE0ODksIm1hbGxObyI6Nzg1MjIsInNvbHV0aW9uVHlwZSI6IlNIT1BCWSIsImV4cCI6NDkwODU2MzAwMiwic2hvcE5vIjoxMDAzNzY1LCJpYXQiOjE3NTQ5NjMwMDJ9.rEYIdHOb68Pr4N47aRRPI4bdjuW4KAg_bqUDyoF49Zc"
    
    print("🔍 JWT 토큰 분석")
    print("=" * 50)
    
    payload = decode_jwt_payload(current_token)
    if payload:
        print("✅ JWT Payload 디코드 성공:")
        print(f"  파트너번호: {payload.get('partnerNo')}")
        print(f"  관리자번호: {payload.get('adminNo')}")
        print(f"  관리자ID: {payload.get('adminId')}")
        print(f"  발급자: {payload.get('iss')}")
        print(f"  앱번호: {payload.get('appNo')}")
        print(f"  몰번호: {payload.get('mallNo')}")
        print(f"  솔루션타입: {payload.get('solutionType')}")
        print(f"  발급시간: {datetime.fromtimestamp(payload.get('iat', 0))}")
        print(f"  만료시간: {datetime.fromtimestamp(payload.get('exp', 0))}")
        
        # 만료 여부 확인
        now = datetime.now()
        exp_time = datetime.fromtimestamp(payload.get('exp', 0))
        
        if now > exp_time:
            print(f"❌ 토큰이 만료되었습니다!")
            print(f"  현재시간: {now}")
            print(f"  만료시간: {exp_time}")
        else:
            print(f"✅ 토큰이 유효합니다")
            remaining = exp_time - now
            print(f"  남은시간: {remaining}")
    else:
        print("❌ JWT 디코드 실패")

if __name__ == "__main__":
    main()
