import json
import logging
import os
from typing import Any

from app.config import get_now, settings

logger = logging.getLogger("watson.settings")


class SettingsService:
    """
    GTD 작업 디렉토리 및 시스템 동적 설정 관리자 (ADR-007).
    웹 UI 및 API를 통해 동적으로 GTD 경로를 변경하고 영속화합니다.
    """

    def __init__(self, config_file: str = "config/gtd_config.json"):
        self.config_file = config_file

    def get_gtd_path(self) -> str:
        """
        우선순위에 따라 현재 활성화된 GTD 저장소 경로를 반환합니다.
        1. config/gtd_config.json
        2. settings.GTD_PATH (.env)
        3. settings.REPO_PATH (기본값 '.')
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    path = data.get("gtd_path")
                    if path and os.path.exists(os.path.abspath(os.path.expanduser(path))):
                        return os.path.abspath(os.path.expanduser(path))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read gtd_config.json: {e}")

        if settings.GTD_PATH and settings.GTD_PATH.strip():
            expanded = os.path.abspath(os.path.expanduser(settings.GTD_PATH.strip()))
            if os.path.exists(expanded):
                return expanded

        # Fallback to REPO_PATH for backward compatibility
        return os.path.abspath(os.path.expanduser(settings.REPO_PATH))

    def get_status(self) -> dict[str, Any]:
        """현재 GTD 디렉토리의 유효성, Git 저장소 여부 및 파일 구조 상태를 반환합니다."""
        path = self.get_gtd_path()
        exists = os.path.exists(path)
        is_git_repo = os.path.exists(os.path.join(path, ".git")) if exists else False

        # Detect GTD structure
        has_gtd_folder = os.path.exists(os.path.join(path, "gtd")) if exists else False
        has_inbox = (
            os.path.exists(os.path.join(path, "gtd", "inbox.md"))
            or os.path.exists(os.path.join(path, "inbox.md"))
            if exists
            else False
        )
        has_daily_logs = (
            os.path.exists(os.path.join(path, "logs", "daily"))
            or os.path.exists(os.path.join(path, "lifelogs"))
            if exists
            else False
        )

        structure_type = "default"
        if has_gtd_folder or has_inbox:
            structure_type = "gtd_custom"
        elif has_daily_logs:
            structure_type = "daily_lifelog"

        # Check if it's external or same as bot repo
        bot_repo_path = os.path.abspath(os.path.expanduser(settings.REPO_PATH))
        is_external = os.path.normpath(path) != os.path.normpath(bot_repo_path)

        return {
            "gtd_path": path,
            "exists": exists,
            "is_external": is_external,
            "is_git_repo": is_git_repo,
            "has_gtd_folder": has_gtd_folder,
            "has_inbox": has_inbox,
            "has_daily_logs": has_daily_logs,
            "structure_type": structure_type,
            "timezone": settings.TIMEZONE,
        }

    def set_gtd_path(self, new_path: str, create_if_missing: bool = True) -> dict[str, Any]:
        """
        새로운 GTD 작업 디렉토리를 지정하고 영속화합니다.
        """
        if not new_path or not new_path.strip():
            raise ValueError("GTD path cannot be empty")

        resolved_path = os.path.abspath(os.path.expanduser(new_path.strip()))

        if not os.path.exists(resolved_path):
            if create_if_missing:
                os.makedirs(resolved_path, exist_ok=True)
            else:
                raise ValueError(f"Directory does not exist: {resolved_path}")

        # Check directory writability
        test_file = os.path.join(resolved_path, ".watson_perm_test")
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("test")
            os.remove(test_file)
        except OSError as e:
            raise PermissionError(f"Directory is not writable: {e}") from e

        # Persist to config_file
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        config_data = {
            "gtd_path": resolved_path,
            "updated_at": get_now().isoformat(),
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Updated GTD directory path to: {resolved_path}")
        return self.get_status()
