from flask import Flask, request, jsonify
from slack_sdk import WebClient
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from datetime import datetime
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)

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
    
    import json
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

def append_to_sheet(data):
    service = get_google_sheets_service()
    first_empty_row = find_first_empty_row(service)
    
    # Prepare the values with the current date (m/d format for Excel date recognition)
    current_date = datetime.now().strftime('%-m/%-d')  # e.g., "8/5" for August 5th
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
        
        if event.get('type') == 'message':
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
                        result = append_to_sheet(parsed_data)
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
    app.run(host='0.0.0.0', port=5001, debug=True) 