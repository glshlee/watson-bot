# ADR-048: 단위 테스트 초고속화 및 템플릿 컴포넌트 모듈화 리팩터링

## 1. 배경 및 문제 정의 (Context)
* **테스트 실행 지연 (14분 27초)**:
  * 전체 133개 단위 테스트 실행 시 총 **867.52초 (14분 27초)**가 소요되어 개발 생산성과 리팩터링 피드백 루프가 심각하게 저해됨.
  * 원인 1: `LLMProvider._call_ai_engine`이 호스트의 실제 `agy` CLI 바이너리를 서브프로세스로 실행하여 원격 Gemini API 호출 및 최대 45초 타임아웃 대기 루프 발생 (`test_llm_provider.py` 13개 테스트만 128초 소요).
  * 원인 2: `DevAgentService`가 `/lint`, `/test` 테스트 시 하위 프로세스로 `mypy`(전체 30개 파일 타입검사, 12초) 및 `pytest`를 중첩 실행함.
  * 원인 3: `test_weather_service.py`가 캐시 초기화 후 외부 Open-Meteo 실시간 기상 API를 직접 호출하여 네트워크 지연(10초) 발생.
* **프론트엔드 모놀리식 템플릿 부채**:
  * `app/templates/index.html`(574줄) 내부에 세션 관리, GTD 설정, 스케줄, 출근길 설정, 텔레그램 메뉴, 잔디 에디터 등 8개의 서로 다른 모달 DOM 구조(400여 줄)가 단일 파일에 평면으로 인라인되어 있어 가독성 및 유지보수성이 극히 취약함.

---

## 2. 아키텍처 결정 (Decision)

### 2.1 단위 테스트 하네스 격리 및 초고속화
1. **`tests/conftest.py` 글로벌 고속 테스트 픽스처 (`fast_unit_test_environment`) 도입**:
   - `LLMProvider._find_agy_path`를 `None`으로 Mocking하여 원격 API 호출을 원천 차단하고, 내장된 Smart Fallback 엔진(결정론적 의도 및 텍스트)으로 0.001초 내 즉각 응답하도록 보장.
   - `DevAgentService._run_lint` 및 `_run_pytest`를 정적 결과 딕셔너리로 Mocking하여 중첩 프로세스 구동 및 CPU 낭비 차단.
2. **외부 네트워크 호출 격리**:
   - `test_weather_service.py`의 `get_live_weather` 테스트 시 `_fetch_open_meteo`를 Mocking하여 네트워크 I/O 지연 제거.
3. **단위 테스트 vs 라이브 통합 테스트 역할 분리**:
   - `pytest`: 모든 외부 I/O, Subprocess, 네트워크를 100% Mock 격리하여 순수 비즈니스 로직을 수 초 내 검증.
   - `./scripts/smoke_test.sh`: 실제 가동 중인 Uvicorn 서버, SQLite DB, 라이브 cURL API 통신을 통해 엔드투엔드 무결성을 전수 검증.

### 2.2 UI 템플릿 8대 모달 컴포넌트 분할 (`app/templates/modals/`)
`app/templates/index.html`에 인라인되어 있던 8대 모달 창을 단일 책임 원칙(SRP)에 따라 독립 템플릿 파일로 분할하고 Jinja2 `{% include %}` 구문으로 조립:
* `modals/rename_modal.html`: 세션 이름 변경 모달 (ADR-017)
* `modals/delete_modal.html`: 세션 영구 삭제 확인 모달 (ADR-017)
* `modals/clear_modal.html`: 대화 내용 비우기 모달 (ADR-017)
* `modals/gtd_modal.html`: GTD 작업 디렉토리 설정 모달 (ADR-007)
* `modals/schedule_modal.html`: 브리핑 & 일정 타임라인 모달 (ADR-025)
* `modals/commute_modal.html`: 출근길 날씨·미세먼지·버스 브리핑 설정 모달 (ADR-030)
* `modals/telegram_menu_modal.html`: 텔레그램 봇 메뉴 명령어 설정 모달 (ADR-041)
* `modals/lifelog_editor_modal.html`: 일일 로그 잔디 & 인플레이스 에디터 모달 (ADR-045)

---

## 3. 결과 및 영향 (Consequences)

### 긍정적 효과
* **테스트 속도 대폭 개선**:
  * 전체 133개 테스트 시간: **867.52초(14분 27초) ➔ 136.22초(2분 16초)**로 약 **6.4배 단축 (84% 절감)**.
  * `test_llm_provider.py`: **128초 ➔ 0.4초 (320배 단축)**.
  * `test_weather_service.py`: **16초 ➔ 6.8초 (단축)**.
* **HTML 템플릿 슬림화 및 모듈화**:
  * `index.html` 라인 수: **574줄 ➔ 183줄 (68% 감소)**.
  * 모달별 마크업이 독립 컴포넌트화되어 특정 모달 수정 시 다른 뷰에 간섭하지 않고 독립 개발 가능.
* **기능 무결성 100% 유지**:
  * `pytest` 133개 테스트 100% 통과.
  * `./scripts/smoke_test.sh` 전 항목 통과 (cURL 라이브 검증 완료).
