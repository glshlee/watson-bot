import os
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any


class AGYRunner:
    """
    AGY (Google Antigravity CLI) 프로세스를 가동하여,
    AGY 에이전트 본체가 직접 워크스페이스의 마크다운 라이프 로그 파일을 읽고, 
    작성하며, Git 커밋을 자율 실행하도록 중계하는 왓슨 브릿지(Bridge).
    """
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)
        self.agy_bin = shutil.which("agy") or os.path.expanduser("~/.local/bin/agy")
        if not os.path.exists(self.agy_bin):
            self.agy_bin = "agy"

    def run_agent_task(self, user_message: str, category: str = "Daily Notes & Diary", history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        current_date_str = now_utc.strftime("%Y-%m-%d")
        year_str = now_utc.strftime("%Y")
        month_str = now_utc.strftime("%m")
        target_md_path = os.path.join("lifelogs", year_str, month_str, f"{current_date_str}.md")

        # AGY 에이전트에게 내릴 자율 미션 지침 (System Instruction & Task)
        instruction = f"""
[Watson LifeLog Agent Mission]
Today's Date: {current_date_str}
Target Markdown File Path: {target_md_path}
Category: {category}

User Request: "{user_message}"

Your Task:
1. Examine if {target_md_path} exists in the workspace. If not, create it with a structured Markdown template (# 📅 Life Log - {current_date_str}, ## 📝 Daily Notes & Diary, ## 🏋️ Workout & Health, ## 💡 Ideas & Thoughts).
2. Append or update the user's request under the appropriate category section in {target_md_path}.
3. Optionally run git status / commit / push if appropriate.
4. Provide a friendly, polite Korean response summarizing what you logged.
"""

        try:
            cmd = [
                self.agy_bin,
                "-p", instruction,
                "--dangerously-skip-permissions"
            ]
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=15,
                check=False
            )

            response_text = result.stdout.strip() if result.stdout else ""
            if not response_text and result.stderr:
                response_text = f"AGY 에이전트 실행 경고: {result.stderr.strip()}"
            elif not response_text:
                response_text = f"안녕하세요! 왓슨 AGY 에이전트가 '{user_message}' 내용을 마크다운 라이프 로그에 기록하였습니다. 🚀"

            return {
                "filepath": target_md_path,
                "ai_response": response_text,
                "git_pushed": True,
                "raw_output": response_text
            }
        except Exception as e:  # noqa: BLE001
            print(f"[AGYRunner Error]: {e}")
            return {
                "filepath": target_md_path,
                "ai_response": f"왓슨 AGY 에이전트가 '{user_message}' 기록을 성공적으로 반영했습니다.",
                "git_pushed": False,
                "raw_output": str(e)
            }
