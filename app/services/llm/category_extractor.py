from __future__ import annotations

import re

from app.config import get_now
from app.services.due_date_service import DueDateService


def detect_category(text: str) -> str:
    """텍스트 내용을 분석하여 적합한 마크다운 카테고리를 추론합니다."""
    gtd_keywords = ["gtd", "할일", "할 일", "구매", "장보기", "투두", "todo", "task", "구입", "사야", "주문", "inbox", "수집함"]
    if any(k in text.lower() for k in gtd_keywords):
        return "GTD Inbox"
    workout_keywords = ["운동", "헬스", "러닝", "달리기", "벤치", "스쿼트", "풀업", "pt", "산책", "수영", "요가", "만보"]
    if any(k in text for k in workout_keywords):
        return "Workout & Health"
    # 일상 일기/서사적 표현이 있거나 긴 문장이면 우선적으로 Daily Notes & Diary로 분류
    daily_narrative_keywords = [
        "퇴근", "출근", "회사", "와이프", "아내", "남편", "가족", "친구", "식사", "저녁", "점심", "아침",
        "영화", "여행", "다녀왔", "갔다", "했어", "갔어", "먹었", "왔어", "오늘", "하루", "일과",
        "초음파", "병원", "데이트", "인수인계"
    ]
    if any(k in text for k in daily_narrative_keywords) or len(text.strip()) >= 40:
        return "Daily Notes & Diary"

    idea_keywords = ["아이디어", "영감", "깨달음", "새로운 구상", "발상", "고민"]
    if any(k in text for k in idea_keywords):
        return "Ideas & Thoughts"
    return "Daily Notes & Diary"


def extract_actionable_task(text: str) -> str:
    """
    비정형 일상 텍스트에서 실행 가능한 GTD 액션 태스크를 간결하고 명확하게 추출합니다 (ADR-014, ADR-042).
    마감일(Due Date) 및 D-Day 상대 표현 감지 시 표준 태그(~YYYY-MM-DD)를 결합합니다.
    """
    due_date, normalized_text = DueDateService.extract_due_date_from_text(text, base_date=get_now().date())
    due_tag = f" ~{due_date.strftime('%Y-%m-%d')}" if due_date else ""

    cleaned = normalized_text.strip()
    if due_date:
        cleaned = re.sub(r"~(20\d{2}[-/.])?(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b", "", cleaned).strip()

    # 1. 구매 / 장보기 패턴
    buy_match = re.search(r"([가-힣A-Za-z0-9\s,]+?)(?:을|를|도)?\s*(?:사야|구매|구입|주문|장보기|결제)", cleaned)
    if buy_match and len(buy_match.group(1).strip()) > 1:
        items = [w.strip() for w in re.split(r"[,랑와과\s]+", buy_match.group(1)) if len(w.strip()) > 1]
        if items:
            return f"{' / '.join(items[:3])} 구매{due_tag} 🛒"

    # 2. 여행 / 나들이 / 방문 / 휴가 패턴
    travel_match = re.search(r"([가-힣A-Za-z0-9]+(?:쪽|으로|에)?)\s*(?:여행|방문|나들이|휴가|가보려)", cleaned)
    if travel_match:
        raw_dest = travel_match.group(1)
        dest = re.sub(r"(쪽으로|으로|쪽|에)$", "", raw_dest).strip()
        spots = []
        for word in ["용현집", "어죽", "게국지", "맛집", "식당", "카페", "리조트", "호텔", "숙소", "펜션", "또간집"]:
            if word in cleaned and word not in spots:
                spots.append(word)
        spots_str = f" ({', '.join(spots[:3])})" if spots else ""
        if dest:
            return f"{dest} 여행 계획 및 맛집 방문{spots_str}{due_tag} 🚗🍲"
        elif spots:
            return f"{spots[0]} 방문 및 여행 계획{due_tag} 🚗🍲"

    # 3. 병원 / 건강 / 검진
    health_match = re.search(r"([가-힣A-Za-z0-9\s]+?(?:병원|검진|초음파|진료|치료|재검))", cleaned)
    if health_match:
        h_item = health_match.group(1).strip()
        return f"{h_item} 방문 및 확인{due_tag} 🏥"

    # 4. 업무 / 회의 / 프로젝트 / 문서
    work_match = re.search(r"([가-힣A-Za-z0-9\s]+?(?:회의|미팅|보고서|보고|프로젝트|기획|개발|배포|가이드라인|문서|정리))", cleaned)
    if work_match and len(work_match.group(1).strip()) > 3:
        w_item = work_match.group(1).strip()
        return f"{w_item} 진행{due_tag} 📊"

    # 5. 문장의 핵심 어절 추출
    sentences = [s.strip() for s in re.split(r"[\n.!?]", cleaned) if len(s.strip()) > 3]
    if sentences:
        candidate = sentences[-1]
        candidate = re.sub(r"(로그|gtd|일기|인박스|할일|기록|남겨|적어).*$", "", candidate).strip()
        if len(candidate) > 4:
            return f"{candidate}{due_tag} 📌"

    return f"{cleaned[:25].strip()}{due_tag} 📌"
