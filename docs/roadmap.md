# 🗺️ Watson 개발 로드맵 & 마일스톤 백로그 (Roadmap)

## 📌 전체 개발 단계 (Phases Overview)

```text
Phase 1: 기획 및 아키텍처 수립 (PRD, Spec, ADR) -> ✅ 진행 완료
  ↓
Phase 2: 백엔드 코어 & Git 자동화 모듈 구현 (GitWorker, AgentEngine)
  ↓
Phase 3: 텔레그램 봇 연동 & 24/7 백그라운드 봇 서비스 구현
  ↓
Phase 4: 웹 대시보드 UI (Watson Web Interface) & 마크다운 렌더러/에디터 구축
  ↓
Phase 5: 통합 QA, 24시간 서버 배포 및 자동 재시작(systemd/Docker) 구축 -> ✅ 완료
  ↓
Phase 6: GTD 저장소 격리 & 동적 디렉토리 오케스트레이션 (ADR-007) - 🚀 진행 중
```

---

## 🎯 상세 백로그 (Detailed Backlog)

### Phase 1: 기반 기획 및 아키텍처 (Current Phase - Done)
- [x] AGENTS.md 에이전트 하네스 구축
- [x] 제품 기획서 (`docs/PRD.md`) 작성
- [x] 기능 요구사항 명세서 (`docs/requirements.md`) 작성
- [x] 기술 아키텍처 ADR (`docs/adr/ADR-001-architecture-design.md`) 작성
- [x] 로드맵 문서 (`docs/roadmap.md`) 작성

### Phase 2: 코어 파이썬 백엔드 & Git 서비스 (Done)
- [x] 파이썬 프로젝트 구조 (`app/`, `config.py`, `requirements.txt`) 세팅
- [x] 세션 및 대화 컨텍스트 영속성 모듈 (`app/services/session_service.py` & SQLite DB) 구현
- [x] Git 자동화 모듈 (`app/services/git_service.py`) 작성: pull, commit, push, conflict handling
- [x] AI 마크다운 파서 및 템플릿 생성기 (`app/services/agent_service.py`) 구현
- [x] 기본 Pytest 단위 테스트 모듈 작성 및 통과 검증

### Phase 3: 텔레그램 봇 연동 모듈 (Telegram Bot Integration - ADR-006) - ✅ 완료
- [x] Telegram Bot API 수신 및 사용자 화이트리스트 검증 모듈 (`app/services/telegram_service.py`)
- [x] 텍스트 대화 ➔ 지능형 비서 연동 (잡담 분리 및 인라인 키보드 제안/승인)
- [x] 사진/미디어 수신 ➔ 마크다운 자동 링크 삽입 및 Git Commit 연동
- [x] 텔레그램 명령어 (`/start`, `/log`, `/status`, `/help`) 파싱 구현
- [x] FastAPI 백그라운드 태스크 및 Webhook/Polling 동시 지원 라우터 (`app/routers/telegram_router.py`)

### Phase 4: 웹 대시보드 및 지능형 비서 엔진 (Watson Butler) - ✅ 완료
- [x] FastAPI 기반 라우터 및 HTML Jinja2/Vanilla CSS 템플릿 구성
- [x] 라이프 로그 캘린더 뷰 및 대화 세션 조회 페이지 구현
- [x] 웹 대시보드 내 대화형 AI Agent 콘솔 인터페이스 개발 (`POST /api/chat`)
- [x] 모바일/대형 화면 반응형 Glassmorphism UI 구현
- [x] AGY AI 에이전트 브릿지 및 지능형 챗봇 엔진 결합 (`ADR-003`)
- [x] 지능형 비서 의도 분석 및 대화-기록 분리 (ADR-004): 단순 대화 보존 vs 라이프로그 능동 제안
- [x] 세션 상태 머신 기반 `pending_log` 후보 관리 및 승인 시 1기록 1커밋 자동 파이프라인
- [x] cURL 실서버 라이브 스모크 테스트 스크립트 (`scripts/smoke_test.sh`) 구축

