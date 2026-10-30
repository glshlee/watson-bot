# ADR-066: LLM 자율 GTD 스킬 위임 및 파이썬 워크플로우 경계 분리 (Autonomous GTD Skill Delegation & Workflow Separation)

## 1. 배경 및 문제 정의 (Context & Problem)
* 기존 구조에서는 사용자가 *"일정을 someday로 이동시켜줘"*와 같이 GTD 상태 파일 간 이동(`inbox.md` / `next_actions.md` ➔ `someday_maybe.md` / `waiting_for.md`)이나 문맥 기반 분류(Clarify)를 요청했을 때, 다음과 같은 구조적 한계로 인해 **현황 브리핑(`task_briefing` / `gtd_inspect`)이 잘못 출력되는 문제**가 발생했습니다:
  1. `app/services/llm/prompt_builder.py`의 `load_skill_instructions()`가 GTD 저장소 내 `.agents/skills/gtd-assistant/SKILL.md`의 실제 본문(5대 상태 파일: `inbox.md`, `next_actions.md`, `waiting_for.md`, `someday_maybe.md`, `projects.md`)을 읽지 않고 하드코딩된 3줄 요약만 주입했습니다.
  2. 시스템 프롬프트가 LLM(`agy` 에이전트)의 직접 파일 조작을 금지하고 좁은 `[INTENT: ...]` 메뉴판만 강제했는데, 정작 메뉴판과 `GTDService`에는 상태 간 이동(`gtd_move`)이 정의되어 있지 않아 LLM이 차선책으로 `task_briefing`을 출력했습니다.
* 근본적으로 **자연어 의도 파악 및 마크다운 내용/상태 조작은 LLM(및 `gtd-assistant` 스킬)에 맡기고, 파이썬 백엔드는 세션·슬래시 패스트트랙·외부 API·Git 커밋/푸시 워크플로우만 오케스트레이션**해야 합니다.

## 2. 결정 사항 (Decision)
1. **`SKILL.md` 원문 동적 주입 (`load_skill_instructions`)**:
   * 하드코딩된 3줄 요약을 제거하고, 연결된 GTD 저장소의 `.agents/skills/gtd-assistant/SKILL.md` (또는 `skills/gtd-assistant/SKILL.md`) 원문 전체를 시스템 프롬프트에 직접 주입하여 LLM이 5대 GTD 파일 구조와 분류(Clarify) 규칙을 100% 인지하도록 합니다.
2. **LLM 자율 파일 조작 허용 및 `git status` 변경 감지 (`SupervisorService`)**:
   * `build_system_prompt()`에서 LLM(`agy`, `cwd=gtd_path`)이 사용자의 자연어 GTD 분류/이동/정리 요청 시 `SKILL.md`에 따라 마크다운 파일을 직접 읽고 수정할 수 있도록 제약을 해제합니다(단, `git commit`/`git push`는 파이썬 워크플로우가 전담).
   * `SupervisorService.process_user_request()`는 LLM 실행 전후의 `git_service.get_dirty_files()` 차집합(`llm_modified_files`)을 감지하여, LLM이 직접 마크다운 파일을 수정한 경우에도 로컬 변경 상태(`filepath`)와 로컬 우선/자동 백업 워크플로우(ADR-064)를 일관되게 연결합니다.
3. **GTD 상태 간 이동 워크플로우 (`GTDService.move_gtd_tasks` & `gtd_move`) 신설**:
   * 결정론적 폴백 및 태그 연동(`[INTENT: gtd_move target="..." to="someday|waiting|next_actions|inbox"]`)을 위해 `GTDService.move_gtd_tasks()`를 구현하여 `inbox.md`, `next_actions.md`, `waiting_for.md`, `someday_maybe.md`, 당일 일일 로그 간 항목 이동(Cut & Paste)을 지원합니다.
   * `/gtd` 조회(`read_gtd_files`) 시에도 `someday_maybe.md` 현황을 함께 표시합니다.

## 3. 결과 및 영향 (Consequences)
* *"~ 일정을 someday로 이동시켜줘"*, *"~를 대기(waiting)로 옮겨줘"* 등의 자연어 GTD 분류 요청 시 더 이상 엉뚱한 현황 브리핑이 출력되지 않고, `gtd/someday_maybe.md` 등 목적지 상태 파일로 정확히 이동·반영됩니다.
* 파이썬 백엔드는 인프라/워크플로우에 집중하고, 자연어 맥락 이해와 GTD 스킬 실행은 LLM이 주도하는 역할 분담이 확립되었습니다.
