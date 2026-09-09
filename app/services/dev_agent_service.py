import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.llm_provider import LLMProvider
from app.services.session_service import SessionService

logger = logging.getLogger("watson.dev_agent")


class DevAgentService:
    """
    개발 전담 AI 에이전트 (DevBot / Dev Agent) 서비스 (ADR-018 준수).
    코드베이스 분석, Git 상태/Diff/커밋 조회, 터미널 도구 실행 및 소프트웨어 엔지니어링 대화를 수행한다.
    """

    def __init__(self, db: Session, workspace_path: str = "."):
        self.db = db
        self.workspace_path = os.path.abspath(workspace_path)
        self.session_service = SessionService(db)
        self.llm_provider = LLMProvider()

    def _run_git_cmd(self, args: list[str]) -> str:
        """안전한 읽기 전용 Git 명령을 실행합니다."""
        try:
            res = subprocess.run(
                ["git", "-C", self.workspace_path] + args,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            out = res.stdout.strip()
            if not out and res.stderr:
                out = res.stderr.strip()
            return out or "(내용 없음)"
        except Exception as e:  # noqa: BLE001
            return f"오류 발생: {e}"

    def get_workspace_status(self) -> dict[str, Any]:
        """워크스페이스의 현재 Git 및 시스템 상태를 요약 반환합니다."""
        branch = self._run_git_cmd(["branch", "--show-current"])
        last_commit = self._run_git_cmd(["log", "-1", "--oneline"])
        status_raw = self._run_git_cmd(["status", "--porcelain"])
        changed_files = len([line for line in status_raw.splitlines() if line.strip()]) if status_raw != "(내용 없음)" else 0

        return {
            "workspace": os.path.basename(self.workspace_path),
            "branch": branch or "main",
            "last_commit": last_commit,
            "changed_files_count": changed_files,
            "status": "clean" if changed_files == 0 else "modified",
            "engine": "Antigravity CLI / Gemini Bridge",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def process_dev_request(
        self,
        session_id: str,
        user_message: str,
        channel: str = "web",
    ) -> dict[str, Any]:
        """개발자 요청을 분석하여 Git/엔지니어링 명령을 실행하거나 AI 응답을 반환합니다."""
        clean_msg = user_message.strip()

        # 1. Ensure dev session exists
        self.session_service.get_or_create_session(
            session_id=session_id,
            channel=channel,
            title="New Dev Task",
            agent_type="dev",
        )

        # 2. Record user message
        self.session_service.add_message(session_id, "user", clean_msg)

        # 3. Auto-update session title on first message
        self.session_service.auto_update_session_title(session_id, clean_msg)

        # 4. Check for direct developer shortcuts
        lower_msg = clean_msg.lower()
        ai_response = ""
        action_type = "chat"

        if lower_msg in ["/status", "git status", "상태", "상태 확인", "깃 상태"]:
            action_type = "git_status"
            branch = self._run_git_cmd(["branch", "--show-current"])
            status = self._run_git_cmd(["status", "-s"])
            ai_response = f"### 🌿 Git 상태 요약 (`{branch}`)\n\n"
            if status == "(내용 없음)":
                ai_response += "✅ 작업 트리가 깨끗합니다. (Working tree clean)\n"
            else:
                ai_response += f"```text\n{status}\n```\n"

        elif lower_msg in ["/diff", "git diff", "변경점", "변경점 확인"]:
            action_type = "git_diff"
            diff = self._run_git_cmd(["diff"])
            diff_staged = self._run_git_cmd(["diff", "--staged"])
            ai_response = "### 🔍 Git Diff 결과\n\n"
            if diff == "(내용 없음)" and diff_staged == "(내용 없음)":
                ai_response += "현재 변경된 코드(Unstaged/Staged)가 없습니다."
            else:
                if diff != "(내용 없음)":
                    ai_response += f"#### Unstaged Changes:\n```diff\n{diff}\n```\n"
                if diff_staged != "(내용 없음)":
                    ai_response += f"#### Staged Changes:\n```diff\n{diff_staged}\n```\n"

        elif lower_msg in ["/log", "git log", "최근 커밋", "커밋 내역"]:
            action_type = "git_log"
            logs = self._run_git_cmd(["log", "-n", "7", "--oneline", "--decorate"])
            ai_response = f"### 📜 최근 Git 커밋 내역 (최근 7건)\n\n```text\n{logs}\n```"

        elif lower_msg in ["/branch", "git branch", "브랜치 목록"]:
            action_type = "git_branch"
            branches = self._run_git_cmd(["branch", "-a"])
            ai_response = f"### 🌿 브랜치 목록\n\n```text\n{branches}\n```"

        else:
            # 5. General software engineering query via LLM
            action_type = "ai_reasoning"
            ws_status = self.get_workspace_status()
            repo_context = (
                f"[Workspace Context]\n"
                f"- Repository: {ws_status['workspace']}\n"
                f"- Branch: {ws_status['branch']}\n"
                f"- Changed Files: {ws_status['changed_files_count']}\n"
                f"- Last Commit: {ws_status['last_commit']}\n"
            )

            dev_system_prompt = (
                "You are DevBot, an expert AI Software Engineer and DevOps Agent for this project.\n"
                "You specialize in Python, FastAPI, SQLite, Git automation, and clean architecture.\n"
                "Answer concisely, technically, and constructively with clear code snippets or markdown diagrams when appropriate.\n"
                f"{repo_context}"
            )

            history = self.session_service.get_session_history(session_id, limit=6)
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-4:]]) if history else ""
            full_prompt = f"{dev_system_prompt}\n\nRecent History:\n{history_context}\n\nUser Question: {clean_msg}"

            # Use LLMProvider analyze or generate
            try:
                if self.llm_provider.agy_path:
                    cmd = [
                        self.llm_provider.agy_path,
                        "--mode", "plan",
                        "--dangerously-skip-permissions",
                        full_prompt
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=25, check=False)
                    if res.returncode == 0 and res.stdout.strip():
                        ai_response = res.stdout.strip()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"AGY dev generation fallback: {e}")

            if not ai_response:
                ai_response = (
                    f"안녕하세요! 개발 전담 에이전트 **DevBot**입니다. 💻\n\n"
                    f"현재 워크스페이스(`{ws_status['workspace']}`)의 `{ws_status['branch']}` 브랜치를 모니터링 중입니다. "
                    f"(수정 중인 파일: {ws_status['changed_files_count']}개)\n\n"
                    f"문의하신 내용: **\"{clean_msg}\"**\n\n"
                    f"코드베이스 분석, 버그 수정, 단위 테스트(`pytest`), Git 브랜치 관리 등 "
                    f"필요한 엔지니어링 작업을 언제든 말씀해 주세요! 빠른 명령어(`/status`, `/diff`, `/log`)도 지원합니다."
                )

        # 6. Record assistant response
        self.session_service.add_message(session_id, "assistant", ai_response)

        return {
            "session_id": session_id,
            "user_message": clean_msg,
            "ai_response": ai_response,
            "action_type": action_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
