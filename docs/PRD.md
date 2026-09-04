# 📋 Watson (GitHub LifeLog AI Agent) PRD (Product Requirement Document)

## 1. 제품 개요 (Product Overview)
* **제품명**: Watson (GitHub LifeLog AI Agent System)
* **목적**: 24시간 가동되는 개인 서버 환경에서 AI 에이전트를 상시 운영하여, 노트북/PC 연결 없이도 텔레그램 봇 및 웹 대시보드를 통해 언제 어디서나 삶의 기록(Life Log)을 마크다운(MD) 형식으로 작성, 수정, 관리하고 GitHub 레포지토리에 자동 커밋/푸시(Git Commit & Push)하는 자동화 시스템 구축.
* **핵심 타겟**: 
  * GitHub 마크다운 파일 기반으로 일기, 운동, 업무, 생각 등의 라이프 로그를 작성하는 유저.
  * 24시간 서버 환경을 통해 언제 어디서나 모바일/웹으로 AI 에이전트를 호출해 정제된 라이프 로그를 남기고자 하는 유저.

---

## 2. 핵심 비전 및 유저 경험 (User Experience Goals)
1. **Anytime, Anywhere Access (어디서나 접근성)**
   * 모바일에서는 텔레그램 봇으로 메시지/사진/음성 메모 송신 ➔ AI가 라이프로그 정제 후 GitHub 즉시 반영.
   * PC/모바일 브라우저에서는 웹 대시보드(Watson)로 월별/일별 라이프 로그 시각화 및 AI 대화형 편집.
2. **Seamless Git Automation (투명한 Git 자동화 & 1기록 1커밋 - ADR-004)**
   * 단순 잡담/질의는 커밋하지 않으며, 비서가 감지/제안하여 사용자가 승인했거나 직접 기록한 유의미한 라이프로그에 한해 즉시 `git commit` & `git push` 자동 집행.
   * 다중 세션(텔레그램, 웹) 간 데이터 정합성을 위해 확정된 기록 즉시 안전하게 원격 반영.
3. **Smart Lifelog Butler (비서형 상호작용 & 마크다운 구조화)**
   * 수동 명령어 없이도 대화 중 운동, 미팅, 생각 등 가치 있는 일과를 비서가 감지하여 자연스럽게 기록을 제안(Proactive Suggestion).
   * 무작위 메모도 AI가 템플릿(일기, 운동 기록, 감상평, 캘린더 등)에 맞춰 일관성 있게 구조화된 MD로 작성.

---

## 3. 주요 기능 명세 (Key Features)

### 3.1. 🤖 AI 에이전트 코어 (Agent Core Engine)
* **Smart Lifelog Butler & Intent Router (지능형 비서 및 의도 분리기)**:
  * 대화 입력 시 [단순 잡담/질의], [일과 감지 및 기록 제안], [제안 승인], [직접 명령]을 자동 판별.
  * 제안된 후보(`pending_log`)를 세션 맥락에 보관하고, 승인 시 마크다운 반영 및 Git 커밋 파이프라인 트리거.
* **LifeLog Generator**: 입력된 메시지/데이터를 날짜별(`YYYY-MM-DD.md` 또는 `year/month/day.md`) 양식에 맞춰 변환/업데이트.
* **Git Operations Worker**: 백그라운드에서 repository pull ➔ MD 파일 변경 ➔ commit (`docs(lifelog): [카테고리] 요약 - YYYY-MM-DD`) ➔ push 수행.
* **Session & Context Management (다중 세션 대화 맥락 관리)**: 
  * 세션 ID 기반 대화 히스토리 및 맥락(Context Memory), 임시 기록 후보(`pending_log`) 영속적 유지.
  * 동일 세션 내 이전 대화 내용 및 대상 MD 파일 상태를 AI가 인지하여 자연스러운 연속 대화 및 덧붙이기(Append/Edit) 수행.
  * 텔레그램 채널별/웹 대시보드 대화방별 멀티 세션 독립 관리.

### 3.2. 💬 텔레그램 봇 인터페이스 (Telegram Bot Interface)
* `/log [내용]`: 라이프 로그 바로 기록.
* `/summary`: 최근 기록 요약 및 이번 주/달 분석 리포트 제공.
* `/status`: Git 서버 상태 및 최근 커밋 확인.
* 사진/이미지 및 메모 수신 시 AI 처리 후 적절한 MD 경로에 매핑 저장.

### 3.3. 🌐 웹 대시보드 (Web Dashboard - Watson)
* **대시보드 메인**: 최근 활동 스트림, 최근 깃 커밋 내역, 이번 달 라이프 로그 달력(Calendar View).
* **MD 라이프 로그 뷰어 & 에디터**: 렌더링된 마크다운 보기 및 실시간 수동 수정 기능.
* **에이전트 대화창**: 웹상에서 AI 에이전트와 직접 상호작용하며 라이프 로그 추가/질의응답/재정리 요청.

---

## 4. 시스템 아키텍처 개요 (System Architecture Overview)

```text
[ 모바일 텔레그램 앱 ]      [ 모바일 / PC 웹 브라우저 ]
          │                           │
          ▼                           ▼
  [ Telegram Bot API ]     [ FastAPI Web Dashboard ]
          │                           │
          └─────────────┬─────────────┘
                        ▼
            [ Watson Agent Core Engine ]
         (AI Processing & MD Template Manager)
                        │
                        ▼
            [ Git Automation Engine ]
        (Git Pull/Commit/Push to GitHub)
                        │
                        ▼
             [ GitHub Repository ]
```

---

## 5. 성공 지표 (Key Success Metrics)
* **기록 소요 시간**: 모바일 텔레그램 메시지 보낸 후 GitHub 푸시 반영까지 5초 이내 완료.
* **시스템 가용성**: 24/7 서버 상시 가동 및 오류 발생 시 텔레그램으로 즉시 Fallback 알림.
* **사용자 만족도**: 텍스트 입력만으로 마크다운 구조화 및 깃 푸시 100% 성공.
