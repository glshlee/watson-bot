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
* **Spec-Code Alignment**: 모든 기획 문서(`docs/PRD.md`, `docs/requirements.md`, `docs/roadmap.md`)와 구현 코드는 100% 일치할 것.
* **Explicit User Commit Trigger Only (명시적 사용자 커밋 수칙)**: 코드 수정 및 기능 구현 후 Git 커밋(`git commit`)은 에이전트가 임의로 자동 실행하지 않으며, 오직 **사용자가 명시적으로 "커밋해" 지시를 내렸을 때만** 수행할 것.
* **Curl-Based Live Verification (필수)**: 모든 코드 수정 후 반드시 `./scripts/smoke_test.sh` cURL 테스트를 실행하여 실제 라이브 API 수신 및 500 에러 부재를 검증할 것.
* **Self-Verification & Evolution Loop**: 코드 변경 시 `pytest`/`mypy`/`ruff` 및 cURL 검증 수행 후 실패 시 `evolution.md` 지침에 따라 하네스 자가 진화 집행.
* **의사결정 기록 (ADR 필수)**: 유저 피드백 및 설계 변경 시 `docs/adr/ADR-xxx.md` 작성.

### 4. Progressive Disclosure (상세 문서 참조)
* **제품 기획서 개요**: `docs/PRD.md` | **기능 요구사항**: `docs/requirements.md`
* **개발 로드맵 & 백로그**: `docs/roadmap.md` | **ADR 목록**: `docs/adr/`

---

## 🛠 1. 기술 스택 & 프로젝트 구조 요약

* **Tech Stack**: Python (v3.10+), FastAPI, SQLAlchemy, SQLite, Jinja2/HTML5/CSS3/JS, pytest, mypy, ruff
* **Project Structure**: `.agents/`, `app/` (`models/`, `services/`, `routers/`, `templates/`, `static/`), `scripts/`, `tests/`, `docs/`
