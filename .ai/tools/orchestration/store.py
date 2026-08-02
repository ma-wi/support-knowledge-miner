"""Bounded, atomic persistence below the orchestration state root."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import tempfile
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, TypeVar

from .model import (
    STATE_SCHEMA_VERSION,
    Checkpoint,
    Event,
    Lease,
    ModelError,
    Phase,
    Queue,
)

MAX_JSON_BYTES = 1_048_576
MAX_EVENT_BYTES = 65_536
MAX_EVENT_LOG_BYTES = 8_388_608
T = TypeVar("T")


class StoreError(RuntimeError):
    """Raised for unsafe or inconsistent persistent state."""


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_time(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise StoreError(f"invalid timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        raise StoreError(f"timestamp must include a timezone: {value!r}")
    return parsed


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        # Python cannot open directory handles with os.open on Windows. The
        # replaced file itself is still flushed before the atomic rename.
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class StateStore:
    def __init__(self, repository_root: Path):
        self.repository_root = repository_root.resolve()
        self.root = self.repository_root / ".ai" / "orchestration"
        self._bound_lease: Lease | None = None
        self._local_guard = threading.Lock()
        self._ensure_safe_root()

    def _ensure_safe_root(self) -> None:
        ai_root = self.repository_root / ".ai"
        if ai_root.is_symlink() or (ai_root.exists() and not ai_root.is_dir()):
            raise StoreError(".ai must be a real directory")
        if self.root.is_symlink() or (self.root.exists() and not self.root.is_dir()):
            raise StoreError("orchestration state root must be a real directory")
        if (
            self.root.resolve(strict=False)
            != self.repository_root / ".ai/orchestration"
        ):
            raise StoreError("orchestration state root escapes the repository")

    def _assert_fencing_token(self) -> None:
        if self._bound_lease is None:
            return
        current = self.load("LEASE.json", Lease.from_dict)
        if (
            current.owner_id != self._bound_lease.owner_id
            or current.invocation_id != self._bound_lease.invocation_id
        ):
            raise StoreError("orchestration lease fencing token was superseded")

    def resolve(self, relative: str, *, allow_missing: bool = True) -> Path:
        self._ensure_safe_root()
        if not relative or Path(relative).is_absolute():
            raise StoreError("state path must be non-empty and relative")
        candidate = self.root / relative
        parent = candidate.parent.resolve(strict=False)
        try:
            parent.relative_to(self.root.resolve(strict=False))
        except ValueError as error:
            raise StoreError(
                f"state path escapes orchestration root: {relative}"
            ) from error
        if candidate.exists() or candidate.is_symlink():
            resolved = candidate.resolve(strict=True)
            try:
                resolved.relative_to(self.root.resolve(strict=True))
            except ValueError as error:
                raise StoreError(
                    f"state symlink escapes orchestration root: {relative}"
                ) from error
        elif not allow_missing:
            raise StoreError(f"state path does not exist: {relative}")
        return candidate

    def read_json(self, relative: str) -> dict[str, Any]:
        path = self.resolve(relative, allow_missing=False)
        if not path.is_file() or path.is_symlink():
            raise StoreError(f"state is not a regular file: {relative}")
        size = path.stat().st_size
        if size > MAX_JSON_BYTES:
            raise StoreError(f"state file exceeds {MAX_JSON_BYTES} bytes: {relative}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise StoreError(f"invalid JSON state: {relative}") from error
        if not isinstance(value, dict):
            raise StoreError(f"JSON state must be an object: {relative}")
        return value

    def load(self, relative: str, factory: Callable[[object], T]) -> T:
        try:
            return factory(self.read_json(relative))
        except ModelError as error:
            raise StoreError(f"invalid state model in {relative}: {error}") from error

    def write_json(self, relative: str, value: dict[str, object]) -> None:
        encoded = (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        if len(encoded) > MAX_JSON_BYTES:
            raise StoreError(f"JSON state exceeds {MAX_JSON_BYTES} bytes: {relative}")
        self.write_bytes(relative, encoded)

    def write_bytes(self, relative: str, content: bytes) -> None:
        if relative == "LEASE.json" or self._bound_lease is None:
            self._write_bytes_unchecked(relative, content)
            return
        with self._lease_guard():
            self._assert_fencing_token()
            self._write_bytes_unchecked(relative, content)

    def _write_bytes_unchecked(self, relative: str, content: bytes) -> None:
        path = self.resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            _fsync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)

    def fenced_promotion(
        self,
        handoff_relative: str,
        handoff: dict[str, object],
        mutation: Callable[[], T],
        marker_relative: str,
        marker_factory: Callable[[T | None], dict[str, object]],
    ) -> T:
        """Fence a recoverable marker and source mutation under one lease token."""
        if self._bound_lease is None:
            raise StoreError("promotion requires a bound orchestration lease")
        with self._lease_guard():
            self._assert_fencing_token()
            handoff_bytes = (
                json.dumps(handoff, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            self._write_bytes_unchecked(handoff_relative, handoff_bytes)
            prepared = marker_factory(None)
            prepared["status"] = "prepared"
            self._write_bytes_unchecked(
                marker_relative,
                (
                    json.dumps(prepared, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n"
                ).encode("utf-8"),
            )
            mutating = marker_factory(None)
            mutating["status"] = "mutating"
            self._write_bytes_unchecked(
                marker_relative,
                (
                    json.dumps(mutating, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n"
                ).encode("utf-8"),
            )
            result = mutation()
            committed = marker_factory(result)
            committed["status"] = "committed"
            marker_bytes = (
                json.dumps(
                    committed,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            self._write_bytes_unchecked(marker_relative, marker_bytes)
            return result

    def append_event(
        self,
        item_id: str,
        event_type: str,
        invocation_id: str,
        previous_state: str,
        details: dict[str, object] | None = None,
    ) -> None:
        try:
            event = Event(
                item_id=item_id,
                time=iso_time(),
                invocation_id=invocation_id,
                previous_state=Phase(previous_state),
                event_type=event_type,
                details=details or {},
            )
        except ValueError as error:
            raise StoreError("event references an invalid previous phase") from error
        encoded = (
            json.dumps(
                event.to_dict(),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        if len(encoded) > MAX_EVENT_BYTES:
            raise StoreError("event exceeds safe size limit")
        if self._bound_lease is None:
            self._append_event_bytes(item_id, encoded)
            return
        with self._lease_guard():
            self._assert_fencing_token()
            self._append_event_bytes(item_id, encoded)

    def _append_event_bytes(self, item_id: str, encoded: bytes) -> None:
        relative = f"runs/{item_id}/EVENTS.jsonl"
        path = self.resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raw = path.read_bytes()
            if raw and not raw.endswith(b"\n"):
                # Validate the complete prefix before removing a crash-torn tail.
                self.read_events(item_id)
                boundary = raw.rfind(b"\n")
                descriptor = os.open(path, os.O_WRONLY)
                try:
                    os.ftruncate(descriptor, boundary + 1)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        current_size = path.stat().st_size if path.exists() else 0
        if current_size + len(encoded) > MAX_EVENT_LOG_BYTES:
            raise StoreError("event log exceeds safe size limit")
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        descriptor = os.open(path, flags, 0o600)
        try:
            written = os.write(descriptor, encoded)
            if written != len(encoded):
                raise StoreError("event append was incomplete")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def read_events(self, item_id: str) -> list[dict[str, Any]]:
        relative = f"runs/{item_id}/EVENTS.jsonl"
        path = self.resolve(relative, allow_missing=False)
        if path.stat().st_size > MAX_EVENT_LOG_BYTES:
            raise StoreError("event log exceeds safe size limit")
        raw = path.read_bytes()
        lines = raw.splitlines(keepends=True)
        events: list[dict[str, Any]] = []
        for index, line in enumerate(lines):
            if not line.endswith(b"\n"):
                if index == len(lines) - 1:
                    break
                raise StoreError("event log has an incomplete non-final line")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise StoreError(f"event log corruption at line {index + 1}") from error
            try:
                event = Event.from_dict(value)
            except ModelError as error:
                raise StoreError(
                    f"invalid event at line {index + 1}: {error}"
                ) from error
            if event.item_id != item_id:
                raise StoreError(f"event item mismatch at line {index + 1}")
            events.append(event.to_dict())
        return events

    def queue_exists(self) -> bool:
        return self.resolve("QUEUE.json").is_file()

    def control_digest(self) -> str:
        """Digest trusted runtime state so an agent cannot mutate it unnoticed."""
        digest = hashlib.sha256()
        if not self.root.exists():
            return digest.hexdigest()
        for path in sorted(self.root.rglob("*")):
            relative = path.relative_to(self.root).as_posix()
            if relative == "LEASE.json" or relative.startswith("sandboxes/"):
                continue
            if path.is_symlink() or not path.is_file():
                if path.is_dir():
                    continue
                raise StoreError(f"unsafe runtime state entry: {relative}")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()

    def load_queue(self) -> Queue:
        if not self.queue_exists():
            return Queue([])
        value = self.read_json("QUEUE.json")
        if value.get("schema_version") != STATE_SCHEMA_VERSION:
            raise StoreError(
                "legacy orchestration runtime state cannot be resumed with autonomous "
                "Git delivery; finish it with the previous controller or archive the "
                "completed .ai/orchestration directory before starting a new run"
            )
        try:
            return Queue.from_dict(value)
        except ModelError as error:
            raise StoreError(f"invalid state model in QUEUE.json: {error}") from error

    def save_queue(self, queue: Queue) -> None:
        self.write_json("QUEUE.json", queue.to_dict())

    def load_checkpoint(self, item_id: str) -> Checkpoint | None:
        relative = f"runs/{item_id}/CHECKPOINT.json"
        if not self.resolve(relative).is_file():
            return None
        return self.load(relative, Checkpoint.from_dict)

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        self.write_json(
            f"runs/{checkpoint.item_id}/CHECKPOINT.json", checkpoint.to_dict()
        )

    @contextmanager
    def _lease_guard(self):
        self._ensure_safe_root()
        with self._local_guard:
            ai_root = self.repository_root / ".ai"
            ai_root.mkdir(parents=True, exist_ok=True)
            self._ensure_safe_root()
            guard = ai_root / ".orchestration.guard"
            try:
                descriptor = os.open(guard, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as error:
                stale = False
                try:
                    host, process_id = guard.read_text(encoding="ascii").split(":", 1)
                    if host == socket.gethostname():
                        os.kill(int(process_id), 0)
                except ProcessLookupError:
                    stale = True
                except (OSError, UnicodeError, ValueError):
                    pass
                if not stale:
                    raise StoreError("another process is mutating the lease") from error
                guard.unlink()
                descriptor = os.open(guard, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                os.write(
                    descriptor,
                    f"{socket.gethostname()}:{os.getpid()}".encode("ascii"),
                )
                os.fsync(descriptor)
                os.close(descriptor)
                yield
            finally:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                guard.unlink(missing_ok=True)

    def acquire_lease(
        self,
        owner_id: str,
        invocation_id: str,
        duration_seconds: int,
        *,
        allow_takeover: bool = True,
    ) -> tuple[Lease, bool]:
        with self._lease_guard():
            now = utc_now()
            path = self.resolve("LEASE.json")
            takeover = False
            if path.exists():
                existing = self.load("LEASE.json", Lease.from_dict)
                if parse_time(existing.expires_at) > now and (
                    existing.owner_id != owner_id
                    or existing.invocation_id != invocation_id
                ):
                    raise StoreError(
                        f"active orchestration lease belongs to {existing.owner_id}"
                    )
                takeover = (
                    existing.owner_id != owner_id
                    or existing.invocation_id != invocation_id
                )
                if takeover and not allow_takeover:
                    raise StoreError(
                        "expired orchestration lease requires resume reconciliation"
                    )
            lease = Lease(
                owner_id=owner_id,
                acquired_at=iso_time(now),
                expires_at=iso_time(now + timedelta(seconds=duration_seconds)),
                invocation_id=invocation_id,
            )
            self.write_json("LEASE.json", lease.to_dict())
            self._bound_lease = lease
            return lease, takeover

    def renew_lease(self, lease: Lease, duration_seconds: int) -> Lease:
        with self._lease_guard():
            current = self.load("LEASE.json", Lease.from_dict)
            if (
                current.owner_id != lease.owner_id
                or current.invocation_id != lease.invocation_id
            ):
                raise StoreError("cannot renew a lease owned by another invocation")
            renewed = Lease(
                owner_id=lease.owner_id,
                acquired_at=lease.acquired_at,
                expires_at=iso_time(utc_now() + timedelta(seconds=duration_seconds)),
                invocation_id=lease.invocation_id,
            )
            self.write_json("LEASE.json", renewed.to_dict())
            self._bound_lease = renewed
            return renewed

    def release_lease(self, lease: Lease) -> None:
        with self._lease_guard():
            path = self.resolve("LEASE.json")
            if not path.exists():
                return
            current = self.load("LEASE.json", Lease.from_dict)
            if (
                current.owner_id != lease.owner_id
                or current.invocation_id != lease.invocation_id
            ):
                raise StoreError("cannot release a lease owned by another invocation")
            path.unlink()
            self._bound_lease = None

    def completion_receipt(self) -> dict[str, Any] | None:
        path = self.repository_root / ".ai" / "orchestration-completed.json"
        if not path.exists():
            return None
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > MAX_JSON_BYTES
        ):
            raise StoreError("orchestration completion receipt is unsafe")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise StoreError("orchestration completion receipt is invalid") from error
        if not isinstance(value, dict):
            raise StoreError("orchestration completion receipt must be an object")
        if set(value) != {
            "schema_version",
            "completed_at",
            "initial_branch",
            "initial_revision",
            "latest_branch",
            "latest_commit",
            "items",
        }:
            raise StoreError("orchestration completion receipt has invalid fields")
        revision = re.compile(r"^[0-9a-f]{40,64}$")
        if (
            value.get("schema_version") != 1
            or not all(
                isinstance(value.get(name), str) and value[name]
                for name in ("completed_at", "initial_branch", "latest_branch")
            )
            or not all(
                isinstance(value.get(name), str)
                and revision.fullmatch(value[name]) is not None
                for name in ("initial_revision", "latest_commit")
            )
            or not isinstance(value.get("items"), list)
        ):
            raise StoreError("orchestration completion receipt has invalid values")
        parse_time(value["completed_at"])
        for item in value["items"]:
            if (
                not isinstance(item, dict)
                or set(item) != {"id", "branch", "commit"}
                or not all(
                    isinstance(item.get(name), str) and item[name]
                    for name in ("id", "branch")
                )
                or not isinstance(item.get("commit"), str)
                or revision.fullmatch(item["commit"]) is None
            ):
                raise StoreError("orchestration completion receipt item is invalid")
        return value

    def _write_completion_receipt(self, receipt: dict[str, object]) -> None:
        ai_root = self.repository_root / ".ai"
        ai_root.mkdir(parents=True, exist_ok=True)
        path = ai_root / "orchestration-completed.json"
        encoded = (
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        if len(encoded) > MAX_JSON_BYTES:
            raise StoreError("orchestration completion receipt exceeds its size limit")
        descriptor, temporary_name = tempfile.mkstemp(prefix=".completed.", dir=ai_root)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            _fsync_directory(ai_root)
        finally:
            temporary.unlink(missing_ok=True)

    def fenced_cleanup(self, receipt: dict[str, object] | None = None) -> None:
        """Remove completed runtime state while retaining the lease fence."""
        if self._bound_lease is None:
            raise StoreError("fenced cleanup requires a bound lease")
        with self._lease_guard():
            self._assert_fencing_token()
            if receipt is not None:
                self._write_completion_receipt(receipt)
            shutil.rmtree(self.root)
            self._bound_lease = None
