# 📏 Spec-Code Alignment Rule (기획-코드 동기화 규칙)

## 1. 개요
본 규칙은 모든 기획 문서(`docs/PRD.md`, `docs/requirements.md`, `docs/roadmap.md`, `docs/adr/`)와 구현 코드가 항상 100% 완벽히 동기화되도록 강제하는 범용 하네스 규칙이다.

## 2. 필수 검증 수칙
1. **기획 우선 수칙 (Spec-First)**
   - 어떤 코드를 작성하거나 수정하기 전, 해당 기능이 `docs/requirements.md`에 정의되어 있는지 확인한다.
   - 새로운 기능/요구사항이 발견될 경우, **반드시 기획 문서와 ADR을 먼저 업데이트**한 후 코드 구현에 착수한다.

2. **추적성 매트릭스 동기화 (Traceability)**
   - 요구사항 ID(FR-01, FR-02 등)와 구현 파일(`app/services/...`) 간 1:1 연결을 `docs/requirements.md` 하단 매트릭스에 항상 유지한다.

3. **자가 검증 루프 (Self-Verification & Live Curl Testing)**
   - 코드 작성 완료 후 `pytest`, `mypy .`, `ruff check .`뿐만 아니라 **실제 라이브 서버 cURL 검증 스크립트 (`./scripts/smoke_test.sh`)**를 직접 실행하여 단 1개의 500 에러나 수신 오류도 없음을 증명한다.
