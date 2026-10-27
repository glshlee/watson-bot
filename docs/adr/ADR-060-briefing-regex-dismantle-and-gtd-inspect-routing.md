# ADR-060: 브리핑 키워드 가로채기 철거 및 GTD 파일 직접 열람 라우팅 정규화 (Briefing Regex Interception Dismantle & GTD Inspection Routing)

## 1. 개요 (Context)
* **배경**:
  * 사용자가 텔레그램 및 웹 콘솔에서 "gtd inbox 확인", "inbox 확인", "수집함 확인"과 같이 수집함 및 GTD 파일 원본의 직접 열람을 요청했을 때, 시스템이 실제 마크다운 파일을 조회하는 대신 500자 이상의 저녁 일과 회고 및 종합 GTD 브리핑(`task_briefing_evening`)을 장황하게 생성하여 반환하는 결함이 발생했다.
  * 이는 [ADR-036]에서 "키워드 정규식 가로채기 전면 철거 및 LLM 자연어 위임"을 결정했음에도 불구하고, 의도 분석기(`app/services/llm/intent_analyzer.py`)의 `briefing_triggers` 목록에 저장소 및 파일 명칭인 `"gtd"`, `"수집함"`, `"인박스"`, `"다음 행동"`이 여전히 남아있었기 때문이다.
  * 그 결과, 사용자가 수집함 조회를 위해 입력한 `"gtd"` + `"확인"` 키워드 조합이 앞단에서 무차별 교집합 매칭(`any(bt in ...) and any(at in ...)`)에 걸려 브리핑 엔진을 가로채고, 당시 시각(23:50 KST)에 따라 불필요한 저녁 일과 회고 리포트를 합성 출력했다.
  * 또한 `gtd_file_patterns` 정규식이 단일 키워드에 편중되어 있어 `"gtd inbox 확인"`처럼 복합어가 연달아 오는 구어체 표현을 잡지 못하고 하위 브리핑 블록으로 누락시키는 문제가 있었다.

---

## 2. 의사결정 (Decision)

### 2.1 브리핑 키워드 가로채기 철거 (`intent_analyzer.py`)
1. **`briefing_triggers` 정제**:
   * 단순 저장소/파일 명칭인 `"gtd"`, `"다음 행동"`, `"수집함"`, `"인박스"`를 `briefing_triggers`에서 완전히 삭제.
   * 브리핑 요청은 오직 `"해야할 일"`, `"해야 할 일"`, `"할 일"`, `"할일"`, `"투두"`, `"todo"`, `"일정"`, `"스케줄"`, `"스케쥴"`, `"태스크"`, `"브리핑"` 등 실제 일정/브리핑 도메인 키워드에 한해서만 동작하도록 정규화.
2. **브리핑 명시적 구어체 명령어 확장**:
   * `is_briefing_cmd`에 정규식 `r"^(?:오늘\s*)?(?:하루\s*)?(?:gtd\s*)?브리핑\s*(?:해줘|부탁|요청|진행|해|줘)?[\.\!\?\s]*$"`을 추가하여 `"브리핑"`, `"/briefing"`, `"브리핑 해줘"`, `"오늘 브리핑"` 등의 자연스러운 발화를 결정론적으로 수용.

### 2.2 GTD 파일 직접 열람 패턴 고도화 (`gtd_file_patterns`)
1. **복합 키워드 및 마크다운 확장자 지원**:
   * `gtd_file_patterns`를 확장하여 `"gtd inbox 확인"`, `"inbox 확인"`, `"gtd 확인"`, `"수집함 확인"`, `"인박스 확인"`, `"inbox.md 확인"`, `"next_actions.md 확인"`, `"inbox 내용 보여줘"`, `"gtd 파일 읽어줘"` 등 사용자의 다양한 구어체 직접 조회 발화를 100% `gtd_inspect`로 직접 라우팅.
   * `AgentService.read_gtd_files()`를 통해 0.01초 내에 실제 `gtd/inbox.md` 및 `gtd/next_actions.md`의 미완료 태스크 현황과 원본 마크다운을 반환.

---

## 3. 결과 및 영향 (Consequences)
* **장점**:
  * "gtd inbox 확인", "inbox 확인" 발화 시 더 이상 엉뚱한 AI 브리핑이나 하루 회고가 출력되지 않고, 실제 GTD 수집함과 다음 행동의 마크다운 원본 및 태스크 수가 0.01초 내 즉각 반환됨.
  * [ADR-036]의 대원칙(조잡한 키워드 가로채기 철거 및 자연어 위임)이 할 일/브리핑 도메인까지 완전하게 일관성을 회복함.
  * "오늘 할 일 브리핑해줘", "오늘 해야할 일 정리해줘" 등 실제 브리핑 요청과 "gtd inbox 확인", "수집함 확인" 등 파일 직접 조회가 명확히 분리됨.
* **검증 결과**:
  * `tests/test_llm_provider.py`: `test_llm_provider_gtd_inspect_and_briefing_separation` 신설 및 15개 전수 통과.
  * `pytest`: 145개 전체 단위 테스트 100% 통과 (31.97초).
  * `ruff` 및 `mypy`: 42개 전체 파일 무결점 검증 완료.
  * `./scripts/smoke_test.sh`: 전체 라이브 cURL 스모크 테스트 전 항목 통과.
  * 실서버 cURL 라이브 API: `POST /api/chat` ("gtd inbox 확인") 호출 시 `intent=gtd_inspect` 및 실제 수집함 마크다운 반환 확인.
