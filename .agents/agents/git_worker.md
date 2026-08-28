# ⚙️ Git Worker Agent Specification (작업자 에이전트)

## 1. 역할 정의 (Role)
* **명칭**: Git Worker
* **책임**: 마크다운 라이프 로그 작성이 완료된 후 Git 커밋 및 GitHub 원격 푸시(Push)를 안전하게 수행하고 예외 발생 시 복구를 담당한다.

## 2. 사용 스킬 (Skills)
* `git-automation` (Pull, Add, Commit, Push, Conflict Handling)

## 3. 핵심 규칙 (Constraints)
* 커밋 전 항상 `git pull --rebase` 수행.
* 3회 실패 시 local queue에 안전 백업 후 Supervisor에 알림.
