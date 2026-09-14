# ADR-037: 실시간 출근 버스 도착정보 API 실연동 및 지능형 캐시·안전 폴백 (Real-time Commute Bus Arrival API Integration & Intelligent Fallback)

## 1. Status (상태)
**Accepted (채택됨)** - 2026-09-14

---

## 2. Context (배경 및 문제 정의)
* **시뮬레이션(Mock) 하드코딩의 한계**:
  * 기존 출근길 모닝 브리핑 및 실시간 카드(ADR-030, ADR-033, ADR-035)에서 날씨와 대기질은 Open-Meteo 실시간 오픈 API를 통해 100% 라이브로 연동되었으나, 출근 버스는 `4분 후 도착 (2번째 전)`이라는 고정된 시뮬레이션 값으로 하드코딩되어 실제 버스 도착 현황을 확인하기 어려웠음.
* **실시간 대중교통 데이터와 사용자 편의성**:
  * 서울시 TOPIS(대중교통정보) 및 국토교통부 TAGO(버스도착정보) 공공 API를 실제 연동하여, 탑승 정류소(ARS ID 또는 노선 ID)와 노선 번호에 대한 실시간 잔여시간(분/초), 남은 정류소 수, 막차/차고지 대기 상태를 실시간 제공할 필요가 있음.
  * API 키가 미등록되어 있거나 외부 공공 API가 일시 장애/점검 중일 때도 시스템이 중단되지 않고, 현재 시각 기반의 가변적 시뮬레이션(Mock) 및 명확한 가이드 배지로 안전하게 폴백(Fallback)되어야 함.

---

## 3. Decision (결정 사항)

### 3.1 `BusService` 실시간 버스 도착정보 엔진 구축 (`app/services/bus_service.py`)
1. **서울시 TOPIS 버스도착정보 API 연동**:
   * 엔드포인트: `http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid`
   * ARS ID(5자리 정류소 번호) 및 노선번호 기반 실시간 도착 정보 조회.
   * `arrmsg1`, `arrmsg2` 정규식 파서(`parse_arrmsg`): `(\d+)분\s*(\d+)초?후[(\d+)번째 전]`, `곧 도착`, `운행종료`, `출발대기` 등 다양한 상태를 안전하게 정규화.
2. **국토교통부 TAGO 버스도착정보 API 연동**:
   * 엔드포인트: `http://apis.data.go.kr/1613000/ArvlInfoInqireService/getSttnAcctoArvlPrearngeInfoList`
   * 전국 및 경기도(city_code) 정류소(nodeId) 및 노선번호 기반 도착 예정 시간(초) 및 잔여 정류소 파싱.
3. **Encoding/Decoding 키 이중 인코딩 방지**:
   * `urllib.parse.unquote()`를 적용하여 사용자가 data.go.kr의 인코딩 키/디코딩 키 중 어느 것을 입력하더라도 `httpx`에서 1회만 정확히 인코딩되도록 보장.
4. **인메모리 캐싱 (45초 TTL)**:
   * 버스 위치는 30~60초 주기로 갱신되므로, 45초 인메모리 캐시(`_cache`)를 두어 사용자 반복 조회 시 API 호출을 최소화하고 0.01초 초고속 응답 보장.
5. **동적 스마트 시뮬레이션 & 안전 폴백**:
   * API 키가 없거나(`TEST_KEY_12345`, 공백 등) 외부 통신 오류 시, 현재 분(minute)에 따라 가변적인 잔여 시간(3~11분)과 비서 출근 팁을 동적 계산하여 정적 4분 고정 버그를 탈피.
   * `is_live` 플래그 및 출처 배지(`서울 TOPIS 실시간 API`, `국토교통부 TAGO`, `시뮬레이션 모드 (공공데이터 API 키 등록 필요)`)를 명시하여 투명성 보장.

### 3.2 브리핑 및 단독 버스 카드 연동 (`CommuteConfigService`, `SupervisorService`, `LLMProvider`)
1. **모닝 브리핑 카드 실연동 (`CommuteConfigService`)**:
   * `generate_preview()`, `get_morning_weather_card()` 내 고정 하드코딩을 `BusService.get_arrival_info()`로 전면 교체.
   * 단독 실시간 버스 브리핑 카드 반환 메서드 `get_standalone_bus_card()` 신설.
2. **자연어 및 슬래시 커맨드 라우팅 (`LLMProvider`, `SupervisorService`)**:
   * `/bus`, "출근 버스 언제 와?", "버스 도착 정보", "버스 시간" 질의 시 `commute_inspect` 인텐트(`log_content="bus"`)로 직행하여 단독 버스 도착 카드를 즉각 반환.

---

## 4. Consequences (파급 효과)

### 긍정적 효과
* **실시간 대중교통 정보 제공**:
  * 공공데이터포털 또는 서울시 버스 API 키 등록 시 실제 버스 잔여 시간과 정류소 위치가 왓슨 브리핑에 실시간 반영됨.
* **무설정 환경에서도 생동감 있는 시뮬레이션**:
  * API 키가 없어도 현재 시각에 따라 가변적으로 잔여 시간이 흐르는 현실적인 시뮬레이션 경험 제공.
* **단독 질의 지원**:
  * 출근 전 현관에서 `/bus` 한 줄 입력으로 즉시 실시간 버스 도착 현황 파악 가능.

---

## 5. Verification Plan (검증 계획)
* `tests/test_bus_service.py`: 노선명 정규화, 메시지 파싱, 목킹 API 호출, 인메모리 캐시 및 슈퍼바이저 라우팅 8개 단위 테스트 검증.
* `tests/test_commute_config_service.py`: 설정 저장, 프리뷰 생성, 모닝 브리핑 카드 통합 검증.
* `./scripts/smoke_test.sh`: 6-7 단계 `/bus` cURL 라이브 API 검증.