### Phase 5: 서버 배포 및 24/7 상시가동 안정화 (ADR-005) - ✅ 완료
- [x] `.env.example` 및 환경변수 설정 템플릿 작성
- [x] 경량 멀티아키텍처 `Dockerfile` 및 `docker-compose.yml` 패키징
- [x] SQLite DB 및 마크다운 라이프로그 볼륨 영속화 구성
- [x] systemd 서비스 유닛 파일 (`systemd/watson.service`) 제공
- [x] 원격 서버 배포 및 실행 가이드 문서 작성 (`docs/deployment_guide.md`)

### Phase 6: GTD 저장소 격리 & 동적 디렉토리 오케스트레이션 (ADR-007) - ✅ 완료
- [x] GTD 작업 디렉토리 동적 설정 관리자 (`app/services/settings_service.py`) 구현
- [x] REST API 엔드포인트 (`GET/POST /api/settings/gtd-path`) 구현
- [x] 대상 저장소 내 기정의된 GTD 체계(`gtd/inbox.md`, `logs/daily/` 등) 자동 감지 및 오케스트레이션 연동
- [x] GTD 전용 레포지토리 독립 Git 커밋/푸시 격리 파이프라인 연동
- [x] 웹 대시보드 UI 상단 GTD 경로 조회 및 동적 변경 모달 인터페이스 구현
- [x] 단위 테스트 및 cURL 스모크 테스트 업데이트

### Phase 7: GTD 지능형 브리핑 및 Linux AGY 엔진 브릿지 (ADR-008) - ✅ 완료
- [x] GTD 할 일/일정 브리핑 파이프라인 (`task_briefing`) 구현
- [x] Linux 환경 AGY CLI 동적 경로 탐색 및 systemd 환경변수 반영
- [x] 데일리 로그, Next Actions, Inbox 미처리 태스크 종합 요약 포맷팅
- [x] 단위 테스트 및 라이브 API 검증

### Phase 8: GTD 저장소 원격 동기화 및 자동 Pull 파이프라인 (ADR-009) - ✅ 완료
- [x] `GitService.pull(autostash=True)` 안전 원격 동기화 메서드 구현
- [x] `LLMProvider`에 `repo_sync` 인텐트 및 복합 브리핑(`sync_and_brief`) 분류기 추가
- [x] `task_briefing` 실행 시 자동 사전 Git Pull 파이프라인 연동
- [x] 단위 테스트 및 cURL 스모크 테스트 검증

### Phase 9: 세션 대화 맥락 참조 기록 & AGY 프롬프트 경량화 (ADR-010) - ✅ 완료
- [x] 대화 맥락 참조 기록("아까 말한 내용 기록해줘") 히스토리 역추적 파이프라인 구현
- [x] 멀티라인 및 복합 기록 지시어 유연 파싱 로직 구현
- [x] AGY CLI 호출 시 히스토리 토큰 경량화 슬라이싱 및 타임아웃 50초 확장
- [x] 단위 테스트 및 라이브 API 스모크 검증

### Phase 10: 결정론적 Git 원격 푸시 & AGY Headless 무중단 실행 (ADR-011) - ✅ 완료
- [x] `GitService.push()` 독립 구현 및 `sync_and_commit_push` 내 `autostash` 안전 격리
- [x] `LLMProvider`에 `repo_push` 인텐트 신설 ("푸시해줘", "/push" 등) 및 LLM 환각 차단
- [x] `AGY CLI` headless 모드 `--dangerously-skip-permissions` 플래그 및 프롬프트 가드레일 반영
- [x] 텔레그램 `/push` 명령어 및 도움말 지원
- [x] 단위 테스트 및 cURL 스모크 검증

