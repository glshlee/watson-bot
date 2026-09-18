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

### Phase 24: 브리핑 스케줄 UI 시각화 및 당일 일정 타임라인 (ADR-025) - ✅ 완료
- [x] 아침(08:30 KST, 활성 05:00~13:59), 저녁(20:00 KST, 활성 14:00~04:59) 정규 브리핑 시각 및 윈도우 명세 정립
- [x] `BriefingService.get_schedule_info()` 및 `format_schedule_briefing()`으로 구조화된 스케줄 정보 및 당일 일정 타임라인 파싱 구현
- [x] `LLMProvider` 및 `SupervisorService`에 `briefing_schedule_inspect` 인텐트(`/schedule`, `/briefing schedule`, "몇 시에 스케줄링 되어있어?", "스케줄 확인") 연동
- [x] 경량 REST 엔드포인트(`GET /api/briefing/schedule`) 신설
- [x] 웹 콘솔 퀵 바에 시간 명시 칩(`[🌅 아침 (08:30)]`, `[🌇 저녁 (20:00)]`) 및 `[⏰ 스케줄]` 칩 배치
- [x] 인터랙티브 스케줄 팝업 모달(`#schedule-modal`) 구현 (현재 활성 브리핑 모드 뱃지, 규격 상세, 당일 일정 타임라인)
- [x] 모바일 반응형 스타일링 및 캐시 방지 버전(`v=1.3.5`) 일괄 적용
- [x] 단위 테스트(`test_briefing_service.py`, `test_web_router.py`) 및 `./scripts/smoke_test.sh` 3-13-5, 3-13-6 라이브 검증 완료

### Phase 25: 텔레그램 정기 브리핑 자동 푸시 스케줄러 (ADR-026) - ✅ 완료
- [x] `BriefingScheduler` 백그라운드 서비스 구현 (매일 08:30 KST 아침 브리핑 및 20:00 KST 저녁 회고 자동 감시 및 능동 푸시)
- [x] 일자별 발송 이력(`last_dispatched`) 추적으로 하루 1회 중복 발송 차단
- [x] 푸시 발송 전 원격 Git 저장소 최신화(`git pull`) 및 세션 히스토리(`telegram:{chat_id}`) 자동 영속화
- [x] `TelegramService.send_message` 마크다운 파싱 오류 시 일반 텍스트 자동 폴백 재시도 방어막 구축
- [x] FastAPI lifespan 컨텍스트 매니저에 스케줄러 백그라운드 태스크 등록 및 안전 종료 로직 연동
- [x] `GET /api/briefing/scheduler/status` 및 `POST /api/briefing/trigger-push` REST 엔드포인트 신설
- [x] 웹 콘솔 스케줄 모달(`#schedule-modal`) 내 텔레그램 푸시 연동 카드 및 `[🔔 텔레그램으로 지금 즉시 발송]` 버튼 제공
- [x] 단위 테스트(`tests/test_briefing_scheduler.py`, `tests/test_web_router.py`) 및 `./scripts/smoke_test.sh` 3-14 라이브 검증 완료

### Phase 26: 텔레그램 인터랙티브 인라인 키보드 및 원클릭 태스크 조작 (ADR-027) - ✅ 완료
- [x] `TelegramService.get_briefing_keyboard()` 구현 (아침: 1순위 완료/동기화/전체할일/푸시, 저녁: 일기쓰기/동기화/푸시/내일할일)
- [x] `AgentService.complete_top_task()` 및 `complete_matching_tasks()` 결정론적 체크박스 완료(`- [x]`) 엔진 구현
- [x] 텔레그램 인라인 콜백 쿼리 라우팅(`task_done_top1`, `action_sync`, `action_push`, `action_show_tasks`, `action_show_next`, `action_prompt_diary`) 및 0.1초 고속 토스트 응답
- [x] `/done` 및 `/done [태스크명]` 슬래시 커맨드 및 `LLMProvider` `task_complete` 인텐트 연동
- [x] `BriefingScheduler.dispatch_briefing` 및 텔레그램 대화 브리핑 시 인라인 키보드 자동 부착
- [x] 단위 테스트(`test_telegram_service.py`, `test_agent_service.py`, `test_briefing_scheduler.py`) 및 `./scripts/smoke_test.sh` 3-8-1 라이브 검증 완료

### Phase 27: 기록 여부 결정론적 검사 및 문두 기록 지시어 라우팅 (ADR-028) - ✅ 완료
- [x] `LLMProvider`에 `log_status_inspect` 인텐트 신설 ("오늘 로그 파일에 기록했어?", "기록했어?", "일기 적었어?", "기록 확인" 등 질의의 LLM 가상 시뮬레이션 원천 차단)
- [x] `SupervisorService` 물리적 디스크 검사 파이프라인 구현 (파일/기록 존재 시 실제 전문 보고, 미작성 시 직전 대화 역추적 스니펫 제시 및 "응" 원클릭 기록 승인 유도)
- [x] 문두 기록 지시어 패턴(`front_record_pattern`) 신설 ("어제 gtd에 이 내용을 넣어달라구 [본문]", "오늘 일기에 이거 적어줘: [본문]" 등)
- [x] 구어체 액션 정규식(`record_action_pattern`) 및 컨텍스트 안전 `sync_triggers` 필터링 적용 ("업데이트 해줘 위 내용" 오분류 차단)
- [x] `_call_ai_engine` 시스템 프롬프트에 가상 시뮬레이션 기록 금지 엄격 가드레일 추가
- [x] 단위 테스트(`test_llm_provider.py`, `test_supervisor_service.py`), 린트/타입 검사 및 `./scripts/smoke_test.sh` 3-8-2 라이브 검증 완료

### Phase 28: 2단계 사전 검토 및 원터치 승인 워크플로우 (ADR-029) - ✅ 완료
- [x] 운동, 생각, 일상/업무, 가족/식사/병원 등 삶의 일과 감지 시 마크다운 초안 카드(Draft Preview Card) 사전 제안 파이프라인 구현 (`log_suggest`)
- [x] 타임스탬프(`- [HH:MM]`), 저장될 대상 파일 경로, 카테고리 명시 및 GTD 액션 과제 동시 감지 초안 지원
- [x] SQLite 세션 메타데이터에 `pending_log` (`content`, `category`, `gtd_task`, `is_dual`) 영속화
- [x] 텔레그램 인라인 버튼(`[✅ 응, 기록해줘]`, `[❌ 아니야]`) 및 콜백 쿼리 라우팅(`confirm_log`, `reject_log`) 연동
- [x] 웹 대시보드(`/watson`) 퀵 액션 버튼(`[응, 기록해줘]`, `[아니야]`) 동적 렌더링 및 원터치 처리
- [x] 복합 승인 정규식 패턴(`confirm_patterns`) 고도화 ("응", "좋아", "응 좋아", "이대로 기록해줘", "응 좋아 기록해줘" 등 완벽 대응) 및 맥락 역추적 안전 가드
- [x] 파워유저용 패스트트랙(`/log [내용]`) 직통 기록 유지
- [x] 단위 테스트(`test_llm_provider.py`, `test_supervisor_service.py`), 린트/타입 검사 및 `./scripts/smoke_test.sh` 3-8-3 라이브 검증 완료

