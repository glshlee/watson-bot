from unittest.mock import MagicMock, patch

import pytest

from app.services.bus_service import BusService
from app.services.commute_config_service import CommuteConfigService


@pytest.fixture(autouse=True)
def clean_bus_cache():
    BusService.clear_cache()
    yield
    BusService.clear_cache()


def test_normalize_route_name():
    assert BusService.normalize_route_name("146번") == "146"
    assert BusService.normalize_route_name("  771번  ") == "771"
    assert BusService.normalize_route_name("N13") == "N13"
    assert BusService.normalize_route_name("M4101번") == "M4101"
    assert BusService.normalize_route_name("간선146") == "간선146"


def test_parse_arrmsg():
    # 1. 분후[번째 전]
    p1 = BusService.parse_arrmsg("3분후[1번째 전]")
    assert p1["min"] == 3
    assert p1["stops"] == 1
    assert "3분 후 도착" in p1["text"]

    # 2. 초 포함
    p2 = BusService.parse_arrmsg("12분20초후[6번째 전]")
    assert p2["min"] == 12
    assert p2["stops"] == 6
    assert "12분 후 도착" in p2["text"]

    # 3. 곧 도착
    p3 = BusService.parse_arrmsg("곧 도착")
    assert p3["min"] == 1
    assert p3["stops"] == 1
    assert "곧 도착" in p3["text"]

    # 4. 운행종료 / 출발대기
    p4 = BusService.parse_arrmsg("운행종료")
    assert p4["min"] is None
    assert p4["text"] == "운행종료"

    p5 = BusService.parse_arrmsg("출발대기")
    assert p5["min"] is None
    assert "출발대기" in p5["text"]

    # 5. 빈 문자열
    p6 = BusService.parse_arrmsg("")
    assert p6["text"] == "도착 정보 없음"


def test_smart_mock_arrival():
    mock = BusService.get_smart_mock_arrival(
        bus_route_name="146",
        bus_stop_name="역삼역",
        bus_stop_id="23284",
    )
    assert mock["is_live"] is False
    assert mock["route_name"] == "146번"
    assert mock["stop_name"] == "역삼역"
    assert "분 후 도착" in mock["status"]
    assert "시뮬레이션" in mock["source"]
    assert mock["remaining_min"] is not None
    assert mock["remaining_stops"] is not None
    assert "출근 팁" in mock or len(mock["tip"]) > 0


