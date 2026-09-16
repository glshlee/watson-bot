"""
Watson 1-Click 셀프호스팅 셋업 점검 및 배포 상태 서비스 (ADR-046).
초기 설치 및 상시 운영 환경에서 텔레그램, LLM, GTD 저장소, 보안 인증, 출근길 설정 등의
필수/선택 구성 요소 준비 상태를 진단하고 리포트를 생성합니다.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from typing import Any

from app.config import settings
from app.services.commute_config_service import CommuteConfigService
from app.services.settings_service import SettingsService

logger = logging.getLogger("watson.setup")


class SetupService:
    """왓슨 시스템 설정 및 환경 점검 서비스."""

    def __init__(self) -> None:
        self.settings_service = SettingsService()
        self.commute_service = CommuteConfigService()

    @staticmethod
    def _mask_secret(val: str, show_chars: int = 4) -> str:
        if not val:
            return ""
        clean = val.strip()
        if len(clean) <= show_chars * 2:
            return "******"
        return f"{clean[:show_chars]}...{clean[-show_chars:]}"

    def get_setup_status(self) -> dict[str, Any]:
        """시스템 주요 구성 요소의 설정 및 정상 작동 여부를 종합 진단합니다."""
        checks: dict[str, dict[str, Any]] = {}
        missing_required: list[str] = []
        recommendations: list[str] = []

        # 1. 텔레그램 봇 토큰
        tg_token = settings.TELEGRAM_BOT_TOKEN.strip()
        tg_token_ok = bool(tg_token and tg_token != "your_telegram_bot_token_here")
        if not tg_token_ok:
            missing_required.append("TELEGRAM_BOT_TOKEN")
            recommendations.append("@BotFather에서 텔레그램 봇 토큰을 발급받아 설정하세요.")
        checks["telegram_bot"] = {
            "name": "텔레그램 봇 토큰",
            "required": True,
            "status": "ok" if tg_token_ok else "missing",
            "configured": tg_token_ok,
            "masked_value": self._mask_secret(tg_token) if tg_token_ok else "",
        }

        # 2. 텔레그램 관리자 Chat ID
        tg_ids = [i.strip() for i in settings.TELEGRAM_ALLOWED_CHAT_IDS.split(",") if i.strip()]
        tg_ids_ok = len(tg_ids) > 0
        if not tg_ids_ok:
            missing_required.append("TELEGRAM_ALLOWED_CHAT_IDS")
            recommendations.append("보안을 위해 본인의 텔레그램 Chat ID(@userinfobot)를 등록하세요.")
        checks["telegram_admin"] = {
            "name": "텔레그램 관리자 ID",
            "required": True,
            "status": "ok" if tg_ids_ok else "missing",
            "configured": tg_ids_ok,
            "count": len(tg_ids),
        }

        # 3. AI LLM 엔진 (Gemini / LLM API Key)
        gemini_key = (settings.GEMINI_API_KEY or settings.LLM_API_KEY or os.getenv("GEMINI_API_KEY", "")).strip()
        llm_ok = bool(gemini_key and gemini_key != "your_gemini_api_key_here")
        if not llm_ok:
            recommendations.append("Google AI Studio(aistudio.google.com)에서 무료 Gemini API Key를 등록하면 고급 비서 기능이 활성화됩니다.")
        checks["llm_engine"] = {
            "name": "AI LLM 엔진",
            "required": False,
            "status": "ok" if llm_ok else "warning",
            "configured": llm_ok,
            "model": settings.LLM_MODEL,
            "masked_key": self._mask_secret(gemini_key) if llm_ok else "",
            "note": "무료 Gemini API Key 설정 권장 (미설정 시 룰 기반 엔진 작동)",
        }

        # 4. GTD 및 라이프로그 저장소
        gtd_path = self.settings_service.get_gtd_path()
        gtd_exists = os.path.exists(gtd_path) and os.path.isdir(gtd_path)
        git_dir = os.path.join(gtd_path, ".git")
        git_ok = os.path.exists(git_dir) and os.path.isdir(git_dir)
        daily_dir = os.path.join(gtd_path, "logs", "daily")
        has_daily = os.path.exists(daily_dir)
        inbox_file = os.path.join(gtd_path, "gtd", "inbox.md")
        has_inbox = os.path.exists(inbox_file)

        gtd_status = "ok" if (gtd_exists and git_ok) else ("warning" if gtd_exists else "missing")
        if not gtd_exists:
            missing_required.append("GTD_PATH")
            recommendations.append(f"GTD 저장소 디렉토리({gtd_path})를 생성하세요.")
        elif not git_ok:
            recommendations.append(f"GTD 저장소({gtd_path})에서 `git init`을 실행하여 버전 관리를 활성화하세요.")

        checks["gtd_storage"] = {
            "name": "GTD 저장소",
            "required": True,
            "status": gtd_status,
            "configured": gtd_exists,
            "path": gtd_path,
            "directory_exists": gtd_exists,
            "git_initialized": git_ok,
            "has_daily_logs": has_daily,
            "has_inbox": has_inbox,
        }

        # 5. 웹 대시보드 보안 인증 (Basic Auth)
        web_auth = settings.WEB_AUTH_ENABLED
        web_user = settings.WEB_AUTH_USERNAME
        has_pw = bool(settings.WEB_AUTH_PASSWORD.strip())
        checks["web_auth"] = {
            "name": "웹 대시보드 보안",
            "required": False,
            "status": "ok" if (web_auth and has_pw) else ("info" if not web_auth else "warning"),
            "enabled": web_auth,
            "username": web_user if web_auth else "",
            "password_set": has_pw,
            "note": "외부망 노출 시 WEB_AUTH_ENABLED=true 및 비밀번호 설정을 권장합니다.",
        }

        # 6. 출근길 및 날씨 브리핑 설정
        commute_cfg = self.commute_service.get_config()
        location_set = bool(commute_cfg.get("location_name"))
        bus_set = bool(commute_cfg.get("bus_stop_id"))
        checks["commute_briefing"] = {
            "name": "출근길·날씨 브리핑",
            "required": False,
            "status": "ok" if (location_set and bus_set) else ("info" if location_set else "default"),
            "configured": location_set,
            "location": commute_cfg.get("location_name", "미설정"),
            "dispatch_time": commute_cfg.get("dispatch_time", "07:30"),
            "bus_route": commute_cfg.get("bus_route_no", ""),
        }

        # 7. Cloudflare Tunnel (외부 접속)
        cf_token = settings.CLOUDFLARE_TUNNEL_TOKEN.strip()
        cf_ok = bool(cf_token)
        checks["cloudflare_tunnel"] = {
            "name": "Cloudflare Tunnel",
            "required": False,
            "status": "ok" if cf_ok else "info",
            "configured": cf_ok,
            "masked_token": self._mask_secret(cf_token) if cf_ok else "",
            "note": "포트포워딩 없이 외부 HTTPS 접속 시 CLOUDFLARE_TUNNEL_TOKEN을 설정하세요.",
        }

        # 8. 시스템 런타임 환경
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        db_exists = os.path.exists(db_path)
        checks["runtime"] = {
            "name": "시스템 런타임",
            "required": True,
            "status": "ok",
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "port": settings.PORT,
            "timezone": settings.TIMEZONE,
            "db_path": db_path,
            "db_exists": db_exists,
        }

        total_checks = len(checks)
        passed_checks = sum(1 for c in checks.values() if c["status"] == "ok")
        readiness_pct = round((passed_checks / total_checks) * 100, 1)
        is_ready = len(missing_required) == 0

        return {
            "is_ready": is_ready,
            "readiness_percentage": readiness_pct,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "missing_required": missing_required,
            "recommendations": recommendations,
            "checks": checks,
        }

    def format_status_report(self) -> str:
        """DevBot 및 CLI 환경에서 가독성 높은 마크다운 점검 리포트를 반환합니다."""
        status_data = self.get_setup_status()
        checks = status_data["checks"]
        is_ready = status_data["is_ready"]
        pct = status_data["readiness_percentage"]

        header_icon = "🚀" if is_ready else "⚠️"
        ready_badge = "✅ 준비 완료 (운영 가능)" if is_ready else "❌ 필수 설정 미흡 (보완 필요)"

        lines = [
            f"### {header_icon} **Watson 시스템 설정 & 배포 상태 진단** (`ADR-046`)",
            f"• **준비율**: `{pct}%` ({status_data['passed_checks']}/{status_data['total_checks']} 항목 통과)",
            f"• **종합 판정**: {ready_badge}",
            "",
            "#### 📋 **구성 요소별 상세 진단표**",
        ]

        def _icon(st: str) -> str:
            if st == "ok":
                return "✅"
            if st == "warning":
                return "⚠️"
            if st == "missing":
                return "❌"
            return "ℹ️"

        # 텔레그램 봇
        tb = checks["telegram_bot"]
        lines.append(f"1. **{tb['name']}**: {_icon(tb['status'])} {'설정됨' if tb['configured'] else '미설정 (필수)'}")

        # 텔레그램 관리자
        ta = checks["telegram_admin"]
        lines.append(f"2. **{ta['name']}**: {_icon(ta['status'])} {'등록됨 (' + str(ta['count']) + '명)' if ta['configured'] else '미등록 (필수)'}")

        # AI LLM 엔진
        llm = checks["llm_engine"]
        lines.append(f"3. **{llm['name']}**: {_icon(llm['status'])} {'연동됨 (' + llm['model'] + ')' if llm['configured'] else '미등록 (룰 기반 폴백)'}")

        # GTD 저장소
        gtd = checks["gtd_storage"]
        gtd_detail = f"`{gtd['path']}`"
        if gtd["directory_exists"]:
            gtd_detail += " (Git: " + ("연동됨" if gtd["git_initialized"] else "미초기화") + ")"
        else:
            gtd_detail += " (디렉토리 없음)"
        lines.append(f"4. **{gtd['name']}**: {_icon(gtd['status'])} {gtd_detail}")

        # 웹 보안
        wa = checks["web_auth"]
        lines.append(f"5. **{wa['name']}**: {_icon(wa['status'])} {'활성화 (ID: ' + wa['username'] + ')' if wa['enabled'] else '비활성화 (내부망/로컬용)'}")

        # 출근길 & 날씨
        cb = checks["commute_briefing"]
        lines.append(f"6. **{cb['name']}**: {_icon(cb['status'])} {cb['location']} (발송: {cb['dispatch_time']})")

        # Cloudflare Tunnel
        cf = checks["cloudflare_tunnel"]
        lines.append(f"7. **{cf['name']}**: {_icon(cf['status'])} {'토큰 등록됨 (HTTPS)' if cf['configured'] else '미설정 (선택)'}")

        # 런타임
        rt = checks["runtime"]
        lines.append(f"8. **{rt['name']}**: {_icon(rt['status'])} Python {rt['python_version']} (포트: {rt['port']}, 타임존: {rt['timezone']})")

        if status_data["missing_required"]:
            lines.extend([
                "",
                "#### 🚨 **즉시 조치가 필요한 필수 항목**",
            ])
            for m in status_data["missing_required"]:
                lines.append(f"• ❌ `{m}` 값이 비어있습니다.")

        if status_data["recommendations"]:
            lines.extend([
                "",
                "#### 💡 **추천 권장 사항**",
            ])
            for r in status_data["recommendations"]:
                lines.append(f"• {r}")

        lines.extend([
            "",
            "*(대화형 자동 설정은 터미널에서 `./scripts/setup_wizard.sh`를 실행하세요)* 🛠️✨",
        ])

        return "\n".join(lines)
