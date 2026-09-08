# ADR-013: 한국 표준시(KST, Asia/Seoul) 기준 타임존 로컬라이제이션

## 1. 배경 (Context)
기존 왓슨 봇은 서버 기본 시간(UTC)을 기준으로 라이프로그 파일 경로(`YYYY-MM-DD.md`), 일기 기록 타임스탬프(`[HH:MM]`), 커밋 메시지 날짜 및 비서 브리핑을 생성하였다.
이로 인해 다음과 같은 심각한 시간 불일치 문제가 발생하였다:
1. **타임스탬프 오차**: 한국(KST, UTC+9)에서 오후 2시 13분에 기록한 일과가 UTC 기준인 `[05:13]`으로 기록됨.
2. **날짜 경계(Midnight Boundary) 역전**: 한국 시간 오전 0시~9시 사이에 기록 시 UTC는 전날에 머물러 있어 오늘 기록이 어제 날짜 파일(예: `2026-09-07.md`)로 분기되는 결함 발생.
3. 사용자가 한국 현지에서 실시간 비서로 활용하는 특성상 모든 사용자 대면 시간과 라이프로그는 한국 표준시(KST, Asia/Seoul)로 일관되게 기록되어야 함.

## 2. 결정 사항 (Decision)
1. **중앙 집중식 타임존 설정 (`app/config.py`)**:
   - `Settings`에 `TIMEZONE: str = "Asia/Seoul"` 환경 변수 및 설정 필드 추가.
   - 표준 라이브러리 `zoneinfo.ZoneInfo`를 기반으로 타임존을 파싱하는 `get_app_timezone()` 및 현재 로컬 시간을 반환하는 `get_now()` 헬퍼 함수 제공.
2. **라이프로그 날짜/시간 정규화 (`AgentService._normalize_datetime`)**:
   - `get_lifelog_filepath`, `append_or_update_lifelog`, `get_gtd_summary` 호출 시 전달된 `datetime` 객체가 UTC이든 naive이든 설정된 타임존(`Asia/Seoul`)으로 엄격히 정규화.
   - UTC 시각 `05:13`은 `14:13 KST`로 변환되어 마크다운에 `[14:13]`으로 기록되고, 날짜 경계도 KST 기준으로 계산.
3. **슈퍼바이저, AGY 러너 및 텔레그램 상태 연동**:
   - `SupervisorService`의 커밋 메시지 일자, 마크다운 기록 및 브리핑 호출 시 `get_now()` 사용.
   - `TelegramService`의 `/status` 동기화 시간 및 사진 저장 타임스탬프를 KST로 통일.
   - `SettingsService.get_status()` 응답에 현재 적용된 `timezone` 정보 노출.
4. **기존 일기 타임스탬프 소급 정정**:
   - 기존 UTC로 잘못 기록되었던 `life_log/logs/daily/2026-09-08.md`의 `[05:13]`을 `[14:13]`으로, `[04:13]`을 `[13:13]`으로 정정.

## 3. 결과 및 영향 (Consequences)
- **장점**:
  - 한국 현지 사용자의 실제 생활 시간대와 라이프로그 기록 시간이 100% 일치.
  - 자정 넘은 새벽 시간대 기록 시에도 올바른 한국 날짜 파일에 기록 보장.
  - `.env`의 `TIMEZONE` 설정을 통해 향후 타 국가 시간대로도 유연하게 변경 가능.
- **테스트 및 검증**:
  - `test_timezone_conversion_utc_to_kst`: UTC 05:13 입력 시 14:13 KST 변환 검증 완료.
  - `test_timezone_date_rollover_utc_to_kst`: UTC 밤 20:00(익일 05:00 KST) 입력 시 익일 파일명 생성 검증 완료.
  - `./scripts/smoke_test.sh`: 격리 샌드박스에서 100% 통과.
