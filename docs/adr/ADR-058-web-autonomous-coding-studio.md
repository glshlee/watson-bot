# ADR-058: 웹 기반 자율 코딩 스튜디오 (Web Autonomous Coding Studio & Self-Healing Loop)

## 1. 개요 (Context)
* **배경**:
  * DevBot(소프트웨어 엔지니어링 전담 에이전트 콘솔)은 Git 관리, 테스트/린트 실행 및 로드맵/스킬 인스펙터를 지원하나, 웹 콘솔 환경에서 워크스페이스 내 소스코드를 직접 탐색하고, 구문 하이라이트된 코드를 읽고, 안전하게 수정(패치) 및 롤백할 수 있는 자율 코딩 스튜디오 기능이 부재했다.
  * 또한 단위 테스트나 코드 검증 실패 시 에러 트레이스를 신속히 분석하여 실패 지점과 예외 유형을 진단하고 자가 치유(Self-Healing)를 유도하는 툴체인이 필요했다.
* **보안 및 무결성 과제**:
  * 웹 콘솔을 통한 소스코드 접근 시 상위 디렉토리 탈출(Path Traversal: `../../etc/passwd`) 및 환경 변수(`.env`), Git 메타데이터(`.git`), DB 파일(`watson.db`) 등 민감 파일 접근을 철저히 차단해야 한다.
  * 임의 코드 수정 시 기존 파일이 손상되지 않도록 자동 백업(`.backups/`) 및 즉시 롤백(Rollback) 복원 메커니즘이 보장되어야 한다.

---

## 2. 의사결정 (Decision)

### 2.1 자율 코딩 스튜디오 전담 서비스 구축 (`CodingStudioService`)
1. **보안 경로 해석기 (`resolve_safe_path`)**:
   * `os.path.normpath`와 `startswith(workspace_path)` 검증으로 디렉토리 탈출 공격을 원천 차단(PermissionError).
   * `.git`, `venv`, `__pycache__`, `.env`, `watson.db`, `.watson.pid` 등 민감 디렉토리 및 파일에 대한 블랙리스트 검증을 강제.
2. **워크스페이스 파일 탐색 (`list_workspace_files`)**:
   * 서브 디렉토리 필터링 및 최대 깊이 제한(max_depth=3)으로 빠른 파일 트리 목록 제공.
   * 파일명, 상대 경로, 파일 크기, 라인 수 및 언어(Language) 자동 감지 메타데이터 반환.
3. **소스코드 안전 열람 (`read_code_file` / `format_code_card`)**:
   * 시작 라인(start_line)과 종료 라인(end_line) 슬라이싱을 지원하여 대용량 파일도 부하 없이 열람.
   * 언어별 코드 블록 및 `/diff`, `/test`, `/rollback` 연계 인터랙티브 액션 버튼 카드 렌더링.
4. **Unified Diff 프리뷰 & 안전 패치 (`generate_diff_preview` / `apply_code_patch`)**:
   * Python `difflib` 기반 Unified Diff 생성으로 변경 전/후 라인 단위 비교.
   * 패치 적용 전 `.backups/{rel_path}.{timestamp}.bak` 자동 백업을 생성하여 0초 무손실 복원 지원.
5. **무손실 백업 롤백 (`rollback_file`)**:
   * 가장 최근 백업 또는 특정 백업 ID를 역참조하여 원본 파일을 즉시 복원.
6. **자가 치유(Self-Healing) 진단 엔진 (`diagnose_test_failure`)**:
   * Pytest 오류 출력 정규식 분석으로 예외 유형(`AssertionError` 등), 실패 파일 및 라인 번호(`tests/xxx.py:line`), 대상 함수명을 도출하고 대화형 진단 리포트 생성.

### 2.2 DevBot 콘솔 명령어, 웹 스튜디오 모달 및 REST API 연동
1. **인브라우저 웹 코딩 스튜디오 모달 (`#code-studio-modal` & `code_studio_modal.js`)**:
   * 좌측 워크스페이스 파일 트리 사이드바(실시간 필터링 및 새로고침) + 상단 탭 전환(코드 에디터 vs Diff 프리뷰).
   * 고정밀 모노스페이스 텍스트에디터: Tab 키 들여쓰기(2스페이스), 단축키 `Ctrl+S` 즉시 패치 저장 지원.
   * 실시간 Diff 비교(`generate_diff_preview`), 인플레이스 패치 적용(`apply_code_patch`), 무손실 롤백(`rollback_file`) 및 단위 테스트 비동기 실행 버튼 탑재.
2. **DevBot 자율 코드 구현 엔진 (`_handle_autonomous_implementation`)**:
   * 사용자가 채팅창에서 코드 구현/수정을 요청하면("구현해줘", "코드 수정해줘", `/implement`, `/patch`), 단순 구두 설명에 그치지 않고 워크스페이스 내 대상 파일에 수술적 패치(Surgical Patch)를 자동 생성 및 적용.
   * 패치 적용 즉시 자동 백업(`.backups/`) 생성, `pytest` 단위 테스트 자동 검증, 실시간 Unified Diff 및 툴체인 연계 카드(`format_patch_card`) 반환.
   * 치환 대상 불일치 시 자동으로 웹 스튜디오(`tool_studio_open`)를 실행하여 사용자가 브라우저에서 즉시 수동 확인/편집할 수 있도록 안전 폴백 제공.
