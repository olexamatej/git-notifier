from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class RefInfo:
    name: str
    sha: str
    subject: str


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    subject: str


@dataclass(frozen=True)
class RefEvent:
    ref: str
    old_sha: str | None
    new_sha: str
    commits: tuple[CommitInfo, ...]
    kind: str

    @property
    def sound_count(self) -> int:
        return max(1, len(self.commits))


class GitRepo:
    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()

    def validate(self) -> None:
        self._git("rev-parse", "--git-dir")

    def fetch_all(self) -> None:
        self._git("fetch", "--all", "--prune", "--quiet")

    def refs(self, include_local: bool = True, include_remote: bool = True) -> dict[str, RefInfo]:
        namespaces: list[str] = []
        if include_local:
            namespaces.append("refs/heads")
        if include_remote:
            namespaces.append("refs/remotes")
        if not namespaces:
            return {}

        output = self._git(
            "for-each-ref",
            "--format=%(refname)%00%(objectname)%00%(subject)%00%(symref)",
            *namespaces,
        )

        refs: dict[str, RefInfo] = {}
        for line in output.splitlines():
            parts = line.split("\0")
            if len(parts) != 4:
                continue
            ref, sha, subject, symref = parts
            if symref:
                continue
            refs[ref] = RefInfo(ref, sha, subject)
        return refs

    def commits_between(self, old_sha: str, new_sha: str) -> tuple[CommitInfo, ...]:
        output = self._git(
            "log",
            "--reverse",
            "--format=%H%x00%s",
            f"{old_sha}..{new_sha}",
            check=False,
        )
        commits: list[CommitInfo] = []
        for line in output.splitlines():
            parts = line.split("\0", 1)
            if len(parts) == 2:
                commits.append(CommitInfo(parts[0], parts[1]))
        return tuple(commits)

    def detect_events(
        self,
        previous_refs: dict[str, str],
        current_refs: dict[str, RefInfo],
        notify_initial: bool = False,
    ) -> list[RefEvent]:
        if not previous_refs and not notify_initial:
            return []

        events: list[RefEvent] = []
        for ref, info in sorted(current_refs.items()):
            old_sha = previous_refs.get(ref)
            if old_sha == info.sha:
                continue
            if old_sha is None:
                events.append(
                    RefEvent(
                        ref=ref,
                        old_sha=None,
                        new_sha=info.sha,
                        commits=(CommitInfo(info.sha, info.subject),),
                        kind="new-ref",
                    )
                )
                continue

            commits = self.commits_between(old_sha, info.sha)
            kind = "commit" if commits else "ref-move"
            events.append(
                RefEvent(
                    ref=ref,
                    old_sha=old_sha,
                    new_sha=info.sha,
                    commits=commits,
                    kind=kind,
                )
            )
        return events

    def _git(self, *args: str, check: bool = True) -> str:
        process = subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if check and process.returncode != 0:
            stderr = process.stderr.strip()
            raise GitError(stderr or f"git {' '.join(args)} failed")
        if process.returncode != 0:
            return ""
        return process.stdout
