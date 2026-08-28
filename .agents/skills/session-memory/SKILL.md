---
name: session-memory
description: 텔레그램 및 웹 대시보드 사용자별 대화 세션 히스토리와 마크다운 맥락 보존 스킬
---

# 🧠 Session Memory Skill

## 1. 목적
동일 세션 내에서 사용자의 이전 대화 내역과 수정 요청 맥락(Context)을 영속적으로 복원하고 유지한다.

## 2. 세션 처리 로직 (Session Handling Logic)
1. **세션 식별 (Session Identification)**
   - 텔레그램: `telegram:{chat_id}`
   - 웹 대시보드: UUID `session_id`
2. **히스토리 복원 (History Retrieval)**
   - DB(`app/db/watson.db`)에서 해당 세션의 최근 N개 메시지 로딩.
   - 현재 작업 대상 마크다운 파일(`lifelogs/YYYY/MM/YYYY-MM-DD.md`) 내용 로딩.
3. **맥락 융합 (Context Fusion)**
   - LLM 프롬프트에 `[Current Session History]`와 `[Target Markdown Content]`를 결합하여 연속성 유지.
4. **저장 (Context Save)**
   - 턴 완료 후 유저 메시지 및 AI 답변을 DB에 영속 저장.
