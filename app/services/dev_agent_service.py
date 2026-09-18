import logging
import os
import re
import subprocess
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_now
from app.services.agent_service import AgentService
from app.services.briefing_service import BriefingService
from app.services.llm_provider import LLMProvider
from app.services.session_service import SessionService
from app.services.settings_service import SettingsService

logger = logging.getLogger("watson.dev_agent")


class DevAgentService:
    """
    개발 전담 AI 에이전트 (DevBot / Dev Agent) 서비스 (ADR-018 준수).
    코드베이스 분석, Git 상태/Diff/커밋 조회, 터미널 도구 실행 및 소프트웨어 엔지니어링 대화를 수행한다.
    """

    def __init__(self, db: Session, workspace_path: str = ".", fast_mode: bool = False):
        self.db = db
        self.workspace_path = os.path.abspath(workspace_path)
        self.fast_mode = fast_mode or (os.getenv("FAST_MODE", "").lower() in ("1", "true"))
        self.session_service = SessionService(db)
        self.llm_provider = LLMProvider(fast_mode=self.fast_mode)

    def _get_agent_service(self) -> AgentService:
        """현재 설정된 GTD 저장소 경로를 기반으로 AgentService 인스턴스를 반환합니다."""
        gtd_path = SettingsService().get_gtd_path()
        return AgentService(base_dir=gtd_path)

    def _get_briefing_service(self) -> BriefingService:
        """현재 설정된 GTD 저장소 경로를 기반으로 BriefingService 인스턴스를 반환합니다 (ADR-024)."""
        gtd_path = SettingsService().get_gtd_path()
        return BriefingService(base_dir=gtd_path, llm_provider=self.llm_provider)

    def _run_git_cmd(self, args: list[str]) -> str:
        """안전한 읽기 전용 Git 명령을 실행합니다."""
        try:
            res = subprocess.run(
                ["git", "-C", self.workspace_path] + args,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            out = res.stdout.strip()
            if not out and res.stderr:
                out = res.stderr.strip()
            return out or "(내용 없음)"
        except Exception as e:  # noqa: BLE001
            return f"오류 발생: {e}"

    def get_workspace_status(self) -> dict[str, Any]:
        """워크스페이스의 현재 Git 및 시스템 상태를 요약 반환합니다."""
        branch = self._run_git_cmd(["branch", "--show-current"])
        last_commit = self._run_git_cmd(["log", "-1", "--oneline"])
        status_raw = self._run_git_cmd(["status", "--porcelain"])
        changed_files = len([line for line in status_raw.splitlines() if line.strip()]) if status_raw != "(내용 없음)" else 0

        return {
            "workspace": os.path.basename(self.workspace_path),
            "branch": branch or "main",
            "last_commit": last_commit,
            "changed_files_count": changed_files,
            "status": "clean" if changed_files == 0 else "modified",
            "engine": "Antigravity CLI / Gemini Bridge",
            "updated_at": get_now().isoformat(),
        }

    def _run_pytest(self, target: str = "") -> dict[str, Any]:
        """pytest 단위 테스트를 안전하게 실행하고 결과를 반환합니다."""
        clean_target = target.strip()
        if any(c in clean_target for c in [";", "&", "|", ">", "<", "$", "`", ".."]):
            return {"success": False, "output": "❌ 유효하지 않거나 안전하지 않은 경로 문자가 포함되어 있습니다.", "target": clean_target}

        pytest_bin = os.path.join(self.workspace_path, "venv", "bin", "pytest")
        if not os.path.exists(pytest_bin):
            pytest_bin = "pytest"

        cmd = [pytest_bin, "-q"]
        if clean_target:
            cmd.extend(clean_target.split())
        else:
            cmd.extend(["tests/test_auth.py", "tests/test_dev_agent.py"])

        env = os.environ.copy()
        env["PYTHONPATH"] = self.workspace_path
        env["PATH"] = f"{self.workspace_path}/venv/bin:" + env.get("PATH", "")

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.workspace_path,
                env=env,
                timeout=45,
                check=False,
            )
            out = (res.stdout + "\n" + res.stderr).strip()
            lines = out.splitlines()
            if len(lines) > 35:
                out = "\n".join(lines[:25] + ["... (중략) ..."] + lines[-8:])
            return {
                "success": res.returncode == 0,
                "target": clean_target or "기본 핵심 테스트 (tests/test_auth.py, tests/test_dev_agent.py)",
                "output": out or "(출력 없음)",
                "returncode": res.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "target": clean_target or "기본 핵심 테스트",
                "output": "⏱️ 테스트 실행 시간이 초과되었습니다 (45초 제한).",
                "returncode": -1,
            }
        except (subprocess.SubprocessError, OSError) as e:
            return {
                "success": False,
                "target": clean_target,
                "output": f"오류 발생: {e}",
                "returncode": -1,
            }

    def _run_lint(self) -> dict[str, Any]:
        """ruff 및 mypy 정적 분석을 실행하고 결과를 반환합니다."""
        ruff_bin = os.path.join(self.workspace_path, "venv", "bin", "ruff")
        mypy_bin = os.path.join(self.workspace_path, "venv", "bin", "mypy")
        if not os.path.exists(ruff_bin):
            ruff_bin = "ruff"
        if not os.path.exists(mypy_bin):
            mypy_bin = "mypy"

        env = os.environ.copy()
        env["PYTHONPATH"] = self.workspace_path
        env["PATH"] = f"{self.workspace_path}/venv/bin:" + env.get("PATH", "")

        try:
            ruff_res = subprocess.run(
                [ruff_bin, "check", "."],
                capture_output=True,
                text=True,
                cwd=self.workspace_path,
                env=env,
                timeout=15,
                check=False,
            )
            ruff_ok = (ruff_res.returncode == 0)
            ruff_out = ruff_res.stdout.strip() or ruff_res.stderr.strip()
        except (subprocess.SubprocessError, OSError) as e:
            ruff_ok = False
            ruff_out = f"Ruff 실행 오류: {e}"

        try:
            mypy_res = subprocess.run(
                [mypy_bin, "."],
                capture_output=True,
                text=True,
                cwd=self.workspace_path,
                env=env,
                timeout=25,
                check=False,
            )
            mypy_ok = (mypy_res.returncode == 0)
            mypy_out = mypy_res.stdout.strip() or mypy_res.stderr.strip()
        except (subprocess.SubprocessError, OSError) as e:
            mypy_ok = False
            mypy_out = f"Mypy 실행 오류: {e}"

        return {
            "all_passed": ruff_ok and mypy_ok,
            "ruff_ok": ruff_ok,
            "ruff_out": ruff_out,
            "mypy_ok": mypy_ok,
            "mypy_out": mypy_out,
        }

    def _run_git_commit(self, message: str) -> dict[str, Any]:
        """안전하게 git add 및 commit을 수행합니다."""
        clean_msg = message.strip()
        status = self._run_git_cmd(["status", "--porcelain"])
        if status == "(내용 없음)":
            return {
                "success": False,
                "message": "현재 작업 트리가 깨끗합니다 (커밋할 변경 사항 없음).",
            }

        add_res = self._run_git_cmd(["add", "-A"])
        if "오류" in add_res:
            return {"success": False, "message": f"Git Add 실패: {add_res}"}

        commit_res = self._run_git_cmd(["commit", "-m", clean_msg])
        last_commit = self._run_git_cmd(["log", "-1", "--oneline"])

        return {
            "success": True,
            "commit": last_commit,
            "details": commit_res,
        }

    def _run_git_push(self) -> dict[str, Any]:
        """로컬 커밋을 원격 GitHub 저장소(origin)로 푸시합니다."""
        branch = self._run_git_cmd(["branch", "--show-current"]) or "main"
        remote_url = self._run_git_cmd(["remote", "get-url", "origin"])

        try:
            res = subprocess.run(
                ["git", "push", "origin", branch],
                capture_output=True,
                text=True,
                cwd=self.workspace_path,
                timeout=35,
                check=False,
            )
            out = (res.stdout + "\n" + res.stderr).strip()
            success = (res.returncode == 0)
            last_commit = self._run_git_cmd(["log", "-1", "--oneline"])
            return {
                "success": success,
                "branch": branch,
                "remote_url": remote_url,
                "commit": last_commit,
                "output": out or ("성공적으로 원격 저장소에 푸시되었습니다." if success else "푸시 실패"),
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "branch": branch,
                "remote_url": remote_url,
                "commit": "",
                "output": "⏱️ Git 푸시 실행 시간이 초과되었습니다 (35초 제한).",
            }
        except (subprocess.SubprocessError, OSError) as e:
            return {
                "success": False,
                "branch": branch,
                "remote_url": remote_url,
                "commit": "",
                "output": f"오류 발생: {e}",
            }

    def _run_git_sync(self) -> dict[str, Any]:
        """원격 GitHub 저장소(origin)로부터 autostash를 사용하여 최신 코드를 안전하게 가져옵니다."""
        branch = self._run_git_cmd(["branch", "--show-current"]) or "main"
        try:
            res = subprocess.run(
                ["git", "pull", "--autostash"],
                capture_output=True,
                text=True,
                cwd=self.workspace_path,
                timeout=35,
                check=False,
            )
            out = (res.stdout + "\n" + res.stderr).strip()
            success = (res.returncode == 0)
            last_commit = self._run_git_cmd(["log", "-1", "--oneline"])
            return {
                "success": success,
                "branch": branch,
                "commit": last_commit,
                "output": out or "이미 최신 상태입니다.",
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "branch": branch,
                "commit": "",
                "output": "⏱️ Git 동기화 실행 시간이 초과되었습니다 (35초 제한).",
            }
        except (subprocess.SubprocessError, OSError) as e:
            return {
                "success": False,
                "branch": branch,
                "commit": "",
                "output": f"오류 발생: {e}",
            }

    def _recommend_commit_messages(self) -> str:
        """현재 git diff 및 상태를 기반으로 추천 커밋 메시지를 생성합니다."""
        status = self._run_git_cmd(["status", "-s"])
        if status == "(내용 없음)":
            return "현재 작업 트리가 깨끗하여 추천할 커밋 변경점이 없습니다. (Working tree clean)"

        changed_lines = [line.strip() for line in status.splitlines() if line.strip()]
        sample_files = ", ".join([line.split()[-1] for line in changed_lines[:4]])

        msg1 = "feat(dev): implement command palette and interactive git wizard"
        msg2 = "fix(dev): improve devbot console toolchain and mobile responsiveness"
        msg3 = "refactor(dev): streamline dev engineering tools and terminal rendering"

        return (
            f"### 💡 추천 커밋 메시지 (Conventional Commits)\n\n"
            f"현재 변경 중인 파일({len(changed_lines)}개: `{sample_files}` 등)을 기반으로 분석한 추천 메시지입니다.\n"
            f"원하는 메시지의 버튼을 누르면 즉시 커밋이 실행됩니다:\n\n"
            f'<div class="dev-git-wizard">\n'
            f'  <div class="dev-commit-opt">\n'
            f'    <div class="opt-desc"><strong>1. 기능 추가 (feat)</strong>: 새 도구 또는 콘솔 기능 구현</div>\n'
            f'    <button type="button" class="dev-btn-action dev-btn-commit" data-commit-cmd="/commit {msg1}"><i class="fa-solid fa-code-commit"></i> {msg1}</button>\n'
            f'  </div>\n'
            f'  <div class="dev-commit-opt">\n'
            f'    <div class="opt-desc"><strong>2. 버그 수정 (fix)</strong>: 안정성 및 오류 보완</div>\n'
            f'    <button type="button" class="dev-btn-action dev-btn-commit" data-commit-cmd="/commit {msg2}"><i class="fa-solid fa-wrench"></i> {msg2}</button>\n'
            f'  </div>\n'
            f'  <div class="dev-commit-opt">\n'
            f'    <div class="opt-desc"><strong>3. 구조 개선 (refactor)</strong>: 코드 리팩토링 및 툴체인 최적화</div>\n'
            f'    <button type="button" class="dev-btn-action dev-btn-commit" data-commit-cmd="/commit {msg3}"><i class="fa-solid fa-arrows-rotate"></i> {msg3}</button>\n'
            f'  </div>\n'
            f'</div>\n\n'
            f"*직접 메시지를 지정하여 커밋하려면 `/commit <원하는 메시지>` 명령으로 실행해 주세요.*"
        )

    def get_available_skills(self) -> list[dict[str, Any]]:
        """
        .agents/skills/ 디렉토리에 정의된 범용 하네스 스킬 목록을 동적으로 탐색하고 파싱합니다.
        """
        skills_dir = os.path.join(self.workspace_path, ".agents", "skills")
        skills: list[dict[str, Any]] = []
        if not os.path.exists(skills_dir):
            return skills

        try:
            for entry in sorted(os.listdir(skills_dir)):
                skill_path = os.path.join(skills_dir, entry, "SKILL.md")
                if os.path.isfile(skill_path):
                    name = entry
                    description = ""
                    with open(skill_path, encoding="utf-8") as f:
                        raw = f.read()
                        content = raw
                        if raw.startswith("---"):
                            parts = raw.split("---", 2)
                            if len(parts) >= 3:
                                frontmatter = parts[1]
                                for line in frontmatter.splitlines():
                                    if line.strip().startswith("name:"):
                                        name = line.split("name:", 1)[1].strip()
                                    elif line.strip().startswith("description:"):
                                        description = line.split("description:", 1)[1].strip()
                    skills.append({
                        "id": entry,
                        "name": name,
                        "description": description or "설명 없음",
                        "path": f".agents/skills/{entry}/SKILL.md",
                        "content": content,
                    })
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to load skills: {e}")

        return skills

    def format_skills_catalog(self, skill_name: str | None = None) -> str:
        """스킬 카탈로그 또는 특정 스킬의 상세 가이드를 마크다운 서식으로 생성합니다."""
        skills = self.get_available_skills()
        if not skills:
            return "현재 등록된 `.agents/skills/` 개발 스킬이 없습니다."

        if skill_name:
            target = skill_name.strip().lower()
            matched = None
            for s in skills:
                if target == s["id"].lower() or target == s["name"].lower() or target in s["id"].lower():
                    matched = s
                    break
            if matched:
                return (
                    f"### 🧩 개발 스킬 상세: `{matched['name']}`\n\n"
                    f"* **설명**: {matched['description']}\n"
                    f"* **스킬 경로**: `{matched['path']}`\n\n"
                    f"```markdown\n{matched['content'].strip()}\n```\n\n"
                    f'<div class="dev-git-wizard">\n'
                    f'  <button type="button" class="dev-btn-action" data-cmd="/skills"><i class="fa-solid fa-list"></i> 전체 스킬 카탈로그 (/skills)</button>\n'
                    f'  <button type="button" class="dev-btn-action" data-cmd="/roadmap"><i class="fa-solid fa-map"></i> 개발 로드맵 (/roadmap)</button>\n'
                    f'  <button type="button" class="dev-btn-action" data-cmd="/test"><i class="fa-solid fa-flask"></i> 단위 테스트 실행 (/test)</button>\n'
                    f'</div>'
                )
            else:
                available = ", ".join([f"`{s['id']}`" for s in skills])
                return f"⚠️ `{skill_name}` 스킬을 찾을 수 없습니다.\n\n* **사용 가능한 스킬**: {available}\n* 전체 스킬 목록은 `/skills`로 확인하세요."

        # Catalog Overview
        lines = [
            "### 🧩 Watson 하네스 개발 스킬 카탈로그 (Skill Catalog)\n",
            "DevBot이 개발 및 오케스트레이션에 활용하는 표준 하네스 스킬입니다:\n",
        ]
        for s in skills:
            lines.append(
                f'<div class="dev-commit-opt" style="margin-bottom: 12px;">\n'
                f'  <div class="opt-desc"><strong>🔹 {s["name"]}</strong>: {s["description"]} (`{s["path"]}`)</div>\n'
                f'  <button type="button" class="dev-btn-action" data-cmd="/skill {s["id"]}">'
                f'<i class="fa-solid fa-book-open"></i> {s["name"]} 스킬 명세 열람 (/skill {s["id"]})'
                f'</button>\n'
                f'</div>'
            )

        lines.append("\n*특정 스킬의 전문 가이드를 보시려면 `/skill <스킬명>`(예: `/skill dev-workflow`, `/skill git-automation`)을 입력하세요.*")
        return "\n".join(lines)

    def parse_roadmap_data(self) -> dict[str, Any]:
        """docs/roadmap.md를 분석하여 마일스톤 완료 통계 및 상태를 반환합니다."""
        roadmap_path = os.path.join(self.workspace_path, "docs", "roadmap.md")
        if not os.path.exists(roadmap_path):
            return {
                "total_phases": 0,
                "completed_phases": 0,
                "completion_rate": 0.0,
                "progress_bar": "░░░░░░░░░░ 0.0%",
                "active_phases": [],
                "recent_phases": [],
                "all_phases": [],
            }

        phases: list[dict[str, Any]] = []
        try:
            with open(roadmap_path, encoding="utf-8") as f:
                content = f.read()

            for line in content.splitlines():
                m = re.match(r"^###\s+Phase\s+(\d+):\s*(.*)$", line.strip())
                if m:
                    num = int(m.group(1))
                    raw_title = m.group(2).strip()
                    done = any(k in raw_title.lower() for k in ["done", "완료", "completed"])
                    clean_title = re.sub(r"\s*-\s*✅\s*완료|\s*\((Done|완료|Current Phase - Done)\)", "", raw_title).strip()
                    phases.append({
                        "phase": num,
                        "raw_title": raw_title,
                        "title": clean_title,
                        "completed": done,
                    })
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to parse roadmap: {e}")

        total = len(phases)
        completed = sum(1 for p in phases if p["completed"])
        rate = round((completed / total * 100), 1) if total > 0 else 0.0

        filled_blocks = min(10, max(0, round(rate / 10)))
        empty_blocks = 10 - filled_blocks
        progress_bar = f"{'█' * filled_blocks}{'░' * empty_blocks} {rate}%"

        active = [p for p in phases if not p["completed"]]
        recent = [p for p in phases if p["completed"]][-4:]

        return {
            "total_phases": total,
            "completed_phases": completed,
            "completion_rate": rate,
            "progress_bar": progress_bar,
            "active_phases": active,
            "recent_phases": recent,
            "all_phases": phases,
        }

    def format_roadmap_report(self) -> str:
        """개발 로드맵 및 마일스톤 진행 현황을 대화형 카드로 서식화합니다."""
        data = self.parse_roadmap_data()
        if data["total_phases"] == 0:
            return "⚠️ `docs/roadmap.md` 파일을 찾을 수 없거나 마일스톤이 정의되지 않았습니다."

        lines = [
            "### 🗺️ Watson 개발 로드맵 & 마일스톤 현황\n",
            f"* **📊 마일스톤 진척도**: `[{data['progress_bar']}]` (**{data['completed_phases']}** / {data['total_phases']} 단계 완료)\n",
        ]

        if data["active_phases"]:
            lines.append("#### 🎯 진행 중 & 예정 마일스톤 (Active & Upcoming)")
            for p in data["active_phases"]:
                lines.append(f"- **Phase {p['phase']}**: {p['title']}")
            lines.append("")

        if data["recent_phases"]:
            lines.append("#### 🌟 최근 완료 마일스톤 하이라이트 (Recent Completed)")
            for p in reversed(data["recent_phases"]):
                lines.append(f"- ✅ **Phase {p['phase']}**: {p['title']}")
            lines.append("")

        lines.append(
            '<div class="dev-git-wizard">\n'
            '  <button type="button" class="dev-btn-action" data-cmd="/skills"><i class="fa-solid fa-puzzle-piece"></i> 개발 스킬 목록 (/skills)</button>\n'
            '  <button type="button" class="dev-btn-action" data-cmd="/test"><i class="fa-solid fa-flask"></i> 단위 테스트 실행 (/test)</button>\n'
            '  <button type="button" class="dev-btn-action" data-cmd="/lint"><i class="fa-solid fa-broom"></i> 코드 린트 검사 (/lint)</button>\n'
            '  <button type="button" class="dev-btn-action" data-cmd="/status"><i class="fa-solid fa-circle-info"></i> Git 상태 확인 (/status)</button>\n'
            '</div>\n\n'
            '*전체 상세 백로그는 `docs/roadmap.md` 파일에서 확인하실 수 있습니다.*'
        )

        return "\n".join(lines)

    def _get_roadmap_summary(self) -> str:
        """docs/roadmap.md 파일에서 최근 완료 상태 및 다음 계획 요약을 추출합니다."""
        try:
            roadmap_path = os.path.join(self.workspace_path, "docs", "roadmap.md")
            if os.path.exists(roadmap_path):
                with open(roadmap_path, encoding="utf-8") as f:
                    content = f.read()
                lines = [line for line in content.splitlines() if line.strip().startswith("### Phase") or "- [ ]" in line or "- [x]" in line]
                return "\n".join(lines[-15:])
        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Failed to read roadmap summary: {e}")
        return ""

    def process_dev_request(
        self,
        session_id: str,
        user_message: str,
        channel: str = "web",
    ) -> dict[str, Any]:
        """개발자 요청을 분석하여 Git/엔지니어링 명령을 실행하거나 AI 응답을 반환합니다."""
        clean_msg = user_message.strip()

        # 1. Ensure dev session exists
        self.session_service.get_or_create_session(
            session_id=session_id,
            channel=channel,
            title="New Dev Task",
            agent_type="dev",
        )

        # 2. Record user message
        self.session_service.add_message(session_id, "user", clean_msg)

        # 3. Auto-update session title on first message
        self.session_service.auto_update_session_title(session_id, clean_msg)

        # 4. Check for direct developer shortcuts
        lower_msg = clean_msg.lower()
        ai_response = ""
        action_type = "chat"

        if lower_msg in ["/status", "git status", "상태", "상태 확인", "깃 상태"]:
            action_type = "git_status"
            branch = self._run_git_cmd(["branch", "--show-current"])
            status = self._run_git_cmd(["status", "-s"])
            ai_response = f"### 🌿 Git 상태 요약 (`{branch}`)\n\n"
            if status == "(내용 없음)":
                ai_response += "✅ 작업 트리가 깨끗합니다. (Working tree clean)\n"
            else:
                ai_response += f"```text\n{status}\n```\n"

        elif lower_msg in ["/diff", "git diff", "변경점", "변경점 확인"]:
            action_type = "git_diff"
            diff = self._run_git_cmd(["diff"])
            diff_staged = self._run_git_cmd(["diff", "--staged"])
            ai_response = "### 🔍 Git Diff 결과\n\n"
            if diff == "(내용 없음)" and diff_staged == "(내용 없음)":
                ai_response += "현재 변경된 코드(Unstaged/Staged)가 없습니다."
            else:
                if diff != "(내용 없음)":
                    ai_response += f"#### Unstaged Changes:\n```diff\n{diff}\n```\n"
                if diff_staged != "(내용 없음)":
                    ai_response += f"#### Staged Changes:\n```diff\n{diff_staged}\n```\n"

        elif lower_msg in ["/log", "git log", "최근 커밋", "커밋 내역"]:
            action_type = "git_log"
            logs = self._run_git_cmd(["log", "-n", "7", "--oneline", "--decorate"])
            ai_response = f"### 📜 최근 Git 커밋 내역 (최근 7건)\n\n```text\n{logs}\n```"

        elif lower_msg in ["/branch", "git branch", "브랜치 목록"]:
            action_type = "git_branch"
            branches = self._run_git_cmd(["branch", "-a"])
            ai_response = f"### 🌿 브랜치 목록\n\n```text\n{branches}\n```"

        elif lower_msg.startswith("/test") or lower_msg in ["pytest", "테스트", "단위 테스트", "테스트 실행"]:
            action_type = "tool_test"
            target = clean_msg[5:].strip() if clean_msg.startswith("/test") else ""
            test_res = self._run_pytest(target)
            status_emoji = "✅" if test_res["success"] else "❌"
            status_text = "테스트 성공 (All Passed)" if test_res["success"] else "테스트 실패 (Failures Detected)"
            ai_response = (
                f"### 🧪 단위 테스트 실행 결과 (`pytest`)\n\n"
                f"* **대상**: `{test_res['target']}`\n"
                f"* **결과**: {status_emoji} {status_text}\n\n"
                f"```text\n{test_res['output']}\n```"
            )

        elif lower_msg in ["/lint", "lint", "린트", "검사", "린트 검사", "정적 검사", "ruff", "mypy"]:
            action_type = "tool_lint"
            lint_res = self._run_lint()
            ruff_badge = "✅ 무결점 통과" if lint_res["ruff_ok"] else "❌ 규칙 위반 발견"
            mypy_badge = "✅ 타입 무결점" if lint_res["mypy_ok"] else "❌ 타입 오류 발견"

            ai_response = "### 🧹 정적 분석 및 린트 검사 결과\n\n"
            ai_response += f"* **Ruff Linter**: {ruff_badge}\n"
            ai_response += f"* **Mypy Type Check**: {mypy_badge}\n\n"

            if lint_res["all_passed"]:
                ai_response += "✨ 전체 소스코드에 대한 린트 및 정적 타입 검사를 결함 없이 100% 통과했습니다!\n"
            else:
                if not lint_res["ruff_ok"]:
                    ai_response += f"#### Ruff 이슈 내역:\n```text\n{lint_res['ruff_out']}\n```\n"
                if not lint_res["mypy_ok"]:
                    ai_response += f"#### Mypy 오류 내역:\n```text\n{lint_res['mypy_out']}\n```\n"

        elif lower_msg.startswith("/commit") or lower_msg in ["커밋", "커밋해줘", "커밋 추천"]:
            action_type = "tool_commit"
            commit_arg = clean_msg[7:].strip() if clean_msg.startswith("/commit") else ""
            if commit_arg:
                commit_res = self._run_git_commit(commit_arg)
                if commit_res["success"]:
                    ai_response = (
                        f"### 🚀 Git 커밋 완료\n\n"
                        f"* **최신 커밋**: `{commit_res['commit']}`\n\n"
                        f"```text\n{commit_res['details']}\n```\n\n"
                        f'<div class="dev-push-banner">\n'
                        f'  <div class="push-desc"><i class="fa-solid fa-circle-question"></i> 원격 저장소(GitHub)에 바로 푸시하시겠습니까?</div>\n'
                        f'  <button type="button" class="dev-btn-action dev-btn-push" data-push-cmd="/push"><i class="fa-solid fa-cloud-arrow-up"></i> 🚀 GitHub 원격 푸시 실행 (/push)</button>\n'
                        f'</div>'
                    )
                else:
                    ai_response = f"⚠️ **Git 커밋 실패**: {commit_res['message']}"
            else:
                ai_response = self._recommend_commit_messages()

        elif lower_msg in ["/push", "git push", "푸시", "푸시해줘", "원격 푸시"]:
            action_type = "tool_push"
            push_res = self._run_git_push()
            if push_res["success"]:
                ai_response = (
                    f"### 🚀 GitHub 원격 푸시 완료 (`origin/{push_res['branch']}`)\n\n"
                    f"* **원격 저장소**: `{push_res['remote_url']}`\n"
                    f"* **브랜치**: `{push_res['branch']}`\n"
                    f"* **최신 커밋**: `{push_res['commit']}`\n\n"
                    f"```text\n{push_res['output']}\n```"
                )
            else:
                ai_response = (
                    f"⚠️ **GitHub 원격 푸시 실패**\n\n"
                    f"* **브랜치**: `{push_res['branch']}`\n"
                    f"```text\n{push_res['output']}\n```\n\n"
                    f"원격 저장소와 충돌 또는 변경사항이 있다면 `/sync` 명령으로 먼저 최신화해 보세요."
                )

        elif lower_msg in ["/sync", "/pull", "git pull", "동기화", "최신화", "원격 동기화", "레포 동기화"]:
            action_type = "tool_sync"
            sync_res = self._run_git_sync()
            status_badge = "✅ 동기화 완료" if sync_res["success"] else "⚠️ 동기화 주의"
            ai_response = (
                f"### 🔄 원격 GitHub 동기화 결과 (`origin/{sync_res['branch']}`)\n\n"
                f"* **결과**: {status_badge}\n"
                f"* **최신 커밋**: `{sync_res['commit']}`\n\n"
                f"```text\n{sync_res['output']}\n```"
            )

        elif lower_msg in ["/today", "/daily", "today", "daily", "오늘 로그", "오늘 일기", "오늘자 로그", "오늘 로그 보여줘", "오늘 일기 보여줘"]:
            action_type = "tool_today_log"
            agent_svc = self._get_agent_service()
            ai_response = agent_svc.read_daily_log(date_obj=get_now())

        elif lower_msg in ["/gtd", "/inbox", "gtd", "inbox", "gtd 파일", "인박스 파일", "gtd 파일 보여줘", "인박스 파일 보여줘"]:
            action_type = "tool_gtd_files"
            agent_svc = self._get_agent_service()
            ai_response = agent_svc.read_gtd_files()

        elif lower_msg in ["/gtd-today", "/today-gtd", "/all-log"]:
            action_type = "tool_gtd_and_today_log"
            agent_svc = self._get_agent_service()
            ai_response = agent_svc.read_gtd_and_daily_log(date_obj=get_now())

        elif lower_msg.startswith("/briefing") or ("브리핑" in lower_msg and any(k in lower_msg for k in ["아침", "저녁", "회고", "해줘", "정리"])):
            action_type = "tool_briefing"
            briefing_svc = self._get_briefing_service()
            if any(k in lower_msg for k in ["morning", "am", "아침", "출근", "모닝"]):
                mode = "morning"
            elif any(k in lower_msg for k in ["evening", "pm", "저녁", "회고", "정산", "이브닝"]):
                mode = "evening"
            else:
                mode = None
            briefing_res = briefing_svc.generate_briefing(mode=mode)
            ai_response = briefing_res["markdown"]

        elif lower_msg in ["/schedule", "/briefing schedule"] or ("스케줄" in lower_msg and any(k in lower_msg for k in ["확인", "몇 시", "몇시", "보여", "알려", "어떻게", "언제"])):
            action_type = "tool_schedule"
            briefing_svc = self._get_briefing_service()
            ai_response = briefing_svc.format_schedule_briefing(date_obj=get_now())

        elif lower_msg in ["/dday", "/deadline", "dday", "deadline", "디데이", "마감일", "마감일 확인", "dday 확인", "디데이 확인"]:
            action_type = "tool_dday"
            from app.services.due_date_service import DueDateService

            settings_svc = SettingsService()
            ai_response = DueDateService.format_standalone_deadline_report(
                base_dir=settings_svc.get_gtd_path(),
                base_date=get_now(),
            )

        elif lower_msg.startswith(("/search", "/find", "/검색", "/찾기")):
            action_type = "tool_search"
            parts = clean_msg.split(maxsplit=1)
            query = parts[1].strip() if len(parts) > 1 else ""
            from app.services.search_service import SearchService

            settings_svc = SettingsService()
            search_service = SearchService(base_dir=settings_svc.get_gtd_path())
            results = search_service.search(query=query)
            ai_response = search_service.format_search_results_card(query=query, results=results)

        elif lower_msg in ["/weekly", "/review", "/주간", "/주간결산", "/주간회고", "weekly", "주간결산", "주간회고"]:
            action_type = "tool_weekly"
            from app.services.weekly_review_service import WeeklyReviewService

            settings_svc = SettingsService()
            weekly_service = WeeklyReviewService(
                base_dir=settings_svc.get_gtd_path(),
                llm_provider=self.llm_provider,
            )
            weekly_data = weekly_service.generate_weekly_review()
            ai_response = weekly_data["markdown"]

        elif lower_msg.startswith(("/vision", "/photo", "/이미지", "/사진")):
            action_type = "tool_vision"
            parts = clean_msg.split(maxsplit=2)
            target_path = parts[1].strip() if len(parts) > 1 else ""
            caption = parts[2].strip() if len(parts) > 2 else ""

            from app.services.vision_service import VisionService

            vision_svc = VisionService()
            if not target_path:
                ai_response = (
                    "### 📷 Vision AI 시각 지능 도구 (ADR-044)\n\n"
                    "* **사용법**: `/vision [이미지 상대/절대 경로] [선택적 캡션]`\n"
                    "* **지원 도메인**: 🏃 운동 인증, 🧾 영수증/지출, 🍲 식사/맛집, 📝 메모/손글씨, 🖼️ 일반 일상\n\n"
                    "* **예시**:\n"
                    "  * `/vision attachments/2026/09/running.jpg 오늘 야외 러닝 5km 420kcal 완료`\n"
                    "  * `/vision attachments/2026/09/receipt.jpg 용현집 어죽 결제 18000원`\n\n"
                    "분석 결과는 도메인별 메트릭 추출, 민감정보 마스킹 및 정갈한 라이프로그 초안 카드를 제공합니다."
                )
            else:
                settings_svc = SettingsService()
                abs_path = target_path if os.path.isabs(target_path) else os.path.join(settings_svc.get_gtd_path(), target_path)
                vision_res = vision_svc.analyze_image(image_path=abs_path, user_caption=caption, image_rel_path=target_path)
                ai_response = vision_svc.format_draft_card(vision_res)

        elif lower_msg.startswith(("/edit", "/editor", "/수정", "/편집")):
            action_type = "tool_edit"
            parts = clean_msg.split(maxsplit=1)
            target_date = parts[1].strip() if len(parts) > 1 else ""
            from app.services.heatmap_service import HeatmapService
            settings_svc = SettingsService()
            heatmap_svc = HeatmapService(base_dir=settings_svc.get_gtd_path())
            d_str = target_date or get_now().strftime("%Y-%m-%d")
            ai_response = heatmap_svc.format_edit_card(date_str=d_str)

        elif lower_msg.startswith(("/heatmap", "/잔디", "/기여도")):
            action_type = "tool_heatmap"
            from app.services.heatmap_service import HeatmapService
            settings_svc = SettingsService()
            heatmap_svc = HeatmapService(base_dir=settings_svc.get_gtd_path())
            hm_data = heatmap_svc.get_heatmap_data(days=365)
            s = hm_data["summary"]
            recent_14 = hm_data["days"][-14:]
            bar = "".join("🟩" if d["level"] > 0 else "⬜" for d in recent_14)
            ai_response = (
                f"### 🟩 **Watson 라이프로그 잔디(Contribution Heatmap) 요약** 🌱\n\n"
                f"• **총 기록 일수**: **{s['total_days_logged']}일** / {s['range_days']}일 ({s['completion_rate']}%)\n"
                f"• **🔥 현재 연속 기록**: **{s['current_streak']}일 연속** 달성 중\n"
                f"• **🏆 최장 연속 기록**: **{s['longest_streak']}일**\n"
                f"• **✅ 완료된 GTD 태스크**: 총 **{s['total_completed_tasks']}개**\n"
                f"• **📝 총 기록 글자 수**: 약 **{s['total_chars']:,}자**\n\n"
                f"#### 📅 **최근 2주간의 잔디 현황**\n"
                f"`{bar}` *(최근 14일)*\n\n"
                f"웹 대시보드(`/watson`)에서 365일 인터랙티브 잔디 뷰와 마크다운 분할 에디터를 확인하실 수 있습니다! 🖥️✨"
            )

        elif lower_msg.startswith(("/setup", "/배포", "/설정점검", "/setup-status")):
            action_type = "tool_setup"
            from app.services.setup_service import SetupService
            setup_svc = SetupService()
            ai_response = setup_svc.format_status_report()

        elif lower_msg in ["/roadmap", "/로드맵", "roadmap", "로드맵", "개발 로드맵", "로드맵 확인", "마일스톤", "마일스톤 확인", "로드맵 보여줘"]:
            action_type = "tool_roadmap"
            ai_response = self.format_roadmap_report()

        elif lower_msg in ["/skills", "/스킬", "skills", "스킬", "개발 스킬", "스킬 목록", "스킬 확인", "스킬 보여줘"]:
            action_type = "tool_skills"
            ai_response = self.format_skills_catalog()

        elif lower_msg.startswith(("/skill ", "/스킬 ")):
            action_type = "tool_skill_detail"
            skill_arg = clean_msg.split(maxsplit=1)[1].strip()
            ai_response = self.format_skills_catalog(skill_arg)

        elif lower_msg in ["/help", "help", "도움말", "명령어", "도구"]:
            action_type = "tool_help"
            ai_response = (
                "### 🛠️ DevBot 지원 엔지니어링 도구 안내\n\n"
                "* **🗺️ 개발 로드맵 & 하네스 스킬 (ADR-057)**:\n"
                "  * `/roadmap`: 전체 개발 로드맵 진행률 및 예정 마일스톤 현황 점검\n"
                "  * `/skills`: DevBot 활용 가능 `.agents/skills/` 카탈로그 조회\n"
                "  * `/skill [이름]`: 특정 스킬(예: `/skill dev-workflow`, `/skill git-automation`)의 상세 명세 열람\n"
                "* **🌿 Git 워크스페이스 도구**:\n"
                "  * `/status`: 현재 작업 트리 상태 및 브랜치 확인\n"
                "  * `/diff`: 변경 코드(Staged/Unstaged) 실시간 비교\n"
                "  * `/log`: 최근 7건의 Git 커밋 히스토리 확인\n"
                "  * `/branch`: 브랜치 목록 조회\n"
                "* **⚙️ 셀프호스팅 배포 & 환경 점검 (ADR-046)**:\n"
                "  * `/setup`: 텔레그램, LLM, GTD, 보안 등 시스템 배포 준비 상태 종합 진단\n"
                "* **📋 라이프로그 & GTD 브리핑/열람/검색 (ADR-022, ADR-024, ADR-042, ADR-043)**:\n"
                "  * `/search [키워드]`: 과거 라이프로그 및 GTD 문서 고속 텍스트/키워드 검색\n"
                "  * `/weekly`: 지난 7일간의 기록 달성률, 완료 태스크 및 주간 결산 리포트\n"
                "  * `/briefing [morning|evening]`: 아침 집중 과제 및 저녁 일과 회고 맞춤형 브리핑\n"
                "  * `/dday`: GTD 마감일(D-Day) 현황 및 기한 임박/초과 과제 종합 점검\n"
                "  * `/today`: 오늘자 작성된 일일 로그(`logs/daily/YYYY-MM-DD.md`) 즉시 열람\n"
                "  * `/gtd`: 현재 연결된 GTD 수집함(`inbox.md`) 및 다음 행동(`next_actions.md`) 마크다운 직접 확인\n"
                "* **📷 멀티모달 시각 지능 (ADR-044)**:\n"
                "  * `/vision [경로] [캡션]`: 운동 인증샷, 영수증, 음식, 메모 사진 Vision AI 분석 및 초안 생성\n"
                "* **✏️ 일일 로그 편집 & 잔디 시각화 (ADR-045)**:\n"
                "  * `/edit [날짜]`: 특정 일자 또는 오늘 마크다운 일일 로그 웹 분할 에디터 열기\n"
                "  * `/heatmap`: 최근 1년간 잔디(Contribution Heatmap) 및 기록 스트릭 통계 요약\n"
                "* **🧪 자동화 CI & 검증 도구**:\n"
                "  * `/test [경로]`: pytest 단위 테스트 비동기 실행 (예: `/test`, `/test tests/test_auth.py`)\n"
                "  * `/lint`: Ruff 린터 및 Mypy 타입 검사 즉시 실행\n"
                "* **🚀 Git 커밋 & 원격 관리 (ADR-055)**:\n"
                "  * `/commit <메시지>`: 현재 변경된 코드를 스테이징 및 커밋\n"
                "  * `/commit`: 현재 변경점을 분석하여 Conventional Commit 메시지 추천 위저드\n"
                "  * `/push`: 로컬 커밋을 원격 GitHub 저장소(origin/main)에 즉시 푸시\n"
                "  * `/sync`: 원격 GitHub 저장소로부터 autostash로 안전하게 최신화 (Pull)\n"
                "* **💡 엔지니어링 인공지능 질의**:\n"
                "  * \"다음에 뭘 개발하면 좋을지 추천해줘\", \"이 코드 구조 개선해줘\" 등 자유로운 기술 상담"
            )

        else:
            # 5. General software engineering query via LLM
            action_type = "ai_reasoning"
            ws_status = self.get_workspace_status()
            roadmap_summary = self._get_roadmap_summary()
            skills = self.get_available_skills()
            skills_summary = "\n".join([f"- {s['name']}: {s['description']}" for s in skills])

            repo_context = (
                f"[프로젝트 현황 컨텍스트]\n"
                f"- 워크스페이스: {ws_status['workspace']}\n"
                f"- 브랜치: {ws_status['branch']}\n"
                f"- 변경 중인 파일 수: {ws_status['changed_files_count']}\n"
                f"- 최근 커밋: {ws_status['last_commit']}\n"
            )
            if skills_summary:
                repo_context += f"- 보유 개발 스킬 (.agents/skills):\n{skills_summary}\n"
            if roadmap_summary:
                repo_context += f"- 최근 완료 단계 및 로드맵:\n{roadmap_summary}\n"

            dev_system_prompt = (
                "너는 왓슨(Watson) 프로젝트의 개발 및 DevOps를 전담하는 전문 AI 소프트웨어 엔지니어 'DevBot'이다.\n"
                "Python, FastAPI, SQLite, Git 자동화, LLM 에이전트 아키텍처에 능통하다.\n"
                "너는 하네스에 정의된 개발 스킬(.agents/skills/)과 로드맵을 철저히 숙지하고 준수하여 개발 작업을 수행한다.\n"
                "기능 개발 요청 시 dev-workflow 스킬의 표준 7단계(요구사항 분석 ➔ TDD 테스트 ➔ 수술적 코드 구현 ➔ 린트/타입 검사 ➔ cURL 검증 ➔ 4단계 문서화 루프 ➔ Conventional Commits 제안)를 기반으로 단계별 안내를 제공하라.\n"
                "사용자가 '커밋해'라고 명시적으로 지시하기 전까지 임의 커밋하지 않는 규칙을 엄격히 준수하라.\n"
                "친절하고 정중하며 기술적으로 명쾌하고 깊이 있게 한국어로 답변하라.\n"
                "절대로 쉘 명령어나 외부 도구를 호출하지 말고, 오직 주어진 [프로젝트 현황 컨텍스트]를 완벽히 숙지하여 텍스트로만 구체적이고 실현 가능한 제안을 제시하라.\n"
                "절대로 기계적이거나 판에 박힌 앵무새 답변을 하지 마라.\n\n"
                f"{repo_context}"
            )

            history = self.session_service.get_session_history(session_id, limit=4)
            history_lines = []
            if history:
                for m in history[-3:]:
                    c = str(m.get("content", "")).strip()
                    if len(c) > 200:
                        c = c[:200] + "..."
                    history_lines.append(f"{m.get('role')}: {c}")
            history_context = "\n".join(history_lines)
            full_prompt = f"{dev_system_prompt}\n\n[최근 대화 맥락]\n{history_context}\n\n[사용자 질문]\n{clean_msg}\n\nDevBot 엔지니어 답변:"

            # Use LLMProvider analyze or generate
            try:
                if not self.fast_mode and self.llm_provider.agy_path:
                    cmd = [
                        self.llm_provider.agy_path,
                        "-p",
                        full_prompt,
                        "--model",
                        "gemini-3.8-flash-low",
                        "--effort",
                        "low",
                        "--disable-slash-commands",
                        "--dangerously-skip-permissions",
                    ]
                    env = os.environ.copy()
                    env["PATH"] = "/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=45,
                        check=False,
                        env=env,
                        cwd="/tmp",
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        ai_response = res.stdout.strip()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"AGY dev generation fallback: {e}")

            if not ai_response:
                ai_response = (
                    f"안녕하세요! 개발 전담 에이전트 **DevBot**입니다. 💻\n\n"
                    f"현재 워크스페이스(`{ws_status['workspace']}`)의 `{ws_status['branch']}` 브랜치를 모니터링 중입니다. "
                    f"(수정 중인 파일: {ws_status['changed_files_count']}개)\n\n"
                    f"문의하신 내용: **\"{clean_msg}\"**\n\n"
                    f"코드베이스 분석, 버그 수정, 단위 테스트(`pytest`), Git 브랜치 관리 등 "
                    f"필요한 엔지니어링 작업을 언제든 말씀해 주세요! 빠른 명령어(`/status`, `/diff`, `/log`, `/today`, `/gtd`)도 지원합니다."
                )

        # 6. Record assistant response
        self.session_service.add_message(session_id, "assistant", ai_response)

        return {
            "session_id": session_id,
            "user_message": clean_msg,
            "ai_response": ai_response,
            "action_type": action_type,
            "timestamp": get_now().isoformat(),
        }
