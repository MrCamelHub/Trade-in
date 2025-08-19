# Bonibello Delivery API

송장입력, 발송처리, 발송완료처리 전용 API 서버

## 기능

### 📦 주요 엔드포인트
- `POST /invoice/input` - 송장 입력 처리
- `POST /shipping/process` - 발송 처리  
- `POST /shipping/complete` - 발송 완료 처리

### 🔧 시스템 엔드포인트
- `GET /` - API 정보 및 엔드포인트 목록
- `GET /health` - 헬스 체크
- `GET /status` - 서비스 상태
- `GET /test` - 테스트

## 배포

### Railway 배포
```bash
# Railway CLI로 배포
railway deploy
```

### 로컬 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
python app.py
```

## 구조

```
Delivery_API/
├── app.py              # 메인 Flask 앱
├── requirements.txt    # Python 의존성
├── Procfile           # Railway 실행 설정
├── railway.toml       # Railway 배포 설정
├── README.md          # 문서
└── data/              # 데이터 폴더
    ├── downloads/     # 다운로드 파일
    ├── logs/          # 로그 파일  
    └── outputs/       # 출력 파일
```
