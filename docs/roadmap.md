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

### Phase 2: 코어 파이썬 백엔드 & Git 서비스
- [ ] 파이썬 프로젝트 구조 (`app/`, `config.py`, `requirements.txt`) 세팅
- [ ] 세션 및 대화 컨텍스트 영속성 모듈 (`app/services/session_service.py` & SQLite DB) 구현
- [ ] Git 자동화 모듈 (`app/services/git_service.py`) 작성: pull, commit, push, conflict handling
- [ ] AI 마크다운 파서 및 템플릿 생성기 (`app/services/agent_service.py`) 구현
- [ ] 기본 Pytest 단위 테스트 모듈 작성 및 통과 검증

### Phase 3: 텔레그램 봇 연동 모듈
- [ ] Telegram Bot API 수신 및 사용자 화이트리스트 검증 모듈 (`app/bot/telegram_bot.py`)
- [ ] 텍스트/이미지 메시지 ➔ AI 에이전트 연동 ➔ Git Push 자동 연동
- [ ] 텔레그램 명령어 (`/start`, `/log`, `/status`, `/help`) 파싱 구현

### Phase 4: 웹 대시보드 (Watson Web Dashboard)
- [ ] FastAPI 기반 라우터 및 HTML Jinja2/Vanilla CSS 템플릿 구성
- [ ] 라이프 로그 캘린더 뷰 및 마크다운 랜더링 페이지 구현
- [ ] 웹 대시보드 내 대화형 AI Agent 인터페이스 개발
- [ ] 모바일/대형 화면 반응형 Glassmorphism UI 구현

### Phase 5: 서버 배포 및 24/7 상시가동 안정화
- [ ] `.env.example` 및 환경변수 설정 가이드 작성
- [ ] systemd 서비스 등록 파일 (`watson.service`) 또는 Dockerfile 작성
- [ ] 전체 스모크 테스트 및 24시간 서버 배포 검증
