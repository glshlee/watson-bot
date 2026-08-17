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

SYSTEM_PROMPT = """당신은 친절하고 스마트한 AI 조수 'Watson'입니다.
사용자와 자연스럽게 질문 답변, 대화, 아이디어 논의를 진행하세요.

[규칙]
- 만약 사용자가 '할 일 추가', '메모 작성', '일정 저장'을 명확하게 요청한 경우에만 메시지 끝에 아래 형식의 JSON 태그를 포함하세요.
  ```json
  {"action": "save_todo" | "save_memo" | "save_schedule", "content": "저장할 내용"}
  ```
- 일반 대화, 잡담, 아이디어 스케치, 질문 답변일 경우 JSON 태그 없이 친절한 대화 답변만 작성하세요.
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

        prompt = f"{SYSTEM_PROMPT}\n\n사용자 메시지: {user_text}"
        session_id = f"watson_user_{user_id}"

        try:
            res = await self.engine.ask(prompt, session_id=session_id)
            raw_answer = res.get("answer", "")
            
            if not raw_answer or "정제된 답변이 없습니다" in raw_answer:
                raw_answer = "안녕하세요! 무엇을 도와드릴까요?"

            # JSON 코드 블록 검색
            action = "chat"
            content = ""
            reply = raw_answer

            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_answer, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    action = parsed.get("action", "chat")
                    content = parsed.get("content", "")
                    # JSON 블록 제거 후 깨끗한 대화 텍스트만 추출
                    reply = re.sub(r"```json\s*\{.*?\}\s*```", "", raw_answer, flags=re.DOTALL).strip()
                except Exception:
                    pass
            else:
                # 일반 인라인 JSON 태그 검색
                json_match2 = re.search(r"(\{\"action\".*?\})", raw_answer, re.DOTALL)
                if json_match2:
                    try:
                        parsed = json.loads(json_match2.group(1))
                        action = parsed.get("action", "chat")
                        content = parsed.get("content", "")
                        reply = raw_answer.replace(json_match2.group(1), "").strip()
                    except Exception:
                        pass

            return {
                "action": action,
                "content": content,
                "reply": reply if reply else raw_answer
            }
        except Exception as e:
            logging.error(f"AI Engine error: {e}")
            return {
                "action": "chat",
                "content": "",
                "reply": "네, 대화를 이해했습니다. 구체적으로 어떤 내용을 도와드릴까요?"
            }
