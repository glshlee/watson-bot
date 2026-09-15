"""
Vision AI 멀티모달 시각 지능 서비스 단위 테스트 (ADR-044).
"""

import os
import tempfile

from app.services.llm_provider import LLMProvider
from app.services.vision_service import VisionAnalysisResult, VisionService


def test_vision_workout_analysis():
    """운동 인증샷(러닝, 헬스) 메트릭 추출 및 Workout & Health 섹션 분류 검증."""
    vision_service = VisionService()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake_image_bytes_workout")
        tmp_path = f.name

    try:
        caption = "오늘 저녁 야외 러닝 5.2km 420kcal 28분 완주"
        result = vision_service.analyze_image(
            image_path=tmp_path,
            user_caption=caption,
            image_rel_path="attachments/2026/09/workout.jpg",
        )

        assert result.domain == "workout"
        assert result.domain_kr == "운동 인증"
        assert result.suggested_category == "Workout & Health"
        assert "5.2 km" in result.details.get("distance", "")
        assert "420 kcal" in result.details.get("calories", "")
        assert "28 분" in result.details.get("duration", "")
        assert "운동 인증" in result.markdown_content
        assert "![운동 인증](/attachments/2026/09/workout.jpg)" in result.markdown_content
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_vision_receipt_analysis_and_masking():
    """영수증 지출 분석, 금액/상호 추출, 카드번호 마스킹 및 GTD 가계부 태스크 검증."""
    vision_service = VisionService()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake_image_bytes_receipt")
        tmp_path = f.name

    try:
        caption = "용현집 어죽 결제 영수증 18,000원"
        result = vision_service.analyze_image(
            image_path=tmp_path,
            user_caption=caption,
            image_rel_path="attachments/2026/09/receipt.jpg",
        )

        assert result.domain == "receipt"
        assert result.domain_kr == "영수증/지출"
        assert "18,000원" in result.details.get("amount", "")
        assert "용현집" in result.details.get("merchant", "")
        assert result.details.get("masked_card") == "****-****-****-****"
        assert result.gtd_task is not None
        assert "가계부 정리" in result.gtd_task
        assert "18,000원" in result.gtd_task
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_vision_meal_and_memo_analysis():
    """식사/맛집 및 필기/메모 도메인 분석 검증."""
    vision_service = VisionService()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake_image_bytes_meal")
        tmp_path = f.name

    try:
        # 식사 테스트
        res_meal = vision_service.analyze_image(
            image_path=tmp_path,
            user_caption="점심으로 얼큰한 순대국밥 맛있게 먹었어",
            image_rel_path="attachments/2026/09/meal.jpg",
        )
        assert res_meal.domain == "meal"
        assert res_meal.domain_kr == "식사/맛집"
        assert "식사 & 미식 저널" in res_meal.markdown_content

        # 메모 테스트
        res_memo = vision_service.analyze_image(
            image_path=tmp_path,
            user_caption="오늘 오후 기획 회의 화이트보드 아이디어 메모 정리",
            image_rel_path="attachments/2026/09/memo.jpg",
        )
        assert res_memo.domain == "memo"
        assert res_memo.domain_kr == "메모/손글씨"
        assert res_memo.gtd_task is not None
        assert "태스크 구체화" in res_memo.gtd_task
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_vision_draft_card_and_fallback():
    """초안 카드 포맷팅 및 파일 부재 시 안전 폴백 검증."""
    vision_service = VisionService()

    # 1. 파일이 존재하지 않는 경우 폴백
    res_missing = vision_service.analyze_image(
        image_path="/path/does/not/exist/photo.jpg",
        user_caption="그냥 일상 사진",
    )
    assert res_missing.domain == "general"
    assert "존재하지 않습니다" in res_missing.details.get("error", "")

    # 2. 초안 카드 포맷 검증
    sample = VisionAnalysisResult(
        domain="workout",
        domain_kr="운동 인증",
        summary="야외 러닝 5km 완료",
        details={"duration": "25분", "distance": "5.0 km", "calories": "350 kcal"},
        suggested_category="Workout & Health",
        markdown_content="- [19:00] 🏃 야외 러닝 5.0 km 완주",
        gtd_task=None,
        image_rel_path="attachments/2026/09/run.jpg",
    )
    card = vision_service.format_draft_card(sample)
    assert "사진 시각 분석 완료" in card
    assert "운동 인증" in card
    assert "5.0 km" in card
    assert "이대로 기록할까요" in card


def test_llm_provider_vision_intent():
    """LLMProvider에서 /vision 명령어 입력 시 vision_inspect 인텐트 분류 검증."""
    provider = LLMProvider()
    res = provider.analyze_and_respond("/vision attachments/2026/09/run.jpg 야외 러닝 5km")
    assert res.intent == "vision_inspect"
    assert "attachments/2026/09/run.jpg" in (res.log_content or "")


def test_vision_api_endpoints():
    """Vision API 엔드포인트(/api/vision/analyze 및 /api/vision/upload-and-log) 검증."""
    import io

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    file_bytes = b"fake_jpeg_image_data_for_testing"
    files = {"file": ("running.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    data = {"caption": "야외 러닝 5km 400kcal 완료"}

    # 1. POST /api/vision/analyze
    res_analyze = client.post("/api/vision/analyze", files=files, data=data)
    assert res_analyze.status_code == 200
    res_data = res_analyze.json()
    assert res_data["status"] == "success"
    assert res_data["data"]["domain"] == "workout"
    assert "draft_card" in res_data

    # 2. POST /api/vision/upload-and-log (with pending preview)
    files2 = {"file": ("receipt.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    data2 = {
        "caption": "용현집 어죽 결제 18000원 영수증",
        "session_id": "test_vision_session",
        "auto_confirm": "false",
    }
    res_log = client.post("/api/vision/upload-and-log", files=files2, data=data2)
    assert res_log.status_code == 200
    log_data = res_log.json()
    assert log_data["status"] == "success"
    assert log_data["logged"] is False
    assert "draft_card" in log_data

