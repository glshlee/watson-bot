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

### FR-13: 복합 의도 감지 및 GTD 태스크 정제 (Compound Intent & Task Formulation - ADR-014)
- **FR-13.1**: "로그와 gtd에 기록해줘", "일기랑 할일에 적어줘" 등 단일 요청에서 일기 기록과 GTD 태스크 수집이 동시에 지시된 경우, 복합 인텐트(`log_dual`)로 자동 분류되어야 한다.
- **FR-13.2**: 발화 끝의 지시어("로그와 gtd에 기록해줘") 및 불필요한 구두점을 완벽히 절삭하여 데일리 로그에 순수한 일상 서사만 기록해야 한다.
- **FR-13.3**: 비정형 일기 텍스트에서 여행/맛집/업무 등의 실행 키워드를 추출하여 행동 지향적 태스크 포맷으로 합성하고, GTD 인박스의 적합한 섹션(`## 🧘 개인 생활 & 건강` 등)에 배치해야 한다.
- **FR-13.4**: 데일리 로그와 GTD 인박스 두 변경 사항을 원자적(atomic)으로 Git 커밋 및 동기화해야 한다.

### FR-14: 웹 콘솔 보안 인증 및 Cloudflare Tunnel 외부 연동 (Web Auth & Tunnel - ADR-015)
- **FR-14.1**: `WEB_AUTH_ENABLED=true` 활성화 시, 웹 대시보드(`/`) 및 모든 관리 API(`/api/chat`, `/api/sessions`, `/api/settings/*`)는 HTTP Basic 인증(`Authorization: Basic`)을 요구해야 하며, 미인증 시 401 Unauthorized와 `WWW-Authenticate` 헤더를 반환해야 한다.
- **FR-14.2**: 인바운드 포트 개방 없이 Cloudflare Tunnel을 통해 안전한 HTTPS 외부 접속 경로를 제공해야 한다.
- **FR-14.3**: `watson-tunnel.service` 데몬을 통해 24/7 상시 터널링 가동 및 토큰 기반 영구 도메인 연동을 지원해야 한다.

### FR-15: 모바일 퍼스트 반응형 웹 인터페이스 및 터치 UX 최적화 (Mobile Responsive UX - ADR-016)
- **FR-15.1**: 모바일 화면(<= 768px)에서 사이드바를 오프캔버스 드로어로 자동 전환하고, 햄버거 메뉴 및 반투명 백드롭으로 여닫을 수 있어야 한다.
- **FR-15.2**: 세션 전환 또는 새 세션 생성 시 모바일 드로어가 자동으로 닫혀 즉시 채팅 입력창에 집중할 수 있어야 한다.
- **FR-15.3**: `100dvh` 동적 뷰포트와 iOS Safe Area(`env(safe-area-inset-bottom)`), 모바일 16px 폰트(자동 줌 방지)를 적용하여 스마트폰 브라우저 환경에서 매끄러운 스크롤 및 터치 UX를 제공해야 한다.

### FR-16: 웹 콘솔 세션 관리 고도화 (Advanced Session Management UI - ADR-017)
- **FR-16.1**: 세션 목록 실시간 검색창과 `전체` / `웹` / `텔레그램` 채널 필터 탭을 제공하여 다중 세션을 신속하게 탐색할 수 있어야 한다.
- **FR-16.2**: `PATCH /api/sessions/{session_id}` API를 통해 세션 제목을 수정하고 실시간 UI 및 SQLite DB에 반영할 수 있어야 한다.
- **FR-16.3**: `DELETE /api/sessions/{session_id}` API를 통해 특정 세션 및 하위 메시지를 영구 삭제하고, 현재 활성 세션 삭제 시 안전하게 인접 세션으로 폴백해야 한다.
- **FR-16.4**: `POST /api/sessions/{session_id}/clear` API를 통해 세션을 유지한 채 대화 내역만 초기화할 수 있어야 한다.
- **FR-16.5**: 신규 세션에서 기본 제목("New Conversation" 등) 상태일 때 사용자의 첫 발화 기반으로 스마트 제목 자동 생성이 실행되어야 한다.
- **FR-16.6**: 세션 카드에 메시지 개수, 상대 시간("방금", "5분 전"), 채널 배지를 표시하고 헤더 영역과 동기화되어야 한다.

### FR-17: 에이전트 허브 대시보드 포털 및 개발 에이전트 분리 (Agent Hub & Dev Agent - ADR-018)
- **FR-17.1**: 루트 경로(`/`) 요청 시 Watson 비서, DevBot 개발자, 확장 슬롯을 카드 형태로 제공하는 에이전트 허브 대시보드(`portal.html`)를 반환해야 한다.
- **FR-17.2**: `GET /api/hub/status` API를 통해 등록된 에이전트 목록, 활성 상태, 세션 수량 및 워크스페이스 상태 메트릭을 반환해야 한다.
- **FR-17.3**: `GET /watson` 엔드포인트를 통해 비서 왓슨 전용 콘솔을 제공하고, `GET /dev` 엔드포인트를 통해 개발 전담 DevBot 콘솔을 제공해야 한다.
- **FR-17.4**: `POST /api/dev/chat` 엔드포인트를 통해 Git 상태/Diff/Log/Branch 등의 빠른 도구 명령 실행 및 소프트웨어 엔지니어링 AI 응답을 제공해야 한다.
- **FR-17.5**: `SessionModel`의 `agent_type` 컬럼을 통해 왓슨 비서 세션(`watson`)과 개발 에이전트 세션(`dev`)을 상호 격리해야 한다.
- **FR-17.6**: 각 에이전트 콘솔 상단 헤더에 `[🏠 에이전트 허브]` 바로가기 버튼을 제공하여 포털과의 유기적 이동을 보장해야 한다.

### FR-18: DevBot 대화형 엔지니어링 툴체인 및 실시간 개발 실행 환경 (Interactive Dev Toolchain - ADR-019)
- **FR-18.1**: `POST /api/dev/chat`에 `/test` 명령 전달 시 대상 테스트 파일(또는 기본 코어 스위트)에 대한 `pytest`를 비차단 방식으로 안전하게 실행하고 요약 브리핑을 반환해야 한다.
- **FR-18.2**: `POST /api/dev/chat`에 `/lint` 명령 전달 시 `ruff check .` 및 `mypy .`를 실행하여 정적 분석 및 타입 검사 결과를 뱃지 형태로 보고해야 한다.
- **FR-18.3**: `POST /api/dev/chat`에 `/commit` 명령 전달 시 변경점을 분석하여 Conventional Commits 3종을 추천하거나, 메시지가 함께 전달된 경우 Git 커밋을 원자적으로 집행해야 한다.
- **FR-18.4**: `POST /api/dev/chat`에 `/help` 명령 전달 시 사용 가능한 모든 개발자 단축 도구 목록과 사용 예시를 반환해야 한다.
- **FR-18.5**: DevBot AI 엔지니어링 추론 시 `docs/roadmap.md`의 최근 마일스톤 및 워크스페이스 상태를 프롬프트 컨텍스트에 실시간 주입하고, AGY CLI 비대화형 표준 규격(`-p`, `--dangerously-skip-permissions`)으로 실행해야 한다.
- **FR-18.6**: 웹 콘솔(`/dev`) 입력창 상단에 빠른 도구 실행을 위한 퀵 액션 칩(`/test`, `/lint`, `/commit`, `/help`)을 제공해야 한다.
- **FR-18.7**: 모든 외부 명령어 인자에 대해 경로 트래버설(`..`) 및 쉘 메타문자 인젝션을 방지하는 보안 검증을 수행해야 한다.

