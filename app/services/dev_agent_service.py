import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_now
from app.services.agent_service import AgentService
from app.services.llm_provider import LLMProvider
from app.services.session_service import SessionService
from app.services.settings_service import SettingsService

logger = logging.getLogger("watson.dev_agent")


class DevAgentService:
    """
    개발 전담 AI 에이전트 (DevBot / Dev Agent) 서비스 (ADR-018 준수).
    코드베이스 분석, Git 상태/Diff/커밋 조회, 터미널 도구 실행 및 소프트웨어 엔지니어링 대화를 수행한다.
    """

    def __init__(self, db: Session, workspace_path: str = "."):
        self.db = db
        self.workspace_path = os.path.abspath(workspace_path)
        self.session_service = SessionService(db)
        self.llm_provider = LLMProvider()

    def _get_agent_service(self) -> AgentService:
        """현재 설정된 GTD 저장소 경로를 기반으로 AgentService 인스턴스를 반환합니다."""
        gtd_path = SettingsService().get_gtd_path()
        return AgentService(base_dir=gtd_path)

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
            "updated_at": datetime.now(timezone.utc).isoformat(),
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

    def _recommend_commit_messages(self) -> str:
        """현재 git diff 및 상태를 기반으로 추천 커밋 메시지를 생성합니다."""
        status = self._run_git_cmd(["status", "-s"])
        if status == "(내용 없음)":
            return "현재 작업 트리가 깨끗하여 추천할 커밋 변경점이 없습니다. (Working tree clean)"

        changed_lines = [line.strip() for line in status.splitlines() if line.strip()]
        sample_files = ", ".join([line.split()[-1] for line in changed_lines[:4]])

        return (
            f"### 💡 추천 커밋 메시지 (Conventional Commits)\n\n"
            f"현재 변경 중인 파일({len(changed_lines)}개: `{sample_files}` 등)을 기반으로 추천된 메시지입니다.\n"
            f"원하시는 메시지를 선택하여 `/commit <메시지>` 명령으로 실행해 주세요:\n\n"
            f"1. `/commit feat(dev): implement interactive dev toolchain (/test, /lint)`\n"
            f"2. `/commit fix(dev): enhance DevBot engineering capabilities and prompt alignment`\n"
            f"3. `/commit refactor(dev): streamline dev agent tools and roadmap integration`\n"
        )

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
                        f"```text\n{commit_res['details']}\n```\n"
                    )
                else:
                    ai_response = f"⚠️ **Git 커밋 실패**: {commit_res['message']}"
            else:
                ai_response = self._recommend_commit_messages()

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

        elif lower_msg in ["/help", "help", "도움말", "명령어", "도구"]:
            action_type = "tool_help"
            ai_response = (
                "### 🛠️ DevBot 지원 엔지니어링 도구 안내\n\n"
                "* **🌿 Git 워크스페이스 도구**:\n"
                "  * `/status`: 현재 작업 트리 상태 및 브랜치 확인\n"
                "  * `/diff`: 변경 코드(Staged/Unstaged) 실시간 비교\n"
                "  * `/log`: 최근 7건의 Git 커밋 히스토리 확인\n"
                "  * `/branch`: 브랜치 목록 조회\n"
                "* **📋 라이프로그 & GTD 실시간 열람 (ADR-022)**:\n"
                "  * `/today`: 오늘자 작성된 일일 로그(`logs/daily/YYYY-MM-DD.md`) 즉시 열람\n"
                "  * `/gtd`: 현재 연결된 GTD 수집함(`inbox.md`) 및 다음 행동(`next_actions.md`) 마크다운 직접 확인\n"
                "* **🧪 자동화 CI & 검증 도구**:\n"
                "  * `/test [경로]`: pytest 단위 테스트 비동기 실행 (예: `/test`, `/test tests/test_auth.py`)\n"
                "  * `/lint`: Ruff 린터 및 Mypy 타입 검사 즉시 실행\n"
                "* **🚀 Git 커밋 관리**:\n"
                "  * `/commit <메시지>`: 현재 변경된 코드를 스테이징 및 커밋\n"
                "  * `/commit`: 현재 변경점을 분석하여 Conventional Commit 메시지 추천\n"
                "* **💡 엔지니어링 인공지능 질의**:\n"
                "  * \"다음에 뭘 개발하면 좋을지 추천해줘\", \"이 코드 구조 개선해줘\" 등 자유로운 기술 상담"
            )

        else:
            # 5. General software engineering query via LLM
            action_type = "ai_reasoning"
            ws_status = self.get_workspace_status()
            roadmap_summary = self._get_roadmap_summary()

            repo_context = (
                f"[프로젝트 현황 컨텍스트]\n"
                f"- 워크스페이스: {ws_status['workspace']}\n"
                f"- 브랜치: {ws_status['branch']}\n"
                f"- 변경 중인 파일 수: {ws_status['changed_files_count']}\n"
                f"- 최근 커밋: {ws_status['last_commit']}\n"
            )
            if roadmap_summary:
                repo_context += f"- 최근 완료 단계 및 로드맵:\n{roadmap_summary}\n"

            dev_system_prompt = (
                "너는 왓슨(Watson) 프로젝트의 개발 및 DevOps를 전담하는 전문 AI 소프트웨어 엔지니어 'DevBot'이다.\n"
                "Python, FastAPI, SQLite, Git 자동화, LLM 에이전트 아키텍처에 능통하다.\n"
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
                if self.llm_provider.agy_path:
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
