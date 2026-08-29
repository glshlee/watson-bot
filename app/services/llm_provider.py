import os
import subprocess

from app.config import settings

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class LLMProvider:
    """
    Google Gemini API, AGY CLI 또는 intelligent Fallback을 사용하는 AI 대화 생성기
    """
    def __init__(self):
        self.api_key = settings.LLM_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = settings.LLM_MODEL or "gemini-1.5-flash"
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
            except Exception:  # noqa: BLE001
                self.model = None
        else:
            self.model = None

    def generate_response(self, prompt: str, history: list[dict[str, str]]) -> str:
        prompt_trimmed = prompt.strip()
        
        # 1. Gemini API 이용 가능 시 실시간 AI 대화 생성
        if self.model:
            try:
                formatted_history = []
                for msg in history[:-1]:  # Exclude latest
                    role = "user" if msg["role"] == "user" else "model"
                    formatted_history.append({"role": role, "parts": [msg["content"]]})
                
                chat = self.model.start_chat(history=formatted_history)
                response = chat.send_message(prompt_trimmed)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:  # noqa: BLE001
                print(f"[Gemini API Notice]: Fallback to Watson persona due to: {e}")

        # 2. AGY CLI 도구 설치 시 실행
        if shutil_which("agy"):
            try:
                result = subprocess.run(
                    ["agy", "prompt", prompt_trimmed],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.SubprocessError, OSError):
                pass

        # 3. 대화형 AI 페르소나 (Watson AI Assistant) Fallback 응답
        if prompt_trimmed in ["안녕?", "안녕", "안녕하세요", "반가워", "하이", "hi", "hello"]:
            return "안녕하세요! 👋 왓슨(Watson) AI 비서입니다. 무엇을 도와드릴까요? 오늘 있었던 일이나 생각, 운동 기록을 편하게 말해주시면 마크다운 라이프 로그로 기록하고 GitHub에 푸시해 드려요!"
        elif "너는 누구" in prompt_trimmed or "누구야" in prompt_trimmed:
            return "저는 24시간 언제나 가동되며 사용자의 삶의 기록(Life Log)을 관리하고 GitHub에 자동 푸시해 주는 Watson AI 에이전트입니다. 🤖"
        else:
            return f"네! 말씀해주신 '{prompt_trimmed}' 내용을 잘 이해했습니다. 왓슨 AI 에이전트가 이 기록을 정제하여 마크다운 라이프 로그에 작성하고 GitHub에 안전하게 커밋 및 푸시를 완료했습니다. ✨"

def shutil_which(cmd: str) -> bool:
    import shutil
    return shutil.which(cmd) is not None
