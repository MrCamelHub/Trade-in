from flask import Flask, request, jsonify
from slack_sdk import WebClient
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from datetime import datetime
import re
import pytz
import json
import hashlib

# Load environment variables
load_dotenv()

app = Flask(__name__)

# 전역 변수로 처리된 이벤트 ID를 저장 (메모리 기반)
processed_event_ids = set()

# 처리된 이벤트 ID를 파일에 저장하는 함수
def save_processed_event_id(event_id):
    """처리된 이벤트 ID를 파일에 저장"""
    try:
        with open('processed_slack_events.txt', 'a') as f:
            f.write(f"{event_id}\n")
    except Exception as e:
        print(f"⚠️ Failed to save processed event ID: {e}")

# 처리된 이벤트 ID를 파일에서 로드하는 함수
def load_processed_event_ids():
    """파일에서 처리된 이벤트 ID들을 로드"""
    processed_ids = set()
    try:
        if os.path.exists('processed_slack_events.txt'):
            with open('processed_slack_events.txt', 'r') as f:
                for line in f:
                    processed_ids.add(line.strip())
            print(f"📋 Loaded {len(processed_ids)} processed event IDs from file")
    except Exception as e:
        print(f"⚠️ Failed to load processed event IDs: {e}")
    return processed_ids

# 앱 시작 시 처리된 이벤트 ID들을 로드
processed_event_ids = load_processed_event_ids()

# 오래된 이벤트 ID들을 정리하는 함수
def cleanup_old_event_ids(max_age_hours=24):
    """24시간 이상 된 이벤트 ID들을 정리"""
    try:
        current_time = datetime.now()
        cleaned_ids = set()
        
        if os.path.exists('processed_slack_events.txt'):
            with open('processed_slack_events.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # 파일명에서 타임스탬프 추출 시도 (선택사항)
                        cleaned_ids.add(line)
            
            # 메모리에서도 정리
            global processed_event_ids
            processed_event_ids = cleaned_ids
            
            print(f"🧹 Cleaned up old event IDs, keeping {len(cleaned_ids)} recent ones")
    except Exception as e:
        print(f"⚠️ Failed to cleanup old event IDs: {e}")

# Slack configuration
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# Google Sheets configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

def get_google_sheets_service():
    # Get service account JSON from environment variable
    service_account_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not service_account_json:
        raise Exception("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set")
    
    service_account_info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)
    
    return build('sheets', 'v4', credentials=credentials)

def find_first_empty_row(service):
    # Get all values from column B
    range_name = '보니벨로 Trade-in_신청!B:B'
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name
    ).execute()
    values = result.get('values', [])
    
    # Find the first empty row by checking each row
    for i, row in enumerate(values, 1):
        if not row or not row[0].strip():  # Empty or whitespace-only
            return i
    
    # If no empty row found, return next row after last data
    return len(values) + 1

def clean_slack_formatting(text):
    """Remove Slack link markup so field delimiters '|' are not corrupted.

    Examples transformed:
    - "<tel:1801151302|180 115-1302>" -> "180 115-1302"
    - "<http://example.com|example>" -> "example"
    - "<http://example.com>" -> "http://example.com"
    """
    # Replace link-with-label first: <something|label> -> label
    text = re.sub(r"<[^>|]+\|([^>]+)>", r"\1", text)
    # Then replace bare autolinks: <something> -> something
    text = re.sub(r"<([^>]+)>", r"\1", text)
    return text

def parse_slack_message(message):
    # Split the message by newlines and process each line
    # Clean Slack's autolink/markup (e.g., <tel:...|...>) before splitting by '|'
    cleaned_message = clean_slack_formatting(message or "")
    lines = cleaned_message.strip().split('\n')
    data = []
    
    for line in lines:
        if '|' in line:
            parts = line.split('|')
            # Skip header line (contains "이름|연락처|주소|희망일자|박스수")
            if '이름' in parts[0] or '연락처' in parts[0]:
                continue
            # Check if we have the expected number of fields (5 fields including empty last field)
            if len(parts) >= 5:
                address = parts[2].strip()
                # Extract postal code from address (format: (12345) 주소)
                postal_code = ''
                if address.startswith('(') and ')' in address:
                    postal_code = address[1:address.find(')')]
                    # Remove postal code from address
                    address = address[address.find(')')+1:].strip()
                
                # Parse box count and remove "개" suffix
                box_count_raw = parts[4].strip() if parts[4].strip() else '1개'
                box_count = box_count_raw.replace('개', '').replace('+', '')  # Remove "개" and "+" characters
                
                # Convert to integer, default to 1 if parsing fails
                try:
                    box_count_int = int(box_count)
                except ValueError:
                    box_count_int = 1
                
                # Parse desired date (희망일자)
                desired_date = parts[3].strip()
                
                data.append({
                    'name': parts[0].strip(),
                    'phone': parts[1].strip(),
                    'postal_code': postal_code,
                    'address': address,
                    'box_count': box_count_int,
                    'desired_date': desired_date
                })
    return data