### Phase 29: 출근길 맞춤형 브리핑 설정 인터페이스 및 동적 연동 (ADR-030) - ✅ 완료
- [x] `CommuteConfigService` 신설: 거주지, 기상청 격자 좌표, 에어코리아 측정소, 출근 버스(정류소명/ID, 노선 번호, 도시코드), 발송 시각(`07:30`), 공공데이터 API 키 관리 및 `config/commute_config.json` 영속화
- [x] API 키 안전 마스킹(`****`) 및 기존 등록 키 보존 로직 구현
- [x] REST API 엔드포인트(`GET/POST /api/settings/commute`, `POST /api/settings/commute/preview`) 구축
- [x] 웹 대시보드 상단 헤더 배지(`#commute-settings-badge`), 퀵바 칩(`[🚌 출근길 설정]`), 인터랙티브 모달(`#commute-modal`) 구현
- [x] 모달 내 실시간 브리핑 카드 미리보기(`[🔍 실시간 미리보기]`) 및 원터치 저장/토스트 연동
- [x] `SupervisorService` 및 `LLMProvider`에 `commute_inspect` 인텐트, 슬래시 커맨드(`/commute`, `/commute test`), 자연어 질의 연계
- [x] DevBot 콘솔(`/dev`) 퀵바에 `/commute (출근길)` 칩 추가
- [x] 공공데이터 키 미등록/외부 장애 시 스마트 시뮬레이션(Mock) 폴백 지원
- [x] 단위 테스트(`tests/test_commute_config_service.py`) 및 `./scripts/smoke_test.sh` 6단계(6-1 ~ 6-4) 라이브 검증 완료

### Phase 30: 구어체 태스크 완료 인식 고도화 및 항의·메타 피드백 가드레일 (ADR-031) - ✅ 완료
- [x] `LLMProvider`에 구어체 태스크 완료 보고 패턴(`colloquial_complete_pattern`) 지원 ("민방위 사이버교육은 완료했어", "사이버교육 다했어", "보고서 제출 끝났어" 등)
- [x] `[태스크] 완료 gtd에 기록해/반영해` 지시 시 신규 할 일 생성 차단 및 `task_complete` 인텐트로 최우선 라우팅
- [x] 사용자 항의 / 메타 피드백 가드레일(`meta_protest_patterns`) 구축 ("아니 이미 인박스에 있다면서. 그래서 완료했다고 말한건데?" 등)
- [x] 항의 발화 감지 시 일기 초안(`log_suggest`) 오탐을 100% 방지하고, 이전 대화 히스토리(`history`) 역추적으로 의도된 태스크를 자동 발췌하여 지능형 복구 및 정중한 사과 응답 연계
- [x] `AgentService.complete_matching_tasks`의 서술어("완료했어", "끝났어", "해결함", "은/는/이/가") 자동 strip 및 2글자 이상 세부 토큰 분해 매칭 구현
- [x] 단위 테스트(`tests/test_task_completion_and_meta_guard.py`), 린트/타입 검사 및 `./scripts/smoke_test.sh` 7단계(7-1 ~ 7-3) 라이브 검증 완료

### Phase 31: GTD 스킬 명세 동기화 및 태스크 완료 시 데일리 로그 수술적 이관 (ADR-032) - ✅ 완료
- [x] `AgentService`에 `transfer_completed_task_to_daily_log` 메서드 구현 (당일 일일 로그 `logs/daily/YYYY-MM-DD.md` 생성 및 `## ✅ 오늘 완료한 일 (Completed GTD Tasks)` 섹션에 `- [x]` 형태로 이관)
- [x] `AgentService.complete_top_task` 및 `complete_matching_tasks` 고도화: `gtd/` 파일(`inbox.md`, `next_actions.md`)에서 완료 항목을 물리적으로 완전히 **잘라내어(Cut)** 삭제하고, 오늘 날짜 데일리 로그로 **이동(Paste)**하는 수술적 이동(Surgical Transfer) 집행
- [x] `LLMProvider`에 GTD 저장소 내 `skills/gtd-assistant/SKILL.md` 행동 강령(SSOT, Surgical Transfer) 파싱 및 시스템 프롬프트 자동 주입(`_load_skill_instructions`) 연동
- [x] `_call_ai_engine`의 `agy` CLI 호출 시 서브프로세스 `cwd`를 사용자의 GTD 저장소 경로(`GTD_PATH`)로 지정하여 Antigravity CLI의 네이티브 스킬 자동 탐색 및 로딩 보장
- [x] 헬스장/스쿼트/푸시업 등 운동 일과 발화가 `task_complete`로 오인되지 않도록 가드레일 분리
- [x] 단위 테스트(`tests/test_agent_service.py`, `tests/test_telegram_service.py`, `tests/test_task_completion_and_meta_guard.py`), Ruff/Mypy 검사 및 `./scripts/smoke_test.sh` 전체 통과 완료

### Phase 32: 아침 브리핑 실시간 날씨·미세먼지 통합 및 자연어 기상 질의 연동 (ADR-033) - ✅ 완료
- [x] `CommuteConfigService`에 `get_morning_weather_card()` 및 `get_standalone_weather_card()` 구현
- [x] `BriefingService`의 아침 브리핑(`mode == "morning"`) 상단에 실시간 날씨(기온, 체감, 강수확률/우산 팁), 대기질(PM10/PM2.5), 출근 버스 도착 정보 기본 통합 탑재
- [x] `generate_briefing`의 LLM 프롬프트에 기상 데이터 주입 및 기존 `"날씨"` 배제 필터 버그 수정, AI 응답 내 날씨 누락 시 상단 자동 보강(Patch) 탑재
- [x] `LLMProvider` 및 `SupervisorService`에 자연어 기상 질의("날씨 브리핑", "날씨 정보", "미세먼지 수치", `/weather`) 연동 및 인사/잡담(`chat_only`) 안전 분리
- [x] 단위 테스트(`tests/test_briefing_service.py`, `tests/test_commute_config_service.py`, `tests/test_web_router.py`), Ruff/Mypy 검사 및 `./scripts/smoke_test.sh` 전체 통과 완료

### Phase 33: 동네 설정 스마트 지오코딩 및 대화형 위치 변경 연동 (ADR-034) - ✅ 완료
- [x] 스마트 지오코딩 엔진(`GeoService`) 구축: 서울 25개 구/주요 동, 경기/인천/광역시 주요 도시를 망라하는 격자(X, Y), 대기 측정소, 시도 코드 0.001초 결정론적 매핑
- [x] `CommuteConfigService`에 `update_location_by_query()` 구현: 동네명 자연어 분석 및 `config/commute_config.json` 실시간 영속화
- [x] `LLMProvider` 및 `SupervisorService`에 `location_set` 및 `location_inspect` 인텐트 지원:
  - `/location [동네명]`, `/동네 [동네명]`, "우리 동네 성동구 금호동으로 설정해줘", "동네는 성동구 금호동인데 이렇게 그냥 설정하면 되는거야?" 등 즉시 반영
  - 동네 설정 직후 해당 지역 기준의 실시간 기상 브리핑 프리뷰 카드 반환
  - `/location`, "우리 동네 어디로 되어있어?" 등 현재 거주지 조회 안내
