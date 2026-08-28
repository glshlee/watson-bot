# ADR-002: 다중 대화 세션 및 컨텍스트 영속성 관리 (Multi-Session Context Management)

* **상태 (Status)**: 승인됨 (Accepted)
* **날짜 (Date)**: 2026-08-03
* **작성자 (Author)**: Watson Core Team

---

## 1. 맥락 (Context)
Watson은 텔레그램 및 웹 대시보드를 통해 유저의 삶의 기록(Life Log) 및 일상 메모를 작성/관리한다. 유저가 서로 다른 주제(예: 일기 작성, 일일 계획 수립, 운동 기록, 생각 정리 등)에 대해 AI와 지속적으로 상호작용할 때, 대화 맥락(Context)이 세션 단위로 분리·유지되어야 연속적인 대화 및 일관된 라이프 로그 작성이 가능하다.

---

## 2. 의사결정 (Decision)

### 2.1. 세션 식별자 (Session Identifier) 구조
* **텔레그램**: `telegram:{chat_id}` (기본 세션) 및 `/session switch [name]` (특정 주제별 하위 세션)
* **웹 대시보드**: UUID 기반 `session_id` 생성 및 대화방 목록 관리

### 2.2. 세션 메모리 및 컨텍스트 영속성 (Context Persistence)
* **저장소**: SQLite DB (`app/db/watson.db`) 및 `sessions` / `chat_history` 테이블 구성.
* **컨텍스트 윈도우 관리**:
  * 각 세션별로 최근 N개의 대화 메세지(User/Assistant History)를 DB에서 불러와 LLM prompt context로 전달.
  * 일정 토큰 수 초과 시 AI 요약 메모리(Summary Memory)를 자동 생성하여 컨텍스트 압축 유지.
* **마크다운 파일 맥락 연동**: 세션 내에서 다루고 있는 마크다운 파일(예: `2026-08-02.md`)의 현재 내용도 세션 컨텍스트의 일부로 자동 포함하여 AI가 이전 기록을 참조하여 자연스럽게 Append/Edit 할 수 있도록 함.

---

## 3. 결과 및 영향 (Consequences)

### Positive (긍정적 영향)
* **연속성 보장**: 같은 세션에서는 대화 흐름이 무너지지 않고 자연스럽게 이어짐.
* **주제별 분리**: 웹 및 텔레그램에서 여러 세션을 독립적으로 전환하며 관리 가능.
* **정확한 파일 편집**: 현재 다루는 라이프 로그 파일의 맥락을 AI가 인지하여 중복이나 오작동 방지.

### Negative / Risk (주의사항)
* 컨텍스트 토큰 초과 관리(Sliding Window & Summarization) 로직 구현 필요.
