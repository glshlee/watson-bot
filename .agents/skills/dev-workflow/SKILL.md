---
name: dev-workflow
description: 단위 테스트(TDD), 정적 린트/타입 검사, Conventional Commits, 4단계 문서화 루프 및 하네스 개발 규약 스킬
---

# 🛠️ Watson Dev Workflow Skill (개발 표준 규약)

## 1. 목적
DevBot 및 엔지니어링 에이전트가 왓슨(Watson) 코드베이스를 수정하거나 신규 기능을 구현할 때 준수해야 하는 최고 수준의 소프트웨어 엔지니어링 표준 및 하네스 개발 절차를 규정한다.

## 2. 표준 개발 7단계 파이프라인 (7-Step Workflow)
1. **요구사항 분석 & 설계 (Analysis & Design)**:
   - `docs/PRD.md`, `docs/requirements.md`, `docs/roadmap.md` 검토
   - 필요 시 신규 기능/아키텍처에 대한 ADR 초안 구상 (`docs/adr/ADR-xxx.md`)
2. **단위 테스트 작성 & 실행 (TDD & Pytest)**:
   - `pytest tests/` (또는 `/test [경로]`)로 기존 테스트 무결성 확인 및 신규 테스트 케이스 추가
3. **수술적 코드 구현 & SRP 준수 (Surgical Implementation)**:
   - 단일 책임 원칙(SRP) 및 파사드(Facade) 패턴을 적용하여 파일 비대화 방지
4. **정적 린트 및 타입 검사 (Quality Gate)**:
   - `ruff check .` (린트 무결점)
   - `mypy app/` (타입 안정성 100% 통과)
5. **실서버 cURL 라이브 검증 (Live Verification)**:
   - `./scripts/smoke_test.sh` 실행하여 실제 API 동작 및 500 에러 부재 검증
6. **4단계 필수 문서화 루프 (Mandatory Documentation Loop)**:
   - ① `docs/adr/ADR-xxx.md` 작성
   - ② `docs/PRD.md`, `docs/requirements.md`, `docs/roadmap.md` 마일스톤 동기화
   - ③ `README.md` 사용법 및 아키텍처 갱신
   - ④ `AGENTS.md` 갱신 (반드시 100줄 이내 유지)
7. **Conventional Commits & 명시적 사용자 커밋 대기**:
   - `feat`, `fix`, `refactor` 등 표준 커밋 메시지 제안
   - **사용자가 명시적으로 "커밋해" 지시하기 전까지 임의 자동 커밋 금지**

## 3. DevBot 지원 명령어 매핑 (Toolchain Mapping)
- `/test [경로]`: Pytest 단위 테스트 실행
- `/lint`: Ruff 린터 및 Mypy 타입 정적 검사
- `/commit [메시지]`: Conventional Commits 추천 및 커밋 실행
- `/push`: GitHub 원격 저장소(`origin/main`) 푸시
- `/sync`: 원격 GitHub 변경점 최신화 (`git pull --autostash`)
- `/roadmap`: 개발 로드맵 및 마일스톤 진행률 현황 조회
- `/skills`: 하네스 개발 스킬 카탈로그 및 상세 명세 조회
- `/status` & `/diff`: Git 변경 상태 및 소스코드 차이점 검토