- [x] `settings_router.py`에 `POST /api/settings/commute/resolve-location` REST API 구축
- [x] 웹 대시보드 모달(`#commute-modal`) 내 `[<i class="fa-solid fa-wand-magic-sparkles"></i> 자동 찾기]` 버튼(`#btn-resolve-location`) 및 `main.js` 자동 채움 연동
- [x] 단위 테스트(`tests/test_geo_service.py`), Ruff/Mypy 검사 및 `./scripts/smoke_test.sh` 6-5, 6-6 라이브 검증 완료

### Phase 34: Open-Meteo 무설정 오픈 API 기반 실시간 날씨 및 대기질 연동 (ADR-035) - ✅ 완료
- [x] Zero-Key 글로벌 오픈 기상/대기질 조회 엔진(`WeatherService`) 구축:
  - Open-Meteo Forecast & Air Quality API를 통한 위경도 기반 실시간 기온, 체감기온, WMO 기상 코드, 강수확률, PM10, PM2.5 실시간 조회 (평균 150ms)
  - 한국 환경부 기준 대기질 등급(좋음, 보통, 나쁨, 매우나쁨) 및 직관적 색상 이모지(🟢, 🟡, 🟠, 🔴) 정규화
  - 강수확률 및 WMO 기상 코드(비/눈/소나기/뇌우) 기반 지능형 우산 팁(`우산 필수 ☔`, `접이식 우산 추천 🌂`, `우산 불필요 ☀️`) 자동 생성
  - 10분(600초) TTL 인메모리 캐시 및 3.5초 타임아웃 기반 무중단 안전 폴백(Fallback) 구조 완비
- [x] `GeoService` 위경도 지오코딩 보강: 서울 25개 자치구 및 전국 주요 지역의 위도(`lat`)와 경도(`lon`) 내장 및 자동 산출
- [x] `CommuteConfigService` 실시간 연동:
  - `config/commute_config.json`에 `latitude`, `longitude` 영속화 및 누락 시 자동 보강
  - 모닝 브리핑 및 날씨 카드에 `(📡 Open-Meteo 실시간 라이브 API - HH:MM 기준)` 신뢰성 배지 출력
### Phase 35: 키워드 정규식 가로채기 철거 및 LLM 자연어 위임·부정 피드백 가드레일 (ADR-036) - ✅ 완료
- [x] 단순 명사 부분 일치(`workout_keywords`, `idea_keywords`, `work_keywords`, `life_keywords`) 기반 강제 `log_suggest` 생성기 전면 철거
- [x] 부정 / 불필요 / 취소 / 피드백 가드레일(`negative_feedback_patterns`) 최우선 적용:
  - `"필요 없어"`, `"필요가 없어"`, `"안 사도 돼"`, `"안 해도 돼"`, `"선물받아"`, `"취소"`, `"삭제"`, `"어때?"` 등 감지 시 일과 초안 생성 원천 차단 및 즉시 LLM 대화로 직행
- [x] "휴지는 선물받아서 구매할 필요가 없어"에서 "필[요가] 없어"의 "요가" 서브스트링 매칭으로 인한 `Workout & Health` 오탐지 결함 근본 해결
- [x] 과거형/완료형 서술어와 결합된 실제 서사적 완료 진술문(`스쿼트 100kg 성공`, `러닝 5km 완주`, `미역국을 끓였어` 등)에 한정한 안전한 초안 제안 로직 유지
- [x] 텔레그램 세션 DB 내 오염된 `pending_log` 초기화 및 GTD `inbox.md` 구매 목록(두루마리 휴지 선물 수령) 정제
- [x] 신규 회귀 방지 단위 테스트(`test_llm_provider_negative_feedback_and_yoga_guard`), Ruff/Mypy 검사 및 `./scripts/smoke_test.sh` 전 항목 라이브 검증 완료

### Phase 36: 실시간 출근 버스 도착정보 API 실연동 및 지능형 캐시·안전 폴백 (ADR-037) - ✅ 완료
- [x] `BusService` 구축:
  - 서울시 TOPIS 버스도착정보조회 API(`http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid`) 연동 및 ARS ID/노선번호 기반 실시간 잔여시간, 잔여 정류소, 막차/차고지 상태 조회
  - 국토교통부 TAGO 버스도착정보조회 API 연동 및 전국/경기도(city_code) 정류소 도착 예정 정보 조회
  - `urllib.parse.unquote()` 기반 이중 인코딩 방지 및 공공데이터포털(data.go.kr) 서비스키 완벽 호환
  - 45초 TTL 인메모리 캐시(`_cache`) 적용으로 API 쿼터 절약 및 0.01초 초고속 응답 보장
  - API 키 미등록 또는 외부 장애 시 현재 분(minute) 기반 가변적 잔여 시간(3~11분)과 비서 출근 팁 동적 계산으로 정적 4분 고정 결함 탈피 및 안전한 폴백 제공
- [x] `CommuteConfigService` 실연동:
  - 모닝 브리핑 및 프리뷰 생성 시 `BusService.get_arrival_info()` 실시간 반영
  - 단독 버스 도착 카드 반환 메서드 `get_standalone_bus_card()` 신설
- [x] `LLMProvider` 및 `SupervisorService` 연동:
  - `/bus`, "출근 버스 언제 와?", "버스 도착 정보" 질의 시 단독 실시간 버스 도착 카드 즉시 제공
- [x] 단위 테스트(`tests/test_bus_service.py`), Ruff/Mypy 검사 및 `./scripts/smoke_test.sh` 6-7 단계 라이브 검증 완료

### Phase 38: 실시간 버스 도착 정보 원터치 인라인 갱신 및 웹/텔레그램 동시 지원 (ADR-039) - ✅ 완료
- [x] `BusService.get_arrival_info` 및 `CommuteConfigService` 내 `force_refresh=True` 매개변수 지원으로 45초 인메모리 캐시 즉시 우회 및 실시간 강제 조회 구현
- [x] 단독 버스 카드(`get_standalone_bus_card`)의 조회 일시에 초 단위 타임스탬프(`%H:%M:%S KST`) 적용으로 시각적 갱신 확인 보장
- [x] REST API 엔드포인트 `GET/POST /api/settings/commute/bus-card` 신설:
  - 최신 마크다운 카드(`markdown`), 브리핑용 요약 라인(`transit_line`), 갱신 시각(`updated_time`), `transit_summary` 반환
- [x] 텔레그램 인플레이스 갱신 연동 (`TelegramService`):
  - `edit_message_text` 구현 및 버스 카드/아침 브리핑 하단 `[🔄 실시간 버스 갱신]` (`action_refresh_bus`) 인라인 버튼 부착
  - 버튼 클릭 시 새 메시지 생성 없이 기존 메시지를 즉시 수정(editMessageText)하고 0.1초 콜백 토스트 제공
  - `/start`, `/help` 명령어 목록에 `/bus` 안내 추가
- [x] 웹 대시보드 콘솔 실시간 인라인 갱신 연동 (`main.js`, `style.css`, `index.html`):
  - 버스 카드가 포함된 어시스턴트 메시지 버블 하단에 `.bus-refresh-bar` 및 `[🔄 버스 도착 갱신]` 버튼 동적 렌더링
  - 클릭 시 `/api/settings/commute/bus-card` 비동기 통신 및 버블 텍스트 인라인 교체, `[✅ HH:MM:SS 갱신됨]` 배지 시각화
  - 왓슨 퀵 숏컷 바에 `[🚍 버스 도착]` (`data-cmd="/bus"`) 원클릭 칩 추가
