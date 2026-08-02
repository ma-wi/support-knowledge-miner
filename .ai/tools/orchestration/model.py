"""Strict, dependency-free orchestration data models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, ClassVar

SCHEMA_VERSION = 1
STATE_SCHEMA_VERSION = 2
MAX_TEXT = 16_384
MAX_ITEMS = 100
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
GIT_REVISION = re.compile(r"^[0-9a-f]{40,64}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
EVENT_TYPES = {
    "awaiting-owner",
    "commit-created",
    "handoff-recovered",
    "host-visual-gate",
    "lease-takeover",
    "owner-decision",
    "retryable-failure",
    "status-change",
    "transition",
    "verification-passed",
}


class ModelError(ValueError):
    """Raised when persisted or agent-provided state is invalid."""


class QueueStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    AWAITING_OWNER = "awaiting-owner"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class Phase(str, Enum):
    INTAKE = "intake"
    DISCOVERY = "discovery"
    SPECIFICATION = "specification"
    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    CODE_REVIEW = "code-review"
    VISUAL_REVIEW = "visual-review"
    REMEDIATION = "remediation"
    CLOSEOUT = "closeout"
    DONE = "done"


class Role(str, Enum):
    PLANNER = "planner"
    IMPLEMENTER = "implementer"
    CODE_REVIEWER = "code-reviewer"
    VISUAL_REVIEWER = "visual-reviewer"
    CONTROLLER = "controller"


class HandoffResult(str, Enum):
    COMPLETED = "completed"
    NEEDS_OWNER_DECISION = "needs-owner-decision"
    NEEDS_REMEDIATION = "needs-remediation"
    RETRYABLE_FAILURE = "retryable-failure"
    BLOCKED = "blocked"
    INVALID_STATE = "invalid-state"


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ModelError(f"{label} must be a JSON object")
    return value


def _strict(
    data: dict[str, Any], required: set[str], optional: set[str] = set()
) -> None:
    missing = sorted(required - data.keys())
    unknown = sorted(data.keys() - required - optional)
    if missing:
        raise ModelError(f"missing field(s): {', '.join(missing)}")
    if unknown:
        raise ModelError(f"unknown field(s): {', '.join(unknown)}")


def _schema(data: dict[str, Any]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ModelError(f"unsupported schema_version: {data.get('schema_version')!r}")


def _text(value: object, label: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ModelError(f"{label} must be a non-empty string")
    if len(value) > MAX_TEXT:
        raise ModelError(f"{label} exceeds {MAX_TEXT} characters")
    return value


def _identifier(value: object, label: str) -> str:
    result = _text(value, label)
    if not IDENTIFIER.fullmatch(result):
        raise ModelError(f"{label} is not a safe identifier")
    return result


def _revision(value: object, label: str) -> str:
    result = _text(value, label)
    if not GIT_REVISION.fullmatch(result):
        raise ModelError(f"{label} is not a Git revision")
    return result


def _branch(value: object, label: str, *, empty: bool = False) -> str:
    result = _text(value, label, empty=empty)
    if not result and empty:
        return result
    if (
        len(result) > 120
        or result.startswith(("-", "/"))
        or result.endswith(("/", "."))
        or ".." in result
        or any(ord(character) < 32 or character in " ~^:?*[\\" for character in result)
    ):
        raise ModelError(f"{label} is not a safe Git branch")
    return result


def _digest(value: object, label: str) -> str:
    result = _text(value, label)
    if not DIGEST.fullmatch(result):
        raise ModelError(f"{label} is not a SHA-256 digest")
    return result


def _timestamp(value: object, label: str) -> str:
    result = _text(value, label)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as error:
        raise ModelError(f"{label} is not an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ModelError(f"{label} must include a timezone")
    return result


def _string_list(value: object, label: str, *, limit: int = MAX_ITEMS) -> list[str]:
    if not isinstance(value, list) or len(value) > limit:
        raise ModelError(f"{label} must be a list with at most {limit} entries")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_text(item, f"{label}[{index}]"))
    if len(set(result)) != len(result):
        raise ModelError(f"{label} contains duplicates")
    return result


def _path_list(value: object, label: str, *, limit: int = 32) -> list[str]:
    result = _string_list(value, label, limit=limit)
    for item in result:
        path = PurePosixPath(item)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in item
        ):
            raise ModelError(f"{label} contains an unsafe repository path")
    return result


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ModelError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class CheckResult:
    name: str
    outcome: str
    command: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: object) -> CheckResult:
        data = _mapping(value, "check")
        _strict(data, {"name", "outcome", "command"})
        outcome = _text(data["outcome"], "check.outcome")
        if outcome not in {"passed", "failed", "skipped"}:
            raise ModelError("check.outcome must be passed, failed, or skipped")
        return cls(
            name=_text(data["name"], "check.name"),
            outcome=outcome,
            command=_string_list(data["command"], "check.command", limit=32),
        )

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "outcome": self.outcome, "command": self.command}


@dataclass(frozen=True)
class OwnerRequest:
    decision_id: str
    question: str
    recommendation: str
    alternatives: list[str]
    risks: str
    allowed_answers: list[str]
    default: str | None = None
    authorized_paths: list[str] = field(default_factory=list)
    authorizing_answers: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: object) -> OwnerRequest:
        data = _mapping(value, "owner request")
        _strict(
            data,
            {
                "decision_id",
                "question",
                "recommendation",
                "alternatives",
                "risks",
                "allowed_answers",
                "default",
            },
            {"authorized_paths", "authorizing_answers"},
        )
        default = data["default"]
        if default is not None:
            default = _text(default, "owner_request.default")
        answers = _string_list(
            data["allowed_answers"], "owner_request.allowed_answers", limit=10
        )
        if default is not None and default not in answers:
            raise ModelError("owner request default is not an allowed answer")
        authorizing_answers = _string_list(
            data.get("authorizing_answers", []),
            "owner_request.authorizing_answers",
            limit=10,
        )
        if not set(authorizing_answers).issubset(answers):
            raise ModelError("owner authorizing answers must be allowed answers")
        return cls(
            decision_id=_identifier(data["decision_id"], "owner_request.decision_id"),
            question=_text(data["question"], "owner_request.question"),
            recommendation=_text(
                data["recommendation"], "owner_request.recommendation"
            ),
            alternatives=_string_list(
                data["alternatives"], "owner_request.alternatives", limit=5
            ),
            risks=_text(data["risks"], "owner_request.risks"),
            allowed_answers=answers,
            default=default,
            authorized_paths=_path_list(
                data.get("authorized_paths", []),
                "owner_request.authorized_paths",
            ),
            authorizing_answers=authorizing_answers,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "question": self.question,
            "recommendation": self.recommendation,
            "alternatives": self.alternatives,
            "risks": self.risks,
            "allowed_answers": self.allowed_answers,
            "default": self.default,
            "authorized_paths": self.authorized_paths,
            "authorizing_answers": self.authorizing_answers,
        }


@dataclass
class QueueItem:
    item_id: str
    summary: str
    priority: int = 0
    depends_on: list[str] = field(default_factory=list)
    sequence: int = 0
    status: QueueStatus = QueueStatus.PENDING
    phase: Phase = Phase.INTAKE
    active_invocation_id: str | None = None
    retry_count: int = 0
    identical_failure_count: int = 0
    failure_signature: str | None = None
    next_attempt_at: str | None = None
    branch_name: str = ""
    base_revision: str | None = None
    branch_ready: bool = False
    reviewed_source_digest: str | None = None
    expected_closeout_digest: str | None = None
    expected_commit_tree: str | None = None
    commit_revision: str | None = None

    FIELDS: ClassVar[set[str]] = {
        "item_id",
        "summary",
        "priority",
        "depends_on",
        "sequence",
        "status",
        "phase",
        "active_invocation_id",
        "retry_count",
        "identical_failure_count",
        "failure_signature",
        "next_attempt_at",
        "branch_name",
        "base_revision",
        "branch_ready",
        "reviewed_source_digest",
        "expected_closeout_digest",
        "expected_commit_tree",
        "commit_revision",
    }

    @classmethod
    def from_dict(cls, value: object) -> QueueItem:
        data = _mapping(value, "queue item")
        _strict(data, cls.FIELDS)
        try:
            status = QueueStatus(_text(data["status"], "queue_item.status"))
            phase = Phase(_text(data["phase"], "queue_item.phase"))
        except ValueError as error:
            raise ModelError(str(error)) from error
        nullable: dict[str, str | None] = {}
        for name in ("active_invocation_id", "failure_signature", "next_attempt_at"):
            raw = data[name]
            nullable[name] = None if raw is None else _text(raw, f"queue_item.{name}")
        if nullable["active_invocation_id"] is not None:
            nullable["active_invocation_id"] = _identifier(
                nullable["active_invocation_id"], "queue_item.active_invocation_id"
            )
        if nullable["next_attempt_at"] is not None:
            nullable["next_attempt_at"] = _timestamp(
                nullable["next_attempt_at"], "queue_item.next_attempt_at"
            )
        git_values: dict[str, str | None] = {}
        for name in (
            "base_revision",
            "reviewed_source_digest",
            "expected_closeout_digest",
            "expected_commit_tree",
            "commit_revision",
        ):
            raw = data[name]
            git_values[name] = None if raw is None else _text(raw, f"queue_item.{name}")
        for name in ("base_revision", "commit_revision"):
            if git_values[name] is not None:
                git_values[name] = _revision(git_values[name], f"queue_item.{name}")
        for name in ("reviewed_source_digest", "expected_closeout_digest"):
            if git_values[name] is not None:
                git_values[name] = _digest(git_values[name], f"queue_item.{name}")
        if git_values["expected_commit_tree"] is not None:
            git_values["expected_commit_tree"] = _revision(
                git_values["expected_commit_tree"], "queue_item.expected_commit_tree"
            )
        branch_ready = data["branch_ready"]
        if not isinstance(branch_ready, bool):
            raise ModelError("queue_item.branch_ready must be boolean")
        return cls(
            item_id=_identifier(data["item_id"], "queue_item.item_id"),
            summary=_text(data["summary"], "queue_item.summary"),
            priority=_integer(data["priority"], "queue_item.priority"),
            depends_on=[
                _identifier(value, "queue_item.depends_on")
                for value in _string_list(data["depends_on"], "queue_item.depends_on")
            ],
            sequence=_integer(data["sequence"], "queue_item.sequence"),
            status=status,
            phase=phase,
            active_invocation_id=nullable["active_invocation_id"],
            retry_count=_integer(data["retry_count"], "queue_item.retry_count"),
            identical_failure_count=_integer(
                data["identical_failure_count"],
                "queue_item.identical_failure_count",
            ),
            failure_signature=nullable["failure_signature"],
            next_attempt_at=nullable["next_attempt_at"],
            branch_name=_branch(
                data["branch_name"], "queue_item.branch_name", empty=True
            ),
            base_revision=git_values["base_revision"],
            branch_ready=branch_ready,
            reviewed_source_digest=git_values["reviewed_source_digest"],
            expected_closeout_digest=git_values["expected_closeout_digest"],
            expected_commit_tree=git_values["expected_commit_tree"],
            commit_revision=git_values["commit_revision"],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "summary": self.summary,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "sequence": self.sequence,
            "status": self.status.value,
            "phase": self.phase.value,
            "active_invocation_id": self.active_invocation_id,
            "retry_count": self.retry_count,
            "identical_failure_count": self.identical_failure_count,
            "failure_signature": self.failure_signature,
            "next_attempt_at": self.next_attempt_at,
            "branch_name": self.branch_name,
            "base_revision": self.base_revision,
            "branch_ready": self.branch_ready,
            "reviewed_source_digest": self.reviewed_source_digest,
            "expected_closeout_digest": self.expected_closeout_digest,
            "expected_commit_tree": self.expected_commit_tree,
            "commit_revision": self.commit_revision,
        }


@dataclass
class RunGitState:
    initial_branch: str
    initial_revision: str
    latest_branch: str | None = None
    latest_commit: str | None = None

    @classmethod
    def from_dict(cls, value: object) -> RunGitState:
        data = _mapping(value, "run Git state")
        _strict(
            data,
            {"initial_branch", "initial_revision", "latest_branch", "latest_commit"},
        )
        latest_branch = data["latest_branch"]
        latest_commit = data["latest_commit"]
        return cls(
            initial_branch=_branch(data["initial_branch"], "run_git.initial_branch"),
            initial_revision=_revision(
                data["initial_revision"], "run_git.initial_revision"
            ),
            latest_branch=(
                None
                if latest_branch is None
                else _branch(latest_branch, "run_git.latest_branch")
            ),
            latest_commit=(
                None
                if latest_commit is None
                else _revision(latest_commit, "run_git.latest_commit")
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "initial_branch": self.initial_branch,
            "initial_revision": self.initial_revision,
            "latest_branch": self.latest_branch,
            "latest_commit": self.latest_commit,
        }


@dataclass
class Queue:
    items: list[QueueItem]
    run_git: RunGitState | None = None

    @classmethod
    def from_dict(cls, value: object) -> Queue:
        data = _mapping(value, "queue")
        _strict(data, {"schema_version", "items", "run_git"})
        if data.get("schema_version") != STATE_SCHEMA_VERSION:
            raise ModelError(
                f"unsupported orchestration state schema_version: "
                f"{data.get('schema_version')!r}"
            )
        raw_items = data["items"]
        if not isinstance(raw_items, list) or len(raw_items) > MAX_ITEMS:
            raise ModelError(f"queue.items must contain at most {MAX_ITEMS} entries")
        items = [QueueItem.from_dict(item) for item in raw_items]
        ids = [item.item_id for item in items]
        if len(ids) != len(set(ids)):
            raise ModelError("queue contains duplicate item IDs")
        run_git_raw = data["run_git"]
        run_git = None if run_git_raw is None else RunGitState.from_dict(run_git_raw)
        return cls(items, run_git)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "items": [item.to_dict() for item in self.items],
            "run_git": None if self.run_git is None else self.run_git.to_dict(),
        }


@dataclass(frozen=True)
class AgentRequest:
    item_id: str
    summary: str
    phase: Phase
    role: Role
    invocation_id: str
    head_revision: str
    source_digest: str
    workspace: str
    allowed_paths: list[str]
    instructions: str
    task_ids: list[str]
    owner_authorized_paths: list[str] = field(default_factory=list)
    source_branch: str = ""

    @classmethod
    def from_dict(cls, value: object) -> AgentRequest:
        data = _mapping(value, "agent request")
        _strict(
            data,
            {
                "schema_version",
                "item_id",
                "summary",
                "phase",
                "role",
                "invocation_id",
                "head_revision",
                "source_digest",
                "workspace",
                "allowed_paths",
                "instructions",
                "task_ids",
            },
            {"owner_authorized_paths", "source_branch"},
        )
        _schema(data)
        try:
            phase = Phase(_text(data["phase"], "request.phase"))
            role = Role(_text(data["role"], "request.role"))
        except ValueError as error:
            raise ModelError(str(error)) from error
        return cls(
            item_id=_identifier(data["item_id"], "request.item_id"),
            summary=_text(data["summary"], "request.summary"),
            phase=phase,
            role=role,
            invocation_id=_identifier(data["invocation_id"], "request.invocation_id"),
            head_revision=_revision(data["head_revision"], "request.head_revision"),
            source_digest=_digest(data["source_digest"], "request.source_digest"),
            workspace=_text(data["workspace"], "request.workspace"),
            allowed_paths=_string_list(
                data["allowed_paths"], "request.allowed_paths", limit=32
            ),
            instructions=_text(data["instructions"], "request.instructions"),
            task_ids=_string_list(data["task_ids"], "request.task_ids"),
            owner_authorized_paths=_path_list(
                data.get("owner_authorized_paths", []),
                "request.owner_authorized_paths",
            ),
            source_branch=_branch(
                data.get("source_branch", ""), "request.source_branch", empty=True
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "item_id": self.item_id,
            "summary": self.summary,
            "phase": self.phase.value,
            "role": self.role.value,
            "invocation_id": self.invocation_id,
            "head_revision": self.head_revision,
            "source_digest": self.source_digest,
            "workspace": self.workspace,
            "allowed_paths": self.allowed_paths,
            "instructions": self.instructions,
            "task_ids": self.task_ids,
            "owner_authorized_paths": self.owner_authorized_paths,
            "source_branch": self.source_branch,
        }


@dataclass(frozen=True)
class AgentResult:
    """Untrusted semantic result emitted by a host-side agent adapter."""

    result: HandoffResult
    task_ids: list[str]
    checks: list[CheckResult]
    findings: list[str]
    owner_requests: list[OwnerRequest]
    next_phase: Phase | None
    diagnostic_code: str

    @classmethod
    def from_dict(cls, value: object) -> AgentResult:
        data = _mapping(value, "agent result")
        _strict(
            data,
            {
                "result",
                "task_ids",
                "checks",
                "findings",
                "owner_requests",
                "next_phase",
                "diagnostic_code",
            },
        )
        try:
            result = HandoffResult(_text(data["result"], "agent_result.result"))
            next_phase = (
                None
                if data["next_phase"] is None
                else Phase(_text(data["next_phase"], "agent_result.next_phase"))
            )
        except ValueError as error:
            raise ModelError(str(error)) from error
        checks_raw = data["checks"]
        requests_raw = data["owner_requests"]
        if not isinstance(checks_raw, list) or len(checks_raw) > 100:
            raise ModelError("agent_result.checks must contain at most 100 entries")
        if not isinstance(requests_raw, list) or len(requests_raw) > 20:
            raise ModelError(
                "agent_result.owner_requests must contain at most 20 entries"
            )
        owner_requests = [OwnerRequest.from_dict(request) for request in requests_raw]
        decision_ids = [request.decision_id for request in owner_requests]
        if len(decision_ids) != len(set(decision_ids)):
            raise ModelError(
                "agent_result.owner_requests contains duplicate decision IDs"
            )
        return cls(
            result=result,
            task_ids=_string_list(data["task_ids"], "agent_result.task_ids"),
            checks=[CheckResult.from_dict(check) for check in checks_raw],
            findings=_string_list(data["findings"], "agent_result.findings"),
            owner_requests=owner_requests,
            next_phase=next_phase,
            diagnostic_code=_identifier(
                data["diagnostic_code"], "agent_result.diagnostic_code"
            ),
        )

    def to_handoff(
        self,
        request: AgentRequest,
        *,
        staged_digest: str,
        changed_paths: list[str],
    ) -> AgentHandoff:
        return AgentHandoff(
            item_id=request.item_id,
            phase=request.phase,
            role=request.role,
            invocation_id=request.invocation_id,
            result=self.result,
            head_revision=request.head_revision,
            source_digest=request.source_digest,
            staged_digest=_digest(staged_digest, "agent_result.staged_digest"),
            task_ids=self.task_ids,
            changed_paths=_path_list(
                changed_paths, "agent_result.changed_paths", limit=1_000
            ),
            checks=self.checks,
            findings=self.findings,
            owner_requests=self.owner_requests,
            next_phase=self.next_phase,
            diagnostic_code=self.diagnostic_code,
        )


@dataclass(frozen=True)
class AgentHandoff:
    item_id: str
    phase: Phase
    role: Role
    invocation_id: str
    result: HandoffResult
    head_revision: str
    source_digest: str
    staged_digest: str
    task_ids: list[str]
    changed_paths: list[str]
    checks: list[CheckResult]
    findings: list[str]
    owner_requests: list[OwnerRequest]
    next_phase: Phase | None
    diagnostic_code: str

    @classmethod
    def from_dict(cls, value: object) -> AgentHandoff:
        data = _mapping(value, "agent handoff")
        _strict(
            data,
            {
                "schema_version",
                "item_id",
                "phase",
                "role",
                "invocation_id",
                "result",
                "head_revision",
                "source_digest",
                "staged_digest",
                "task_ids",
                "changed_paths",
                "checks",
                "findings",
                "owner_requests",
                "next_phase",
                "diagnostic_code",
            },
        )
        _schema(data)
        try:
            phase = Phase(_text(data["phase"], "handoff.phase"))
            role = Role(_text(data["role"], "handoff.role"))
            result = HandoffResult(_text(data["result"], "handoff.result"))
            next_phase = (
                None
                if data["next_phase"] is None
                else Phase(_text(data["next_phase"], "handoff.next_phase"))
            )
        except ValueError as error:
            raise ModelError(str(error)) from error
        checks_raw = data["checks"]
        requests_raw = data["owner_requests"]
        if not isinstance(checks_raw, list) or len(checks_raw) > 100:
            raise ModelError("handoff.checks must contain at most 100 entries")
        if not isinstance(requests_raw, list) or len(requests_raw) > 20:
            raise ModelError("handoff.owner_requests must contain at most 20 entries")
        owner_requests = [OwnerRequest.from_dict(request) for request in requests_raw]
        decision_ids = [request.decision_id for request in owner_requests]
        if len(decision_ids) != len(set(decision_ids)):
            raise ModelError("handoff.owner_requests contains duplicate decision IDs")
        return cls(
            item_id=_identifier(data["item_id"], "handoff.item_id"),
            phase=phase,
            role=role,
            invocation_id=_identifier(data["invocation_id"], "handoff.invocation_id"),
            result=result,
            head_revision=_revision(data["head_revision"], "handoff.head_revision"),
            source_digest=_digest(data["source_digest"], "handoff.source_digest"),
            staged_digest=_digest(data["staged_digest"], "handoff.staged_digest"),
            task_ids=_string_list(data["task_ids"], "handoff.task_ids"),
            changed_paths=_string_list(
                data["changed_paths"], "handoff.changed_paths", limit=1_000
            ),
            checks=[CheckResult.from_dict(check) for check in checks_raw],
            findings=_string_list(data["findings"], "handoff.findings"),
            owner_requests=owner_requests,
            next_phase=next_phase,
            diagnostic_code=_identifier(
                data["diagnostic_code"], "handoff.diagnostic_code"
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "item_id": self.item_id,
            "phase": self.phase.value,
            "role": self.role.value,
            "invocation_id": self.invocation_id,
            "result": self.result.value,
            "head_revision": self.head_revision,
            "source_digest": self.source_digest,
            "staged_digest": self.staged_digest,
            "task_ids": self.task_ids,
            "changed_paths": self.changed_paths,
            "checks": [check.to_dict() for check in self.checks],
            "findings": self.findings,
            "owner_requests": [
                owner_request.to_dict() for owner_request in self.owner_requests
            ],
            "next_phase": None if self.next_phase is None else self.next_phase.value,
            "diagnostic_code": self.diagnostic_code,
        }


@dataclass(frozen=True)
class Checkpoint:
    item_id: str
    phase: Phase
    queue_status: QueueStatus
    head_revision: str
    source_digest: str
    invocation_id: str | None
    updated_at: str
    branch_name: str = ""

    @classmethod
    def from_dict(cls, value: object) -> Checkpoint:
        data = _mapping(value, "checkpoint")
        _strict(
            data,
            {
                "schema_version",
                "item_id",
                "phase",
                "queue_status",
                "head_revision",
                "source_digest",
                "invocation_id",
                "updated_at",
                "branch_name",
            },
        )
        if data.get("schema_version") != STATE_SCHEMA_VERSION:
            raise ModelError(
                f"unsupported checkpoint state schema_version: "
                f"{data.get('schema_version')!r}"
            )
        try:
            phase = Phase(_text(data["phase"], "checkpoint.phase"))
            status = QueueStatus(_text(data["queue_status"], "checkpoint.queue_status"))
        except ValueError as error:
            raise ModelError(str(error)) from error
        invocation = data["invocation_id"]
        return cls(
            item_id=_identifier(data["item_id"], "checkpoint.item_id"),
            phase=phase,
            queue_status=status,
            head_revision=_revision(data["head_revision"], "checkpoint.head_revision"),
            source_digest=_digest(data["source_digest"], "checkpoint.source_digest"),
            invocation_id=(
                None
                if invocation is None
                else _identifier(invocation, "checkpoint.invocation_id")
            ),
            updated_at=_timestamp(data["updated_at"], "checkpoint.updated_at"),
            branch_name=_branch(
                data["branch_name"], "checkpoint.branch_name", empty=True
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "item_id": self.item_id,
            "phase": self.phase.value,
            "queue_status": self.queue_status.value,
            "head_revision": self.head_revision,
            "source_digest": self.source_digest,
            "invocation_id": self.invocation_id,
            "updated_at": self.updated_at,
            "branch_name": self.branch_name,
        }


@dataclass(frozen=True)
class Lease:
    owner_id: str
    acquired_at: str
    expires_at: str
    invocation_id: str

    @classmethod
    def from_dict(cls, value: object) -> Lease:
        data = _mapping(value, "lease")
        _strict(
            data,
            {
                "schema_version",
                "owner_id",
                "acquired_at",
                "expires_at",
                "invocation_id",
            },
        )
        _schema(data)
        acquired_at = _timestamp(data["acquired_at"], "lease.acquired_at")
        expires_at = _timestamp(data["expires_at"], "lease.expires_at")
        acquired = datetime.fromisoformat(acquired_at.replace("Z", "+00:00"))
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires <= acquired:
            raise ModelError("lease.expires_at must be later than acquired_at")
        return cls(
            owner_id=_text(data["owner_id"], "lease.owner_id"),
            acquired_at=acquired_at,
            expires_at=expires_at,
            invocation_id=_identifier(data["invocation_id"], "lease.invocation_id"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "owner_id": self.owner_id,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
            "invocation_id": self.invocation_id,
        }


@dataclass(frozen=True)
class OwnerDecision:
    decision_id: str
    item_id: str
    phase: Phase
    state_digest: str
    owner: str
    answer: str
    rationale: str

    @classmethod
    def from_markdown_fields(cls, fields: dict[str, str]) -> OwnerDecision:
        required = {
            "Schema version",
            "Decision ID",
            "Item",
            "Phase",
            "State digest",
            "Owner",
            "Answer",
            "Rationale",
        }
        missing = required - fields.keys()
        if missing:
            raise ModelError(
                f"owner decision missing field(s): {', '.join(sorted(missing))}"
            )
        unknown = fields.keys() - required
        if unknown:
            raise ModelError(
                f"owner decision has unknown field(s): {', '.join(sorted(unknown))}"
            )
        if fields["Schema version"] != str(SCHEMA_VERSION):
            raise ModelError("unsupported owner decision schema version")
        try:
            phase = Phase(fields["Phase"])
        except ValueError as error:
            raise ModelError(str(error)) from error
        return cls(
            decision_id=_identifier(fields["Decision ID"], "decision.decision_id"),
            item_id=_identifier(fields["Item"], "decision.item_id"),
            phase=phase,
            state_digest=_digest(fields["State digest"], "decision.state_digest"),
            owner=_text(fields["Owner"], "decision.owner"),
            answer=_text(fields["Answer"], "decision.answer"),
            rationale=_text(fields["Rationale"], "decision.rationale"),
        )


@dataclass(frozen=True)
class Event:
    item_id: str
    time: str
    invocation_id: str
    previous_state: Phase
    event_type: str
    details: dict[str, Any]

    @classmethod
    def from_dict(cls, value: object) -> Event:
        data = _mapping(value, "event")
        _strict(
            data,
            {
                "schema_version",
                "item_id",
                "time",
                "invocation_id",
                "previous_state",
                "type",
                "details",
            },
        )
        _schema(data)
        try:
            previous_state = Phase(
                _text(data["previous_state"], "event.previous_state")
            )
        except ValueError as error:
            raise ModelError(str(error)) from error
        event_type = _identifier(data["type"], "event.type")
        if event_type not in EVENT_TYPES:
            raise ModelError("event.type is not a supported orchestration event")
        invocation_id = _identifier(data["invocation_id"], "event.invocation_id")
        if event_type == "owner-decision" and invocation_id != "host":
            raise ModelError("owner-decision event must use the host invocation")
        if (
            event_type
            in {
                "host-visual-gate",
                "verification-passed",
            }
            and invocation_id != "controller"
        ):
            raise ModelError(f"{event_type} event must use the controller invocation")
        if event_type in {
            "awaiting-owner",
            "handoff-recovered",
            "status-change",
            "transition",
        } and invocation_id in {"host", "controller"}:
            raise ModelError("agent event must reference an agent invocation")
        return cls(
            item_id=_identifier(data["item_id"], "event.item_id"),
            time=_timestamp(data["time"], "event.time"),
            invocation_id=invocation_id,
            previous_state=previous_state,
            event_type=event_type,
            details=_mapping(data["details"], "event.details"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "item_id": self.item_id,
            "time": self.time,
            "invocation_id": self.invocation_id,
            "previous_state": self.previous_state.value,
            "type": self.event_type,
            "details": self.details,
        }
