# ADR-019: DevBot 대화형 엔지니어링 툴체인 및 실시간 개발 실행 환경 (Interactive Dev Toolchain)

## 1. 배경 및 맥락 (Context)
ADR-018을 통해 상위 대시보드 포털(`/`)과 개발 전담 에이전트인 DevBot(`/dev`) 콘솔이 도입되었다. 그러나 초기 DevBot은 단순 Git 조회(`/status`, `/diff`, `/log`, `/branch`)와 정적 AI 질의응답 수준에 머물렀다.
사용자는 "데브봇 콘솔 로그를 보고 지금 너(Antigravity)랑 기능 차이가 왜 나는지 확인해봐. 지금 너랑 하는 방식(툴체인 실행, 테스트/린트 자가 검증, 컨텍스트 기반 아키텍처 피드백, 실시간 커밋 제안)이 좋거든?"이라며 DevBot의 엔지니어링 실행력을 Antigravity 수준으로 격상시킬 것을 요구하였다.

또한 기존 코드에서 `agy` CLI 호출 시 잘못된 인자 전달(`--mode plan`)로 인해 LLM 추론이 실패하고 기본 템플릿 응답으로 폴백되던 결함이 발견되었다.

## 2. 의사결정 (Decision)

1. **AGY CLI 호출 정규화 및 고탄력 추론**:
   - `agy` 비대화형 실행 표준 인자인 `-p "<prompt>" --dangerously-skip-permissions` 규격을 엄격 적용하고 50초 타임아웃 및 PATH 보정(`/home/ubuntu/.gemini/antigravity-cli/bin`)을 적용.
   - 워크스페이스 상태, 활성 브랜치, 변경 파일 수, 최근 커밋뿐 아니라 `docs/roadmap.md`의 최근 마일스톤 현황을 프롬프트 컨텍스트에 자동 주입하여 실제 프로젝트 엔지니어와 대화하듯 생생한 기술 조언 제공.

2. **대화형 엔지니어링 툴체인 구축 (`DevAgentService`)**:
   - `/test [경로]`: `pytest` 단위 테스트 러너를 DevBot 콘솔에서 즉시 실행하고 간결한 테스트 결과(Pass/Fail/통계) 브리핑. (인자 미지정 시 빠른 코어 스위트 기본 실행)
   - `/lint`: `ruff check .` 및 `mypy .` 정적 분석 및 타입 검사를 병렬 실행하고 뱃지 형태(`✅ RUFF PASS`, `✅ MYPY PASS`)로 결과 제공.
   - `/commit [메시지]`:
     - 인자 없이 호출 시: 현재 변경된 Git 파일 및 Diff를 분석하여 Conventional Commits 기반 추천 메시지 3종(`feat: ...`, `fix: ...`, `refactor: ...`)을 생성하여 사용자에게 제안.
     - 메시지와 함께 호출 시: 변경 사항을 안전하게 `git add -A` 후 커밋을 즉시 집행하고 해시 반환.
   - `/help`: 사용 가능한 모든 엔지니어링 툴체인 명령 목록 및 예시를 안내.

3. **입력 보안 및 쉘 인젝션 방지 (Safe Subprocess Execution)**:
   - 모든 외부 명령어 실행 시 `shlex.split` 및 화이트리스트 기반 인자 검증(`;`, `&`, `|`, `>` 등 쉘 메타문자 및 디렉토리 트래버설 `..` 차단)을 통해 안전한 하위 프로세스 실행 보장.

4. **웹 콘솔 UI 퀵 툴 칩 (Quick Action Chips)**:
   - `/dev` 웹 콘솔 입력창 상단에 `/test (pytest)`, `/lint (ruff/mypy)`, `/commit (추천)`, `/help` 등의 퀵 칩을 추가하여 터치 한 번으로 엔지니어링 도구를 실행할 수 있도록 UX 고도화.

## 3. 결과 및 영향 (Consequences)
- **장점**:
  - DevBot이 단순 조회용 챗봇에서 터미널 없이도 테스트, 린트, 커밋을 조율하는 실질적인 AI 소프트웨어 엔지니어로 진화.
  - Antigravity 페어 프로그래밍 경험과 동일한 자가 검증 루프 및 컨텍스트 인지형 개발 피드백 제공.
- **영향 범위**:
  - 백엔드: `app/services/dev_agent_service.py` (`_run_pytest`, `_run_lint`, `_run_git_commit`, `_recommend_commit_messages`, `_get_roadmap_summary`)
  - 프론트엔드: `app/templates/dev.html` (퀵 액션 바)
  - 테스트: `tests/test_dev_agent.py`, `scripts/smoke_test.sh`
