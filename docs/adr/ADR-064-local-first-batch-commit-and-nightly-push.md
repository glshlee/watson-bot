# ADR-064: 로컬 우선 기록(Local-First) 및 일괄 커밋·야간 자동 푸시 워크플로우

* **상태 (Status)**: 승인됨 (Accepted)
* **작성일 (Date)**: 2026-10-27
* **결정자 (Deciders)**: 사용자 및 Watson AI Architect

---

## 1. 배경 및 문제 정의 (Context & Problem Statement)
기존 **ADR-004 (1기록 1커밋 즉시 푸시)** 정책에서는 사용자가 일기 메모나 GTD 할 일을 추가·완료·제거할 때마다 즉시 `git add` ➔ `git commit` ➔ `git pull --rebase --autostash` ➔ `git push`를 동기 실행했습니다. 이로 인해 다음과 같은 불편이 발생했습니다:
1. **네트워크 I/O 블로킹 지연**: 단순 메모 한 줄을 남길 때마다 원격 GitHub 통신이 발생하여 2~5초의 응답 지연이 발생함.
2. **Git 커밋 히스토리 파편화**: 하루 동안 여러 번 할 일을 추가하고 완료할 때마다 자잘한 커밋이 수십 개씩 생성됨.
3. **사용자 요구사항**: 평상시 명령 시에는 로컬 마크다운 파일에만 즉시 작업(`Local-First`)하고, 나중에 원할 때 한 번에 모아서 커밋(`/commit`, `/push`)하며, 사용자가 잊고 자더라도 **하루에 한 번 자기 전(밤 23:30 KST)에 자동으로 일괄 커밋 및 푸시**하는 워크플로우가 필요함.

---

## 2. 결정 사항 (Decision)
1. **평상시 로컬 우선 기록 (Local-First Modification)**:
   * `SupervisorService.process_user_request` 및 `ChatRequest`의 `auto_push` 기본값을 `False`로 변경하고, 일기 기록(`log_confirm`, `log_explicit`, `log_dual`) 및 GTD 조작(`task_complete`, `gtd_remove`) 시 로컬 마크다운 파일에만 즉시(0.01초) 반영합니다.
2. **온디맨드 일괄 커밋 (`/commit`) 및 원스톱 푸시 (`/push`)**:
   * `GitService.get_dirty_files()` 및 `build_batch_commit_message()`를 신설하여 현재 작업 트리에 축적된 모든 수정/신규 파일 목록을 기반으로 `docs(lifelog & gtd): batch update N file(s) (YYYY-MM-DD) [파일목록]` 형태의 일괄 커밋을 생성합니다.
   * `GitService.push(auto_commit_dirty=True)`를 통해 사용자가 `"푸시해줘"` 또는 `/push`만 입력하더라도 미커밋 로컬 작업이 남아 있으면 자동으로 먼저 일괄 커밋한 뒤 원격 GitHub로 푸시합니다.
3. **자기 전 하루 1회 야간 자동 백업 스케줄러 (`Nightly Auto-Commit & Push`, 23:30 KST)**:
   * `BriefingScheduler`에 매일 밤 `23:30 KST`(`NIGHTLY_PUSH_TIME` 환경변수로 조정 가능) 정기 루틴(`dispatch_nightly_git_sync`)을 탑재합니다.
   * 미커밋 로컬 파일(`dirty_files`) 또는 미푸시 커밋(`ahead_count > 0`)이 존재할 때만 일괄 커밋 및 원격 푸시를 수행하고 텔레그램으로 완료 알림을 발송하며, 변경사항이 없을 때는 불필요한 커밋이나 알림 없이 조용히 스킵합니다.

---

## 3. 결과 및 기대 효과 (Consequences)
* **체감 응답 속도 극대화**: 일상 메모 및 GTD 할 일 추가/완료 시 Git 네트워크 대기 시간이 제거되어 즉각 응답합니다.
* **깔끔한 Git 히스토리 & 무자각 백업 보장**: 하루의 작업이 의미 있는 배치 커밋 단위로 묶이며, 밤 23:30 자동 백업으로 데이터 유실을 원천 방지합니다.
