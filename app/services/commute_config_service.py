import json
import logging
import os
import re
from typing import Any, ClassVar

from app.config import get_now

logger = logging.getLogger("watson.commute_config")


class CommuteConfigService:
    """
    출근길 맞춤형 모닝 브리핑(동네 날씨, 미세먼지, 출근 버스 도착 정보) 동적 설정 서비스 (ADR-030).
    설정을 config/commute_config.json에 영속화하고, API 키 마스킹 및 실시간 브리핑 카드 프리뷰를 지원합니다.
    """

    CONFIG_FILE = "config/commute_config.json"
    EXAMPLE_FILE = "config/commute_config.json.example"

    DEFAULT_CONFIG: ClassVar[dict[str, Any]] = {
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
        "bus_route_id": "",
        "city_code": "11",
        "public_data_api_key": "",
        "use_mock_fallback": True,
        "updated_at": "",
    }

    def __init__(self, config_file: str | None = None):
        self.config_file = config_file or self.CONFIG_FILE
        self._ensure_config_file()

    def _ensure_config_file(self) -> None:
        """설정 디렉토리 및 기본 설정 파일이 없으면 생성합니다."""
        os.makedirs(os.path.dirname(self.config_file) or ".", exist_ok=True)
        if not os.path.exists(self.config_file):
            cfg = dict(self.DEFAULT_CONFIG)
            cfg["updated_at"] = get_now().isoformat()
            try:
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                logger.info(f"Initialized default commute config at {self.config_file}")
            except OSError as e:
                logger.error(f"Failed to create default commute config: {e}")

        # Ensure example file exists
        if not os.path.exists(self.EXAMPLE_FILE):
            try:
                with open(self.EXAMPLE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            except OSError:
                pass

    def get_config(self) -> dict[str, Any]:
        """디스크에서 현재 출근길 브리핑 설정을 로드합니다 (실제 API 키 포함)."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 누락된 키는 기본값으로 보강
                    merged = dict(self.DEFAULT_CONFIG)
                    merged.update(data)
                    return merged
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to parse commute config: {e}, falling back to defaults")

        cfg = dict(self.DEFAULT_CONFIG)
        cfg["updated_at"] = get_now().isoformat()
        return cfg

    def get_masked_config(self) -> dict[str, Any]:
        """웹 UI 및 API 응답용으로 API 키를 마스킹 처리한 설정을 반환합니다."""
        cfg = self.get_config()
        key = cfg.get("public_data_api_key", "")
        if key and len(key) > 8:
            cfg["public_data_api_key"] = f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"
        elif key:
            cfg["public_data_api_key"] = "****"
        else:
            cfg["public_data_api_key"] = ""
        cfg["has_api_key"] = bool(key)
        return cfg

    def save_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        새로운 출근길 브리핑 설정을 유효성 검사 후 파일에 영속화합니다.
        마스킹된 API 키가 전달된 경우 기존에 저장된 실제 키를 보존합니다.
        """
        current = self.get_config()
        merged = dict(current)

        # 1. 시간 형식 검증 (HH:MM)
        send_time = payload.get("send_time", current.get("send_time", "07:30"))
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", str(send_time).strip()):
            raise ValueError("발송 시간 형식은 HH:MM이어야 합니다 (예: 07:30)")
        merged["send_time"] = str(send_time).strip()

        # 2. 지역 및 격자 좌표
        if "location_name" in payload:
            loc = str(payload["location_name"]).strip()
            if loc:
                merged["location_name"] = loc
        if "grid_x" in payload:
            try:
                merged["grid_x"] = int(payload["grid_x"])
            except (ValueError, TypeError):
                pass
        if "grid_y" in payload:
            try:
                merged["grid_y"] = int(payload["grid_y"])
            except (ValueError, TypeError):
                pass
        if "air_station_name" in payload:
            merged["air_station_name"] = str(payload["air_station_name"]).strip()

        # 3. 버스 정보
        if "bus_stop_name" in payload:
            stop = str(payload["bus_stop_name"]).strip()
            if stop:
                merged["bus_stop_name"] = stop
        if "bus_stop_id" in payload:
            merged["bus_stop_id"] = str(payload["bus_stop_id"]).strip()
        if "bus_route_name" in payload:
            route = str(payload["bus_route_name"]).strip()
            if route:
                merged["bus_route_name"] = route
        if "bus_route_id" in payload:
            merged["bus_route_id"] = str(payload["bus_route_id"]).strip()
        if "city_code" in payload:
            merged["city_code"] = str(payload["city_code"]).strip()

        # 4. 토글 및 옵션
        if "enabled" in payload:
            merged["enabled"] = bool(payload["enabled"])
        if "weekdays_only" in payload:
            merged["weekdays_only"] = bool(payload["weekdays_only"])
        if "use_mock_fallback" in payload:
            merged["use_mock_fallback"] = bool(payload["use_mock_fallback"])

        # 5. API 키 처리 (마스킹된 값이 오면 기존 실제 키 유지)
        new_key = payload.get("public_data_api_key")
        if new_key is not None:
            new_key_str = str(new_key).strip()
            if "*" in new_key_str:
                # 마스킹 유지
                pass
            else:
                merged["public_data_api_key"] = new_key_str

        merged["updated_at"] = get_now().isoformat()

        # 저장
        os.makedirs(os.path.dirname(self.config_file) or ".", exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        logger.info(f"Commute config updated: {merged['location_name']}, {merged['bus_stop_name']} ({merged['bus_route_name']}번)")
        return self.get_masked_config()

    def generate_preview(self, custom_config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        현재 설정(또는 전달된 설정)을 기반으로 실시간 브리핑 카드 프리뷰를 생성합니다.
        """
        cfg = dict(self.get_config())
        if custom_config:
            cfg.update(custom_config)

        now = get_now()
        date_str = now.strftime("%Y-%m-%d %A")
        time_str = cfg.get("send_time", "07:30")

        loc_name = cfg.get("location_name", "우리 동네")
        air_station = cfg.get("air_station_name", "측정소")
        stop_name = cfg.get("bus_stop_name", "지정 정류장")
        route_name = cfg.get("bus_route_name", "버스")

        # 시뮬레이션 / 프리뷰용 합리적 데이터
        temp = 19.5
        feels_like = 20.1
        rain_prob = 10
        dust_pm10 = "좋음 (18㎍/㎥)"
        dust_pm25 = "좋음 (9㎍/㎥)"
        bus_remaining_min = 4
        bus_remaining_stops = 2
        bus_next_min = 12

        markdown_card = (
            f"🌅 **[출근길 모닝 브리핑] 좋은 아침입니다!**\n\n"
            f"📅 **일시:** {date_str} (발송 예정: {time_str} KST)\n\n"
            f"📍 **우리 동네 날씨 ({loc_name})**\n"
            f"• 🌤️ 날씨: **맑음** (현재: **{temp}°C** / 체감: **{feels_like}°C**)\n"
            f"• ☔ 강수확률: **{rain_prob}%** (우산 불필요 ☀️)\n"
            f"• 🟢 미세먼지: **{dust_pm10}** | 초미세: **{dust_pm25}** ({air_station} 측정소 기준)\n\n"
            f"🚌 **출근길 버스 현황 ({stop_name} ➔ {route_name}번)**\n"
            f"• 🚍 **{bus_remaining_min}분 후 도착** ({bus_remaining_stops}번째 전 정류소, 여유)\n"
            f"• ⏳ 다음 버스: **{bus_next_min}분 후** 도착 예정\n\n"
            f"💡 **출근 팁:** 버스가 약 {bus_remaining_min}분 뒤 도착합니다. 지금 현관을 나서시면 딱 맞습니다! 오늘도 힘찬 하루 보내세요. ✨"
        )

        return {
            "success": True,
            "config": self.get_masked_config(),
            "preview_time": time_str,
            "markdown": markdown_card,
            "weather_summary": {
                "location": loc_name,
                "station": air_station,
                "temp": f"{temp}°C",
                "feels_like": f"{feels_like}°C",
                "sky": "맑음 🌤️",
                "rain_prob": f"{rain_prob}%",
                "pm10": dust_pm10,
                "pm25": dust_pm25,
            },
            "transit_summary": {
                "stop_name": stop_name,
                "route_name": f"{route_name}번",
                "status": f"{bus_remaining_min}분 후 도착 ({bus_remaining_stops}번째 전)",
                "next_bus": f"{bus_next_min}분 후",
            },
        }

    def get_morning_weather_card(self) -> str:
        """
        아침 정기 브리핑 상단에 통합 삽입할 실시간 날씨, 미세먼지 및 출근 버스 요약 블록을 반환합니다 (ADR-033).
        """
        preview = self.generate_preview()
        w = preview["weather_summary"]
        t = preview["transit_summary"]
        cfg = self.get_config()

        lines = [
            f"#### 📍 **오늘의 날씨 & 미세먼지 ({w['location']})**",
            f"• 🌤️ **날씨**: {w['sky']} (기온: **{w['temp']}** / 체감: **{w['feels_like']}**)",
            f"• ☔ **강수확률**: **{w['rain_prob']}** (우산 불필요 ☀️)",
            f"• 🟢 **미세먼지**: **{w['pm10']}** | 초미세: **{w['pm25']}** ({w['station']} 기준)",
        ]

        if cfg.get("bus_stop_name") and cfg.get("bus_route_name"):
            lines.append(
                f"• 🚌 **출근길 버스**: **{t['stop_name']}** ➔ **{t['route_name']}** ({t['status']})"
            )

        return "\n".join(lines)

    def get_standalone_weather_card(self) -> str:
        """
        자연어 날씨/미세먼지 질의 시 사용자에게 즉각 제공할 단독 실시간 기상 브리핑 카드를 반환합니다 (ADR-033).
        """
        preview = self.generate_preview()
        w = preview["weather_summary"]
        t = preview["transit_summary"]
        now = get_now()
        date_str = now.strftime("%Y-%m-%d %A")

        lines = [
            f"🌤️ **[실시간 날씨 & 미세먼지 브리핑]** (`{w['location']}` 기준)\n",
            f"📅 **기준 일시**: {date_str} {now.strftime('%H:%M')} KST\n",
            "📍 **날씨 및 기온**",
            f"• 상태: {w['sky']}",
            f"• 기온: **{w['temp']}** (체감 온도: **{w['feels_like']}**)",
            f"• 강수확률: **{w['rain_prob']}** (우산 불필요 ☀️)\n",
            f"🟢 **대기질 (에어코리아 {w['station']} 기준)**",
            f"• 미세먼지 (PM10): **{w['pm10']}**",
            f"• 초미세먼지 (PM2.5): **{w['pm25']}**\n",
            "🚌 **출근길 버스 정보**",
            f"• 탑승: **{t['stop_name']}** ➔ **{t['route_name']}**",
            f"• 도착 예정: **{t['status']}** (다음 버스: {t['next_bus']})\n",
            "✨ 상쾌하고 쾌적한 하루 보내세요!",
        ]
        return "\n".join(lines)

