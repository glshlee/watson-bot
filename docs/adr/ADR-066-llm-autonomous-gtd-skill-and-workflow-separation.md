# ADR-066: 파이썬 자연어 인텐트 분류기 전면 철거 및 순수 LLM 에이전트 자율 위임 (Pure Agent Delegation & Intent Classifier Removal)

## 1. 배경 및 문제 정의 (Context & Problem)
* 기존 코드에서는 `prompt_builder.py`에 `[INTENT: ...]` 태그 메뉴판과 340여 줄의 `get_smart_fallback()` 정규식 분류기가 존재하고, `intent_analyzer.py`에서 `_parse_llm_intent_result()`로 LLM 응답에서 인텐트를 추출하여 파이썬(`supervisor_service.py`)이 분기 처리를 수행했습니다.
* 이로 인해 사용자가 *"일정을 someday로 이동시켜달라"*거나 복합적인 자연어 지시를 내렸을 때, 파이썬이 미리 정의해 둔 좁은 인텐트 목록에 맞추려다 보니 **엉뚱한 현황 브리핑(`task_briefing`)으로 오분류**되는 구조적 한계가 발생했습니다.
* 이미 `agy` CLI 에이전트가 GTD 작업 디렉토리(`cwd=gtd_path`)와 `.agents/skills/gtd-assistant/SKILL.md`를 기반으로 파일을 읽고 편집할 수 있으므로, 파이썬이 중간에서 자연어 의도를 분류할 이유가 없습니다.

## 2. 결정 사항 (Decision)
1. **파이썬 자연어 인텐트 분류기 전면 철거 (`prompt_builder.py`, `intent_analyzer.py`)**:
   * `prompt_builder.py`에서 `[INTENT: ...]` 태그 출력 강제 프롬프트와 340여 줄의 자연어 정규식 폴백 분류기를 전면 삭제했습니다.
   * `intent_analyzer.py`에서 `_parse_llm_intent_result()`를 제거하고, 슬래시(`/`)로 시작하지 않는 **모든 자연어 입력은 파이썬 인텐트 분류 없이 100% LLM(`call_ai_engine_func`)에 직결**하여 에이전트의 응답을 그대로 반환합니다.
2. **`gtd-assistant/SKILL.md` 원문 전체 동적 주입 (`load_skill_instructions`)**:
   * 하드코딩된 3줄 요약을 제거하고, 연결된 GTD 저장소의 `.agents/skills/gtd-assistant/SKILL.md` 원문 전체(5대 상태 파일: `inbox.md`, `next_actions.md`, `waiting_for.md`, `someday_maybe.md`, `projects.md`)를 시스템 프롬프트에 그대로 주입합니다.
3. **파이썬의 역할 축소 (슬래시 숏컷 + `git status` 사후 워크플로우)**:
   * 파이썬(`SupervisorService`)은 오직 ① 명시적 `/` 슬래시 명령어 패스트트랙, ② 세션 히스토리 관리, ③ LLM 실행 전후 `git_service.get_dirty_files()` 비교를 통한 로컬 파일 변경 감지 및 커밋/푸시 워크플로우만 담당합니다.

## 3. 결과 및 영향 (Consequences)
* `prompt_builder.py`와 `intent_analyzer.py`에서 약 600줄의 인텐트 분류/파싱 레거시 코드가 제거되어 구조가 극도로 단순해졌습니다.
* 자연어 요청 시 파이썬의 오분류(현황 브리핑 오탐 등)가 원천적으로 불가능해지고, LLM이 `SKILL.md`에 따라 `someday_maybe.md` 이동 등을 자율적으로 수행합니다.
