from app.db.database import SessionLocal
from app.services.geo_service import GeoService
from app.services.llm_provider import LLMProvider
from app.services.supervisor_service import SupervisorService


def test_geo_service_resolution():
    # 1. 서울 자치구 + 동
    r1 = GeoService.resolve_location("성동구 금호동")
    assert r1["matched"] is True
    assert r1["location_name"] == "서울 성동구 금호동"
    assert r1["grid_x"] == 61
    assert r1["grid_y"] == 127
    assert r1["latitude"] == 37.55
    assert r1["longitude"] == 127.02
    assert r1["air_station_name"] == "성동구"

    # 2. 동 이름 단독 (금호동, 판교)
    r2 = GeoService.resolve_location("금호동")
    assert r2["matched"] is True
    assert "금호동" in r2["location_name"]
    assert r2["air_station_name"] == "성동구"

    r3 = GeoService.resolve_location("판교")
    assert r3["matched"] is True
    assert "판교" in r3["location_name"]
    assert r3["air_station_name"] == "분당구"

    # 3. 경기 주요 지역 (광교, 동탄)
    r4 = GeoService.resolve_location("광교동")
    assert r4["matched"] is True
    assert "광교" in r4["location_name"]

    # 4. 자연어 질의 문장
    r5 = GeoService.resolve_location("동네는 성동구 금호동인데 이렇게 그냥 설정하면 되는거야? 자동매핑 기능은 있는게 좋은 것 같아")
    assert r5["matched"] is True
    assert r5["location_name"] == "서울 성동구 금호동"
    assert r5["air_station_name"] == "성동구"


def test_llm_provider_location_intents():
    provider = LLMProvider()

    res1 = provider.analyze_and_respond("/location 성동구 금호동")
    assert res1.intent == "location_set"
    assert res1.log_content == "성동구 금호동"

    res2 = provider.analyze_and_respond("/location")
    assert res2.intent == "location_inspect"

    res3 = provider.analyze_and_respond("우리 동네 성동구 금호동으로 설정해줘")
    assert res3.intent == "location_set"

    res4 = provider.analyze_and_respond("우리 동네 어디로 되어있어?")
    assert res4.intent == "location_inspect"


def test_supervisor_location_set_flow():
    db = SessionLocal()
    service = SupervisorService(db)
    res = service.process_user_request(
        session_id="test_geo_flow",
        user_message="우리 동네 성동구 금호동으로 설정해줘",
        channel="web",
    )
    assert res["intent"] == "location_set"
    assert "서울 성동구 금호동" in res["ai_response"]
    assert "자동 매핑 성공" in res["ai_response"]
    assert "성동구" in res["ai_response"]
