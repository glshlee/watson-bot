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







