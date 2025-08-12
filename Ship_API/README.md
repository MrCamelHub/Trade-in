# Ship API

샵바이 API에서 결제완료 주문을 가져와서 코너로지스 API로 전송하는 자동화 시스템입니다.

## 기능

- 샵바이 API에서 결제완료 주문 조회
- Google Sheets에서 SKU 매핑 정보 로드
- 주문 데이터를 코너로지스 API 형식으로 변환
- 코너로지스 API로 출고 주문 생성
- 평일 13:00 자동 실행 (한국 시간, 공휴일 제외)

## 설치

```bash
pip install -r requirements.txt
```

## 환경변수 설정

`.env.example`을 참고하여 `.env` 파일을 생성하고 필요한 값들을 설정하세요.

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 값들로 변경
```

### 필수 환경변수

- `SHOPBY_AUTH_TOKEN`: 샵바이 API 인증 토큰
- `SHOPBY_SYSTEM_KEY`: 샵바이 시스템 키
- `CORNERLOGIS_API_KEY`: 코너로지스 API 키 (또는 username/password)
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Google Sheets API 인증 JSON

## 사용법

### 1. 수동 실행

```bash
# 즉시 실행 (스케줄 조건 무시)
python -m Ship_API.main run

# 스케줄 조건 확인 후 실행 (평일 13:00만)
python -m Ship_API.main schedule

# 테스트 모드 (실제 API 호출 없이 검증만)
python -m Ship_API.main test
```

### 2. 스케줄 실행 (Railway/cron)

```bash
# Railway에서 cron 설정
python -m Ship_API.main schedule
```

### 3. 개별 모듈 테스트

```bash
# 샵바이 API 테스트
python -m Ship_API.shopby_api_client

# 코너로지스 API 테스트
python -m Ship_API.cornerlogis_api_client

# 데이터 변환 테스트
python -m Ship_API.data_transformer

# SKU 매핑 테스트
python -m Ship_API.sku_mapping
```

## 프로젝트 구조

```
Ship_API/
├── __init__.py
├── config.py              # 설정 관리
├── shopby_api_client.py    # 샵바이 API 클라이언트
├── cornerlogis_api_client.py # 코너로지스 API 클라이언트
├── data_transformer.py     # 데이터 변환 로직
├── sku_mapping.py          # SKU 매핑 관리
├── main.py                 # 메인 워크플로우
├── requirements.txt        # 의존성 패키지
├── .env.example           # 환경변수 예시
└── README.md              # 문서
```

## 데이터 흐름

1. **샵바이 API 호출**: 결제완료 주문 목록 조회
2. **SKU 매핑 로드**: Google Sheets에서 상품 코드 매핑 정보 가져오기
3. **데이터 변환**: 샵바이 주문 데이터를 코너로지스 API 형식으로 변환
4. **유효성 검사**: 변환된 데이터의 필수 필드 확인
5. **API 전송**: 코너로지스 API로 출고 주문 생성
6. **결과 저장**: 처리 결과를 JSON 파일로 저장

## 로그 및 결과

처리 결과는 `data/outputs/` 디렉토리에 저장됩니다:

- `processing_result_YYYYMMDD_HHMMSS.json`: 전체 처리 결과
- `transformed_orders_YYYYMMDD_HHMMSS.json`: 변환된 주문 데이터

## Railway 배포

### Option 1: 새로운 Railway 프로젝트 생성 (권장)

1. **새 Railway 프로젝트 생성**:
   - Railway 대시보드에서 "New Project" 클릭
   - GitHub 저장소 연결
   - `feature/ship-api-implementation` 브랜치 선택

2. **환경변수 설정**:
   ```
   CORNERLOGIS_API_KEY=your_api_key_here
   SHOPBY_AUTH_TOKEN=your_shopby_token
   GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
   RAILWAY_ENVIRONMENT=production
   ```

3. **배포 확인**:
   - URL: `https://your-new-app.railway.app`
   - 헬스체크: `https://your-new-app.railway.app/health`
   - 테스트: `https://your-new-app.railway.app/test`

### Option 2: 기존 프로젝트에 새 서비스 추가

1. **기존 Railway 프로젝트에서**:
   - Settings → Services → Add Service
   - GitHub 저장소의 `feature/ship-api-implementation` 브랜치 선택
   - 서비스명: `ship-api`

2. **별도 환경변수 설정** (기존 서비스와 분리)

3. **Cron 스케줄링**:
   ```bash
   # UTC 04:00 = KST 13:00 (평일만)
   0 4 * * 1-5 curl -X POST https://your-ship-api.railway.app/schedule
   ```

### 추천 배포 구조

```
기존 Railway 프로젝트
├── web-production-928a (기존 서비스)
│   └── 판매신청 및 도착 관련
└── ship-api (새 서비스)
    ├── 웹 인터페이스: app.py
    └── 스케줄러: cron job
```

## 트러블슈팅

### 샵바이 API 인증 오류
- `SHOPBY_AUTH_TOKEN`이 만료되었을 수 있습니다
- 새로운 토큰을 발급받아 환경변수를 업데이트하세요

### Google Sheets 접근 오류
- Google Service Account 인증 정보를 확인하세요
- 해당 시트에 대한 읽기 권한이 있는지 확인하세요

### 코너로지스 API 오류
- API 키나 인증 정보를 확인하세요
- 전송하는 데이터 형식이 올바른지 확인하세요

## 개발

새로운 기능 추가나 버그 수정 시:

1. 테스트 모드로 먼저 검증
2. 로컬에서 수동 실행으로 테스트
3. Railway에 배포 후 스케줄 모드 확인

## 주의사항

- API 호출 제한을 고려하여 적절한 지연 시간을 두고 있습니다
- 민감한 정보(API 키, 인증 토큰 등)는 환경변수로 관리합니다
- 한국 시간 기준으로 평일 13:00에만 자동 실행됩니다
