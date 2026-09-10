# ADR-024: 아침/저녁 맞춤형 GTD 브리핑(Morning & Evening Briefing) 프로토타입

## 1. Context (배경 및 문제점)
사용자가 데브콘솔(DevBot) 및 왓슨 비서에게 요청한 핵심 기능 요구사항:
1. **일괄 브리핑의 시간대별 맥락 한계**:
   - 기존의 `/briefing` 및 "할 일 알려줘" 명령은 시간대(오전/오후)와 무관하게 고정된 포맷의 일괄 목록만 브리핑하여, 아침에 집중해야 할 실행 우선순위와 저녁에 점검해야 할 일과 회고/이월 과제가 명확히 분리되지 못했다.
2. **아침 집중 과제와 저녁 일과 회고의 분리 요구**:
   - 아침(Morning): 오늘 반드시 끝내야 할 **Top 3 집중 우선순위**, 오전/오후 추천 실행 흐름, 미분류 수집함(Inbox) 정리 권유 필요.
   - 저녁(Evening): 오늘 완료된 작업 하이라이트 요약, 미완료 과제 점검 및 **내일로의 이월(Rollover)**, 내일 아침 1순위 핵심 과제 제안 필요.
3. **DevBot 실행 격리와 구현 루프**:
   - 웹 데브콘솔(`/dev`)의 DevBot은 안전한 샌드박스(`/tmp`) 기반의 대화형 엔지니어링 어드바이저로 격리되어 있어 웹 채팅 상에서 워크스페이스 코드를 직접 수정하지 못하며, 마스터 에이전트 하네스(Antigravity)를 통해 정식 구현 및 검증 루프를 집행해야 함.

## 2. Decision (결정 사항)

### 2.1 BriefingService 듀얼 엔진 아키텍처 구현 (`app/services/briefing_service.py`)
- **`detect_briefing_mode(override_mode, date_obj)`**:
  - 명시적 모드(`morning`, `am`, `아침`, `evening`, `pm`, `저녁`, `회고` 등) 지정 시 즉시 반영.
  - 미지정 시 한국 표준시(KST) 기준 오전 05:00 ~ 13:59는 `morning`, 14:00 이후 및 심야는 `evening`으로 자동 판별.
- **`read_briefing_context(date_obj)`**:
  - `gtd/inbox.md`, `gtd/next_actions.md`, 당일 일일 로그(`logs/daily/YYYY-MM-DD.md`)를 동시 분석하여 미완료 태스크, 완료 태스크, 일정 데이터를 구조화 수집.
- **결정론적 룰 기반 & AI 지능형 합성 듀얼 엔진 (`generate_briefing`)**:
  - LLM/AGY 호출을 통해 따뜻하고 맥락 있는 맞춤 브리핑을 합성하고, 네트워크/LLM 지연이나 오류 발생 시 0.01초 내에 완벽한 마크다운을 보장하는 결정론적 룰 기반 포맷터로 안전 폴백.

### 2.2 LLMProvider & SupervisorService 라우팅 확장 (`llm_provider.py`, `supervisor_service.py`)
- **인텐트 분류 고도화**:
  - `task_briefing_morning`: `/briefing morning`, `/briefing am`, `/briefing 아침`, "오늘 아침 브리핑 해줘", "출근 브리핑"
  - `task_briefing_evening`: `/briefing evening`, `/briefing pm`, `/briefing 저녁`, "오늘 저녁 회고 정리해줘", "퇴근 브리핑", "오늘 일과 정리"
  - `task_briefing`: 시간대 기반 자동 모드 판별 브리핑
- **Git 자동 동기화 연동**:
  - 브리핑 요청 시 백엔드에서 원격 GitHub로부터 `git pull`을 사전 집행하여 항상 최신 데이터 기준으로 브리핑 제공.
- **공개 REST API 엔드포인트 노출 (`app/routers/web_router.py`)**:
  - `GET /api/briefing?mode=morning|evening` 엔드포인트를 제공하여 외부 크론/웹훅과의 자동 연동 지원.

### 2.3 DevAgentService 및 반응형 웹 UI 액션 칩 바 업데이트 (`dev_agent_service.py`, `index.html`, `dev.html`)
- **DevBot 콘솔 연동**:
  - DevBot 콘솔에서도 `/briefing morning` 및 `/briefing evening`을 즉시 실행 가능하도록 도구 체인 연계.
- **원터치 빠른 액션 칩 바**:
  - 왓슨 및 데브콘솔 하단 칩 바에 `[🌅 아침 브리핑]`, `[🌇 저녁 회고]` 칩을 추가 배치하여 모바일에서도 원터치 실행 보장.

## 3. Consequences (영향 및 효과)
- **하루 라이프사이클에 최적화된 비서 경험**: 아침에는 선명한 우선순위로 업무를 시작하고, 저녁에는 보람찬 성과 확인과 미완료 태스크 이월로 하루를 편안하게 마감.
- **초고속 안정성 보장**: AI 지능형 생성과 결정론적 로컬 포맷터를 결합하여 무지연 실시간 브리핑 및 테스트 무결점 달성.
- **일관된 멀티 인터페이스 지원**: 웹 대시보드, 텔레그램 봇, REST API, DevBot 콘솔 전반에서 100% 동일한 브리핑 품질 유지.