def test_fetch_seoul_bus_arrival_mocked_http():
    fake_response_data = {
        "msgHeader": {"headerCd": "0", "headerMsg": "정상"},
        "msgBody": {
            "itemList": [
                {
                    "rtNm": "146",
                    "stNm": "역삼역.포스코P&S타워",
                    "arrmsg1": "4분후[2번째 전]",
                    "arrmsg2": "14분후[8번째 전]",
                    "traTime1": "240",
                    "traTime2": "840",
                },
                {
                    "rtNm": "360",
                    "stNm": "역삼역.포스코P&S타워",
                    "arrmsg1": "1분후[0번째 전]",
                    "arrmsg2": "10분후[5번째 전]",
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response_data

    with patch("httpx.Client.get", return_value=mock_resp):
        res = BusService.fetch_seoul_bus_arrival(
            bus_stop_id="23284",
            bus_route_name="146번",
            api_key="VALID_TEST_API_KEY_12345",
            bus_stop_name="역삼역",
        )

        assert res is not None
        assert res["is_live"] is True
        assert res["route_name"] == "146번"
        assert res["stop_name"] == "역삼역.포스코P&S타워"
        assert res["remaining_min"] == 4
        assert res["remaining_stops"] == 2
        assert "4분 후 도착" in res["status"]
        assert "14분 후 도착" in res["next_bus"]
        assert "서울 TOPIS" in res["source"]


def test_fetch_tago_bus_arrival_mocked_http():
    fake_response_data = {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": {
                    "item": [
                        {
                            "routeno": "771",
                            "nodenm": "상암DMC역",
                            "arrtime": 300,
                            "arrprevstationcnt": 3,
                        }
                    ]
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response_data

    with patch("httpx.Client.get", return_value=mock_resp):
        res = BusService.fetch_tago_bus_arrival(
            bus_stop_id="DJB8001793",
            bus_route_name="771",
            city_code="31",
            api_key="VALID_TEST_API_KEY_12345",
        )

        assert res is not None
        assert res["is_live"] is True
        assert res["route_name"] == "771번"
        assert res["stop_name"] == "상암DMC역"
        assert res["remaining_min"] == 5
        assert res["remaining_stops"] == 3
        assert "5분 후 도착" in res["status"]
        assert "TAGO" in res["source"]


def test_bus_service_caching():
    mock_arrival = {
        "is_live": True,
        "source": "서울 TOPIS 실시간 API",
        "stop_name": "테스트역",
        "stop_id": "11111",
        "route_name": "146번",
        "status": "3분 후 도착",
        "next_bus": "10분 후",
        "remaining_min": 3,
        "remaining_stops": 1,
        "tip": "빠르게 출발하세요!",
        "updated_time": "14:00",
    }

    with patch.object(BusService, "fetch_seoul_bus_arrival", return_value=mock_arrival) as mock_fetch:
        # 1st call -> calls fetch
        r1 = BusService.get_arrival_info(
            bus_stop_id="11111",
            bus_route_name="146",
            api_key="VALID_API_KEY_54321",
            city_code="11",
        )
        assert r1["status"] == "3분 후 도착"
        assert mock_fetch.call_count == 1

        # 2nd call -> hit cache, no network call
        r2 = BusService.get_arrival_info(
            bus_stop_id="11111",
            bus_route_name="146",
            api_key="VALID_API_KEY_54321",
            city_code="11",
        )
        assert r2["status"] == "3분 후 도착"
        assert mock_fetch.call_count == 1


def test_commute_standalone_bus_card():
    service = CommuteConfigService()
    card = service.get_standalone_bus_card()
    assert "실시간 출근 버스 도착 정보" in card
    assert ("도착 현황" in card or "도착 예정 현황" in card)
    assert "출근 팁" in card


def test_supervisor_bus_query():
    from app.db.database import SessionLocal
    from app.services.supervisor_service import SupervisorService

    db = SessionLocal()
    try:
        service = SupervisorService(db=db)

        # 1. /bus command
        res = service.process_user_request(
            session_id="test_bus_session",
            user_message="/bus",
            channel="web",
            auto_push=False,
        )
        assert res["intent"] == "commute_inspect"
        assert "실시간 출근 버스 도착 정보" in res["ai_response"]

        # 2. Natural language bus query
        res2 = service.process_user_request(
            session_id="test_bus_session",
            user_message="출근 버스 언제 와?",
            channel="web",
            auto_push=False,
        )
        assert res2["intent"] == "commute_inspect"
        assert "실시간 출근 버스 도착 정보" in res2["ai_response"]
    finally:
        db.close()


def test_bus_service_stop_only_all_routes_topis():
    mock_payload = {
        "msgHeader": {"headerCd": "0", "headerMsg": "정상조회"},
        "msgBody": {
            "itemList": [
                {"rtNm": "146", "stNm": "역삼역", "arrmsg1": "3분[2번째 전]", "arrmsg2": "12분[8번째 전]"},
                {"rtNm": "360", "stNm": "역삼역", "arrmsg1": "곧 도착", "arrmsg2": "10분[6번째 전]"},
                {"rtNm": "740", "stNm": "역삼역", "arrmsg1": "7분[4번째 전]", "arrmsg2": "15분[10번째 전]"},
            ]
        },
    }

    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        res = BusService.fetch_seoul_bus_arrival(
            bus_stop_id="23284",
            bus_route_name="",  # 정류소 번호만 입력
            api_key="TEST_API_KEY_12345",
        )

        assert res is not None
        assert res["is_live"] is True
        assert res["is_all_routes"] is True
        assert res["stop_name"] == "역삼역"
        assert res["route_name"] == "전체 노선"
        assert len(res["buses"]) == 3
        # 360번(곧 도착=1분)이 146번(3분)보다 먼저 정렬되어야 함
        assert "360번" in res["buses"][0]["route_name"]
        assert "146번" in res["buses"][1]["route_name"]


def test_bus_service_stop_only_all_routes_tago():
    mock_payload = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"routeno": "301", "nodenm": "봉명역", "arrtime": 180, "arrprevstationcnt": 2},
                        {"routeno": "102", "nodenm": "봉명역", "arrtime": 60, "arrprevstationcnt": 1},
                    ]
                }
            }
        }
    }

    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        res = BusService.fetch_tago_bus_arrival(
            bus_stop_id="DJB8001793",
            bus_route_name="",  # 정류소 번호만 입력
            city_code="34",
            api_key="TEST_API_KEY_12345",
        )

        assert res is not None
        assert res["is_live"] is True
        assert res["is_all_routes"] is True
        assert res["stop_name"] == "봉명역"
        assert res["route_name"] == "전체 노선"
        assert len(res["buses"]) == 2
        # 102번(60초=1분)이 301번(180초=3분)보다 먼저 정렬
        assert "102번" in res["buses"][0]["route_name"]


