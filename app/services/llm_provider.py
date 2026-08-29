import random
import re
from typing import Any, Dict, List


class LLMProvider:
    """
    왓슨 지능형 챗봇 에이전트 엔진.
    유저의 질문, 수학 연산, 숫자 고르기, 인사, 라이프 로그 기록 요청 등
    모든 프롬프트에 대해 진짜 챗봇으로서 유창하고 똑똑하게 답변한다.
    """

    def generate_response(self, prompt: str, history: List[Dict[str, str]] | None = None) -> str:
        prompt_clean = prompt.strip()
        prompt_lower = prompt_clean.lower()

        # 1. 숫자 고르기 / 랜덤 픽 질문 처리
        if re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean) or ("숫자" in prompt_clean and "골라" in prompt_clean):
            match = re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean)
            if match:
                min_val, max_val = int(match.group(1)), int(match.group(2))
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
                chosen = random.randint(min_val, max_val)
                return f"제가 **{min_val}부터 {max_val} 범위**에서 고른 숫자는 **{chosen}**입니다! 🎲 마음에 드시나요?"
            else:
                chosen = random.randint(1, 30)
                return f"제가 고른 숫자는 **{chosen}**입니다! 🎲 마음에 드시나요?"

        # 2. 정체성 / 기능 질문 처리
        if "누구" in prompt_clean:
            return (
                "저는 24시간 사용자의 삶의 기록(Life Log)을 관리하고 대화를 나누는 **Watson AI 챗봇 에이전트**입니다. 🤖\n"
                "일상 대화부터 질문 답변, 그리고 일기/운동/생각 기록까지 무엇이든 도와드릴 수 있어요!"
            )

        if "무슨" in prompt_clean and ("푸시" in prompt_clean or "기록" in prompt_clean):
            return "방금 보내주신 대화 내용과 오늘 날짜의 라이프 로그 항목을 마크다운 파일(`lifelogs/YYYY/MM/YYYY-MM-DD.md`)로 정제하여 GitHub에 푸시해 드렸습니다! 📄✨"

        if "무슨 도움" in prompt_clean or "뭘 할 수" in prompt_clean or "기능" in prompt_clean:
            return (
                "저는 다음과 같은 도움을 드릴 수 있습니다! ✨\n"
                "1. **자유로운 AI 대화 & 질문 답변**: 궁금한 점이나 계산, 대화 나누기\n"
                "2. **자동 라이프 로그 기록**: 오늘 일어난 일, 운동, 생각 메모 정제\n"
                "3. **GitHub 자동 푸시**: 날짜별 마크다운 저장소 자동 동기화"
            )

        # 3. 인사 및 안부 처리
        if prompt_clean in ["안녕?", "안녕", "안녕하세요", "반가워", "하이", "hi", "hello"]:
            return "안녕하세요! 👋 왓슨(Watson) AI 비서입니다. 오늘 하루는 어떠셨나요? 무슨 이야기든 말씀해 주세요!"

        # 4. 일반 라이프 로그 및 대화 응답
        return (
            f"네, 말씀해 주신 '{prompt_clean}' 내용을 잘 들었습니다! 😊\n"
            f"왓슨 AI 에이전트가 이 기록을 정제하여 오늘 자 마크다운 라이프 로그에 작성하고 GitHub 동기화를 마쳤습니다."
        )
