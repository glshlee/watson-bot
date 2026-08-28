
import git
from git.exc import GitError

from app.config import settings


class GitService:
    def __init__(self, repo_path: str | None = None):
        self.repo_path = repo_path or settings.REPO_PATH
        try:
            self.repo = git.Repo(self.repo_path)
        except GitError:
            self.repo = None

    def sync_and_commit_push(self, commit_message: str, file_path: str | None = None) -> bool:
        if not self.repo:
            return False

        try:
            # 1. Pull latest rebase
            origin = self.repo.remotes[settings.GIT_REMOTE_NAME]
            origin.pull(rebase=True)

            # 2. Add file
            if file_path:
                self.repo.index.add([file_path])
            else:
                self.repo.git.add(A=True)

            # 3. Commit if there are changes
            if self.repo.is_dirty(untracked_files=True):
                self.repo.index.commit(commit_message)

            # 4. Push
            origin.push()
            return True
        except GitError as e:
            print(f"[GitService Error]: {e}")
            return False
