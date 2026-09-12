# ADR-027: 텔레그램 인터랙티브 인라인 키보드 및 원클릭 태스크 조작 (Telegram Interactive Inline Keyboards & Task Operations)

## 1. Context (배경 및 문제점)
사용자 피드백: *"1번(텔레그램 인라인 키보드)과 5번(웹 캘린더) 좋다"*
1. **타이핑 없는 즉각적 모바일 제어 필요성**:
   - ADR-026을 통해 매일 08:30(아침)과 20:00(저녁) 텔레그램으로 브리핑이 자동 푸시 발송되지만, 받은 브리핑에 대응하려면 사용자가 직접 텍스트를 타이핑해야 하는 모바일 UX 병목이 존재했다.
2. **GTD 태스크 완료(`- [x]`) 상태 전이 요구**:
   - 기존에는 태스크를 완전히 지우는 `gtd_remove` 기능만 있었으며, GTD 방법론의 핵심인 "1순위 태스크 완료 체크(`- [ ]` ➔ `- [x]`)" 및 커밋/푸시 파이프라인이 정립되지 않았다.
3. **텔레그램 콜백 쿼리(`callback_query`)의 단편성**:
   - 기존 인라인 키보드는 단순 일과 기록 제안 승인/거절(`confirm_log`, `reject_log`)에만 한정되어 있어, 브리핑에 대한 후속 액션(동기화, 완료, 푸시, 할 일 열람, 일기 작성)을 터치 한 번으로 처리할 수 없었다.

## 2. Decision (결정 사항)

### 2.1 텔레그램 브리핑 인터랙티브 인라인 키보드 규격 (`TelegramService.get_briefing_keyboard`)
- **🌅 아침 브리핑 (08:30 KST)** 인라인 키보드:
  - `[✅ 1순위 태스크 완료]` (`callback_data: "task_done_top1"`): 가장 시급한 Top 1 태스크를 즉시 완료 체크하고 Git 커밋/푸시.
  - `[🔄 GTD 동기화]` (`callback_data: "action_sync"`): 원격 GitHub 저장소로부터 최신 상태 동기화(`git pull --autostash`).
  - `[📋 전체 할 일 보기]` (`callback_data: "action_show_tasks"`): 오늘 일일 로그 및 GTD 현황 즉시 브리핑.
  - `[🚀 원격 푸시]` (`callback_data: "action_push"`): 로컬 라이프로그 및 GTD 커밋을 원격 저장소로 안전 푸시.
- **🌇 저녁 일과 회고 (20:00 KST)** 인라인 키보드:
  - `[📝 오늘 일기 작성]` (`callback_data: "action_prompt_diary"`): 하루를 돌아보는 일기 작성 가이드 안내 및 세션 연결.
  - `[🔄 GTD 동기화]` (`callback_data: "action_sync"`): 퇴근 전 원격 저장소 동기화.
  - `[🚀 오늘 기록 푸시]` (`callback_data: "action_push"`): 오늘 작성된 일기 및 태스크 전체를 GitHub에 푸시.
  - `[📋 내일 할 일 보기]` (`callback_data: "action_show_next"`): 내일 착수할 Next Actions 조회.

### 2.2 결정론적 태스크 완료 엔진 (`AgentService.complete_top_task` & `complete_matching_tasks`)
- `gtd/next_actions.md` ➔ 당일 일일 로그(`logs/daily/YYYY-MM-DD.md`) ➔ `gtd/inbox.md` 순서로 탐색하여, 첫 번째 미완료 항목(`- [ ] <태스크>`)을 찾아 `- [x] <태스크>`로 교체 및 파일 저장.
- 특정 키워드 매칭 완료(`complete_matching_tasks`) 및 `/done [태스크명]` 슬래시 커맨드 지원.

### 2.3 텔레그램 콜백 쿼리 라우팅 및 무타자(Zero-Typing) 피드백 (`TelegramService.process_update`)
- 콜백 수신 즉시 `answer_callback_query(cb_id, text=...)`로 0.1초 내 터치 토스트 응답을 표출하여 네트워크 지연 체감 해소.
- 각 콜백 액션을 단일 진실 공급원인 `SupervisorService`의 표준 명령 파이프라인(`/done`, `/sync`, `/push`, `/gtd-today`, `/gtd`)으로 연계하여 일관된 세션 히스토리 영속화 및 Git 원자적 푸시 보장.

### 2.4 스케줄러 및 대화형 브리핑 연동 (`BriefingScheduler`, `LLMProvider`)
- `BriefingScheduler.dispatch_briefing`에서 브리핑 발송 시 `reply_markup`으로 맞춤형 인라인 키보드를 자동 동봉.
- 텔레그램 챗봇 대화 중 브리핑 관련 인텐트(`task_briefing_morning`, `task_briefing_evening`, `task_briefing`, `repo_sync_and_briefing`) 응답 시에도 인터랙티브 키보드를 자동 부착.

## 3. Consequences (영향 및 효과)
- **무타자(Zero-Typing) 모바일 GTD 라이프 실현**: 아침 브리핑 알림을 받고 터치 한 번으로 1순위 과제를 완료 처리하거나, 저녁 회고 후 원터치로 일일 기록을 GitHub에 푸시할 수 있어 사용자 편의성 대폭 증대.
- **체크박스 상태 추적 정합성 확보**: 태스크 삭제뿐만 아니라 `- [ ]` ➔ `- [x]` 완료 상태 전환 및 커밋 히스토리가 투명하게 기록되어 성취감과 생산성 통계 기반 마련.
- **다중 채널 무결성 유지**: 텔레그램 인라인 키보드 동작 결과가 데이터베이스 세션 및 실제 마크다운 파일, Git 원격 저장소에 완벽히 동기화됨.