### Phase 11: 테스트 샌드박스 격리 & 대화형 지시어 문맥 역추적 (ADR-012) - ✅ 완료
- [x] `scripts/smoke_test.sh` 임시 GTD 샌드박스 격리 및 원본 경로 자동 복원 트랩 구현
- [x] "응 오늘 로그에 기록해줘" 등 순수 지시어 판별 및 세션 히스토리 사연 역추적 파이프라인 구현
- [x] 단일 문장 직접 기록 정규식 내 지시어 접두어 오인 필터링 방어막 구축
- [x] 단위 테스트 및 샌드박스 cURL 스모크 테스트 검증

### Phase 12: 한국 표준시(KST) 타임존 로컬라이제이션 (ADR-013) - ✅ 완료
- [x] `Settings`에 `TIMEZONE: str = "Asia/Seoul"` 추가 및 `get_app_timezone`, `get_now` 유틸리티 구현
- [x] `AgentService._normalize_datetime`을 통한 일일 로그 경로 및 타임스탬프(`[HH:MM]`) KST 정규화
- [x] 자정 넘은 새벽 시간대(00:00~09:00 KST) 기록 시 익일 정상 반영 및 자정 경계 결함 해결
- [x] 슈퍼바이저 커밋 일자, 텔레그램 동기화 시간 및 상태 API KST 반영
- [x] 단위 테스트(`test_timezone_conversion_utc_to_kst`, `test_timezone_date_rollover_utc_to_kst`) 및 라이브 cURL 스모크 테스트 검증

### Phase 13: 복합 의도 감지 & GTD 태스크 정제 (ADR-014) - ✅ 완료
- [x] "로그와 gtd에 기록해줘" 등 복합 의도(`log_dual`) 정규식 및 인텐트 판별 구현
- [x] 발화 말미 지시어("로그와 gtd에 기록해줘") 및 불필요한 문장부호 완벽 절삭
- [x] 여행/맛집/업무 등 비정형 일기로부터 핵심 행동을 추출하는 경량 휴리스틱 태스크 정제기(`_extract_actionable_task`) 구현
- [x] `inbox.md` 내부 도메인 섹션(`## 🧘 개인 생활 & 건강` 등) 지능형 탐색 및 태스크 배치
- [x] 데일리 로그 + GTD 인박스 단일 트랜잭션 동시 반영 및 원자적 Git 커밋/동기화
- [x] 단위 테스트, 3-8 cURL 라이브 스모크 테스트 및 실사용 데이터 소급 정정 완료

### Phase 14: 웹 콘솔 보안 인증 & Cloudflare Tunnel 외부 연동 (ADR-015) - ✅ 완료
- [x] FastAPI `HTTPBasic` 기반 웹 콘솔/API 보안 인증 가드(`app/auth.py`) 구현
- [x] `.env` 내 `WEB_AUTH_ENABLED`, `WEB_AUTH_USERNAME`, `WEB_AUTH_PASSWORD` 구성
- [x] `cloudflared` 설치 및 무개방 HTTPS 터널 러너(`scripts/run_tunnel.sh`) 구현
- [x] `systemd/watson-tunnel.service` 데몬 등록 및 24/7 상시 터널링 가동
- [x] `tests/test_auth.py` 단위 테스트 및 `./scripts/smoke_test.sh` Auth Guard 실시간 검증 완료

### Phase 15: 모바일 퍼스트 반응형 웹 인터페이스 & 터치 UX 최적화 (ADR-016) - ✅ 완료
- [x] 모바일 화면(<= 768px)용 오프캔버스 슬라이드 드로어 및 햄버거 메뉴/백드롭 구현
- [x] 세션 전환 및 새 세션 생성 시 모바일 드로어 자동 닫힘 인터랙션 적용
- [x] `100dvh` 동적 뷰포트, iOS Safe Area 및 16px 폰트 적용으로 모바일 Safari 자동 확대 방지
- [x] 헤더 축약 타이틀, GTD 배지 말줄임, 모바일 최적화 빠른 액션 버튼 및 텍스트에어리어 반응형 스타일링
- [x] `tests/conftest.py` 테스트 환경 격리 fixture 추가 및 `./scripts/smoke_test.sh` 라이브 검증 완료

