# ADR-023: 모바일 뷰포트 레이아웃 안정화 & 컴포넌트 충돌 방지

## 1. Context (배경 및 문제점)
모바일 브라우저 환경(스마트폰 뷰포트 폭 360px ~ 430px)에서 Watson 비서 콘솔(`/watson`), DevBot 개발 콘솔(`/dev`), 에이전트 허브 포털(`/`)을 운영하는 과정에서 다음과 같은 UI 컴포넌트 간 충돌 및 겹침 현상이 확인되었다:

1. **상단 헤더(Top Header) 수평 충돌 및 줄바꿈 결함**:
   - 우측 프로필/배지 영역(홈, 대화 비우기/에이전트 전환, GTD 저장소 배지: 약 220px)과 좌측 영역(햄버거 버튼 + 제목 + 30자 이상의 긴 부제목 설명: 약 300px)이 한 줄에서 충돌함.
   - 모바일에서 부제목 텍스트가 3~4줄로 꺾이면서 헤더 높이가 과도하게 늘어나고 우측 버튼들과 겹쳐 시각적 붕괴 발생.
2. **하단 입력창(Input Wrapper) 3단 누적으로 인한 화면 가림 (140px~150px)**:
   - 빠른 숏컷 칩 바(`.watson-quick-bar`) + 카테고리 셀렉트 바(`.category-bar`) + 텍스트 입력창(`.input-row`)이 수직으로 누적되어 하단 고정 높이가 150px에 육박함.
   - 가상 키보드가 올라오거나 작은 뷰포트에서 화면의 40~50%를 덮어 채팅 메시지를 가리고, 360px 기기에서 카테고리 셀렉트와 Auto Git Push 배지가 서로 맞닿아 줄바꿈 및 겹침 발생.
3. **마크다운 코드 블록 및 GTD 표의 Flex Child Overflow 현상**:
   - `/today`, `/gtd`, `/test`, `/diff` 등 긴 마크다운 코드 블록(`<pre class="code-block">`)이나 테이블이 출력될 때, CSS Flex 자식 기본값(`min-width: auto`)으로 인해 말풍선이 화면 우측 밖으로 삐져나가면서 아바타 아이콘을 밀어내고 페이지 전체에 원치 않는 좌우 스크롤을 유발함.
4. **추천 액션 버튼(`.quick-actions-container`) 오프셋 충돌**:
   - 라이프로그 제안 버튼군이 고정된 38px 좌측 마진으로 인해 좁은 화면에서 비대칭적으로 줄바꿈되거나 상단 말풍선과 여백이 뭉개짐.

## 2. Decision (결정 사항)

### 2.1 상단 헤더 슬림화 및 충돌 격리 (`index.html`, `dev.html`, `style.css`)
- **긴 부제목 텍스트 모바일 숨김**:
  - `p#chat-subtitle`에 `.desktop-only` 클래스를 부여하여 모바일(`<= 768px`)에서는 헤더 부제목을 자동 숨김 처리.
- **우측 배지 아이콘 전용 컴팩트화**:
  - 모바일에서 홈 버튼, 대화 비우기, DevBot 전환 버튼을 `34x34px` 정사각형 터치 아이콘 버튼으로 정돈.
  - `#gtd-storage-badge` 및 `#gtd-path-text`의 최대 폭을 50px로 축약하고 말줄임표(`ellipsis`)를 적용하여 360px 초소형 화면에서도 헤더 좌우 겹침을 완전 차단.
- **Flex Child Containment**:
  - `.header-left`와 `.header-title`에 `min-width: 0; overflow: hidden;` 및 `white-space: nowrap; text-overflow: ellipsis;`를 엄격 적용.

### 2.2 하단 입력 독(Input Dock) 초슬림화 & 50% 높이 다이어트 (`style.css`)
- **인라인 가로 스크롤 칩 바**:
  - `.watson-quick-bar`와 `.dev-quick-bar`의 불필요한 배경/테두리/패딩을 제거하고, `white-space: nowrap; -webkit-overflow-scrolling: touch; scrollbar-width: none;`의 유려한 가로 스크롤 필(Pill) 툴바로 개편.
- **카테고리 셀렉트 & 입력창 최적화**:
  - 카테고리 셀렉트 높이를 28px로 컴팩트화하고 마진을 5px로 압축.
  - 텍스트 입력창 높이를 40px로 정돈하여 하단 입력 영역 전체 높이를 140px에서 **75px~80px**로 50% 슬림화.
  - 가상 키보드 팝업 시에도 메시지 가시 면적을 70% 이상 확보.

### 2.3 Flex Overflow 원천 차단 및 아바타 고정 (`style.css`)
- `.message`, `.bubble`, `.code-block`에 `min-width: 0; word-break: break-word; overflow-wrap: anywhere;` 적용.
- `.message .avatar`에 `flex-shrink: 0;`을 영구 지정하여 긴 텍스트/코드 블록이 들어와도 아바타가 절대 찌그러지거나 밀려나지 않도록 보호.
- `<pre class="code-block">`에 `max-width: 100%; box-sizing: border-box; overflow-x: auto;`를 적용하여 말풍선 내부에서만 안전하게 가로 스크롤되도록 격리.

### 2.4 추천 액션 버튼 및 대시보드 그리드 반응형 정돈
- `.quick-actions-container`의 좌측 마진을 아바타 기준선(40px)으로 정렬하고, 400px 이하 초소형 화면에서는 `margin-left: 0;`으로 유연 전환.
- 에이전트 허브 포털의 메트릭 카드 4종을 모바일에서 `grid-template-columns: repeat(2, 1fr);`의 2x2 컴팩트 그리드로 재배치하여 불필요한 세로 스크롤 억제.
- 정적 자산 캐시 방지를 위해 템플릿의 CSS 버전을 `v=1.3.2`로 일괄 업데이트.

## 3. Consequences (영향 및 효과)
- **컴포넌트 겹침/충돌 100% 해소**: 360px ~ 430px 모든 모바일 뷰포트에서 헤더, 칩 바, 입력창, 말풍선 간의 텍스트 밀림이나 겹침이 완전히 사라짐.
- **메시지 영역 가시성 대폭 향상**: 하단 고정 높이가 절반으로 줄어들어 작은 모바일 화면에서도 대화 흐름을 시원하게 파악 가능.
- **터치 편의성 및 반응성 보장**: 지저분한 스크롤바 없는 네이티브 앱 감각의 부드러운 가로 스와이프 칩 바 제공.
