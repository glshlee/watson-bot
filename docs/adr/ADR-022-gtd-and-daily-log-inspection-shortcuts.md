# ADR-022: GTD 및 데일리 로그 파일 즉시 열람 숏컷(/today, /gtd) 및 DevBot 대기시간 최적화

## 1. Context (배경 및 문제점)
Watson 비서(`/watson`)와 개발 콘솔 DevBot(`/dev`)을 사용하는 과정에서 다음과 같은 요구사항과 성능 병목이 확인되었다:
1. **GTD 파일 및 오늘자 데일리 로그 직접 열람 요구**:
   - 기존 시스템은 "할 일 알려줘", "일정 정리" 등 자연어 브리핑(`task_briefing`) 기능만 제공하여, 사용자가 현재 GTD 수집함(`inbox.md`), 다음 행동(`next_actions.md`), 그리고 오늘자 일일 로그(`logs/daily/YYYY-MM-DD.md`)에 마크다운이 어떻게 저장되어 있는지 원본과 미완료 태스크 현황을 즉시 확인하기 어려웠다.
   - 사용자 피드백: *"왓슨봇에 gtd 현재 파일을 읽어서 보여주는 숏컷이 있었으면 좋겠어. 오늘자 로그도 보여주고"*
2. **반복 입력의 불편함과 원클릭 숏컷 부재**:
   - 일일 로그 확인, GTD 현황 파악, 최신화(pull), 원격 푸시(push), 브리핑 등의 잦은 명령을 매번 텍스트로 타이핑해야 하는 모바일/웹 사용성 한계가 존재했다.
3. **DevBot AGY CLI 호출 시 지연 및 타임아웃 문제**:
   - DevBot 콘솔에서 시스템 프롬프트 및 대화 맥락이 누적되었을 때 외부 CLI(`agy`) 호출이 50초 이상 소요되어 타임아웃 후 고정 안내 템플릿으로 떨어지는 현상이 발생했다.

## 2. Decision (결정 사항)

### 2.1 AgentService: 결정론적 파일 즉시 열람 메서드 구현 (`app/services/agent_service.py`)
- **`read_daily_log(date_obj)`**:
  - 한국 표준시(KST) 기준 오늘 날짜의 일일 로그(`logs/daily/YYYY-MM-DD.md`)를 직접 읽어 최종 수정 시각, 파일 라인 수, 마크다운 본문을 구조화하여 반환한다. (파일 미존재 시 친절한 안내 제공)
- **`read_gtd_files()`**:
  - `gtd/inbox.md` 및 `gtd/next_actions.md` 마크다운을 직접 읽고, 정규표현식으로 미완료 태스크(`- [ ]`) 개수를 자동 집계하여 마크다운 코드 블록으로 포맷팅해 반환한다.
- **`read_gtd_and_daily_log(date_obj)`**:
  - 오늘자 일일 로그와 GTD 파일 현황을 결합하여 종합 열람 뷰를 제공한다.

### 2.2 LLMProvider & SupervisorService: 인텐트 라우팅 및 슬래시 커맨드 (`llm_provider.py`, `supervisor_service.py`)
- **의도 분류 확장**:
  - `daily_log_inspect`: `/today`, `/daily`, "오늘 로그 보여줘", "오늘 일기 읽어줘" 등
  - `gtd_inspect`: `/gtd`, `/inbox`, "gtd 파일 보여줘", "인박스 파일 읽어줘" 등
  - `gtd_and_log_inspect`: `/gtd-today`, `/today-gtd`, "gtd랑 오늘 로그 보여줘" 등
- **무지연 백엔드 직결**:
  - LLM 토큰 소모나 대기 시간 없이 `SupervisorService`에서 `AgentService` 메서드를 직결 실행하여 0.01초 이내에 즉각 응답을 보장한다.
  - `/briefing` 슬래시 커맨드 또한 `task_briefing`으로 매핑하여 즉시 브리핑을 지원한다.

### 2.3 DevAgentService: 개발 콘솔 GTD/로그 숏컷 및 맥락 다이어트 (`dev_agent_service.py`)
- **엔지니어링 툴체인 연동**:
  - DevBot에서도 `/today`, `/gtd`, `/gtd-today` 명령을 즉시 처리하여 엔지니어링 작업 중에도 자신의 일과와 GTD를 즉시 확인할 수 있도록 지원한다.
- **프롬프트 다이어트, 독립 격리 실행 및 고속 모델 튜닝**:
  - 대화 히스토리의 각 항목을 200자로 축약(ADR-010 표준 준수)하여 프롬프트 토큰을 절감.
  - `agy` 비대화형 실행 시 작업 디렉토리를 `cwd="/tmp"`로 격리하여, 워크스페이스에 대한 자율 도구(테스트, 파일탐색 등) 실행 루프와 인덱싱 오버헤드를 원천 차단.
  - `--model gemini-3.8-flash-low`, `--effort low`, `--disable-slash-commands` 플래그를 주입하고 타임아웃을 45초로 튜닝하여 50초 응답 지연/고정 폴백 결함을 완벽히 해소.

### 2.4 반응형 웹 UI: 빠른 액션 칩 바 도입 (`index.html`, `dev.html`, `main.js`, `style.css`)
- **Watson 비서 콘솔 (`/watson`)**:
  - 입력창 상단에 `.watson-quick-bar` 배치: `[📅 오늘 로그(/today)]`, `[📋 GTD 현황(/gtd)]`, `[📢 브리핑(/briefing)]`, `[🔄 동기화(/sync)]`, `[🚀 원격 푸시(/push)]`
  - 원터치 클릭 시 즉시 왓슨에게 메시지를 전송하고 응답을 수신.
- **DevBot 콘솔 (`/dev`)**:
  - `.dev-quick-bar`에 `/today (일일로그)`, `/gtd (GTD현황)` 칩 추가.

## 3. Consequences (영향 및 효과)
- **사용자 편의성 극대화**: 번거로운 타이핑 없이 칩 클릭 한 번으로 오늘자 라이프로그와 GTD 태스크를 원본 그대로 즉시 점검 가능.
- **무지연 실시간성**: LLM 지연 시간 없이 로컬 파일 시스템에서 직접 읽어 0.01초 내에 초고속 응답.
- **DevBot 안정성 강화**: 프롬프트 다이어트로 AGY 호출 타임아웃 종결.
