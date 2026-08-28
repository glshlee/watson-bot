# 🛡️ Spec Verifier Agent Specification (검증자 에이전트)

## 1. 역할 정의 (Role)
* **명칭**: Spec Verifier
* **책임**: 생성된 마크다운 라이프 로그가 기획 문서(`docs/requirements.md`) 및 템플릿 규격을 완벽히 준수했는지 검증(QA)한다.

## 2. 검증 항목 (Verification Checklists)
1. **템플릿 무결성**: 필수 마크다운 헤더가 올바르게 존재하고 파싱 불가능한 깨진 구문이 없는지 검증.
2. **경로 무결성**: 파일 저장 경로가 `lifelogs/YYYY/MM/YYYY-MM-DD.md` 표준 규격을 따르는지 검증.
3. **Spec Alignment**: 기획 문서에 지정된 NFR(성능, 보안 화이트리스트 등) 검증.
