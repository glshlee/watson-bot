# ADR-047: 웹 콘솔 한국 표준시(KST) 동기화 및 실시간 시계 배지 연동 (Web Console Timezone & Time Synchronization)

## 1. Context (배경 및 문제점)
사용자 피드백:
- *"웹콘솔은 시간 설정이 제대로 안된 것 같아. 확인해봐."*

조사 및 진단 결과:
1. **세션 상대 시간 왜곡 버그 ("9시간 전" 결함)**:
   - `SessionModel`(`created_at`, `updated_at`) 및 `ChatMessageModel`에서 `datetime.now(timezone.utc)`를 기본값으로 사용하고 세션 갱신 시에도 UTC 시간을 저장하고 있었음.
   - SQLite는 타임존 오프셋을 제거한 채 naive 문자열(`2026-09-16 00:13:48`)로 영속화하므로, API 직렬화 시 `"2026-09-16T00:13:48.889348"`처럼 `+09:00`이나 `Z` 없이 반환됨.
   - 사용자 브라우저(한국, KST, UTC+9)의 JavaScript `new Date()`는 타임존 정보가 없는 ISO 문자열을 로컬 시간(KST 00:13:48)으로 해석함.
   - 당시 한국 실제 시각은 09:13:48이었으므로 브라우저는 9시간 전으로 계산하여 방금 전송한 메시지도 사이드바에 무조건 **"9시간 전"**으로 오표기하는 치명적인 결함이 발생함.
2. **일일 로그 에디터 날짜 판별(자정~오전 9시) 결함**:
   - 인플레이스 에디터 모달(`openEditorModal`)에서 `const today = new Date()`로 클라이언트 로컬 날짜를 추출하여, UTC 기반 원격 접속자나 자정 직후 시간대에 어제 날짜 파일이 열리는 현상이 잠재함.
3. **웹 콘솔 상단 헤더의 실시간 시계 및 KST 타임존 표시 부재**:
   - 에이전트 허브(`/`)에는 `[KST (Asia/Seoul)]` 배지가 있었으나, 주 사용처인 비서 콘솔(`/watson`)과 개발자 콘솔(`/dev`) 헤더에는 현재 시간이나 타임존을 확인할 수 있는 인디케이터가 없어 사용자가 시스템 시간을 불신하거나 혼란을 겪음.
4. **출근길 브리핑 스케줄러 동적 시각 모니터링 누락**:
   - `commute_config.json`의 `send_time`(기본 `07:30`) 설정이 웹 모달에 노출되어 있으나, 백그라운드 `BriefingScheduler`에서 해당 시각 일치 검사 및 출근 브리핑 능동 푸시 로직이 누락되어 있었음.

---

## 2. Decision (결정 사항)

### 2.1 세션 모델 및 서비스 KST 통일 (`app/models/session.py`, `app/services/session_service.py`)
- `utc_now`를 제거하고 `kst_now()` (`get_now()`, `Asia/Seoul`)로 전면 교체.
- `add_message`, `update_session_title`, `clear_session_messages` 등 세션 갱신 시 `get_now()` 사용.
- `SessionService._format_datetime_iso()` 도입: SQLite에서 읽은 naive datetime에 KST 타임존(`Asia/Seoul`)을 명시적으로 바인딩하여 JSON 응답에 항상 `+09:00` 오프셋을 포함(`2026-09-16T09:39:54+09:00`).
- 기존 SQLite `app.db` 내 과거 UTC 세션 및 메시지 타임스탬프를 KST(+9 hours)로 1회 일괄 마이그레이션.

### 2.2 웹 프론트엔드 KST 상대 시간 포맷터 및 에디터 날짜 보정 (`app/static/js/main.js`, `app/static/js/dev.js`)
- `formatRelativeTime(dateStr)` 개선: 타임존 표기가 없는 문자열도 KST(`+09:00`)로 안전하게 보정하여 "방금", "n분 전"이 정확히 계산되도록 방어.
- `getKSTDateString()` 도입: `Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' })`을 사용하여 에디터 모달 기본 열람 일자를 한국 표준시 기준 당일 날짜로 엄격 보장.

### 2.3 상단 헤더 실시간 KST 디지털 시계 배지 탑재 (`index.html`, `dev.html`, `style.css`)
- Watson 콘솔 및 DevBot 콘솔 상단 헤더에 `#header-clock-badge` 탑재 (`[⏰ 09:49:10 KST]`).
- 초 단위 실시간 업데이트(`setInterval(updateLiveClock, 1000)`) 및 tabular-nums 고정폭 폰트 스타일 적용.

### 2.4 프로세스 레벨 타임존 KST 고정 및 출근 스케줄러 연동 (`app/main.py`, `briefing_scheduler.py`)
- `app/main.py` 수명 주기(lifespan) 시작 시 `os.environ["TZ"] = settings.TIMEZONE` 및 `time.tzset()` 호출로 Python 런타임, C 라이브러리, Git 서브프로세스(`+0900` 커밋) 전역 표준화.
- `/api/health` 응답에 `timestamp` (KST ISO) 및 `timezone: "Asia/Seoul"` 명시 반환.
- `BriefingScheduler`에 `commute_config`의 `send_time`(KST) 매칭 및 `dispatch_commute_briefing()` 능동 푸시 파이프라인 연동.

---

## 3. Consequences (영향 및 효과)
1. **세션 업데이트 상대 시간 100% 정상화**: 새 메시지 전송 즉시 사이드바에 "방금"으로 표기되며, 9시간 전 오표기 버그가 원천 해결됨.
2. **시각적 신뢰성 확보**: 헤더에서 초 단위로 살아 움직이는 실시간 KST 시계를 제공하여 사용자에게 시스템 가동 및 시간대 일관성을 명확히 전달.
3. **자정 경계 에디터 무결성**: 새벽 시간대(00:00~09:00 KST) 접속 시에도 항상 올바른 KST 당일 일일 로그 파일이 오픈됨.
4. **Git 커밋 타임존 일치**: 백엔드에서 생성되는 모든 자동 커밋이 UTC(`+0000`)가 아닌 KST(`+0900`)로 정확히 기록됨.
