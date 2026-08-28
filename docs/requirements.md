# 📝 Watson - 기능 및 비기능 요구사항 명세서 (Requirements Specification)

## 1. 기능 요구사항 (Functional Requirements)

### FR-01: AI 에이전트 마크다운 처리 (AI LifeLog Engine)
- **FR-01.1**: 사용자 입력(텍스트/이미지 설명)을 수신하면 지정된 라이프 로그 템플릿(일기, 메모, 운동, 독서 등)으로 변환할 수 있어야 한다.
- **FR-01.2**: 기본 저장 경로 규칙(`lifelogs/YYYY/MM/YYYY-MM-DD.md`)을 준수하며, 파일이 존재하지 않을 경우 자동 생성하고, 존재할 경우 항목별(예: `# Daily Log`, `## Note`)로 Append 또는 Update 할 수 있어야 한다.
- **FR-01.3**: 유저가 수정을 요청할 경우 기존 MD 파일의 구조를 깨뜨리지 않고 해당 섹션만 안전하게 변경해야 한다.

### FR-02: Git 자동화 (Git Operations)
- **FR-02.1**: 에이전트가 MD 파일 작성/수정 완료 즉시 `git pull --rebase` ➔ `git add` ➔ `git commit -m "[message]"` ➔ `git push`를 수행해야 한다.
- **FR-02.2**: Git Push 실패(CORS, 인증, 충돌 등) 발생 시 재시도(Retry)를 3회 수행하고, 최종 실패 시 사용자(텔레그램 알림)에게 오류 원인과 백업 데이터를 전송해야 한다.
- **FR-02.3**: Git Commit 메시지는 AI가 수정한 내용 요약 기반으로 자동 생성해야 한다. (예: `docs(log): Add daily log for 2026-08-02`)

### FR-03: 텔레그램 봇 연동 (Telegram Bot Integration)
- **FR-03.1**: 텔레그램 봇 웰컴 메시지 및 도움말(`/start`, `/help`)을 제공해야 한다.
- **FR-03.2**: 텔레그램으로 받은 메시지를 에이전트에 전달하고, 깃 푸시 완료 결과를 텔레그램 답변으로 반환해야 한다.
- **FR-03.3**: 미디어(사진 등) 수신 시 이미지 저장소 경로(`static/images/YYYY-MM/`)에 저장 후 마크다운 링크(`![image](path)`)로 변환 삽입해야 한다.

### FR-04: 웹 대시보드 (Web Dashboard & Management)
- **FR-04.1**: FastAPI 기반 웹 서버로 대시보드 UI를 제공해야 한다.
- **FR-04.2**: 라이프 로그 마크다운 파일 목록 조회, 월별 달력(Calendar View), 파일 클릭 시 렌더링된 HTML 및 텍스트 에디터 기능을 제공해야 한다.
- **FR-04.3**: 웹 인터페이스 내에서도 텔레그램과 동일하게 AI 에이전트 채팅창을 통해 라이프 로그를 명령/수정할 수 있어야 한다.

### FR-05: 세션 및 대화 컨텍스트 관리 (Session & Context Management)
- **FR-05.1**: 세션 ID(Session ID)별로 대화 히스토리 및 맥락을 DB(`app/db/watson.db`)에 영속적으로 저장하고 복원할 수 있어야 한다.
- **FR-05.2**: 동일 세션 내에서 유저가 이전 대화 내용을 인용하거나 연속된 수정을 요청하면 이전 컨텍스트(Context History)를 LLM 앤드포인트에 함께 전달해야 한다.
- **FR-05.3**: 텔레그램(유저/대화방 단위) 및 웹 대시보드(대화방 생성/전환 단위)에서 멀티 세션을 독립적으로 조회/전환할 수 있어야 한다.

---

## 2. 비기능 요구사항 (Non-Functional Requirements)

### NFR-01: 성능 및 속도 (Performance)
- **NFR-01.1**: 텔레그램/웹 요청 수신 후 AI 처리 및 GitHub Push 완료까지 **5초 이내** 응답해야 한다.
- **NFR-01.2**: 24/7 지속 가동 환경에서 메모리 누수 없이 경량화된 Python 프로세스 상태를 유지해야 한다.

### NFR-02: 안정성 및 복구성 (Reliability & Recovery)
- **NFR-02.1**: 인터넷 연결 끊김 또는 GitHub 장애 발생 시, 로컬에 임시 저장(Local Queue) 후 연결 재개 시 자동 푸시해야 한다.
- **NFR-02.2**: 서비스 예기치 않은 종료 시 systemd / docker restart policy에 의해 자동 재시작되어야 한다.

### NFR-03: 보안 (Security)
- **NFR-03.1**: 텔레그램 봇은 허용된 사용자 ID(Chat ID)의 요청만 처리하도록 화이트리스트 검증을 적용해야 한다.
- **NFR-03.2**: GitHub Access Token, Telegram Bot Token, LLM API Key 등 비밀 정보는 `.env` 및 환경 변수로 엄격히 분리 및 관리한다.

---

## 3. 추적성 매트릭스 (Requirements Traceability Matrix)

| 요구사항 ID | 주요 관련 모듈 | 검증 방법 |
| :--- | :--- | :--- |
| **FR-01** | `app/services/agent_service.py` | Pytest 단위 테스트 |
| **FR-02** | `app/services/git_service.py` | Git mock & 실제 push 테스트 |
| **FR-03** | `app/routers/telegram_router.py` | 텔레그램 Webhook / Polling 테스트 |
| **FR-04** | `app/routers/web_router.py` | 스모크 및 브라우저 UI 검증 |
| **FR-05** | `app/services/session_service.py` | Pytest 대화 맥락 유지/복원 테스트 |
