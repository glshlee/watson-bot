# ADR-053: AgentService 라이프로그 및 GTD 오케스트레이션 분리 (Modular Lifelog & GTD Architecture)

## 상태 (Status)
**채택됨 (Accepted)** - 2026-09-17 구현 및 단위 테스트/cURL 라이브 검증 완료

## 맥락 (Context)
* `app/services/agent_service.py`는 왓슨의 핵심인 라이프로그 기록 및 GTD 오케스트레이션 기능(ADR-001 ~ ADR-045)이 지속적으로 누적되면서 853라인에 달하는 복합 모놀리식 모듈로 비대화되었습니다.
* 단일 파일 내에 일일 마크다운 로그(`YYYY-MM-DD.md`) 경로/포맷팅/중복 방지 로직과 GTD 수집함(`inbox.md`), 다음 행동(`next_actions.md`), 태스크 완료 및 수술적 이관(Surgical Transfer), 태스크 구문 삭제, D-Day 마감일 스캔 및 브리핑이 결합되어 있어 단일 책임 원칙(SRP)이 결여되어 있었습니다.
* 점진적 리팩터링 종합 계획(Phase 3-3)에 의거하여, 기존 공개/내부 메서드 시그니처와 단위 테스트 호환성을 100% 보존하면서 일일 라이프로그 전담(`LifelogService`)과 GTD 수집/태스크 전담(`GTDService`)으로 분리하고 `AgentService`를 경량 오케스트레이터 파사드로 개편하는 아키텍처를 수립했습니다.

## 결정 (Decision)
1. **`LifelogService` 전담 모듈 신설 (`app/services/lifelog_service.py`)**:
   * 일일 로그 디렉토리(`logs/daily/` 또는 `lifelogs/YYYY/MM/`) 감지 및 파일 경로 계산 (`get_lifelog_filepath`).
   * KST 타임존 정규화(`normalize_datetime`) 및 `[HH:MM]` 타임스탬프 엔트리 서식화.
   * 카테고리별 섹션 헤더 탐색, 멀티라인 정규화 및 30자 프리픽스 중복 방지(`append_or_update_lifelog`).
   * GTD에서 완료된 태스크의 수술적 이관(Surgical Transfer) 수신 및 당일 로그의 `## ✅ 오늘 완료한 일 (Completed GTD Tasks)` 섹션에 `- [x]` 형태로 안전하게 이관(`transfer_completed_task_to_daily_log`).
   * 일일 로그 실시간 전문 및 메타데이터(수정 시각, 라인 수) 읽기(`read_daily_log`).
2. **`GTDService` 전담 모듈 신설 (`app/services/gtd_service.py`)**:
   * GTD 수집함(`inbox.md`) 및 다음 행동(`next_actions.md`) 경로 관리 및 상태 확인 (`has_gtd_inbox`, `get_gtd_inbox_filepath`).
   * 문맥 기반(개인/업무/인프라/사이드) 스마트 섹션 탐색 및 Inbox 추가(`append_to_gtd_inbox`).
   * 당일 일정, Next Actions, Inbox 항목 종합 브리핑 텍스트 합성(`get_gtd_summary`).
   * 자연어 및 키워드 기반 태스크 물리적 삭제 (`remove_gtd_tasks`, `find_and_remove_matching_tasks`).
   * 결정론적 체크박스 완료 처리(`complete_top_task`, `complete_matching_tasks`) 및 GTD 파일 내 잘라내기(Cut) 후 `LifelogService`로의 수술적 이관(Paste) 오케스트레이션.
   * GTD 파일 마크다운 원문 및 마감일(D-Day) 긴급도 요약 조회(`read_gtd_files`).
3. **`AgentService` 파사드(Facade) 경량화 (`app/services/agent_service.py`)**:
   * 모놀리식 853라인에서 **105라인(87.7% 감축)**으로 대폭 슬림화.
   * `LifelogService`와 `GTDService`를 인스턴스화하고 상호 바인딩(`set_gtd_service`, `set_lifelog_service`)하여 순환 참조 없이 완벽한 협업 구현.
   * 모든 기존 메서드 및 속성(`_normalize_datetime`, `read_gtd_and_daily_log` 등)을 100% 동일하게 위임 노출하여 기존 테스트 및 상위 라우터/서비스의 수정 없는 100% 호환성 보장.

## 결과 및 효과 (Consequences)
* **단일 책임 원칙(SRP) 확립**: 마크다운 일일 일기와 GTD 상태/태스크 관리가 독립된 도메인 서비스로 격리되어 유지보수성과 확장성이 획기적으로 향상됨.
* **100% 하위 호환성 보장**: `tests/test_agent_service.py`, `tests/test_task_completion_and_meta_guard.py`, `tests/test_settings_service.py`, `app/routers/lifelog_router.py`, `SupervisorService`, `DevAgentService` 등 모든 호출부가 기존 인터페이스 그대로 정상 작동.
* **검증 완료**: `test_agent_service.py` 8개 전수 통과 (1.61s), 태스크 완료 및 가드레일 테스트 7개 전수 통과, `mypy` 41개 파일 무결점, `ruff` 무결점.
