# 🎯 Bonibello Trade-in 자동화 시스템

슬랙과 구글시트를 연동한 Trade-in 신청 자동화 시스템입니다.

## 🚀 주요 기능

### 1. 슬랙 → 구글시트 자동 입력
- 슬랙에서 Trade-in 신청 메시지가 오면 자동으로 구글시트에 데이터 저장
- 메시지 형식: `이름|연락처|주소|희망일자|박스수`

### 2. 구글시트 → 슬랙 + 카카오톡 알림
- **M열 (송장번호)** 업데이트 시:
  - 슬랙에 "송장번호 입력 완료" 메시지 전송
  - 고객에게 카카오톡 알림톡 발송 (솔라피 API 사용)
- **L열 (물류센터 도착)** 업데이트 시:
  - 슬랙에 "물류센터 도착" 메시지 전송

## 🔧 최신 개선사항

### ✨ 솔라피 Python SDK 적용 (v2.0)
- 기존 직접 HTTP 요청 방식에서 **공식 Python SDK** 사용으로 변경
- 더 안정적이고 깔끔한 카카오톡 알림톡 전송
- 오류 처리 및 로깅 개선

## 📋 필요한 환경변수

다음 환경변수들을 설정해야 합니다:

```bash
# Slack 설정
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL=#08_biz_bonibello_request

# Google Sheets 설정
SPREADSHEET_ID=your-spreadsheet-id-here
SHEET_NAME=보니벨로 Trade-in_신청
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}

# SOLAPI 카카오톡 알림톡 설정 (Python SDK 사용)
SOLAPI_API_KEY=your-solapi-api-key
SOLAPI_API_SECRET=your-solapi-api-secret
SOLAPI_TEMPLATE_ID=your-template-id
SOLAPI_PF_ID=your-plusfriend-id
SOLAPI_FROM_NUMBER=070-xxxx-xxxx
```

## 🛠 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정 (.env 파일 생성)
cp env_example.txt .env
# .env 파일을 열어서 실제 값들로 수정

# 실행
python main.py
```

## 🚢 Railway 배포

### 1. Git 저장소 연결
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/MrCamelHub/Trade-in.git
git branch -M main
git push -u origin main
```

### 2. Railway 프로젝트 생성
1. [Railway](https://railway.app) 접속
2. "New Project" → "Deploy from GitHub repo"
3. `MrCamelHub/Trade-in` 저장소 선택

### 3. 환경변수 설정
Railway 대시보드에서 다음 환경변수들을 설정:
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL`
- `SPREADSHEET_ID`
- `SHEET_NAME`
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`
- `SOLAPI_API_KEY`
- `SOLAPI_API_SECRET`
- `SOLAPI_TEMPLATE_ID`
- `SOLAPI_PF_ID`
- `SOLAPI_FROM_NUMBER`

### 4. 배포 확인
- Railway가 자동으로 애플리케이션을 빌드하고 배포합니다
- 로그에서 정상 실행 여부를 확인할 수 있습니다

## 📚 시스템 구조

```
main.py              # 메인 애플리케이션 (Flask + 모니터링)
├── slack_to_sheets.py   # 슬랙 웹훅 → 구글시트
└── sheets_to_slack.py   # 구글시트 모니터링 → 슬랙 + 카카오톡
```

## 🔧 웹훅 설정

슬랙 앱에서 다음 URL로 Event Subscriptions 설정:
```
https://your-railway-domain.railway.app/slack/webhook
```

## 📊 구글시트 컬럼 구조

| A | B | C | D | E | F | G | H | I | ... | L | M |
|---|---|---|---|---|---|---|---|---|-----|---|---|
| 번호 | 이름 | 연락처 | 우편번호 | 주소 | 박스수 | 비고 | 신청일 | 희망일자 | ... | 물류센터도착 | 송장번호 |

## 🎯 동작 흐름

1. **고객이 슬랙에 Trade-in 신청 메시지 전송**
2. **시스템이 자동으로 구글시트에 데이터 입력**
3. **담당자가 M열에 송장번호 입력**
4. **시스템이 자동으로:**
   - 슬랙에 알림 전송
   - 고객에게 카카오톡 알림톡 발송
5. **물류센터에서 L열에 도착 표시**
6. **시스템이 슬랙에 도착 알림 전송**

## 📞 지원

문제가 있으시면 개발팀에 문의해주세요.