def append_to_sheet(data, received_date_str=None):
    service = get_google_sheets_service()
    first_empty_row = find_first_empty_row(service)
    
    # Prepare the values with the received date in KST (m/d format for Excel date recognition)
    if not received_date_str:
        kst = pytz.timezone('Asia/Seoul')
        current_date = datetime.now(kst).strftime('%-m/%-d')  # e.g., "8/5" for August 5th
    else:
        current_date = received_date_str
    values = []
    
    for item in data:
        # Create multiple rows based on box count
        for _ in range(item['box_count']):
            # Order: B(이름), C(번호), D(우편번호), E(주소), F(박스수), H(메시지수신일), I(희망일자)
            # A열은 건드리지 않음 (사용자가 직접 관리)
            row = [''] * 9  # Create empty list for columns A-I
            row[1] = item['name']          # B열 (이름)
            row[2] = item['phone']         # C열 (번호)
            row[3] = item['postal_code']   # D열 (우편번호)
            row[4] = item['address']       # E열 (주소)
            row[5] = item['box_count']     # F열 (박스수)
            row[7] = current_date          # H열 (메시지수신일)
            row[8] = item['desired_date']  # I열 (희망일자)
            values.append(row)
    
    range_name = f'보니벨로 Trade-in_신청!A{first_empty_row}'
    body = {
        'values': values
    }
    
    result = service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()
    
    return result

@app.route('/')
def health_check():
    """헬스체크 엔드포인트"""
    return {'status': 'healthy', 'service': 'Bonibello Trade-in Automation'}

@app.route('/health')
def health():
    """상세 헬스체크 엔드포인트"""
    return {
        'status': 'healthy',
        'service': 'Bonibello Trade-in Automation',
        'features': [
            'Slack webhook receiver',
            'Google Sheets integration',
            'KakaoTalk notification'
        ]
    }

@app.route('/slack/webhook', methods=['POST'])
def slack_webhook():
    """슬랙 웹훅 엔드포인트 - Trade-in 신청 메시지를 받아서 구글시트에 저장"""
    print("🔔 Slack webhook received!")
    
    # Get the JSON data from the request
    data = request.json
    print(f"📥 Received webhook data: {data}")  # Debug log

    # Handle Slack's URL verification challenge
    if data and data.get('type') == 'url_verification':
        challenge = data.get('challenge')
        print(f"🔗 URL verification challenge: {challenge}")  # Debug log
        return jsonify({'challenge': challenge})

    # Handle regular event
    if data and data.get('event'):
        event = data.get('event')
        print(f"📨 Received event: {event}")  # Debug log
        
        # 중복 방지: event_id 체크
        event_id = data.get('event_id')
        if event_id:
            if event_id in processed_event_ids:
                print(f"🔄 Duplicate event detected (ID: {event_id}), skipping...")
                return jsonify({'status': 'skipped', 'message': 'Duplicate event'})
            else:
                print(f"✅ New event (ID: {event_id}), processing...")
                # 처리된 이벤트 ID를 메모리와 파일에 저장
                processed_event_ids.add(event_id)
                save_processed_event_id(event_id)
        else:
            print("⚠️ No event_id found, checking message content hash...")
            # event_id가 없는 경우 메시지 내용 기반 해시로 중복 체크
            message_content = str(event.get('text', '')) + str(event.get('attachments', []))
            if message_content:
                message_hash = hashlib.md5(message_content.encode()).hexdigest()
                if message_hash in processed_event_ids:
                    print(f"🔄 Duplicate message content detected (hash: {message_hash}), skipping...")
                    return jsonify({'status': 'skipped', 'message': 'Duplicate message content'})
                else:
                    print(f"✅ New message content (hash: {message_hash}), processing...")
                    processed_event_ids.add(message_hash)
                    save_processed_event_id(message_hash)
        
        if event.get('type') == 'message':
            # Determine received date from Slack timestamp (KST)
            received_date_str = None
            try:
                ts_value = event.get('ts')
                if ts_value is not None:
                    # 'ts' is a string like "1723567890.1234"
                    ts_seconds = float(ts_value)
                else:
                    event_time = data.get('event_time')  # fallback, int seconds
                    ts_seconds = float(event_time) if event_time is not None else None
                if ts_seconds is not None:
                    kst = pytz.timezone('Asia/Seoul')
                    received_dt_kst = datetime.fromtimestamp(ts_seconds, tz=pytz.utc).astimezone(kst)
                    received_date_str = received_dt_kst.strftime('%-m/%-d')
            except Exception as ts_err:
                print(f"⚠️ Failed to parse Slack timestamp: {ts_err}")
                received_date_str = None

            # Check for text in event
            message = event.get('text', '')
            
            # Check for text in attachments if main text is empty
            if not message and 'attachments' in event:
                for attachment in event['attachments']:
                    if 'text' in attachment:
                        message = attachment['text']
                        break
            
            print(f"Processing message: {message}")  # Debug log
            
            if message:
                print(f"📝 Processing message: {message}")
                parsed_data = parse_slack_message(message)
                print(f"🔍 Parsed data: {parsed_data}")  # Debug log
                
                if parsed_data:
                    try:
                        print(f"📊 Adding data to Google Sheets...")
                        result = append_to_sheet(parsed_data, received_date_str=received_date_str)
                        print(f"✅ Sheet update result: {result}")  # Debug log
                        return jsonify({'status': 'success', 'message': 'Data added to Google Sheets'})
                    except Exception as e:
                        print(f"❌ Error updating sheet: {str(e)}")  # Debug log
                        return jsonify({'status': 'error', 'message': str(e)})
                else:
                    print("⚠️ No data parsed from message")  # Debug log
            else:
                print("⚠️ No message text found in event or attachments")  # Debug log
    
    print("❌ Invalid message format or no event data")  # Debug log
    return jsonify({'status': 'error', 'message': 'Invalid message format'})

if __name__ == '__main__':
    # 앱 시작 시 오래된 이벤트 ID 정리
    cleanup_old_event_ids()
    print(f"🚀 Starting Bonibello Trade-in Automation with duplicate prevention")
    print(f"📊 Loaded {len(processed_event_ids)} processed event IDs")
    app.run(host='0.0.0.0', port=5001, debug=True) 