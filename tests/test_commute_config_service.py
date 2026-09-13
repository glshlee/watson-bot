import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.commute_config_service import CommuteConfigService

client = TestClient(app)


def test_commute_config_service_defaults_and_save():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "commute_test.json")
        service = CommuteConfigService(config_file=config_path)

        # 1. Default config load
        cfg = service.get_config()
        assert cfg["enabled"] is True
        assert cfg["send_time"] == "07:30"
        assert cfg["location_name"] == "서울 강남구 역삼동"
        assert cfg["bus_stop_name"] == "역삼역"
        assert cfg["bus_route_name"] == "146"

        # 2. Save new config with real API key
        new_payload = {
            "enabled": True,
            "send_time": "08:15",
            "weekdays_only": True,
            "location_name": "충청남도 서산시 대산읍",
            "grid_x": 51,
            "grid_y": 110,
            "air_station_name": "대산읍",
            "bus_stop_name": "대산정류소",
            "bus_stop_id": "34001",
            "bus_route_name": "900",
            "city_code": "34",
            "public_data_api_key": "SECRET_DATA_GO_KR_KEY_123456",
            "use_mock_fallback": True,
        }
        saved_masked = service.save_config(new_payload)
        assert saved_masked["send_time"] == "08:15"
        assert saved_masked["location_name"] == "충청남도 서산시 대산읍"
        # API key should be masked
        assert saved_masked["public_data_api_key"].startswith("SECR")
        assert saved_masked["public_data_api_key"].endswith("3456")
        assert "****" in saved_masked["public_data_api_key"]

        # 3. Verify disk file has actual key
        raw_cfg = service.get_config()
        assert raw_cfg["public_data_api_key"] == "SECRET_DATA_GO_KR_KEY_123456"

        # 4. Save again with masked key -> should preserve actual key
        update_payload = dict(saved_masked)
        update_payload["send_time"] = "07:45"
        updated = service.save_config(update_payload)
        assert updated["send_time"] == "07:45"
        raw_cfg2 = service.get_config()
        assert raw_cfg2["public_data_api_key"] == "SECRET_DATA_GO_KR_KEY_123456"

        # 5. Invalid time format raises ValueError
        with pytest.raises(ValueError):
            service.save_config({"send_time": "25:99"})


def test_commute_preview_generation():
    service = CommuteConfigService()
    preview = service.generate_preview({
        "location_name": "서울 마포구 상암동",
        "bus_stop_name": "상암DMC역",
        "bus_route_name": "771",
        "send_time": "07:20",
    })

    assert preview["success"] is True
    assert "서울 마포구 상암동" in preview["markdown"]
    assert "상암DMC역" in preview["markdown"]
    assert "771번" in preview["markdown"]
    assert "07:20" in preview["markdown"]


def test_commute_settings_api_endpoints():
    # 1. GET /api/settings/commute
    res_get = client.get("/api/settings/commute")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["success"] is True
    assert "data" in data
    assert "location_name" in data["data"]
    assert "send_time" in data["data"]

    # 2. POST /api/settings/commute (save valid)
    payload = {
        "enabled": True,
        "send_time": "07:30",
        "weekdays_only": True,
        "location_name": "서울 강남구 역삼동",
        "grid_x": 61,
        "grid_y": 125,
        "air_station_name": "강남구",
        "bus_stop_name": "역삼역",
        "bus_stop_id": "23284",
        "bus_route_name": "146",
        "city_code": "11",
        "public_data_api_key": "",
        "use_mock_fallback": True,
    }
    res_post = client.post("/api/settings/commute", json=payload)
    assert res_post.status_code == 200
    assert res_post.json()["success"] is True

    # 3. POST /api/settings/commute/preview
    res_preview = client.post(
        "/api/settings/commute/preview",
        json={"config": payload}
    )
    assert res_preview.status_code == 200
    preview_json = res_preview.json()
    assert preview_json["success"] is True
    assert "markdown" in preview_json
    assert "146번" in preview_json["markdown"]


def test_supervisor_commute_slash_command():
    from app.db.database import SessionLocal
    from app.services.supervisor_service import SupervisorService

    db = SessionLocal()
    try:
        service = SupervisorService(db=db)

        # 1. /commute status query
        res = service.process_user_request(
            session_id="test_commute_session",
            user_message="/commute",
            channel="web",
            auto_push=False,
        )
        assert res["intent"] == "commute_inspect"
        assert "출근길 날씨·미세먼지·버스 브리핑 설정" in res["ai_response"]

        # 2. /commute test preview query
        res_test = service.process_user_request(
            session_id="test_commute_session",
            user_message="/commute test",
            channel="web",
            auto_push=False,
        )
        assert res_test["intent"] == "commute_inspect"
        assert "출근길 모닝 브리핑" in res_test["ai_response"]
    finally:
        db.close()
