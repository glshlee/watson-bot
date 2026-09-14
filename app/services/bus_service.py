import logging
import re
import time
import urllib.parse
from typing import Any, ClassVar

import httpx

from app.config import get_now

logger = logging.getLogger("watson.bus_service")


class BusService:
    """
    실시간 출근 버스 도착정보 조회 및 지능형 캐시·폴백 서비스 (ADR-037).
    
    지원 API:
    1. 서울시 버스도착정보조회 서비스 (TOPIS):
       - http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid
       - ARS-ID(5자리 정류소 번호) 및 노선번호 기반 실시간 잔여시간, 잔여 정류소, 막차/차고지 상태 조회.
       - 노선 번호 미입력 시 정류소명 자동 인식 및 해당 정류소 전체 도착 버스 타임라인 일괄 브리핑.
    2. 국토교통부(TAGO) 버스도착정보조회 서비스:
       - https://apis.data.go.kr/1613000/ArvlInfoInqireService/getSttnAcctoArvlPrearngeInfoList
       - 전국 및 경기도 정류소(nodeId) 기반 실시간 도착 예정 조회.
       - 노선 번호 미입력 시 정류소명 자동 인식 및 전 노선 정렬 브리핑.
    3. 스마트 시뮬레이션 및 고탄력 안전 폴백:
       - API 키 미등록, 인증 실패, 타임아웃 또는 미운행 시간대에 시간 기반의 동적 가변 시뮬레이션 제공.
       - 45초 TTL 인메모리 캐시를 적용하여 API 쿼터 보호 및 고속 응답 보장.
    """

    CACHE_TTL: float = 45.0  # 45초 캐시
    _cache: ClassVar[dict[str, tuple[float, dict[str, Any]]]] = {}
    _stop_name_cache: ClassVar[dict[str, dict[str, Any]]] = {}

    @classmethod
    def clear_cache(cls) -> None:
        """인메모리 캐시를 초기화합니다 (테스트용)."""
        cls._cache.clear()
        cls._stop_name_cache.clear()

    @classmethod
    def normalize_route_name(cls, route_name: str) -> str:
        """노선명에서 '번', 공백 등을 제거하여 정규화합니다 (예: '146번' -> '146')."""
        cleaned = re.sub(r"번$", "", route_name.strip())
        return cleaned.strip()

    @classmethod
    def parse_arrmsg(cls, arrmsg: str) -> dict[str, Any]:
        """
        서울시 TOPIS 도착 메시지 문자열을 파싱하여 잔여 분, 정류소 수, 상태를 추출합니다.
        """
        if not arrmsg or not arrmsg.strip():
            return {"min": None, "stops": None, "text": "도착 정보 없음"}

        msg = arrmsg.strip()
        if "곧 도착" in msg:
            return {"min": 1, "stops": 1, "text": "곧 도착 (1번째 전)"}
        if "운행종료" in msg:
            return {"min": None, "stops": None, "text": "운행종료"}
        if "출발대기" in msg:
            return {"min": None, "stops": None, "text": "출발대기 (차고지)"}

        # 정규식 1: '(\d+)분(?: (\d+)초)?후[(\d+)번째 전]'
        m = re.search(r"(\d+)\s*분(?:\s*(\d+)\s*초)?\s*후\s*\[(\d+)\s*번째\s*전\]", msg)
        if m:
            mins = int(m.group(1))
            stops = int(m.group(3))
            return {
                "min": mins,
                "stops": stops,
                "text": f"{mins}분 후 도착 ({stops}번째 전)",
            }

        # 정규식 2: '(\d+)분후'
        m2 = re.search(r"(\d+)\s*분\s*후", msg)
        if m2:
            mins = int(m2.group(1))
            return {"min": mins, "stops": 1, "text": f"{mins}분 후 도착"}

        return {"min": None, "stops": None, "text": msg}

    @classmethod
    def generate_commute_tip(cls, remaining_min: int | None, status_text: str = "") -> str:
        """잔여 시간에 따라 비서다운 맞춤형 출근 팁을 생성합니다."""
        if "운행종료" in status_text:
            return "현재 해당 노선은 운행 종료 상태입니다. 지하철이나 대체 교통편을 확인해 주세요. 🚇"
        if "출발대기" in status_text:
            return "차고지에서 출발 대기 중입니다. 잠시 후 실시간 도착 예정 시간이 갱신됩니다. ⏳"

        if remaining_min is not None:
            if remaining_min <= 2:
                return "버스가 곧 정류장에 도착합니다! 서둘러 이동하세요. 🏃💨"
            if 3 <= remaining_min <= 6:
                return f"버스가 약 {remaining_min}분 뒤 도착합니다. 지금 현관을 나서시면 딱 맞습니다! 👟"
            if 7 <= remaining_min <= 12:
                return f"버스가 약 {remaining_min}분 뒤 도착합니다. 여유 있게 준비하시고 출발하세요. ☕"
            return f"도착까지 약 {remaining_min}분 남았습니다. 아직 준비하기에 여유가 있습니다. ✨"

        return "실시간 버스 도착 정보를 확인하시고 안전하게 이동하세요. ✨"

    @classmethod
    def resolve_bus_stop(
        cls,
        bus_stop_id: str,
        city_code: str = "11",
        api_key: str | None = None,
        endpoint: str | None = None,
        timeout: float = 3.5,
    ) -> dict[str, Any]:
        """
        정류소 번호(ARS-ID, Node ID)를 기반으로 정류소명, 방면, 지역 정보를 자동 조회합니다 (ADR-038).
        1. 공공 포털 및 지도 검색을 통한 정류소명 추출 (서울 5자리 ARS-ID 및 전국 정류소 지원)
        2. 국토교통부 TAGO 버스 API 연계
        """
        sid = bus_stop_id.strip()
        if not sid:
            return {"stop_name": "", "direction": "", "region": "", "stop_id": ""}

        if sid in cls._stop_name_cache:
            return dict(cls._stop_name_cache[sid])

        # 1. Kakao Map 공공 검색을 통한 정류소명 추출 (서울 및 전국 ARS 지원)
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            url = f"https://m.map.kakao.com/actions/searchView?q={urllib.parse.quote(sid)}"
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    text = resp.text
                    m = re.search(r'data-type="busStop"[^>]*data-title="([^"]+)"', text)
                    if m:
                        st_name = m.group(1).strip()
                        dir_m = re.search(
                            r'버스 정류장 번호 : </span>' + re.escape(sid) + r'<span class="txt_bar">\|</span>([^<]+)</span>',
                            text,
                        )
                        direction = dir_m.group(1).strip() if dir_m else ""
                        reg_m = re.search(r'<span class="txt_ginfo">([^<]+)</span>', text)
                        region = reg_m.group(1).strip() if reg_m else ""
                        res = {
                            "stop_name": st_name,
                            "direction": direction,
                            "region": region,
                            "stop_id": sid,
                            "source": "공공 정류소 데이터베이스",
                        }
                        cls._stop_name_cache[sid] = res
                        return res
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Web stop search failed for {sid}: {e}")

        # 2. TAGO API를 통한 정류소명 추출 (TAGO 등록 정류소)
        if api_key and cls._is_valid_api_key(api_key):
            try:
                tago_res = cls.fetch_tago_bus_arrival(
                    bus_stop_id=sid,
                    city_code=city_code,
                    api_key=api_key,
                    endpoint=endpoint,
                    timeout=timeout,
                )
                if tago_res and tago_res.get("stop_name"):
                    nm = str(tago_res["stop_name"])
                    if not nm.startswith("정류소("):
                        tago_result = {
                            "stop_name": nm,
                            "direction": "",
                            "region": "",
                            "stop_id": sid,
                            "source": "국토교통부 TAGO API",
                        }
                        cls._stop_name_cache[sid] = tago_result
                        return tago_result
            except Exception as e:  # noqa: BLE001
                logger.debug(f"TAGO stop resolve failed for {sid}: {e}")

        # 3. 기본 정류소 폴백
        fallback_res = {
            "stop_name": f"정류소({sid})",
            "direction": "",
            "region": "",
            "stop_id": sid,
            "source": "기본 정류소",
        }
        return fallback_res

    @classmethod
    def get_smart_mock_arrival(
        cls,
        bus_route_name: str = "",
        bus_stop_name: str = "지정 정류장",
        bus_stop_id: str = "",
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        API 키가 없거나 외부 API 장애 시 현재 시간을 기반으로 가변적인 시뮬레이션 데이터를 제공합니다.
        노선명이 비어있으면 해당 정류소의 다중 도착 버스 목록을 시뮬레이션합니다.
        """
        now = get_now()
        clean_route = cls.normalize_route_name(bus_route_name)

        cycle = 10
        rem_min = max(2, cycle - (now.minute % cycle))
        rem_stops = max(1, (rem_min + 1) // 2)
        next_min = rem_min + 9

        source_str = "시뮬레이션 모드 (공공데이터 API 키 등록 필요)"
        if reason:
            source_str = f"시뮬레이션 폴백 ({reason})"

        if not clean_route or clean_route in ["전체", "전체노선"]:
            # 정류소 번호나 명칭에 따른 맞춤형 가상 노선
            if "금옥" in bus_stop_name or bus_stop_id == "04158":
                route_candidates = ["421번", "2016번", "110A번"]
            else:
                route_candidates = ["146번", "360번", "740번"]

            buses = [
                {"route_name": route_candidates[0], "status": f"{rem_min}분 후 도착 ({rem_stops}번째 전)", "min": rem_min, "stops": rem_stops},
                {"route_name": route_candidates[1], "status": f"{rem_min + 3}분 후 도착 ({rem_stops + 1}번째 전)", "min": rem_min + 3, "stops": rem_stops + 1},
                {"route_name": route_candidates[2], "status": f"{next_min}분 후 도착 ({rem_stops + 3}번째 전)", "min": next_min, "stops": rem_stops + 3},
            ]
            status_lines = [f"• 🚍 **{b['route_name']}**: {b['status']}" for b in buses]
            status_str = "\n".join(status_lines)
            tip = cls.generate_commute_tip(rem_min, str(buses[0]["status"]))

            return {
                "is_live": False,
                "is_all_routes": True,
                "source": source_str,
                "stop_name": bus_stop_name or f"정류소({bus_stop_id or '기본'})",
                "stop_id": bus_stop_id,
                "route_name": "전체 노선",
                "status": status_str,
                "status_text": f"총 {len(buses)}개 노선 운행 중 (시뮬레이션)",
                "detail_text": f"가장 빠른 버스: {buses[0]['route_name']} ({buses[0]['status']})",
                "next_bus": f"{len(buses)}개 노선",
                "remaining_min": rem_min,
                "remaining_stops": rem_stops,
                "buses": buses,
                "raw_message": status_str,
                "tip": tip,
                "updated_time": now.strftime("%H:%M"),
            }

        status_str = f"{rem_min}분 후 도착 ({rem_stops}번째 전, 여유)"
        next_str = f"{next_min}분 후"
        tip = cls.generate_commute_tip(rem_min, status_str)

        return {
            "is_live": False,
            "is_all_routes": False,
            "source": source_str,
            "stop_name": bus_stop_name or "지정 정류소",
            "stop_id": bus_stop_id,
            "route_name": f"{clean_route}번",
            "status": status_str,
            "status_text": f"{rem_min}분 후 도착",
            "detail_text": f"{rem_stops}번째 전 정류소",
            "next_bus": next_str,
            "remaining_min": rem_min,
            "remaining_stops": rem_stops,
            "raw_message": status_str,
            "tip": tip,
            "updated_time": now.strftime("%H:%M"),
        }

    @classmethod
    def _is_valid_api_key(cls, key: str | None) -> bool:
        if not key:
            return False
        k = key.strip()
        if not k or "*" in k:
            return False
        # 플레이스홀더 키 체크
        if any(k.upper().startswith(p) for p in ["TEST_", "SECRET_", "KEY_", "DUMMY"]):
            return False
        return len(k) >= 10

    @classmethod
    def fetch_seoul_bus_arrival(
        cls,
        bus_stop_id: str,
        bus_route_name: str = "",
        api_key: str = "",
        bus_stop_name: str = "",
        timeout: float = 3.5,
    ) -> dict[str, Any] | None:
        """
        서울시 버스도착정보조회 서비스(TOPIS) getStationByUid API를 호출하여 도착 정보를 파싱합니다.
        노선 번호가 비어있으면 해당 정류소에 들어오는 모든 버스를 타임라인 순으로 반환합니다.
        """
        clean_route = cls.normalize_route_name(bus_route_name)
        ars_id = bus_stop_id.strip()
        unquoted_key = urllib.parse.unquote(api_key.strip())

        url = "http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid"
        params = {
            "serviceKey": unquoted_key,
            "arsId": ars_id,
            "resultType": "json",
        }

        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"Seoul Bus API HTTP error: {resp.status_code}")
                return None

            data = resp.json()
            msg_header = data.get("msgHeader", {})
            header_cd = str(msg_header.get("headerCd", ""))
            if header_cd != "0":
                header_msg = msg_header.get("headerMsg", "오류")
                logger.warning(f"Seoul Bus API returned error code {header_cd}: {header_msg}")
                return None

            items = data.get("msgBody", {}).get("itemList", [])
            if not items:
                logger.info(f"No bus arrival items found for ARS ID {ars_id}")
                return None

            st_nm = (items[0].get("stNm") if items else "") or bus_stop_name or f"정류소({ars_id})"

            if clean_route:
                target_item = None
                for it in items:
                    rt_nm = cls.normalize_route_name(str(it.get("rtNm", "")))
                    if rt_nm == clean_route:
                        target_item = it
                        break

                if not target_item:
                    logger.info(f"Route {clean_route} not found in ARS ID {ars_id} items")
                    return None

                st_nm = target_item.get("stNm") or st_nm
                arrmsg1 = target_item.get("arrmsg1", "")
                arrmsg2 = target_item.get("arrmsg2", "")

                parsed1 = cls.parse_arrmsg(arrmsg1)
                parsed2 = cls.parse_arrmsg(arrmsg2)
                now = get_now()
                tip = cls.generate_commute_tip(parsed1["min"], parsed1["text"])

                return {
                    "is_live": True,
                    "is_all_routes": False,
                    "source": "서울 TOPIS 실시간 API",
                    "stop_name": st_nm,
                    "stop_id": ars_id,
                    "route_name": f"{clean_route}번",
                    "status": parsed1["text"],
                    "status_text": f"{parsed1['min']}분 후 도착" if parsed1["min"] else parsed1["text"],
                    "detail_text": f"{parsed1['stops']}번째 전 정류소" if parsed1["stops"] else parsed1["text"],
                    "next_bus": parsed2["text"],
                    "remaining_min": parsed1["min"],
                    "remaining_stops": parsed1["stops"],
                    "raw_message": arrmsg1,
                    "tip": tip,
                    "updated_time": now.strftime("%H:%M"),
                }
            else:
                parsed_buses = []
                for it in items:
                    r_name = cls.normalize_route_name(str(it.get("rtNm", "")))
                    arrmsg1 = it.get("arrmsg1", "")
                    parsed = cls.parse_arrmsg(arrmsg1)
                    parsed_buses.append({
                        "route_name": f"{r_name}번",
                        "status": parsed["text"],
                        "min": parsed["min"],
                        "stops": parsed["stops"],
                    })

                parsed_buses.sort(key=lambda b: (b["min"] is None, b["min"] if b["min"] is not None else 999))
                lines = [f"• 🚍 **{b['route_name']}**: {b['status']}" for b in parsed_buses[:5]]
                status_text = "\n".join(lines) if lines else "도착 예정 버스 없음"
                top_bus = parsed_buses[0] if parsed_buses else None
                top_min = int(top_bus["min"]) if top_bus and top_bus.get("min") is not None else None
                top_status = str(top_bus["status"]) if top_bus and top_bus.get("status") else ""
                tip = cls.generate_commute_tip(top_min, top_status)
                now = get_now()

                return {
                    "is_live": True,
                    "is_all_routes": True,
                    "source": "서울 TOPIS 실시간 API",
                    "stop_name": st_nm,
                    "stop_id": ars_id,
                    "route_name": "전체 노선",
                    "status": status_text,
                    "status_text": f"총 {len(parsed_buses)}개 노선 도착 예정",
                    "detail_text": f"가장 빠른 버스: {top_bus['route_name']} ({top_bus['status']})" if top_bus else "",
                    "next_bus": f"{len(parsed_buses)}개 노선 운행 중",
                    "remaining_min": top_bus["min"] if top_bus else None,
                    "remaining_stops": top_bus["stops"] if top_bus else None,
                    "buses": parsed_buses[:5],
                    "raw_message": str(items[:3]),
                    "tip": tip,
                    "updated_time": now.strftime("%H:%M"),
                }

    @classmethod
    def fetch_tago_bus_arrival(
        cls,
        bus_stop_id: str,
        bus_route_name: str = "",
        city_code: str = "11",
        api_key: str = "",
        bus_stop_name: str = "",
        endpoint: str | None = None,
        timeout: float = 3.5,
    ) -> dict[str, Any] | None:
        """
        국토교통부(TAGO) 버스도착정보조회 서비스 API를 호출하여 도착 정보를 파싱합니다.
        노선 번호가 비어있으면 해당 정류소에 들어오는 모든 버스를 타임라인 순으로 반환합니다.
        """
        clean_route = cls.normalize_route_name(bus_route_name)
        node_id = bus_stop_id.strip()
        unquoted_key = urllib.parse.unquote(api_key.strip())

        base_url = endpoint.strip() if endpoint else "https://apis.data.go.kr/1613000/ArvlInfoInqireService"
        if not base_url.endswith("getSttnAcctoArvlPrearngeInfoList"):
            url = f"{base_url.rstrip('/')}/getSttnAcctoArvlPrearngeInfoList"
        else:
            url = base_url

        params: dict[str, str] = {
            "serviceKey": unquoted_key,
            "cityCode": city_code,
            "nodeId": node_id,
            "numOfRows": "100",
            "_type": "json",
        }

        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"TAGO Bus API HTTP error: {resp.status_code}")
                return None

            data = resp.json()
            body = data.get("response", {}).get("body", {})
            items_container = body.get("items")
            if not isinstance(items_container, dict):
                logger.info(f"No bus arrival items found in TAGO for stop {node_id}")
                return None

            items_obj = items_container.get("item", [])
            items = items_obj if isinstance(items_obj, list) else ([items_obj] if items_obj else [])

            st_nm = (items[0].get("nodenm") if items else "") or bus_stop_name or f"정류소({node_id})"

            if clean_route:
                target_item = None
                for it in items:
                    r_no = cls.normalize_route_name(str(it.get("routeno", "")))
                    if r_no == clean_route:
                        target_item = it
                        break

                if not target_item:
                    return None

                arr_time_sec = target_item.get("arrtime")
                rem_stops = target_item.get("arrprevstationcnt")
                st_nm = target_item.get("nodenm") or st_nm

                rem_min = (int(arr_time_sec) // 60) if arr_time_sec is not None else None
                status_text = f"{rem_min}분 후 도착 ({rem_stops}번째 전)" if rem_min is not None else "도착 정보 대기"
                tip = cls.generate_commute_tip(rem_min, status_text)
                now = get_now()

                return {
                    "is_live": True,
                    "is_all_routes": False,
                    "source": "국토교통부 TAGO 실시간 API",
                    "stop_name": st_nm,
                    "stop_id": node_id,
                    "route_name": f"{clean_route}번",
                    "status": status_text,
                    "status_text": f"{rem_min}분 후 도착" if rem_min is not None else status_text,
                    "detail_text": f"{rem_stops}번째 전 정류소" if rem_stops else "",
                    "next_bus": "다음 버스 정보 확인 중",
                    "remaining_min": rem_min,
                    "remaining_stops": rem_stops,
                    "raw_message": str(target_item),
                    "tip": tip,
                    "updated_time": now.strftime("%H:%M"),
                }
            else:
                parsed_buses = []
                for it in items:
                    r_no = cls.normalize_route_name(str(it.get("routeno", "")))
                    arr_time_sec = it.get("arrtime")
                    rem_stops = it.get("arrprevstationcnt")
                    rem_min = (int(arr_time_sec) // 60) if arr_time_sec is not None else None
                    status_str = f"{rem_min}분 후 도착 ({rem_stops}번째 전)" if rem_min is not None else "도착 정보 대기"
                    parsed_buses.append({
                        "route_name": f"{r_no}번",
                        "status": status_str,
                        "min": rem_min,
                        "stops": rem_stops,
                    })

                parsed_buses.sort(key=lambda b: (b["min"] is None, b["min"] if b["min"] is not None else 999))
                lines = [f"• 🚍 **{b['route_name']}**: {b['status']}" for b in parsed_buses[:5]]
                status_text = "\n".join(lines) if lines else "도착 예정 버스 없음"
                top_bus = parsed_buses[0] if parsed_buses else None
                top_min = int(top_bus["min"]) if top_bus and top_bus.get("min") is not None else None
                top_status = str(top_bus["status"]) if top_bus and top_bus.get("status") else ""
                tip = cls.generate_commute_tip(top_min, top_status)
                now = get_now()

                return {
                    "is_live": True,
                    "is_all_routes": True,
                    "source": "국토교통부 TAGO 실시간 API",
                    "stop_name": st_nm,
                    "stop_id": node_id,
                    "route_name": "전체 노선",
                    "status": status_text,
                    "status_text": f"총 {len(parsed_buses)}개 노선 도착 예정",
                    "detail_text": f"가장 빠른 버스: {top_bus['route_name']} ({top_bus['status']})" if top_bus else "",
                    "next_bus": f"{len(parsed_buses)}개 노선 운행 중",
                    "remaining_min": top_bus["min"] if top_bus else None,
                    "remaining_stops": top_bus["stops"] if top_bus else None,
                    "buses": parsed_buses[:5],
                    "raw_message": str(items[:3]),
                    "tip": tip,
                    "updated_time": now.strftime("%H:%M"),
                }

    @classmethod
    def get_arrival_info(
        cls,
        bus_stop_id: str,
        bus_route_name: str = "",
        api_key: str | None = None,
        city_code: str = "11",
        use_mock_fallback: bool = True,
        bus_stop_name: str = "",
        endpoint: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        출근 버스 도착 정보를 캐시 및 실시간 API(또는 폴백)를 통해 반환합니다.
        노선 번호가 비어있거나 '전체'일 경우 정류소 전체 도착 버스를 반환합니다.
        force_refresh=True인 경우 캐시를 우회하고 최신 도착 정보를 강제 조회합니다 (ADR-039).
        """
        clean_route = cls.normalize_route_name(bus_route_name) if bus_route_name else ""
        stop_id = bus_stop_id.strip()

        # 정류소명이 비어있거나 기본 플레이스홀더일 경우 정류소 번호로 자동 역조회
        if stop_id and (not bus_stop_name or bus_stop_name in ["지정 정류장", "정류장"]):
            resolved_info = cls.resolve_bus_stop(stop_id, city_code, api_key, endpoint)
            if resolved_info.get("stop_name") and not str(resolved_info["stop_name"]).startswith("정류소("):
                bus_stop_name = str(resolved_info["stop_name"])

        # 1. 인메모리 캐시 확인 (45초 TTL) - force_refresh가 아닐 때만 적용
        cache_key = f"{city_code}:{stop_id}:{clean_route}"
        if not force_refresh:
            cached_entry = cls._cache.get(cache_key)
            if cached_entry:
                ts, cached_data = cached_entry
                if time.time() - ts < cls.CACHE_TTL:
                    return cached_data

        # 2. 실시간 API 시도 (정류소 번호가 있으면 노선 번호 없어도 조회 가능)
        if cls._is_valid_api_key(api_key) and stop_id:
            try:
                result = None
                prefer_tago = bool(endpoint and "ArvlInfoInqireService" in endpoint) or (city_code != "11")

                if prefer_tago:
                    result = cls.fetch_tago_bus_arrival(
                        bus_stop_id=stop_id,
                        bus_route_name=clean_route,
                        city_code=city_code,
                        api_key=api_key or "",
                        bus_stop_name=bus_stop_name,
                        endpoint=endpoint,
                    )
                    if not result:
                        result = cls.fetch_seoul_bus_arrival(
                            bus_stop_id=stop_id,
                            bus_route_name=clean_route,
                            api_key=api_key or "",
                            bus_stop_name=bus_stop_name,
                        )
                else:
                    result = cls.fetch_seoul_bus_arrival(
                        bus_stop_id=stop_id,
                        bus_route_name=clean_route,
                        api_key=api_key or "",
                        bus_stop_name=bus_stop_name,
                    )
                    if not result:
                        result = cls.fetch_tago_bus_arrival(
                            bus_stop_id=stop_id,
                            bus_route_name=clean_route,
                            city_code=city_code,
                            api_key=api_key or "",
                            bus_stop_name=bus_stop_name,
                            endpoint=endpoint,
                        )

                if result:
                    cls._cache[cache_key] = (time.time(), result)
                    return result

            except Exception as e:
                logger.warning(f"Failed to fetch live bus arrival: {e}")
                if not use_mock_fallback:
                    raise

        # 3. API 키 미설정 또는 실패 시 스마트 시뮬레이션 폴백
        mock_result = cls.get_smart_mock_arrival(
            bus_route_name=clean_route or bus_route_name,
            bus_stop_name=bus_stop_name,
            bus_stop_id=stop_id,
        )
        cls._cache[cache_key] = (time.time(), mock_result)
        return mock_result
