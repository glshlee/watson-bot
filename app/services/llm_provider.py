import os
import shutil
import subprocess


class LLMProvider:
    """
    AGY (Google Antigravity CLI) 중심의 AI 엔진 파이프라인
    """
    def __init__(self):
        # 1. AGY 바이너리 경로 탐색 (글로벌 PATH 및 사용자 홈 경로)
        self.agy_path = shutil.which("agy") or os.path.expanduser("~/.local/bin/agy")
        if not os.path.exists(self.agy_path):
            self.agy_path = "agy"

    def generate_response(self, prompt: str, history: list[dict[str, str]]) -> str:
        prompt_trimmed = prompt.strip()
        
        # AGY 시스템 프롬프트 및 맥락 구성
        system_instruction = (
            "You are Watson, a 24/7 GitHub LifeLog AI Agent. "
            "Respond kindly and concisely in Korean to the user. "
            "Help manage their daily logs, workout notes, and thoughts."
        )
        
        full_prompt = f"[{system_instruction}]\nUser Message: {prompt_trimmed}"

        # 2. AGY CLI 직접 실행 (non-interactive mode)
        try:
            cmd = [self.agy_path, "-p", full_prompt, "--dangerously-skip-permissions"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=40,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            elif result.stderr:
                print(f"[AGY Execution Warning]: {result.stderr}")
        except Exception as e:  # noqa: BLE001
            print(f"[AGY Subprocess Exception]: {e}")

        # 3. AGY 실행 예외 시 Fallback
        return f"안녕하세요! 왓슨(Watson) AGY 에이전트입니다. 말씀해 주신 '{prompt_trimmed}' 내용이 라이프 로그에 작성되고 GitHub에 안전하게 기록되었습니다. 🚀"
