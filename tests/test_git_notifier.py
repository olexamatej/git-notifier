from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from git_notifier.git import GitRepo


def git(repo: Path, *args: str) -> str:
    return git_cmd("-C", str(repo), *args)


def git_cmd(*args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return process.stdout


def init_repo(repo: Path) -> None:
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")


def commit_file(repo: Path, name: str, content: str, message: str) -> str:
    path = repo / name
    path.write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


class GitNotifierTests(unittest.TestCase):
    def test_detect_events_baselines_without_initial_notifications(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "repo"
            init_repo(repo_path)
            commit_file(repo_path, "one.txt", "one", "first")

            repo = GitRepo(repo_path)
            refs = repo.refs()

            self.assertEqual(repo.detect_events({}, refs, notify_initial=False), [])

    def test_detect_events_reports_new_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "repo"
            init_repo(repo_path)
            first = commit_file(repo_path, "one.txt", "one", "first")
            repo = GitRepo(repo_path)
            previous = {ref: info.sha for ref, info in repo.refs().items()}

            second = commit_file(repo_path, "two.txt", "two", "second")
            events = repo.detect_events(previous, repo.refs())

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].kind, "commit")
            self.assertEqual(events[0].old_sha, first)
            self.assertEqual(events[0].new_sha, second)
            self.assertEqual([commit.subject for commit in events[0].commits], ["second"])

    def test_detect_events_reports_new_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "repo"
            init_repo(repo_path)
            commit_file(repo_path, "one.txt", "one", "first")
            repo = GitRepo(repo_path)
            previous = {ref: info.sha for ref, info in repo.refs().items()}

            git(repo_path, "checkout", "-b", "feature")
            commit_file(repo_path, "two.txt", "two", "feature work")
            events = repo.detect_events(previous, repo.refs())

            self.assertEqual({event.ref for event in events}, {"refs/heads/feature"})
            self.assertEqual(events[0].kind, "new-ref")

    def test_detect_events_reports_remote_push(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            origin = root / "origin.git"
            source = root / "source"
            watcher = root / "watcher"

            git_cmd("init", "--bare", str(origin))
            init_repo(source)
            commit_file(source, "one.txt", "one", "first")
            git(source, "branch", "-M", "main")
            git(source, "remote", "add", "origin", str(origin))
            git(source, "push", "-u", "origin", "main")
            git_cmd("clone", str(origin), str(watcher))

            watcher_repo = GitRepo(watcher)
            previous = {
                ref: info.sha
                for ref, info in watcher_repo.refs(include_local=False, include_remote=True).items()
            }

            second = commit_file(source, "two.txt", "two", "second")
            git(source, "push")

            watcher_repo.fetch_all()
            events = watcher_repo.detect_events(
                previous,
                watcher_repo.refs(include_local=False, include_remote=True),
            )

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].ref, "refs/remotes/origin/main")
            self.assertEqual(events[0].new_sha, second)
            self.assertEqual([commit.subject for commit in events[0].commits], ["second"])


if __name__ == "__main__":
    unittest.main()