- [x] 단위 테스트(`tests/test_bus_service.py`, `tests/test_telegram_service.py`), Ruff/Mypy 정적 검사 및 `./scripts/smoke_test.sh` 6-9 단계 라이브 검증 완료

### Phase 39: 텔레그램 네이티브 봇 메뉴 명령어(Bot Commands Menu) 등록 및 자동 동기화 (ADR-040) - ✅ 완료
- [x] 표준 봇 명령어 14종 사전 정의 (`TelegramService.DEFAULT_COMMANDS`):
  - `today`, `briefing`, `bus`, `log`, `done`, `gtd`, `schedule`, `commute`, `sync`, `push`, `url`, `status`, `help`, `start`
- [x] Telegram Bot API 연동 및 자동 등록 (`TelegramService.set_my_commands`, `get_my_commands`):
  - `setMyCommands` 및 `setChatMenuButton(type="commands")` 호출로 모바일 대화창 좌측 `[/]` 메뉴 팝업 연동
  - 봇 폴링 루프(`start_polling`) 시작 시 자동 등록 실행
- [x] REST API 엔드포인트 신설 (`app/routers/telegram_router.py`):
  - `POST /api/telegram/setup-commands`: 메뉴 명령어 즉시 등록 및 갱신
  - `GET /api/telegram/commands`: 등록된 봇 메뉴 명령어 목록 및 상태 조회
- [x] 텔레그램 메뉴 `/gtd` 라우팅 개선:
  - 메뉴에서 `/gtd` 선택 시 단순 저장소 메타데이터가 아닌 실제 수집함 및 다음 행동 목록 즉시 브리핑
- [x] 단위 테스트(`tests/test_telegram_service.py`), Ruff/Mypy 정적 검사 및 `./scripts/smoke_test.sh` 4-1, 4-2 단계 라이브 검증 완료

### Phase 40: 텔레그램 봇 메뉴 명령어 관리 UI 및 실시간 모바일 미리보기·원터치 동기화 (ADR-041) - ✅ 완료
- [x] `config/telegram_commands.json` 영속화 및 `TelegramService` 관리 메서드(`get_configured_commands`, `save_configured_commands`, `reset_to_default_commands`) 구축
- [x] REST API 엔드포인트 확장 (`app/routers/telegram_router.py`):
  - `POST /api/telegram/commands`: 명령어 저장 및 실시간 Telegram Bot API 동기화
  - `POST /api/telegram/commands/reset`: 기본 14종 복원
- [x] 웹 콘솔 전용 텔레그램 메뉴 설정 모달 (`#telegram-menu-modal` in `app/templates/index.html`):
  - 상단 헤더 배지(`[📱 메뉴: N개]`) 및 퀵 바 `[📱 텔레그램 메뉴]` 원터치 칩 연동
  - 좌측 명령어 편집기: 토글 체크박스, 명령어/설명 인라인 편집, 삭제, 새 명령어 추가 폼
  - 우측 모바일 텔레그램 다크 UI 실시간 팝업 미리보기(`mock-telegram-frame`)
  - 하단 액션: `[기본값 복원]` 및 `[텔레그램에 즉시 반영]`
- [x] 반응형 인터랙션 스타일링 (`app/static/css/style.css`) 및 비동기 DOM 컨트롤러 (`app/static/js/main.js`) 구현
- [x] 단위 테스트(`tests/test_telegram_service.py`), Ruff/Mypy 정적 분석 및 `./scripts/smoke_test.sh` 4-3, 4-4 단계 라이브 검증 완료

### Phase 41: GTD 마감일(Due Date / D-Day) 자동 감지 & 브리핑 알림 시스템 (ADR-042) - ✅ 완료
- [x] `DueDateService` 구축 (`app/services/due_date_service.py`):
  - 마감일 태그 포맷 파서 (`~YYYY-MM-DD`, `~YYYY.MM.DD`, `@due(YYYY-MM-DD)`) 구현
  - 한국어 자연어 상대일자("오늘까지", "내일까지", "모레까지", "이번 주 금요일까지", "다음 주 화요일까지", "N일 뒤까지") 정밀 계산 엔진 구현
  - D-Day 잔여일 계산 및 4단계 긴급도 분류 (`overdue`: 기한 초과, `today`: 오늘 마감, `urgent`: 3일 이내 임박, `upcoming`: 4일 이상)
  - 마감일 기준 우선순위 가중치 스코어링 (`calculate_priority_score`) 및 `next_actions.md` 지능형 정렬
  - 브리핑용 경고 섹션 포맷터 및 단독 `/dday` 마감일 점검 리포트 생성기 구현
- [x] 모닝 & 이브닝 브리핑 및 실시간 GTD 요약 연동 (`app/services/briefing_service.py`, `app/services/agent_service.py`):
  - 아침 08:30 브리핑 상단에 D-Day 경고 섹션(`🚨 오늘 마감 D-Day`, `⚠️ 마감 임박 D-1~D-3`, `⛔ 기한 초과 Overdue`) 주입
  - 아침 1순위 집중 추천 시 D-Day 임박 과제를 최우선 추천하도록 자동 선별
  - 저녁 브리핑에서 미완료된 D-Day 당일/초과 과제를 내일로 이월할 최우선 과제로 강조
  - `read_gtd_files()` 요약 브리핑에 `#### ⏳ 3. 마감일(D-Day) 현황` 섹션 추가
- [x] 단독 마감일 점검 질의 & 텔레그램/웹 콘솔 연동:
  - `/dday`, `/deadline`, "마감일 확인", "D-day 확인" 의도 감지 (`dday_inspect`) 및 라우팅 (`app/services/llm_provider.py`, `app/services/supervisor_service.py`)
  - DevBot `/dday` 툴체인 단독 실행 및 `/help` 안내 지원 (`app/services/dev_agent_service.py`)
  - 텔레그램 브리핑 인라인 키보드에 `[⏳ D-Day 마감 확인]` (`action_show_dday`) 원터치 콜백 버튼 추가 (`app/services/telegram_service.py`)
  - 웹 대시보드 왓슨 및 DevBot 퀵 숏컷 바에 `[⏳ D-Day 마감]` (`data-cmd="/dday"`) 원터치 칩 추가 (`app/templates/index.html`, `app/templates/dev.html`)
  - 텔레그램 네이티브 봇 메뉴 15종 명령어로 `/dday` 기본 등록 (`TelegramService.DEFAULT_COMMANDS`, `config/telegram_commands.json`)
- [x] 대화형 마감일 지정 태스크 생성:
  - 사용자가 "내일까지 보고서 제출 GTD에 추가해줘" 발화 시 `_extract_actionable_task`에서 상대일자를 파싱하여 `~YYYY-MM-DD` 태그 자동 부착
- [x] 단위 테스트(`tests/test_due_date_service.py`), Ruff/Mypy 정적 검사 및 `./scripts/smoke_test.sh` 3-13-7, 3-13-8 단계 라이브 검증 완료

