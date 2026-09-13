# ADR-033: 아침 브리핑 실시간 날씨·미세먼지 통합 및 자연어 기상 질의 연동 (Morning Briefing Weather Integration)

## 1. Context (배경 및 문제점)
- 이전 ADR-030에서 출근길 맞춤형 브리핑 설정(`CommuteConfigService`) 및 웹 모달 UI가 구축되었으나, 매일 오전 08:30 KST에 정기 발송되는 아침 브리핑(`BriefingService.generate_briefing()`, `/briefing morning`)에는 날씨와 미세먼지 정보가 연동되지 않고 순수 GTD 할 일만 나열되는 결함이 존재함.
- `BriefingService.generate_briefing()`의 AI 합성 로직 내부 필터(`not any(f in ai_res for f in ["날씨", "시간"])`)로 인해, AI가 날씨 정보를 포함하여 브리핑을 작성하더라도 무조건 폐기되고 룰 기반 폴백으로 누락되는 치명적인 필터 버그가 발견됨.
- 또한 사용자가 "오늘 날씨 어때?", "날씨랑 미세먼지 알려줘" 등 일상 기상 정보를 질문했을 때도 설정 상태 텍스트만 출력되거나 일반 잡담으로 처리되는 한계가 있었음.

---

## 2. Decision (결정 사항)

### 2.1 아침 브리핑 최상단 날씨 & 미세먼지 카드 기본 통합 (`BriefingService`)
- `BriefingService`에 `CommuteConfigService`를 주입하여, `mode == "morning"`일 때 인사말 직후 `self.commute_config_service.get_morning_weather_card()`를 필수 배치.
- 룰 기반 브리핑 및 LLM 브리핑 프롬프트 상단에 실시간 날씨(기온, 체감기온, 하늘상태, 강수확률/우산 팁), 대기질(PM10/PM2.5 수치 및 등급), 출근길 버스 도착 현황을 `#### 📍 오늘의 날씨 & 미세먼지` 블록으로 통합.
- AI 브리핑 필터에서 `"날씨"` 배제 조건을 제거하고, AI 브리핑에 날씨가 누락될 경우 상단에 카드를 자동 보강(Patch)하는 안전장치 탑재.

### 2.2 실시간 날씨 카드 생성 메서드 및 단독 질의 지원 (`CommuteConfigService`, `SupervisorService`)
- `CommuteConfigService`에 `get_morning_weather_card()` 및 `get_standalone_weather_card()` 구현.
- `LLMProvider`에서 "날씨 브리핑", "날씨 정보", "미세먼지 수치", "대기질 정보" 등 자연어 기상 질의 시 `commute_inspect` (`log_content="weather"`)로 라우팅하고, 단순 인사/감탄("안녕하세요! 오늘 날씨 좋네요")은 `chat_only`로 자연스럽게 분리.
- `SupervisorService`에서 `log_content == "weather"` 수신 시 즉시 실시간 기상 카드를 반환.

---

## 3. Consequences (영향 및 효과)
1. **완벽한 모닝 브리핑 완성**: 매일 아침 텔레그램 푸시 및 웹 대시보드 브리핑에서 날씨(우산 팁), 미세먼지 수치, 출근 버스, 오늘의 Top 3 우선순위 과제를 한눈에 확인 가능.
2. **AI 브리핑 품질 정상화**: 부적절한 키워드 필터 제거로 AI가 자연스럽게 날씨와 일정을 조화롭게 브리핑.
3. **직관적인 기상 정보 질의**: "날씨랑 미세먼지 알려줘", `/weather` 명령어로 언제든 동네 실시간 날씨와 대기질을 즉시 확인 가능.