### FR-19: 결정론적 GTD 태스크 삭제, 구어체 원격 푸시/커밋 라우팅 및 저장소 투명성 (ADR-020)
- **FR-19.1**: 사용자 메시지에 등록된 태스크 삭제/제거 의도("제거해", "삭제해", "빼줘" 등) 감지 시 `inbox.md` 및 `next_actions.md`에서 일치하는 태스크를 물리적으로 안전하게 제거하고 Git 커밋/푸시를 집행해야 한다.
- **FR-19.2**: "커밋해", "커밋", "/commit" 등 명시적 커밋 요청 시 작업 트리가 변경되었을 때만 실제 `git commit`을 집행하고, 변경점이 없으면 깨끗한 상태를 정직하게 보고해야 한다.
- **FR-19.3**: "푸시도해야지", "푸시해야지", "올려야지" 등 한국어 구어체 어미와 보조사를 `repo_push` 인텐트로 완벽히 라우팅하여 실제 `git push`를 집행해야 한다.
- **FR-19.4**: "어디다 푸시한거야?", "어디로 푸시했어?" 등 푸시 대상/상태 질의 시 실제 연결된 GitHub Remote URL, 브랜치명, 최신 커밋 해시를 투명하게 반환하고, 가상 브랜치 날조 등 LLM 환각을 원천 차단해야 한다.

### FR-20: 웹 연결 복원력, Cloudflare HTTP/2 터널 안정화 및 화면 복귀 자동 동기화 (ADR-021)
- **FR-20.1**: Cloudflare Tunnel 연결 시 `--protocol http2` 및 `--retries 10`을 설정하여 클라우드 NAT 게이트웨이 및 모바일 네트워크에서의 UDP 유휴 타임아웃 및 QUIC 스트림 드롭을 원천 차단해야 한다.
- **FR-20.2**: Uvicorn 구동 시 `--timeout-keep-alive 75` 및 `--limit-concurrency 100`을 적용하여 역방향 프록시와의 연결 닫힘 경합 및 502/504 Bad Gateway를 방지해야 한다.
- **FR-20.3**: `GET /api/health` 및 `GET /healthz` 초경량 헬스체크 엔드포인트를 제공하여 터널 모니터링 및 프론트엔드 하트비트 핑에 `< 1ms` 내 응답해야 한다.
- **FR-20.4**: 프론트엔드 웹 콘솔(`main.js`, `dev.js`)에 `fetchWithRetry` 지능형 재시도 엔진을 적용하여 일시적 네트워크 결함 시 지수 백오프로 자동 재시도하고, 65초 타임아웃 신호를 주입해야 한다.
- **FR-20.5**: 모바일 화면 꺼짐 및 탭 백그라운드 복귀 시(`visibilitychange`, `online`) 즉시 헬스체크 및 세션 히스토리 재동기화를 수행하여 서버에서 완료된 AI 응답을 유실 없이 자동 렌더링해야 한다.
- **FR-20.6**: 프론트엔드 최상단에 실시간 연결 상태 배너(`#connection-banner`)와 3단계 펄스 인디케이터(`online`, `warning`, `offline`) 및 수동 재시도 버튼을 제공해야 한다.

### FR-21: GTD 및 데일리 로그 파일 즉시 열람 숏컷 & DevBot 대기시간 최적화 (ADR-022)
- **FR-21.1**: `AgentService`에 `read_daily_log()`, `read_gtd_files()`, `read_gtd_and_daily_log()`를 구현하여 오늘자 일일 로그 및 GTD 수집함/다음 행동 파일의 마크다운 원본, 수정 시각, 줄 수, 미완료 태스크 개수를 0.01초 내에 반환해야 한다.
- **FR-21.2**: `LLMProvider`에 `daily_log_inspect`(`/today`, `/daily`), `gtd_inspect`(`/gtd`, `/inbox`), `gtd_and_log_inspect`(`/gtd-today`, `/today-gtd`), `task_briefing`(`/briefing`) 인텐트 분류 및 라우팅을 지원해야 한다.
- **FR-21.3**: `SupervisorService` 및 `DevAgentService`에서 해당 인텐트 수신 시 LLM 지연 없이 로컬 파일 시스템을 즉시 조회하여 초고속으로 응답해야 한다.
- **FR-21.4**: DevBot 엔지니어링 추론 시 대화 히스토리를 200자로 축약(ADR-010 규격)하고 AGY 타임아웃을 35초로 튜닝하여 무응답 결함을 차단해야 한다.
- **FR-21.5**: Watson 비서 웹 콘솔(`.watson-quick-bar`) 및 DevBot 웹 콘솔(`.dev-quick-bar`)에 빠른 실행 칩을 제공하여 원터치 조회를 지원해야 한다.

### FR-22: 모바일 뷰포트 레이아웃 안정화 & 컴포넌트 충돌 방지 (ADR-023)
- **FR-22.1**: 모바일 화면(<= 768px)에서 헤더 부제목 텍스트(`p#chat-subtitle`)를 숨김 처리하여 360px 기기에서도 타이틀 줄바꿈 및 우측 버튼과의 수평 충돌을 100% 방지해야 한다.
- **FR-22.2**: 모바일 우측 액션 배지들을 `34x34px` 정사각형 터치 버튼으로 정돈하고, GTD 경로 배지 및 텍스트 폭을 50px로 축약(ellipsis)하여 좌우 컴포넌트 간 여백을 확보해야 한다.
- **FR-22.3**: 하단 빠른 칩 바(`.watson-quick-bar`, `.dev-quick-bar`)를 불필요한 테두리/패딩 없는 슬림 가로 스와이프 필 바(`scrollbar-width: none`)로 개편하고, 수동 카테고리 드롭다운을 제거해 100% AI 자동 분류로 전환함으로써 하단 고정 높이를 140px에서 65px 수준으로 슬림화해야 한다.
- **FR-22.4**: `.message`, `.bubble`, `.code-block`에 `min-width: 0; word-break: break-word; overflow-wrap: anywhere;`를 적용하고, 아바타에 `flex-shrink: 0;`을 고정하여 코드 블록 및 마크다운 표 출력 시 화면 밀림과 Flex Overflow를 원천 차단해야 한다.
- **FR-22.5**: 에이전트 허브 포털의 메트릭 카드를 모바일에서 2x2 반응형 그리드로 정돈하고, 정적 CSS/JS 캐시 방지를 위해 `v=1.3.3` 쿼리 파라미터를 적용해야 한다.

### FR-23: 아침/저녁 맞춤형 GTD 브리핑 프로토타입 (Morning & Evening Briefing - ADR-024)
- **FR-23.1**: `BriefingService`를 통해 시간대(KST 기준 오전 05:00~13:59는 morning, 14:00 이후는 evening) 기반 자동 모드 판별 및 명시적 인자(`/briefing morning`, `/briefing evening`)를 처리해야 한다.
- **FR-23.2**: 아침 브리핑 시 오늘 집중해야 할 **Top 3 우선순위**, 오전/오후 추천 실행 순서, Inbox 미분류 정리 권유를 구조화하여 제공해야 한다.
- **FR-23.3**: 저녁 브리핑 시 오늘 완료된 작업 하이라이트 요약, 미완료 과제 점검 및 내일로의 이월(Rollover), 내일 아침 1순위 핵심 과제를 제안해야 한다.
- **FR-23.4**: LLM 지능형 합성 엔진과 0.01초 무지연 결정론적 룰 기반 포맷터 듀얼 엔진으로 무결점 복원력을 제공해야 한다.
- **FR-23.5**: 외부 연동용 REST API(`GET /api/briefing?mode=morning|evening`) 및 웹 콘솔 퀵 바 원터치 칩(`[🌅 아침 브리핑]`, `[🌇 저녁 회고]`)을 제공해야 한다.