3. **슬래시 명령어 라우팅 (`DevAgentService`)**:
   * `/studio [파일경로]`: 웹 에디터 및 Diff 프리뷰 스튜디오 모달 즉시 실행 (`action_type=tool_studio_open`).
   * `/implement [지시]`: 자율 코드 구현 및 수술적 패치 적용, 단위 테스트 검증.
   * `/patch [파일|target|replacement]`: 지정 코드 블록 수술적 치환 패치 집행.
   * `/files [경로]`: 워크스페이스 소스 파일 탐색기 카드 제공 및 파일별 `[열람]` / `[편집(스튜디오)]` 원터치 버튼 배치.
   * `/code [파일경로]`: 지정 파일 소스코드 실시간 열람 및 `[웹 스튜디오에서 편집]` 연계.
   * `/rollback [파일경로]`: 최근 백업 시점으로 파일 안전 원상 복구.
   * `/heal`: 단위 테스트 실행 및 실패 시 자가 치유 진단 리포트 렌더링.
4. **REST API 엔드포인트 (`app/routers/web_router.py`)**:
   * `GET /api/dev/code/tree`: 워크스페이스 파일 목록 조회.
   * `GET /api/dev/code/file`: 소스코드 파일 열람 (403/404 안전 예외 반환).
   * `POST /api/dev/code/patch`: Diff 생성(`dry_run=true`) 또는 패치 적용.
   * `POST /api/dev/code/rollback`: 백업 기반 롤백 복원.
   * `POST /api/dev/code/self-heal`: Pytest 자가 치유 분석 실행.
5. **프론트엔드 UI 연동**:
   * `templates/dev.html`: 상단 헤더에 `[💻 스튜디오]` 원터치 퀵 버튼 및 `#code-studio-modal` 템플릿 임포트.
   * `templates/modals/code_studio_modal.html`: 파일 트리, 탭 전환, 에디터, Diff 뷰어, 롤백/테스트 액션 바.
   * `templates/modals/command_palette_dev.html`: 코딩 스튜디오 그룹 6종 도구 확충 및 총 23개 도구 팔레트로 확장.
   * `app/static/js/modules/code_studio_modal.js`: 스튜디오 모달 전담 컨트롤러(IIFE).
   * `app/static/js/dev.js`: 스튜디오 퀵 버튼, 말풍선 내 `[data-open-studio]` 클릭 위임, `tool_studio_open` 이벤트 연동.
   * `app/static/css/dev.css`: 스튜디오 모달 전용 레이아웃, 사이드바, 에디터, 컬러 Diff 및 반응형 스타일 추가.

---

## 3. 구현 세부사항 (Implementation)

| 파일 | 역할 및 변경 내용 |
| :--- | :--- |
| `app/services/coding_studio_service.py` | 경로 보안, 파일 탐색, 코드 열람, Diff 생성, 백업/패치/롤백, 테스트 실패 진단, 패치 카드 포맷 신설 |
| `app/services/dev_agent_service.py` | 자율 코드 구현 엔진(`_handle_autonomous_implementation`), `/studio`, `/implement`, `/patch` 라우팅 |
| `app/templates/modals/code_studio_modal.html` | 웹 자율 코딩 스튜디오 모달 UI (파일트리 + 에디터 + Diff 프리뷰) |
| `app/static/js/modules/code_studio_modal.js` | 코딩 스튜디오 브라우저 컨트롤러 (Tab 들여쓰기, Ctrl+S, 실시간 Diff, 롤백, 테스트) |
| `app/templates/dev.html` | 스튜디오 모달 및 JS 모듈 임포트, 상단 `[💻 스튜디오]` 퀵 버튼 배치 |
| `app/routers/web_router.py` | `/api/dev/code/tree`, `/api/dev/code/file`, `/patch`, `/rollback`, `/self-heal` 엔드포인트 추가 |
| `app/templates/modals/command_palette_dev.html` | 코딩 스튜디오 전용 그룹 신설 및 23종 명령어 팔레트 갱신 |
| `app/static/js/dev.js` | 스튜디오 퀵 버튼, `data-open-studio` 클릭 이벤트 위임, `tool_studio_open` 연동 |
| `app/static/css/dev.css` | 코딩 스튜디오 모달 전용 다크 테마, 사이드바, 에디터, 컬러 Diff 라인 스타일 |
| `tests/test_coding_studio_service.py` | 코딩 스튜디오 7종 단위 테스트 스위트 신설 |
| `tests/test_dev_agent.py` | 스튜디오 및 자율 구현, REST API 전수 검증 테스트 케이스 추가 |
| `scripts/smoke_test.sh` | 8-9 ~ 8-13 cURL 라이브 API 검증 단계 추가 |

---

## 4. 검증 결과 (Verification)
1. **단위 테스트**: `pytest` 143개 전수 통과 (100% Passed).
2. **정적 검사**: `ruff check .` 및 `mypy app/` 오류 제로(0).
3. **cURL 라이브 검증**: `./scripts/smoke_test.sh` 100% 통과 (Exit Code 0).