### Phase 42: 과거 라이프로그·GTD 고속 검색 & 주간 결산 리포트 (`/search`, `/weekly` - ADR-043) - ✅ 완료
- [x] `SearchService` 구축 (`app/services/search_service.py`):
  - 일일 로그(`logs/daily/*.md`), GTD 문서(`gtd/*.md`, `inbox.md`), 프로젝트 문서 대상 고속 마크다운 검색 엔진 구현
  - 공백 구분 다중 키워드 AND 검색 및 대소문자 무시 지원
  - 본문 볼드 하이라이트(`**키워드**`) 및 220자 문맥 스니펫 생성
  - 일일 로그 최신성, 완전 일치, GTD 수집함 결합 관련도 스코어링 및 역순 정렬
  - 검색 결과 요약 마크다운 카드 포맷터(`format_search_results_card`) 구현
- [x] `WeeklyReviewService` 구축 (`app/services/weekly_review_service.py`):
  - 기준일(KST 오늘)로부터 지난 7일간의 일일 로그 파싱 및 정량 메트릭 수집 (기록 달성률 %, 완료 태스크 `- [x]`, 카테고리별 활동)
  - `gtd/inbox.md` 미분류 태스크 체류 점검 및 `next_actions.md` 정리 가이드 제공
  - LLM 지능형 총평 및 기록률 기반 정교한 룰 기반 하이브리드 "왓슨의 주간 한마디" 합성
  - 주간 결산 마크다운 리포트 카드 생성(`generate_weekly_review`)
- [x] 일요일 21:00 KST 능동 푸시 스케줄러 (`BriefingScheduler`):
  - 매주 일요일 21:00 KST 정각 주간 결산 능동 발송 루프 구현 (`dispatch_weekly_review`)
  - 일자별 중복 발송 방지(`self.last_dispatched["weekly"]`), 텔레그램 세션 히스토리 영속화
  - 발송 시 `[📥 Inbox 정리하기]`, `[⏳ D-Day 확인]`, `[🔄 원격 최신화]`, `[🚀 푸시]` 인라인 키보드 부착
- [x] REST API 엔드포인트 신설 (`app/routers/web_router.py`):
  - `GET /api/search?q=키워드`: 검색 결과 목록 및 카드 JSON 반환
  - `GET /api/weekly?days=7`: 주간 결산 메트릭 및 리포트 카드 반환
  - `POST /api/weekly/trigger-push`: 주간 결산 텔레그램 푸시 즉시 테스트
- [x] 인텐트 라우팅 및 텔레그램/웹 콘솔 연동:
  - `/search [키워드]`, `/find [키워드]`, 자연어 질의("지난달 서산 맛집 찾아줘") ➔ `search_query` 인텐트 연동
  - `/weekly`, `/review`, "주간 결산", "이번 주 회고" ➔ `weekly_review` 인텐트 연동
  - DevBot 콘솔 `/search`, `/weekly` 툴체인 단독 실행 및 `/help` 갱신
  - 텔레그램 네이티브 봇 메뉴 17종 명령어로 `weekly`, `search` 추가 등록
  - 웹 대시보드 왓슨 및 DevBot 퀵 숏컷 바에 `[🔍 기록 검색]`, `[📊 주간 결산]` 원터치 칩 추가
- [x] 단위 테스트(`tests/test_search_and_weekly_service.py`), Ruff/Mypy 정적 검사 및 `./scripts/smoke_test.sh` 3-13-9 ~ 3-13-15 단계 라이브 검증 완료

### Phase 43: 사진·영수증·운동인증 Vision AI 멀티모달 분석 & 스마트 기록 (`/vision` - ADR-044) - ✅ 완료
- [x] `VisionService` 구축 (`app/services/vision_service.py`):
  - Gemini 1.5 Flash Vision REST API 멀티모달 프롬프트 및 Base64 전송 파이프라인 연동
  - 5대 도메인 자동 분류: 🏃 운동 인증(workout), 🍲 식사/맛집(meal), 🧾 영수증/지출(receipt), 📝 메모/손글씨(memo), 🖼️ 일상 사진(general)
  - 운동 지표(시간, 거리, 칼로리, 심박수) 추출 및 `## 🏃 운동 & 건강 (Workout & Health)` 섹션 포맷팅
  - 영수증 상호/일시/금액 추출, 카드번호 자동 마스킹 및 GTD 가계부 정리 태스크 자동 제안
  - 오프라인/키 부재 시 100% 무중단 지능형 휴리스틱 스마트 분석 폴백 엔진 구현
  - 초안 미리보기 카드 포맷터(`format_draft_card`) 구현
- [x] 텔레그램 사진 수신 파이프라인 고도화 (`app/services/telegram_service.py`):
  - 사진 수신 시 디스크 저장 및 Vision AI 자동 분석
  - 2단계 사전 검토 초안 카드 및 인라인 키보드(`[✅ 응, 기록해줘]`, `[❌ 아니야]`) 부착
  - 캡션 내 `/log` 또는 `!` 포함 시 즉시 커밋·푸시하는 패스트트랙 지원
- [x] REST API 엔드포인트 신설 (`app/routers/web_router.py`):
  - `POST /api/vision/analyze`: 사진 파일 멀티파트 업로드 및 시각 분석 결과 JSON 반환
  - `POST /api/vision/upload-and-log`: 사진 업로드 후 사전 검토 세션 보류 또는 패스트트랙 즉시 기록
- [x] 인텐트 라우팅 및 텔레그램/웹 콘솔 연동:
  - `/vision [경로] [캡션]`, `/photo`, "사진 분석" ➔ `vision_inspect` 인텐트 및 `SupervisorService` 연동
  - DevBot 콘솔 `/vision [경로] [캡션]` 전용 엔지니어링 도구 체인 및 `/help` 안내 갱신
  - 텔레그램 네이티브 봇 메뉴 18종 명령어로 `vision` 추가 등록 (`TelegramService.DEFAULT_COMMANDS`)
  - 웹 대시보드 왓슨 및 DevBot 퀵 숏컷 바에 `[📷 사진 분석]` (`data-cmd="/vision "`) 원터치 칩 추가
- [x] 단위 테스트(`tests/test_vision_service.py`), Ruff/Mypy 정적 검사 및 `./scripts/smoke_test.sh` 3-13-16 ~ 3-13-19 단계 라이브 검증 완료

---

## 🔮 차세대 기능 백로그 (Future Backlog - 상세 설계: `docs/ideas.md` 참조)

### Phase 44: 웹 대시보드 연간 잔디(Heatmap) & 마크다운 인플레이스 에디터 (`/edit`, `/heatmap` - ADR-045) - ✅ 완료
- [x] `HeatmapService` 구축 (`app/services/heatmap_service.py`):
  - 최근 365일간 일일 로그 파일 전수 스캔 및 5단계(0~4) GitHub 스타일 기여도 레벨 정규화
  - 연속 기록 일수(`current_streak`), 최장 스트릭(`longest_streak`), 총 기록 일수, 연간 달성률(%) 집계
  - 일일 로그 원문 조회(`get_lifelog_content`) 및 마크다운 디스크 저장 & 원자적 Git 커밋/푸시(`save_lifelog_content`)
- [x] REST API 엔드포인트 신설 (`app/routers/web_router.py`):
  - `GET /api/lifelog/heatmap?days=365`: 연간 잔디 그리드 및 통계 메트릭 JSON 반환
  - `GET /api/lifelog/file?date=YYYY-MM-DD`: 특정 일자 일일 로그 원문 및 메타데이터 반환
  - `POST /api/lifelog/save`: 마크다운 편집 내용 저장 및 Git 커밋·푸시 집행
