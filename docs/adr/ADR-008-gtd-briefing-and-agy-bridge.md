# ADR-008: GTD 지능형 브리핑(할 일/일정 정리) 및 Linux 환경 AGY CLI 브릿지 경로 자동 감지

* **상태 (Status)**: 승인됨 (Accepted)
* **날짜 (Date)**: 2026-09-08
* **작성자 (Author)**: Watson Core Team & User

---

## 1. 맥락 (Context)
사용자가 텔레그램을 통해 **"오늘 해야할 일 정리해줘"**라고 요청했을 때, Watson이 GTD 저장소를 조회하거나 지능적인 일과 요약을 제공하지 못하고 고정된 더미 텍스트(`"네, 말씀해 주신 내용 잘 새겨들었습니다! 😊 이와 관련해 더 나누고 싶은 생각이나..."`)를 반환하는 기대 불일치가 발생했다.

### 원인 분석
1. **GTD 조회 및 브리핑(Task Briefing) 기능 부재**:
   * 기존 시스템은 사용자의 입력을 마크다운 파일에 추가(Append)하는 쓰기 중심 기능만 갖추고 있었으며, 기정의된 GTD 체계(`gtd/next_actions.md`, `logs/daily/YYYY-MM-DD.md`, `gtd/inbox.md`)에서 오늘 해야 할 일과 미완료 작업을 읽어와 브리핑해 주는 조회(Query/Briefing) 파이프라인이 누락되어 있었다.
2. **Linux 서버 환경 AGY CLI 경로 탐색 실패**:
   * `LLMProvider` 내부에 Mac 로컬 개발 경로(`/Users/glshlee/...`)가 하드코딩되어 있었고, `systemd` 서비스 데몬 실행 시 기본 `PATH`에 `/home/ubuntu/.local/bin`이 포함되지 않아 실제 서버에 설치된 `agy`(`1.1.27`) 바이너리를 감지하지 못하고 로컬 더미 폴백으로 빠졌다.

---

## 2. 의사결정 (Decision)

### 2.1. GTD 지능형 브리핑 (`task_briefing`) 인텐트 구현
* 사용자가 "오늘 해야할 일", "할 일 정리", "일정 알려줘", "투두", "GTD 요약" 등을 요청할 때 이를 `task_briefing` 인텐트로 분류한다.
* `AgentService.get_gtd_summary()` 메서드를 통해 연결된 GTD 저장소에서 다음 항목을 수집 및 정제한다:
  1. 당일 데일리 로그(`logs/daily/YYYY-MM-DD.md`)의 `## 📅 주요 일정 (Schedule)`
  2. `gtd/next_actions.md`의 우선순위별 다음 행동 목록
  3. `gtd/inbox.md`의 미분류 수집 항목 (`## 💬 빠른 메모 / 캡처`)
* 수집된 항목을 일목요연하고 시각적으로 직관적인 비서형 요약 메시지로 구성하여 회신한다.

### 2.2. Linux/서버 환경 AGY CLI 경로 동적 탐색 및 systemd 환경변수 주입
* `LLMProvider`에서 특정 OS/사용자명에 종속된 경로를 제거하고, 다음 순서로 바이너리를 탐색한다:
  1. `shutil.which("agy")`
  2. `os.path.expanduser("~/.local/bin/agy")`
  3. `/home/ubuntu/.local/bin/agy`
  4. `/usr/local/bin/agy`
* `systemd/watson.service` 및 `/etc/systemd/system/watson.service`에 `Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin"`을 명시하여 백그라운드 서비스에서도 `agy`가 100% 실행되도록 보장한다.

---

## 3. 결과 및 영향 (Consequences)

### Positive (긍정적 영향)
* **실시간 비서형 GTD 브리핑**: "오늘 해야할 일 정리해줘" 한마디로 사용자의 실제 GTD 저장소(`life_log`) 내 일정과 할 일을 정확히 확인 가능.
* **살아있는 대화형 AI**: Linux 서버 환경에서도 `agy` CLI 연동이 안정적으로 작동하여 기계적인 앵무새 답변이 제거되고 상황에 맞는 유연한 비서 대화 제공.
