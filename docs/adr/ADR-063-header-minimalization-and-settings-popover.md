# ADR-063: 웹 콘솔 상단 헤더 미니멀화 및 `[⚙️ 설정]` 드롭다운 팝오버 통합 (Header Minimalization & Unified Settings Popover)

## 1. 개요 (Context)
* **배경**:
  * 기존 웹 콘솔(`/watson` 및 `/dev`)의 상단 헤더 우측(`.user-profile`)에는 최대 10개의 배지(`에이전트 허브`, `대화 비우기`, `KST 시계`, `연속 잔디`, `출근 설정`, `텔레그램 메뉴`, `GTD 경로`, `AGY / LLM`, `Auto Push`, `GitHub 아이콘`)가 한 줄에 나열되어 있었다.
  * 이로 인해 일반 노트북/태블릿/데스크톱 뷰포트에서 좌측 세션 타이틀(`.header-left`) 공간이 압박되어 텍스트 줄바꿈 및 겹침(Overlap)이 발생하고 시각적 피로도가 높았다.
  * 또한 `gtd_modal.js`에서 `#gtd-path-display`만 참조하고 `#gtd-path-text` 폴백이 누락되어 헤더의 GTD 경로 텍스트가 `"GTD: 로딩 중..."`에 머무르는 결함이 있었다.

---

## 2. 의사결정 (Decision)

### 2.1 상단 헤더 핵심 배지 슬림화 (`app/templates/index.html`, `dev.html`)
1. **왓슨 콘솔(`/watson`) 상단 바**:
   * 상시 노출 항목을 **핵심 4종**(`🏠 에이전트 허브`, `📅 연속 기록(잔디) & 에디터`, `🕒 실시간 KST 시계`, `🎛️ [설정 ▾]`)으로 축소하여 여유로운 타이틀 영역과 모던한 레이아웃을 확보한다.
2. **DevBot 콘솔(`/dev`) 상단 바**:
   * 상시 노출 항목을 `🏠 에이전트 허브`, `🤖 비서 Watson`, `💻 스튜디오`, `🕒 KST 시계`, `🎛️ [도구 ▾]`로 정돈한다.

### 2.2 통합 `[⚙️ 설정 / 도구]` 팝오버 드롭다운 메뉴 (`#header-settings-dropdown`)
1. **기존 DOM ID 100% 하위 호환 유지**:
   * `#gtd-storage-badge`, `#commute-settings-badge`, `#telegram-menu-badge`, `#clear-chat-btn`, `#btn-dev-roadmap-quick`, `#btn-dev-skills-quick` 등 모든 기존 ID를 드롭다운 아이템 내부에 그대로 보존하여 기존 모달 컨트롤러(`gtd_modal.js`, `commute_modal.js`, `telegram_modal.js`, `main.js`, `dev.js`)와 100% 호환되도록 구성한다.
2. **드롭다운 인터랙션 (`app/static/js/utils/modal.js`)**:
   * `initHeaderSettingsDropdown()`을 통해 버튼 클릭 토글, 메뉴 항목 선택 시 자동 닫힘, 외부 영역 클릭 닫기(Light Dismiss), `Escape` 키 닫기를 지원한다.
3. **GTD 경로 텍스트 바인딩 수정 (`app/static/js/modules/gtd_modal.js`)**:
   * `document.getElementById("gtd-path-display") || document.getElementById("gtd-path-text")`로 보완하여 실제 연결된 GTD 저장소 경로 및 Git 상태(`⚡Git`)가 즉시 표시되도록 수정한다.

---

## 3. 결과 및 영향 (Consequences)
* **장점**:
  * 상단 헤더 우측 배지 수를 10개에서 4개로 60% 감축하여 어떤 해상도에서도 타이틀(`New Conversation` 등)과 배지가 절대 겹치지 않음.
  * 설정 항목들이 아이콘 + 제목 + 현재 설정값 부제로 구성된 카드형 드롭다운 메뉴에 정리되어 가독성과 조작성이 대폭 향상됨.
