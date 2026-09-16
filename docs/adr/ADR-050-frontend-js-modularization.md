# ADR-050: 프론트엔드 자바스크립트(JS) 모듈화 및 모달 컨트롤러 분리 (Frontend JS Modularization Architecture)

## 상태 (Status)
**채택됨 (Accepted)** - 2026-09-16 구현 및 단위 테스트/cURL 라이브 검증 완료

## 맥락 (Context)
* `app/static/js/main.js`는 시스템의 지속적인 기능 확장(세션 관리, 실시간 채팅, 연결 복원력, GTD/스케줄/출근길/텔레그램메뉴/잔디에디터 등 5종 모달)에 따라 1,984라인에 달하는 거대 모놀리식 스크립트로 비대화되었습니다.
* 또한 개발 전담 콘솔인 `app/static/js/dev.js`에도 네트워크 재시도(`fetchWithRetry`), 헬스체크/연결 UI, KST 디지털 시계(`updateLiveClock`) 등의 유틸리티 코드가 중복 구현되어 있었습니다.
* 이에 따라 점진적 리팩터링 계획(Phase 2)에 의거하여, 복잡한 번들러(Webpack/Vite) 도입 없이 브라우저 네이티브 환경에서 즉시 동작하는 네임스페이스(`window.Watson*`) 기반 유틸리티 및 전용 모달 컨트롤러 분리 아키텍처를 수립했습니다.

## 결정 (Decision)
1. **공통 유틸리티 모듈 분리 (`app/static/js/utils/`)**:
   * `api.js` (114라인): 네트워크 지수 백오프 재시도(`fetchWithRetry`), 헬스체크 주기 폴링(`checkHealth`), 온라인/오프라인/경고 상태 배너 UI 제어(`updateConnectionUI`), `window.WatsonAPI` 네임스페이스로 익스포트.
   * `date.js` (75라인): KST 기준 날짜 계산(`getKSTDateString`), 상대 시간 포맷터(`formatRelativeTime`), 상단 헤더 디지털 시계 실시간 갱신(`updateLiveClock`), `window.WatsonDate` 네임스페이스로 익스포트.
   * `modal.js` (39라인): 모달 백드롭 클릭/ESC 키 닫기(`setupModalDismiss`), `openModal`/`closeModal`, XSS 방지 HTML 이스케이프(`escapeHtml`), `window.WatsonModal` 네임스페이스로 익스포트.
2. **5대 도메인 전용 모달 컨트롤러 분리 (`app/static/js/modules/`)**:
   * `gtd_modal.js` (124라인): GTD 저장소 경로 설정, 원격 저장소 동기화 상태 조회 및 저장 (`window.WatsonGTD`).
   * `schedule_modal.js` (215라인): 아침(08:30)/저녁(20:00) 브리핑 타임라인 렌더링, 수동 푸시 트리거 및 숏컷 연동 (`window.WatsonSchedule`).
   * `commute_modal.js` (326라인): 거주지 스마트 지오코딩 자동 매핑, 버스 정류소 번호(ARS-ID) 실시간 역조회, 출근 설정 저장 및 실시간 카드 프리뷰 (`window.WatsonCommute`).
   * `telegram_modal.js` (282라인): 14종 슬래시 명령어 CRUD, 모바일 폰 목업 실시간 미리보기, Telegram Bot API 동기화 및 기본값 복원 (`window.WatsonTelegram`).
   * `editor_modal.js` (317라인): 365일 연간 잔디(Heatmap) 그리드 렌더링, 일일 로그 파일 로드, 마크다운 분할 에디터 및 원터치 커밋·저장 (`window.WatsonEditor`).
3. **메인 컨트롤러 경량화 (`app/static/js/main.js`)**:
   * 모놀리식 1,984라인에서 **662라인(66.6% 대폭 감축)**으로 경량화.
   * 순수 세션 관리(목록/필터/검색/이름변경/삭제/비우기), 실시간 채팅 메시지 송수신/렌더링, 퀵 칩 바 및 라이프사이클 디스패치에만 집중하도록 단일 책임 원칙(SRP) 확립.
4. **DevBot 스크립트 중복 제거 (`app/static/js/dev.js`)**:
   * 중복 구현되었던 `WatsonAPI` 및 `WatsonDate` 유틸리티를 공통 재사용하도록 리팩터링하여 코드 중복 해소.
5. **템플릿 스크립트 순서 보장 (`index.html`, `dev.html`)**:
   * `utils/` ➔ `modules/` ➔ `main.js` 순으로 순서 종속성을 완벽히 보장하여 빌드 단계 없이 100% 네이티브 구동 보장.

## 결과 및 효과 (Consequences)
* **모듈별 단일 책임 및 유지보수성 극대화**: 각 모달 기능 수정 시 메인 채팅 엔진과의 간섭이 원천 차단되어 독립적 기능 확장 및 디버깅 용이.
* **코드 중복 제거**: 왓슨 메인 콘솔과 DevBot 콘솔 간의 핵심 공통 유틸리티(API 재시도, KST 날짜) 재사용 달성.
* **빌드리스(Build-less) 네이티브 안정성**: Node.js/번들러 환경 설정 없이 순수 브라우저 스크립트 태그만으로 동작하여 배포 복잡도 제로 유지.
* **검증 완료**: `pytest` 100% 통과, `mypy` 및 `ruff` 정적 검사 무결점, `./scripts/smoke_test.sh` 40+개 라이브 테스트 전수 통과.