### FR-24: 브리핑 스케줄 UI 시각화 및 당일 일정 타임라인 (ADR-025)
- **FR-24.1**: `BriefingService.get_schedule_info()` 및 `format_schedule_briefing()`을 통해 아침 브리핑(08:30 KST, 활성 05:00~13:59), 저녁 회고(20:00 KST, 활성 14:00~04:59)의 정규 시각 및 당일 일일 로그(`logs/daily/YYYY-MM-DD.md`)의 시간대별 일정 타임라인을 구조화하여 제공해야 한다.
- **FR-24.2**: `LLMProvider`에 `briefing_schedule_inspect`(`/schedule`, `/briefing schedule`, "몇 시에 스케줄링 되어있어?", "스케줄 확인") 인텐트를 추가하고 지연 없이 즉각 브리핑을 반환해야 한다.
- **FR-24.3**: `GET /api/briefing/schedule` REST API를 통해 현재 활성 모드, 아침/저녁 규격 및 당일 일정 목록을 JSON으로 제공해야 한다.
- **FR-24.4**: 웹 콘솔 퀵 바에 시간 명시 칩(`[🌅 아침 (08:30)]`, `[🌇 저녁 (20:00)]`)과 `[⏰ 스케줄]` 칩을 제공하고, 탭 시 `#schedule-modal`을 통해 활성 뱃지 및 타임라인을 시각화해야 한다.

### FR-25: 텔레그램 정기 브리핑 자동 푸시 스케줄러 (ADR-026)
- **FR-25.1**: `BriefingScheduler` 백그라운드 서비스를 통해 매일 08:30 KST(아침) 및 20:00 KST(저녁) 정각을 감지하여 텔레그램 허용 사용자(`TELEGRAM_ALLOWED_CHAT_IDS`)에게 맞춤형 브리핑을 능동 푸시 발송해야 한다.
- **FR-25.2**: 일자별 발송 플래그(`last_dispatched`)를 유지하여 동일 일자에 동일 모드 브리핑이 중복 발송되는 결함을 원천 방지해야 한다.
- **FR-25.3**: 발송 직전 `git pull`을 수행하여 원격 최신 변경점을 반영하고, 발송된 브리핑은 `telegram:{chat_id}` DB 세션에 저장되어 대화 맥락을 보존해야 한다.
- **FR-25.4**: `GET /api/briefing/scheduler/status` 및 `POST /api/briefing/trigger-push` REST API를 제공하여 스케줄러 상태 확인과 즉시 시험 발송을 지원해야 한다.
- **FR-25.5**: 웹 콘솔 스케줄 모달(`#schedule-modal`)에 텔레그램 푸시 연동 박스와 `[🔔 텔레그램으로 지금 즉시 발송]` 버튼을 제공해야 한다.

### FR-26: 텔레그램 인터랙티브 인라인 키보드 및 원클릭 태스크 조작 (ADR-027)
- **FR-26.1**: 아침 브리핑(`task_done_top1`, `action_sync`, `action_show_tasks`, `action_push`) 및 저녁 회고(`action_prompt_diary`, `action_sync`, `action_push`, `action_show_next`)에 대응하는 2x2 규격의 인터랙티브 인라인 키보드를 자동 부착해야 한다.
- **FR-26.2**: `AgentService.complete_top_task()`는 `gtd/next_actions.md`, 당일 일일 로그, `gtd/inbox.md` 순으로 첫 번째 미완료 항목(`- [ ]`)을 `- [x]`로 안전하게 완료 처리하고 Git 커밋 및 푸시를 실행해야 한다.
- **FR-26.3**: 텔레그램 `/done` 및 `/done [태스크명]` 슬래시 커맨드를 지원하여 대화형 또는 수동 완료 처리가 가능해야 한다.
- **FR-26.4**: 콜백 쿼리 수신 시 `answer_callback_query`를 통해 0.1초 내 터치 토스트 응답을 전달하고, 실행 결과를 세션 히스토리에 영속화해야 한다.

### FR-27: 기록 여부 결정론적 검사 및 문두 지시어 라우팅 (ADR-028)
- **FR-27.1**: `LLMProvider`에 `log_status_inspect` 인텐트를 신설하여 `"오늘 로그 파일에 기록했어?"`, `"기록했어?"`, `"오늘 일기 적었어?"`, `"기록 확인"` 등 기록 여부 질의를 LLM 대화로 넘기지 않고 물리적 디스크 검사 파이프라인으로 라우팅해야 한다.
- **FR-27.2**: `SupervisorService`는 실제 당일 일일 로그(`logs/daily/YYYY-MM-DD.md`) 파일 및 본문 엔트리(`- [HH:MM]`) 존재 여부를 검사하여, 존재할 경우 전문과 수정시각을 보고하고, 미작성 시 정직하게 안내함과 동시에 직전 사용자 대화를 역추적하여 "응" 원클릭 기록 승인을 유도해야 한다.
- **FR-27.3**: 문장 시작부에 지시어가 위치하는 문두 기록 패턴(`front_record_pattern`)과 구어체 액션 정규식(`record_action_pattern`)을 지원하여 `"어제 gtd에 이 내용을 넣어달라구 [본문]"`, `"업데이트 해줘 위 내용"` 등의 지시어를 누락 없이 실제 파일 기록으로 연계해야 한다.
- **FR-27.4**: `LLMProvider._call_ai_engine` 시스템 프롬프트에 가상 시뮬레이션 기록 답변 금지 가드레일을 적용하여 언어모델의 환각을 원천 차단해야 한다.

### FR-28: 2단계 사전 검토 및 원터치 승인 워크플로우 (ADR-029)
- **FR-28.1**: 운동, 생각/아이디어, 일상/업무, 가족/식사/병원 등 삶의 일과 감지 시 즉각적인 물리 파일 기록 및 커밋을 지양하고, `log_suggest` 인텐트를 통해 정제된 타임스탬프(`- [HH:MM]`), 저장 경로, 카테고리를 포함한 마크다운 초안 카드(Draft Preview Card)를 사용자에게 사전에 제시해야 한다.
- **FR-28.2**: 제안 시 세션 메타데이터(`pending_log`)에 본문, 카테고리, GTD 액션 태스크, 듀얼 로깅 여부를 SQLite에 보관하고, 승인("응", "좋아", "이대로 해줘", 버튼 클릭) 시 단일/듀얼 기록을 실행하며 `pending_log`를 초기화해야 한다.
- **FR-28.3**: 텔레그램에서는 인라인 버튼(`[✅ 응, 기록해줘]`, `[❌ 아니야]`)을 부착하고, 웹 대시보드(`/watson`)에서는 퀵 액션 버튼(`[응, 기록해줘]`, `[아니야]`)을 동적 제공하여 무타자 원터치 승인/거절을 지원해야 한다.
- **FR-28.4**: 파워유저를 위한 패스트트랙(`/log [내용]`)을 유지하여 2단계 검토 없이 0초 만에 직접 물리 기록 및 Git 커밋·푸시를 집행할 수 있어야 한다.

