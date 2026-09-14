from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import verify_web_auth
from app.services.commute_config_service import CommuteConfigService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(verify_web_auth)])


class GTDPathRequest(BaseModel):
    path: str = Field(..., description="Absolute or relative path to the GTD repository/directory")
    create_if_missing: bool = Field(True, description="Automatically create directory if not found")


class CommuteConfigRequest(BaseModel):
    enabled: bool = Field(True, description="출근길 모닝 브리핑 활성화 여부")
    send_time: str = Field("07:30", description="정기 발송 시각 (HH:MM 형식)")
    weekdays_only: bool = Field(True, description="평일(월~금)만 발송 여부")
    location_name: str = Field("서울 강남구 역삼동", description="거주지/동네 명칭")
    grid_x: int = Field(61, description="기상청 격자 X 좌표")
    grid_y: int = Field(125, description="기상청 격자 Y 좌표")
    air_station_name: str = Field("강남구", description="에어코리아 대기 측정소명")
    bus_stop_name: str = Field("역삼역", description="출근 버스 탑승 정류소명")
    bus_stop_id: str = Field("23284", description="정류소 번호 / ARS-ID / node_id")
    bus_route_name: str = Field("146", description="탑승 버스 노선 번호")
    bus_route_id: str = Field("", description="버스 노선 고유 ID")
    city_code: str = Field("11", description="도시 코드 (서울: 11, 경기: 31 등)")
    public_data_api_key: str = Field("", description="공공데이터포털 일반 인증키")
    use_mock_fallback: bool = Field(True, description="API 키 미설정/장애 시 스마트 시뮬레이션 모드 허용")


class CommutePreviewRequest(BaseModel):
    config: CommuteConfigRequest | None = Field(None, description="임시 테스트할 출근 설정 (생략 시 저장된 설정 사용)")


@router.get("/gtd-path")
def get_gtd_path_status() -> dict[str, Any]:
    """
    현재 설정된 GTD 작업 디렉토리 경로, Git 레포지토리 여부 및 구조 정보를 반환합니다 (ADR-007).
    """
    service = SettingsService()
    return service.get_status()


@router.post("/gtd-path")
def update_gtd_path(payload: GTDPathRequest) -> dict[str, Any]:
    """
    GTD 작업 디렉토리 경로를 동적으로 변경 및 영속화합니다.
    디렉토리 유효성 및 쓰기 권한을 검증합니다.
    """
    service = SettingsService()
    try:
        updated_status = service.set_gtd_path(
            new_path=payload.path,
            create_if_missing=payload.create_if_missing,
        )
        return {
            "success": True,
            "message": "GTD directory path updated successfully",
            "data": updated_status,
        }
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# ==============================================================================
# Commute & Weather Briefing Settings Endpoints (ADR-030)
# ==============================================================================


@router.get("/commute")
def get_commute_settings() -> dict[str, Any]:
    """
    현재 저장된 출근길 모닝 브리핑(동네 날씨, 미세먼지, 버스 정보) 설정을 반환합니다 (API 키 마스킹 포함).
    """
    service = CommuteConfigService()
    return {
        "success": True,
        "data": service.get_masked_config(),
    }


@router.post("/commute")
def update_commute_settings(payload: CommuteConfigRequest) -> dict[str, Any]:
    """
    출근길 모닝 브리핑 설정을 유효성 검사 후 영속화합니다.
    """
    service = CommuteConfigService()
    try:
        saved = service.save_config(payload.model_dump())
        return {
            "success": True,
            "message": "출근길 모닝 브리핑 설정이 안전하게 저장되었습니다.",
            "data": saved,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"출근길 설정 저장 중 오류: {e}")


@router.post("/commute/preview")
def preview_commute_card(payload: CommutePreviewRequest | None = None) -> dict[str, Any]:
    """
    현재 설정 또는 클라이언트가 전달한 임시 설정을 바탕으로 출근길 모닝 브리핑 카드를 실시간 렌더링 미리보기합니다.
    """
    service = CommuteConfigService()
    custom = payload.config.model_dump() if (payload and payload.config) else None
    result = service.generate_preview(custom_config=custom)
    return result


class ResolveLocationRequest(BaseModel):
    query: str = Field(..., description="사용자가 입력한 동네/지역 검색어")


@router.post("/commute/resolve-location")
def resolve_commute_location(payload: ResolveLocationRequest) -> dict[str, Any]:
    """
    동네 검색어를 스마트 지오코딩하여 격자 좌표와 대기 측정소를 반환합니다 (ADR-034).
    """
    from app.services.geo_service import GeoService

    resolved = GeoService.resolve_location(payload.query)
    return {
        "success": True,
        "data": resolved,
    }
