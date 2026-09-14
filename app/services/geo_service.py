"""
한국 행정구역 기반 스마트 지오코딩 및 기상청 격자/에어코리아 측정소 매핑 서비스 (ADR-034).
사용자가 입력한 자연어 동네명(예: "성동구 금호동", "판교", "마포구 상암동")을 분석하여
정규화된 지역명, 기상청 단기예보 격자 좌표(grid_x, grid_y), 대기질 측정소명(air_station_name),
도시코드(city_code)를 0.001초 내에 결정론적으로 매핑합니다.
"""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar

logger = logging.getLogger("watson.geo_service")


class GeoService:
    """한국 주요 시/도/구/동 스마트 지오코딩 엔진"""

    # 서울 25개 자치구 표준 격자 및 대기 측정소
    SEOUL_DISTRICTS: ClassVar[dict[str, dict[str, Any]]] = {
        "강남구": {"grid_x": 61, "grid_y": 125, "station": "강남구", "city_code": "11"},
        "강동구": {"grid_x": 62, "grid_y": 126, "station": "강동구", "city_code": "11"},
        "강북구": {"grid_x": 61, "grid_y": 128, "station": "강북구", "city_code": "11"},
        "강서구": {"grid_x": 58, "grid_y": 126, "station": "강서구", "city_code": "11"},
        "관악구": {"grid_x": 59, "grid_y": 125, "station": "관악구", "city_code": "11"},
        "광진구": {"grid_x": 62, "grid_y": 126, "station": "광진구", "city_code": "11"},
        "구로구": {"grid_x": 58, "grid_y": 125, "station": "구로구", "city_code": "11"},
        "금천구": {"grid_x": 59, "grid_y": 124, "station": "금천구", "city_code": "11"},
        "노원구": {"grid_x": 61, "grid_y": 129, "station": "노원구", "city_code": "11"},
        "도봉구": {"grid_x": 61, "grid_y": 129, "station": "도봉구", "city_code": "11"},
        "동대문구": {"grid_x": 61, "grid_y": 127, "station": "동대문구", "city_code": "11"},
        "동작구": {"grid_x": 59, "grid_y": 125, "station": "동작구", "city_code": "11"},
        "마포구": {"grid_x": 59, "grid_y": 127, "station": "마포구", "city_code": "11"},
        "서대문구": {"grid_x": 59, "grid_y": 127, "station": "서대문구", "city_code": "11"},
        "서초구": {"grid_x": 61, "grid_y": 125, "station": "서초구", "city_code": "11"},
        "성동구": {"grid_x": 61, "grid_y": 127, "station": "성동구", "city_code": "11"},
        "성북구": {"grid_x": 61, "grid_y": 127, "station": "성북구", "city_code": "11"},
        "송파구": {"grid_x": 62, "grid_y": 126, "station": "송파구", "city_code": "11"},
        "양천구": {"grid_x": 58, "grid_y": 126, "station": "양천구", "city_code": "11"},
        "영등포구": {"grid_x": 58, "grid_y": 126, "station": "영등포구", "city_code": "11"},
        "용산구": {"grid_x": 60, "grid_y": 126, "station": "용산구", "city_code": "11"},
        "은평구": {"grid_x": 59, "grid_y": 127, "station": "은평구", "city_code": "11"},
        "종로구": {"grid_x": 60, "grid_y": 127, "station": "종로구", "city_code": "11"},
        "중구": {"grid_x": 60, "grid_y": 127, "station": "중구", "city_code": "11"},
        "중랑구": {"grid_x": 62, "grid_y": 128, "station": "중랑구", "city_code": "11"},
    }

    # 서울 주요 동 -> 자치구 매핑 (빈출 지역명)
    SEOUL_DONGS: ClassVar[dict[str, str]] = {
        # 성동구
        "금호동": "성동구", "금호": "성동구", "옥수동": "성동구", "옥수": "성동구",
        "성수동": "성동구", "성수": "성동구", "행당동": "성동구", "행당": "성동구",
        "왕십리": "성동구", "왕십리동": "성동구", "마장동": "성동구", "응봉동": "성동구",
        "송정동": "성동구", "용답동": "성동구", "사근동": "성동구",
        # 강남구
        "역삼동": "강남구", "역삼": "강남구", "개포동": "강남구", "청담동": "강남구",
        "삼성동": "강남구", "대치동": "강남구", "신사동": "강남구", "논현동": "강남구",
        "압구정": "강남구", "압구정동": "강남구", "수서동": "강남구", "도곡동": "강남구",
        "일원동": "강남구", "자곡동": "강남구", "세곡동": "강남구",
        # 서초구
        "반포동": "서초구", "반포": "서초구", "방배동": "서초구", "방배": "서초구",
        "양재동": "서초구", "양재": "서초구", "서초동": "서초구", "잠원동": "서초구",
        # 송파구
        "잠실": "송파구", "잠실동": "송파구", "신천동": "송파구", "문정동": "송파구",
        "가락동": "송파구", "방이동": "송파구", "오금동": "송파구", "석촌동": "송파구",
        "삼전동": "송파구", "거여동": "송파구", "마천동": "송파구", "장지동": "송파구",
        # 마포구
        "상암동": "마포구", "상암": "마포구", "공덕동": "마포구", "공덕": "마포구",
        "합정동": "마포구", "합정": "마포구", "망원동": "마포구", "연남동": "마포구",
        "서교동": "마포구", "홍대": "마포구", "동교동": "마포구", "아현동": "마포구",
        # 용산구
        "한남동": "용산구", "한남": "용산구", "이태원": "용산구", "이태원동": "용산구",
        "이촌동": "용산구", "동부이촌동": "용산구", "용산동": "용산구", "후암동": "용산구",
        # 영등포구
        "여의도": "영등포구", "여의도동": "영등포구", "문래동": "영등포구", "당산동": "영등포구",
        "신길동": "영등포구", "대림동": "영등포구",
        # 양천구
        "목동": "양천구", "신정동": "양천구", "신월동": "양천구",
        # 종로구 / 중구
        "광화문": "종로구", "혜화동": "종로구", "대학로": "종로구", "명동": "중구",
        "을지로": "중구", "신당동": "중구", "약수동": "중구",
        # 관악구 / 동작구
        "신림동": "관악구", "신림": "관악구", "봉천동": "관악구", "낙성대": "관악구",
        "사당동": "동작구", "사당": "동작구", "노량진": "동작구", "흑석동": "동작구",
        # 광진구 / 동대문구
        "자양동": "광진구", "구의동": "광진구", "건대": "광진구", "장안동": "동대문구",
        "청량리": "동대문구", "답십리": "동대문구",
        # 서대문구 / 은평구
        "신촌": "서대문구", "연희동": "서대문구", "홍제동": "서대문구", "불광동": "은평구",
        "응암동": "은평구", "연신내": "은평구",
        # 노원구 / 도봉구 / 강북구
        "상계동": "노원구", "중계동": "노원구", "하계동": "노원구", "공릉동": "노원구",
        "창동": "도봉구", "쌍문동": "도봉구", "수유동": "강북구", "미아동": "강북구",
    }

    # 경기/인천 및 전국 주요 도시 격자 & 측정소
    MAJOR_REGIONS: ClassVar[dict[str, dict[str, Any]]] = {
        # 성남시
        "분당구": {"full_name": "경기도 성남시 분당구", "grid_x": 62, "grid_y": 123, "station": "분당구", "city_code": "31"},
        "판교": {"full_name": "경기도 성남시 분당구 판교동", "grid_x": 62, "grid_y": 123, "station": "분당구", "city_code": "31"},
        "판교동": {"full_name": "경기도 성남시 분당구 판교동", "grid_x": 62, "grid_y": 123, "station": "분당구", "city_code": "31"},
        "백현동": {"full_name": "경기도 성남시 분당구 백현동", "grid_x": 62, "grid_y": 123, "station": "분당구", "city_code": "31"},
        "정자동": {"full_name": "경기도 성남시 분당구 정자동", "grid_x": 62, "grid_y": 123, "station": "분당구", "city_code": "31"},
        "서현동": {"full_name": "경기도 성남시 분당구 서현동", "grid_x": 62, "grid_y": 123, "station": "분당구", "city_code": "31"},
        "야탑동": {"full_name": "경기도 성남시 분당구 야탑동", "grid_x": 62, "grid_y": 123, "station": "분당구", "city_code": "31"},
        "수정구": {"full_name": "경기도 성남시 수정구", "grid_x": 63, "grid_y": 124, "station": "수정구", "city_code": "31"},
        "중원구": {"full_name": "경기도 성남시 중원구", "grid_x": 63, "grid_y": 124, "station": "중원구", "city_code": "31"},
        "성남시": {"full_name": "경기도 성남시", "grid_x": 63, "grid_y": 124, "station": "수정구", "city_code": "31"},
        "위례": {"full_name": "성남시 위례", "grid_x": 63, "grid_y": 124, "station": "수정구", "city_code": "31"},
        # 수원시
        "영통구": {"full_name": "경기도 수원시 영통구", "grid_x": 61, "grid_y": 120, "station": "영통구", "city_code": "31"},
        "광교": {"full_name": "경기도 수원시 영통구 광교동", "grid_x": 61, "grid_y": 120, "station": "영통구", "city_code": "31"},
        "광교동": {"full_name": "경기도 수원시 영통구 광교동", "grid_x": 61, "grid_y": 120, "station": "영통구", "city_code": "31"},
        "팔달구": {"full_name": "경기도 수원시 팔달구", "grid_x": 60, "grid_y": 120, "station": "팔달구", "city_code": "31"},
        "장안구": {"full_name": "경기도 수원시 장안구", "grid_x": 60, "grid_y": 121, "station": "장안구", "city_code": "31"},
        "권선구": {"full_name": "경기도 수원시 권선구", "grid_x": 60, "grid_y": 119, "station": "권선구", "city_code": "31"},
        "수원시": {"full_name": "경기도 수원시", "grid_x": 60, "grid_y": 120, "station": "팔달구", "city_code": "31"},
        # 용인시
        "수지구": {"full_name": "경기도 용인시 수지구", "grid_x": 62, "grid_y": 121, "station": "수지구", "city_code": "31"},
        "기흥구": {"full_name": "경기도 용인시 기흥구", "grid_x": 62, "grid_y": 119, "station": "기흥구", "city_code": "31"},
        "처인구": {"full_name": "경기도 용인시 처인구", "grid_x": 64, "grid_y": 119, "station": "처인구", "city_code": "31"},
        "동백": {"full_name": "경기도 용인시 기흥구 동백동", "grid_x": 62, "grid_y": 119, "station": "기흥구", "city_code": "31"},
        "용인시": {"full_name": "경기도 용인시", "grid_x": 62, "grid_y": 120, "station": "수지구", "city_code": "31"},
        # 고양시
        "일산동구": {"full_name": "경기도 고양시 일산동구", "grid_x": 56, "grid_y": 129, "station": "일산동구", "city_code": "31"},
        "일산서구": {"full_name": "경기도 고양시 일산서구", "grid_x": 56, "grid_y": 129, "station": "일산서구", "city_code": "31"},
        "일산": {"full_name": "경기도 고양시 일산", "grid_x": 56, "grid_y": 129, "station": "일산동구", "city_code": "31"},
        "덕양구": {"full_name": "경기도 고양시 덕양구", "grid_x": 57, "grid_y": 128, "station": "덕양구", "city_code": "31"},
        "화정": {"full_name": "경기도 고양시 덕양구 화정동", "grid_x": 57, "grid_y": 128, "station": "덕양구", "city_code": "31"},
        "삼송": {"full_name": "경기도 고양시 덕양구 삼송동", "grid_x": 57, "grid_y": 128, "station": "덕양구", "city_code": "31"},
        "고양시": {"full_name": "경기도 고양시", "grid_x": 57, "grid_y": 128, "station": "덕양구", "city_code": "31"},
        # 안양시
        "동안구": {"full_name": "경기도 안양시 동안구", "grid_x": 59, "grid_y": 123, "station": "동안구", "city_code": "31"},
        "평촌": {"full_name": "경기도 안양시 동안구 평촌동", "grid_x": 59, "grid_y": 123, "station": "동안구", "city_code": "31"},
        "만안구": {"full_name": "경기도 안양시 만안구", "grid_x": 59, "grid_y": 123, "station": "만안구", "city_code": "31"},
        "안양시": {"full_name": "경기도 안양시", "grid_x": 59, "grid_y": 123, "station": "동안구", "city_code": "31"},
        # 화성시 / 평택시
        "동탄": {"full_name": "경기도 화성시 동탄", "grid_x": 60, "grid_y": 118, "station": "동탄", "city_code": "31"},
        "화성시": {"full_name": "경기도 화성시", "grid_x": 57, "grid_y": 119, "station": "화성", "city_code": "31"},
        "평택시": {"full_name": "경기도 평택시", "grid_x": 62, "grid_y": 114, "station": "평택", "city_code": "31"},
        "고덕": {"full_name": "경기도 평택시 고덕", "grid_x": 62, "grid_y": 114, "station": "평택", "city_code": "31"},
        # 기타 경기
        "부천시": {"full_name": "경기도 부천시", "grid_x": 57, "grid_y": 125, "station": "부천", "city_code": "31"},
        "하남시": {"full_name": "경기도 하남시", "grid_x": 64, "grid_y": 126, "station": "하남", "city_code": "31"},
        "미사": {"full_name": "경기도 하남시 미사", "grid_x": 64, "grid_y": 126, "station": "하남", "city_code": "31"},
        "과천시": {"full_name": "경기도 과천시", "grid_x": 60, "grid_y": 124, "station": "과천", "city_code": "31"},
        "광명시": {"full_name": "경기도 광명시", "grid_x": 58, "grid_y": 125, "station": "광명", "city_code": "31"},
        "군포시": {"full_name": "경기도 군포시", "grid_x": 59, "grid_y": 122, "station": "군포", "city_code": "31"},
        "산본": {"full_name": "경기도 군포시 산본동", "grid_x": 59, "grid_y": 122, "station": "군포", "city_code": "31"},
        "의왕시": {"full_name": "경기도 의왕시", "grid_x": 60, "grid_y": 122, "station": "의왕", "city_code": "31"},
        "남양주시": {"full_name": "경기도 남양주시", "grid_x": 64, "grid_y": 128, "station": "남양주", "city_code": "31"},
        "다산": {"full_name": "경기도 남양주시 다산동", "grid_x": 64, "grid_y": 128, "station": "남양주", "city_code": "31"},
        "구리시": {"full_name": "경기도 구리시", "grid_x": 62, "grid_y": 127, "station": "구리", "city_code": "31"},
        "김포시": {"full_name": "경기도 김포시", "grid_x": 55, "grid_y": 128, "station": "김포", "city_code": "31"},
        "파주시": {"full_name": "경기도 파주시", "grid_x": 56, "grid_y": 131, "station": "파주", "city_code": "31"},
        "운정": {"full_name": "경기도 파주시 운정", "grid_x": 56, "grid_y": 131, "station": "파주", "city_code": "31"},
        # 인천광역시
        "인천": {"full_name": "인천광역시", "grid_x": 55, "grid_y": 124, "station": "남동구", "city_code": "28"},
        "송도": {"full_name": "인천광역시 연수구 송도동", "grid_x": 55, "grid_y": 124, "station": "송도", "city_code": "28"},
        "청라": {"full_name": "인천광역시 서구 청라동", "grid_x": 55, "grid_y": 126, "station": "청라", "city_code": "28"},
        "부평": {"full_name": "인천광역시 부평구", "grid_x": 55, "grid_y": 126, "station": "부평구", "city_code": "28"},
        # 광역시 및 전국
        "부산": {"full_name": "부산광역시 해운대구", "grid_x": 99, "grid_y": 75, "station": "해운대구", "city_code": "26"},
        "해운대": {"full_name": "부산광역시 해운대구", "grid_x": 99, "grid_y": 75, "station": "해운대구", "city_code": "26"},
        "대구": {"full_name": "대구광역시 수성구", "grid_x": 89, "grid_y": 90, "station": "수성구", "city_code": "27"},
        "대전": {"full_name": "대전광역시 유성구", "grid_x": 67, "grid_y": 100, "station": "유성구", "city_code": "30"},
        "광주": {"full_name": "광주광역시 서구", "grid_x": 59, "grid_y": 74, "station": "서구", "city_code": "29"},
        "울산": {"full_name": "울산광역시 남구", "grid_x": 102, "grid_y": 84, "station": "남구", "city_code": "31"},
        "세종": {"full_name": "세종특별자치시", "grid_x": 66, "grid_y": 103, "station": "세종", "city_code": "36"},
        "제주": {"full_name": "제주특별자치도 제주시", "grid_x": 52, "grid_y": 38, "station": "제주", "city_code": "39"},
    }

    @classmethod
    def resolve_location(cls, query: str) -> dict[str, Any]:
        """
        사용자 입력 문자열(예: '성동구 금호동', '금호동', '판교', '서울 마포구 상암동')로부터
        정규화된 동네명, 격자좌표(grid_x, grid_y), 측정소명(station), 도시코드(city_code)를 추론합니다.
        """
        raw_text = query.strip()
        # 불필요한 조사/수식어 제거 (예: "우리 동네는", "성동구 금호동인데", "으로 설정해줘")
        cleaned = re.sub(r"^(우리\s*동네는?|동네는?|동네\s*설정|위치는?|지역은?)\s*", "", raw_text)
        cleaned = re.sub(r"(으로|로|인데|으로\s*설정해줘?|으로\s*바꿔줘?|설정해줘?|바꿔줘?|\?|\!|\.|\,)*$", "", cleaned).strip()

        if not cleaned:
            cleaned = raw_text

        # 1. 서울 자치구 직접 명시 확인 (예: "성동구 금호동", "서울 성동구")
        for gu, gu_info in cls.SEOUL_DISTRICTS.items():
            if gu in cleaned:
                # 구 명칭 이후 텍스트에서 동 검색 (예: "성동구 금호동" -> "금호동")
                after_gu = cleaned.split(gu, 1)[1].strip()
                dong_match = re.search(r"([가-힣]{1,4}[동가읍면리\d]+)", after_gu)
                dong_name = dong_match.group(1) if dong_match else ""

                if not dong_name:
                    cleaned_without_gu = cleaned.replace(gu, "").strip()
                    dong_match2 = re.search(r"([가-힣]{1,4}[동가읍면리\d]+)", cleaned_without_gu)
                    dong_name = dong_match2.group(1) if dong_match2 else ""

                if dong_name and not dong_name.endswith("구"):
                    full_name = f"서울 {gu} {dong_name}"
                else:
                    full_name = f"서울 {gu}"

                return {
                    "matched": True,
                    "location_name": full_name,
                    "grid_x": gu_info["grid_x"],
                    "grid_y": gu_info["grid_y"],
                    "air_station_name": gu_info["station"],
                    "city_code": gu_info["city_code"],
                    "source": "seoul_district",
                }

        # 1-1. 경기/인천/광역시 등의 구체적인 동/읍/면 우선 검사 (예: "판교동", "광교동", "정자동")
        dong_cand = re.findall(r"([가-힣]{1,4}[동가읍면리])", cleaned)
        for dc in dong_cand:
            if dc in cls.MAJOR_REGIONS:
                reg = cls.MAJOR_REGIONS[dc]
                return {
                    "matched": True,
                    "location_name": reg["full_name"],
                    "grid_x": reg["grid_x"],
                    "grid_y": reg["grid_y"],
                    "air_station_name": reg["station"],
                    "city_code": reg["city_code"],
                    "source": "major_dong",
                }

        # 2. 서울 주요 동 이름 단독/복합 검색 (더 구체적이고 긴 동명 우선 매칭)
        for dong, gu in sorted(cls.SEOUL_DONGS.items(), key=lambda x: len(x[0]), reverse=True):
            if dong in cleaned:
                gu_info = cls.SEOUL_DISTRICTS[gu]
                exact_dong = dong if dong.endswith("동") else f"{dong}동"
                return {
                    "matched": True,
                    "location_name": f"서울 {gu} {exact_dong}",
                    "grid_x": gu_info["grid_x"],
                    "grid_y": gu_info["grid_y"],
                    "air_station_name": gu_info["station"],
                    "city_code": gu_info["city_code"],
                    "source": "seoul_dong",
                }

        # 3. 경기/인천 및 전국 주요 지역 검색 (더 구체적이고 긴 지명 우선 매칭)
        for reg_key, reg_info in sorted(cls.MAJOR_REGIONS.items(), key=lambda x: len(x[0]), reverse=True):
            if reg_key in cleaned:
                return {
                    "matched": True,
                    "location_name": reg_info["full_name"],
                    "grid_x": reg_info["grid_x"],
                    "grid_y": reg_info["grid_y"],
                    "air_station_name": reg_info["station"],
                    "city_code": reg_info["city_code"],
                    "source": "major_region",
                }

        # 4. 일치하지 않는 경우: 일반 텍스트 보존 및 서울 중심부 기본값(또는 이전값 보존)으로 스마트 폴백
        logger.warning(f"Could not auto-resolve location for '{query}', falling back to general representation")
        return {
            "matched": False,
            "location_name": cleaned or raw_text,
            "grid_x": 60,
            "grid_y": 127,  # 서울 종로/중구 기본 좌표
            "air_station_name": "중구",
            "city_code": "11",
            "source": "fallback",
        }