### FR-29: 출근길 맞춤형 브리핑 설정 인터페이스 및 동적 연동 (ADR-030)
- **FR-29.1**: `CommuteConfigService`를 구축하여 거주 지역(동네명, 기상 격자 X/Y 좌표, 대기 측정소명), 출근길 버스(탑승 정류소명, 정류소 ID, 버스 노선 번호, 도시코드), 정기 발송 시각(`07:30` KST, 평일 전용 토글), 공공데이터포털 API 키를 `config/commute_config.json`에 안전하게 영속화해야 한다.
- **FR-29.2**: RESTful API(`GET/POST /api/settings/commute`, `POST /api/settings/commute/preview`)를 제공하여 설정 조회(API 키 마스킹 포함), 설정 저장, 실시간 카드 렌더링 미리보기를 지원해야 한다.
- **FR-29.3**: 웹 콘솔 상단 헤더 배지(`[🚌 출근: 07:30]`), 퀵바 칩(`[🚌 출근길 설정]`), 인터랙티브 모달(`#commute-modal`)을 제공하여 타이핑 없이 1클릭으로 설정을 열람/수정하고 모달 내에서 실시간으로 브리핑 카드를 테스트할 수 있어야 한다.
- **FR-29.4**: 대화형 슬래시 명령어(`/commute`, `/commute test`) 및 자연어 질의("출근길", "우리 동네 날씨", "버스 언제 와")를 지원하여 현재 설정 현황 및 실시간 브리핑 카드를 즉시 확인할 수 있어야 한다.
- **FR-29.5**: 공공데이터 API 키 미등록 또는 외부 서버 장애 시에도 스마트 시뮬레이션(Mock) 모드로 자동 폴백되어 시스템이 중단되지 않아야 한다.

### FR-30: 구어체 태스크 완료 인식 고도화 및 항의·메타 피드백 가드레일 (ADR-031)
- **FR-30.1**: "민방위 사이버교육은 완료했어", "사이버교육 다했어", "보고서 제출 끝났어" 등 일상 구어체 완료 발화를 정확히 감지하여 `task_complete` 인텐트로 라우팅해야 한다.
- **FR-30.2**: `[태스크] 완료 gtd에 기록해/반영해` 지시 시 신규 미완료 태스크 생성을 원천 차단하고 기존 GTD 태스크의 완료(`- [x]`) 처리로 우선 라우팅해야 한다.
- **FR-30.3**: "아니 이미 인박스에 있다면서. 그래서 완료했다고 말한건데?" 등 봇의 이전 동작에 대한 항의/정정 발화 감지 시 일기 초안(`log_suggest`)으로 오인 제안하지 않고, 대화 히스토리를 역추적하여 원래 요청 태스크를 찾아 자동 복구 및 정중히 사과해야 한다.
- **FR-30.4**: `AgentService.complete_matching_tasks`는 서술어("완료했어", "끝났어", "해결함", "은/는/이/가")를 자동 정제하고 2글자 이상 세부 토큰으로 분해하여 유연하고 안전하게 GTD 태스크를 매칭해야 한다.
### FR-31: GTD 스킬 명세 동기화 및 태스크 완료 시 데일리 로그 수술적 이관 (ADR-032)
- **FR-31.1**: 미완료 할 일은 오직 `gtd/` 디렉토리 5개 상태 파일(`inbox.md`, `next_actions.md` 등)에서만 보관(SSOT)하고, 데일리 로그(`logs/daily/YYYY-MM-DD.md`)는 미완료 할 일을 남기거나 이월(Rollover)하지 않아야 한다.
- **FR-31.2**: 태스크 완료("완료했어", "/done", 1순위 완료 등) 시 `AgentService`는 `gtd/` 파일에서 해당 항목을 완전히 잘라내어(Cut) 제거하고, 당일 데일리 로그(`logs/daily/YYYY-MM-DD.md`)의 `## ✅ 오늘 완료한 일 (Completed GTD Tasks)` 섹션으로 `- [x]` 형태로 안전하게 이관(Paste)해야 한다 (`transfer_completed_task_to_daily_log`).
### FR-32: 아침 브리핑 실시간 날씨·미세먼지 통합 및 자연어 기상 질의 연동 (ADR-033)
- **FR-32.1**: `BriefingService`의 아침 브리핑(`mode == "morning"`) 및 08:30 KST 텔레그램 푸시 시 최상단 인사말 직후 실시간 날씨(기온, 체감, 강수확률, 우산 소지 팁), 대기질(PM10/PM2.5 수치), 출근 버스 정보를 필수 통합 렌더링해야 한다.
- **FR-32.2**: `BriefingService.generate_briefing`의 LLM 프롬프트에 실시간 기상 데이터를 제공하고, AI 응답 필터에서 부적절한 `"날씨"` 배제 조건을 제거하여 AI가 날씨와 GTD 일정을 조화롭게 브리핑할 수 있도록 보장해야 한다.
- **FR-32.3**: "날씨 브리핑", "날씨 정보", "미세먼지 수치", "대기질 정보", `/weather` 등 자연어 기상 질의 시 `commute_inspect` (`log_content="weather"`)로 즉시 라우팅하여 단독 기상 브리핑 카드를 반환해야 한다.
- **FR-32.4**: "안녕하세요! 오늘 날씨 좋네요" 등 인사가 포함된 일상 발화는 기상 카드 대신 자연스러운 대화(`chat_only`)로 분리 유지해야 한다.

### FR-34: Open-Meteo 무설정 오픈 API 기반 실시간 날씨 및 대기질 연동 (ADR-035)
- **FR-34.1**: API 키 발급이 불필요한 Open-Meteo 글로벌 오픈 API(`Forecast API`, `Air Quality API`)를 연동하여 거주지 위경도 좌표 기준 실시간 기온, 체감온도, 하늘상태(WMO 코드), 일일 강수확률, PM10, PM2.5를 직접 조회하는 `WeatherService`를 제공해야 한다.
- **FR-34.2**: 대기질 수치는 한국 환경부 기준 등급(좋음, 보통, 나쁨, 매우나쁨) 및 직관적 색상 이모지(🟢, 🟡, 🟠, 🔴)로 정규화하여 출력해야 한다.
- **FR-34.3**: 강수확률 및 WMO 기상 코드(비/눈/소나기/뇌우)를 결합하여 `우산 필수 ☔`, `접이식 우산 추천 🌂`, `우산 불필요 ☀️`를 결정론적으로 제안하는 우산 팁 생성 로직을 제공해야 한다.
- **FR-34.4**: `GeoService` 내 서울 25개 구 및 전국 주요 지역의 위도(`lat`)와 경도(`lon`)를 탑재하여 동네 설정 시 위경도를 자동 영속화해야 한다.
- **FR-34.5**: 10분(600초) TTL 인메모리 캐시를 적용하여 중복 호출을 차단하고, 3.5초 타임아웃 및 네트워크 장애 시 최근 캐시 또는 스마트 시뮬레이션 데이터로 무중단 안전 폴백(Fallback)되어야 한다.
- **FR-34.6**: 모든 브리핑 및 날씨 카드에 `(📡 Open-Meteo 실시간 라이브 API - HH:MM 기준)` 출처 배지를 명시하여 데이터 신뢰성을 보장해야 한다.

