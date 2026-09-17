from __future__ import annotations

import logging
import os
import shutil
import subprocess

logger = logging.getLogger("watson.llm.agy")


def find_agy_path() -> str | None:
    """멀티 플랫폼(Linux/Mac/Docker) agy CLI 바이너리 경로를 동적으로 탐색합니다."""
    found = shutil.which("agy")
    if found and os.path.exists(found):
        return found
    candidates = [
        os.path.expanduser("~/.local/bin/agy"),
        "/home/ubuntu/.local/bin/agy",
        "/usr/local/bin/agy",
        "/usr/bin/agy",
        "/Users/glshlee/.local/bin/agy",
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


def execute_agy(
    full_prompt: str,
    gtd_path: str | None = None,
    agy_bin: str | None = None,
    timeout: int = 45,
) -> str | None:
    """Antigravity CLI 바이너리를 서브프로세스로 안전하게 실행하고 응답을 반환합니다."""
    bin_path = agy_bin or find_agy_path()
    if not bin_path:
        return None

    try:
        env = os.environ.copy()
        env["PATH"] = "/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")

        cmd = [
            bin_path,
            "-p",
            full_prompt,
            "--model",
            "gemini-3.8-flash-low",
            "--effort",
            "low",
            "--disable-slash-commands",
            "--dangerously-skip-permissions",
        ]
        work_dir = gtd_path if (gtd_path and os.path.exists(gtd_path)) else "/tmp"
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
            cwd=work_dir,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except (subprocess.SubprocessError, OSError) as e:
        logger.warning(f"AGY execution error: {e}")

    return None
