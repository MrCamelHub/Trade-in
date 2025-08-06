from google.oauth2 import service_account
from googleapiclient.discovery import build
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import requests
import json

# Load environment variables
load_dotenv()

# Google Sheets configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SHEET_NAME = os.getenv('SHEET_NAME', '보니벨로 Trade-in_신청')  # 기본값 설정

# Slack configuration
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#08_biz_bonibello_request')  # 기본 채널
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# SOLAPI configuration for KakaoTalk
SOLAPI_API_KEY = os.getenv('SOLAPI_API_KEY')
SOLAPI_API_SECRET = os.getenv('SOLAPI_API_SECRET')
SOLAPI_TEMPLATE_ID = os.getenv('SOLAPI_TEMPLATE_ID')  # 알림톡 템플릿 ID
SOLAPI_PF_ID = os.getenv('SOLAPI_PF_ID', 'KA01PF240722030442524jxhTR86GIYZ')  # 플러스친구 ID
SOLAPI_FROM_NUMBER = os.getenv('SOLAPI_FROM_NUMBER', '070-4788-9600')  # 발신번호

def get_google_sheets_service():
    # Get service account JSON from environment variable
    service_account_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not service_account_json:
        raise Exception("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set")
    
    import json
    service_account_info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)
    
    return build('sheets', 'v4', credentials=credentials)

def get_m_column_data(service):
    """M열의 모든 데이터를 가져옵니다."""
    range_name = f'{SHEET_NAME}!M:M'
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name
    ).execute()
    return result.get('values', [])

def get_l_column_data(service):
    """L열의 모든 데이터를 가져옵니다."""
    range_name = f'{SHEET_NAME}!L:L'
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name
    ).execute()
    return result.get('values', [])

def get_spreadsheet_revision(service):
    """스프레드시트의 최신 수정 시간을 가져옵니다."""
    try:
        result = service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID
        ).execute()
        return result.get('properties', {}).get('modifiedTime')
    except Exception as e:
        print(f"Error getting spreadsheet revision: {e}")
        return None

def get_row_data(service, row_number):
    """특정 행의 데이터를 가져옵니다."""
    range_name = f'{SHEET_NAME}!A{row_number}:I{row_number}'
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name
    ).execute()
    values = result.get('values', [])
    return values[0] if values else []

def send_slack_message(message):
    """슬랙으로 메시지를 보냅니다."""
    try:
        # 채널 설정 확인
        if not SLACK_CHANNEL:
            print("❌ SLACK_CHANNEL 환경변수가 설정되지 않았습니다.")
            print("💡 Railway에서 SLACK_CHANNEL 환경변수를 설정해주세요.")
            return False
            
        print(f"📤 Attempting to send message to channel: {SLACK_CHANNEL}")
        print(f"📝 Message content: {message}")
        print(f"🔑 Bot token (first 10 chars): {SLACK_BOT_TOKEN[:10]}...")
        
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=message
        )
        print(f"✅ Slack message sent successfully: {response['ts']}")
        return True
    except SlackApiError as e:
        print(f"❌ Error sending Slack message: {e.response['error']}")
        print(f"📋 Full error response: {e.response}")
        
        # 채널 관련 오류인 경우 추가 안내
        if e.response['error'] == 'channel_not_found':
            print("💡 해결 방법:")
            print("   1. Railway에서 SLACK_CHANNEL 환경변수 확인")
            print("   2. 채널명 형식: '#채널명' 또는 'C1234567890'")
            print("   3. 봇이 해당 채널에 초대되어 있는지 확인")
        
        return False
    except Exception as e:
        print(f"❌ Unexpected error sending Slack message: {e}")
        return False

def format_slack_message(row_data, m_value):
    """슬랙 메시지를 포맷합니다."""
    # row_data: [A, B, C, D, E, F, G, H, I]
    # A: 번호, B: 이름, C: 연락처, D: 우편번호, E: 주소, F: 박스수, G: 비고, H: 판매신청일, I: 희망일자
    
    if len(row_data) < 9:
        return f"데이터 형식 오류: 행 데이터가 부족합니다. (필요: 9개, 실제: {len(row_data)}개)"
    
    message = "💌 판매신청 수거 송장번호가 입력되었습니다."
    
    return message

def format_l_column_message():
    """L열 업데이트용 슬랙 메시지를 포맷합니다."""
    return "🚚 판매신청 상품이 물류센터에 도착하였습니다."

