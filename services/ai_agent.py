import os
import sys
import json
import logging
import re

# Add life_log/infra to sys.path to use AgyEngine
workspace_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
infra_path = os.path.join(workspace_path, "..", "life_log", "infra")
if os.path.exists(infra_path) and infra_path not in sys.path:
    sys.path.append(infra_path)

try:
    from agy_engine import AgyEngine
except ImportError:
    AgyEngine = None

SYSTEM_PROMPT = """당신은 유능하고 친절한 AI 조수 'Watson'입니다.
사용자와 자유롭게 잡담, 아이디어 스케치, 브레인스토밍, 질의응답을 나눌 수 있습니다.

사용자의 메시지를 읽고, 아래의 4가지 행동 중 하나를 결정하세요:
1. "chat": 일반 대화, 잡담, 질문 답변, 아이디어 논의 (기본값, 단순 메모/할일 저장이 아닌 모든 경우)
2. "save_todo": 사용자가 명확하게 할 일(Todo, 과제, 작업)을 추가해 달라고 요청한 경우
3. "save_memo": 사용자가 명확하게 메모 작성, 노트 기록을 요청한 경우
4. "save_schedule": 사용자가 특정 시간/일정을 등록해 달라고 요청한 경우

응답은 반드시 아래 JSON 형식만 출력하세요:
```json
{
  "action": "chat" | "save_todo" | "save_memo" | "save_schedule",
  "content": "저장할 내용 (action이 save일 때만 작성, chat일 경우 빈 문자열)",
  "reply": "사용자에게 전송할 친절한 응답 및 대화 메시지"
}
```
"""

class WatsonAIEngine:
    def __init__(self):
        if AgyEngine:
            self.engine = AgyEngine()
        else:
            self.engine = None
            logging.warning("AgyEngine not available, fallback to basic chat mode.")

    async def analyze_and_respond(self, user_text: str, user_id: int) -> dict:
        if not self.engine:
            return {
                "action": "chat",
                "content": "",
                "reply": f"🤖 Watson입니다: {user_text}"
            }

        prompt = f"{SYSTEM_PROMPT}\n\n[사용자 입력]\n{user_text}"
        session_id = f"watson_user_{user_id}"

        try:
            res = await self.engine.ask(prompt, session_id=session_id)
            raw_answer = res.get("answer", "")
            
            # JSON 블록 추출
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_answer, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
            else:
                # 괄호 수색
                json_match2 = re.search(r"(\{.*?\})", raw_answer, re.DOTALL)
                if json_match2:
                    parsed = json.loads(json_match2.group(1))
                else:
                    # JSON 형식이 아닌 경우 일반 대화 처리
                    parsed = {
                        "action": "chat",
                        "content": "",
                        "reply": raw_answer
                    }
            return parsed
        except Exception as e:
            logging.error(f"AI Engine error: {e}")
            return {
                "action": "chat",
                "content": "",
                "reply": "죄송합니다, 대화 처리 중 오류가 발생했습니다."
            }
