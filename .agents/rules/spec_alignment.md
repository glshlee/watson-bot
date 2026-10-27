# 📏 Spec-Code Alignment Rule (기획-코드 동기화 규칙)

## 1. 개요
본 규칙은 모든 기획 문서(`docs/PRD.md`, `docs/requirements.md`, `docs/roadmap.md`, `docs/adr/`) 및 사용자 안내서(`README.md`)와 구현 코드가 항상 100% 완벽히 동기화되도록 강제하는 범용 하네스 규칙이다.

## 2. 필수 검증 수칙
1. **기획 우선 수칙 (Spec-First)**
   - 어떤 코드를 작성하거나 수정하기 전, 해당 기능이 `docs/requirements.md`에 정의되어 있는지 확인한다.
   - 새로운 기능/요구사항이 발견될 경우, **반드시 기획 문서와 ADR을 먼저 업데이트**한 후 코드 구현에 착수한다.

2. **추적성 매트릭스 동기화 (Traceability)**
   - 요구사항 ID(FR-01, FR-02 등)와 구현 파일(`app/services/...`) 간 1:1 연결을 `docs/requirements.md` 하단 매트릭스에 항상 유지한다.

3. **README 상시 동기화 수칙 (Mandatory README Update)**
   - 기능 추가, 아키텍처 변경, CLI/환경변수/디렉토리 설정 옵션이 변경될 때마다 사용자 대면 문서인 `README.md`를 즉시 갱신한다.
   - 모든 작업 마무리 시 `README.md`의 사용 예시, 아키텍처 다이어그램, 배포 가이드가 최신 상태인지 필수로 교차 점검한다.

4. **2단계 검증 루프 (Fast Dev Loop & Pre-Push Gate — ADR-062)**
   - 일상 코드 수정 중(Fast Dev Loop)에는 수정된 파일의 `ruff check <file>`, `mypy <file>` 및 직결된 단일 `pytest tests/test_xxx.py`만 실행하여 비용을 절감한다.
   - 개발 완료 후 커밋/푸시 직전(Pre-Push Gate)에는 반드시 `./scripts/gate.sh`(`ruff check .`, `mypy app/`, 전체 `pytest`, 격리 샌드박스 `./scripts/smoke_test.sh --quick`)를 1회 실행하여 단 1개의 오류도 없음을 증명한다.
