# ADR-062: 개발/운영 프로세스 분리 및 Pre-Push 품질 게이트 도입 (Dev/Prod Separation & Pre-Push Quality Gate)

## 1. 개요 (Context)
* **배경**:
  * 기존 하네스 규칙(`AGENTS.md`, `spec_alignment.md`, `dev-workflow/SKILL.md`)은 **"모든 코드 수정 후 반드시 전체 `pytest`, `mypy .`, `ruff check .` 및 `./scripts/smoke_test.sh` 라이브 cURL 검증과 서비스 재시작을 수행할 것"**을 강제하고 있었다.
  * 이로 인해 사소한 코드 한 줄을 수정하거나 반복적(Iterative)으로 기능을 개발할 때마다 무거운 전체 단위 테스트와 수십 개의 시나리오가 포함된 `smoke_test.sh`가 매번 실행되어 **에이전트 턴(Turn) 소모, 토큰 비용 증가, 작업 대기 시간 지연**이 심각하게 발생했다.
  * 또한 개발 중인 미검증 코드가 곧바로 24/7 운영 중인 서버 프로세스(`service.sh restart`)에 반영되어 개발계(Dev)와 운영계(Prod)의 경계가 모호한 문제가 있었다.

---

## 2. 의사결정 (Decision)

### 2.1 로컬 경량 개발 루프 (Fast Dev Loop) 전환
1. **일상 코드 수정 시 전체 검증 생략**:
   * 개발 진행 중에는 전체 `pytest` 및 `smoke_test.sh` 실행 의무를 해제한다.
   * 수정된 파일에 대한 `ruff check <file>`, `mypy <file>` 및 직결된 단일 테스트 파일(`pytest tests/test_xxx.py`)만 타겟 실행하여 1~3초 내에 피드백을 얻는다.
2. **운영 프로세스 재시작 지양**:
   * 단순 코드 수정 단계에서는 운영 서버(`8000`번 포트)를 재시작하지 않는다. 필요 시 개발용 별도 포트(`8001`, 텔레그램 폴링 비활성화)로 확인한다.

### 2.2 Pre-Push 통합 빌드/테스트 게이트 (`scripts/gate.sh` & Git Hook)
1. **푸시/배포 시점 단일 게이트 운영**:
   * 로컬 개발을 완료하고 원격 저장소에 푸시(`git push`)하거나 운영 환경에 배포(`scripts/deploy.sh`)하는 단계에서만 통합 품질 게이트(`scripts/gate.sh`)를 가동한다.
2. **게이트 검증 파이프라인**:
   * `Step 1`: `ruff check .` (전체 코드 린트)
   * `Step 2`: `mypy app/` (전체 정적 타입 검사)
   * `Step 3`: `pytest` (전체 단위 테스트)
   * `Step 4`: 스모크 검증 (`./scripts/smoke_test.sh --quick` 또는 전체 스모크 검증)
3. **Git `pre-push` 훅 연동**:
   * `git push` 실행 시 자동으로 `scripts/gate.sh`가 트리거되어, 검증을 통과하지 못한 코드는 원격 저장소 푸시 및 운영 반영이 차단(Fail-Fast)되도록 구성한다.

### 2.3 하네스 규약 문서화 (`.agents/rules/release_gate.md`)
* 에이전트가 작업 시 이 규칙을 최우선으로 참조하도록 `.agents/rules/release_gate.md`를 신설하고, `AGENTS.md` 및 `.agents/skills/dev-workflow/SKILL.md`의 과도한 매 수정 검증 강제 조항을 **"경량 개발 + 푸시/배포 게이트"** 체계로 개정한다.

---

## 3. 기대 효과 (Consequences)
* **에이전트 개발 비용 및 시간 80% 이상 절감**:
  * 반복적인 코드 수정 시 무거운 전체 테스트와 스모크 테스트 실행을 생략함으로써 토큰 사용량과 응답 시간을 획기적으로 단축한다.
* **운영 안정성 및 코드 무결성 100% 보장**:
  * 실제 푸시(`git push`) 및 운영 배포 시점에는 게이트가 엄격하게 작동하므로, 원격 저장소와 운영 서버에는 검증된 코드만 반영된다.
