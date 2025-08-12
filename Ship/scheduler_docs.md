Railway Cron 설정 가이드 (A 방식, 한국 공휴일 제외)

요구사항: 평일 13:00 KST, 한국 공휴일 제외.

권장: Railway Cron으로 UTC 04:00에 실행. 공휴일 제외는 코드에서 판단 후 즉시 종료.

1) Railway → Deploy → Cron → New Trigger
   - Schedule: 0 4 * * 1-5 (UTC, 월~금 04:00 = KST 13:00)
   - Command: python -m Ship.run_ship

2) 공휴일 제외 로직은 run_ship.py의 should_run_now_kst()에서 수행할 수 있도록 후속 확장 포인트를 남김.