### Phase 16: 웹 콘솔 세션 관리 고도화 (ADR-017) - ✅ 완료
- [x] `SessionService` 내 세션 이름 변경(`update_session_title`), 삭제(`delete_session`), 대화 비우기(`clear_session_messages`) 및 메타데이터 강화(`list_sessions`)
- [x] 첫 프롬프트 전송 시 의미 있는 대화명 자동 생성(`auto_update_session_title`)
- [x] `WebRouter` 내 `PATCH /api/sessions/{session_id}`, `DELETE /api/sessions/{session_id}`, `POST /api/sessions/{session_id}/clear` REST API 엔드포인트 구현
- [x] 사이드바 실시간 검색 입력창 및 채널별(`전체`, `🌐 웹`, `📱 텔레그램`) 필터 탭 UI 구현
- [x] 카드 호버/터치 액션 버튼(이름 변경, 대화 비우기, 세션 삭제) 및 모달 UI 구현
- [x] 활성 세션 삭제 시 인접 세션 또는 기본 세션 자동 폴백 UX 적용
- [x] 헤더 영역 활성 세션 제목, 채널 배지, 메시지 개수 실시간 연동 및 대화 비우기 바로가기 버튼 추가
- [x] 단위 테스트(`tests/test_session_service.py`, `tests/test_web_router.py`), 린트/타입 검사 및 `./scripts/smoke_test.sh` 라이브 cURL 검증 완료

### Phase 17: 에이전트 허브 대시보드 포털 & 개발 에이전트 분리 (ADR-018) - ✅ 완료
- [x] 상위 에이전트 허브 대시보드 포털(`app/templates/portal.html`) 및 `GET /` 루트 엔드포인트 구현
- [x] Watson 비서 콘솔(`GET /watson`) 및 DevBot 개발 콘솔(`GET /dev`, `app/templates/dev.html`) 독립 라우팅 분리
- [x] 개발 전담 에이전트 서비스(`DevAgentService`) 구현: Git 단축 명령(`/status`, `/diff`, `/log`, `/branch`) 및 엔지니어링 AI 추론
- [x] `SessionModel`에 `agent_type` 컬럼 추가 및 SQLite 자동 마이그레이션 (`database.init_db`)
- [x] `GET /api/hub/status`, `POST /api/dev/chat`, `GET /api/dev/sessions`, `GET /api/dev/status` REST 엔드포인트 구축
- [x] 포털 및 개발자 콘솔 전용 반응형 스타일링(`style.css`), `portal.js`, `dev.js` 클라이언트 구현
- [x] 각 에이전트 콘솔 상단 헤더에 `[🏠 에이전트 허브]` 복귀 내비게이션 버튼 배치
- [x] 대시보드 포털 모바일/데스크톱 세로 스크롤 버그 수정 및 카드 원클릭 터치 내비게이션 UX 고도화
- [x] 단위 테스트(`tests/test_dev_agent.py`), Mypy/Ruff 검증 및 `./scripts/smoke_test.sh` 라이브 검증 완료

### Phase 18: DevBot 대화형 엔지니어링 툴체인 및 실시간 개발 실행 환경 (ADR-019) - ✅ 완료
- [x] DevBot 전용 엔지니어링 툴체인 메서드(`_run_pytest`, `_run_lint`, `_run_git_commit`, `_recommend_commit_messages`, `_get_roadmap_summary`) 구현
- [x] AGY CLI 호출 정규화(`-p`, `--dangerously-skip-permissions`, 50s 타임아웃, PATH 자동 보정) 및 고탄력 추론 안정화
- [x] 대화형 툴체인 단축 명령 지원:
  - `/test [경로]`: pytest 단위 테스트 실행 및 결과 요약 브리핑
  - `/lint`: ruff 및 mypy 린트/타입 검사 병렬 실행 및 뱃지 상태 반환
  - `/commit [메시지]`: Conventional Commits 메시지 자동 추천 3종 또는 안전한 git commit 집행
  - `/help`: 개발자 툴체인 명령어 도움말 제공
