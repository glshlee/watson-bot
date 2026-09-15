import logging
import os
import re
from datetime import datetime
from typing import Any, ClassVar

from app.config import get_now

logger = logging.getLogger("watson.search")


class SearchService:
    """
    라이프로그 및 GTD 전체 텍스트/키워드 고속 검색 서비스 (ADR-043).
    
    일일 로그(logs/daily/*.md) 및 GTD 파일(gtd/*.md, inbox.md 등), 
    기타 마크다운 저장소 문서를 대상으로 키워드 매칭과 하이라이트 스니펫을 추출합니다.
    """

    WEEKDAYS_KO: ClassVar[list[str]] = ["월", "화", "수", "목", "금", "토", "일"]

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(os.path.expanduser(base_dir))

    def _get_searchable_files(self) -> list[tuple[str, str | None]]:
        """
        검색 대상 마크다운 파일 목록을 반환합니다.
        반환 형태: [(절대경로, 날짜문자열 'YYYY-MM-DD' 또는 None)]
        """
        results: list[tuple[str, str | None]] = []

        if not os.path.exists(self.base_dir):
            return results

        # 1. 일일 로그 디렉토리 (우선순위 최고)
        daily_dir = os.path.join(self.base_dir, "logs", "daily")
        if os.path.exists(daily_dir):
            for fname in sorted(os.listdir(daily_dir), reverse=True):
                if fname.endswith(".md"):
                    fpath = os.path.join(daily_dir, fname)
                    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})", fname)
                    date_str = date_match.group(1) if date_match else None
                    results.append((fpath, date_str))

        # 2. GTD 디렉토리 및 루트 GTD 파일
        gtd_candidates = [
            os.path.join(self.base_dir, "gtd", "inbox.md"),
            os.path.join(self.base_dir, "gtd", "next_actions.md"),
            os.path.join(self.base_dir, "gtd", "projects.md"),
            os.path.join(self.base_dir, "gtd", "someday_maybe.md"),
            os.path.join(self.base_dir, "gtd", "waiting_for.md"),
            os.path.join(self.base_dir, "inbox.md"),
            os.path.join(self.base_dir, "next_actions.md"),
        ]
        for fpath in gtd_candidates:
            if os.path.exists(fpath) and (fpath, None) not in results:
                results.append((fpath, None))

        # 3. 추가 폴더 내 마크다운 파일 (01_work, 02_personal, 03_side_projects 등)
        for sub_dir_name in ["01_work", "02_personal", "03_side_projects", "common"]:
            sub_path = os.path.join(self.base_dir, sub_dir_name)
            if os.path.exists(sub_path):
                for root, _, files in os.walk(sub_path):
                    for fname in sorted(files):
                        if fname.endswith(".md"):
                            fpath = os.path.join(root, fname)
                            if (fpath, None) not in results:
                                results.append((fpath, None))

        return results

    def _highlight_snippet(self, line: str, terms: list[str], max_len: int = 220) -> str:
        """라인 내에서 검색어를 볼드(**단어**) 처리하고 적절한 길이로 스니펫을 생성합니다."""
        clean_line = line.strip()
        if not clean_line:
            return ""

        # 하이라이트 정규식 빌드 (대소문자 무시)
        escaped_terms = [re.escape(t) for t in terms if t.strip()]
        if not escaped_terms:
            return clean_line[:max_len]

        pattern = re.compile(f"({'|'.join(escaped_terms)})", re.IGNORECASE)

        # 길이 트리밍
        if len(clean_line) > max_len:
            # 첫 번째 검색어 위치 찾기
            first_match = pattern.search(clean_line)
            if first_match:
                start_idx = max(0, first_match.start() - 40)
                end_idx = min(len(clean_line), start_idx + max_len)
                trimmed = clean_line[start_idx:end_idx]
                if start_idx > 0:
                    trimmed = "..." + trimmed
                if end_idx < len(clean_line):
                    trimmed = trimmed + "..."
                clean_line = trimmed
            else:
                clean_line = clean_line[:max_len] + "..."

        # 볼드 하이라이트 치환
        def _replace_match(m: re.Match) -> str:
            return f"**{m.group(1)}**"

        return pattern.sub(_replace_match, clean_line)

    def search(
        self,
        query: str,
        max_results: int = 10,
        max_per_file: int = 3,
    ) -> list[dict[str, Any]]:
        """
        주어진 키워드로 마크다운 라이프로그와 GTD 문서를 고속 검색합니다.
        
        Args:
            query: 검색 질의어 (공백 구분 다중 키워드 지원)
            max_results: 최대 반환 결과 개수 (기본 10)
            max_per_file: 단일 파일당 최대 매칭 행 수 (기본 3)
        """
        clean_query = query.strip().strip("'\"")
        if not clean_query:
            return []

        terms = [t.lower() for t in clean_query.split() if t.strip()]
        if not terms:
            return []

        searchable_files = self._get_searchable_files()
        matched_results: list[dict[str, Any]] = []

        now_date = get_now().date()

        for fpath, date_str in searchable_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to read file {fpath} during search: {e}")
                continue

            rel_path = os.path.relpath(fpath, self.base_dir)
            current_section = "일반"
            file_matches = 0

            # 일자 객체 파싱 (있는 경우)
            file_date = None
            if date_str:
                try:
                    file_date = datetime.strptime(date_str, "%Y-%m-%d").date()  # noqa: DTZ007
                except ValueError:
                    file_date = None

            for idx, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    continue

                # 마크다운 섹션 헤더 추적
                if stripped.startswith("#"):
                    current_section = stripped.lstrip("#").strip()
                    # 헤더 자체에만 매칭되는 경우는 본문 라인이 아니므로 건너뛰거나 섹션으로 보존
                    continue

                line_lower = stripped.lower()

                # 모든 검색어가 현재 라인(또는 섹션명+라인)에 포함되어 있는지 확인 (AND 조건)
                combined_text = f"{current_section.lower()} {line_lower}"
                if all(term in combined_text for term in terms):
                    file_matches += 1
                    snippet = self._highlight_snippet(stripped, terms)

                    # 관련도 점수 계산
                    score = 10
                    # 전체 쿼리가 라인에 통째로 들어있는 경우 가산점
                    if clean_query.lower() in line_lower:
                        score += 30
                    # 일일 로그 가산점
                    if date_str:
                        score += 15
                        if file_date:
                            days_diff = (now_date - file_date).days
                            # 최근 30일 이내일수록 추가 가산점
                            if 0 <= days_diff <= 30:
                                score += max(0, 30 - days_diff)
                    elif "inbox" in rel_path.lower() or "next_actions" in rel_path.lower():
                        score += 10

                    matched_results.append({
                        "file_path": rel_path,
                        "date": date_str,
                        "file_date": file_date,
                        "section": current_section,
                        "line_number": idx + 1,
                        "line_content": stripped,
                        "snippet": snippet,
                        "score": score,
                    })

                    if file_matches >= max_per_file:
                        break

        # 정렬: 
        # 1. 일자 있는 항목은 최신순 우선 고려 + 점수 결합
        def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
            dt = item.get("date") or "1970-01-01"
            score = item.get("score", 0)
            return (score, dt)

        matched_results.sort(key=_sort_key, reverse=True)
        return matched_results[:max_results]

    def format_search_results_card(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> str:
        """
        검색 결과를 깔끔한 마크다운 카드 형태로 포맷팅합니다.
        """
        clean_query = query.strip().strip("'\"")

        if not results:
            return (
                f"🔍 **[라이프로그 & GTD 검색 결과]**\n"
                f"*검색어: \"{clean_query}\"*\n\n"
                f"❌ 일치하는 기록을 찾지 못했습니다.\n\n"
                f"💡 **검색 팁:**\n"
                f"• 더 짧거나 대표적인 키워드로 검색해 보세요. (예: `/search 서산`, `/search 미역국`, `/search 운동`)\n"
                f"• 특정 날짜의 전체 기록을 보려면 `/today YYYY-MM-DD`를 입력하세요."
            )

        card_lines = [
            f"🔍 **[라이프로그 & GTD 검색 결과 (총 {len(results)}건)]**",
            f"*검색어: \"{clean_query}\"*\n",
        ]

        for r in results:
            date_str = r.get("date")
            rel_path = r.get("file_path", "")
            section = r.get("section", "기록")
            snippet = r.get("snippet", "")

            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")  # noqa: DTZ007
                    weekday_ko = self.WEEKDAYS_KO[dt.weekday()]
                    date_badge = f"📅 **{date_str} ({weekday_ko})**"
                except ValueError:
                    date_badge = f"📅 **{date_str}**"
            else:
                date_badge = f"📁 **{rel_path}**"

            card_lines.append(f"{date_badge} · `{section}`")
            card_lines.append(f"> {snippet}\n")

        card_lines.append("---")
        card_lines.append("💡 *특정 날짜의 전체 일기를 열람하려면 `/today YYYY-MM-DD` 명령어를 사용하세요.*")

        return "\n".join(card_lines)
