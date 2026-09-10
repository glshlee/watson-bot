# 🚀 AGENTS.md - Watson 범용 에이전트 하네스 마스터 가이드

본 문서는 Watson(24/7 가동 GitHub LifeLog AI Agent) 애플리케이션의 범용 개발 하네스 규칙, 아키텍처 패턴, 기술 스택, 핵심 제약사항을 정의하는 최고 지침서입니다. (100줄 이내 유지)

---

## 🤖 0. Vendor-Agnostic Agent Harness Architecture

본 하네스는 특정 AI 플랫폼에 종속되지 않고 Antigravity, Gemini, Claude, OpenAI 등 모든 AI 엔진에서 완벽히 작동하는 **`.agents/` 범용 하네스 표준**을 준수합니다.

### 1. Essential Commands (수행 명령어)
* **의존성 설치**: `pip install -r requirements.txt` (또는 `poetry install`)
* **개발 서버 실행**: `python app.py` (또는 `uvicorn app.main:app --reload`)
* **단위 및 스모크 테스트**: `pytest`
* **cURL 라이브 API 검증 (필수)**: `./scripts/smoke_test.sh` (또는 `curl -X POST "http://localhost:8000/api/chat" ...`)
* **타입 검사 및 코드 린트**: `mypy . && ruff check .`

### 2. Multi-Agent & Skill System (.agents/)
* **서브 에이전트 분담 (`.agents/agents/`)**:
  * `supervisor.md`: [감독자] 유저 요청 수신, 세션 맥락 연결 및 작업 오케스트레이션
  * `lifelog_generator.md`: [생성자] 비정형 메모 ➔ 마크다운 라이프 로그 파싱 & 작성
  * `git_worker.md`: [작업자] Git Pull/Commit/Push 및 예외 롤백 처리
  * `spec_verifier.md`: [검증자] 마크다운 템플릿 및 PRD 명세 무결성 검증
* **모듈형 스킬 (`.agents/skills/`)**:
  * `git-automation/SKILL.md`: Git 커밋/푸시 및 충돌 복구 스킬
  * `session-memory/SKILL.md`: 텔레그램/웹 대시보드 대화 세션 맥락 관리 스킬
  * `markdown-lifelog/SKILL.md`: 마크다운 템플릿 변환 및 Append/Edit 스킬
* **하네스 진화 및 동기화 규칙 (`.agents/rules/`)**:
  * `evolution.md`: 💡 실행 실패 시 ADR 작성 및 하네스/스킬 자동 업그레이드 규칙
  * `spec_alignment.md`: 기획-코드 100% 동기화 및 cURL 검증 루프 규칙

