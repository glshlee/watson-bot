import logging
import os
import re

import git
from git.exc import GitError

from app.config import get_now, settings

logger = logging.getLogger("watson.git")


class GitService:
    """
    Git 자동화 서비스 (ADR-001, ADR-007, ADR-064 준수).
    지정된 repo_path(독립 GTD 레포지토리)의 로컬 변경 감지, 일괄 커밋(Batch Commit) 및
    온디맨드/야간 자동 푸시(Nightly Auto-Push)를 담당합니다.
    """

    def __init__(self, repo_path: str | None = None):
        self.repo_path = os.path.abspath(os.path.expanduser(repo_path or settings.REPO_PATH))
        self.repo: git.Repo | None = None
        try:
            self.repo = git.Repo(self.repo_path)
        except GitError:
            self.repo = None

    @property
    def is_git_repo(self) -> bool:
        return self.repo is not None

    def get_dirty_files(self) -> list[str]:
        """현재 작업 트리에 수정되었거나 새로 추가된(미커밋) 상대 파일 경로 목록을 반환합니다 (ADR-064)."""
        if not self.repo:
            return []
        try:
            status_out = self.repo.git.status("--porcelain", "-uall")
            files: list[str] = []
            for line in status_out.splitlines():
                if len(line) > 3:
                    raw_path = line[3:].strip().strip('"')
                    if " -> " in raw_path:
                        raw_path = raw_path.split(" -> ")[-1].strip()
                    if raw_path and raw_path not in files:
                        files.append(raw_path)
            return files
        except (GitError, TypeError, OSError) as e:
            logger.debug("Failed to inspect dirty files: %s", e)
            return []

    def build_batch_commit_message(
        self,
        dirty_files: list[str] | None = None,
        prefix: str = "docs(lifelog & gtd)",
    ) -> str:
        """누적된 로컬 변경 파일 목록을 기반으로 깔끔한 일괄 커밋 메시지를 생성합니다 (ADR-064)."""
        files = dirty_files if dirty_files is not None else self.get_dirty_files()
        date_str = get_now().strftime("%Y-%m-%d")
        if not files:
            return f"{prefix}: batch update ({date_str})"
        basenames = [os.path.basename(f) for f in files[:3]]
        suffix = f", +{len(files) - 3} more" if len(files) > 3 else ""
        file_summary = ", ".join(basenames) + suffix
        return f"{prefix}: batch update {len(files)} file(s) ({date_str}) [{file_summary}]"


    def sync_and_commit_push(self, commit_message: str, file_path: str | None = None) -> bool:
        if not self.repo:
            logger.info(f"Target directory {self.repo_path} is not a git repository. Skipping git commit.")
            return False

        try:
            # 1. Add file
            if file_path:
                if os.path.isabs(file_path):
                    rel_file = os.path.relpath(file_path, self.repo.working_tree_dir)
                    self.repo.index.add([rel_file])
                else:
                    self.repo.index.add([file_path])
            else:
                self.repo.git.add(A=True)

            # 2. Commit if there are changes
            if self.repo.is_dirty(untracked_files=True):
                self.repo.index.commit(commit_message)
                logger.info(f"Committed to {self.repo_path}: {commit_message}")

            # 3. Pull & Push if origin remote exists
            if self.repo.remotes:
                remote_name = (
                    settings.GIT_REMOTE_NAME
                    if settings.GIT_REMOTE_NAME in self.repo.remotes
                    else self.repo.remotes[0].name
                )
                branch = self.repo.active_branch.name
                # (3-1) Pull with rebase & autostash to handle untracked/unstaged changes safely
                try:
                    self.repo.git.pull(remote_name, branch, rebase=True, autostash=True)
                except (GitError, TypeError, OSError) as pe:
                    logger.warning(f"[Git Remote Pull Warning in sync]: {pe}")

                # (3-2) Push to remote
                try:
                    self.repo.git.push(remote_name, branch)
                    logger.info(f"Pushed branch '{branch}' to remote '{remote_name}' in {self.repo_path}")
                except (GitError, TypeError, OSError) as psh_err:
                    logger.error(f"[Git Remote Push Error in sync]: {psh_err}")

            return True
        except GitError as e:
            logger.error(f"[GitService Error]: {e}")
            return False

    def pull(self) -> tuple[bool, str]:
        """
        원격 저장소로부터 최신 커밋을 안전하게 가져옵니다 (ADR-009).
        로컬 변경사항이 있어도 autostash를 통해 보존하며 충돌 없이 병합합니다.
        """
        if not self.repo:
            return False, f"지정된 디렉토리({self.repo_path})가 Git 저장소가 아닙니다."
        if not self.repo.remotes:
            return False, "연결된 원격 저장소(remote)가 없습니다."

        try:
            remote_name = (
                settings.GIT_REMOTE_NAME
                if settings.GIT_REMOTE_NAME in self.repo.remotes
                else self.repo.remotes[0].name
            )
            branch = self.repo.active_branch.name

            pull_output = self.repo.git.pull(remote_name, branch, rebase=True, autostash=True)
            logger.info(f"Pulled latest changes for {self.repo_path}: {pull_output}")

            if "Already up to date" in pull_output:
                return True, f"원격 저장소('{remote_name}/{branch}')와 이미 최신 상태입니다."
            return True, f"원격 저장소('{remote_name}/{branch}')로부터 최신 변경사항을 성공적으로 동기화했습니다."
        except (GitError, TypeError) as e:
            logger.warning(f"[GitService Pull Warning]: {e}")
            return False, f"Git 동기화 중 오류 발생: {e}"

    def push(
        self,
        auto_commit_dirty: bool = True,
        commit_message: str | None = None,
    ) -> tuple[bool, str]:
        """
        원격 저장소(GitHub)로 로컬 커밋들을 안전하게 푸시합니다 (ADR-011, ADR-064).
        - auto_commit_dirty=True(기본값)일 때 미커밋된 로컬 작업(is_dirty)이 존재하면
          자동으로 일괄 커밋(Batch Commit)을 먼저 수행한 뒤 pull(--rebase --autostash) 및 push를 집행합니다.
        """
        if not self.repo:
            return False, f"지정된 디렉토리({self.repo_path})가 Git 저장소가 아닙니다."
        if not self.repo.remotes:
            return False, "연결된 원격 저장소(remote)가 없습니다."

        try:
            auto_commit_note = ""
            if auto_commit_dirty and self.repo.is_dirty(untracked_files=True):
                c_ok, c_msg = self.commit(commit_message=commit_message)
                if c_ok:
                    auto_commit_note = f"• {c_msg}\n"

            remote_name = (
                settings.GIT_REMOTE_NAME
                if settings.GIT_REMOTE_NAME in self.repo.remotes
                else self.repo.remotes[0].name
            )
            branch = self.repo.active_branch.name

            # 1. 푸시 전 원격 변경사항 안전하게 동기화 (rebase + autostash)
            try:
                self.repo.git.pull(remote_name, branch, rebase=True, autostash=True)
            except (GitError, TypeError, OSError) as pe:
                logger.warning(f"[Git Push Pre-Pull Warning]: {pe}")

            # 2. 로컬과 원격 간의 푸시 대상 커밋 개수 확인
            ahead_count = 0
            try:
                ahead_output = self.repo.git.rev_list("--count", f"{remote_name}/{branch}..{branch}").strip()
                ahead_count = int(ahead_output)
            except (GitError, ValueError):
                ahead_count = 0

            # 3. Push 실행
            self.repo.git.push(remote_name, branch)
            logger.info(f"Pushed branch '{branch}' to remote '{remote_name}' in {self.repo_path}")

            if ahead_count > 0 or auto_commit_note:
                count_disp = max(ahead_count, 1) if auto_commit_note and ahead_count == 0 else ahead_count
                return (
                    True,
                    f"{auto_commit_note}원격 저장소(`{remote_name}/{branch}`)로 {count_disp}개의 로컬 커밋을 성공적으로 푸시했습니다! 🚀📦",
                )
            return True, f"원격 저장소(`{remote_name}/{branch}`)와 이미 모든 커밋이 최신으로 동기화(푸시)되어 있습니다. ✅"
        except (GitError, TypeError) as e:
            logger.error(f"[GitService Push Error]: {e}")
            return False, f"GitHub 푸시 중 오류 발생: {e}"

    def commit(self, commit_message: str | None = None) -> tuple[bool, str]:
        """
        현재 작업 트리의 누적된 로컬 변경 사항을 스테이징(git add -A)하고 일괄 Git 커밋을 생성합니다 (ADR-020, ADR-064).
        """
        if not self.repo:
            return False, "지정된 디렉토리가 Git 저장소가 아닙니다."

        try:
            dirty_files = self.get_dirty_files()
            self.repo.git.add(A=True)
            if not self.repo.is_dirty(untracked_files=True):
                return False, "현재 변경된 파일이 없어 커밋할 내용이 없습니다. (Working tree clean)"

            final_msg = (
                commit_message.strip()
                if commit_message and commit_message.strip()
                else self.build_batch_commit_message(dirty_files)
            )
            commit_obj = self.repo.index.commit(final_msg)
            commit_hash = commit_obj.hexsha[:7]
            file_count = len(dirty_files) if dirty_files else 1
            logger.info("Committed %s (%d files): %s in %s", commit_hash, file_count, final_msg, self.repo_path)
            return (
                True,
                f"로컬 변경 사항({file_count}개 파일)을 성공적으로 일괄 커밋했습니다 (`{commit_hash}`: {final_msg}) ✍️",
            )
        except (GitError, TypeError, OSError) as e:
            logger.error(f"Git commit error: {e}")
            return False, f"Git 커밋 중 오류 발생: {e}"

    def get_remote_info(self) -> dict:
        """
        현재 Git 저장소의 원격 저장소 URL, 브랜치, 최근 커밋 해시 및 미커밋/미푸시 상태를 투명하게 반환합니다.
        """
        dirty_files = self.get_dirty_files()
        if not self.repo:
            return {
                "configured": False,
                "message": "Git 저장소가 설정되지 않았습니다.",
                "dirty_files": [],
                "dirty_count": 0,
            }
        if not self.repo.remotes:
            return {
                "configured": False,
                "message": "연결된 원격 저장소(remote)가 없습니다.",
                "is_dirty": self.repo.is_dirty(untracked_files=True),
                "dirty_files": dirty_files,
                "dirty_count": len(dirty_files),
            }

        remote_name = settings.GIT_REMOTE_NAME if settings.GIT_REMOTE_NAME in self.repo.remotes else self.repo.remotes[0].name
        remote = self.repo.remotes[remote_name]
        raw_url = str(remote.url)
        safe_url = re.sub(r"https://[^@]+@", "https://", raw_url)
        branch = self.repo.active_branch.name if not self.repo.head.is_detached else "detached"

        latest_commit = ""
        latest_hash = ""
        try:
            head_commit = self.repo.head.commit
            latest_hash = head_commit.hexsha[:7]
            summary_val = head_commit.summary
            latest_commit = summary_val.decode("utf-8", errors="replace") if isinstance(summary_val, bytes) else str(summary_val)
        except (GitError, AttributeError, ValueError) as exc:
            logger.debug("Failed to read head commit: %s", exc)

        ahead_count = 0
        try:
            ahead_output = self.repo.git.rev_list("--count", f"{remote_name}/{branch}..{branch}").strip()
            ahead_count = int(ahead_output)
        except (GitError, ValueError) as exc:
            logger.debug("Failed to count ahead commits: %s", exc)
            ahead_count = 0

        return {
            "configured": True,
            "remote_name": remote_name,
            "url": safe_url,
            "branch": branch,
            "latest_hash": latest_hash,
            "latest_commit": latest_commit,
            "ahead_count": ahead_count,
            "is_dirty": self.repo.is_dirty(untracked_files=True),
            "dirty_files": dirty_files,
            "dirty_count": len(dirty_files),
        }


