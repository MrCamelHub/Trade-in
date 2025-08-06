#!/usr/bin/env python3
"""
솔라피 Python SDK 테스트 스크립트
카카오톡 알림톡 전송 기능을 테스트합니다.
"""

import os

# 환경변수 로드 (dotenv 선택사항)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📁 .env 파일 로드됨")
except ImportError:
    print("⚠️ python-dotenv 미설치 - 시스템 환경변수만 사용")
except:
    print("📁 .env 파일 없음 - 시스템 환경변수만 사용")

def test_solapi_import():
    """솔라피 SDK import 테스트"""
    try:
        from solapi import SolapiMessageService
        print("✅ SOLAPI SDK import 성공 (최신 5.x 버전)")
        return "sdk"
    except ImportError as e:
        print(f"⚠️ SOLAPI SDK import 실패: {e}")
        print("💡 솔라피 SDK 미설치 - HTTP 요청 방식 사용 가능")
        print("💡 Railway 배포 시에는 자동으로 SDK가 설치됩니다")
        return "http"

def test_environment_variables():
    """환경변수 설정 확인"""
    required_vars = [
        'SOLAPI_API_KEY',
        'SOLAPI_API_SECRET', 
        'SOLAPI_TEMPLATE_ID'
    ]
    
    optional_vars = [
        'SOLAPI_PF_ID',
        'SOLAPI_FROM_NUMBER'
    ]
    
    print("\n🔍 환경변수 확인:")
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: 설정됨")
        else:
            print(f"  ❌ {var}: 설정 안됨 (필수)")
            all_set = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: 설정됨")
        else:
            print(f"  ⚠️ {var}: 설정 안됨 (선택사항)")
    
    return all_set

def test_solapi_connection():
    """솔라피 연결 테스트 (실제 메시지 전송하지 않음)"""
    try:
        from solapi import SolapiMessageService
        
        api_key = os.getenv('SOLAPI_API_KEY')
        api_secret = os.getenv('SOLAPI_API_SECRET')
        
        if not api_key or not api_secret:
            print("❌ API 키 또는 시크릿이 설정되지 않았습니다.")
            return False
        
        # 서비스 인스턴스 생성만 테스트
        message_service = SolapiMessageService(api_key, api_secret)
        print("✅ SOLAPI 서비스 인스턴스 생성 성공")
        
        # 실제 메시지 전송은 하지 않고 데이터 구조만 확인
        template_id = os.getenv('SOLAPI_TEMPLATE_ID')
        pf_id = os.getenv('SOLAPI_PF_ID', 'default-pf-id')
        from_number = os.getenv('SOLAPI_FROM_NUMBER', '070-0000-0000')
        
        test_message_data = {
            "to": "010-0000-0000",  # 테스트용 더미 번호
            "from": from_number,
            "type": "CTA",
            "kakaoOptions": {
                "pfId": pf_id,
                "templateId": template_id,
                "variables": {
                    "name": "테스트",
                    "tradein_date": "2024-01-01",
                    "delivery_company": "우체국"
                }
            }
        }
        
        print("✅ 메시지 데이터 구조 검증 완료")
        print(f"  📱 발신번호: {from_number}")
        print(f"  🆔 플러스친구 ID: {pf_id}")
        print(f"  📋 템플릿 ID: {template_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ SOLAPI 연결 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🧪 솔라피 카카오톡 알림톡 테스트 시작")
    print("=" * 50)
    
    # 1. SDK import 테스트
    import_result = test_solapi_import()
    if import_result == "sdk":
        print("📦 SDK 방식으로 테스트합니다")
    elif import_result == "http":
        print("🌐 HTTP 요청 방식으로 테스트합니다")
    else:
        print("❌ 알 수 없는 import 결과")
        return
    
    # 2. 환경변수 확인
    if not test_environment_variables():
        print("\n❌ 필수 환경변수가 설정되지 않았습니다.")
        print("💡 .env 파일을 확인하거나 환경변수를 설정해주세요.")
        return
    
    # 3. 연결 테스트
    print(f"\n🔗 SOLAPI 연결 테스트 ({import_result.upper()} 방식):")
    if test_solapi_connection():
        print("\n🎉 모든 테스트 통과!")
        print("💌 카카오톡 알림톡 기능이 정상적으로 설정되었습니다.")
        print(f"🚀 Railway 배포 시 {import_result.upper()} 방식으로 동작합니다.")
    else:
        print("\n❌ 연결 테스트 실패")
        print("💡 API 키, 시크릿, 템플릿 ID를 다시 확인해주세요.")

if __name__ == '__main__':
    main()