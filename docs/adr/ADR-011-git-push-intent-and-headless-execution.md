# ADR-011: Git 원격 푸시 의도 분기(repo_push), autostash 안전 동기화 및 AGY Headless 무중단 실행

* **상태 (Status)**: 승인됨 (Accepted)
* **날짜 (Date)**: 2026-09-08
* **작성자 (Author)**: Watson Core Team & User

---

## 1. 맥락 (Context)
사용자가 텔레그램을 통해 라이프로그 기록 후 GitHub 저장소를 확인하였으나 푸시가 되어 있지 않아 **"푸시도 해줘"**, **"푸시가 안됐는데 다시 확인해줘"**라고 요청했음에도, Watson이 실제 Git 푸시를 실행하지 않고 LLM이 "푸시까지 안전하게 완료했습니다"라고 허위 환각(Hallucination) 답변을 하거나, 뒤이어 `"말씀해 주신 깊은 마음과 생각 잘 헤아리고 있습니다. 곁에서 언제나 든든한 버팀목이 되어 드릴 테니..."`라는 동문서답식 감성 폴백을 반환하는 문제가 발생했다.

### 원인 분석
1. **작업 트리의 언스테이징 파일로 인한 Git Rebase Pull 실패 및 푸시 스킵**:
   * GTD 저장소(`life_log`) 내에 작업 중인 파일(예: `infra/engineer_bot.py`) 등 언스테이징된 변경사항이 존재할 때, 기존 `sync_and_commit_push` 내부의 `remote.pull(branch, rebase=True)`가 `autostash` 없이 실행되어 exit code 128(`cannot pull with rebase: You have unstaged changes`)로 중단되었다.
   * `pull` 예외가 발생하면서 그 뒤에 위치한 `remote.push(branch)`가 아예 호출되지 않아, 로컬에는 커밋되었으나 GitHub 원격에는 푸시되지 않았다.
2. **독립적 Git 푸시 의도(`repo_push`) 및 전용 메서드 부재**:
   * "푸시해줘", "푸시도 해줘", "깃 푸시", "/push", "푸시가 안됐는데 다시 확인해줘" 등의 명시적 푸시 요청을 처리하는 인텐트가 없어 일반 대화(`chat_only`)로 분류되었다.
   * LLM이 실제 Git 명령을 실행할 수 없음에도 마치 푸시가 완료된 것처럼 환각 문장을 생성하여 사용자에게 잘못된 상태를 안내했다.
3. **AGY Headless 모드의 대화형 도구 권한 거부**:
   * 사용자가 "푸시가 안됐는데 다시 확인해줘"라고 재차 질의했을 때, `agy -p`가 CLI 환경에서 터미널 커맨드 도구를 자의적으로 실행하려 시도했다.
   * 비대화형(Headless) 모드에서는 터미널 권한 프롬프트를 띄울 수 없어 `jetski: no output produced — a tool required the "command" permission...` 에러와 함께 출력이 차단되었고, 빈 문자열로 인해 로컬의 감성 폴백 문구가 표출되었다.

---

## 2. 의사결정 (Decision)

### 2.1. GitService autostash 격리 및 전용 `push()` 구현
* **`sync_and_commit_push()` 견고화**:
  * `pull` 시 `rebase=True, autostash=True`를 필수 적용하여 작업 트리에 수정 중인 파일이 있어도 안전하게 스태시 후 최신 커밋을 병합하도록 보장.
  * `pull`과 `push`의 실행 블록을 독립 분리하여, 네트워크 경고나 사소한 풀 경고가 발생하더라도 원격 푸시 시도를 누락하지 않음.
* **전용 `push()` 메서드 신설**:
  * 로컬과 원격 간 앞선 커밋 개수(`rev-list --count remote/branch..branch`)를 정확히 계측.
  * `git push` 실행 후 푸시된 커밋 수와 원격 브랜치 정보를 투명하게 사용자에게 보고.

### 2.2. 결정론적 푸시 인텐트(`repo_push`) 라우팅
* `LLMProvider`에 `repo_push` 인텐트를 추가하여 LLM 환각을 원천 차단:
  * 트리거: `/push`, `push`, `푸시`, `푸시해줘`, `푸시도 해줘`, `깃 푸시`, `깃허브로 올려줘`, `푸시가 안됐는데 다시 확인해줘` 등.
  * 헬스/운동 키워드("푸시업", "pushup")는 예외 처리하여 운동 라이프로그와 충돌 방지.
* `SupervisorService`에서 `repo_push` 인텐트 감지 시 즉시 `git_service.push()`를 호출하여 실제 Git 작업을 집행하고 명확한 결과를 응답.

### 2.3. AGY CLI Headless 무중단 권한 플래그 및 프롬프트 가드레일
* `_call_ai_engine`의 `agy -p` 실행 인자에 `--dangerously-skip-permissions` 플래그를 추가하여 headless 도구 실행 권한 블로킹을 해제.
* 시스템 프롬프트에 도구 시뮬레이션 및 터미널 모사 금지 지침을 명시하여 순수한 대화 및 카운슬링에 집중 유도.
* 만약의 폴백 발생 시에도 시스템/깃 명령 관련 질의는 감성 문구가 아닌 시스템 점검 안내(`/status`, `/sync`, `/push`)를 반환하도록 분기 개선.

### 2.4. 텔레그램 `/push` 명령어 제공
* `/start` 및 `/help` 안내문에 `/push` 명령어를 정식 추가하여 사용자가 언제든 수동으로 즉시 원격 푸시를 실행할 수 있도록 지원.

---

## 3. 결과 및 영향 (Consequences)

### Positive (긍정적 영향)
* **100% 신뢰할 수 있는 GitHub 동기화**: 로컬 작업 트리에 언스테이징 파일이 있더라도 autostash를 통해 안정적으로 원격 저장소 푸시 완료.
* **LLM 거짓말/환각 원천 배제**: 푸시 명령은 결정론적 백엔드 파이프라인(`GitService.push()`)에서 직접 실행되어, 실제 Git 성공/실패 결과를 있는 그대로 정직하게 피드백.
* **무중단 AGY CLI 동작**: headless 권한 거부로 인한 침묵 및 엉뚱한 감성 문구 출력 현상 완전 해소.