### FR-35: 키워드 정규식 가로채기 철거 및 LLM 자연어 위임·부정 피드백 가드레일 (ADR-036)
- **FR-35.1**: 단순 명사 부분 일치(`workout_keywords`, `idea_keywords`, `work_keywords`, `life_keywords`)에 의해 무조건 `log_suggest` 초안 카드가 생성되던 정규식 가로채기 블록을 전면 철거해야 한다.
- **FR-35.2**: `"필요 없어"`, `"필요가 없어"`, `"안 사도 돼"`, `"안 해도 돼"`, `"선물받아"`, `"취소"`, `"삭제"`, `"어때?"` 등 부정/불필요/취소/피드백 발화 감지 시 일과 초안 생성을 원천 차단하고 즉시 LLM 대화(`chat_only`)로 위임해야 한다.
- **FR-35.3**: "휴지는 선물받아서 구매할 필요가 없어" 등에서 "필[요가] 없어"의 "요가"가 서브스트링으로 오탐지되어 `Workout & Health` 초안이 생성되는 결함을 원천 차단해야 한다.
### FR-36: 실시간 출근 버스 도착정보 API 실연동 및 지능형 캐시·안전 폴백 (ADR-037)
- **FR-36.1**: 서울시 TOPIS 버스도착정보조회 API(`http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid`)를 연동하여 ARS ID 및 노선 번호 기반 실시간 잔여시간(분/초), 남은 정류소 수, 막차/출발대기 상태를 조회하는 `BusService`를 제공해야 한다.
- **FR-36.2**: 국토교통부 TAGO 버스도착정보조회 API(`http://apis.data.go.kr/1613000/ArvlInfoInqireService/getSttnAcctoArvlPrearngeInfoList`)를 연동하여 전국 및 경기도 정류소 도착 예정 정보를 조회해야 한다.
- **FR-36.3**: `urllib.parse.unquote()` 기반 이중 인코딩 방지를 적용하여 공공데이터포털(data.go.kr)의 인코딩/디코딩 키와 완벽히 호환되어야 한다.
- **FR-36.4**: 45초 TTL 인메모리 캐시를 적용하여 중복 호출을 최소화하고 0.01초 초고속 응답을 보장해야 한다.
- **FR-36.5**: API 키 미설정 또는 외부 장애 시 현재 분(minute) 기반 가변적 잔여 시간(3~11분)과 비서 출근 팁을 동적 계산하여 정적 4분 고정 결함을 탈피하고 안전한 시뮬레이션 폴백을 제공해야 한다.
- **FR-36.6**: `/bus`, "출근 버스 언제 와?", "버스 도착 정보" 등 자연어 및 슬래시 커맨드 질의 시 단독 실시간 버스 도착 카드를 즉시 반환해야 한다.

### FR-37: 정류소 번호 원클릭 조회 및 지능형 정류소명 자동 매핑과 테스트 샌드박스 보존 (ADR-038)
- **FR-37.1**: 서울 5자리 ARS-ID 및 전국 정류소 번호 입력 시 공공 정류소 DB/지도 검색을 통해 정류소명, 방면, 행정구역을 실시간 역조회하고 1시간 캐시하는 `BusService.resolve_bus_stop`을 제공해야 한다.
- **FR-37.2**: `POST /api/settings/commute/resolve-bus-stop` 엔드포인트를 제공하고 웹 모달 Section 2에서 정류소 번호 입력 시 정류소명을 실시간 자동 완성해야 한다.
- **FR-37.3**: 스모크 테스트 실행 시 `config/commute_config.json`을 백업/복원하여 실제 사용자 API 키와 출근길 설정을 영구 보존해야 한다.

### FR-38: 실시간 버스 도착 정보 원터치 인라인 갱신 및 웹/텔레그램 동시 지원 (ADR-039)
- **FR-38.1**: `BusService.get_arrival_info` 및 `CommuteConfigService`에 `force_refresh=True` 매개변수를 지원하여 45초 캐시를 우회하고 실시간 강제 조회를 집행해야 한다.
- **FR-38.2**: 단독 버스 카드의 조회 일시에 초 단위 타임스탬프(`%H:%M:%S KST`)를 적용하여 갱신 완료 여부를 명확히 시각화해야 한다.
- **FR-38.3**: `GET/POST /api/settings/commute/bus-card` REST 엔드포인트를 통해 최신 마크다운 카드, 브리핑 요약 행, 갱신 시각을 즉시 반환해야 한다.
- **FR-38.4**: 텔레그램 버스 카드 및 아침 브리핑에 `[🔄 실시간 버스 갱신]` 인라인 키보드를 부착하고, `editMessageText`를 통해 기존 메시지를 인플레이스로 즉시 수정해야 한다.
- **FR-38.5**: 웹 대시보드 콘솔 버스 카드 말풍선 하단에 `[🔄 버스 도착 갱신]` 버튼을 렌더링하고, 클릭 시 해당 말풍선 내 도착 시간을 인라인으로 즉시 새로고침하며 퀵 바에 `[🚍 버스 도착]` 칩을 제공해야 한다.

### FR-39: 텔레그램 네이티브 봇 메뉴 명령어 등록 및 자동 동기화 (ADR-040)
- **FR-39.1**: `TelegramService.DEFAULT_COMMANDS`에 핵심 14종 명령어(`today`, `briefing`, `bus`, `log`, `done`, `gtd`, `schedule`, `commute`, `sync`, `push`, `url`, `status`, `help`, `start`)와 한글 설명을 표준 정의해야 한다.
- **FR-39.2**: `TelegramService.set_my_commands()`를 통해 Telegram Bot API `setMyCommands` 및 `setChatMenuButton`을 연동하고, 봇 폴링 루프 기동 시 자동 실행되어야 한다.
- **FR-39.3**: `POST /api/telegram/setup-commands` 및 `GET /api/telegram/commands` REST 엔드포인트를 제공하여 명령어 등록 및 상태 조회가 가능해야 한다.
- **FR-39.4**: 텔레그램 메뉴에서 `/gtd` 실행 시 단순 저장소 메타데이터가 아닌 실제 수집함 및 다음 행동 목록을 반환해야 한다.

### FR-40: 텔레그램 봇 메뉴 명령어 관리 UI 및 실시간 모바일 미리보기·원터치 동기화 (ADR-041)
- **FR-40.1**: `config/telegram_commands.json` 파일을 통해 사용자 정의 명령어 목록 및 활성화 여부(`enabled: bool`)를 안전하게 영속화해야 한다.
- **FR-40.2**: `POST /api/telegram/commands` (저장 및 즉시 동기화) 및 `POST /api/telegram/commands/reset` (14종 기본값 복원) 엔드포인트를 제공해야 한다.
- **FR-40.3**: 웹 콘솔 헤더 `[📱 메뉴: N개]` 배지 및 퀵 바 `[📱 텔레그램 메뉴]` 버튼을 통해 `#telegram-menu-modal`을 원클릭으로 호출할 수 있어야 한다.
- **FR-40.4**: 모달 내에서 온/오프 체크박스 토글, 명령어/설명 인라인 편집, 새 명령어 추가 및 스마트폰 다크 테마 팝업 실시간 미리보기를 제공해야 한다.

### FR-41: GTD 마감일(Due Date / D-Day) 자동 감지 및 긴급도 브리핑 (ADR-042)
- **FR-41.1**: 마크다운 태스크 내 `~YYYY-MM-DD`, `~YYYY.MM.DD`, `@due(YYYY-MM-DD)` 태그 및 한국어 자연어 상대일자("오늘까지", "내일까지", "모레까지", "이번 주 금요일까지", "다음 주 화요일까지")를 KST 기준 D-Day로 자동 파싱해야 한다.
- **FR-41.2**: 태스크의 긴급도를 `overdue`(기한 초과), `today`(오늘 마감), `urgent`(D-1~D-3), `upcoming`(D-4 이상) 4단계로 분류하고 가중치 우선순위를 부여해야 한다.
- **FR-41.3**: 아침 08:30 브리핑 상단에 D-Day 경고 섹션을 주입하고 최우선 집중 과제를 마감 임박 태스크로 우선 정렬해야 한다.
- **FR-41.4**: 저녁 20:00 브리핑 시 미완료된 당일/초과 과제를 내일 최우선 이월 과제로 강조하고, GTD 파일 읽기 시 마감일 현황 섹션을 제공해야 한다.
- **FR-41.5**: `/dday`, `/deadline`, "마감일 확인" 명령어 수신 시 단독 마감 리포트를 즉시 출력하고, 텔레그램 인라인 키보드 `[⏳ D-Day 마감 확인]` 및 웹 콘솔 퀵 바 칩을 제공해야 한다.
- **FR-41.6**: 사용자가 대화 중 "내일까지 보고서 제출 GTD에 추가해줘" 요청 시 `~YYYY-MM-DD` 태그가 부착된 마크다운 할 일로 자동 정제해야 한다.

