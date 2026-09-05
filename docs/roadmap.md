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
Phase 5: 통합 QA, 24시간 서버 배포 및 자동 재시작(systemd/Docker) 구축
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

### Phase 3: 텔레그램 봇 연동 모듈 (Telegram Bot Integration - ADR-006) - 🚀 진행 중
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

### Phase 5: 서버 배포 및 24/7 상시가동 안정화 (ADR-005) - 🚀 진행 중
- [x] `.env.example` 및 환경변수 설정 템플릿 작성
- [x] 경량 멀티아키텍처 `Dockerfile` 및 `docker-compose.yml` 패키징
- [x] SQLite DB 및 마크다운 라이프로그 볼륨 영속화 구성
- [x] systemd 서비스 유닛 파일 (`systemd/watson.service`) 제공
- [x] 원격 서버 배포 및 실행 가이드 문서 작성 (`docs/deployment_guide.md`)