- [x] 디렉토리 트래버설(`..`) 및 쉘 메타문자 차단을 통한 안전한 하위 프로세스 실행 보장
- [x] 웹 콘솔(`/dev`) 입력창 상단 퀵 툴 칩(`/test`, `/lint`, `/commit`, `/help`) UI 추가
- [x] `tests/test_dev_agent.py` 단위 테스트, Mypy/Ruff 검증 및 `./scripts/smoke_test.sh` 3-10 라이브 cURL 검증 완료

### Phase 19: 결정론적 GTD 태스크 삭제, 구어체 원격 푸시/커밋 라우팅 및 저장소 투명성 (ADR-020) - ✅ 완료
- [x] GTD 태스크 실제 삭제/완료 메서드(`remove_gtd_tasks`, `find_and_remove_matching_tasks`) 구현 및 `gtd_remove` 인텐트 연동
- [x] 명시적 Git 커밋 명령(`repo_commit`) 신설 ("커밋해", "커밋", "/commit" 등) 및 변경점 유무 정직한 보고
- [x] 구어체 원격 푸시(`repo_push`) 어미/조사 확장 ("푸시도해야지", "푸시해야지", "푸시도", "올려야지" 등)
- [x] 원격 저장소 상태/주소 질의(`get_remote_info`) 처리 ("어디다 푸시한거야?", "어디로 푸시했어?")로 실제 GitHub URL/브랜치 투명 브리핑
- [x] 시스템 프롬프트 가드레일 강화로 Git 환각 및 허위 가상 브랜치 날조 원천 차단
- [x] `tests/test_agent_service.py`, `tests/test_supervisor_service.py`, `./scripts/smoke_test.sh` 검증 완료

### Phase 20: 웹 연결 복원력, Cloudflare HTTP/2 터널 안정화 및 화면 복귀 자동 동기화 (ADR-021) - ✅ 완료
- [x] Cloudflare Tunnel 통신 프로토콜을 QUIC UDP에서 신뢰성 높은 HTTP/2 TCP TLS로 강제 전환하여 유휴 연결 드롭 차단
- [x] Uvicorn Keep-Alive 시간(75초) 및 동시성(100) 튜닝을 통해 역방향 프록시 소켓 경합 및 502/504 방지
- [x] SQLite 동시성 락 방지 (`timeout=30.0`) 적용
- [x] 초경량 헬스체크 및 하트비트 핑 엔드포인트 (`GET /api/health`, `GET /healthz`) 신설
- [x] 프론트엔드(`main.js`, `dev.js`) 지능형 재시도 엔진(`fetchWithRetry`) 및 65초 타임아웃 주입
- [x] 스마트폰 백그라운드 전환/화면 복귀 시 자동 헬스체크 및 세션 히스토리 복원(`visibilitychange`, `online`/`offline`) 구현
- [x] 실시간 연결 상태 배너(`#connection-banner`) 및 3단계 펄스 인디케이터(`online`, `warning`, `offline`) UI 적용
- [x] `tests/test_web_router.py` 헬스체크 단위 테스트 및 `scripts/smoke_test.sh` 0-1 단계 라이브 검증 완료

