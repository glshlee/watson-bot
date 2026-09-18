from __future__ import annotations

import logging
import os

from app.services.llm.agy_client import execute_agy, find_agy_path
from app.services.llm.category_extractor import (
    detect_category,
    extract_actionable_task,
)
from app.services.llm.intent_analyzer import IntentResult, analyze_intent
from app.services.llm.prompt_builder import (
    build_system_prompt,
    get_smart_fallback,
    load_skill_instructions,
)

logger = logging.getLogger("watson.llm")

# Re-export IntentResult for backward compatibility
__all__ = ["IntentResult", "LLMProvider"]


class LLMProvider:
    """
    왓슨 지능형 비서(Watson Butler) 엔진 파사드 (ADR-003, ADR-004, ADR-008, ADR-052).
    서브 도메인 모듈(agy_client, prompt_builder, category_extractor, intent_analyzer)을
    조합하여 단일 진입점 인터페이스 및 100% 하위 호환성을 제공합니다.
    """

    def __init__(self, gtd_path: str | None = None, fast_mode: bool = False):
        self.gtd_path = gtd_path or os.getenv("GTD_PATH", "/home/ubuntu/workspace/life_log")
        self.fast_mode = fast_mode or (os.getenv("FAST_MODE", "").lower() in ("1", "true"))
        self.agy_path = self._find_agy_path()

    def _find_agy_path(self) -> str | None:
        """멀티 플랫폼 agy CLI 바이너리 경로를 탐색합니다 (테스트 패치 호환 유지)."""
        return find_agy_path()

    def _load_skill_instructions(self) -> str:
        """GTD 저장소 내 SKILL.md 지침을 로드합니다 (ADR-032)."""
        return load_skill_instructions(self.gtd_path)

    def _detect_category(self, text: str) -> str:
        """텍스트 내용을 분석하여 적합한 마크다운 카테고리를 추론합니다."""
        return detect_category(text)

    def _extract_actionable_task(self, text: str) -> str:
        """비정형 일상 텍스트에서 실행 가능한 GTD 액션 태스크를 추출합니다 (ADR-014, ADR-042)."""
        return extract_actionable_task(text)

    def _call_ai_engine(self, prompt: str, history: list[dict[str, str]] | None = None) -> str:
        """AGY CLI 또는 지능형 AI 엔진을 호출하며, 미구동 시 스마트 로컬 폴백을 제공합니다."""
        if self.fast_mode:
            return get_smart_fallback(prompt=prompt, history=history)

        agy_bin = self._find_agy_path()
        if agy_bin:
            full_prompt = build_system_prompt(prompt=prompt, history=history, gtd_path=self.gtd_path)
            res = execute_agy(full_prompt=full_prompt, gtd_path=self.gtd_path, agy_bin=agy_bin, timeout=45)
            if res:
                return res

        return get_smart_fallback(prompt=prompt, history=history)

    def analyze_and_respond(
        self,
        prompt: str,
        history: list[dict[str, str]] | None = None,
        pending_log: dict[str, str] | None = None,
    ) -> IntentResult:
        """사용자 입력의 의도를 분석하고 대응 액션 및 응답을 도출합니다."""
        return analyze_intent(
            prompt=prompt,
            history=history,
            pending_log=pending_log,
            gtd_path=self.gtd_path,
            call_ai_engine_func=self._call_ai_engine,
        )

    def generate_response(self, prompt: str, history: list[dict[str, str]] | None = None) -> str:
        """기존 인터페이스 하위 호환용 응답 생성 메서드."""
        result = self.analyze_and_respond(prompt=prompt, history=history)
        return result.ai_response
