# 🧬 Harness Evolution Rule (하네스 자가 진화 규칙)

## 1. 개요
본 규칙은 24시간 가동되는 서버 환경에서 깃 푸시 실패, LLM 파싱 예외, 세션 꼬임 등의 실행 오차(Delta)가 발생했을 때, AI가 스스로 원인을 분석하고 하네스 룰과 스킬을 업데이트하는 자가 피드백 진화 메커니즘을 정의한다.

## 2. 피드백 진화 프로세스 (Evolution Loop)
```text
[실행 오차/실패 발생] ➔ [로그 분석 & 원인 규명] ➔ [ADR 문서 기록] ➔ [하네스/스킬 업데이트]
```

1. **오류 포착 및 격리 (Capture & Isolate)**
   - Git Push 실패, 마크다운 템플릿 깨짐 등의 오류 발생 시 즉시 프로세스를 안전 상태(Local Queue 백업)로 격리한다.

2. **의사결정 문서 작성 (ADR Update)**
   - 해당 예외 케이스의 발생 원인과 해결책을 `docs/adr/ADR-xxx-[issue].md` 형식으로 기록한다.

3. **스킬 및 규칙 피드백 (Rule/Skill Evolution)**
   - 재발 방지를 위해 관련 스킬(`.agents/skills/*/SKILL.md`)의 예외 처리 지침을 보강하고, `.agents/rules/`에 해당 제약 조건을 자동 추가한다.
