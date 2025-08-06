# 🚢 Railway 배포 가이드

## 1. Railway 계정 및 프로젝트 생성

### 1-1. Railway 가입 및 로그인
1. [Railway.app](https://railway.app) 접속
2. GitHub 계정으로 로그인
3. "New Project" 클릭

### 1-2. GitHub 저장소 연결
1. "Deploy from GitHub repo" 선택
2. `MrCamelHub/Trade-in` 저장소 선택
3. "Deploy" 클릭

## 2. 환경변수 설정

Railway 대시보드 → Variables 탭에서 다음 환경변수들을 설정해주세요:

### 2-1. 필수 환경변수

```bash
# Slack 설정
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token-here
SLACK_CHANNEL=#08_biz_bonibello_request

# Google Sheets 설정  
SPREADSHEET_ID=your-actual-spreadsheet-id-here
SHEET_NAME=보니벨로 Trade-in_신청

# Google Service Account JSON (한 줄로 입력)
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project",...}
```

### 2-2. 선택적 환경변수

```bash
# SOLAPI 카카오톡 알림톡 (Python SDK 사용)
SOLAPI_API_KEY=your-solapi-api-key
SOLAPI_API_SECRET=your-solapi-api-secret  
SOLAPI_TEMPLATE_ID=your-template-id
SOLAPI_PF_ID=your-plusfriend-id
SOLAPI_FROM_NUMBER=070-xxxx-xxxx

# Railway 포트 (자동 설정되므로 보통 필요없음)
PORT=5000
```

## 3. 환경변수 값 얻는 방법

### 3-1. Slack 설정

**SLACK_BOT_TOKEN:**
1. [Slack API](https://api.slack.com/apps) → 앱 선택
2. "OAuth & Permissions" → "Bot User OAuth Token" 복사
3. `xoxb-`로 시작하는 토큰

**SLACK_CHANNEL:**
- 채널명: `#08_biz_bonibello_request`
- 또는 채널 ID: `C1234567890`

### 3-2. Google Sheets 설정

**SPREADSHEET_ID:**
- 구글시트 URL: `https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit`
- URL에서 긴 ID 부분 복사

**GOOGLE_APPLICATION_CREDENTIALS_JSON:**
1. [Google Cloud Console](https://console.cloud.google.com/)
2. "Service Accounts" → 서비스 계정 생성
3. JSON 키 파일 다운로드
4. JSON 파일 내용을 한 줄로 만들어서 입력

### 3-3. SOLAPI 설정 (카카오톡 알림톡용)

1. [SOLAPI](https://solapi.com) 가입
2. API 키 및 시크릿 발급
3. 카카오톡 채널 연동 및 템플릿 생성

## 4. 배포 확인

### 4-1. 배포 상태 확인
1. Railway 대시보드 → Deployments 탭
2. "Active" 상태 확인
3. 로그에서 오류 없는지 확인

### 4-2. 애플리케이션 URL 확인
1. Railway 대시보드 → Settings 탭
2. "Domains" 섹션에서 자동 생성된 URL 확인
3. 예: `https://trade-in-production-xxxx.up.railway.app`

## 5. 슬랙 웹훅 설정

### 5-1. Event Subscriptions 설정
1. [Slack API](https://api.slack.com/apps) → 앱 선택
2. "Event Subscriptions" → Enable Events
3. Request URL 입력: `https://your-railway-domain.railway.app/slack/webhook`
4. "Subscribe to bot events" → `message.channels` 추가
5. "Save Changes"

### 5-2. 웹훅 연결 확인
1. Railway 대시보드에서 도메인 확인: `https://your-app-name.railway.app`
2. 브라우저에서 `https://your-app-name.railway.app/health` 접속하여 서비스 상태 확인
3. Slack Event Subscriptions에서 "Verify" 버튼 클릭하여 연결 확인

### 5-2. 권한 설정 확인
"OAuth & Permissions" → "Scopes"에서 다음 권한 확인:
- `chat:write`
- `channels:history` 
- `channels:read`

## 6. 테스트

### 6-1. 슬랙 메시지 테스트
슬랙 채널에서 다음 형식으로 메시지 전송:
```
김철수|010-1234-5678|(12345) 서울시 강남구|2024-01-15|2개
```

### 6-2. 구글시트 확인
- 슬랙 메시지가 구글시트에 자동 입력되는지 확인

### 6-3. M열/L열 테스트
- 구글시트 M열에 송장번호 입력 → 슬랙 + 카카오톡 알림 확인
- 구글시트 L열에 값 입력 → 슬랙 알림 확인

## 7. 모니터링

### 7-1. Railway 로그 확인
Railway 대시보드 → Logs 탭에서 실시간 로그 확인:
```
🚀 Starting Flask webhook server...
📊 Starting Google Sheets monitor...
✅ Slack connection test successful, starting monitoring...
```

### 7-2. 문제 해결
- 로그에서 오류 메시지 확인
- 환경변수 설정 재확인
- Railway 재배포: Settings → Deploy

## 8. 24/7 운영

Railway는 자동으로 24/7 운영됩니다:
- 자동 재시작 정책 적용
- 헬스체크 자동 수행
- 트래픽에 따른 자동 스케일링

## ⚠️ 주의사항

1. **환경변수 보안**: 중요한 토큰들이므로 외부 노출 금지
2. **API 사용량**: Slack, Google Sheets, SOLAPI API 사용량 모니터링
3. **로그 모니터링**: 정기적으로 오류 로그 확인
4. **백업**: 중요한 데이터는 별도 백업 권장

## 📞 지원

문제 발생시:
1. Railway 로그 확인
2. 환경변수 재설정  
3. 재배포 시도
4. 개발팀 문의