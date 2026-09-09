# ADR-018: 에이전트 허브 대시보드 포털 및 개발 전담 에이전트 분리 (Agent Hub & Dev Agent)

## 1. 배경 및 맥락 (Context)
Watson 애플리케이션은 24/7 가동되는 개인 비서이자 라이프로그 에이전트로 시작하여 일기 작성, 감정 회고, GTD 할 일 수집, 텔레그램 모바일 연동 등의 역할을 완벽히 수행해 왔다. 그러나 사용자가 소프트웨어 엔지니어링, 코드베이스 구조 분석, Git 변경점(Diff/Status/Log) 검토, 터미널 도구 실행 등 개발 업무를 요청할 때, 개인 일기/GTD 맥락과 개발 맥락이 단일 세션에 뒤섞여 프롬프트 오염 및 데이터베이스 복잡도가 증가하는 한계가 있었다.

사용자는 비서 역할을 하는 Watson 외에 **"개발도 전담할 수 있는 별도의 에이전트"**와 이를 조율하는 **"상위 대시보드 포털"** 도입을 요구하였다.

## 2. 의사결정 (Decision)
1. **상위 에이전트 허브 대시보드 포털 (`/`) 구축**:
   - 루트 경로(`/`)에 진입 시 모든 등록된 에이전트의 실시간 가동 상태, 기능 요약, 세션 현황을 한눈에 볼 수 있는 **Agent Hub Dashboard**를 제공한다.
   - 각 에이전트 카드를 클릭하면 해당 전용 콘솔로 즉시 진입할 수 있도록 라우팅 분리:
     - 👔 **Watson (Personal Butler & LifeLog)**: `/watson`
     - 💻 **DevBot (Software Engineering & Code Ops)**: `/dev`
     - ➕ **Custom Agent Slot (Expansion)**: 향후 리서처, 재무분석가 등 모듈형 확장 지원
2. **단일 FastAPI 통합 인증 & 공통 보안 (Single Sign-On)**:
   - Cloudflare Tunnel 및 HTTP Basic 인증 체계를 상위에서 공유하여 별도 로그인 없이 에이전트 간 안전한 이동 보장.
3. **에이전트별 세션 및 역할 격리 (`agent_type`)**:
   - `SessionModel`에 `agent_type: str = "watson" | "dev"` 컬럼을 추가하고 SQLite 자동 마이그레이션을 지원하여, 비서의 일기/GTD 데이터와 개발자의 소스코드/Git 로그가 서로 격리되도록 보장.
4. **Dev Agent 전용 엔지니어링 도구 (`DevAgentService`) 탑재**:
   - 워크스페이스 Git 상태 조회 (`/status`), 코드 변경점 비교 (`/diff`), 최근 커밋 히스토리 (`/log`), 브랜치 확인 (`/branch`) 등의 빠른 단축 명령을 즉시 실행.
   - 개발 시스템 프롬프트 및 워크스페이스 컨텍스트(브랜치, 수정 파일 수)를 자동 주입하여 전문적인 코딩 질의응답 및 아키텍처 제안 제공.
5. **글로벌 네비게이션 (`[🏠 에이전트 허브]` 바로가기)**:
   - 왓슨 콘솔과 개발 콘솔 상단 헤더에 에이전트 허브로 언제든 복귀할 수 있는 버튼을 제공하여 끊김 없는 멀티 에이전트 워크스페이스 UX 완성.
6. **모바일/데스크톱 세로 스크롤 정상화 & 원클릭 카드 터치 UX**:
   - 대시보드 포털(`portal.html`)에 `overflow-y: auto !important`, `-webkit-overflow-scrolling: touch`를 적용하여 모든 해상도에서 부드러운 스크롤을 보장.
   - 하단 버튼뿐 아니라 카드 본문 전체를 터치/클릭해도 즉시 전용 콘솔(`/watson`, `/dev`)로 진입할 수 있도록 인터랙션 극대화.

## 3. 결과 및 영향 (Consequences)
- **장점**:
  - 개인 일상/비서 업무와 기술/개발 업무가 완벽히 분리되어 프롬프트 간섭 및 데이터 혼선 방지.
  - 향후 제3의 에이전트(Researcher, Writer 등)를 무한히 확장할 수 있는 표준 멀티 에이전트 아키텍처 토대 마련.
  - 개발 콘솔에서 원클릭으로 Git 상태/Diff를 파악하고 코딩 지원을 받을 수 있어 생산성 극대화.
- **영향 범위**:
  - 라우팅: `GET /` (포털), `GET /watson` (왓슨 비서), `GET /dev` (개발 콘솔), `GET /api/hub/status`
  - 백엔드: `DevAgentService`, `SessionModel.agent_type`, `database.init_db()` 자동 마이그레이션
  - 프론트엔드: `app/templates/portal.html`, `app/templates/dev.html`, `portal.js`, `dev.js`, `style.css`
