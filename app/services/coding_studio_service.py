from __future__ import annotations

import difflib
import logging
import os
import re
import time
from typing import Any, ClassVar

logger = logging.getLogger("watson.coding_studio")


class CodingStudioService:
    """
    웹 기반 자율 코딩 스튜디오 서비스 (Web Autonomous Coding Studio - ADR-058 / Phase 57).
    DevBot 웹 콘솔에서 소스코드 안전 조회, 실시간 Diff 생성, 코드 패치 적용,
    백업 및 롤백, 테스트 실패 시 자가 치유(Self-Healing) 진단을 전담한다.
    """

    LANGUAGE_MAP: ClassVar[dict[str, str]] = {
        ".py": "python",
        ".js": "javascript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".sh": "bash",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sql": "sql",
        ".txt": "text",
    }

    RESTRICTED_PREFIXES: tuple[str, ...] = (
        ".git",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    )

    RESTRICTED_FILENAMES: tuple[str, ...] = (
        ".env",
        ".env.example",
        ".watson.pid",
        "watson.db",
    )

    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)
        self.backups_dir = os.path.join(self.workspace_path, ".backups")
        os.makedirs(self.backups_dir, exist_ok=True)

    def resolve_safe_path(self, rel_path: str) -> str:
        """
        워크스페이스 내부의 안전한 절대 경로를 반환합니다.
        디렉토리 탈출(Path Traversal) 및 민감 파일 접근을 엄격히 차단합니다.
        """
        clean = rel_path.strip().lstrip("/\\")
        norm = os.path.normpath(clean)
        abs_path = os.path.abspath(os.path.join(self.workspace_path, norm))

        # Check path traversal
        if not abs_path.startswith(self.workspace_path):
            raise PermissionError("경로 탐색(Path Traversal)이 감지되어 파일 접근이 차단되었습니다.")

        # Check sensitive patterns
        rel = os.path.relpath(abs_path, self.workspace_path)
        parts = rel.split(os.sep)

        for p in parts:
            if p in self.RESTRICTED_PREFIXES or p in self.RESTRICTED_FILENAMES:
                raise PermissionError(f"보안상 접근이 제한된 민감 파일/디렉토리입니다: `{p}`")

        if os.path.basename(abs_path) in self.RESTRICTED_FILENAMES:
            raise PermissionError(f"보안상 접근이 제한된 설정 파일입니다: `{os.path.basename(abs_path)}`")

        return abs_path

    def list_workspace_files(self, sub_dir: str = "", max_depth: int = 3) -> list[dict[str, Any]]:
        """
        워크스페이스 내의 개발 대상 소스코드 및 문서 파일 목록을 탐색하여 반환합니다.
        """
        try:
            target_dir = self.resolve_safe_path(sub_dir) if sub_dir else self.workspace_path
        except PermissionError:
            return []

        if not os.path.isdir(target_dir):
            return []

        results: list[dict[str, Any]] = []
        base_depth = target_dir.rstrip(os.sep).count(os.sep)

        for root, dirs, files in os.walk(target_dir):
            # Prune restricted directories in-place
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in self.RESTRICTED_PREFIXES
                and d not in ("attachments", "logs")
            ]

            cur_depth = root.count(os.sep) - base_depth
            if cur_depth > max_depth:
                continue

            for f in sorted(files):
                if f.startswith(".") or f in self.RESTRICTED_FILENAMES or f.endswith((".pyc", ".db", ".log")):
                    continue

                abs_file = os.path.join(root, f)
                rel_file = os.path.relpath(abs_file, self.workspace_path)
                try:
                    stat = os.stat(abs_file)
                    size = stat.st_size
                    lines = 0
                    if size < 500_000:  # count lines for files < 500KB
                        with open(abs_file, encoding="utf-8", errors="ignore") as fp:
                            lines = sum(1 for _ in fp)

                    ext = os.path.splitext(f)[1].lower()
                    results.append({
                        "name": f,
                        "path": rel_file,
                        "size": size,
                        "lines": lines,
                        "is_dir": False,
                        "language": self.LANGUAGE_MAP.get(ext, "text"),
                    })
                except OSError as e:
                    logger.debug(f"Failed to stat file {abs_file}: {e}")

        return results

    def read_code_file(
        self,
        rel_path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> dict[str, Any]:
        """
        지정된 소스코드 파일을 안전하게 읽어 반환합니다.
        라인 범위 슬라이싱 및 언어 감지를 지원합니다.
        """
        try:
            abs_path = self.resolve_safe_path(rel_path)
        except PermissionError as e:
            return {"success": False, "error": str(e), "path": rel_path}

        if not os.path.isfile(abs_path):
            return {"success": False, "error": f"파일을 찾을 수 없습니다: `{rel_path}`", "path": rel_path}

        ext = os.path.splitext(abs_path)[1].lower()
        language = self.LANGUAGE_MAP.get(ext, "text")

        try:
            with open(abs_path, encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            s_idx = max(0, start_line - 1)
            e_idx = min(total_lines, end_line) if end_line is not None else total_lines
            sliced_lines = all_lines[s_idx:e_idx]
            content = "".join(sliced_lines)

            return {
                "success": True,
                "path": rel_path,
                "content": content,
                "total_lines": total_lines,
                "start_line": s_idx + 1,
                "end_line": e_idx,
                "size": os.path.getsize(abs_path),
                "language": language,
            }
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": f"파일 읽기 오류: {e}", "path": rel_path}

    def generate_diff_preview(
        self,
        rel_path: str,
        target_content: str,
        replacement_content: str,
    ) -> dict[str, Any]:
        """
        기존 코드와 변경 대상 코드 간의 Unified Diff 프리뷰를 생성합니다.
        """
        read_res = self.read_code_file(rel_path)
        if not read_res["success"]:
            return {"success": False, "error": read_res.get("error", "파일을 읽을 수 없습니다.")}

        original_text = read_res["content"]
        if target_content not in original_text:
            return {
                "success": False,
                "error": f"치환 대상 코드(Target Content)가 `{rel_path}` 파일 내용과 일치하지 않습니다.",
            }

        modified_text = original_text.replace(target_content, replacement_content, 1)

        diff_lines = list(difflib.unified_diff(
            original_text.splitlines(keepends=True),
            modified_text.splitlines(keepends=True),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
        ))

        diff_str = "".join(diff_lines)
        added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

        return {
            "success": True,
            "path": rel_path,
            "diff": diff_str,
            "lines_added": added,
            "lines_removed": removed,
            "has_changes": bool(diff_str.strip()),
        }

    def apply_code_patch(
        self,
        rel_path: str,
        new_content: str | None = None,
        target_content: str | None = None,
        replacement_content: str | None = None,
    ) -> dict[str, Any]:
        """
        파일에 코드 패치를 안전하게 적용하고, 이전 상태를 자동 백업합니다.
        """
        try:
            abs_path = self.resolve_safe_path(rel_path)
        except PermissionError as e:
            return {"success": False, "error": str(e), "path": rel_path}

        if not os.path.exists(abs_path):
            return {"success": False, "error": f"수정할 대상 파일이 존재하지 않습니다: `{rel_path}`"}

        try:
            with open(abs_path, encoding="utf-8") as f:
                original_text = f.read()

            # Create backup
            os.makedirs(self.backups_dir, exist_ok=True)
            safe_rel = rel_path.replace(os.sep, "_")
            backup_filename = f"{safe_rel}.{int(time.time())}.bak"
            backup_file = os.path.join(self.backups_dir, backup_filename)
            with open(backup_file, "w", encoding="utf-8") as bf:
                bf.write(original_text)

            # Determine updated content
            if new_content is not None:
                updated_text = new_content
            elif target_content is not None and replacement_content is not None:
                if target_content not in original_text:
                    return {
                        "success": False,
                        "error": "치환 대상(Target Content)이 파일 내용에 존재하지 않습니다.",
                    }
                updated_text = original_text.replace(target_content, replacement_content, 1)
            else:
                return {"success": False, "error": "수정할 내용(new_content 또는 target/replacement)이 제공되지 않았습니다."}

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(updated_text)

            # Generate diff
            diff_lines = list(difflib.unified_diff(
                original_text.splitlines(keepends=True),
                updated_text.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            ))
            diff_str = "".join(diff_lines)

            return {
                "success": True,
                "path": rel_path,
                "backup_id": backup_filename,
                "diff": diff_str,
                "message": f"`{rel_path}` 파일에 패치가 안전하게 적용되었습니다.",
            }
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": f"패치 적용 실패: {e}", "path": rel_path}

    def rollback_file(self, rel_path: str, backup_id: str | None = None) -> dict[str, Any]:
        """
        가장 최근의 백업(또는 특정 backup_id)으로부터 파일을 원상 복구합니다.
        """
        try:
            abs_path = self.resolve_safe_path(rel_path)
        except PermissionError as e:
            return {"success": False, "error": str(e), "path": rel_path}

        safe_rel = rel_path.replace(os.sep, "_")
        target_backup = None

        if backup_id:
            candidate = os.path.join(self.backups_dir, os.path.basename(backup_id))
            if os.path.isfile(candidate):
                target_backup = candidate
        else:
            # Find latest matching backup
            matching = [
                os.path.join(self.backups_dir, f)
                for f in os.listdir(self.backups_dir)
                if f.startswith(safe_rel) and f.endswith(".bak")
            ]
            if matching:
                target_backup = max(matching, key=os.path.getmtime)

        if not target_backup or not os.path.isfile(target_backup):
            return {"success": False, "error": f"`{rel_path}`에 대한 사용 가능한 백업을 찾을 수 없습니다."}

        try:
            with open(target_backup, encoding="utf-8") as bf:
                restored_text = bf.read()

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(restored_text)

            return {
                "success": True,
                "path": rel_path,
                "restored_from": os.path.basename(target_backup),
                "message": f"`{rel_path}` 파일이 백업 `{os.path.basename(target_backup)}` 시점으로 성공적으로 복원되었습니다.",
            }
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": f"롤백 복원 실패: {e}", "path": rel_path}

    def diagnose_test_failure(self, error_output: str) -> dict[str, Any]:
        """
        Pytest 실행 오류 출력을 분석하여 실패한 함수, 파일명, 예외 유형 및 자가 치유 방향을 도출합니다.
        """
        if not error_output or ("FAILED" not in error_output and "FAILURES" not in error_output and "ERROR" not in error_output and "AssertionError" not in error_output):
            return {
                "has_error": False,
                "summary": "감지된 테스트 실패나 구문 오류가 없습니다.",
                "error_type": "",
                "file": "",
                "line": 0,
                "test_func": "",
            }

        error_type = "AssertionError"
        failing_file = ""
        line_num = 0
        test_func = ""

        # Match exception name
        exc_match = re.search(r"(\w+(?:Error|Exception)):(.*)", error_output)
        if exc_match:
            error_type = exc_match.group(1)

        # Match file and line (e.g., tests/test_sample.py:10: AssertionError)
        file_match = re.search(r"(tests/[a-zA-Z0-9_\-\./]+\.py):(\d+)", error_output)
        if file_match:
            failing_file = file_match.group(1)
            line_num = int(file_match.group(2))

        # Match test function name (e.g., def test_something():)
        func_match = re.search(r"def\s+(test_[a-zA-Z0-9_]+)", error_output)
        if func_match:
            test_func = func_match.group(1)

        diagnosis = (
            f"테스트 실패 원인 분석:\n"
            f"* **예외 유형**: `{error_type}`\n"
            f"* **실패 지점**: `{failing_file}:{line_num}`\n"
            f"* **대상 함수**: `{test_func or '단위 테스트'}`\n"
            f"해당 라인의 단언문(assert) 조건 및 반환값 불일치로 인해 테스트가 중단되었습니다."
        )

        return {
            "has_error": True,
            "error_type": error_type,
            "file": failing_file,
            "line": line_num,
            "test_func": test_func,
            "summary": diagnosis,
        }

    def format_code_card(
        self,
        rel_path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> str:
        """
        DevBot 대화창에 렌더링할 소스코드 열람 마크다운 카드를 생성합니다.
        """
        res = self.read_code_file(rel_path, start_line, end_line)
        if not res["success"]:
            return f"⚠️ **코드 조회 실패**: {res.get('error', '파일을 열 수 없습니다.')}"

        lines = [
            f"### 📄 소스코드 확인: `{res['path']}`\n",
            f"* **전체 라인 수**: {res['total_lines']}줄 (표시: {res['start_line']} ~ {res['end_line']}줄)",
            f"* **파일 크기**: {res['size']:,} bytes | **언어**: `{res['language']}`\n",
            f"```{res['language']}\n{res['content'].rstrip()}\n```\n",
            (
                '<div class="dev-git-wizard">\n'
                f'  <button type="button" class="dev-btn-action" data-open-studio="{res["path"]}"><i class="fa-solid fa-laptop-code"></i> ✏️ 웹 스튜디오에서 편집</button>\n'
                f'  <button type="button" class="dev-btn-action" data-cmd="/diff"><i class="fa-solid fa-code-compare"></i> 변경점 비교 (/diff)</button>\n'
                f'  <button type="button" class="dev-btn-action" data-cmd="/test"><i class="fa-solid fa-flask"></i> 단위 테스트 (/test)</button>\n'
                f'  <button type="button" class="dev-btn-action" data-cmd="/rollback {res["path"]}"><i class="fa-solid fa-rotate-left"></i> 이전 백업 롤백 (/rollback)</button>\n'
                '</div>'
            ),
        ]
        return "\n".join(lines)

    def format_diff_card(
        self,
        rel_path: str,
        target_content: str,
        replacement_content: str,
    ) -> str:
        """
        Diff 프리뷰와 원터치 패치 적용 버튼이 포함된 카드를 생성합니다.
        """
        diff_res = self.generate_diff_preview(rel_path, target_content, replacement_content)
        if not diff_res["success"]:
            return f"⚠️ **Diff 생성 실패**: {diff_res.get('error', '차이점을 생성할 수 없습니다.')}"

        lines = [
            f"### 🔍 코드 변경 Diff 프리뷰: `{rel_path}`\n",
            f"* **변경 라인**: 🟢 +{diff_res['lines_added']}줄 / 🔴 -{diff_res['lines_removed']}줄\n",
            f"```diff\n{diff_res['diff'].strip()}\n```\n",
            (
                '<div class="dev-git-wizard">\n'
                f'  <button type="button" class="dev-btn-action" data-open-studio="{rel_path}"><i class="fa-solid fa-laptop-code"></i> ✏️ 웹 스튜디오에서 열기</button>\n'
                '  <button type="button" class="dev-btn-action" data-cmd="/test"><i class="fa-solid fa-flask"></i> 단위 테스트 검증 (/test)</button>\n'
                '  <button type="button" class="dev-btn-action" data-cmd="/lint"><i class="fa-solid fa-broom"></i> 린트 검사 (/lint)</button>\n'
                '</div>'
            ),
        ]
        return "\n".join(lines)

    def format_patch_card(
        self,
        rel_path: str,
        backup_id: str,
        diff: str,
        test_passed: bool = True,
        explanation: str = "",
    ) -> str:
        """
        코드 패치 적용 결과 및 툴체인 연계 카드를 생성합니다.
        """
        test_badge = "✅ 단위 테스트 통과 (All Passed)" if test_passed else "❌ 단위 테스트 실패 감지"
        lines = [
            f"### 🛠️ 자율 코드 구현 & 패치 완료: `{rel_path}`\n",
        ]
        if explanation:
            lines.append(f"{explanation.strip()}\n")

        lines.extend([
            f"* **적용 파일**: `{rel_path}`",
            f"* **자동 백업 ID**: `{backup_id}`",
            f"* **단위 테스트 검증**: {test_badge}\n",
        ])

        if diff.strip():
            lines.append(f"```diff\n{diff.strip()}\n```\n")

        lines.append(
            
                '<div class="dev-git-wizard">\n'
                f'  <button type="button" class="dev-btn-action" data-open-studio="{rel_path}"><i class="fa-solid fa-laptop-code"></i> ✏️ 웹 스튜디오에서 확인</button>\n'
                '  <button type="button" class="dev-btn-action" data-cmd="/test"><i class="fa-solid fa-flask"></i> 테스트 재검증 (/test)</button>\n'
                '  <button type="button" class="dev-btn-action" data-cmd="/lint"><i class="fa-solid fa-broom"></i> 린트 검사 (/lint)</button>\n'
                f'  <button type="button" class="dev-btn-action" data-cmd="/rollback {rel_path}"><i class="fa-solid fa-rotate-left"></i> 즉시 롤백 (/rollback)</button>\n'
                '  <button type="button" class="dev-btn-action" data-cmd="/commit"><i class="fa-solid fa-code-commit"></i> 커밋 추천 (/commit)</button>\n'
                '</div>'
            
        )
        return "\n".join(lines)
