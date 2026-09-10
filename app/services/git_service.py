import logging
import os
import re

import git
from git.exc import GitError

from app.config import settings

logger = logging.getLogger("watson.git")


class GitService:
    """
    Git 자동화 서비스 (ADR-001, ADR-007 준수).
    지정된 repo_path(독립 GTD 레포지토리)의 커밋/푸시를 담당하며,
    Git 저장소가 아닌 경우에도 오류 없이 안전하게 로컬 저장을 지원합니다.
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

    def push(self) -> tuple[bool, str]:
        """
        원격 저장소(GitHub)로 로컬 커밋들을 안전하게 푸시합니다 (ADR-011).
        푸시 전 autostash를 적용한 pull로 원격 변경사항을 통합한 후 푸시합니다.
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

            if ahead_count > 0:
                return True, f"원격 저장소(`{remote_name}/{branch}`)로 {ahead_count}개의 로컬 커밋을 성공적으로 푸시했습니다! 🚀📦"
            return True, f"원격 저장소(`{remote_name}/{branch}`)와 이미 모든 커밋이 최신으로 동기화(푸시)되어 있습니다. ✅"
        except (GitError, TypeError) as e:
            logger.error(f"[GitService Push Error]: {e}")
            return False, f"GitHub 푸시 중 오류 발생: {e}"

    def commit(self, commit_message: str) -> tuple[bool, str]:
        """
        현재 작업 트리의 변경 사항을 스테이징(git add -A)하고 로컬 Git 커밋을 생성합니다.
        """
        if not self.repo:
            return False, "지정된 디렉토리가 Git 저장소가 아닙니다."

        try:
            self.repo.git.add(A=True)
            if not self.repo.is_dirty(untracked_files=True):
                return False, "현재 변경된 파일이 없어 커밋할 내용이 없습니다. (Working tree clean)"

            commit_obj = self.repo.index.commit(commit_message)
            commit_hash = commit_obj.hexsha[:7]
            logger.info("Committed %s: %s in %s", commit_hash, commit_message, self.repo_path)
            return True, f"로컬 변경 사항을 성공적으로 커밋했습니다 (`{commit_hash}`: {commit_message}) ✍️"
        except (GitError, TypeError, OSError) as e:
            logger.error(f"Git commit error: {e}")
            return False, f"Git 커밋 중 오류 발생: {e}"

    def get_remote_info(self) -> dict:
        """
        현재 Git 저장소의 원격 저장소 URL, 브랜치, 최근 커밋 해시 및 상태를 투명하게 반환합니다.
        """
        if not self.repo:
            return {"configured": False, "message": "Git 저장소가 설정되지 않았습니다."}
        if not self.repo.remotes:
            return {"configured": False, "message": "연결된 원격 저장소(remote)가 없습니다."}

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
        }