### FR-42: 과거 라이프로그·GTD 고속 검색 및 주간 결산 회고 리포트 (ADR-043)
- **FR-42.1**: `SearchService`를 통해 `logs/daily/*.md`, `gtd/*.md` 및 마크다운 파일 전체를 대상으로 공백 구분 다중 키워드 AND 검색 및 본문 볼드 하이라이트 스니펫을 0.5초 이내 반환해야 한다.
- **FR-42.2**: `/search [키워드]`, `/find [키워드]`, 자연어 질의("지난달 서산 맛집 찾아줘") 수신 시 `search_query` 인텐트로 라우팅하여 일치 카드 리포트를 즉시 출력해야 한다.
- **FR-42.3**: `WeeklyReviewService`를 통해 기준일(KST 오늘)로부터 지난 7일간의 기록 달성률(%), 완료 태스크 수(`- [x]`), 카테고리별 활동(운동/업무/생각)을 정량 집계해야 한다.
- **FR-42.4**: `gtd/inbox.md`의 미분류 태스크를 점검하여 수집함 정리 가이드 및 다음 행동 배치를 권유해야 한다.
- **FR-42.5**: 매주 일요일 21:00 KST에 허용된 텔레그램 사용자에게 주간 결산 리포트 및 인라인 액션 키보드를 능동 푸시 발송해야 한다.
- **FR-42.6**: `GET /api/search`, `GET /api/weekly`, `POST /api/weekly/trigger-push` REST API 엔드포인트를 제공하고 텔레그램 봇 메뉴 17종 및 웹 퀵 바 칩(`[🔍 기록 검색]`, `[📊 주간 결산]`)을 제공해야 한다.

### FR-43: 사진·영수증·운동인증 Vision AI 멀티모달 분석 & 스마트 기록 (ADR-044)
- **FR-43.1**: `VisionService`를 통해 사진 수신 시 Gemini 1.5 Flash Vision REST API 또는 휴리스틱 폴백 엔진으로 5대 도메인(운동, 식사, 영수증, 메모, 일상)을 자동 분류하고 메트릭을 추출해야 한다.
- **FR-43.2**: 운동 인증샷 수신 시 종목/시간/거리/칼로리/심박수를 추출하여 `## 🏃 운동 & 건강 (Workout & Health)` 섹션에 표/불릿으로 포맷팅해야 한다.
- **FR-43.3**: 영수증 및 지출 사진 수신 시 상호명/일시/금액을 추출하고 카드번호 등 민감정보를 자동 마스킹하며, GTD 수집함 가계부 정리 태스크를 자동 생성해야 한다.
- **FR-43.4**: 텔레그램 사진 수신 시 즉시 커밋하지 않고 2단계 사전 검토 초안 카드와 인라인 키보드(`[✅ 응, 기록해줘]`, `[❌ 아니야]`)를 제시해야 한다.
- **FR-43.5**: 캡션에 `/log` 또는 `!` 포함 시 사전 검토를 생략하고 즉시 라이프로그에 반영 후 Git 커밋·푸시하는 패스트트랙을 지원해야 한다.
### FR-44: 웹 대시보드 연간 잔디(Heatmap) & 마크다운 인플레이스 에디터 (ADR-045)
- **FR-44.1**: `HeatmapService`를 통해 `logs/daily/*.md` 및 마크다운 일일 로그 전수를 스캔하여 날짜별 글자수 및 완료 태스크 기반 GitHub 표준 5단계(0~4) 기여도 레벨을 계산해야 한다.
- **FR-44.2**: 현재 연속 기록 스트릭(`current_streak`), 역대 최장 스트릭(`longest_streak`), 총 기록 일수, 연간 달성률(%)을 정확히 산출해야 한다.
- **FR-44.3**: 웹 대시보드 상단에 연간 잔디 뱃지(`#heatmap-badge`), 퀵 바 칩(`[✏️ 잔디 & 로그 편집]`), 52주 잔디 그리드 및 호버 툴팁을 시각화해야 한다.
- **FR-44.4**: 웹 대시보드 내 좌우 분할 에디터(Textarea + 실시간 마크다운 프리뷰)를 통해 일일 로그를 인플레이스 편집하고 커밋 메시지 입력 및 원터치 Git 커밋·푸시를 집행해야 한다.
- **FR-44.5**: `/?edit=YYYY-MM-DD` 딥링크 접속 시 해당 일자의 에디터 모달을 즉시 오픈해야 하며, `/edit [날짜]`, `/heatmap` 인텐트 및 안내 카드를 제공해야 한다.
### FR-45: 1-Click 셀프호스팅 배포 패키지 & 대화형 셋업 위저드 (ADR-046)
- **FR-45.1**: `./scripts/setup_wizard.sh`를 통해 시스템 도구 확인, 7단계 대화형 설정 질문(포트, 타임존, 봇 토큰, Chat ID, Gemini 키, GTD 경로, 동네명, 웹 보안) 및 `.env`/`config/` 자동 생성을 지원해야 한다.
- **FR-45.2**: `-y`/`--non-interactive`(무인 설치), `-d`/`--dry-run`(모의 테스트), `-c`/`--check`(설정 점검) 옵션을 지원해야 한다.
- **FR-45.3**: `SetupService`를 통해 텔레그램, LLM, GTD, 웹 보안 등 8개 핵심 영역의 설정 무결성을 진단하고 `GET /api/system/setup-status` REST API를 제공해야 한다.
- **FR-45.4**: DevBot 콘솔에서 `/setup` 명령어를 통해 시스템 배포 준비 상태 리포트를 즉시 출력해야 한다.
- **FR-45.5**: `Dockerfile` (Python 3.12-slim, safe.directory, 헬스체크) 및 `docker-compose.yml` 볼륨 마운트 패키징을 제공해야 한다.
- **FR-45.6**: 초보자용 10분 완성 1-Click 셀프호스팅 가이드(`docs/quickstart_guide.md`)를 완비해야 한다.

### FR-46: 웹 콘솔 한국 표준시(KST) 동기화 및 실시간 시계 배지 연동 (ADR-047)
- **FR-46.1**: `SessionModel` 및 `ChatMessageModel`의 `created_at`/`updated_at` 기본값 및 세션 갱신을 `get_now()`(KST)로 통일하고, `_format_datetime_iso()`를 통해 `+09:00` 타임존 오프셋을 포함해야 한다.
- **FR-46.2**: 웹 프론트엔드 `formatRelativeTime(dateStr)`에서 타임존 표기가 누락된 문자열을 KST로 안전 보정하여 "9시간 전" 오표기를 해소하고 "방금" 등 실시간 상대 시각을 정확히 계산해야 한다.
- **FR-46.3**: 웹 콘솔(Watson `/watson` 및 DevBot `/dev`) 상단 헤더에 `#header-clock-badge`를 탑재하여 초 단위 실시간 KST 디지털 시계를 출력해야 한다.
- **FR-46.4**: 일일 로그 에디터 모달(`openEditorModal`)에서 `getKSTDateString()`을 사용하여 자정~오전 9시 접속 시에도 KST 당일 날짜 파일을 안정적으로 열어야 한다.
- **FR-46.5**: `app/main.py` 수명 주기 시작 시 `os.environ["TZ"] = settings.TIMEZONE` 및 `time.tzset()`을 호출하여 프로세스, C 라이브러리, Git 서브프로세스를 KST로 고정해야 한다.
- **FR-46.6**: `BriefingScheduler` 루프에서 `commute_config`의 `send_time`(KST) 일치를 모니터링하여 활성화된 출근길 브리핑을 능동 푸시 발송해야 한다.