def clean_date_string(date_str):
    """날짜 문자열을 정리하고 ISO 8601 형식으로 변환합니다."""
    if not date_str:
        return ""
    
    # 작은따옴표, 큰따옴표, 공백 제거
    cleaned = date_str.strip().replace("'", "").replace('"', "")
    
    try:
        # 다양한 날짜 형식 시도
        from datetime import datetime
        
        # YYYY-MM-DD 형식 시도
        if len(cleaned) == 10 and cleaned.count('-') == 2:
            date_obj = datetime.strptime(cleaned, '%Y-%m-%d')
            return date_obj.strftime('%Y-%m-%d')
        
        # YYYY/MM/DD 형식 시도
        elif len(cleaned) == 10 and cleaned.count('/') == 2:
            date_obj = datetime.strptime(cleaned, '%Y/%m/%d')
            return date_obj.strftime('%Y-%m-%d')
        
        # YYYY.MM.DD 형식 시도
        elif len(cleaned) == 10 and cleaned.count('.') == 2:
            date_obj = datetime.strptime(cleaned, '%Y.%m.%d')
            return date_obj.strftime('%Y-%m-%d')
        
        # 기타 형식들도 시도
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y년%m월%d일']:
            try:
                date_obj = datetime.strptime(cleaned, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        print(f"Warning: Could not parse date format: {date_str} -> {cleaned}")
        return cleaned  # 파싱 실패시 정리된 원본 반환
        
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return cleaned  # 오류시 정리된 원본 반환

def send_kakao_notification(name, phone, tradein_date):
    """SOLAPI를 사용해서 카카오톡 알림톡을 보냅니다 (SDK 우선, 실패시 HTTP 요청)."""
    try:
        # SOLAPI 설정 상태 확인
        print(f"📋 SOLAPI configuration check:")
        print(f"  ✅ SOLAPI_API_KEY: {'SET' if SOLAPI_API_KEY else 'NOT SET'}")
        print(f"  ✅ SOLAPI_API_SECRET: {'SET' if SOLAPI_API_SECRET else 'NOT SET'}")
        print(f"  ✅ SOLAPI_TEMPLATE_ID: {'SET' if SOLAPI_TEMPLATE_ID else 'NOT SET'}")
        
        if not all([SOLAPI_API_KEY, SOLAPI_API_SECRET, SOLAPI_TEMPLATE_ID]):
            print("❌ SOLAPI configuration is incomplete. Skipping KakaoTalk notification.")
            return False
        
        # 먼저 SOLAPI Python SDK 사용 시도
        try:
            from solapi import SolapiMessageService
            return _send_with_sdk(name, phone, tradein_date)
        except ImportError:
            print("⚠️ SOLAPI SDK not available, falling back to HTTP requests")
            return _send_with_http(name, phone, tradein_date)
            
    except Exception as e:
        print(f"❌ Error sending KakaoTalk notification: {e}")
        return False

def _send_with_sdk(name, phone, tradein_date):
    """SOLAPI Python SDK를 사용한 알림톡 전송"""
    try:
        from solapi import SolapiMessageService
        from solapi.model import RequestMessage
        from solapi.model.kakao.kakao_option import KakaoOption
        
        # SOLAPI 메시지 서비스 인스턴스 생성
        message_service = SolapiMessageService(SOLAPI_API_KEY, SOLAPI_API_SECRET)
        
        # 카카오 알림톡 발송을 위한 옵션을 생성합니다
        kakao_option = KakaoOption(
            pf_id=SOLAPI_PF_ID,
            template_id=SOLAPI_TEMPLATE_ID,
            variables={
                "#{name}": name,
                "#{tradein_date}": tradein_date,
                "#{delivery_company}": "우체국"
            }
        )
        
        # 단일 메시지를 생성합니다
        message = RequestMessage(
            from_=SOLAPI_FROM_NUMBER,  # 발신번호
            to=phone,  # 수신번호
            kakao_options=kakao_option,
        )
        
        print(f"📱 [SDK] Sending KakaoTalk notification to {name} ({phone}) for pickup date: {tradein_date}")
        
        # 메시지를 발송합니다
        response = message_service.send(message)
        
        print(f"✅ [SDK] KakaoTalk notification sent successfully!")
        print(f"Group ID: {response.group_info.group_id}")
        print(f"요청한 메시지 개수: {response.group_info.count.total}")
        
        # 응답 구조 확인 및 안전한 속성 접근
        try:
            if hasattr(response.group_info.count, 'registered'):
                print(f"성공한 메시지 개수: {response.group_info.count.registered}")
            elif hasattr(response.group_info.count, 'success'):
                print(f"성공한 메시지 개수: {response.group_info.count.success}")
            else:
                print(f"응답 구조: {dir(response.group_info.count)}")
        except Exception as e:
            print(f"응답 정보 출력 중 오류: {e}")
        
        return True
            
    except Exception as e:
        print(f"❌ [SDK] Error: {e}")
        return False

def _send_with_http(name, phone, tradein_date):
    """HTTP 요청을 사용한 알림톡 전송 (후방 호환성)"""
    try:
        import hmac
        import hashlib
        import time
        
        # SOLAPI API endpoint - v4
        url = "https://api.solapi.com/messages/v4/send"
        
        # 타임스탬프 생성
        timestamp = str(int(time.time()))
        
        # 서명 생성 (HMAC-SHA256)
        signature_data = f"{SOLAPI_API_KEY}{timestamp}"
        signature = hmac.new(
            SOLAPI_API_SECRET.encode('utf-8'),
            signature_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'hmac-sha256 apiKey={SOLAPI_API_KEY}, timestamp={timestamp}, signature={signature}'
        }
        
        # 메시지 데이터 준비 (v4 API 형식)
        message_data = {
            "messages": [
                {
                    "to": phone,
                    "from": SOLAPI_FROM_NUMBER,
                    "type": "CTA",  # 카카오톡 알림톡 타입
                    "kakaoOptions": {
                        "pfId": SOLAPI_PF_ID,
                        "templateId": SOLAPI_TEMPLATE_ID,
                        "variables": {
                            "name": name,
                            "tradein_date": tradein_date,
                            "delivery_company": "우체국"
                        }
                    }
                }
            ]
        }
        
        print(f"📱 [HTTP] Sending KakaoTalk notification to {name} ({phone}) for pickup date: {tradein_date}")
        
        # HTTP 요청 전송
        response = requests.post(url, headers=headers, json=message_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ [HTTP] KakaoTalk notification sent successfully: {result}")
            return True
        else:
            print(f"❌ [HTTP] Failed to send KakaoTalk notification. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ [HTTP] Error: {e}")
        return False

def monitor_columns():
    """M열과 L열을 모니터링하여 새로운 데이터가 있으면 슬랙으로 메시지를 보냅니다."""
    service = get_google_sheets_service()
    
    # 이전에 처리된 데이터를 저장할 파일들
    processed_m_file = 'processed_m_data.txt'
    processed_l_file = 'processed_l_data.txt'
    processed_m_rows = set()
    processed_l_rows = set()
    
    # 기존 처리 데이터 초기화 (테스트용)
    if os.path.exists(processed_m_file):
        print("Removing existing processed M data file for fresh start...")
        os.remove(processed_m_file)
    
    if os.path.exists(processed_l_file):
        print("Removing existing processed L data file for fresh start...")
        os.remove(processed_l_file)
    
    # 현재 M열과 L열의 모든 데이터를 이미 처리된 것으로 마킹
    print("Marking existing M column data as already processed...")
    m_column_data = get_m_column_data(service)
    for row_num, row in enumerate(m_column_data, 1):
        if row and row[0].strip():  # M열에 데이터가 있음
            row_key = f"{row_num}_{row[0].strip()}"
            processed_m_rows.add(row_key)
    
    print("Marking existing L column data as already processed...")
    l_column_data = get_l_column_data(service)
    for row_num, row in enumerate(l_column_data, 1):
        if row and row[0].strip():  # L열에 데이터가 있음
            row_key = f"{row_num}_{row[0].strip()}"
            processed_l_rows.add(row_key)
    
    # 처리된 데이터를 파일에 저장
    with open(processed_m_file, 'w') as f:
        for row_key in processed_m_rows:
            f.write(f"{row_key}\n")
    
    with open(processed_l_file, 'w') as f:
        for row_key in processed_l_rows:
            f.write(f"{row_key}\n")
    
    print(f"Starting column monitoring (DIRECT CHECK MODE)... (Processed M rows: {len(processed_m_rows)}, Processed L rows: {len(processed_l_rows)})")
    
    while True:
        try:
            # 직접 M열과 L열 데이터 확인
            print("Checking M and L columns directly...")
            m_column_data = get_m_column_data(service)
            l_column_data = get_l_column_data(service)
            
            # 새로운 데이터가 있는지 확인
            new_data_found = False
            
            # M열 모니터링
            for row_num, row in enumerate(m_column_data, 1):
                if row and row[0].strip():  # M열에 데이터가 있음
                    row_key = f"{row_num}_{row[0].strip()}"
                    
                    if row_key not in processed_m_rows:
                        print(f"New M column data found in row {row_num}: {row[0]}")
                        new_data_found = True
                        
                        # 해당 행의 전체 데이터 가져오기
                        row_data = get_row_data(service, row_num)
                        
                        if row_data:
                            # 슬랙 메시지 생성 및 전송
                            message = format_slack_message(row_data, row[0])
                            slack_sent = send_slack_message(message)
                            
                            # 카카오톡 알림톡 전송 (M열에 송장번호가 입력된 경우)
                            if len(row_data) >= 9:  # 이름, 연락처, 수거신청일이 있는지 확인
                                name = row_data[1] if len(row_data) > 1 else ""  # B열: 이름
                                phone = row_data[2] if len(row_data) > 2 else ""  # C열: 연락처
                                tradein_date_raw = row_data[8] if len(row_data) > 8 else ""  # I열: 수거신청일
                                
                                # 날짜 데이터 정리 및 ISO 8601 형식으로 변환
                                tradein_date = clean_date_string(tradein_date_raw)
                                
                                if name and phone and tradein_date:
                                    kakao_sent = send_kakao_notification(name, phone, tradein_date)
                                    print(f"KakaoTalk notification {'sent' if kakao_sent else 'failed'} for {name}")
                                else:
                                    print(f"Incomplete data for KakaoTalk notification: name={name}, phone={phone}, tradein_date={tradein_date}")
                            
                            if slack_sent:
                                # 처리 완료 표시
                                processed_m_rows.add(row_key)
                                
                                # 처리된 데이터를 파일에 저장
                                with open(processed_m_file, 'a') as f:
                                    f.write(f"{row_key}\n")
                                
                                print(f"Processed M row {row_num}")
                            else:
                                print(f"Failed to send Slack message for M row {row_num}")
                        else:
                            print(f"Failed to get row data for M row {row_num}")
            
            # L열 모니터링
            for row_num, row in enumerate(l_column_data, 1):
                if row and row[0].strip():  # L열에 데이터가 있음
                    row_key = f"{row_num}_{row[0].strip()}"
                    
                    if row_key not in processed_l_rows:
                        print(f"New L column data found in row {row_num}: {row[0]}")
                        new_data_found = True
                        
                        # L열용 슬랙 메시지 생성 및 전송
                        message = format_l_column_message()
                        if send_slack_message(message):
                            # 처리 완료 표시
                            processed_l_rows.add(row_key)
                            
                            # 처리된 데이터를 파일에 저장
                            with open(processed_l_file, 'a') as f:
                                f.write(f"{row_key}\n")
                            
                            print(f"Processed L row {row_num}")
                        else:
                            print(f"Failed to send Slack message for L row {row_num}")
            
            # 새로운 데이터가 있으면 1분 대기, 없으면 1분 대기 (테스트용)
            if new_data_found:
                print("New data processed, waiting 1 minute...")
                time.sleep(60)  # 1분
            else:
                print("No new column data, waiting 1 minute...")
                time.sleep(60)  # 1분
            
        except Exception as e:
            print(f"Error in monitoring: {e}")
            time.sleep(60)  # 오류 발생 시 1분 대기 (테스트용)

def monitor_m_column():
    """M열을 모니터링하여 새로운 데이터가 있으면 슬랙으로 메시지를 보냅니다."""
    service = get_google_sheets_service()
    
    # 이전에 처리된 M열 데이터를 저장할 파일
    processed_file = 'processed_m_data.txt'
    processed_rows = set()
    
    # 기존 처리 데이터 초기화 (테스트용)
    if os.path.exists(processed_file):
        print("Removing existing processed data file for fresh start...")
        os.remove(processed_file)
    
    # 현재 M열의 모든 데이터를 이미 처리된 것으로 마킹
    print("Marking existing M column data as already processed...")
    m_column_data = get_m_column_data(service)
    for row_num, row in enumerate(m_column_data, 1):
        if row and row[0].strip():  # M열에 데이터가 있음
            row_key = f"{row_num}_{row[0].strip()}"
            processed_rows.add(row_key)
    
    # 처리된 데이터를 파일에 저장
    with open(processed_file, 'w') as f:
        for row_key in processed_rows:
            f.write(f"{row_key}\n")
    
    print(f"Starting M column monitoring (DIRECT CHECK MODE)... (Processed rows: {len(processed_rows)})")
    
    while True:
        try:
            # 직접 M열 데이터 확인 (수정 시간 확인 우회)
            print("Checking M column directly...")
            m_column_data = get_m_column_data(service)
            
            # 새로운 데이터가 있는지 확인
            new_data_found = False
            for row_num, row in enumerate(m_column_data, 1):
                if row and row[0].strip():  # M열에 데이터가 있음
                    row_key = f"{row_num}_{row[0].strip()}"
                    
                    if row_key not in processed_rows:
                        print(f"New data found in row {row_num}: {row[0]}")
                        new_data_found = True
                        
                        # 해당 행의 전체 데이터 가져오기
                        row_data = get_row_data(service, row_num)
                        
                        if row_data:
                            # 슬랙 메시지 생성 및 전송
                            message = format_slack_message(row_data, row[0])
                            slack_sent = send_slack_message(message)
                            
                            # 카카오톡 알림톡 전송 (M열에 송장번호가 입력된 경우)
                            if len(row_data) >= 9:  # 이름, 연락처, 수거신청일이 있는지 확인
                                name = row_data[1] if len(row_data) > 1 else ""  # B열: 이름
                                phone = row_data[2] if len(row_data) > 2 else ""  # C열: 연락처
                                tradein_date_raw = row_data[8] if len(row_data) > 8 else ""  # I열: 수거신청일
                                
                                # 날짜 데이터 정리 및 ISO 8601 형식으로 변환
                                tradein_date = clean_date_string(tradein_date_raw)
                                
                                if name and phone and tradein_date:
                                    kakao_sent = send_kakao_notification(name, phone, tradein_date)
                                    print(f"KakaoTalk notification {'sent' if kakao_sent else 'failed'} for {name}")
                                else:
                                    print(f"Incomplete data for KakaoTalk notification: name={name}, phone={phone}, tradein_date={tradein_date}")
                            
                            if slack_sent:
                                # 처리 완료 표시
                                processed_rows.add(row_key)
                                
                                # 처리된 데이터를 파일에 저장
                                with open(processed_file, 'a') as f:
                                    f.write(f"{row_key}\n")
                                
                                print(f"Processed row {row_num}")
                            else:
                                print(f"Failed to send Slack message for row {row_num}")
                        else:
                            print(f"Failed to get row data for row {row_num}")
            
            # 새로운 데이터가 있으면 1분 대기, 없으면 1분 대기 (테스트용)
            if new_data_found:
                print("New data processed, waiting 1 minute...")
                time.sleep(60)  # 1분
            else:
                print("No new M column data, waiting 1 minute...")
                time.sleep(60)  # 1분
            
        except Exception as e:
            print(f"Error in monitoring: {e}")
            time.sleep(60)  # 오류 발생 시 1분 대기 (테스트용)

def test_slack_connection():
    """슬랙 연결을 테스트합니다."""
    try:
        print("Testing Slack connection...")
        print(f"Bot token (first 10 chars): {SLACK_BOT_TOKEN[:10]}...")
        print(f"Target channel: {SLACK_CHANNEL}")
        
        # 봇 정보 가져오기
        auth_test = slack_client.auth_test()
        print(f"Bot user ID: {auth_test['user_id']}")
        print(f"Bot team: {auth_test['team']}")
        
        # 채널 정보 가져오기
        try:
            channel_info = slack_client.conversations_info(channel=SLACK_CHANNEL)
            print(f"Channel found: {channel_info['channel']['name']}")
            print(f"Channel ID: {channel_info['channel']['id']}")
        except SlackApiError as e:
            print(f"Error getting channel info: {e.response['error']}")
        
        # 테스트 메시지 전송 제거 - 토큰 소모 방지
        print("Slack connection test successful - test message skipped to save tokens")
        return True
        
    except SlackApiError as e:
        print(f"Slack API Error: {e.response['error']}")
        print(f"Full error response: {e.response}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("Google Sheets M & L Column Monitor Started")
    print(f"Monitoring spreadsheet: {SPREADSHEET_ID}")
    print(f"Sheet name: {SHEET_NAME}")
    print(f"Slack channel: {SLACK_CHANNEL}")
    
    # 슬랙 연결 테스트
    if test_slack_connection():
        print("Slack connection test successful, starting monitoring...")
        monitor_columns()  # M열과 L열 모두 모니터링
    else:
        print("Slack connection test failed, please check configuration.") 