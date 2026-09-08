# 📝 Watson - 기능 및 비기능 요구사항 명세서 (Requirements Specification)

## 1. 기능 요구사항 (Functional Requirements)

### FR-01: AI 에이전트 마크다운 처리 (AI LifeLog Engine)
- **FR-01.1**: 사용자 입력(텍스트/이미지 설명)을 수신하면 지정된 라이프 로그 템플릿(일기, 메모, 운동, 독서 등)으로 변환할 수 있어야 한다.
- **FR-01.2**: 기본 저장 경로 규칙(`lifelogs/YYYY/MM/YYYY-MM-DD.md`)을 준수하며, 파일이 존재하지 않을 경우 자동 생성하고, 존재할 경우 항목별(예: `# Daily Log`, `## Note`)로 Append 또는 Update 할 수 있어야 한다.
- **FR-01.3**: 유저가 수정을 요청할 경우 기존 MD 파일의 구조를 깨뜨리지 않고 해당 섹션만 안전하게 변경해야 한다.
- **FR-01.4 (ADR-004)**: 단순 대화/잡담은 마크다운 파일에 기록하지 않으며, 비서가 감지/제안하여 사용자가 승인했거나 직접 명시한 기록에 한해서만 마크다운에 정제하여 추가해야 한다.

### FR-02: Git 자동화 (Git Operations)
- **FR-02.1 (ADR-004)**: 단순 대화 시에는 커밋하지 않으며, 유의미한 라이프로그 작성이 확정된 시점에 즉시 `git pull --rebase` ➔ `git add` ➔ `git commit -m "[message]"` ➔ `git push`를 1기록 1커밋 단위로 자동 수행해야 한다.
- **FR-02.2**: Git Push 실패(CORS, 인증, 충돌 등) 발생 시 재시도(Retry)를 3회 수행하고, 최종 실패 시 사용자(텔레그램 알림)에게 오류 원인과 백업 데이터를 전송해야 한다.
- **FR-02.3**: Git Commit 메시지는 AI가 수정한 내용 요약 기반으로 자동 생성해야 한다. (예: `docs(lifelog): [Category] Summary - 2026-08-02`)

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
- **FR-05.4 (ADR-004)**: 비서가 제안한 라이프로그 후보(`pending_log`)를 세션에 임시 보관하고, 승인/거절 인터랙션에 따라 상태를 안전하게 처리/초기화해야 한다.

### FR-06: GTD 저장소 격리 및 동적 오케스트레이션 (GTD Directory Isolation & Orchestration - ADR-007)
- **FR-06.1**: GTD/라이프로그 저장 대상 디렉토리 경로를 웹 대시보드 UI 및 REST API (`GET/POST /api/settings/gtd-path`)를 통해 동적으로 설정하고 검증할 수 있어야 한다.
- **FR-06.2**: 설정된 GTD 디렉토리에 `.git`이 존재하는 경우 소스코드 레포가 아닌 해당 GTD 레포지토리로 독립 커밋/푸시를 집행하고, Git이 없으면 로컬 파일로만 안전하게 보관해야 한다.
- **FR-06.3**: 대상 저장소에 기정의된 GTD 체계(`gtd/inbox.md`, `logs/daily/` 등)를 자동 감지하여 왓슨이 기존 체계를 그대로 존중하며 오케스트레이션해야 한다.

### FR-07: GTD 지능형 브리핑 및 일정 요약 (Task Briefing - ADR-008)
- **FR-07.1**: 사용자의 일정/할 일 조회 요청("오늘 해야 할 일 정리해줘", "투두리스트", "일정 알려줘" 등)을 감지하여 GTD 저장소에서 오늘 일정, Next Actions, Inbox 미처리 항목을 즉시 종합 브리핑해야 한다.
- **FR-07.2**: Linux 서버 환경에서도 AGY CLI 바이너리 경로(`~/.local/bin/agy` 등)를 동적 탐색하여 유연한 비서 대화를 100% 보장해야 한다.

### FR-08: GTD 저장소 원격 동기화 및 자동 Pull (Repo Sync - ADR-009)
- **FR-08.1**: 사용자의 동기화 요청("gtd 레포 최신화하고 다시 알려줘", "레포 최신화", "/sync" 등)을 감지하여 원격 GitHub로부터 `git pull --rebase --autostash`를 통해 최신 커밋을 안전하게 동기화해야 한다.
- **FR-08.2**: "최신화하고 알려줘"와 같은 복합 명령 시 원격 동기화(pull) 후 즉시 최신 상태의 GTD 종합 브리핑을 결합 제공해야 한다.
- **FR-08.3**: `task_briefing` 실행 시 원격 저장소와 자동 사전 동기화를 수행하여 다중 기기에서의 편집 내역이 항상 최신으로 유지되도록 해야 한다.

