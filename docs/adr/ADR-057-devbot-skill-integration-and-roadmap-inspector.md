# ADR-057: DevBot 하네스 개발 스킬 연동 및 로드맵 인스펙터 (DevBot Harness Skill Integration & Roadmap Inspector)

## 1. 개요 (Context)
* **배경**:
  * Watson 시스템은 `.agents/skills/` 디렉토리에 정의된 범용 하네스 스킬(`git-automation`, `markdown-lifelog`, `session-memory`) 체계를 갖추고 있다.
  * 기존 DevBot(개발 전담 에이전트 콘솔)은 Git 명령어 및 터미널 툴체인을 지원했으나, 하네스 스킬을 동적으로 탐색하거나 개발 워크플로우에 직접 연동하는 메커니즘이 부재했다.
  * 또한, 개발 진행 상황과 마일스톤 백로그를 담은 `docs/roadmap.md` 문서가 존재하지만, DevBot 콘솔에서 로드맵 진척도와 예정 마일스톤을 실시간으로 열람하거나 점검할 수 있는 명령어나 UI가 없었다.
* **사용자 요구사항**:
  * 데브봇에서 현재 보유한 스킬을 사용해 개발을 수행할 수 있도록 연동할 것.
  * 개발 로드맵을 DevBot 콘솔에서 한눈에 볼 수 있도록 만들 것.

---

## 2. 의사결정 (Decision)

### 2.1 표준 개발 스킬(`dev-workflow`) 신설 및 하네스 스킬 동적 연동
1. **표준 개발 스킬 신설 (`.agents/skills/dev-workflow/SKILL.md`)**:
   * 소프트웨어 엔지니어링 7단계 파이프라인(요구사항 분석 ➔ TDD 단위테스트 ➔ 수술적 코드 구현 ➔ 정적 린트/타입 검사 ➔ cURL 라이브 검증 ➔ 4단계 필수 문서화 루프 ➔ Conventional Commits 제안 및 명시적 사용자 커밋 대기)을 규정.
2. **동적 스킬 탐색기 (`get_available_skills()`)**:
   * `.agents/skills/` 디렉토리 내 모든 `SKILL.md`를 동적 파싱하여 YAML Frontmatter(이름, 설명) 및 전문을 구조화된 데이터로 추출.
3. **스킬 카탈로그 및 상세 열람 서식화 (`format_skills_catalog()`)**:
   * `/skills`: 등록된 전체 개발 스킬 목록 및 인터랙티브 상세 열람 버튼 카드 렌더링.
   * `/skill <스킬명>` (예: `/skill dev-workflow`): 해당 스킬의 전체 마크다운 가이드와 후속 액션 툴체인 버튼 제공.
4. **DevBot LLM 프롬프트 스킬 주입**:
   * 자연어 코딩 요청 수신 시 `dev_system_prompt`에 보유 스킬 요약과 `dev-workflow` 7단계 준수 강령을 주입하여, 일관되고 체계적인 시니어 엔지니어링 답변을 보장.

### 2.2 개발 로드맵 분석 엔진 및 인스펙터 구축
1. **로드맵 파서 (`parse_roadmap_data()`)**:
   * `docs/roadmap.md`를 실시간 파싱하여 전체 Phase 수, 완료 Phase 수, 진행률(%), 10칸 텍스트 진행바(`[██████████ 96.4%]`), 진행 중/예정 마일스톤(Active & Upcoming), 최근 완료 하이라이트(Recent Completed)를 계산.
2. **로드맵 리포트 서식화 (`format_roadmap_report()`)**:
   * `/roadmap` (및 별칭 `/로드맵`, "개발 로드맵", "마일스톤"): 진척도 요약, 예정 마일스톤, 최근 완료 마일스톤 및 툴체인 빠른 액션 버튼을 대화형 카드로 제공.

### 2.3 REST API 및 프론트엔드 UI 연동
1. **REST API 엔드포인트 (`app/routers/web_router.py`)**:
   * `GET /api/dev/roadmap`: 구조화된 로드맵 통계 및 렌더링된 마크다운 제공.
   * `GET /api/dev/skills`: 전체 스킬 카탈로그 목록 및 요약 제공.
   * `GET /api/dev/skills/{skill_name}`: 특정 스킬의 상세 명세 반환 (404 예외 처리 포함).
2. **DevBot 콘솔 UI & 커맨드 팔레트 확장**:
   * `templates/dev.html`: 상단 헤더에 `[🗺️ 로드맵]`(`#btn-dev-roadmap-quick`) 및 `[🧩 스킬]`(`#btn-dev-skills-quick`) 원터치 액션 배지 신설.
   * `templates/modals/command_palette_dev.html`: `/roadmap` 및 `/skills` 항목 추가, 툴체인 뱃지 16개 ➔ 18개로 갱신.
   * `app/static/js/dev.js`: 헤더 퀵 버튼 및 카드 내 `data-cmd` 이벤트 핸들러 바인딩.

---

## 3. 구현 세부사항 (Implementation)

| 파일 | 역할 및 변경 내용 |
| :--- | :--- |
| `.agents/skills/dev-workflow/SKILL.md` | 표준 엔지니어링 7단계 파이프라인 및 하네스 개발 규약 스킬 신설 |
| `app/services/dev_agent_service.py` | `get_available_skills`, `format_skills_catalog`, `parse_roadmap_data`, `format_roadmap_report` 구현, `/roadmap`, `/skills`, `/skill` 라우팅 및 LLM 프롬프트 스킬 주입 |
| `app/routers/web_router.py` | `GET /api/dev/roadmap`, `GET /api/dev/skills`, `GET /api/dev/skills/{skill_name}` REST API 추가 |
| `app/templates/modals/command_palette_dev.html` | `/roadmap`, `/skills` 항목 신설 및 18종 도구 팔레트 갱신 |
| `app/templates/dev.html` | 상단 헤더에 로드맵 및 스킬 원터치 퀵 버튼 추가 |
| `app/static/js/dev.js` | 로드맵 및 스킬 퀵 버튼 클릭 핸들러 및 명령어 전송 바인딩 |
| `app/static/css/dev.css` | `.dev-action-badge` 및 팔레트 아이콘 악센트 스타일링 추가 |
| `tests/test_dev_agent.py` | `/roadmap`, `/skills`, `/skill`, REST API 엔드포인트 4종 전수 테스트 추가 |
| `scripts/smoke_test.sh` | 8-5 ~ 8-8 cURL 라이브 API 검증 단계 추가 |

---

## 4. 검증 결과 (Verification)
1. **단위 테스트 (`pytest`)**:
   * `tests/test_dev_agent.py` 4개 테스트 100% 통과 (7.39초).
   * 전체 테스트 스위트 134개 전수 통과 (27.10초).
2. **정적 린트 및 타입 검사 (`ruff`, `mypy`)**:
   * `ruff check .` 무결점 통과.
   * `mypy app/` 41개 소스 파일 타입 안정성 100% 검증 통과.
3. **cURL 라이브 스모크 테스트 (`scripts/smoke_test.sh`)**:
   * DevBot `/roadmap`, `/skills`, `GET /api/dev/roadmap`, `GET /api/dev/skills` 포함 전체 45+개 항목 정상 통과 (Exit 0).
