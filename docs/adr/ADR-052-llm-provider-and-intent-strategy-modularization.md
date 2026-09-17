# ADR-052: LLMProvider 및 의도 분석 엔진 모듈화 리팩터링 (LLMProvider & Intent Strategy Architecture)

## 상태 (Status)
**채택됨 (Accepted)** - 2026-09-16 구현 및 단위 테스트/cURL 라이브 검증 완료

## 맥락 (Context)
* `app/services/llm_provider.py`는 시스템 기능 확장(ADR-003 ~ ADR-045)에 따라 1,188라인에 달하는 거대 모놀리식 클래스로 비대화되었습니다.
* 단일 파일 내에 의도 판별(정규식/지시어 20여 종), 카테고리 분류, D-Day/태스크 추출, AGY CLI 서브프로세스 호출, 프롬프트 빌더 및 로컬 스마트 폴백이 모두 결합되어 있어 단일 책임 원칙(SRP)을 심각하게 위반하고 있었습니다.
* 이에 따라 점진적 리팩터링 계획(Phase 3-2)에 의거하여, 외부 인터페이스 및 테스트 모킹(`patch.object(LLMProvider, "_find_agy_path", ...)`) 호환성을 100% 유지하면서 책임을 4대 서브모듈로 분할하고 `LLMProvider`를 경량 파사드(Facade)로 개편하는 아키텍처를 수립했습니다.

## 결정 (Decision)
1. **도메인별 4대 서브모듈 분리 (`app/services/llm/`)**:
   * `agy_client.py` (55라인): 멀티 플랫폼 AGY CLI 바이너리 동적 탐색(`find_agy_path`) 및 서브프로세스 안전 실행(`execute_agy`).
   * `prompt_builder.py` (90라인): GTD 스킬 지침 로드(`load_skill_instructions`), 왓슨 비서 페르소나 및 대화 맥락 조립(`build_system_prompt`), 스마트 로컬 폴백(`get_smart_fallback`).
   * `category_extractor.py` (85라인): 4대 라이프로그 카테고리 추론(`detect_category`) 및 D-Day 태그 결합 액션 태스크 추출(`extract_actionable_task`).
   * `intent_analyzer.py` (505라인): `IntentResult` 데이터클래스 정의 및 20여 종의 인텐트(승인/거절, 메타 피드백, 명시적/맥락적 기록, 숏컷 조회, 브리핑, 초안 제안, 자연어 대화) 분석 엔진(`analyze_intent`).
2. **`LLMProvider` 파사드(Facade) 경량화**:
   * 모놀리식 1,188라인에서 **79라인(93.3% 대폭 감축)**으로 슬림화.
   * `_find_agy_path()`, `_load_skill_instructions()`, `_detect_category()`, `_extract_actionable_task()`, `_call_ai_engine()`, `analyze_and_respond()`, `generate_response()` 등 기존 모든 공개/내부 메서드 시그니처를 100% 유지하여 하위 호환성 보장.

## 결과 및 효과 (Consequences)
* **단일 책임 원칙(SRP) 및 응집도 극대화**: 프로세스 호출, 프롬프트 엔지니어링, 텍스트 정제, 의도 분류가 명확히 분리되어 개별 도메인 로직의 수정 및 단위 테스트가 극도로 용이해짐.
* **100% 하위 호환성 및 테스트 안전성**: `tests/conftest.py`의 `fast_unit_test_environment`(`patch.object(LLMProvider, "_find_agy_path")`)를 포함한 모든 기존 테스트 및 서비스 호출부가 수정 없이 100% 정상 작동.
* **검증 완료**: `test_llm_provider.py` (13 passed in 0.92s), 관련 서비스 테스트 28건 100% 통과, `mypy` 39개 파일 및 `ruff` 무결점, `./scripts/smoke_test.sh` 40+개 라이브 테스트 전수 통과.
