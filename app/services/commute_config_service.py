import json
import logging
import os
import re
from typing import Any, ClassVar

from app.config import get_now
from app.services.weather_service import WeatherService

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
        "latitude": 37.50,
        "longitude": 127.04,
        "air_station_name": "강남구",
        "bus_stop_name": "역삼역",
        "bus_stop_id": "23284",
        "bus_route_name": "146",
        "bus_route_id": "",
        "city_code": "11",
        "public_data_api_key": "",
        "public_data_endpoint": "https://apis.data.go.kr/1613000/ArvlInfoInqireService",
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
                    # 위도/경도가 누락된 경우 location_name 기반 자동 보강
                    if "latitude" not in data or "longitude" not in data:
                        from app.services.geo_service import GeoService
                        res = GeoService.resolve_location(merged.get("location_name", ""))
                        merged["latitude"] = res.get("latitude", 37.55)
                        merged["longitude"] = res.get("longitude", 127.02)
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
        if "latitude" in payload:
            try:
                merged["latitude"] = float(payload["latitude"])
            except (ValueError, TypeError):
                pass
        if "longitude" in payload:
            try:
                merged["longitude"] = float(payload["longitude"])
            except (ValueError, TypeError):
                pass
        if "air_station_name" in payload:
            merged["air_station_name"] = str(payload["air_station_name"]).strip()

        # 3. 버스 정보
        if "bus_stop_name" in payload:
            merged["bus_stop_name"] = str(payload["bus_stop_name"]).strip()
        if "bus_stop_id" in payload:
            merged["bus_stop_id"] = str(payload["bus_stop_id"]).strip()
        if "bus_route_name" in payload:
            merged["bus_route_name"] = str(payload["bus_route_name"]).strip()
        if "bus_route_id" in payload:
            merged["bus_route_id"] = str(payload["bus_route_id"]).strip()
        if "city_code" in payload:
            merged["city_code"] = str(payload["city_code"]).strip()

        # 정류소 번호가 제공되었을 때 정류소명이 비어있거나, 이전 기본값('역삼역')이고 번호가 23284가 아닌 경우 자동 조회
        sid = merged.get("bus_stop_id", "")
        current_name = merged.get("bus_stop_name", "")
        if sid and (not current_name or (current_name == "역삼역" and sid != "23284") or current_name == "정류장"):
            resolved = self.resolve_bus_stop(sid, merged.get("city_code", "11"))
            if resolved.get("stop_name") and not str(resolved["stop_name"]).startswith("정류소("):
                merged["bus_stop_name"] = resolved["stop_name"]

        # '버스'라는 예전 플레이스홀더가 들어온 경우 빈 문자열(전체 노선)로 정제
        if merged.get("bus_route_name") == "버스":
            merged["bus_route_name"] = ""

        # 4. 토글 및 옵션
        if "enabled" in payload:
            merged["enabled"] = bool(payload["enabled"])
        if "weekdays_only" in payload:
            merged["weekdays_only"] = bool(payload["weekdays_only"])
        if "use_mock_fallback" in payload:
            merged["use_mock_fallback"] = bool(payload["use_mock_fallback"])

        # 5. API 키 및 엔드포인트 처리 (마스킹된 값이 오면 기존 실제 키 유지)
        if "public_data_endpoint" in payload:
            ep = str(payload["public_data_endpoint"]).strip()
            if ep:
                merged["public_data_endpoint"] = ep

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

        logger.info(f"Commute config updated: {merged['location_name']}, {merged.get('bus_stop_name', '')} ({merged.get('bus_route_name', '')}번)")
        return self.get_masked_config()

    def generate_preview(self, custom_config: dict[str, Any] | None = None, force_refresh: bool = False) -> dict[str, Any]:
        """
        현재 설정(또는 전달된 설정)을 기반으로 실시간 브리핑 카드 프리뷰를 생성합니다 (ADR-030, ADR-035, ADR-037, ADR-039).
        Open-Meteo 실시간 오픈 API를 통해 거주지 기반 실시간 날씨와 대기질을 즉시 반영합니다.
        force_refresh=True일 경우 버스 도착 캐시를 우회하고 최신 도착 현황을 강제 조회합니다.
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
        route_name = cfg.get("bus_route_name", "")
        lat = float(cfg.get("latitude", 37.55))
        lon = float(cfg.get("longitude", 127.02))

        # Open-Meteo 실시간 기상/대기질 조회 (10분 캐시 & 안전 폴백)
        live_w = WeatherService.get_live_weather(latitude=lat, longitude=lon, location_name=loc_name)

        temp_str = live_w["temp"]
        feels_str = live_w["feels_like"]
        sky_str = live_w["sky"]
        rain_prob_str = live_w["rain_prob"]
        umbrella_tip = live_w.get("umbrella_tip", "우산 불필요 ☀️")
        dust_pm10 = live_w["pm10"]
        dust_pm25 = live_w["pm25"]
        source_str = live_w.get("source", "Open-Meteo 실시간 라이브 API")
        updated_time = live_w.get("updated_time", now.strftime("%H:%M"))

        # BusService를 통한 실시간 출근 버스 도착 정보 조회 (ADR-037, ADR-039)
        from app.services.bus_service import BusService

        bus_info = BusService.get_arrival_info(
            bus_stop_id=str(cfg.get("bus_stop_id", "")),
            bus_route_name=str(route_name),
            api_key=cfg.get("public_data_api_key"),
            city_code=str(cfg.get("city_code", "11")),
            use_mock_fallback=bool(cfg.get("use_mock_fallback", True)),
            bus_stop_name=stop_name,
            endpoint=cfg.get("public_data_endpoint"),
            force_refresh=force_refresh,
        )

        bus_status_str = bus_info["status"]
        bus_next_str = bus_info["next_bus"]
        bus_tip = bus_info["tip"]
        bus_source = bus_info["source"]
        bus_remaining_min = bus_info.get("remaining_min")
        is_all_routes = bool(bus_info.get("is_all_routes", False))
        resolved_stop = bus_info.get("stop_name") or stop_name

        if is_all_routes:
            bus_block = (
                f"🚌 **출근길 버스 현황 ({resolved_stop} 전체 노선)**\n"
                f"{bus_status_str}\n"
                f"*(📡 {bus_source})*"
            )
        else:
            bus_block = (
                f"🚌 **출근길 버스 현황 ({resolved_stop} ➔ {route_name}번)**\n"
                f"• 🚍 **{bus_status_str}**\n"
                f"• ⏳ 다음 버스: **{bus_next_str}** 도착 예정\n"
                f"*(📡 {bus_source})*"
            )

        markdown_card = (
            f"🌅 **[출근길 모닝 브리핑] 좋은 아침입니다!**\n\n"
            f"📅 **일시:** {date_str} (발송 예정: {time_str} KST)\n\n"
            f"📍 **우리 동네 날씨 ({loc_name})**\n"
            f"• 🌤️ 날씨: **{sky_str}** (현재: **{temp_str}** / 체감: **{feels_str}**)\n"
            f"• ☔ 강수확률: **{rain_prob_str}** ({umbrella_tip})\n"
            f"• 🟢 미세먼지: **{dust_pm10}** | 초미세: **{dust_pm25}**\n"
            f"*(📡 {source_str} - {updated_time} 기준)*\n\n"
            f"{bus_block}\n\n"
            f"💡 **출근 팁:** {bus_tip}"
        )

        return {
            "success": True,
            "config": self.get_masked_config(),
            "preview_time": time_str,
            "markdown": markdown_card,
            "bus_tip": bus_tip,
            "weather_summary": {
                "location": loc_name,
                "station": air_station,
                "temp": temp_str,
                "feels_like": feels_str,
                "sky": sky_str,
                "rain_prob": rain_prob_str,
                "umbrella_tip": umbrella_tip,
                "pm10": dust_pm10,
                "pm25": dust_pm25,
                "source": source_str,
                "is_live": live_w.get("is_live", True),
                "updated_time": updated_time,
            },
            "transit_summary": {
                "stop_name": resolved_stop,
                "route_name": "전체 노선" if is_all_routes else f"{route_name}번",
                "status": bus_status_str,
                "next_bus": bus_next_str,
                "source": bus_source,
                "is_live": bus_info.get("is_live", False),
                "is_all_routes": is_all_routes,
                "remaining_min": bus_remaining_min,
                "remaining_stops": bus_info.get("remaining_stops"),
                "buses": bus_info.get("buses", []),
            },
        }

    def get_morning_weather_card(self, force_refresh: bool = False) -> str:
        """
        아침 정기 브리핑 상단에 통합 삽입할 실시간 날씨, 미세먼지 및 출근 버스 요약 블록을 반환합니다 (ADR-033, ADR-035, ADR-037, ADR-039).
        """
        preview = self.generate_preview(force_refresh=force_refresh)
        w = preview["weather_summary"]
        t = preview["transit_summary"]
        cfg = self.get_config()

        lines = [
            f"#### 📍 **오늘의 날씨 & 미세먼지 ({w['location']})**",
            f"• 🌤️ **날씨**: {w['sky']} (기온: **{w['temp']}** / 체감: **{w['feels_like']}**)",
            f"• ☔ **강수확률**: **{w['rain_prob']}** ({w.get('umbrella_tip', '우산 불필요 ☀️')})",
            f"• 🟢 **대기질**: 미세 **{w['pm10']}** | 초미세 **{w['pm25']}**",
        ]

        if cfg.get("bus_stop_id") or cfg.get("bus_stop_name"):
            if t.get("is_all_routes"):
                lines.append(
                    f"• 🚌 **출근길 버스 ({t['stop_name']} 전체 노선)**:\n{t['status']}"
                )
            else:
                lines.append(
                    f"• 🚌 **출근길 버스**: **{t['stop_name']}** ➔ **{t['route_name']}** ({t['status']})"
                )

        lines.append(f"*(📡 {w.get('source', 'Open-Meteo 실시간 API')})*")
        return "\n".join(lines)

    def get_standalone_weather_card(self, force_refresh: bool = False) -> str:
        """
        자연어 날씨/미세먼지 질의 시 사용자에게 즉각 제공할 단독 실시간 기상 브리핑 카드를 반환합니다 (ADR-033, ADR-035, ADR-037, ADR-039).
        """
        preview = self.generate_preview(force_refresh=force_refresh)
        w = preview["weather_summary"]
        t = preview["transit_summary"]
        now = get_now()
        date_str = now.strftime("%Y-%m-%d %A")

        lines = [
            f"🌤️ **[실시간 날씨 & 미세먼지 브리핑]** (`{w['location']}` 기준)\n",
            f"📅 **기준 일시**: {date_str} {w.get('updated_time', now.strftime('%H:%M'))} KST ({w.get('source', '실시간 API')})\n",
            "📍 **날씨 및 기온**",
            f"• 상태: {w['sky']}",
            f"• 기온: **{w['temp']}** (체감 온도: **{w['feels_like']}**)",
            f"• 강수확률: **{w['rain_prob']}** ({w.get('umbrella_tip', '우산 불필요 ☀️')})\n",
            "🟢 **실시간 대기질**",
            f"• 미세먼지 (PM10): **{w['pm10']}**",
            f"• 초미세먼지 (PM2.5): **{w['pm25']}**\n",
        ]

        if t.get("is_all_routes"):
            lines.extend([
                "🚌 **출근길 버스 정보**",
                f"• 탑승 정류소: **{t['stop_name']}** (전체 노선)",
                f"{t['status']}\n",
            ])
        else:
            lines.extend([
                "🚌 **출근길 버스 정보**",
                f"• 탑승: **{t['stop_name']}** ➔ **{t['route_name']}**",
                f"• 도착 예정: **{t['status']}** (다음 버스: {t['next_bus']})\n",
            ])

        lines.append("✨ 상쾌하고 쾌적한 하루 보내세요!")
        return "\n".join(lines)

    def get_standalone_bus_card(self, force_refresh: bool = False) -> str:
        """
        자연어 버스 도착 질의(/bus, '출근 버스 언제 와?', '버스 정보') 시
        사용자에게 즉각 제공할 단독 실시간 버스 도착 브리핑 카드를 반환합니다 (ADR-037, ADR-039).
        """
        preview = self.generate_preview(force_refresh=force_refresh)
        t = preview["transit_summary"]
        now = get_now()
        date_str = now.strftime("%Y-%m-%d %A")
        time_str = now.strftime("%H:%M:%S")

        if t.get("is_all_routes"):
            lines = [
                f"🚌 **[실시간 출근 버스 도착 정보]** (`{t['stop_name']}` 정류소 전체 노선)\n",
                f"📅 **조회 일시**: {date_str} {time_str} KST ({t.get('source', '실시간 API')})\n",
                "🚍 **정류소 실시간 도착 현황**",
                f"{t['status']}\n",
                f"💡 **출근 팁:** {preview.get('bus_tip', '안전하게 이동하세요! ✨')}",
            ]
        else:
            lines = [
                f"🚌 **[실시간 출근 버스 도착 정보]** (`{t['stop_name']}` ➔ `{t['route_name']}`)\n",
                f"📅 **조회 일시**: {date_str} {time_str} KST ({t.get('source', '실시간 API')})\n",
                "🚍 **도착 예정 현황**",
                f"• 탑승 정류소: **{t['stop_name']}**",
                f"• 버스 노선: **{t['route_name']}**",
                f"• 도착 현황: **{t['status']}**",
                f"• 다음 버스: **{t['next_bus']}**\n",
                f"💡 **출근 팁:** {preview.get('bus_tip', '안전하게 이동하세요! ✨')}",
            ]
        return "\n".join(lines)

    def update_location_by_query(self, query: str) -> dict[str, Any]:
        """
        자연어 동네명(예: '성동구 금호동', '판교', '마포구 상암동')을 스마트 지오코딩하여
        설정에 즉시 반영하고 영속화합니다 (ADR-034, ADR-035).
        """
        from app.services.geo_service import GeoService

        resolved = GeoService.resolve_location(query)
        payload = {
            "location_name": resolved["location_name"],
            "grid_x": resolved["grid_x"],
            "grid_y": resolved["grid_y"],
            "latitude": resolved.get("latitude", 37.55),
            "longitude": resolved.get("longitude", 127.02),
            "air_station_name": resolved["air_station_name"],
            "city_code": resolved["city_code"],
        }
        saved_cfg = self.save_config(payload)
        return {
            "resolved": resolved,
            "config": saved_cfg,
        }

    def resolve_bus_stop(self, bus_stop_id: str, city_code: str = "11") -> dict[str, Any]:
        """
        정류소 번호(ARS-ID, Node ID)를 기반으로 정류소명, 방면, 지역 정보를 자동 조회합니다 (ADR-038).
        """
        from app.services.bus_service import BusService

        cfg = self.get_config()
        return BusService.resolve_bus_stop(
            bus_stop_id=bus_stop_id,
            city_code=city_code or str(cfg.get("city_code", "11")),
            api_key=cfg.get("public_data_api_key"),
            endpoint=cfg.get("public_data_endpoint"),
        )

