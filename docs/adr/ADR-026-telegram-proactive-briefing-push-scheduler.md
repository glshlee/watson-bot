# ADR-026: 텔레그램 정기 브리핑 자동 푸시 스케줄러 (Telegram Proactive Briefing Push Scheduler)

## 1. Context (배경 및 문제점)
사용자 질의: *"스케줄 대화는 어디로 알림이 와?"*
1. **온디맨드 질의와 능동 알림의 불일치**:
   - 기존의 아침(08:30 KST) / 저녁(20:00 KST) 브리핑은 사용자가 직접 웹 콘솔이나 텔레그램에서 명령(`"/schedule"`, `"/briefing"`, *"할 일 알려줘"*)을 내렸을 때만 반응하는 수동 온디맨드 방식이었다.
   - 사용자가 원한 것은 질문하지 않아도 **매일 08:30 및 20:00 정각에 왓슨이 먼저 스마트폰 텔레그램으로 능동 푸시 메시지(Proactive Push Notification)를 울려주는 자동 비서 경험**이었다.
2. **복수 수신자 및 중복 발송 방지**:
   - 시스템 시간대(KST)를 기준으로 동일 일자(`YYYY-MM-DD`)에 동일 모드(morning/evening) 브리핑이 중복 발송되지 않도록 방어 로직이 필요하며, 화이트리스트 사용자(`TELEGRAM_ALLOWED_CHAT_IDS`) 전원에게 일괄 전달되고 세션 히스토리(`telegram:{chat_id}`)에 영속화되어야 함.
3. **웹 모달 연동 및 즉시 테스트 지원**:
   - 웹 콘솔 스케줄 모달(`#schedule-modal`)에서 텔레그램 자동 푸시 활성 상태를 확인하고, 원클릭으로 텔레그램에 즉시 시험 발송(`POST /api/briefing/trigger-push`)할 수 있는 직관적인 UI 제공 필요.

## 2. Decision (결정 사항)

### 2.1 BriefingScheduler 백그라운드 서비스 구현 (`app/services/briefing_scheduler.py`)
- **24/7 상시 주기 감시**:
  - 20초 간격으로 한국 표준시(KST)를 폴링하여 08:30(아침) 및 20:00(저녁) 정각을 감지.
  - `last_dispatched = {"morning": "YYYY-MM-DD", "evening": "YYYY-MM-DD"}`로 하루 1회 발송 보장.
- **자동 원격 동기화 & 브리핑 합성**:
  - 발송 직전 `git_service.pull()`을 수행하여 원격 최신 커밋을 사전 반영한 뒤 맞춤형 브리핑 합성.
- **텔레그램 일괄 발송 및 세션 히스토리 영속화**:
  - `TELEGRAM_ALLOWED_CHAT_IDS`에 등록된 모든 Chat ID로 Markdown 포맷 메시지 전송.
  - 마크다운 파싱 에러 시 일반 텍스트로 자동 재시도하는 Fallback 탑재 (`TelegramService.send_message`).
  - 발송된 브리핑 메시지를 `telegram:{chat_id}` DB 세션에 `role="assistant"`로 자동 기록하여 대화 맥락 유지.

### 2.2 FastAPI 수명 주기 통합 (`app/main.py`)
- `lifespan` 컨텍스트 매니저에서 텔레그램 폴링 태스크와 함께 `BriefingScheduler.start()` 비동기 백그라운드 태스크 구동 및 서버 종료 시 정상 취소 처리.

### 2.3 REST API 및 수동 트리거 지원 (`app/routers/web_router.py`)
- `GET /api/briefing/scheduler/status`: 스케줄러 구동 여부, 발송 시각 및 수신자 수 조회.
- `POST /api/briefing/trigger-push`: 지정된 모드 또는 자동 판별 모드로 텔레그램 브리핑을 즉시 발송하고 결과(수신자 목록, 발송 건수) 반환.

### 2.4 웹 UI 스케줄 모달 연동 (`index.html`, `main.js`, `style.css`)
- `#schedule-modal` 내에 텔레그램 푸시 알림 상태 박스(활성 뱃지, 대상 Chat ID 안내) 바인딩.
- `[🔔 텔레그램으로 지금 즉시 발송]` 버튼을 제공하여 모달에서 즉시 시험 발송 트리거 및 결과 토스트 피드백 제공.

## 3. Consequences (영향 및 효과)
- **진정한 24/7 능동형 비서 완성**: 질문하지 않아도 매일 출근 시간(08:30 KST)과 퇴근/마감 시간(20:00 KST)에 왓슨이 스마트폰 텔레그램으로 먼저 말을 건네주어 비서 가치 극대화.
- **안전한 중복 방지 및 맥락 연속성**: 일자별 발송 플래그로 중복 발송을 차단하고, 텔레그램 세션 히스토리에 기록이 남아 브리핑 직후 자연스럽게 후속 대화 가능.
- **원클릭 테스트 지원**: 웹 콘솔 및 API를 통해 언제든 푸시 전송을 즉시 시뮬레이션하고 동작 확인 가능.
