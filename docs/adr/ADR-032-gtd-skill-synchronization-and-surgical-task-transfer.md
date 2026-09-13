# ADR-032: GTD 스킬 명세 동기화 및 태스크 완료 시 데일리 로그 수술적 이관 (Surgical Task Transfer)

## 1. Context (배경 및 문제점)
사용자 저장소(`life_log`) 내에 정의된 `skills/gtd-assistant/SKILL.md`는 다음과 같은 원칙을 명시하고 있음:
1. **상태(State)와 시간(Time)의 명확한 역할 분리**:
   - **현재 상태 (SSOT)**: 미완료 할 일은 오직 `gtd/` 디렉토리 내 5개 전용 파일(`inbox.md`, `next_actions.md` 등)에서만 존재.
   - **시간 아카이브 (Daily Logs)**: `logs/daily/YYYY-MM-DD.md`는 당일의 일상 기록(Journaling)과 실제 완료된 작업(`## ✅ 오늘 완료한 일 (Completed GTD Tasks)`)만 모아 보관.
2. **수술적 이동 (Surgical Transfer) 강령**:
   - 사용자가 "완료했어", "끝냈어"라고 할 때, `gtd/` 파일에서 해당 작업 항목을 **잘라내어(Cut)** 제거하고, 오늘 날짜 데일리 로그(`logs/daily/YYYY-MM-DD.md`)의 `## ✅ 오늘 완료한 일 (Completed GTD Tasks)` 섹션에 `- [x]` 형태로 **이동(Paste)**시켜야 함.

그러나 이전 왓슨 구현에서는:
- GTD 파일(`inbox.md`, `next_actions.md`) 내에서 체크박스만 `- [x]`로 변경하고 그대로 방치하여 수집함이 비워지지 않고 데일리 로그에는 반영되지 않는 스킬 명세 위반이 발생함.
- AI 엔진(`agy` CLI) 호출 시 작업 디렉토리(`cwd`)가 `/tmp`로 고정되어 저장소 내 `skills/`를 네이티브 스킬로 인식하지 못하고, 시스템 프롬프트에도 스킬 가이드라인이 주입되지 않았음.

---

## 2. Decision (결정 사항)

### 2.1 결정론적 수술적 이관 (Surgical Transfer) 구현 (`AgentService`)
- `transfer_completed_task_to_daily_log(task_text, date_obj)` 구현:
  - 당일 데일리 로그(`logs/daily/YYYY-MM-DD.md`)가 없을 경우 표준 템플릿으로 자동 생성.
  - `## ✅ 오늘 완료한 일 (Completed GTD Tasks)` 섹션을 탐색하여 `- [x] {task}` 형태로 정제 삽입 (중복 방지 포함).
- `complete_matching_tasks` & `complete_top_task` 고도화:
  - 대상 파일이 `gtd/` 하위 파일인 경우: 해당 파일에서 태스크 라인을 **완전히 잘라내어(Cut)** 삭제 저장하고, 당일 일일 로그로 **이관(Paste)** 집행.
  - 대상 파일이 이미 당일 일일 로그 파일인 경우: 해당 파일 내에서 `- [x]`로 변경.

### 2.2 Antigravity 네이티브 스킬 연동 및 시스템 프롬프트 주입 (`LLMProvider`)
- `LLMProvider` 생성 시 사용자의 `gtd_path`를 주입받아 보관.
- `_load_skill_instructions()`: GTD 경로 내 `skills/gtd-assistant/SKILL.md`의 핵심 규칙(SSOT, Surgical Transfer, Daily Log 아카이빙)을 자동 파싱하여 AI 비서의 시스템 프롬프트에 `[적용 스킬: gtd-assistant]`로 상시 주입.
- `_call_ai_engine()`의 서브프로세스 실행 시 `cwd`를 사용자의 `gtd_path`로 지정하여, Antigravity `agy` CLI가 디렉토리 내의 `skills/` 체계를 네이티브로 발견/로드하도록 보장.

### 2.3 운동 일지 발화와 구어체 태스크 완료의 분리 가드레일
- "오늘 헬스장에서 푸시업 100개 완료", "스쿼트 100kg 완료!" 등 운동 관련 키워드가 포함된 일과 공유는 `task_complete`로 오인되지 않고 운동 라이프로그 초안(`log_suggest`)으로 안전하게 진입하도록 가드레일 보강.

---

## 3. Consequences (영향 및 효과)
1. **스킬 지침 100% 준수**: GTD 수집함(`inbox.md`, `next_actions.md`)에는 오직 미완료 할 일만 깔끔하게 유지되고, 완료된 모든 성과는 당일 일일 로그(`logs/daily/YYYY-MM-DD.md`)의 '오늘 완료한 일' 섹션으로 자동 아카이빙됨.
2. **AI 엔진과 스킬 시스템의 유기적 결합**: AI가 임의로 환각하거나 가상으로 대답하는 대신, 저장소 내 `SKILL.md` 명세를 이해하고 백엔드의 수술적 이동 레이어와 완벽히 동기화되어 작동함.
3. **기존 데이터 정상화**: 사용자 저장소 내 미이관 상태로 남아있던 `민방위 사이버 교육 이수 여부 확인 🛡️💻` 태스크를 `2026-09-13.md`로 수술적 이관 완료.
