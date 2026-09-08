from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


class GTDPathRequest(BaseModel):
    path: str = Field(..., description="Absolute or relative path to the GTD repository/directory")
    create_if_missing: bool = Field(True, description="Automatically create directory if not found")


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
