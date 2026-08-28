# 🚀 AGENTS.md - Watson (프로젝트 관리 시스템) 에이전트 하네스 가이드

본 문서는 Watson(파이썬 기반 프로젝트 관리 웹사이트) 애플리케이션의 개발 하네스 규칙, 기술 스택, 핵심 제약사항을 정의하는 최고 지침서입니다. (100줄 이내 유지)

---

## 🤖 0. Agent Rules for Watson

### Summary
AI 에이전트가 코드를 작성, 수정, 검증할 때 준수해야 하는 최우선 하네스(Harness) 규칙입니다. (프로젝트 오너십 및 실행 책임은 본 하네스 규칙에 전적으로 위임되어 있으며, 사용자는 진행상황 트래킹을 담당합니다.)

### 1. Essential Commands (수행 명령어)
* **의존성 설치**: `pip install -r requirements.txt` (또는 `poetry install`)
* **개발 서버 실행**: `python app.py` (또는 `uvicorn app.main:app --reload`)
* **단위 및 스모크 테스트**: `pytest`
* **단일 파일 테스트**: `pytest tests/test_file.py`
* **타입 검사 및 코드 린트**: `mypy . && ruff check .`

### 2. Hard Constraints (필수 준수 규칙)
* **Role-Based Product Pipeline (역할 기반 7단계 QA 피드백 파이프라인)**: 모든 요청은 `[1.기획자 UX기획 ➔ 2.디자이너 UI설계 ➔ 3.법적 적법성 검토 ➔ 4.기획서/Spec 업데이트 ➔ 5.PM 일정/스펙 확정 ➔ 6.개발자 구현 ➔ 7.QA 테스트 검증 및 피드백 루프]` 순서로 엄격히 검토 및 집행할 것.
* **Spec-Code Alignment (기획-코드 100% 동기화)**: 모든 기획 문서(`docs/PRD.md`, `docs/requirements.md`, `docs/roadmap.md`)와 구현 코드는 항상 100% 완벽히 일치해야 함.
* **Self-Verification Loop**: 모든 코드 수정 후 반드시 `pytest` 및 `mypy`/`ruff`를 직접 실행하여 Pass를 검증할 것.
* **Self-Critique Loop & Design Audit Loop**: 기획자 자가 질문 및 UI/UX 디자이너의 자가 디자인 감사 루프(여백미, 모던 글래스모피즘, 컬러 대비, 마이크로 인터랙션)를 상시 작동할 것.
* **의사결정 기록 (ADR 필수)**: 유저 피드백 및 주요 설계 변경 시 맥락과 사유를 정리한 의사결정 문서(`docs/adr/ADR-xxx.md`)를 작성할 것.
* **안전한 롤백 체크포인트**: 대규모 작업 전 Git 태그/체크포인트를 먼저 생성한 후 진행할 것.

### 3. Project Gotchas & Edge Cases (주의사항)
* **프로젝트/태스크 상태 및 DB 마이그레이션**:
  * DB 스키마 변경 시 Alembic/SQLAlchemy 마이그레이션을 명확히 관리하고 테스트할 것.
  * 프로젝트 상태(진행중/완료/보류) 및 태스크 진행률 연산 시 N+1 쿼리 문제 방지 및 데이터 일관성 검증.
* **파이썬 웹 API 및 에러 처리**:
  * 데이터베이스 세션 Leak 방지 (Context Manager 또는 DI 구조 준수).
  * 프론트엔드 연동/템플릿 렌더링 시 4xx/5xx 에러 예외 처리 및 사용자 친화적 Fallback UI 분기 유지.

### 4. Progressive Disclosure (상세 문서 참조)
* **제품 기획서 개요 (PRD Index)**: `docs/PRD.md`
* **기능 요구사항 명세서**: `docs/requirements.md`
* **의사결정 문서 (ADR 목록)**: `docs/adr/`
* **UI/UX 디자이너 스킬 가이드**: `.gemini/skills/ux-designer/SKILL.md`
* **개발 로드맵 & 백로그**: `docs/roadmap.md`

---

## 🛠 1. 기술 스택 & 프로젝트 구조 요약

* **Tech Stack**: Python (v3.10+), FastAPI / Flask, SQLAlchemy, SQLite / PostgreSQL, Jinja2 / HTML5 / CSS3 / JS, pytest, mypy, ruff
* **Project Structure**: `app/` (또는 `src/`), `app/models/`, `app/routers/` (또는 `views/`), `app/services/`, `app/templates/`, `app/static/`, `tests/`, `docs/adr/`
