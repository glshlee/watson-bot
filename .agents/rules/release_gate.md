# 🚦 Release & Pre-Push Quality Gate Rule (개발/운영 분리 및 푸시 게이트 규칙)

## 1. 개요
본 규칙은 코드 수정 시마다 무거운 전체 테스트 및 실서버 스모크 테스트를 반복 실행하여 발생하는 **과도한 에이전트 비용(토큰·시간)과 운영 서비스 중단 문제를 해소**하기 위해, **로컬 경량 개발 루프(Fast Dev Loop)**와 **푸시/배포 품질 게이트(Pre-Push & Deploy Gate)**를 엄격히 분리하는 하네스 표준 규약이다.

---

## 2. 3단계 파이프라인 운영 원칙

### Phase 1: 로컬 경량 개발 루프 (Fast Dev Loop — 일상 코드 수정 시)
코드를 작성하거나 수정하는 과정(Iteration)에서는 최소한의 비용으로 즉각적인 피드백만 확인한다.
1. **전체 테스트 및 스모크 테스트 실행 금지**:
   - 단순 코드 수정 시 전체 `pytest` 스위트나 `./scripts/smoke_test.sh`를 매번 실행하지 않는다.
   - 운영 서버(`./scripts/service.sh restart`)를 개발 확인 목적으로 수시 재시작하지 않는다.
2. **타겟팅된 초경량 검증만 수행 (Targeted Check)**:
   - 수정한 파일에 한해 정적 린트/타입 검사 수행:
     `ruff check <수정한_파일_경로> && mypy <수정한_파일_경로>`
   - 수정한 기능과 직결된 단일 테스트 파일/케이스만 선택 실행:
     `pytest tests/test_<관련모듈>.py -k "<테스트명>"`

### Phase 2: 푸시 & 통합 품질 게이트 (Pre-Push Gate — 커밋/푸시 직전)
로컬 개발이 완료되어 **사용자가 커밋/푸시(`git push`) 또는 통합 검증을 요청한 시점**에만 전체 빌드 및 품질 게이트(`./scripts/gate.sh`)를 1회 실행한다.
1. **게이트 실행 시점**:
   - `git push` 실행 시 (Git `pre-push` 훅 자동 연동 또는 `./scripts/gate.sh` 명시적 호출)
   - 운영계 배포(`./scripts/deploy.sh`) 직전
2. **게이트 필수 통과 기준 (4단계 검증)**:
   - **[Step 1] 정적 코드 품질 (Lint)**: `ruff check .` 통과
   - **[Step 2] 정적 타입 무결성 (Type Check)**: `mypy app/` 통과
   - **[Step 3] 전체 단위 테스트 (Unit Tests)**: `pytest` 전체 통과
   - **[Step 4] 샌드박스 스모크 테스트 (Smoke Test)**: 운영 서버를 건드리지 않는 격리 환경(또는 `--quick` 헬스/핵심 API 검증) 통과
3. **실패 시 차단 (Fail-Fast)**:
   - 위 단계 중 하나라도 실패하면 `git push` 및 운영 배포를 즉시 중단하고, 해당 오류를 수정한 뒤 게이트를 재실행한다.

### Phase 3: 개발계(Dev) / 운영계(Prod) 실행 분리 및 배포 (Release & Deploy)
1. **운영계 (Production — 포트 `8000`)**:
   - 24/7 가동되는 텔레그램 봇 폴링 및 웹 서비스는 검증이 완료된 상태에서 `./scripts/deploy.sh`(또는 `./scripts/service.sh restart`)를 통해서만 반영한다.
2. **개발계 (Development — 포트 `8001`, 선택적 기동)**:
   - 개발 중 로컬 웹 UI나 API 동작을 수동 확인해야 할 때는 텔레그램 폴링을 비활성화(`DISABLE_TELEGRAM_POLLING=1`)하고 별도 포트(`8001`)로 기동하여 운영 봇과의 충돌을 원천 차단한다.

---

## 3. 에이전트 비용 절감 수칙 요약 (Do & Don't)

| 구분 | 일상 코드 수정 시 (Dev Loop) | 푸시 및 운영 배포 시 (Gate & Deploy) |
| :--- | :--- | :--- |
| **Lint / Type** | `ruff check <변경파일>` / `mypy <변경파일>` | `ruff check . && mypy app/` (전체) |
| **Unit Test** | `pytest tests/test_target.py` (변경분만) | `pytest` (전체 스위트) |
| **Smoke Test** | ❌ **실행 금지** (비용 절감) | ✅ `./scripts/gate.sh` 내 1회 실행 |
| **운영 서버 재시작** | ❌ **재시작 금지** (운영 안정성 보호) | ✅ 게이트 통과 후 배포 시에만 재시작 |
