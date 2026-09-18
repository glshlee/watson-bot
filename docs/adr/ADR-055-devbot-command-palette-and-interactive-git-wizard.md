# ADR-055: DevBot 콘솔 UI 미니멀화 및 인터랙티브 Git 위저드 (DevBot Command Palette & Interactive Git Wizard)

## 상태 (Status)
**채택됨 (Accepted)** - 2026-09-18 구현 및 라이브 cURL/정적 파일/Pytest 전수 검증 완료

## 맥락 (Context)
* DevBot 콘솔(`/dev`)의 입력창 상단에는 엔지니어링 도구 확장에 따라 총 20개의 칩 버튼(`dev-quick-bar`)이 상시 가로 스크롤로 노출되어 있었습니다.
* 이로 인해 모바일 및 PC 화면에서 입력창 영역이 비대해지고 시각적 노이즈가 발생했으며, 원하는 도구를 찾기 위해 긴 좌우 스크롤을 반복해야 했습니다.
* 또한, 코드 수정 후 커밋을 진행할 때 `/commit` 추천 메시지가 평문 마크다운으로만 출력되어 사용자가 추천 메시지를 일일이 복사하거나 재입력해야 하는 번거로움이 있었습니다.
* 커밋 이후 원격 저장소(`origin/main`)에 변경 사항을 반영하기 위해 필요한 `/push` 및 원격 동기화 `/sync` 명령어가 DevBot 백엔드 핸들러에 부재하여 CLI 터미널에 의존해야 했습니다.
* 이에 따라 ADR-054의 미니멀 팝오버 설계를 DevBot 환경에 맞게 특화하고, 대화형 Git 워크플로우(Conventional Commits 3종 원클릭 커밋 및 원터치 푸시 배너)와 다크 IDE 터미널 박스를 완벽히 통합하기로 결정했습니다.

## 결정 (Decision)
1. **DevBot 상시 20개 칩 바 철거 및 `[/]` 팔레트 액션 버튼 도입**:
   * 입력창 상단의 고정 칩 바(`.dev-quick-bar`)를 전면 철거하여 순수한 코딩 페어 프로그래밍 대화 공간 확보.
   * `.input-row` 좌측에 에메랄드 테마의 모던한 사각 라운드형 `[/]` 액션 버튼(`#btn-dev-palette.dev-trigger`) 배치.
2. **DevBot 전용 플로팅 커맨드 팔레트 컴포넌트 신설 (`app/templates/modals/command_palette_dev.html`)**:
   * 16대 핵심 개발 엔지니어링 도구를 3대 카테고리로 체계적 그룹화:
     * 🛠️ **Git 버전 관리 (Git Ops)**: `/status` (상태 점검), `/diff` (코드 변경점 비교), `/commit` (커밋 추천 & 위저드), `/push` (원격 저장소 푸시), `/sync` (원격 최신화), `/log` (커밋 로그 히스토리).
     * 🧪 **품질 & 엔지니어링 (Quality & Test)**: `/test` (pytest 단위 테스트), `/lint` (ruff/mypy 정적 린트), `/setup` (배포 환경 7단계 진단).
     * 📋 **비서 연동 & 유틸리티 (Butler & Tools)**: `/today` (오늘 로그), `/gtd` (GTD 현황), `/dday` (D-Day 마감일), `/briefing morning` (아침 브리핑), `/search` (로그/GTD 검색), `/help` (전체 도구 가이드).
   * 전용 `[✕ 닫기]` 버튼, 터치 백드롭, 키보드 단축키 안내 및 실시간 검색 카운트 배지 탑재.
3. **재사용 가능한 커맨드 팔레트 컨트롤러 모듈 확장 (`app/static/js/modules/command_palette.js`)**:
   * 커스텀 요소 주입(`options`) 패턴을 도입하여 Watson 콘솔과 DevBot 콘솔이 동일한 고성능 검색/키보드 내비게이션/모바일 터치 엔진을 공유하도록 일반화.
   * `dev.js`에서 DevBot 전용 ID들을 주입하여 인스턴스화하고, `/` 타이핑 시 실시간 필터링 및 방향키/Enter 원클릭 실행 지원.
4. **인터랙티브 Conventional Commits 추천 & 원터치 커밋 위저드**:
   * `/commit` (인자 없음) 실행 시 현재 Git Diff 및 변경 파일을 분석하여 3종 Conventional Commits(`feat`, `fix`, `refactor`) 추천 카드와 함께 원클릭 실행 버튼(`.dev-btn-action.dev-btn-commit`)을 즉시 렌더링.
   * 추천 버튼 클릭 시 추가 타이핑 없이 백엔드로 `/commit <선택된 메시지>`를 즉시 전송하여 안전한 스테이징 및 커밋 집행.
5. **결정론적 원터치 원격 푸시 & 동기화 도구 탑재**:
   * 커밋 성공 시 말풍선 하단에 `[🚀 GitHub 원격 푸시 (/push)]` 원터치 액션 배너(`.dev-push-banner`)를 부착.
   * `_run_git_push()` 및 `_run_git_sync()` 핸들러를 신설하여 웹 콘솔에서 즉시 GitHub 원격 저장소(`origin/main`)에 푸시 및 autostash 동기화 집행.
6. **다크 IDE 터미널 박스 및 안전한 HTML 위젯 렌더러 (`dev.css`, `dev.js`)**:
   * `/diff`, `/test`, `/lint`, `/push`, `/sync` 결과를 JetBrains Mono 기반의 세련된 다크 터미널 박스(`.dev-terminal-box`)로 시각화.
   * `formatMarkdown()`에서 DevBot 안전 위젯 태그(`div`, `button`, `span`, `pre`, `code`, `i`, `strong`, `p`, `kbd`)의 선택적 복원을 지원하여 XSS 위험 없이 인터랙티브 액션 버튼을 완벽 렌더링.

## 결과 및 효과 (Consequences)
* **미니멀 & 하이엔드 개발자 콘솔 UX 확립**: 상단 20개 버튼이 사라져 넓고 쾌적한 에디터/터미널 스타일의 몰입형 인터페이스 완성.
* **터미널 없는 엔지니어링 루프 완성**: 변경점 검토(`/diff`) ➔ 단위 테스트(`/test`) ➔ 린트 검사(`/lint`) ➔ 3종 커밋 추천(`/commit`) ➔ 원터치 푸시(`/push`) 전 과정을 웹 브라우저 내에서 0초 지연으로 원터치 집행 가능.
* **웹 기반 자율 코딩 스튜디오 (Web Autonomous Coding Agent) 로드맵의 1단계 초석 완성**: 향후 웹에서 자연어 구현 지시 및 자동 파일 수정·테스트·커밋을 수행할 수 있는 기반 도구 체계 완비.