### 3. Hard Constraints (필수 준수 규칙)
* **Spec-Code & README Alignment**: 모든 기획 문서(`docs/PRD.md`, `docs/requirements.md`, `docs/roadmap.md`) 및 사용자 안내서(`README.md`)와 구현 코드는 100% 일치할 것.
* **4단계 문서화 & README 상시 갱신 의무화 (Mandatory Documentation & README Loop)**: 사용자 피드백이나 아키텍처/기능/정책 변경 시 반드시 ① `docs/adr/ADR-xxx.md` 작성 ➔ ② PRD/요구사항/로드맵 동기화 ➔ ③ `README.md` 사용법/아키텍처/배포 가이드 갱신 ➔ ④ `AGENTS.md` 갱신을 완료할 것. 기능 추가나 변경 시 `README.md` 업데이트는 선택이 아닌 필수 의무임.
* **스마트 비서 & 1기록 1커밋 정책 (ADR-004)**: 일반 대화(잡담/질문)는 세션에만 보관하고 Git 커밋하지 않음. 비서가 일과/기록 가치를 감지해 제안하고, 사용자가 승인("응", "좋아")하거나 직접 명령(`/log`)한 확정된 라이프로그에 한해서만 즉시 마크다운 반영 및 Git 커밋(1기록 1커밋)을 수행할 것.
* **GTD 저장소 격리 및 외부 체계 오케스트레이션 (ADR-007)**: 왓슨 소스코드 레포와 개인 데이터(GTD/라이프로그)를 분리하고, 웹 UI/설정으로 지정된 GTD 경로의 기정의 체계(`inbox.md`, `logs/daily/` 등)를 존중하여 오케스트레이션하며 독립 Git 커밋 수행.
* **GTD 지능형 브리핑 & AGY CLI 자동 감지 (ADR-008)**: 할 일/일정 정리 요청 시 연결된 GTD 저장소에서 데일리 로그 및 Next Actions를 종합 브리핑하며, Linux 서버 환경에서도 AGY 바이너리를 동적 탐색하여 살아있는 비서 대화를 제공할 것.
* **GTD 원격 동기화 & 온디맨드 최신화 (ADR-009)**: "gtd 최신화", "레포 최신화", "/sync" 요청 시 원격 GitHub로부터 git pull(--autostash)을 수행하고, 브리핑 요청 시에도 최신 상태를 자동 반영하여 다중 기기 환경의 일관성을 보장할 것.
* **대화 맥락 참조 기록 & 고탄력 AI (ADR-010)**: "아까 말한 내용 기록해줘" 등 이전 대화 참조 시 히스토리 역추적으로 원문을 추출해 즉시 기록하고, AGY 프롬프트 경량 요약 및 50초 타임아웃으로 맥락 단절을 방지할 것.
* **결정론적 원격 푸시 & Headless 무중단 실행 (ADR-011)**: "푸시해줘", "/push" 등 푸시 명령 시 LLM 환각을 차단하고 백엔드 Git Push를 실행하며, autostash로 병합 충돌 방지 및 AGY headless 권한 오류를 원천 차단할 것.
* **테스트 샌드박스 격리 & 지시어 문맥 역추적 (ADR-012)**: 스모크 테스트 실행 시 임시 GTD 샌드박스로 격리하여 사용자 저장소 오염을 원천 차단하고, "응 오늘 로그에 기록해줘" 등 순수 지시어 시 지시어 텍스트 오인을 방지하며 직전 사연을 역추적 기록할 것.
* **KST 타임존 로컬라이제이션 (ADR-013)**: 일일 로그 경로(`YYYY-MM-DD.md`), 기록 타임스탬프(`[HH:MM]`), 커밋 일자 및 상태 표시는 기본 한국 표준시(`Asia/Seoul`)로 엄격 정규화하여 자정 경계 결함을 원천 차단할 것.
* **복합 의도 감지 & GTD 태스크 정제 (ADR-014)**: "로그와 gtd에 기록해줘" 등 복합 요청 시 데일리 로그(서사 일기)와 GTD 인박스(정제된 액션 태스크)에 동시 기록하며, 지시어 접미사 누출을 차단하고 1회 원자적 Git 커밋을 집행할 것.
* **웹 보안 인증 & Cloudflare Tunnel (ADR-015)**: 외부 접속 시 HTTP Basic 인증으로 일기/GTD 무단 접근을 원천 차단하고, 포트 개방 없는 Cloudflare Tunnel(자동 HTTPS)로 안전한 무중단 터널링을 보장할 것.
* **모바일 퍼스트 반응형 웹 UX (ADR-016)**: 스마트폰 화면(<=768px)에서 사이드바를 오프캔버스 슬라이드 드로어로 자동 전환하고, 100dvh 뷰포트, iOS Safe Area, 사파리 줌 방지(16px) 및 터치 친화적 액션 컴포넌트를 보장할 것.
* **웹 세션 관리 고도화 & 스마트 네이밍 (ADR-017)**: 웹 콘솔에서 세션 실시간 검색 및 채널 필터(`전체`/`웹`/`텔레그램`), 제목 변경/삭제/비우기 CRUD, 활성 세션 삭제 시 인접 세션 안전 폴백 및 첫 발화 기반 스마트 자동 네이밍을 보장할 것.
* **에이전트 허브 포털 & 개발 에이전트 분리 (ADR-018)**: 루트 경로(`/`)에 에이전트 허브 대시보드를 제공하고, 왓슨 비서(`/watson`)와 개발 전담 DevBot(`/dev`)을 독립 라우팅 및 `agent_type` 세션 격리로 분리 운영할 것.
* **DevBot 대화형 엔지니어링 툴체인 (ADR-019)**: DevBot 콘솔(`/dev`)에서 터미널 없이 `/test`(단위 테스트), `/lint`(Ruff & Mypy 정적 검사), `/commit`(Conventional Commits 3종 추천/원터치 커밋)을 즉시 실행하고, `docs/roadmap.md` 마일스톤 주입 및 안전 프로세스 격리로 시니어 페어 프로그래밍 대화를 제공할 것.
* **결정론적 GTD 태스크 제거 & 원격 투명성 (ADR-020)**: 태스크 삭제 요청 시 LLM 구두 시뮬레이션을 차단하고 `inbox.md`/`next_actions.md`에서 물리적 마크다운 삭제 및 즉시 커밋·푸시를 집행하며, "커밋해", "푸시도해야지", "어디다 푸시한거야?" 등 자연어 커밋/푸시 질의에 실제 Git 원격 상태(URL, 브랜치, 해시)를 투명 보고할 것.
* **웹 연결 복원력 & HTTP/2 터널 안정화 (ADR-021)**: Cloudflare Tunnel을 TCP HTTP/2로 고정하여 유휴 드롭을 방지하고, Uvicorn Keep-Alive(75s) 및 초경량 헬스체크(/api/health)를 제공하며, 웹 콘솔 자동 재시도 및 모바일 화면 복귀 시 세션 히스토리 자동 복원을 보장할 것.
* **Explicit User Commit Trigger Only (에이전트 코드 커밋 수칙)**: 코드 수정 및 기능 구현 후 Git 커밋(`git commit`)은 에이전트가 임의로 자동 실행하지 않으며, 오직 **사용자가 명시적으로 "커밋해" 지시를 내렸을 때만** 수행할 것.
* **Curl-Based Live Verification (필수)**: 모든 코드 수정 후 반드시 `./scripts/smoke_test.sh` cURL 테스트를 실행하여 실제 라이브 API 수신 및 500 에러 부재를 검증할 것.
* **Self-Verification & Evolution Loop**: 코드 변경 시 `pytest`/`mypy`/`ruff` 및 cURL 검증 수행 후 실패 시 `evolution.md` 지침에 따라 하네스 자가 진화 집행.

### 4. Progressive Disclosure (상세 문서 참조)
* **제품 기획서 개요**: `docs/PRD.md` | **기능 요구사항**: `docs/requirements.md`
* **개발 로드맵 & 백로그**: `docs/roadmap.md` | **ADR 목록**: `docs/adr/` (ADR-001 ~ ADR-021)


---

## 🛠 1. 기술 스택 & 프로젝트 구조 요약

* **Tech Stack**: Python (v3.10+), FastAPI, SQLAlchemy, SQLite, Jinja2/HTML5/CSS3/JS, pytest, mypy, ruff
* **Project Structure**: `.agents/`, `app/` (`models/`, `services/`, `routers/`, `templates/`, `static/`), `scripts/`, `tests/`, `docs/`