- [x] 웹 대시보드 인터랙티브 UI & 딥링크 (`index.html`, `style.css`, `main.js`):
  - 헤더 연간 잔디 뱃지 (`#heatmap-badge`) 및 퀵 바 칩 (`[✏️ 잔디 & 로그 편집]`)
  - 인터랙티브 모달 (`#lifelog-editor-modal`): 52주 잔디 그리드(호버 툴팁, 셀 클릭 이동), 날짜 네비게이션, 좌우 분할 에디터(Textarea + 실시간 마크다운 프리뷰), 원터치 커밋·푸시
  - 딥링크 연동 (`/?edit=YYYY-MM-DD` 접속 시 해당 일자 에디터 자동 오픈)
- [x] 인텐트 라우팅 및 텔레그램/콘솔 연동:
  - `/edit [날짜]`, "일기 편집", "로그 수정" ➔ `lifelog_edit` 인텐트 및 안내 카드 연동
  - `/heatmap`, "잔디 보여줘", "기여도 히트맵" ➔ `lifelog_heatmap` 인텐트 연동
  - DevBot 콘솔 `/edit`, `/heatmap` 툴체인 단독 실행 및 `/help` 갱신
  - 텔레그램 네이티브 봇 메뉴 20종 명령어로 `edit`, `heatmap` 추가 등록 (`TelegramService.DEFAULT_COMMANDS`)
- [x] 단위 테스트(`tests/test_heatmap_service.py`), Ruff/Mypy 정적 검사 및 `./scripts/smoke_test.sh` 3-13-20 ~ 3-13-26 단계 라이브 검증 완료

### Phase 45: 1-Click 셀프호스팅 배포 패키지 & 셋업 위저드 (타인 배포 1단계 - ADR-046) - ✅ 완료
- [x] 대화형 터미널 셋업 위저드 스크립트 (`./scripts/setup_wizard.sh`):
  - 필수 시스템 도구(Python, Git, Curl) 확인 및 7단계 대화형 프롬프트(포트, 타임존, 텔레그램 토큰/Chat ID, Gemini 키, GTD 경로, 동네명, 웹 보안)
  - `-y`/`--non-interactive`(무인 설치), `-d`/`--dry-run`(모의 테스트), `-c`/`--check`(설정 점검) 옵션 지원
  - GTD 디렉토리 자동 생성(`logs/daily`, `gtd/inbox.md`, `gtd/next_actions.md`) 및 `git init` 자동화
  - 호스트 경로 및 사용자 계정 자동 적응 systemd 서비스 유닛(`/tmp/watson.service`) 생성
- [x] 올인원 Docker Compose 배포 템플릿 및 환경 파일 고도화:
  - `Dockerfile`: `python:3.12-slim`, `safe.directory '*'` 설정, 초경량 헬스체크(`GET /api/health`) 연동
  - `docker-compose.yml`: `./config`, SQLite DB, GTD 볼륨 마운트 및 자동 재시작 정책 완비
  - `.env.example`: 초보자 친화적 상세 주석 및 무료 키 발급 링크 명시
- [x] 시스템 배포 준비 상태 진단 서비스 및 엔드포인트:
  - `SetupService` (`app/services/setup_service.py`): 텔레그램, LLM, GTD, 보안 등 8개 영역 진단 및 준비율(%) 산출
  - `GET /api/system/setup-status`: 시스템 준비 상태 JSON 및 마크다운 리포트 반환
  - DevBot 콘솔 `/setup`, `/설정점검` 툴체인 및 퀵 칩(`[⚙️ 배포점검]`), `/help` 갱신
- [x] 초보자용 10분 완성 퀵스타트 가이드 (`docs/quickstart_guide.md`):
  - 준비물 3종(봇 토큰, Chat ID, Gemini 키) 발급 방법, 위저드 실행, systemd/Docker 가동 및 FAQ 완비
- [x] 단위 테스트(`tests/test_setup_service.py`), Ruff/Mypy 정적 검사 및 `./scripts/smoke_test.sh` 3-13-27 ~ 3-13-29 라이브 검증 완료

### Phase 46: 웹 콘솔 한국 표준시(KST) 동기화 및 실시간 시계 배지 연동 (ADR-047) - ✅ 완료
- [x] 세션 모델 및 서비스 KST 통일:
  - `SessionModel` 및 `ChatMessageModel` 기본값을 `kst_now()`(`get_now()`, `Asia/Seoul`)로 전면 교체
  - `SessionService._format_datetime_iso()` 도입으로 직렬화 시 KST 오프셋(`+09:00`) 항상 포함
  - 기존 SQLite DB(`app.db`) 내 과거 UTC 세션/메시지 타임스탬프를 KST로 일괄 보정 마이그레이션
- [x] 웹 프론트엔드 상대 시간 포맷터 및 에디터 날짜 보정:
  - `formatRelativeTime(dateStr)` 개선: 무오프셋 문자열도 KST로 자동 보정하여 "9시간 전" 왜곡 해소 및 "방금" 정상화
  - `getKSTDateString()` 구현: 자정~오전 9시 접속 시에도 KST 당일 날짜 파일이 열리도록 에디터 모달 보정
- [x] 상단 헤더 실시간 KST 디지털 시계 배지 (`#header-clock-badge`):
  - Watson 콘솔(`/watson`) 및 DevBot 콘솔(`/dev`) 상단 헤더에 `[⏰ 09:49:10 KST]` 초 단위 실시간 시계 탑재
- [x] 프로세스 레벨 타임존 KST 고정 및 출근길 스케줄러 능동 연동:
  - `app/main.py` lifespan에서 `os.environ["TZ"] = settings.TIMEZONE` 및 `time.tzset()` 호출로 Git 커밋(`+0900`) 전역 표준화
  - `BriefingScheduler` 백그라운드 루프에 `commute_config`의 `send_time`(KST) 일치 검사 및 출근 브리핑 푸시 파이프라인 연동
- [x] 단위 테스트(`test_session_service.py`, `test_briefing_scheduler.py`, `test_web_router.py`) 및 `./scripts/smoke_test.sh` 라이브 검증 완료

### Phase 47: 단위 테스트 초고속화 & UI 템플릿 컴포넌트화 리팩터링 (ADR-048) - ✅ 완료
- [x] 단위 테스트 실행 환경 초고속화 (`tests/conftest.py`):
  - `fast_unit_test_environment` autouse 픽스처 구축으로 단위 테스트 시 외부 서브프로세스 격리
  - `LLMProvider._find_agy_path -> None` 모킹으로 45초 AGY CLI 타임아웃 및 원격 LLM 호출 차단 (`test_llm_provider.py` 128초 ➔ 0.4초, 320배 가속)
  - `DevAgentService._run_lint` 및 `_run_pytest` 중첩 재귀 실행 모킹으로 불필요한 반복 검사 제거
  - `test_weather_service.py` 외부 네트워크 API 호출 모킹으로 10초 대기열 제거
  - 전체 단위 테스트 수행 시간 867초(14분 27초) ➔ 136초(2분 16초)로 84% 단축 달성