### FR-09: 세션 대화 맥락 참조 기록 및 탄력적 엔진 (Context-Aware Logging - ADR-010)
- **FR-09.1**: 사용자가 "아까 말한 내용도 기록해줘", "방금 한 말 일기에 적어줘" 등 이전 대화 내용을 가리켜 기록을 요청할 경우, 세션 히스토리(`history`)를 역추적하여 직전 대화 원문을 감지하고 대상 마크다운 파일에 즉시 영속화해야 한다.
- **FR-09.2**: 줄바꿈이나 복합 설명문이 포함된 입력에서도 명령어를 유연하게 분리 파싱해야 한다.
- **FR-09.3**: AI 호출 시 이전 어시스턴트의 긴 응답을 경량 요약 슬라이싱하여 AGY CLI 프롬프트 비대화를 방지하고 타임아웃 오류를 차단해야 한다.

### FR-10: 결정론적 Git 원격 푸시 및 AGY Headless 무중단 실행 (Repo Push - ADR-011)
- **FR-10.1**: 사용자의 명시적 푸시 및 확인 요청("푸시해줘", "푸시도 해줘", "깃 푸시", "/push", "푸시가 안됐는데 다시 확인해줘" 등)을 감지하여 LLM 환각 응답을 차단하고 `GitService.push()`를 실행해야 한다.
- **FR-10.2**: 작업 트리에 언스테이징/수정 중인 파일이 있더라도 `autostash`를 통해 안전하게 rebase 병합 후 푸시를 집행해야 한다.
- **FR-10.3**: AGY CLI headless 모드에서 `--dangerously-skip-permissions` 플래그를 적용하여 도구 권한 거부 오류와 엉뚱한 폴백 표출을 방지해야 한다.

### FR-11: 테스트 샌드박스 격리 및 대화형 지시어 문맥 역추적 (Test Sandbox & Directive Resolution - ADR-012)
- **FR-11.1**: 스모크 테스트 실행 시 임시 GTD 샌드박스를 사용하여 실제 사용자 데이터 저장소에 테스트 더미 데이터가 유입되지 않도록 격리해야 한다.
- **FR-11.2**: "응 오늘 로그에 기록해줘" 등 지시어만 포함된 요청 수신 시 지시어 텍스트를 본문으로 오인하지 않고 세션 히스토리에서 직전 사연을 역추적하여 기록해야 한다.

### FR-12: 한국 표준시(KST) 타임존 로컬라이제이션 (Timezone Localization - ADR-013)
- **FR-12.1**: 모든 일일 로그 파일 경로(`YYYY-MM-DD.md`), 타임스탬프(`[HH:MM]`), Git 커밋 일자, 텔레그램 상태 표시 시간은 기본적으로 한국 표준시(`Asia/Seoul`, UTC+9)로 정규화되어야 한다.
- **FR-12.2**: UTC 입력 또는 naive datetime 입력에 관계없이 일관된 KST 변환 및 자정 경계(Midnight Boundary) 일자 처리가 보장되어야 한다.
- **FR-12.3**: `SettingsService` 상태 조회 API를 통해 현재 활성화된 타임존 문자열을 반환해야 한다.

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
| **FR-04** | `app/routers/web_router.py`, `app/templates/index.html` | `./scripts/smoke_test.sh` cURL 스모크 및 브라우저 UI 검증 |
| **FR-05** | `app/services/session_service.py`, `app/services/llm_provider.py` | Pytest 대화 맥락 유지/복원 & Conversational AI 테스트 |
| **FR-06** | `app/services/settings_service.py`, `app/routers/settings_router.py` | Pytest GTD 설정/오케스트레이션 테스트 & cURL 검증 |
| **FR-07** | `app/services/agent_service.py`, `app/services/supervisor_service.py` | Pytest GTD 브리핑 테스트 & cURL 검증 |
| **FR-08** | `app/services/git_service.py`, `app/services/supervisor_service.py` | Pytest GTD Pull/동기화 테스트 & cURL 검증 |
| **FR-09** | `app/services/llm_provider.py`, `app/services/supervisor_service.py` | Pytest 맥락 참조 기록 & AGY 경량화 테스트 |
| **FR-10** | `app/services/git_service.py`, `app/services/llm_provider.py`, `app/services/supervisor_service.py` | Pytest 푸시 인텐트/실행 테스트 & cURL 검증 |
| **FR-11** | `app/services/llm_provider.py`, `scripts/smoke_test.sh` | Pytest 지시어 역추적 테스트 & sandboxed cURL 검증 |
| **FR-12** | `app/config.py`, `app/services/agent_service.py` | Pytest 타임존 변환/롤오버 단위 테스트 & cURL 검증 |

