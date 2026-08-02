"""Narrow trusted Git operations for autonomous orchestration delivery."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

MAX_GIT_OUTPUT = 1_048_576
MAX_BRANCH_LENGTH = 120
MAX_COMMIT_SUBJECT = 72
REVISION = re.compile(r"^[0-9a-f]{40,64}$")
TREE = REVISION


class GitLifecycleError(RuntimeError):
    """Raised when trusted Git state is unsafe or contradicts persisted intent."""


@dataclass(frozen=True)
class GitPosition:
    branch: str
    revision: str


@dataclass(frozen=True)
class CommitFacts:
    revision: str
    parents: list[str]
    tree: str
    subject: str


class GitLifecycle:
    """Expose only the local Git operations required by the controller."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        executable = shutil.which("git")
        if executable is None:
            raise GitLifecycleError("Git is required for orchestration")
        self.executable = executable
        top = self._run(["rev-parse", "--show-toplevel"]).strip()
        try:
            top_path = Path(top).resolve(strict=True)
        except OSError as error:
            raise GitLifecycleError("Git repository root is not usable") from error
        if top_path != self.root:
            raise GitLifecycleError(
                "orchestration must run at the exact Git worktree root"
            )

    def _environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        for name in list(environment):
            if name in {
                "GIT_DIR",
                "GIT_WORK_TREE",
                "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                "GIT_EXTERNAL_DIFF",
                "GIT_DIFF_OPTS",
                "GIT_CONFIG_COUNT",
            } or name.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
                environment.pop(name, None)
        environment.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_ASKPASS": "/bin/false",
                "GIT_EDITOR": ":",
                "GIT_SEQUENCE_EDITOR": ":",
                "LC_ALL": "C",
            }
        )
        return environment

    def _run(
        self,
        arguments: list[str],
        *,
        input_bytes: bytes | None = None,
        check: bool = True,
        timeout: int = 20,
    ) -> str:
        command = self._command(arguments)
        try:
            result = subprocess.run(  # nosec B603
                command,
                cwd=self.root,
                env=self._environment(),
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise GitLifecycleError("trusted Git operation timed out") from error
        if len(result.stdout) > MAX_GIT_OUTPUT or len(result.stderr) > MAX_GIT_OUTPUT:
            raise GitLifecycleError("trusted Git operation exceeded its output limit")
        if check and result.returncode != 0:
            diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
            if len(diagnostic) > 500:
                diagnostic = diagnostic[:500] + "..."
            raise GitLifecycleError(
                "trusted Git operation failed"
                + (f": {diagnostic}" if diagnostic else "")
            )
        return result.stdout.decode("utf-8", errors="strict")

    def _command(self, arguments: list[str]) -> list[str]:
        configuration = (
            ("core.fsmonitor", "false"),
            ("core.filemode", "true"),
            ("core.checkStat", "default"),
            ("core.trustctime", "true"),
            ("core.ignoreStat", "false"),
            ("core.untrackedCache", "false"),
            ("core.hooksPath", "/dev/null"),
            ("commit.gpgSign", "false"),
            ("credential.interactive", "false"),
        )
        command = [self.executable]
        for name, value in configuration:
            command.extend(["-c", f"{name}={value}"])
        return [*command, *arguments]

    def position(self) -> GitPosition:
        branch = self._run(["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
        branch = branch.strip()
        if not branch:
            raise GitLifecycleError("orchestration requires an attached Git branch")
        revision = self._run(["rev-parse", "--verify", "HEAD"]).strip()
        if REVISION.fullmatch(revision) is None:
            raise GitLifecycleError("orchestration requires a usable Git HEAD")
        return GitPosition(branch=branch, revision=revision)

    def validate_identity(self) -> None:
        for variable in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
            value = self._run(["var", variable], check=False).strip()
            if not value or "<>" in value:
                raise GitLifecycleError(
                    "orchestration requires noninteractive Git author and committer identity"
                )

    def reject_hidden_index_entries(self) -> None:
        raw = self._run(["ls-files", "-v", "-z", "--cached", "--"]).encode("utf-8")
        hidden: list[str] = []
        for record in (value for value in raw.split(b"\0") if value):
            if len(record) < 3 or record[1:2] != b" ":
                raise GitLifecycleError("could not validate Git index visibility")
            marker = chr(record[0])
            path = self._decode_paths(record[2:] + b"\0")[0]
            if marker == "S" or marker.islower():
                hidden.append(path)
        if hidden:
            raise GitLifecycleError(
                "orchestration rejects assume-unchanged or skip-worktree index "
                "entries: " + ", ".join(hidden[:8])
            )

    def changed_paths(self) -> list[str]:
        self.reject_hidden_index_entries()
        tracked = self._run(["diff", "--name-only", "-z", "HEAD", "--"])
        untracked = self._run(
            ["ls-files", "-z", "--others", "--exclude-standard", "--"]
        )
        return self._decode_paths(tracked.encode("utf-8") + untracked.encode("utf-8"))

    def unstaged_paths(self) -> list[str]:
        self.reject_hidden_index_entries()
        tracked = self._run(["diff", "--name-only", "-z", "--"])
        untracked = self._run(
            ["ls-files", "-z", "--others", "--exclude-standard", "--"]
        )
        return self._decode_paths(tracked.encode("utf-8") + untracked.encode("utf-8"))

    def index_is_clean(self) -> bool:
        command = self._command(["diff", "--cached", "--quiet", "--exit-code"])
        result = subprocess.run(  # nosec B603
            command,
            cwd=self.root,
            env=self._environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
        if result.returncode not in {0, 1}:
            raise GitLifecycleError("could not inspect the Git index")
        return result.returncode == 0

    def ensure_clean(self) -> None:
        if not self.index_is_clean() or self.changed_paths():
            raise GitLifecycleError("orchestration requires a clean governed worktree")

    def preflight(self) -> GitPosition:
        position = self.position()
        self.ensure_clean()
        self.validate_identity()
        return position

    @staticmethod
    def commit_subject(item_id: str, summary: str) -> str:
        normalized = " ".join(summary.replace("\x00", " ").split())
        subject = f"{item_id}: {normalized}"
        if len(subject) <= MAX_COMMIT_SUBJECT:
            return subject
        digest = hashlib.sha256(subject.encode("utf-8")).hexdigest()[:8]
        prefix = subject[: MAX_COMMIT_SUBJECT - len(digest) - 2].rstrip()
        return f"{prefix} [{digest}]"

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
        return slug or "item"

    def choose_branch(self, item_id: str, summary: str) -> str:
        stem = f"agent/{self._slug(item_id)}-{self._slug(summary)}"
        stem = stem[: MAX_BRANCH_LENGTH - 4].rstrip("-./")
        for number in range(1, 10_001):
            suffix = "" if number == 1 else f"-{number}"
            candidate = (stem[: MAX_BRANCH_LENGTH - len(suffix)] + suffix).rstrip("./")
            self._validate_branch(candidate)
            if self.ref_target(candidate) is None:
                return candidate
        raise GitLifecycleError("could not derive a collision-safe item branch")

    def _validate_branch(self, branch: str) -> None:
        if not branch or len(branch) > MAX_BRANCH_LENGTH:
            raise GitLifecycleError("item branch name is invalid")
        self._run(["check-ref-format", "--branch", branch])

    def ref_target(self, branch: str) -> str | None:
        self._validate_branch(branch)
        value = self._run(
            ["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"], check=False
        ).strip()
        if not value:
            return None
        if REVISION.fullmatch(value) is None:
            raise GitLifecycleError("item branch does not resolve to a commit")
        return value

    def activate_branch(self, branch: str, base_revision: str) -> None:
        self._validate_branch(branch)
        if REVISION.fullmatch(base_revision) is None:
            raise GitLifecycleError("item branch base revision is invalid")
        self.ensure_clean()
        current = self.position()
        existing = self.ref_target(branch)
        if existing is None:
            if current.revision != base_revision:
                raise GitLifecycleError("item branch base no longer matches HEAD")
            self._run(["checkout", "--no-track", "-b", branch, base_revision])
        else:
            if existing != base_revision:
                raise GitLifecycleError("persisted item branch was rewritten")
            if current.branch != branch:
                if current.revision != base_revision:
                    raise GitLifecycleError("foreign checkout blocks item activation")
                self._run(["checkout", branch])
        observed = self.position()
        if observed != GitPosition(branch, base_revision):
            raise GitLifecycleError("item branch activation did not reach its intent")

    def assert_position(self, branch: str, revision: str) -> None:
        if self.position() != GitPosition(branch, revision):
            raise GitLifecycleError(
                "Git branch or HEAD contradicts orchestration state"
            )

    @staticmethod
    def _decode_paths(raw: bytes) -> list[str]:
        try:
            values = [entry.decode("utf-8") for entry in raw.split(b"\0") if entry]
        except UnicodeDecodeError as error:
            raise GitLifecycleError("Git delta contains a non-UTF-8 path") from error
        result: set[str] = set()
        for value in values:
            path = PurePosixPath(value)
            if path.is_absolute() or any(
                part in {"", ".", ".."} for part in path.parts
            ):
                raise GitLifecycleError("Git delta contains an unsafe path")
            result.add(value)
        return sorted(result)

    def stage_exact(
        self,
        expected_paths: list[str],
        *,
        expected_source_digest: str,
        source_digest: Callable[[], str],
    ) -> str:
        paths = self._decode_paths(
            b"\0".join(path.encode("utf-8") for path in expected_paths) + b"\0"
        )
        if not paths:
            raise GitLifecycleError("closeout produced no commit delta")
        self.reject_hidden_index_entries()
        if source_digest() != expected_source_digest:
            raise GitLifecycleError("closeout workspace changed before exact staging")
        self._reject_external_filters(paths)
        if not self.index_is_clean():
            cached = self.cached_paths()
            if cached != paths:
                raise GitLifecycleError("Git index contains foreign staged paths")
        payload = b"\0".join(path.encode("utf-8") for path in paths) + b"\0"
        self._run(
            ["add", "--pathspec-from-file=-", "--pathspec-file-nul"],
            input_bytes=payload,
        )
        if self.cached_paths() != paths:
            raise GitLifecycleError("staged Git delta differs from the reviewed delta")
        if source_digest() != expected_source_digest:
            raise GitLifecycleError(
                "closeout workspace changed while staging the reviewed delta"
            )
        if self.unstaged_paths():
            raise GitLifecycleError(
                "staged Git content differs from the reviewed workspace"
            )
        tree = self._run(["write-tree"]).strip()
        if TREE.fullmatch(tree) is None:
            raise GitLifecycleError("Git did not produce a valid expected tree")
        if (
            source_digest() != expected_source_digest
            or self.unstaged_paths()
            or self.cached_paths() != paths
            or self._run(["write-tree"]).strip() != tree
        ):
            raise GitLifecycleError(
                "reviewed workspace or staged tree changed during validation"
            )
        return tree

    def _reject_external_filters(self, paths: list[str]) -> None:
        payload = b"\0".join(path.encode("utf-8") for path in paths) + b"\0"
        raw = self._run(
            ["check-attr", "-z", "--stdin", "filter"], input_bytes=payload
        ).encode("utf-8")
        values = [value for value in raw.split(b"\0") if value]
        if len(values) % 3:
            raise GitLifecycleError("could not validate Git filter attributes")
        for index in range(0, len(values), 3):
            filter_value = values[index + 2].decode("utf-8", errors="strict")
            if filter_value not in {"unspecified", "unset"}:
                path = values[index].decode("utf-8", errors="replace")
                raise GitLifecycleError(
                    f"external Git clean filter is not allowed for closeout: {path}"
                )

    def cached_paths(self) -> list[str]:
        raw = self._run(["diff", "--cached", "--name-only", "-z", "HEAD", "--"])
        return self._decode_paths(raw.encode("utf-8"))

    def create_commit(
        self,
        subject: str,
        *,
        branch: str,
        parent: str,
        tree: str,
    ) -> str:
        self._validate_branch(branch)
        if REVISION.fullmatch(parent) is None or TREE.fullmatch(tree) is None:
            raise GitLifecycleError("closeout commit intent is invalid")
        self.validate_identity()
        self.assert_position(branch, parent)
        self.reject_hidden_index_entries()
        if self._run(["write-tree"]).strip() != tree:
            raise GitLifecycleError("Git index changed after exact staging")
        revision = self._run(
            ["commit-tree", tree, "-p", parent],
            input_bytes=(subject + "\n").encode("utf-8"),
            timeout=60,
        ).strip()
        if REVISION.fullmatch(revision) is None:
            raise GitLifecycleError("Git did not create a valid closeout commit")
        self.assert_position(branch, parent)
        self.reject_hidden_index_entries()
        self._run(["update-ref", f"refs/heads/{branch}", revision, parent])
        if self.position() != GitPosition(branch, revision):
            raise GitLifecycleError("closeout branch did not reach the expected commit")
        return revision

    def commit_facts(self, revision: str) -> CommitFacts:
        if REVISION.fullmatch(revision) is None:
            raise GitLifecycleError("commit revision is invalid")
        raw = self._run(
            ["show", "-s", "--format=%H%x00%P%x00%T%x00%s", revision]
        ).rstrip("\n")
        parts = raw.split("\x00")
        if len(parts) != 4:
            raise GitLifecycleError("could not inspect the closeout commit")
        commit, parents, tree, subject = parts
        return CommitFacts(commit, parents.split() if parents else [], tree, subject)

    def verify_commit(
        self,
        revision: str,
        *,
        branch: str,
        parent: str,
        tree: str,
        subject: str,
    ) -> None:
        facts = self.commit_facts(revision)
        if (
            facts.revision != revision
            or facts.parents != [parent]
            or facts.tree != tree
            or facts.subject != subject
        ):
            raise GitLifecycleError("closeout commit contradicts persisted intent")
        self.assert_position(branch, revision)
        self.ensure_clean()