- [x] 웹 UI 템플릿 컴포넌트 모듈화 (`app/templates/index.html` & `app/templates/modals/`):
  - 574라인 단일 모놀리식 템플릿에서 8개 모달 컴포넌트를 `app/templates/modals/`로 완전 분리:
    - `rename_modal.html` (세션 이름 변경)
    - `delete_modal.html` (세션 삭제)
    - `clear_modal.html` (메시지 전체 비우기)
    - `gtd_modal.html` (GTD 작업 경로 설정)
    - `schedule_modal.html` (브리핑 스케줄 및 타임라인)
    - `commute_modal.html` (출근길 날씨·대기질·버스 설정)
    - `telegram_menu_modal.html` (텔레그램 봇 메뉴 관리)
    - `lifelog_editor_modal.html` (연간 잔디 및 일일 로그 인플레이스 에디터)
  - `index.html` 라인 수 574라인 ➔ 183라인으로 68% 경량화 및 가독성/유지보수성 극대화
  - 모든 DOM ID, 폼 액션 및 JavaScript 바인딩 100% 호환 유지
- [x] 단위 테스트, 정적 타입/린트 검사(`mypy`, `ruff`) 및 `./scripts/smoke_test.sh` 라이브 검증 완료

### Phase 48: 프론트엔드 스타일시트(CSS) 컴포넌트 모듈화 리팩터링 (ADR-049) - ✅ 완료
- [x] 7대 도메인별 CSS 모듈 분리 (`app/static/css/`):
  - `variables.css` (69라인): CSS 전역 변수, 리셋, 100dvh 높이, 디스플레이 유틸리티, 공통 애니메이션
  - `layout.css` (657라인): 사이드바, 세션 검색/필터/리스트, 연결 상태 배너, 헤더 배지 6종
  - `chat.css` (333라인): 채팅 콘솔, 메시지 버블, 코드블록, 입력 바, 왓슨 퀵 액션/칩 바
  - `modals.css` (1,370라인): 모달 기본 오버레이 및 8종 팝업 모달 스타일
  - `portal.css` (457라인): 에이전트 허브 대시보드 포털 레이아웃, 메트릭 카드, 에이전트 그리드
  - `dev.css` (120라인): DevBot 콘솔 전용 브랜치 배지, 툴체인 퀵 바, 명령어 칩
  - `responsive.css` (468라인): 모바일/태블릿(`<=768px`, `<=600px`, `<=400px`) 미디어 쿼리 통합
- [x] 메인 `style.css` 오케스트레이터 번들 전환:
  - 3,423라인 ➔ 13라인 `@import url(...)` 선언문으로 전면 개편 (99.6% 경량화)
  - 기존 HTML 템플릿(`<link rel="stylesheet" href="/static/css/style.css">`) 100% 하위 호환성 유지
- [x] 정적 파일 HTTP 200 검증 및 `./scripts/smoke_test.sh` 라이브 검증 완료

### Phase 49: 프론트엔드 자바스크립트(JS) 모듈화 및 모달 컨트롤러 분리 (ADR-050) - ✅ 완료
- [x] 공통 유틸리티 모듈 분리 (`app/static/js/utils/`):
  - `api.js` (114라인): 지수 백오프 네트워크 재시도(`fetchWithRetry`), 헬스체크 및 연결 상태 배너 제어(`window.WatsonAPI`)
  - `date.js` (75라인): KST 기준 날짜 계산, 상대 시간 포맷터, 실시간 디지털 시계 배지 갱신(`window.WatsonDate`)
  - `modal.js` (39라인): 모달 ESC/백드롭 닫기 이벤트, 오픈/클로즈 유틸리티 및 HTML 이스케이프(`window.WatsonModal`)
- [x] 5대 도메인 전용 모달 컨트롤러 분리 (`app/static/js/modules/`):
  - `gtd_modal.js` (124라인): GTD 경로 설정 및 상태 조회 (`window.WatsonGTD`)
  - `schedule_modal.js` (215라인): 브리핑 스케줄 타임라인 및 능동 푸시 트리거 (`window.WatsonSchedule`)
  - `commute_modal.js` (326라인): 지오코딩 자동 매핑, 버스 정류소 역조회, 출근 설정 저장/프리뷰 (`window.WatsonCommute`)
  - `telegram_modal.js` (282라인): 14종 봇 메뉴 명령어 CRUD, 폰 목업 미리보기, 동기화/리셋 (`window.WatsonTelegram`)
  - `editor_modal.js` (317라인): 연간 잔디(Heatmap) 렌더링, 일일 로그 로드, 마크다운 분할 에디터 및 커밋 (`window.WatsonEditor`)
- [x] 메인 스크립트 슬림화 및 DevBot 중복 제거:
  - `main.js`: 1,984라인 ➔ 662라인으로 66.6% 대폭 감축 (세션 관리 및 실시간 채팅 코어 전담)
  - `dev.js`: 중복된 API 재시도 및 실시간 시계 로직을 공통 유틸리티로 대체하여 DRY 원칙 확립
  - `index.html` 및 `dev.html` 스크립트 종속 순서 배치로 번들러 없이 100% 브라우저 네이티브 구동 보장
- [x] 단위 테스트, 정적 타입/린트 검사(`mypy`, `ruff`) 및 `./scripts/smoke_test.sh` 라이브 검증 완료

### Phase 50: 백엔드 라우터 계층 모듈화 리팩터링 (ADR-051) - ✅ 완료
- [x] 4대 도메인 서브 라우터 분할 (`app/routers/`):
  - `chat_router.py` (44라인): 왓슨 대화 및 DevBot 대화 엔드포인트(`POST /api/chat`, `POST /api/dev/chat`)
  - `session_router.py` (72라인): 세션 목록, 히스토리, 변경, 삭제, 비우기 CRUD 엔드포인트
  - `briefing_router.py` (56라인): 맞춤 브리핑, 스케줄 조회, 백그라운드 스케줄러 상태 및 능동 푸시 트리거
  - `lifelog_router.py` (248라인): 마크다운 검색, 주간결산, 사진 비전 분석, 잔디/에디터 파일 입출력, 셋업 상태 진단
- [x] 메인 `web_router.py` 뷰 오케스트레이터 슬림화:
  - 515라인 ➔ 95라인 (81.6% 대폭 감축)
  - HTML 페이지 뷰(`/`, `/watson`, `/dev`) 및 허브/데브 워크스페이스 상태 요약 전담
  - 4개 서브 라우터를 `include_router`로 통합 마운트하여 100% 하위 호환성 유지
- [x] 단위 테스트(`tests/test_web_router.py`), 정적 타입/린트 검사(`mypy`, `ruff`) 및 `./scripts/smoke_test.sh` 40+개 전수 검증 완료

### Phase 51: LLMProvider 및 의도 분석 엔진 모듈화 리팩터링 (ADR-052) - ✅ 완료
- [x] 4대 전용 서브모듈 분할 (`app/services/llm/`):
  - `agy_client.py` (55라인): Antigravity CLI 바이너리 동적 탐색 및 서브프로세스 실행
  - `prompt_builder.py` (90라인): GTD 스킬 행동 강령 주입, 비서 페르소나/대화 맥락 조립 및 스마트 로컬 폴백
  - `category_extractor.py` (85라인): 4대 마크다운 카테고리 추론 및 D-Day 결합 GTD 태스크 추출
  - `intent_analyzer.py` (505라인): 20여 종의 인텐트 분석 엔진 및 IntentResult 데이터클래스 정의