def test_commute_standalone_bus_card_all_routes():
    service = CommuteConfigService()
    custom_cfg = {
        "bus_stop_id": "23284",
        "bus_stop_name": "역삼역",
        "bus_route_name": "",  # 정류소 번호만 설정된 상태
    }
    mock_info = {
        "is_live": True,
        "is_all_routes": True,
        "source": "실시간 API",
        "stop_name": "역삼역",
        "route_name": "전체 노선",
        "status": "• 🚍 **360번**: 1분 후 도착\n• 🚍 **146번**: 3분 후 도착",
        "next_bus": "2개 노선 운행 중",
        "remaining_min": 1,
        "tip": "버스가 곧 도착합니다!",
    }

    with patch.object(BusService, "get_arrival_info", return_value=mock_info):
        preview = service.generate_preview(custom_config=custom_cfg)
        assert "전체 노선" in preview["markdown"]
        assert "360번" in preview["markdown"]

        weather_card = service.get_morning_weather_card()
        assert "전체 노선" in weather_card

        bus_card = service.get_standalone_bus_card()
        assert "전체 노선" in bus_card


def test_resolve_bus_stop_public_mapping():
    mock_html = '''
    <div class="search_result_wrap">
        <li class="search_item base" data-id="11040621014" data-type="busStop" data-title="금옥초등학교앞">
            <strong class="tit_g">금옥초등학교앞</strong>
            <span class="txt_g"><span class="screen_out">버스 정류장 번호 : </span>04158<span class="txt_bar">|</span>옥수삼성아파트 방면</span>
            <span class="txt_ginfo">서울 성동구 금호4가동</span>
        </li>
    </div>
    '''
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html
        mock_get.return_value = mock_resp

        BusService.clear_cache()
        res = BusService.resolve_bus_stop("04158")
        assert res["stop_name"] == "금옥초등학교앞"
        assert res["direction"] == "옥수삼성아파트 방면"
        assert res["region"] == "서울 성동구 금호4가동"
        assert res["stop_id"] == "04158"


def test_resolve_bus_stop_router():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    mock_html = '''
    <li data-type="busStop" data-title="금옥초등학교앞">
        <span class="screen_out">버스 정류장 번호 : </span>04158<span class="txt_bar">|</span>옥수삼성아파트 방면</span>
    </li>
    '''
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html
        mock_get.return_value = mock_resp

        BusService.clear_cache()
        res = client.post(
            "/api/settings/commute/resolve-bus-stop",
            json={"bus_stop_id": "04158", "city_code": "11"},
            headers={"Authorization": "Basic d2F0c29uOnBhc3N3b3Jk"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["stop_name"] == "금옥초등학교앞"


def test_bus_service_force_refresh():
    """force_refresh=True 시 인메모리 캐시를 우회하여 최신 결과를 가져오는지 검증 (ADR-039)."""
    # 1. First call populates cache
    info1 = BusService.get_arrival_info(
        bus_stop_id="23284",
        bus_route_name="146",
        bus_stop_name="역삼역",
        use_mock_fallback=True,
    )
    assert "146번" in info1["route_name"]

    # 2. Modify cache manually to verify cache hit
    cache_key = "11:23284:146"
    assert cache_key in BusService._cache
    _ts, data = BusService._cache[cache_key]
    data["status"] = "MANUAL_CACHED_STATUS"

    info_cached = BusService.get_arrival_info(
        bus_stop_id="23284",
        bus_route_name="146",
        bus_stop_name="역삼역",
        use_mock_fallback=True,
        force_refresh=False,
    )
    assert info_cached["status"] == "MANUAL_CACHED_STATUS"

    # 3. Call with force_refresh=True should bypass the cached status
    info_fresh = BusService.get_arrival_info(
        bus_stop_id="23284",
        bus_route_name="146",
        bus_stop_name="역삼역",
        use_mock_fallback=True,
        force_refresh=True,
    )
    assert info_fresh["status"] != "MANUAL_CACHED_STATUS"


def test_refreshed_bus_card_endpoint():
    """GET/POST /api/settings/commute/bus-card 실시간 갱신 API 엔드포인트 검증 (ADR-039)."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    res = client.get(
        "/api/settings/commute/bus-card",
        headers={"Authorization": "Basic d2F0c29uOnBhc3N3b3Jk"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "[실시간 출근 버스 도착 정보]" in data["markdown"]
    assert "updated_time" in data
    assert "transit_summary" in data
    assert "transit_line" in data

