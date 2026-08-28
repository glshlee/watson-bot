---
name: git-automation
description: Git Pull, Commit, Push 및 충돌 발생 시 로컬 큐 백업/재시도 자동화 스킬
---

# 🛠️ Git Automation Skill

## 1. 목적
에이전트가 마크다운 파일 작성 및 수정을 마친 후, 수동 조작 없이 안전하게 `git pull --rebase` ➔ `git add` ➔ `git commit` ➔ `git push`를 집행하는 절차를 규정한다.

## 2. 작업 순서 (Workflow)
1. **최신 변경사항 동기화**: `git pull --rebase origin main` 실행
2. **변경사항 스테이징**: `git add .` (또는 대상 MD 파일)
3. **의미 있는 커밋 메시지 작성**:
   - 예: `docs(log): Update daily log for 2026-08-28`
4. **원격 푸시**: `git push origin main`

## 3. 예외 및 충돌 처리 (Conflict & Error Handling)
- 푸시 실패 시 최대 3회 재시도(`retry_count=3`).
- 3회 실패 시 local queue에 작업 내용을 무결하게 저장하고, 텔레그램/웹 알림으로 사용자에게 에러 로그 및 백업 완료 통보.
