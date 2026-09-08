import logging
import os

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
                remote = self.repo.remotes[remote_name]
                try:
                    branch = self.repo.active_branch.name
                    remote.pull(branch, rebase=True)
                    remote.push(branch)
                    logger.info(f"Pushed branch '{branch}' to remote '{remote_name}' in {self.repo_path}")
                except (GitError, TypeError) as re:
                    logger.warning(f"[Git Remote Sync Warning]: {re}")

            return True
        except GitError as e:
            logger.error(f"[GitService Error]: {e}")
            return False