- [x] 메인 `LLMProvider` 경량 파사드(Facade) 슬림화:
  - 1,188라인 ➔ 79라인 (93.3% 대폭 감축)
  - 기존 모든 공개/내부 메서드 시그니처 및 `tests/conftest.py` 모킹 픽스처 100% 하위 호환 보장
- [x] 단위 테스트(`tests/test_llm_provider.py` 13 passed in 0.92s, 관련 테스트 28 passed), 정적 타입/린트 검사(`mypy`, `ruff`) 및 `./scripts/smoke_test.sh` 40+개 전수 검증 완료

### Phase 52: AgentService 라이프로그 및 GTD 오케스트레이션 분리 (ADR-053) - ✅ 완료
- [x] 도메인별 2대 전용 서비스 분리 (`app/services/`):
  - `lifelog_service.py` (260라인): 일일 마크다운 로그(`YYYY-MM-DD.md`) 입출력, KST 타임존 정규화, `[HH:MM]` 타임스탬프 엔트리 서식화, 30자 프리픽스 중복 방지, 당일 로그 마크다운 실시간 읽기 및 GTD 수술적 이관(Surgical Transfer) 수신 전담
  - `gtd_service.py` (420라인): GTD 수집함(`inbox.md`), 다음 행동(`next_actions.md`), 문맥 맞춤형 섹션 라우팅, 키워드/자연어 태스크 물리적 삭제(`remove_gtd_tasks`, `find_and_remove_matching_tasks`), 결정론적 체크박스 완료(`complete_top_task`, `complete_matching_tasks`), GTD 잘라내기(Cut) 및 데일리 로그 이관(Paste) 오케스트레이션, D-Day 마감일 종합 브리핑 전담
- [x] 메인 `AgentService` 오케스트레이터 파사드(Facade) 경량화:
  - 853라인 ➔ 105라인 (87.7% 대폭 감축)
  - `LifelogService`와 `GTDService`를 인스턴스화하고 상호 바인딩하여 순환 참조 없이 완벽 협업 구현
  - 기존 모든 공개/내부 메서드 시그니처(`_normalize_datetime`, `read_gtd_and_daily_log` 등) 및 테스트 픽스처 100% 하위 호환 보장
- [x] 단위 테스트(`tests/test_agent_service.py` 8 passed in 1.61s, 태스크 완료 7 passed), 정적 타입/린트 검사(`mypy`, `ruff`) 및 `./scripts/smoke_test.sh` 40+개 전수 검증 완료

### Phase 53: 슬래시(/) 명령어 팔레트 및 미니멀 입력창 UX 개편 (ADR-054) - ✅ 완료
- [x] 상시 노출 15개 칩 바(`watson-quick-bar`) 전면 철거 및 `[/]` 액션 버튼(`btn-command-palette`) 신설
- [x] 플로팅 글래스모피즘 커맨드 팔레트 컴포넌트(`templates/modals/command_palette.html`) 및 3대 도메인 14종 기능 체계적 그룹화
- [x] 독립 컨트롤러 모듈(`app/static/js/modules/command_palette.js`) 신설:
  - `/` 타이핑 시 실시간 검색 필터링 및 키보드(`↑`/`↓`, `Enter`, `ESC`) 완벽 내비게이션
  - 기존 모달 바인딩 ID(`btn-schedule-view`, `btn-commute-view` 등) 100% 유지로 무수정 연동 보장
- [x] 모바일(`<=768px`) 가로 전폭 확장 및 간결 모드 최적화 (`responsive.css`)
- [x] 정적 파일 전송 검증 및 `./scripts/smoke_test.sh` 40+개 전수 라이브 검증 완료

### Phase 54: DevBot 콘솔 UI 미니멀화 및 인터랙티브 Git 위저드 (ADR-055) - ✅ 완료
- [x] DevBot 콘솔(`/dev`) 입력창 상단의 20개 고정 칩 바(`.dev-quick-bar`) 전면 철거 및 `[/]` 에메랄드 액션 버튼 신설
- [x] DevBot 전용 플로팅 커맨드 팔레트 컴포넌트(`templates/modals/command_palette_dev.html`) 신설:
  - 16대 핵심 엔지니어링 도구 3대 카테고리(Git Ops, Quality & Test, Butler & Tools) 체계화
  - 닫기 버튼, 백드롭 터치, 실시간 / 타이핑 검색 필터링, 방향키 및 Enter 실행 지원
- [x] 범용 `command_palette.js` 컨트롤러 모듈 리팩터링 및 `dev.js` 연동
- [x] 인터랙티브 Conventional Commits 3종(`feat`, `fix`, `refactor`) 추천 카드 및 원클릭 커밋 버튼(`.dev-btn-action.dev-btn-commit`) 구현
- [x] 커밋 성공 시 말풍선 하단 `[🚀 GitHub 원격 푸시 (/push)]` 배너 제공 및 백엔드 `_run_git_push()`, `_run_git_sync()` 명령 핸들러 구현
- [x] 다크 IDE 터미널 박스(`.dev-terminal-box`) 및 안전한 HTML 위젯 렌더러 지원
- [x] 단위 테스트(`tests/test_dev_agent.py`), 린트(`ruff`), 정적 타입 검사(`mypy`) 및 `./scripts/smoke_test.sh` 전수 검증 완료

### Phase 55: 비동기 서비스 제어 스크립트 및 데몬 구동 표준화 (ADR-056) - ✅ 완료
- [x] 통합 비동기 서비스 제어기 `scripts/service.sh` 개발 (`start`, `stop`, `restart`, `status`, `logs`, `install-systemd`)
- [x] 원터치 단축 실행 스크립트 구축 (`scripts/start.sh`, `scripts/stop.sh`, `scripts/restart.sh`, `scripts/status.sh`)
- [x] 포그라운드 직접 실행 방지 방어 가드레일 `app.py` 구축 (호출 시 `./scripts/service.sh start` 비동기 자동 위임)
- [x] systemd 서비스 유닛 파일 경로 표준화 (`systemd/watson.service`) 및 `scripts/setup_wizard.sh` 비동기 안내 최신화
- [x] `AGENTS.md` 및 `README.md` 가이드라인에서 포그라운드 직접 실행 금지 및 비동기 스크립트 사용 강제화

### Phase 56: 웹 기반 자율 코딩 스튜디오 (Web Autonomous Coding Studio)
- [ ] DevBot 웹 콘솔에서 자연어 코드 수정 요청 시 실시간 diff 프리뷰 및 파일 편집 인터페이스
- [ ] 테스트 자동 실행 및 오류 발생 시 자가 치유(Self-Healing) 엔지니어링 루프

### Phase 57: 멀티테넌트(Multi-Tenant) 아키텍처 및 다중 사용자 서비스 (타인 배포 2단계)
- [ ] `User` 모델 및 테넌트별 저장소/컨텍스트 격리 (`/data/tenants/{user_id}/`)
- [ ] 단일 텔레그램 봇 기반 다중 사용자 라우팅 및 계정 바인딩 (`/start [연동코드]`)
- [ ] 사용자 GitHub PAT 및 외부 API 키 AES-256 (Fernet) 암호화 보관
- [ ] 사용자별 타임존 및 출근/브리핑 시각 맞춤형 동적 스케줄러 큐 구축
