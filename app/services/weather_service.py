"""
실시간 오픈 기상 및 대기질 API 서비스 (ADR-035).
Open-Meteo 무설정(Zero-Key) 오픈 API를 통해 거주지 위경도 기반
실시간 기온, 체감기온, 하늘상태, 강수확률, 미세먼지(PM10)/초미세먼지(PM2.5)를
0.1초 내로 조회하고 인메모리 캐시(TTL 10분)로 최적화합니다.
"""

from __future__ import annotations

import logging
import time
from typing import Any, ClassVar

import httpx

from app.config import get_now

logger = logging.getLogger("watson.weather_service")


class WeatherService:
    """Open-Meteo 기반 실시간 기상/대기질 조회 서비스"""

    FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
    AIR_QUALITY_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
    CACHE_TTL_SECONDS = 600  # 10분 캐시

    # WMO Weather interpretation codes (WW)
    WMO_CODE_MAP: ClassVar[dict[int, tuple[str, str]]] = {
        0: ("맑음", "☀️"),
        1: ("대체로 맑음", "🌤️"),
        2: ("구름 조금", "⛅"),
        3: ("흐림", "☁️"),
        45: ("안개", "🌫️"),
        48: ("상착 안개", "🌫️"),
        51: ("가벼운 이슬비", "🌧️"),
        53: ("이슬비", "🌧️"),
        55: ("짙은 이슬비", "🌧️"),
        56: ("어는 이슬비", "🌨️"),
        57: ("짙은 어는 이슬비", "🌨️"),
        61: ("약한 비", "🌧️"),
        63: ("보통 비", "🌧️"),
        65: ("강한 비", "🌧️"),
        66: ("어는 비", "🌨️"),
        67: ("강한 어는 비", "🌨️"),
        71: ("약한 눈", "❄️"),
        73: ("보통 눈", "❄️"),
        75: ("강한 눈", "❄️"),
        77: ("싸락눈", "❄️"),
        80: ("약한 소나기", "🌦️"),
        81: ("보통 소나기", "🌦️"),
        82: ("강한 소나기", "🌦️"),
        85: ("약한 눈보라", "🌨️"),
        86: ("강한 눈보라", "🌨️"),
        95: ("뇌우", "⛈️"),
        96: ("뇌우 및 우박", "⛈️"),
        99: ("강한 뇌우 및 우박", "⛈️"),
    }

    _cache: ClassVar[dict[str, tuple[float, dict[str, Any]]]] = {}

    @classmethod
    def get_live_weather(
        cls,
        latitude: float = 37.55,
        longitude: float = 127.02,
        location_name: str = "서울 성동구 금호동",
    ) -> dict[str, Any]:
        """
        주어진 위도/경도의 실시간 기상 및 대기질 정보를 조회합니다.
        네트워크 장애나 지연 시 최근 캐시 또는 합리적인 시뮬레이션 데이터로 안전 폴백합니다.
        """
        cache_key = f"{latitude:.2f},{longitude:.2f}"
        now_ts = time.time()

        if cache_key in cls._cache:
            cached_time, cached_data = cls._cache[cache_key]
            if now_ts - cached_time < cls.CACHE_TTL_SECONDS:
                logger.debug(f"Using cached weather data for {cache_key}")
                return cached_data

        try:
            weather_res = cls._fetch_open_meteo(latitude, longitude)
            cls._cache[cache_key] = (now_ts, weather_res)
            return weather_res
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to fetch live weather from Open-Meteo: {e}, using fallback")
            if cache_key in cls._cache:
                return cls._cache[cache_key][1]
            return cls._get_fallback_weather(location_name)

    @classmethod
    def _fetch_open_meteo(cls, lat: float, lon: float) -> dict[str, Any]:
        """Open-Meteo Forecast & Air Quality API 호출 및 데이터 합성"""
        timeout = httpx.Timeout(3.5, connect=2.0)
        with httpx.Client(timeout=timeout) as client:
            # 1. 기상 예보 조회
            forecast_resp = client.get(
                cls.FORECAST_API_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,apparent_temperature,precipitation,weather_code",
                    "daily": "precipitation_probability_max",
                    "timezone": "Asia/Seoul",
                },
            )
            forecast_resp.raise_for_status()
            f_data = forecast_resp.json()

            # 2. 대기질 조회
            air_resp = client.get(
                cls.AIR_QUALITY_API_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "pm10,pm2_5",
                    "timezone": "Asia/Seoul",
                },
            )
            air_resp.raise_for_status()
            a_data = air_resp.json()

        # 데이터 파싱
        curr = f_data.get("current", {})
        daily = f_data.get("daily", {})
        air_curr = a_data.get("current", {})

        temp = float(curr.get("temperature_2m", 20.0))
        feels_like = float(curr.get("apparent_temperature", temp))
        w_code = int(curr.get("weather_code", 0))
        sky_desc, sky_emoji = cls.WMO_CODE_MAP.get(w_code, ("맑음", "☀️"))

        # 강수확률
        pop_list = daily.get("precipitation_probability_max", [0])
        rain_prob = int(pop_list[0]) if pop_list else 0

        # 우산 팁
        if rain_prob >= 60 or w_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]:
            umbrella_tip = "우산 필수 ☔ (비/소나기 예보)"
        elif rain_prob >= 30 or w_code in [2, 3]:
            umbrella_tip = "접이식 우산 추천 🌂 (강수 가능성 있음)"
        else:
            umbrella_tip = "우산 불필요 ☀️ (비 걱정 없음)"

        # 대기질 파싱
        pm10_val = float(air_curr.get("pm10", 25.0))
        pm25_val = float(air_curr.get("pm2_5", 15.0))

        # 한국 환경부 기준 등급
        if pm10_val <= 30:
            pm10_grade = "좋음 🟢"
        elif pm10_val <= 80:
            pm10_grade = "보통 🟡"
        elif pm10_val <= 150:
            pm10_grade = "나쁨 🟠"
        else:
            pm10_grade = "매우나쁨 🔴"

        if pm25_val <= 15:
            pm25_grade = "좋음 🟢"
        elif pm25_val <= 35:
            pm25_grade = "보통 🟡"
        elif pm25_val <= 75:
            pm25_grade = "나쁨 🟠"
        else:
            pm25_grade = "매우나쁨 🔴"

        now_time_str = get_now().strftime("%H:%M")

        return {
            "is_live": True,
            "source": "Open-Meteo 실시간 라이브 API",
            "updated_time": now_time_str,
            "temp": f"{temp:.1f}°C",
            "feels_like": f"{feels_like:.1f}°C",
            "raw_temp": temp,
            "raw_feels_like": feels_like,
            "sky": f"{sky_desc} {sky_emoji}",
            "weather_code": w_code,
            "rain_prob": f"{rain_prob}%",
            "raw_rain_prob": rain_prob,
            "umbrella_tip": umbrella_tip,
            "pm10": f"{pm10_grade} ({pm10_val:.0f}㎍/㎥)",
            "pm25": f"{pm25_grade} ({pm25_val:.0f}㎍/㎥)",
            "raw_pm10": pm10_val,
            "raw_pm25": pm25_val,
        }

    @classmethod
    def _get_fallback_weather(cls, location_name: str) -> dict[str, Any]:
        """오프라인 또는 오류 시 안전 시뮬레이션 폴백 데이터"""
        return {
            "is_live": False,
            "source": "스마트 시뮬레이션 (Mock Fallback)",
            "updated_time": get_now().strftime("%H:%M"),
            "temp": "21.5°C",
            "feels_like": "22.0°C",
            "raw_temp": 21.5,
            "raw_feels_like": 22.0,
            "sky": "맑음 ☀️",
            "weather_code": 0,
            "rain_prob": "10%",
            "raw_rain_prob": 10,
            "umbrella_tip": "우산 불필요 ☀️",
            "pm10": "좋음 🟢 (22㎍/㎥)",
            "pm25": "좋음 🟢 (12㎍/㎥)",
            "raw_pm10": 22.0,
            "raw_pm25": 12.0,
        }