### FR-47: 단위 테스트 초고속화 & 템플릿 컴포넌트 모듈화 리팩터링 (ADR-048)
- **FR-47.1**: `tests/conftest.py`에 `fast_unit_test_environment` autouse 픽스처를 구축하여 단위 테스트 중 AGY 외부 CLI 프로세스 실행, 중첩 Mypy/Pytest 툴체인 및 외부 기상 API 호출을 격리/모킹하고, 단위 테스트 실행 시간을 14분대에서 2분대 이하(84% 단축)로 가속화해야 한다.
- **FR-47.2**: 574라인에 달하던 `app/templates/index.html` 내 인라인 모달 마크업을 `app/templates/modals/` 8개 전용 컴포넌트 템플릿으로 분리 모듈화하고 Jinja2 `{% include %}` 구문으로 경량화(183라인, 68% 단축)해야 한다.
- **FR-47.3**: 모듈화된 8개 팝업 모달(세션 변경/삭제/비우기, GTD 설정, 스케줄, 출근길, 텔레그램 메뉴, 잔디 에디터)의 DOM ID 및 인터랙티브 JavaScript 이벤트 바인딩 호환성을 100% 유지해야 한다.

### FR-48: 프론트엔드 스타일시트(CSS) 컴포넌트 모듈화 리팩터링 (ADR-049)
- **FR-48.1**: 3,423라인 단일 모놀리식 `style.css`를 7대 도메인별 모듈(`variables.css`, `layout.css`, `chat.css`, `modals.css`, `portal.css`, `dev.css`, `responsive.css`)로 분할하여 개별 모듈의 책임을 격리해야 한다.
- **FR-48.2**: 메인 `app/static/css/style.css`를 13라인의 `@import url(...)` 마스터 오케스트레이터 번들로 전환하여 기존 HTML 템플릿의 `<link>` 태그 호환성을 100% 보장해야 한다.
- **FR-48.3**: 분할된 모든 7개 CSS 모듈의 HTTP 200 서빙과 모바일/데스크톱 반응형 렌더링 무결성을 유지해야 한다.

### FR-49: 프론트엔드 자바스크립트(JS) 모듈화 및 모달 컨트롤러 분리 (ADR-050)
- **FR-49.1**: 1,984라인 단일 모놀리식 `main.js`를 공통 유틸리티(`utils/api.js`, `utils/date.js`, `utils/modal.js`) 및 5개 전용 모달 컨트롤러(`modules/gtd_modal.js`, `modules/schedule_modal.js`, `modules/commute_modal.js`, `modules/telegram_modal.js`, `modules/editor_modal.js`)로 분할 모듈화해야 한다.
- **FR-49.2**: 메인 `main.js`를 662라인으로 경량화하여 세션 목록/검색/필터/CRUD 관리 및 실시간 채팅 엔진 코어에만 집중하도록 단일 책임 원칙을 적용해야 한다.
- **FR-49.3**: `dev.js` 내 중복 구현된 API 재시도 및 실시간 시계 로직을 공통 `WatsonAPI`, `WatsonDate` 유틸리티로 대체하여 코드 중복을 제거해야 한다.
- **FR-49.4**: 브라우저 네이티브(`window.Watson*`) 네임스페이스 및 `index.html`/`dev.html` 스크립트 종속 순서 배치를 통해 별도 번들러 빌드 없이 100% 하위 호환 구동을 보장해야 한다.