### Phase 21: GTD 및 데일리 로그 파일 즉시 열람 숏컷(/today, /gtd) 및 DevBot 대기시간 최적화 (ADR-022) - ✅ 완료
- [x] `AgentService`에 `read_daily_log()`, `read_gtd_files()`, `read_gtd_and_daily_log()` 구현 (KST 기준 파일 원본 마크다운 및 미완료 체크박스 자동 집계)
- [x] `LLMProvider`에 `daily_log_inspect`, `gtd_inspect`, `gtd_and_log_inspect` 인텐트 및 슬래시 커맨드(`/today`, `/daily`, `/gtd`, `/inbox`, `/gtd-today`, `/briefing`) 인식 추가
- [x] `SupervisorService`에서 지연 없는 결정론적 파일 즉시 열람 라우팅 연동
- [x] `DevAgentService`에 `/today`, `/gtd`, `/gtd-today` 엔지니어링 툴체인 연동 및 프롬프트 히스토리 경량화(200자 트리밍) & 35초 타임아웃 적용
- [x] Watson 비서 콘솔(`/watson`)에 빠른 액션 칩 바(`.watson-quick-bar`: `/today`, `/gtd`, `/briefing`, `/sync`, `/push`) 구현
- [x] DevBot 콘솔(`/dev`)에 `/today (일일로그)`, `/gtd (GTD현황)` 칩 추가
- [x] 단위 테스트 및 스모크 테스트 라이브 검증 완료

### Phase 22: 모바일 뷰포트 레이아웃 안정화 & 컴포넌트 충돌 방지 (ADR-023) - ✅ 완료
- [x] 모바일(<= 768px) 헤더 긴 부제목(`p#chat-subtitle`) 자동 숨김으로 줄바꿈 충돌 차단
- [x] 모바일 우측 액션 배지 34x34px 정사각형 터치 아이콘 버튼으로 정돈 및 GTD 경로 배지 50px 축약
- [x] 빠른 칩 바(`.watson-quick-bar`, `.dev-quick-bar`) 슬림 가로 스와이프 필 바로 개편 및 스크롤바 숨김(`scrollbar-width: none`)
- [x] 수동 카테고리 드롭다운 제거 & 100% AI 자동 분류 전환으로 하단 고정 영역 슬림화 (140px ➔ 65px)
- [x] `.message`, `.bubble`, `.code-block`에 `min-width: 0; word-break: break-word; overflow-wrap: anywhere;` 적용 및 아바타 `flex-shrink: 0;` 고정
- [x] 코드 블록(`<pre class="code-block">`) 내부 스크롤 격리로 긴 코드/마크다운 표 Flex Overflow 원천 차단
- [x] 에이전트 허브 포털 메트릭 카드 2x2 반응형 그리드 개편 및 정적 템플릿 CSS/JS 캐시 방지 버전(`v=1.3.3`) 일괄 반영
- [x] 스모크 테스트 및 단위 테스트 라이브 검증 완료

### Phase 23: 아침/저녁 맞춤형 GTD 브리핑(Morning & Evening Briefing) 프로토타입 (ADR-024) - ✅ 완료
- [x] `BriefingService` 신설: 시간대(KST) 기반 Morning(05:00~13:59) / Evening(14:00 이후) 자동 판별 및 명시적 모드 오버라이드 지원
- [x] GTD 수집함(`inbox.md`), 다음 행동(`next_actions.md`), 데일리 로그(`logs/daily/YYYY-MM-DD.md`) 구조화 데이터 수집
- [x] AI 지능형 브리핑 합성 및 0.01초 무지연 결정론적 룰 기반 포맷터 듀얼 엔진 구현
- [x] `LLMProvider`에 `task_briefing_morning`, `task_briefing_evening` 인텐트 및 슬래시 커맨드(`/briefing morning`, `/briefing evening`, `/briefing`) 연동
- [x] `SupervisorService` 및 `DevAgentService`에서 원격 Git 자동 최신화(`git pull`) 후 맞춤형 브리핑 라우팅 연계
- [x] 외부 연동용 REST API 엔드포인트(`GET /api/briefing?mode=morning|evening`) 신설
- [x] 웹 콘솔 퀵 바에 `[🌅 아침 브리핑]`, `[🌇 저녁 회고]` 원터치 칩 추가
- [x] 단위 테스트(`tests/test_briefing_service.py`, `tests/test_web_router.py`), 린트/타입 검사 및 `./scripts/smoke_test.sh` 3-13 라이브 검증 완료











