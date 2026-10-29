# ADR-065: 리치 마크다운 뷰어(Rich Markdown Viewer) 및 라이프로그·GTD 타이포그래피 고도화

## 1. 배경 및 문제 정의 (Context & Problem)
* 기존 Watson 웹 콘솔(`/watson`, `app/static/js/main.js`)의 채팅 말풍선(`appendMessage`)은 AI 응답을 `textContent.innerText = text`로 출력하고 있어, `/gtd`, `/today`, `/briefing` 등 마크다운 문서나 브리핑을 조회할 때 `###`, `**굵은 글씨**`, `` `코드` ``, `---`, `- [ ]` 등의 마크다운 기호가 파싱되지 않고 원문 그대로 노출되어 가독성이 떨어졌습니다.
* 또한 일일 로그/GTD 분할 에디터 모달(`app/static/js/modules/editor_modal.js`)의 미리보기 함수(`renderMarkdownToHtml`)는 단순 정규식 치환 후 모든 개행(`\n`)을 일괄 `<br />`로 치환하여 제목(`<h2>`, `<h3>`)과 목록(`<li>`) 사이에 불필요한 공백 줄이 생기고, GTD 체크리스트나 시간 배지(`[HH:MM]`)가 평면적으로 보이는 문제가 있었습니다.

## 2. 결정 사항 (Decision)
1. **공통 리치 마크다운 렌더러(`window.WatsonMarkdown.render`) 구축**:
   * `app/static/js/utils/modal.js`에 외부 라이브러리 의존성 없는 안전한 블록/인라인 마크다운 파서 `renderRichMarkdown(markdown)`를 구현하고 전역 `window.WatsonMarkdown.render`로 노출합니다.
   * XSS 방지를 위해 원문을 `escapeHtml()`로 이스케이프한 뒤, 코드 블록(` ```lang `) 보호 ➔ 줄 단위 블록 구조(`h1`~`h4`, `hr`, `blockquote`, 마크다운 `table`, GTD 태스크 리스트 `- [ ]`/`- [x]`, 일반/번호 목록, 단락) 파싱 ➔ 인라인 문법(`**bold**`, `*italic*`, `` `code` ``, `[link](url)`) 순서로 변환합니다.
2. **라이프로그 & GTD 특화 배지 및 체크박스 카드 시각화**:
   * GTD 할 일 목록(`- [ ]`, `- [x]`)을 카드형 `.md-task-item` 컴포넌트(체크 아이콘 배지 + 완료 취소선/그린 하이라이트)로 렌더링합니다.
   * 일일 로그 타임스탬프(`[HH:MM]`)는 스카이 블루 타임 배지(`.md-time-badge`)로, GTD 마감일 태그(`~YYYY-MM-DD`, `@due(...)`)는 앰버 캘린더 배지(`.md-due-pill`)로 자동 하이라이팅합니다.
3. **웹 채팅 콘솔 및 모달 프리뷰 전역 적용**:
   * `/watson` 채팅 콘솔(`main.js`의 `appendMessage`), 라이프로그 분할 에디터 실시간 프리뷰(`editor_modal.js`), 출근길 브리핑 미리보기(`commute_modal.js`)에 `window.WatsonMarkdown.render()`와 `.markdown-body` / `.md-viewer-root` 타이포그래피(`app/static/css/chat.css`)를 일괄 적용합니다.
   * 실시간 버스 도착 갱신 버튼(`.btn-bus-refresh`) 동작 시에도 `dataset.rawMarkdown`을 보존하여 리치 마크다운 렌더링이 깨지지 않도록 보장합니다.

## 3. 결과 및 영향 (Consequences)
* `/today`, `/gtd`, `/briefing` 조회 및 일상 대화 시 마크다운 기호 노출 없이 노션/깃허브 스타일의 깔끔한 카드형 할 일 목록, 섹션 헤더, 타임스탬프 배지로 시각적 가독성이 대폭 향상되었습니다.
