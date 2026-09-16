from unittest.mock import MagicMock, patch

from app.services.weather_service import WeatherService


def test_weather_service_get_live_weather():
    # Clear cache before testing
    WeatherService._cache.clear()

    mock_live = {
        "temp": "18.5°C",
        "feels_like": "17.0°C",
        "sky": "맑음 ☀️",
        "rain_prob": "10%",
        "umbrella_tip": "우산 불필요 ☀️",
        "pm10": "좋음 🟢 (25 µg/m³)",
        "pm25": "좋음 🟢 (12 µg/m³)",
        "source": "Open-Meteo API",
        "updated_time": "14:00",
        "is_live": True,
    }
    with patch.object(WeatherService, "_fetch_open_meteo", return_value=mock_live):
        # Fetch live weather (or fallback if offline)
        res = WeatherService.get_live_weather(
            latitude=37.55,
            longitude=127.02,
            location_name="서울 성동구 금호동",
        )

        assert "temp" in res
        assert "feels_like" in res
        assert "sky" in res
        assert "rain_prob" in res
        assert "umbrella_tip" in res
        assert "pm10" in res
        assert "pm25" in res
        assert "source" in res
        assert "updated_time" in res
        assert "°C" in res["temp"]


def test_weather_service_caching():
    WeatherService._cache.clear()

    # First call
    res1 = WeatherService.get_live_weather(37.55, 127.02, "서울 성동구 금호동")
    assert f"{37.55:.2f},{127.02:.2f}" in WeatherService._cache

    # Second call should hit cache without network
    with patch.object(WeatherService, "_fetch_open_meteo") as mock_fetch:
        res2 = WeatherService.get_live_weather(37.55, 127.02, "서울 성동구 금호동")
        mock_fetch.assert_not_called()
        assert res1["temp"] == res2["temp"]


def test_weather_service_fallback_on_error():
    WeatherService._cache.clear()

    with patch.object(WeatherService, "_fetch_open_meteo", side_effect=Exception("Network unreachable")):
        res = WeatherService.get_live_weather(35.10, 129.00, "부산 남포동")
        assert res["is_live"] is False
        assert "시뮬레이션" in res["source"]
        assert "우산" in res["umbrella_tip"]
        assert "°C" in res["temp"]


def test_weather_service_wmo_code_and_air_grade():
    # Mocking httpx response
    mock_forecast_resp = MagicMock()
    mock_forecast_resp.json.return_value = {
        "current": {
            "temperature_2m": 15.5,
            "apparent_temperature": 14.0,
            "precipitation": 2.5,
            "weather_code": 63,  # 보통 비
        },
        "daily": {
            "precipitation_probability_max": [80],
        },
    }
    mock_forecast_resp.raise_for_status = MagicMock()

    mock_air_resp = MagicMock()
    mock_air_resp.json.return_value = {
        "current": {
            "pm10": 95.0,  # 나쁨
            "pm2_5": 45.0,  # 나쁨
        },
    }
    mock_air_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.side_effect = [mock_forecast_resp, mock_air_resp]
        mock_client_cls.return_value = mock_client

        WeatherService._cache.clear()
        res = WeatherService.get_live_weather(37.50, 127.00, "강남")

        assert res["temp"] == "15.5°C"
        assert res["feels_like"] == "14.0°C"
        assert "보통 비" in res["sky"]
        assert "우산 필수" in res["umbrella_tip"]
        assert res["rain_prob"] == "80%"
        assert "나쁨 🟠" in res["pm10"]
        assert "나쁨 🟠" in res["pm25"]