### FR-50: 백엔드 라우터 계층 모듈화 리팩터링 (ADR-051)
- **FR-50.1**: 515라인 단일 모놀리식 `web_router.py`를 4개 도메인 서브 라우터(`chat_router.py`, `session_router.py`, `briefing_router.py`, `lifelog_router.py`)로 분할 모듈화해야 한다.
- **FR-50.2**: 메인 `web_router.py`를 95라인으로 슬림화하여 HTML 뷰 렌더링(`/`, `/watson`, `/dev`) 및 허브/데브 워크스페이스 상태 요약 전담 컨트롤러로 개편해야 한다.
- **FR-50.3**: `web_router.py`에서 4대 서브 라우터를 `include_router`로 통합 마운트하여 기존 모든 클라이언트 통신 및 단위/스모크 테스트와 100% 하위 호환성을 유지해야 한다.

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
| **FR-13** | `app/services/llm_provider.py`, `app/services/agent_service.py`, `app/services/supervisor_service.py` | Pytest 듀얼 로깅/태스크 정제 단위 테스트 & cURL 검증 |
| **FR-14** | `app/auth.py`, `app/config.py`, `systemd/watson-tunnel.service` | Pytest 인증 단위 테스트(`tests/test_auth.py`) & cURL Auth Guard 검증 |
| **FR-15** | `app/templates/index.html`, `app/static/css/style.css`, `app/static/js/main.js` | 모바일 뷰포트 반응형 검증 및 cURL 스모크 테스트 |
| **FR-16** | `app/services/session_service.py`, `app/routers/web_router.py`, `app/templates/index.html`, `app/static/js/main.js` | Pytest 세션 라이프사이클 테스트 & cURL API 검증 |
| **FR-17** | `app/services/dev_agent_service.py`, `app/routers/web_router.py`, `app/templates/portal.html`, `app/templates/dev.html` | Pytest 허브/데브 라우터 테스트(`tests/test_dev_agent.py`) & cURL 검증 |
| **FR-18** | `app/services/dev_agent_service.py`, `app/templates/dev.html` | Pytest 툴체인 단위 테스트(`tests/test_dev_agent.py`) & cURL 라이브 검증 |
| **FR-19** | `app/services/agent_service.py`, `app/services/git_service.py`, `app/services/llm_provider.py`, `app/services/supervisor_service.py` | Pytest 단위 테스트(`test_agent_service.py`, `test_supervisor_service.py`) & cURL 검증 |
| **FR-20** | `scripts/run_tunnel.sh`, `systemd/watson.service`, `app/main.py`, `app/static/js/main.js`, `dev.js` | Pytest 단위 테스트(`test_web_router.py`) & cURL 스모크 검증(0-1) |
| **FR-21** | `app/services/agent_service.py`, `app/services/llm_provider.py`, `app/services/dev_agent_service.py`, `app/templates/index.html`, `dev.html` | Pytest 단위 테스트(`test_agent_service.py`, `test_supervisor_service.py`, `test_dev_agent.py`) & cURL 검증 |
| **FR-22** | `app/templates/index.html`, `app/templates/dev.html`, `app/static/css/style.css` | 모바일 뷰포트 레이아웃 반응형 검증 & cURL 스모크 검증 |
| **FR-23** | `app/services/briefing_service.py`, `app/routers/web_router.py`, `app/templates/index.html` | Pytest 단위 테스트(`test_briefing_service.py`, `test_web_router.py`) & cURL 스모크 검증(3-13) |
| **FR-24** | `app/services/briefing_service.py`, `app/routers/web_router.py`, `app/static/js/main.js`, `app/templates/index.html` | Pytest 단위 테스트(`test_briefing_service.py`, `test_web_router.py`) & cURL 스모크 검증(3-13-5, 3-13-6) |
| **FR-25** | `app/services/briefing_scheduler.py`, `app/services/telegram_service.py`, `app/routers/web_router.py`, `app/main.py` | Pytest 단위 테스트(`test_briefing_scheduler.py`, `test_web_router.py`) & cURL 스모크 검증(3-14) |
| **FR-26** | `app/services/telegram_service.py`, `app/services/agent_service.py`, `app/services/briefing_scheduler.py`, `app/services/supervisor_service.py` | Pytest 단위 테스트(`test_telegram_service.py`, `test_agent_service.py`, `test_briefing_scheduler.py`) & cURL 검증(3-8-1) |
| **FR-27** | `app/services/llm_provider.py`, `app/services/supervisor_service.py`, `app/services/agent_service.py` | Pytest 단위 테스트(`test_llm_provider.py`, `test_supervisor_service.py`) & cURL 스모크 검증(3-8-2) |
| **FR-28** | `app/services/llm_provider.py`, `app/services/supervisor_service.py`, `app/services/session_service.py`, `app/services/telegram_service.py`, `app/static/js/main.js` | Pytest 단위 테스트(`test_llm_provider.py`, `test_supervisor_service.py`) & cURL 스모크 검증(3-8-3) |
| **FR-29** | `app/services/commute_config_service.py`, `app/routers/settings_router.py`, `app/templates/index.html`, `app/static/js/main.js` | Pytest 단위 테스트(`test_commute_config_service.py`) & cURL 스모크 검증(6) |
| **FR-30** | `app/services/llm_provider.py`, `app/services/agent_service.py`, `app/services/supervisor_service.py` | Pytest 단위 테스트(`test_task_completion_and_meta_guard.py`) & cURL 스모크 검증(7) |
| **FR-31** | `app/services/agent_service.py`, `app/services/llm_provider.py`, `app/services/supervisor_service.py` | Pytest 단위 테스트(`test_agent_service.py`, `test_task_completion_and_meta_guard.py`) & cURL 검증 |
| **FR-32** | `app/services/briefing_service.py`, `app/services/commute_config_service.py`, `app/services/llm_provider.py` | Pytest 단위 테스트(`test_briefing_service.py`, `test_commute_config_service.py`) & cURL 검증 |
| **FR-33** | `app/services/geo_service.py`, `app/services/commute_config_service.py`, `app/services/llm_provider.py`, `app/services/supervisor_service.py`, `app/routers/settings_router.py` | Pytest 단위 테스트(`test_geo_service.py`) & cURL 스모크 검증(6-5, 6-6) |
| **FR-34** | `app/services/weather_service.py`, `app/services/commute_config_service.py`, `app/services/geo_service.py` | Pytest 단위 테스트(`test_weather_service.py`, `test_commute_config_service.py`) & cURL 스모크 검증 |
| **FR-35** | `app/services/llm_provider.py`, `tests/test_llm_provider.py` | Pytest 단위 테스트(`test_llm_provider.py`) & cURL 라이브 검증 |
| **FR-36** | `app/services/bus_service.py`, `app/services/commute_config_service.py`, `tests/test_bus_service.py` | Pytest 단위 테스트(`test_bus_service.py`) & cURL 스모크 검증(6-7) |
| **FR-37** | `app/services/bus_service.py`, `app/routers/settings_router.py`, `app/templates/index.html`, `app/static/js/main.js`, `scripts/smoke_test.sh` | Pytest 단위 테스트(`test_bus_service.py`) & cURL 스모크 검증(6-8) |
| **FR-38** | `app/services/bus_service.py`, `app/services/telegram_service.py`, `app/routers/settings_router.py`, `app/static/js/main.js` | Pytest 단위 테스트(`test_bus_service.py`, `test_telegram_service.py`) & cURL 스모크 검증(6-9) |
| **FR-39** | `app/services/telegram_service.py`, `app/routers/telegram_router.py`, `tests/test_telegram_service.py`, `scripts/smoke_test.sh` | Pytest 단위 테스트(`test_telegram_service.py`) & cURL 스모크 검증(4-1, 4-2) |
| **FR-40** | `app/services/telegram_service.py`, `app/routers/telegram_router.py`, `app/templates/index.html`, `app/static/js/main.js`, `app/static/css/style.css` | Pytest 단위 테스트(`test_telegram_service.py`) & cURL 스모크 검증(4-3, 4-4) |
| **FR-41** | `app/services/due_date_service.py`, `app/services/briefing_service.py`, `app/services/agent_service.py`, `app/services/llm_provider.py`, `app/services/supervisor_service.py`, `app/services/telegram_service.py` | Pytest 단위 테스트(`test_due_date_service.py`) & cURL 스모크 검증(3-13-7, 3-13-8) |
| **FR-42** | `app/services/search_service.py`, `app/services/weekly_review_service.py`, `app/services/briefing_scheduler.py`, `app/routers/web_router.py`, `app/services/dev_agent_service.py`, `app/services/supervisor_service.py` | Pytest 단위 테스트(`test_search_and_weekly_service.py`) & cURL 스모크 검증(3-13-9 ~ 3-13-15) |
| **FR-43** | `app/services/vision_service.py`, `app/routers/web_router.py`, `app/services/telegram_service.py`, `app/services/dev_agent_service.py` | Pytest 단위 테스트(`test_vision_service.py`) & cURL 스모크 검증(3-13-16 ~ 3-13-19) |
| **FR-44** | `app/services/heatmap_service.py`, `app/routers/web_router.py`, `app/templates/index.html`, `app/static/js/main.js`, `app/static/css/style.css` | Pytest 단위 테스트(`test_heatmap_service.py`) & cURL 스모크 검증(3-13-20 ~ 3-13-26) |
| **FR-45** | `scripts/setup_wizard.sh`, `app/services/setup_service.py`, `app/routers/web_router.py`, `Dockerfile`, `docker-compose.yml` | Pytest 단위 테스트(`test_setup_service.py`) & cURL 스모크 검증(3-13-27 ~ 3-13-29) |
| **FR-46** | `app/models/session.py`, `app/services/session_service.py`, `app/main.py`, `app/services/briefing_scheduler.py`, `app/templates/index.html`, `app/templates/dev.html`, `app/static/js/main.js`, `app/static/js/dev.js` | Pytest 단위 테스트(`test_session_service.py`, `test_briefing_scheduler.py`) & cURL 스모크 검증(0-1, 2) |
| **FR-47** | `tests/conftest.py`, `app/templates/modals/*.html`, `app/templates/index.html` | Pytest 단위 테스트 & cURL 스모크 검증(0-1, 0-2) |
| **FR-48** | `app/static/css/*.css`, `app/static/css/style.css` | cURL 정적 파일 검증 및 스모크 테스트 |
| **FR-49** | `app/static/js/utils/*.js`, `app/static/js/modules/*.js`, `app/static/js/main.js`, `app/static/js/dev.js` | cURL 정적 파일 검증 및 스모크 테스트 |
| **FR-50** | `app/routers/chat_router.py`, `app/routers/session_router.py`, `app/routers/briefing_router.py`, `app/routers/lifelog_router.py`, `app/routers/web_router.py` | Pytest 단위 테스트(`test_web_router.py`) & cURL 스모크 테스트 |

