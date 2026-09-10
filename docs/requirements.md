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




