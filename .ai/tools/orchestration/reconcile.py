"""Observe Git and lifecycle state without trusting checkpoints alone."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

from .model import Checkpoint, Phase

IGNORED_ROOTS = {".ai/orchestration"}
IGNORED_FILES = {
    ".ai/.orchestration.guard",
    ".ai/orchestration-completed.json",
    "template-update.patch",
    "template-update.manual.patch",
}
FALLBACK_STATE_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
}
MAX_SNAPSHOT_FILE_BYTES = 64 * 1024 * 1024
MAX_SNAPSHOT_FILES = 100_000
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024 * 1024


class ReconcileError(RuntimeError):
    """Raised when observed repository state contradicts persisted state."""


@dataclass(frozen=True)
class FileState:
    digest: str
    mode: int
    size: int


@dataclass(frozen=True)
class RepositoryState:
    head_revision: str
    source_digest: str
    files: dict[str, FileState]
    branch_name: str | None = None


def _ignored(relative: str) -> bool:
    name = Path(relative).name
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    if relative == ".ai/config/project.env":
        return True
    if relative in IGNORED_FILES:
        return True
    if any(
        relative == root or relative.startswith(f"{root}/") for root in IGNORED_ROOTS
    ):
        return True
    return relative == ".git" or relative.startswith(".git/")


def _fallback_ignored(relative: str) -> bool:
    return _ignored(relative) or any(
        part in FALLBACK_STATE_PARTS for part in Path(relative).parts
    )


def governed_paths(root: Path, *, git_dir: Path | None = None) -> list[str]:
    """Return the Git-governed, non-secret orchestration file set."""
    git = shutil.which("git")
    if git is None:
        raise ReconcileError("Git is required for orchestration")
    environment = None
    if git_dir is not None:
        environment = {
            **os.environ,
            "GIT_DIR": os.fspath(git_dir),
            "GIT_WORK_TREE": os.fspath(root.resolve()),
        }
    result = subprocess.run(  # nosec B603
        [git, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    if result.returncode != 0:
        raise ReconcileError("could not enumerate the Git-governed file set")
    try:
        values = [
            value.decode("utf-8") for value in result.stdout.split(b"\0") if value
        ]
    except UnicodeDecodeError as error:
        raise ReconcileError(
            "Git-governed file set contains a non-UTF-8 path"
        ) from error
    return sorted(relative for relative in values if not _ignored(relative))


def snapshot(
    root: Path,
    *,
    revision: str | None = None,
    git_dir: Path | None = None,
) -> RepositoryState:
    resolved_root = root.resolve()
    files: dict[str, FileState] = {}
    aggregate = hashlib.sha256()
    total_bytes = 0
    if (resolved_root / ".git").exists() or git_dir is not None:
        candidates = [
            (relative, resolved_root / relative)
            for relative in governed_paths(resolved_root, git_dir=git_dir)
        ]
    else:
        candidates = [
            (path.relative_to(resolved_root).as_posix(), path)
            for path in sorted(resolved_root.rglob("*"))
            if not _fallback_ignored(path.relative_to(resolved_root).as_posix())
        ]
    for relative, path in candidates:
        if path.is_symlink():
            target = os.readlink(path)
            digest = hashlib.sha256(f"symlink:{target}".encode()).hexdigest()
            mode = stat.S_IFLNK
            size = len(target)
        elif path.is_file():
            size = path.stat().st_size
            if size > MAX_SNAPSHOT_FILE_BYTES:
                raise ReconcileError(f"file exceeds snapshot limit: {relative}")
            hasher = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    hasher.update(chunk)
            digest = hasher.hexdigest()
            mode = stat.S_IMODE(path.stat().st_mode)
        else:
            continue
        total_bytes += size
        if len(files) >= MAX_SNAPSHOT_FILES or total_bytes > MAX_SNAPSHOT_BYTES:
            raise ReconcileError("repository exceeds safe snapshot resource limits")
        state = FileState(digest=digest, mode=mode, size=size)
        files[relative] = state
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(str(mode).encode("ascii"))
        aggregate.update(b"\0")
    return RepositoryState(
        head_revision=revision if revision is not None else head_revision(root),
        source_digest=aggregate.hexdigest(),
        files=files,
        branch_name=(
            current_branch(root, git_dir=git_dir)
            if (resolved_root / ".git").exists() or git_dir is not None
            else None
        ),
    )


def current_branch(root: Path, *, git_dir: Path | None = None) -> str | None:
    git = shutil.which("git")
    if git is None:
        raise ReconcileError("Git is required for orchestration")
    environment = None
    if git_dir is not None:
        environment = {
            **os.environ,
            "GIT_DIR": os.fspath(git_dir),
            "GIT_WORK_TREE": os.fspath(root.resolve()),
        }
    result = subprocess.run(  # nosec B603
        [git, "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=root,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        raise ReconcileError("could not inspect the current Git branch")
    return result.stdout.strip()


def head_revision(root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise ReconcileError("Git is required for orchestration")
    result = subprocess.run(  # nosec B603
        [git, "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    if result.returncode != 0:
        raise ReconcileError("orchestration requires a Git repository with HEAD")
    return result.stdout.strip()


def ensure_clean(root: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise ReconcileError("Git is required for orchestration")
    result = subprocess.run(  # nosec B603
        [git, "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    if result.returncode != 0:
        raise ReconcileError("could not inspect Git worktree state")
    dirty: list[str] = []
    for line in result.stdout.splitlines():
        relative = line[3:]
        if " -> " in relative:
            relative = relative.split(" -> ", 1)[1]
        if not _ignored(relative):
            dirty.append(relative)
    if dirty:
        sample = ", ".join(dirty[:5])
        raise ReconcileError(f"orchestration requires a clean worktree: {sample}")


def run_lifecycle_validator(root: Path) -> None:
    validator = root / ".ai" / "tools" / "check-work-state.py"
    result = subprocess.run(  # nosec B603
        [os.fspath(validator)],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    if result.returncode != 0:
        diagnostic = result.stdout.strip().splitlines()[:3]
        raise ReconcileError("lifecycle state is invalid: " + " | ".join(diagnostic))


def validate_current_plan_binding(root: Path, item_id: str, phase: Phase) -> None:
    if phase in {Phase.INTAKE, Phase.DONE}:
        return
    current = root / ".ai" / "CURRENT_PLAN.md"
    if not current.is_file() or current.is_symlink():
        raise ReconcileError("active orchestration lacks a regular CURRENT_PLAN.md")
    text = current.read_text(encoding="utf-8")
    expected = {
        "Orchestrator item": item_id,
        "Requirement": f"`docs/requirements/{item_id}.md`",
        "Work directory": f"`.ai/work/{item_id}/`",
    }
    for field, value in expected.items():
        match = re.search(rf"(?im)^-\s*{re.escape(field)}:\s*(.*?)\s*$", text)
        if match is None or match.group(1).strip() != value:
            raise ReconcileError(f"CURRENT_PLAN.md {field} is not bound to {item_id}")


def reconcile_checkpoint(
    checkpoint: Checkpoint | None,
    observed: RepositoryState,
    *,
    validate_head: bool = True,
) -> None:
    if checkpoint is None:
        return
    if validate_head and checkpoint.head_revision != observed.head_revision:
        raise ReconcileError("checkpoint HEAD differs from the repository")
    if checkpoint.branch_name and checkpoint.branch_name != observed.branch_name:
        raise ReconcileError("checkpoint branch differs from the repository checkout")
    if checkpoint.source_digest != observed.source_digest:
        raise ReconcileError("checkpoint digest differs from the repository")


def changed_paths(
    before: RepositoryState, after: RepositoryState
) -> tuple[set[str], set[str], set[str]]:
    before_paths = set(before.files)
    after_paths = set(after.files)
    added = after_paths - before_paths
    deleted = before_paths - after_paths
    modified = {
        path
        for path in before_paths & after_paths
        if before.files[path] != after.files[path]
    }
    return added, modified, deleted
