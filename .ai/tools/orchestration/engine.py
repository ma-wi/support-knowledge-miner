"""Pure queue selection and transition validation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .model import (
    AgentHandoff,
    AgentRequest,
    HandoffResult,
    ModelError,
    Phase,
    Queue,
    QueueItem,
    QueueStatus,
    Role,
)

ITEM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_INTAKE_BYTES = 262_144
MAX_INTAKE_ITEMS = 100
LIST_ITEM = re.compile(r"^-\s+\[(?P<meta>[^\]]*)\]\s+(?P<summary>\S.*)$")

ROLE_BY_PHASE = {
    Phase.INTAKE: Role.PLANNER,
    Phase.DISCOVERY: Role.PLANNER,
    Phase.SPECIFICATION: Role.PLANNER,
    Phase.DESIGN: Role.PLANNER,
    Phase.PLANNING: Role.PLANNER,
    Phase.IMPLEMENTATION: Role.IMPLEMENTER,
    Phase.VERIFICATION: Role.CONTROLLER,
    Phase.CODE_REVIEW: Role.CODE_REVIEWER,
    Phase.VISUAL_REVIEW: Role.VISUAL_REVIEWER,
    Phase.REMEDIATION: Role.IMPLEMENTER,
    Phase.CLOSEOUT: Role.IMPLEMENTER,
    Phase.DONE: Role.CONTROLLER,
}

ALLOWED_TRANSITIONS: dict[Phase, set[Phase]] = {
    Phase.INTAKE: {Phase.DISCOVERY, Phase.SPECIFICATION, Phase.PLANNING},
    Phase.DISCOVERY: {Phase.SPECIFICATION, Phase.PLANNING},
    Phase.SPECIFICATION: {Phase.DESIGN, Phase.PLANNING},
    Phase.DESIGN: {Phase.PLANNING},
    Phase.PLANNING: {Phase.IMPLEMENTATION},
    Phase.IMPLEMENTATION: {Phase.VERIFICATION},
    Phase.VERIFICATION: {Phase.CODE_REVIEW},
    Phase.CODE_REVIEW: {
        Phase.IMPLEMENTATION,
        Phase.REMEDIATION,
        Phase.VISUAL_REVIEW,
        Phase.CLOSEOUT,
    },
    Phase.VISUAL_REVIEW: {
        Phase.IMPLEMENTATION,
        Phase.REMEDIATION,
        Phase.CLOSEOUT,
    },
    Phase.REMEDIATION: {Phase.VERIFICATION},
    Phase.CLOSEOUT: {Phase.DONE},
    Phase.DONE: set(),
}


class EngineError(RuntimeError):
    """Raised when queue or transition state is invalid."""


@dataclass(frozen=True)
class ParsedItem:
    item_id: str
    summary: str
    priority: int
    depends_on: list[str]


def normalize_summary(value: str) -> str:
    return " ".join(value.split())


def generated_id(summary: str) -> str:
    digest = hashlib.sha256(normalize_summary(summary).encode("utf-8")).hexdigest()
    return f"REQ-{digest[:12]}"


def _parse_metadata(raw: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for token in raw.split():
        if "=" not in token:
            raise EngineError(f"invalid intake metadata token: {token!r}")
        key, value = token.split("=", 1)
        if key not in {"id", "priority", "depends"}:
            raise EngineError(f"unknown intake metadata key: {key}")
        if key in metadata:
            raise EngineError(f"duplicate intake metadata key: {key}")
        metadata[key] = value
    return metadata


def parse_intake(
    content: str, *, existing_ids: set[str] | None = None
) -> list[QueueItem]:
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_INTAKE_BYTES:
        raise EngineError(f"intake exceeds {MAX_INTAKE_BYTES} bytes")
    lines = [line.rstrip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise EngineError("intake is empty")
    matches = [LIST_ITEM.fullmatch(line) for line in lines]
    parsed: list[ParsedItem] = []
    if any(match is not None for match in matches):
        if not all(match is not None for match in matches):
            raise EngineError("intake must not mix list and non-list content")
        if len(lines) > MAX_INTAKE_ITEMS:
            raise EngineError(f"intake exceeds {MAX_INTAKE_ITEMS} items")
        for match in matches:
            if match is None:
                raise EngineError("intake list parsing failed")
            metadata = _parse_metadata(match.group("meta"))
            summary = normalize_summary(match.group("summary"))
            item_id = metadata.get("id", generated_id(summary))
            if not ITEM_ID.fullmatch(item_id):
                raise EngineError(f"invalid item ID: {item_id!r}")
            priority_raw = metadata.get("priority", "0")
            if not priority_raw.isdigit():
                raise EngineError(f"invalid priority for {item_id}")
            priority = int(priority_raw)
            if priority > 1_000_000:
                raise EngineError(f"priority is too large for {item_id}")
            depends = (
                [] if not metadata.get("depends") else metadata["depends"].split(",")
            )
            if any(not ITEM_ID.fullmatch(item) for item in depends):
                raise EngineError(f"invalid dependency for {item_id}")
            if len(depends) != len(set(depends)):
                raise EngineError(f"duplicate dependency for {item_id}")
            parsed.append(ParsedItem(item_id, summary, priority, depends))
    else:
        summary = normalize_summary(content)
        parsed.append(ParsedItem(generated_id(summary), summary, 0, []))
    ids = [item.item_id for item in parsed]
    summaries = [normalize_summary(item.summary).casefold() for item in parsed]
    if len(ids) != len(set(ids)):
        raise EngineError("intake contains duplicate IDs")
    if len(summaries) != len(set(summaries)):
        raise EngineError("intake contains duplicate summaries")
    known = set(ids) | (existing_ids or set())
    for item in parsed:
        missing = set(item.depends_on) - known
        if missing:
            raise EngineError(
                f"{item.item_id} depends on missing item(s): {', '.join(sorted(missing))}"
            )
        if item.item_id in item.depends_on:
            raise EngineError(f"{item.item_id} depends on itself")
    _validate_acyclic(parsed)
    result = [
        QueueItem(
            item_id=item.item_id,
            summary=item.summary,
            priority=item.priority,
            depends_on=item.depends_on,
            sequence=index,
        )
        for index, item in enumerate(parsed)
    ]
    # Apply the persisted model's bounds before intake mutates durable state.
    try:
        Queue.from_dict(Queue(result).to_dict())
    except ModelError as error:
        raise EngineError(f"invalid intake: {error}") from error
    return result


def _validate_acyclic(items: list[ParsedItem]) -> None:
    graph = {item.item_id: item.depends_on for item in items}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            raise EngineError("intake dependency graph contains a cycle")
        if item_id in visited:
            return
        visiting.add(item_id)
        for dependency in graph[item_id]:
            if dependency in graph:
                visit(dependency)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in graph:
        visit(item_id)


def merge_intake(queue: Queue, incoming: list[QueueItem]) -> Queue:
    existing_ids = {item.item_id for item in queue.items}
    existing_summaries = {
        normalize_summary(item.summary).casefold() for item in queue.items
    }
    for item in incoming:
        if item.item_id in existing_ids:
            raise EngineError(f"queue already contains item ID {item.item_id}")
        if normalize_summary(item.summary).casefold() in existing_summaries:
            raise EngineError(f"queue already contains summary {item.summary!r}")
    sequence = max((item.sequence for item in queue.items), default=-1) + 1
    for offset, item in enumerate(incoming):
        item.sequence = sequence + offset
    result = Queue([*queue.items, *incoming])
    validate_queue(result)
    return result


def select_next(queue: Queue) -> QueueItem | None:
    validate_queue(queue)
    active = [
        item
        for item in queue.items
        if item.status
        in {
            QueueStatus.ACTIVE,
            QueueStatus.AWAITING_OWNER,
            QueueStatus.BLOCKED,
        }
    ]
    if len(active) > 1:
        raise EngineError("queue contains more than one active item")
    if active:
        return active[0]
    completed = {
        item.item_id for item in queue.items if item.status is QueueStatus.COMPLETED
    }
    eligible = [
        item
        for item in queue.items
        if item.status is QueueStatus.PENDING
        and set(item.depends_on).issubset(completed)
    ]
    if not eligible:
        return None
    return sorted(eligible, key=lambda item: (-item.priority, item.sequence))[0]


def validate_queue(queue: Queue) -> None:
    ids = {item.item_id for item in queue.items}
    sequences = [item.sequence for item in queue.items]
    if len(sequences) != len(set(sequences)):
        raise EngineError("queue contains duplicate sequence numbers")
    graph = {item.item_id: item.depends_on for item in queue.items}
    branches = [item.branch_name for item in queue.items if item.branch_name]
    if len(branches) != len(set(branches)):
        raise EngineError("queue contains duplicate item branches")
    commits = [item.commit_revision for item in queue.items if item.commit_revision]
    if len(commits) != len(set(commits)):
        raise EngineError("queue contains duplicate closeout commits")
    for item in queue.items:
        if (item.status is QueueStatus.COMPLETED) != (item.phase is Phase.DONE):
            raise EngineError(f"{item.item_id} has inconsistent completed/done state")
        missing = set(item.depends_on) - ids
        if missing:
            raise EngineError(
                f"{item.item_id} depends on missing item(s): "
                + ", ".join(sorted(missing))
            )
        if item.item_id in item.depends_on:
            raise EngineError(f"{item.item_id} depends on itself")
        has_branch_intent = bool(item.branch_name or item.base_revision)
        if bool(item.branch_name) != (item.base_revision is not None):
            raise EngineError(f"{item.item_id} has incomplete branch intent")
        if item.branch_ready and not has_branch_intent:
            raise EngineError(f"{item.item_id} is branch-ready without branch intent")
        if (
            queue.run_git is not None
            and item.status is not QueueStatus.PENDING
            and not item.branch_ready
        ):
            raise EngineError(f"{item.item_id} has no activated item branch")
        if (
            queue.run_git is not None
            and item.status is QueueStatus.COMPLETED
            and item.commit_revision is None
        ):
            raise EngineError(f"{item.item_id} completed without a closeout commit")
        if (
            queue.run_git is not None
            and item.status is QueueStatus.COMPLETED
            and any(
                value is None
                for value in (
                    item.reviewed_source_digest,
                    item.expected_closeout_digest,
                    item.expected_commit_tree,
                )
            )
        ):
            raise EngineError(f"{item.item_id} completed without exact commit facts")
        if (
            item.commit_revision is not None
            and item.status is not QueueStatus.COMPLETED
        ):
            raise EngineError(f"{item.item_id} has a commit before completion")
        if (
            item.expected_commit_tree is not None
            and item.expected_closeout_digest is None
        ):
            raise EngineError(f"{item.item_id} has a tree without closeout intent")
    if queue.run_git is not None:
        if bool(queue.run_git.latest_branch) != bool(queue.run_git.latest_commit):
            raise EngineError("latest deliverable branch and commit are incomplete")
        if queue.run_git.latest_commit is not None and not any(
            item.branch_name == queue.run_git.latest_branch
            and item.commit_revision == queue.run_git.latest_commit
            for item in queue.items
        ):
            raise EngineError(
                "latest deliverable does not match a completed queue item"
            )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            raise EngineError("queue dependency graph contains a cycle")
        if item_id in visited:
            return
        visiting.add(item_id)
        for dependency in graph[item_id]:
            visit(dependency)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in graph:
        visit(item_id)


def validate_handoff(request: AgentRequest, handoff: AgentHandoff) -> None:
    comparisons = (
        ("item_id", request.item_id, handoff.item_id),
        ("phase", request.phase, handoff.phase),
        ("role", request.role, handoff.role),
        ("invocation_id", request.invocation_id, handoff.invocation_id),
        ("head_revision", request.head_revision, handoff.head_revision),
        ("source_digest", request.source_digest, handoff.source_digest),
    )
    for label, expected, actual in comparisons:
        if expected != actual:
            raise EngineError(
                f"handoff {label} mismatch: expected {expected!r}, got {actual!r}"
            )
    if handoff.result in {
        HandoffResult.NEEDS_OWNER_DECISION,
        HandoffResult.RETRYABLE_FAILURE,
        HandoffResult.BLOCKED,
        HandoffResult.INVALID_STATE,
    } and (handoff.changed_paths or handoff.staged_digest != request.source_digest):
        raise EngineError(
            f"{handoff.result.value} handoff must not contain a repository delta"
        )
    if handoff.result is HandoffResult.COMPLETED:
        if handoff.next_phase is None:
            raise EngineError("completed handoff must propose a next phase")
        if handoff.next_phase not in ALLOWED_TRANSITIONS[request.phase]:
            raise EngineError(
                f"transition {request.phase.value} -> "
                f"{handoff.next_phase.value} is not allowed"
            )
        if handoff.next_phase is Phase.REMEDIATION:
            raise EngineError(
                "completed review cannot enter remediation without findings"
            )
    elif handoff.result is HandoffResult.NEEDS_REMEDIATION:
        if request.phase not in {Phase.CODE_REVIEW, Phase.VISUAL_REVIEW}:
            raise EngineError("only a reviewer may request remediation")
        if handoff.next_phase is not Phase.REMEDIATION:
            raise EngineError("remediation handoff must propose remediation")
        if not handoff.findings:
            raise EngineError("remediation handoff must contain review findings")
    elif handoff.next_phase is not None:
        raise EngineError(
            f"{handoff.result.value} handoff must not propose a next phase"
        )
    if handoff.result is HandoffResult.NEEDS_OWNER_DECISION:
        if not handoff.owner_requests:
            raise EngineError("owner-decision handoff has no owner request")
    elif handoff.owner_requests:
        raise EngineError("owner requests require needs-owner-decision result")


def role_for_phase(phase: Phase) -> Role:
    return ROLE_BY_PHASE[phase]


def advance(item: QueueItem, next_phase: Phase) -> None:
    if next_phase not in ALLOWED_TRANSITIONS[item.phase]:
        raise ModelError(f"invalid transition {item.phase.value} -> {next_phase.value}")
    item.phase = next_phase
    item.active_invocation_id = None
    item.retry_count = 0
    item.failure_signature = None
    item.identical_failure_count = 0
    item.next_attempt_at = None
    if next_phase is Phase.DONE:
        item.status = QueueStatus.COMPLETED
    else:
        item.status = QueueStatus.ACTIVE
