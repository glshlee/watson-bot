# ADR-034: 동네 설정 스마트 지오코딩 및 대화형 위치 변경 연동 (Smart Location Geocoding & Conversational Setup)

## 1. Status (상태)
**Accepted (채택됨)** - 2026-09-14

---

## 2. Context (배경 및 문제 정의)
* **모닝 브리핑 기상 정보의 기준 지역 불명확성**:
  * ADR-033을 통해 아침 브리핑에 실시간 날씨 및 미세먼지 정보가 기본 포함되었으나, 초기 설정 기본값인 `"서울 강남구 역삼동"`이 고정 표시되어 사용자가 "어느 동네 날씨정보야? 동네 설정 같은 걸 할 수 있어야 하지 않을까?"라는 명확한 페인 포인트를 제기함.
* **복잡한 수동 설정의 한계**:
  * 기존에는 웹 UI(`#commute-modal`)를 통해서만 거주지 변경이 가능했으나, 사용자가 기상청 격자 좌표(X, Y)나 에어코리아 대기 측정소명을 직접 알고 입력하기는 매우 어려움.
* **대화형 환경과의 단절**:
  * 텔레그램이나 웹 채팅에서 "우리 동네 성동구 금호동으로 설정해줘", "동네는 성동구 금호동인데 이렇게 설정하면 되는거야?", `/location 성동구 금호동` 등 일상 대화로 동네를 즉시 변경할 수 있는 수단이 부재했음.

---

## 3. Decision (결정 사항)

### 3.1 스마트 지오코딩 엔진 구축 (`app/services/geo_service.py`)
1. **한국 주요 행정구역 데이터베이스 내장**:
   * 서울 25개 자치구 전체 격자(X, Y) 및 에어코리아 대기 측정소 완비.
   * 서울 주요 동(금호동, 성수동, 옥수동, 상암동, 한남동, 여의도, 신림동, 목동 등) ➔ 자치구 스마트 역매핑.
   * 경기/인천/광역시 주요 도시 및 대표 동(성남 판교/분당, 수원 광교, 화성 동탄, 안양 평촌, 부산 해운대 등) 내장.
2. **0.001초 결정론적 지오코딩 (`resolve_location`)**:
   * 자연어 문장에서 불필요한 조사("우리 동네는", "으로 설정해줘")를 절삭하고 동네 키워드를 추출하여 정규화된 `location_name`, `grid_x`, `grid_y`, `air_station_name`, `city_code`를 반환.

### 3.2 대화형 동네 설정 인텐트 및 파이프라인 (`LLMProvider`, `SupervisorService`, `CommuteConfigService`)
1. **인텐트 확장**:
   * `location_set`: `/location [동네명]`, `/동네 [동네명]`, *"우리 동네 성동구 금호동으로 설정해줘"*, *"동네는 성동구 금호동인데 이렇게 그냥 설정하면 되는거야?"* 등 동네 변경 요청 처리.
   * `location_inspect`: `/location`, *"우리 동네 어디로 되어있어?"*, *"동네 어디야?"* 등 현재 거주지 조회 요청 처리.
2. **원스톱 설정 영속화 & 실시간 확인 카드**:
   * `CommuteConfigService.update_location_by_query()`를 통해 `config/commute_config.json`에 즉각 영속화.
   * 설정 완료 직후 변경된 동네 기준의 실시간 기상 브리핑 프리뷰 카드를 즉시 반환하여 사용자 안도감 제공.

### 3.3 웹 콘솔 자동 찾기 버튼 연동 (`settings_router.py`, `index.html`, `main.js`)
* `POST /api/settings/commute/resolve-location` REST API 엔드포인트 제공.
* 웹 모달(`#commute-modal`) 내 `[<i class="fa-solid fa-wand-magic-sparkles"></i> 자동 찾기]` 버튼(`#btn-resolve-location`) 추가로 동네 이름만 타이핑하면 격자 및 측정소 자동 채움 지원.

---

## 4. Consequences (파급 효과)

### 긍정적 효과
* **무설정(Zero-Friction) UX**: 기상청 격자나 측정소 이름을 몰라도 "성동구 금호동"처럼 동네 이름만 말하면 즉시 100% 매핑.
* **텔레그램/웹 모바일 즉각 변경**: 침대에 누워 스마트폰 텔레그램으로 대화하듯 동네를 변경 가능.
* **브리핑 정확도 및 친밀도 향상**: 사용자의 실제 거주지 기준 기온, 체감온도, 미세먼지, 출근 팁이 제공되어 실생활 밀착도 극대화.

---

## 5. Verification Plan (검증 계획)
* `tests/test_geo_service.py`: 서울 자치구/동, 경기 신도시, 자연어 문장 지오코딩 및 Supervisor 처리 플로우 단위 테스트.
* `./scripts/smoke_test.sh`: `POST /api/settings/commute/resolve-location` 및 `POST /api/chat` `/location` 라이브 검증.
* cURL 실제 API 응답 및 텔레그램 호환성 검증.
