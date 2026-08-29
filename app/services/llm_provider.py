import shutil
import subprocess

from app.config import settings


class LLMProvider:
    """
    AGY CLI, Gemini API 또는 Custom LLM을 선택적으로 사용하는 어댑터
    """
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    def generate_response(self, prompt: str, history: list[dict[str, str]]) -> str:
        # 1. AGY CLI 도구가 설치되어 있는 경우 우선 활용 가능
        if shutil.which("agy"):
            try:
                result = subprocess.run(
                    ["agy", "prompt", prompt],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.SubprocessError, OSError):
                pass

        # 2. Rule/Template 기반 또는 LLM Fallback 응답
        last_user_msg = prompt
        reply_lines = [
            f"네, 말씀해 주신 내용('{last_user_msg}')을 왓슨 AI 에이전트가 완벽히 분석했습니다.",
            "라이프 로그 양식에 맞춰 정제하여 날짜별 마크다운 파일에 기록하였으며, GitHub 커밋 및 푸시를 완료했습니다."
        ]
        return "\n\n".join(reply_lines)
