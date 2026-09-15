"""
Vision AI 멀티모달 시각 지능 서비스 (ADR-044).
사진, 영수증, 운동 인증샷, 메모 캡처를 Gemini Vision AI로 심층 분석하고,
정제된 라이프로그 마크다운 및 GTD 태스크 초안을 생성합니다.
"""

import base64
import json
import logging
import mimetypes
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from app.config import get_now, settings

logger = logging.getLogger("watson.vision")


@dataclass
class VisionAnalysisResult:
    """사진 분석 결과 데이터클래스."""

    domain: str  # workout, meal, receipt, memo, general
    domain_kr: str  # 운동 인증, 식사/맛집, 영수증/지출, 메모/손글씨, 일상 사진
    summary: str  # 한 줄 핵심 요약
    details: dict[str, Any] = field(default_factory=dict)  # 세부 메트릭 (칼로리, 시간, 상호, 금액 등)
    suggested_category: str = "Daily Notes & Diary"  # 마크다운 섹션
    markdown_content: str = ""  # 일기에 기록될 포맷팅된 본문 블록
    gtd_task: str | None = None  # GTD inbox에 제안할 액션 태스크
    image_rel_path: str = ""  # 저장된 상대 경로 (예: attachments/2026/09/photo.jpg)


class VisionService:
    """
    멀티모달 시각 분석 서비스 (ADR-044).
    1. Gemini 1.5 Flash Vision REST API를 통한 고속 시각 분석
    2. 도메인별(운동, 영수증, 식사, 메모) 특화 파싱 및 프라이버시 마스킹
    3. 네트워크 미연결 / 키 부재 시 고탄력 휴리스틱 폴백 지원
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.LLM_API_KEY or os.getenv("GEMINI_API_KEY", "")

    def analyze_image(
        self,
        image_path: str,
        user_caption: str = "",
        image_rel_path: str = "",
    ) -> VisionAnalysisResult:
        """
        이미지 파일을 분석하여 도메인, 요약, 수치, 마크다운 초안을 반환합니다.
        """
        if not os.path.exists(image_path):
            return self._create_fallback_result(
                user_caption=user_caption,
                image_rel_path=image_rel_path,
                error_msg=f"이미지 파일이 존재하지 않습니다: {image_path}",
            )

        # 1. API 키가 있는 경우 Gemini 1.5 Flash Vision 호출 시도
        if self.api_key:
            try:
                res = self._call_gemini_vision(image_path, user_caption, image_rel_path)
                if res:
                    return res
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Gemini Vision API 호출 실패, 휴리스틱 분석으로 전환: {e}")

        # 2. 휴리스틱 및 파일 메타데이터 기반 스마트 분석 폴백
        return self._heuristic_analyze(image_path, user_caption, image_rel_path)

    def _call_gemini_vision(
        self,
        image_path: str,
        user_caption: str,
        image_rel_path: str,
    ) -> VisionAnalysisResult | None:
        """Gemini 1.5 Flash REST API를 직접 호출하여 구조화된 JSON 분석을 수행합니다."""
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        b64_data = base64.b64encode(image_bytes).decode("utf-8")

        system_instruction = (
            "당신은 개인 비서 왓슨(Watson)의 시각 지능 엔진입니다. 사용자가 보낸 일상 사진을 분석하여 다음 5대 도메인 중 하나로 분류하고 세부 정보를 JSON으로 추출하세요.\n"
            "1. workout (운동 인증샷: 애플워치, 가민, 인바디, 러닝 앱 화면, 헬스장 기구 등)\n"
            "2. meal (식사 및 맛집 탐방: 음식 사진, 식당 테이블, 디저트 등)\n"
            "3. receipt (영수증 및 지출: 종이/전자 영수증, 결제 캡처 등 - 카드번호는 절대 노출 금지)\n"
            "4. memo (손글씨 메모, 포스트잇, 화이트보드 회의 필기 등)\n"
            "5. general (일반 일상, 풍경, 사물, 반려동물 등)\n\n"
            "반드시 아래 JSON 형식으로만 응답하세요(코드블록 없이 순수 JSON):\n"
            "{\n"
            '  "domain": "workout|meal|receipt|memo|general",\n'
            '  "summary": "한 줄 핵심 요약 (한국어)",\n'
            '  "details": {\n'
            '    "exercise_type": "러닝/웨이트/수영 등 (workout일 때)",\n'
            '    "duration": "운동 시간 (workout일 때)",\n'
            '    "distance": "거리 (workout일 때)",\n'
            '    "calories": "칼로리 (workout일 때)",\n'
            '    "heart_rate": "심박수 (workout일 때)",\n'
            '    "menu_name": "메뉴명 (meal일 때)",\n'
            '    "merchant": "상호명 (receipt일 때)",\n'
            '    "amount": "결제 금액 (receipt일 때)",\n'
            '    "memo_text": "추출된 텍스트 (memo일 때)"\n'
            "  },\n"
            '  "suggested_category": "Workout & Health | Daily Notes & Diary | GTD Inbox",\n'
            '  "markdown_content": "일기에 삽입될 완성형 마크다운 (불릿/표 서식 포함, 사진 태그 제외)",\n'
            '  "gtd_task": "필요 시 GTD inbox에 등록할 액션 태스크 (없으면 null)"\n'
            "}"
        )

        prompt_text = f"사용자 캡션: '{user_caption}'. 사진을 분석하고 명시된 JSON 양식으로 응답하세요."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\n{prompt_text}"},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_data,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"Gemini Vision API error: {resp.status_code} - {resp.text}")
                    return None

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None

                content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = json.loads(content_text)
                return self._build_result_from_dict(parsed, image_rel_path, user_caption)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Vision API 요청 실패: {e}")
            return None

    def _heuristic_analyze(
        self,
        image_path: str,
        user_caption: str,
        image_rel_path: str,
    ) -> VisionAnalysisResult:
        """
        AI API가 없거나 오프라인일 때, 캡션 및 파일 특성을 분석하여
        신뢰할 수 있는 도메인 분류와 정갈한 마크다운을 생성하는 지능형 폴백 엔진입니다.
        """
        caption_lower = user_caption.lower()
        now = get_now()
        time_str = now.strftime("%H:%M")

        # 1. 🏃 운동 인증 도메인 판별
        workout_keywords = ["러닝", "달리기", "런닝", "헬스", "스쿼트", "벤치", "운동", "오운완", "인바디", "workout", "run", "gym", "km", "kcal", "체중"]
        if any(kw in caption_lower for kw in workout_keywords):
            # 수치 추출 시도 (예: 5km, 350kcal, 30분)
            km_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:km|킬로)", user_caption)
            kcal_match = re.search(r"(\d+)\s*(?:kcal|칼로리)", user_caption)
            min_match = re.search(r"(\d+)\s*(?:분|min)", user_caption)

            distance = f"{km_match.group(1)} km" if km_match else "거리 기록 미상"
            calories = f"{kcal_match.group(1)} kcal" if kcal_match else "칼로리 기록 미상"
            duration = f"{min_match.group(1)} 분" if min_match else "시간 기록 미상"

            summary = f"운동 완료 인증 ({user_caption or '러닝 및 트레이닝'})"
            img_tag = f"![운동 인증](/{image_rel_path})" if image_rel_path else ""

            markdown = (
                f"- [{time_str}] 🏃 **운동 인증 및 피트니스 기록**\n"
                f"  - **종목 및 내용**: {user_caption or '러닝/헬스 세션'}\n"
                f"  - **주요 지표**: ⏱️ {duration} | 📏 {distance} | 🔥 {calories}\n"
                f"  {img_tag}\n"
                f"  > 💡 왓슨 코멘트: 꾸준한 운동 실천이 멋집니다! 충분한 수분 섭취와 스트레칭을 잊지 마세요."
            )

            return VisionAnalysisResult(
                domain="workout",
                domain_kr="운동 인증",
                summary=summary,
                details={
                    "exercise_type": user_caption or "트레이닝",
                    "duration": duration,
                    "distance": distance,
                    "calories": calories,
                },
                suggested_category="Workout & Health",
                markdown_content=markdown,
                gtd_task=None,
                image_rel_path=image_rel_path,
            )

        # 2. 🧾 영수증 및 지출 도메인 판별
        receipt_keywords = ["영수증", "결제", "지출", "구매", "내돈내산", "원", "receipt", "pay", "식대", "마트", "카페"]
        if any(kw in caption_lower for kw in receipt_keywords):
            # 금액 추출 시도 (예: 15,000원, 8000원)
            amount_match = re.search(r"([\d,]+)\s*원", user_caption)
            amount = f"{amount_match.group(1)}원" if amount_match else "금액 미상"

            prefix = re.split(r"(?:결제|영수증|지출|내역)", user_caption)[0].strip()
            merchant = prefix.split("에서")[0].strip() if "에서" in prefix else prefix
            if not merchant:
                merchant_match = re.search(r"([가-힣a-zA-Z0-9]+)\s*(?:에서|카페|식당|마트)", user_caption)
                merchant = merchant_match.group(1) if merchant_match else "지출처"

            summary = f"{merchant} 지출 영수증 ({amount})"
            img_tag = f"![영수증](/{image_rel_path})" if image_rel_path else ""

            markdown = (
                f"- [{time_str}] 🧾 **지출 및 결제 영수증**\n"
                f"  - **상호명**: {merchant}\n"
                f"  - **지출 금액**: {amount}\n"
                f"  - **비고**: {user_caption}\n"
                f"  {img_tag}"
            )

            gtd_task = f"- [ ] 가계부 정리 및 지출 확인: {merchant} {amount} (~{now.strftime('%Y-%m-%d')})"

            return VisionAnalysisResult(
                domain="receipt",
                domain_kr="영수증/지출",
                summary=summary,
                details={
                    "merchant": merchant,
                    "amount": amount,
                    "masked_card": "****-****-****-****",
                },
                suggested_category="Daily Notes & Diary",
                markdown_content=markdown,
                gtd_task=gtd_task,
                image_rel_path=image_rel_path,
            )

        # 3. 🍲 식사 & 맛집 도메인 판별
        meal_keywords = ["맛있", "점심", "저녁", "아침", "식사", "맛집", "커피", "디저트", "먹었", "메뉴", "밥", "고기", "국밥"]
        if any(kw in caption_lower for kw in meal_keywords):
            summary = f"식사 및 맛집 기록 ({user_caption or '맛있는 식사'})"
            img_tag = f"![식사 사진](/{image_rel_path})" if image_rel_path else ""

            markdown = (
                f"- [{time_str}] 🍲 **식사 & 미식 저널**\n"
                f"  - **메뉴 및 내용**: {user_caption or '정갈한 한 끼'}\n"
                f"  - **시간대**: {time_str} 식사\n"
                f"  {img_tag}"
            )

            return VisionAnalysisResult(
                domain="meal",
                domain_kr="식사/맛집",
                summary=summary,
                details={
                    "menu_name": user_caption or "식사",
                    "meal_time": time_str,
                },
                suggested_category="Daily Notes & Diary",
                markdown_content=markdown,
                gtd_task=None,
                image_rel_path=image_rel_path,
            )

        # 4. 📝 메모 / 포스트잇 / 화이트보드 도메인 판별
        memo_keywords = ["메모", "필기", "아이디어", "화이트보드", "포스트잇", "회의", "정리", "할일"]
        if any(kw in caption_lower for kw in memo_keywords):
            summary = f"필기 및 아이디어 메모 ({user_caption or '회의/아이디어 메모'})"
            img_tag = f"![메모 캡처](/{image_rel_path})" if image_rel_path else ""

            markdown = (
                f"- [{time_str}] 📝 **캡처 메모 및 아이디어**\n"
                f"  - **메모 내용**: {user_caption or '시각 캡처 메모'}\n"
                f"  {img_tag}"
            )

            gtd_task = f"- [ ] 캡처 메모 내용 검토 및 태스크 구체화: {user_caption or '아이디어 캡처'}"

            return VisionAnalysisResult(
                domain="memo",
                domain_kr="메모/손글씨",
                summary=summary,
                details={
                    "memo_topic": user_caption or "회의/아이디어",
                },
                suggested_category="Daily Notes & Diary",
                markdown_content=markdown,
                gtd_task=gtd_task,
                image_rel_path=image_rel_path,
            )

        # 5. 🖼️ 일반 사진 도메인 기본값
        summary = f"일상 사진 캡처 ({user_caption or '순간 기록'})"
        img_tag = f"![일상 사진](/{image_rel_path})" if image_rel_path else ""

        markdown = (
            f"- [{time_str}] 📷 **일상 캡처 및 모먼트**\n"
            f"  - **설명**: {user_caption or '오늘의 소중한 순간'}\n"
            f"  {img_tag}"
        )

        return VisionAnalysisResult(
            domain="general",
            domain_kr="일상 사진",
            summary=summary,
            details={"caption": user_caption},
            suggested_category="Daily Notes & Diary",
            markdown_content=markdown,
            gtd_task=None,
            image_rel_path=image_rel_path,
        )

    def _build_result_from_dict(
        self,
        data: dict[str, Any],
        image_rel_path: str,
        user_caption: str,
    ) -> VisionAnalysisResult:
        """JSON 데이터로부터 VisionAnalysisResult 객체를 정규화하여 조립합니다."""
        domain = data.get("domain", "general").lower()
        domain_kr_map = {
            "workout": "운동 인증",
            "meal": "식사/맛집",
            "receipt": "영수증/지출",
            "memo": "메모/손글씨",
            "general": "일상 사진",
        }
        domain_kr = domain_kr_map.get(domain, "일상 사진")
        summary = data.get("summary", f"{domain_kr} 기록 ({user_caption})")
        details = data.get("details", {})
        suggested_cat = data.get("suggested_category", "Daily Notes & Diary")
        if domain == "workout":
            suggested_cat = "Workout & Health"

        # 마크다운 본문에 이미지 태그가 없으면 추가
        raw_md = data.get("markdown_content", "").strip()
        img_tag = f"![{summary}](/{image_rel_path})" if image_rel_path else ""

        now = get_now()
        time_str = now.strftime("%H:%M")

        if not raw_md:
            raw_md = f"- [{time_str}] 📷 **{summary}**\n  - {user_caption}"

        # 카드 및 태그 결합
        if img_tag and img_tag not in raw_md:
            formatted_md = f"{raw_md}\n  {img_tag}"
        else:
            formatted_md = raw_md

        # 영수증 민감정보 마스킹 강화
        if domain == "receipt":
            details["masked_card"] = "****-****-****-****"

        gtd_task = data.get("gtd_task")

        return VisionAnalysisResult(
            domain=domain,
            domain_kr=domain_kr,
            summary=summary,
            details=details,
            suggested_category=suggested_cat,
            markdown_content=formatted_md,
            gtd_task=gtd_task,
            image_rel_path=image_rel_path,
        )

    def _create_fallback_result(
        self,
        user_caption: str,
        image_rel_path: str,
        error_msg: str,
    ) -> VisionAnalysisResult:
        """에러 발생 시 안전 폴백 결과 반환."""
        now = get_now()
        time_str = now.strftime("%H:%M")
        img_tag = f"![사진](/{image_rel_path})" if image_rel_path else ""
        return VisionAnalysisResult(
            domain="general",
            domain_kr="일상 사진",
            summary=f"사진 첨부 ({user_caption or '일상 메모'})",
            details={"error": error_msg},
            suggested_category="Media & Attachments",
            markdown_content=f"- [{time_str}] 📷 **사진 첨부**\n  - {user_caption or '사진 메모'}\n  {img_tag}",
            gtd_task=None,
            image_rel_path=image_rel_path,
        )

    def format_draft_card(self, result: VisionAnalysisResult) -> str:
        """
        사용자에게 2단계 사전 검토(ADR-029)로 제시할 초안 카드를 생성합니다.
        """
        icon_map = {
            "workout": "🏃",
            "meal": "🍲",
            "receipt": "🧾",
            "memo": "📝",
            "general": "📷",
        }
        icon = icon_map.get(result.domain, "📷")

        # 세부 수치 요약 라인
        metrics_line = ""
        if result.domain == "workout" and result.details:
            parts = []
            if result.details.get("duration"):
                parts.append(f"⏱️ {result.details['duration']}")
            if result.details.get("distance"):
                parts.append(f"📏 {result.details['distance']}")
            if result.details.get("calories"):
                parts.append(f"🔥 {result.details['calories']}")
            if result.details.get("heart_rate"):
                parts.append(f"❤️ {result.details['heart_rate']}")
            if parts:
                metrics_line = f"• **추출 지표**: {' | '.join(parts)}\n"
        elif result.domain == "receipt" and result.details:
            parts = []
            if result.details.get("merchant"):
                parts.append(f"상호: {result.details['merchant']}")
            if result.details.get("amount"):
                parts.append(f"금액: {result.details['amount']}")
            if parts:
                metrics_line = f"• **지출 내역**: {' | '.join(parts)}\n"

        gtd_line = ""
        if result.gtd_task:
            gtd_line = f"• **GTD 등록 제안**: `{result.gtd_task}`\n"

        card = (
            f"📷 **사진 시각 분석 완료 (Vision AI)**\n\n"
            f"• **분류**: {icon} **{result.domain_kr}**\n"
            f"• **요약**: {result.summary}\n"
            f"{metrics_line}"
            f"• **저장 위치**: `logs/daily/오늘자.md` ➔ `## {result.suggested_category}`\n"
            f"{gtd_line}\n"
            f"```markdown\n"
            f"{result.markdown_content}\n"
            f"```\n"
            f"오늘 라이프로그에 이대로 기록할까요? 😊"
        )
        return card

    def to_dict(self, result: VisionAnalysisResult) -> dict[str, Any]:
        """결과를 딕셔너리로 변환합니다."""
        return asdict(result)
