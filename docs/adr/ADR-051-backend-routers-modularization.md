# ADR-051: 백엔드 라우터 계층 모듈화 리팩터링 (Backend Routers Modularization Architecture)

## 상태 (Status)
**채택됨 (Accepted)** - 2026-09-16 구현 및 단위 테스트/cURL 라이브 검증 완료

## 맥락 (Context)
* `app/routers/web_router.py`는 시스템 기능 확장(ADR-004 ~ ADR-046)에 따라 웹 페이지 뷰, 왓슨/데브봇 대화, 세션 CRUD, 브리핑/스케줄러, 검색, 주간결산, 비전 멀티모달, 잔디/에디터, 셀프호스팅 셋업 등 서로 다른 성격의 엔드포인트 20여 개를 혼자 담당하는 515라인의 모놀리식 파일로 비대화되었습니다.
* 단일 파일 내에 다양한 데이터 스키마(Pydantic BaseModel 5종)와 서비스 의존성이 밀결합되어 있어, 특정 API 수정 시 다른 도메인 엔드포인트에 영향을 미칠 위험이 있었습니다.
* 이에 따라 점진적 리팩터링 계획(Phase 3-1)에 의거하여, 외부 API 명세 및 cURL 통신에 일체의 변경 없이 단일 책임 원칙(SRP)에 기반한 4대 도메인 서브 라우터 분할 아키텍처를 수립했습니다.

## 결정 (Decision)
1. **도메인별 4대 서브 라우터 분리 (`app/routers/`)**:
   * `chat_router.py` (44라인): 왓슨 대화(`POST /api/chat`) 및 DevBot 대화(`POST /api/dev/chat`) 전담.
   * `session_router.py` (72라인): 세션 목록(`GET /api/sessions`, `GET /api/dev/sessions`), 히스토리 조회, 제목 변경(PATCH), 삭제(DELETE), 메시지 비우기(POST) 전담.
   * `briefing_router.py` (56라인): 맞춤 브리핑(`GET /api/briefing`), 스케줄 조회(`GET /api/briefing/schedule`), 스케줄러 상태 및 능동 푸시 즉시 트리거(`POST /api/briefing/trigger-push`) 전담.
   * `lifelog_router.py` (248라인): 마크다운 고속 검색(`GET /api/search`), 주간 결산 리포트 및 푸시(`GET/POST /api/weekly`), Vision AI 사진 분석 및 사전 검토(`POST /api/vision/*`), 연간 잔디/에디터 파일 입출력(`GET/POST /api/lifelog/*`), 셋업 진단(`GET /api/system/setup-status`) 전담.
2. **`web_router.py` 뷰 오케스트레이터 경량화**:
   * 모놀리식 515라인에서 **95라인(81.6% 대폭 감축)**으로 슬림화.
   * 에이전트 허브 포털(`/`), 왓슨 콘솔(`/watson`), DevBot 콘솔(`/dev`) HTML 렌더링 및 워크스페이스 상태 요약(`/api/hub/status`, `/api/dev/status`)만 전담.
   * 4개 서브 라우터를 `router.include_router(...)`로 마운트하여 기존 `app.include_router(web_router.router)` 구조 및 모든 엔드포인트 URL과 100% 하위 호환성 보장.

## 결과 및 효과 (Consequences)
* **단일 책임 원칙(SRP) 확립**: 대화, 세션, 브리핑, 라이프로그 기능이 명확히 분리되어 코드 탐색성과 가독성이 비약적으로 향상됨.
* **100% 하위 호환성 유지**: 기존 프론트엔드 AJAX 요청, 모바일 텔레그램 웹훅, cURL 스모크 테스트의 엔드포인트 URL 및 응답 페이로드가 100% 동일하게 유지됨.
* **검증 완료**: `pytest` 단위 테스트 100% 통과, `mypy` 및 `ruff` 정적 검사 무결점, `./scripts/smoke_test.sh` 40+개 라이브 테스트 전수 통과.
