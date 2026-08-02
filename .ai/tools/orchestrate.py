#!/usr/bin/env python3
"""CLI for deterministic repository-native agent orchestration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import stat
import subprocess  # nosec B404
import sys
import threading
import uuid
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import get, load_yaml_subset, parse_version_requirement  # noqa: E402
from orchestration.engine import (  # noqa: E402
    EngineError,
    advance,
    merge_intake,
    parse_intake,
    role_for_phase,
    select_next,
    validate_handoff,
)
from orchestration.executor import (  # noqa: E402
    CommandExecutor,
    ExecutionResult,
    ExecutorConfig,
    ExecutorError,
    allowed_prefixes,
    clear_promotion_journal,
    probe_codex_runtime,
    restore_promotion_journal,
    validate_codex_runtime,
    validate_remediation_findings,
)
from orchestration.git_lifecycle import (  # noqa: E402
    GitLifecycle,
    GitLifecycleError,
)
from orchestration.model import (  # noqa: E402
    AgentHandoff,
    AgentRequest,
    Checkpoint,
    HandoffResult,
    Lease,
    ModelError,
    OwnerDecision,
    OwnerRequest,
    Phase,
    Queue,
    QueueItem,
    QueueStatus,
    Role,
    RunGitState,
    SCHEMA_VERSION,
)
from orchestration.reconcile import (  # noqa: E402
    ReconcileError,
    RepositoryState,
    changed_paths,
    ensure_clean,
    reconcile_checkpoint,
    run_lifecycle_validator,
    snapshot,
)
from orchestration.store import (  # noqa: E402
    StateStore,
    StoreError,
    iso_time,
    parse_time,
    utc_now,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".ai" / "project.yaml"
FIELD = re.compile(r"^-\s*([^:]+):\s*(.*?)\s*$")
EXIT_SUCCESS = 0
EXIT_OWNER = 20
EXIT_BLOCKED = 30
EXIT_CONFIG = 40
EXIT_INTERNAL = 50
MAX_CONTROLLER_OUTPUT = 262_144
TASK_FIELD = re.compile(r"(?im)^-\s*([^:\n]+):\s*(.*?)\s*$")
TASK_HEADING = re.compile(r"(?im)^#\s*Task\s+([A-Za-z0-9][A-Za-z0-9._-]*)")


class CliError(RuntimeError):
    """Expected safe user-facing CLI failure."""


class ConfigError(CliError):
    """Raised for disabled, missing, or invalid orchestration configuration."""


def _read_bounded_utf8(path: Path, maximum: int, label: str) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise CliError(f"{label} must be a readable regular file") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CliError(f"{label} must be a regular file")
        if metadata.st_size > maximum:
            raise CliError(f"{label} exceeds {maximum} bytes")
        content = bytearray()
        while len(content) <= maximum:
            chunk = os.read(descriptor, min(65_536, maximum + 1 - len(content)))
            if not chunk:
                break
            content.extend(chunk)
        if len(content) > maximum:
            raise CliError(f"{label} exceeds {maximum} bytes")
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise CliError(f"{label} must be readable UTF-8") from error
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class OrchestrationConfig:
    enabled: bool
    command: list[str]
    isolation_kind: str
    timeout_seconds: int
    max_attempts: int
    max_identical_failures: int
    lease_seconds: int
    owner: str
    executor_kind: str = "command"
    codex_expected_version: str = ""
    codex_model: str = ""
    codex_reasoning_effort: str = "high"
    external_repository_processing_approved: bool = False


def _positive_int(value: object, label: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise ConfigError(f"{label} must be an integer between 1 and {maximum}")
    return value


def load_config() -> OrchestrationConfig:
    data = load_yaml_subset(CONFIG)
    section = get(data, "orchestration", default={})
    if section == {}:
        return OrchestrationConfig(
            False,
            ["codex"],
            "codex-sandbox",
            1800,
            3,
            2,
            3600,
            "OWNER",
            "codex",
            "",
            "",
            "high",
            False,
        )
    if not isinstance(section, dict):
        raise ConfigError("orchestration configuration must be a mapping")
    allowed = {
        "enabled",
        "executor_kind",
        "executor_command",
        "executor_isolation",
        "agent_timeout_seconds",
        "max_attempts_per_phase",
        "max_identical_failures",
        "lease_seconds",
        "queue_strategy",
        "owner_delegation_profile",
        "owner",
        "codex_expected_version",
        "codex_model",
        "codex_reasoning_effort",
        "external_repository_processing_approved",
    }
    unknown = set(section) - allowed
    if unknown:
        raise ConfigError(
            "unknown orchestration configuration key(s): " + ", ".join(sorted(unknown))
        )
    enabled = section.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigError("orchestration.enabled must be true or false")
    executor_kind = section.get("executor_kind", "command")
    if executor_kind not in {"command", "codex"}:
        raise ConfigError("executor_kind must be command or codex")
    command = section.get("executor_command", [])
    if (
        not isinstance(command, list)
        or len(command) > 32
        or any(not isinstance(value, str) or not value for value in command)
    ):
        raise ConfigError("executor_command must be a bounded list of strings")
    isolation_default = "codex-sandbox" if executor_kind == "codex" else "bwrap"
    isolation_kind = section.get("executor_isolation", isolation_default)
    expected_isolation = "codex-sandbox" if executor_kind == "codex" else "bwrap"
    if isolation_kind != expected_isolation:
        raise ConfigError(
            f"executor_isolation must be {expected_isolation} for {executor_kind}"
        )
    expected_version = section.get("codex_expected_version", "")
    model = section.get("codex_model", "")
    reasoning = section.get("codex_reasoning_effort", "high")
    external_approved = section.get("external_repository_processing_approved", False)
    if executor_kind == "codex":
        if (
            len(command) != 1
            or not isinstance(command[0], str)
            or any(character in command[0] for character in "{}")
        ):
            raise ConfigError(
                "Codex executor_command must contain exactly one executable"
            )
        if not isinstance(expected_version, str) or (
            expected_version and parse_version_requirement(expected_version) is None
        ):
            raise ConfigError(
                "codex_expected_version must be empty or an exact or bounded "
                "numeric version requirement"
            )
        if not isinstance(model, str) or len(model) > 128:
            raise ConfigError("codex_model must be a short string")
        if reasoning not in {"low", "medium", "high", "xhigh"}:
            raise ConfigError("codex_reasoning_effort is unsupported")
        if not isinstance(external_approved, bool):
            raise ConfigError("external_repository_processing_approved must be boolean")
    if section.get("queue_strategy", "sequential") != "sequential":
        raise ConfigError("only sequential queue strategy is supported")
    if section.get("owner_delegation_profile", "local-host") != "local-host":
        raise ConfigError("only local-host owner delegation is supported")
    owner = section.get("owner", "OWNER")
    if not isinstance(owner, str) or not owner.strip() or len(owner) > 128:
        raise ConfigError("orchestration.owner must be a non-empty short string")
    timeout_seconds = _positive_int(
        section.get("agent_timeout_seconds", 1800),
        "agent_timeout_seconds",
        86_399,
    )
    lease_seconds = _positive_int(
        section.get("lease_seconds", 3600), "lease_seconds", 86_400
    )
    if lease_seconds <= timeout_seconds:
        raise ConfigError("lease_seconds must be greater than agent_timeout_seconds")
    return OrchestrationConfig(
        enabled=enabled,
        executor_kind=executor_kind,
        command=list(command),
        isolation_kind=isolation_kind,
        codex_expected_version=expected_version,
        codex_model=model,
        codex_reasoning_effort=reasoning,
        external_repository_processing_approved=external_approved,
        timeout_seconds=timeout_seconds,
        max_attempts=_positive_int(
            section.get("max_attempts_per_phase", 3),
            "max_attempts_per_phase",
            20,
        ),
        max_identical_failures=_positive_int(
            section.get("max_identical_failures", 2),
            "max_identical_failures",
            20,
        ),
        lease_seconds=lease_seconds,
        owner=owner.strip(),
    )


def _require_runnable(config: OrchestrationConfig) -> None:
    if not config.enabled:
        raise ConfigError("orchestration is disabled in .ai/project.yaml")
    if not config.command:
        raise ConfigError(
            "orchestration executor is not configured; no agent changes were made"
        )
    if (
        config.executor_kind == "codex"
        and not config.external_repository_processing_approved
    ):
        raise ConfigError(
            "Codex orchestration requires explicit external repository processing "
            "approval"
        )


def _executor_config(config: OrchestrationConfig) -> ExecutorConfig:
    return ExecutorConfig(
        command=config.command,
        timeout_seconds=config.timeout_seconds,
        isolation_kind=config.isolation_kind,
        kind=config.executor_kind,
        codex_expected_version=config.codex_expected_version,
        codex_model=config.codex_model,
        codex_reasoning_effort=config.codex_reasoning_effort,
    )


def _write_output(payload: Mapping[str, object], *, human: str) -> None:
    print(human)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _checkpoint(store: StateStore, item: QueueItem) -> Checkpoint:
    observed = snapshot(ROOT)
    checkpoint = Checkpoint(
        item_id=item.item_id,
        phase=item.phase,
        queue_status=item.status,
        head_revision=observed.head_revision,
        source_digest=observed.source_digest,
        invocation_id=item.active_invocation_id,
        updated_at=iso_time(),
        branch_name=item.branch_name or (observed.branch_name or ""),
    )
    store.save_checkpoint(checkpoint)
    return checkpoint


def _request_instructions(store: StateStore, item: QueueItem, role: Role) -> str:
    decisions_relative = f"runs/{item.item_id}/OWNER_DECISIONS.json"
    decisions = []
    path = store.resolve(decisions_relative)
    if path.is_file():
        raw = store.read_json(decisions_relative)
        value = raw.get("decisions", [])
        if isinstance(value, list):
            decisions = value
    decision_text = (
        " Confirmed owner decisions: "
        + json.dumps(decisions, ensure_ascii=False, separators=(",", ":"))
        if decisions
        else ""
    )
    return (
        f"Follow .ai/roles/{role.value.upper().replace('-', '_')}.md when present, "
        f"AGENTS.md, and the canonical policies. Work only on {item.item_id} during "
        f"phase {item.phase.value}. Objective: {item.summary}. "
        "Work only on the task/review batch IDs in the request; when eligible "
        "tasks remain after this batch, propose implementation rather than closeout. "
        "Return the strict result required by the configured executor adapter."
        f"{decision_text}"
    )


def _build_request(store: StateStore, item: QueueItem, role: Role) -> AgentRequest:
    observed = snapshot(ROOT)
    invocation_id = str(uuid.uuid4())
    item.active_invocation_id = invocation_id
    task_root = ROOT / ".ai" / "work" / item.item_id / "tasks"
    task_ids = _select_task_ids(task_root, item.phase)
    owner_authorized_paths: set[str] = set()
    decisions_path = f"runs/{item.item_id}/OWNER_DECISIONS.json"
    if store.resolve(decisions_path).is_file():
        decisions = store.read_json(decisions_path).get("decisions", [])
        if isinstance(decisions, list):
            for decision in decisions:
                if isinstance(decision, dict):
                    paths = decision.get("authorized_paths", [])
                    consumed = decision.get("consumed_paths", [])
                    if isinstance(paths, list) and isinstance(consumed, list):
                        owner_authorized_paths.update(
                            path
                            for path in paths
                            if isinstance(path, str) and path not in consumed
                        )
    return AgentRequest(
        item_id=item.item_id,
        summary=item.summary,
        phase=item.phase,
        role=role,
        invocation_id=invocation_id,
        head_revision=observed.head_revision,
        source_digest=observed.source_digest,
        workspace=".",
        allowed_paths=allowed_prefixes(role, item.item_id),
        instructions="",
        task_ids=task_ids,
        owner_authorized_paths=sorted(owner_authorized_paths),
        source_branch=item.branch_name,
    )


def _select_task_ids(task_root: Path, phase: Phase) -> list[str]:
    if not task_root.is_dir():
        return []
    records: dict[str, tuple[str, list[str], str]] = {}
    for path in sorted(task_root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        heading = TASK_HEADING.search(text)
        task_id = heading.group(1) if heading else path.stem
        if task_id in records:
            raise CliError(f"duplicate canonical task ID: {task_id}")
        fields = {
            match.group(1).strip().lower(): match.group(2).strip()
            for match in TASK_FIELD.finditer(text)
        }
        dependency_text = fields.get("depends on", "")
        dependencies = (
            []
            if dependency_text.lower() in {"", "none", "not-applicable"}
            else [value for value in re.split(r"[\s,;]+", dependency_text) if value]
        )
        records[task_id] = (
            fields.get("status", ""),
            dependencies,
            fields.get("review batch", "default"),
        )
    if phase in {
        Phase.INTAKE,
        Phase.DISCOVERY,
        Phase.SPECIFICATION,
        Phase.DESIGN,
        Phase.PLANNING,
    }:
        return sorted(records)
    unknown = sorted(
        dependency
        for _, dependencies, _ in records.values()
        for dependency in dependencies
        if dependency not in records
    )
    if unknown:
        raise CliError(
            "task dependency references unknown task(s): " + ", ".join(unknown)
        )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise CliError("task dependency graph contains a cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in records[task_id][1]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in records:
        visit(task_id)
    complete = {"verified", "reviewed", "done"}
    if phase in {Phase.CODE_REVIEW, Phase.VISUAL_REVIEW}:
        candidates = [
            task_id
            for task_id, (status, _, _) in records.items()
            if status == "verified"
        ]
    elif phase is Phase.CLOSEOUT:
        candidates = [
            task_id
            for task_id, (status, _, _) in records.items()
            if status == "reviewed"
        ]
    else:
        candidates = [
            task_id
            for task_id, (status, dependencies, _) in records.items()
            if status in {"ready", "in-progress", "implemented", "verified"}
            and all(records[dependency][0] in complete for dependency in dependencies)
        ]
    if not candidates:
        return []
    plan = task_root.parent / "PLAN.md"
    plan_text = plan.read_text(encoding="utf-8") if plan.is_file() else ""
    cadence_match = re.search(
        r"(?im)^-\s*Cadence:\s*(per-task|batch|feature)\s*$", plan_text
    )
    cadence = cadence_match.group(1) if cadence_match else "feature"
    maximum_match = re.search(
        r"(?im)^-\s*Maximum tasks per review batch:\s*([1-9][0-9]?)\s*$",
        plan_text,
    )
    maximum = int(maximum_match.group(1)) if maximum_match else 10
    project = load_yaml_subset(task_root.parents[3] / ".ai" / "project.yaml")
    configured_maximum = get(
        project,
        "incremental_changes",
        "max_tasks_per_review_batch",
        default=3,
    )
    if (
        isinstance(configured_maximum, bool)
        or not isinstance(configured_maximum, int)
        or not 1 <= configured_maximum <= 10
    ):
        raise CliError("configured maximum review batch size is invalid")
    maximum = min(maximum, configured_maximum)
    selected = sorted(candidates)
    if cadence == "per-task":
        return selected[:1]
    if cadence == "batch":
        first_batch = records[selected[0]][2]
        selected = [
            task_id for task_id in selected if records[task_id][2] == first_batch
        ]
    return selected[:maximum]


def _replace_request_instructions(
    request: AgentRequest, instructions: str
) -> AgentRequest:
    value = request.to_dict()
    value["instructions"] = instructions
    return AgentRequest.from_dict(value)


def _consume_owner_authorizations(
    store: StateStore, item_id: str, changed_paths: list[str]
) -> None:
    relative = f"runs/{item_id}/OWNER_DECISIONS.json"
    if not store.resolve(relative).is_file():
        return
    payload = store.read_json(relative)
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        raise CliError("stored owner decisions are invalid")
    changed = set(changed_paths)
    mutated = False
    for decision in decisions:
        if not isinstance(decision, dict):
            raise CliError("stored owner decision entry is invalid")
        paths = decision.get("authorized_paths", [])
        consumed = decision.get("consumed_paths", [])
        if not isinstance(consumed, list):
            raise CliError("stored owner decision consumption is invalid")
        newly_consumed = sorted(
            changed.intersection(path for path in paths if isinstance(path, str))
            - set(path for path in consumed if isinstance(path, str))
        )
        if newly_consumed:
            decision["consumed_paths"] = sorted([*consumed, *newly_consumed])
            mutated = True
    if mutated:
        store.write_json(relative, payload)


def _render_owner_inbox(store: StateStore, queue: Queue) -> None:
    lines = ["# Owner inbox", ""]
    count = 0
    for item in queue.items:
        if item.status is not QueueStatus.AWAITING_OWNER:
            continue
        relative = f"runs/{item.item_id}/OWNER_REQUESTS.json"
        if not store.resolve(relative).is_file():
            continue
        request_archive = store.read_json(relative).get("requests", [])
        if not isinstance(request_archive, list):
            raise CliError("stored owner request archive is invalid")
        resolved_relative = f"runs/{item.item_id}/OWNER_DECISIONS.json"
        resolved: set[str] = set()
        if store.resolve(resolved_relative).is_file():
            raw_decisions = store.read_json(resolved_relative).get("decisions", [])
            if isinstance(raw_decisions, list):
                resolved = {
                    value["decision_id"]
                    for value in raw_decisions
                    if isinstance(value, dict)
                    and isinstance(value.get("decision_id"), str)
                }
        for record in request_archive:
            if not isinstance(record, dict):
                raise CliError("stored owner request record is invalid")
            request = OwnerRequest.from_dict(record.get("request"))
            if request.decision_id in resolved:
                continue
            count += 1
            lines.extend(
                [
                    f"## {request.decision_id}",
                    "",
                    f"- Item: {item.item_id}",
                    f"- Phase: {item.phase.value}",
                    f"- Question: {request.question}",
                    f"- Recommendation: {request.recommendation}",
                    f"- Alternatives: {'; '.join(request.alternatives) or 'none'}",
                    f"- Risks: {request.risks}",
                    f"- Allowed answers: {', '.join(request.allowed_answers)}",
                    "- Authorized paths: "
                    + (
                        ", ".join(request.authorized_paths)
                        if request.authorized_paths
                        else "none"
                    ),
                    "- Authorizing answers: "
                    + (
                        ", ".join(request.authorizing_answers)
                        if request.authorizing_answers
                        else "none"
                    ),
                    f"- Default: {request.default or 'none'}",
                    "",
                ]
            )
    if count == 0:
        lines.append("No open owner decisions.")
    store.write_bytes("OWNER_INBOX.md", ("\n".join(lines) + "\n").encode("utf-8"))


def _archive_owner_requests(
    store: StateStore,
    item: QueueItem,
    handoff: AgentHandoff,
    state_digest: str,
) -> None:
    relative = f"runs/{item.item_id}/OWNER_REQUESTS.json"
    records: list[dict[str, object]] = []
    if store.resolve(relative).is_file():
        raw = store.read_json(relative).get("requests", [])
        if not isinstance(raw, list):
            raise CliError("stored owner request archive is invalid")
        records = [record for record in raw if isinstance(record, dict)]
    known: dict[str, dict[str, object]] = {}
    for archived_record in records:
        archived_request = archived_record.get("request")
        if not isinstance(archived_request, dict):
            continue
        decision_id = archived_request.get("decision_id")
        if isinstance(decision_id, str):
            known[decision_id] = archived_record
    for owner_request in handoff.owner_requests:
        record: dict[str, object] = {
            "phase": item.phase.value,
            "state_digest": state_digest,
            "request": owner_request.to_dict(),
        }
        existing = known.get(owner_request.decision_id)
        if existing is not None:
            if existing != record:
                raise CliError("owner decision ID was reused across invocations")
            continue
        records.append(record)
    store.write_json(relative, {"schema_version": SCHEMA_VERSION, "requests": records})


@contextmanager
def _serialized_mutation(store: StateStore, lease_seconds: int):
    owner_id = f"{socket.gethostname()}:{os.getpid()}"
    lease, _ = store.acquire_lease(
        owner_id,
        str(uuid.uuid4()),
        lease_seconds,
        allow_takeover=False,
    )
    try:
        yield
    finally:
        if store.resolve("LEASE.json").exists():
            store.release_lease(lease)


def _set_current_phase(phase: Phase) -> None:
    current = ROOT / ".ai" / "CURRENT_PLAN.md"
    if phase in {Phase.INTAKE, Phase.DONE}:
        if phase is Phase.DONE:
            current.write_text(
                "# Current work\n\nNo active requirement.\n", encoding="utf-8"
            )
        return
    text = current.read_text(encoding="utf-8")
    if phase is Phase.DESIGN and re.search(
        r"(?im)^-\s*Status:\s*design-(?:draft|review)\s*$", text
    ):
        return
    mapping = {Phase.DESIGN: "design-draft", Phase.CODE_REVIEW: "review"}
    target = mapping.get(phase, phase.value)
    updated, count = re.subn(
        r"(?im)^(-\s*Status:\s*).*$", rf"\g<1>{target}", text, count=1
    )
    if count != 1:
        raise CliError("CURRENT_PLAN.md has no Status field for phase transition")
    temporary = current.with_name(".CURRENT_PLAN.md.orchestrator")
    temporary.write_text(updated, encoding="utf-8")
    os.replace(temporary, current)


def _run_verification() -> None:
    process = subprocess.Popen(  # nosec B603
        [os.fspath(ROOT / ".ai" / "tools" / "verify.sh")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=os.name == "posix",
    )
    pipe = process.stdout
    if pipe is None:
        raise CliError("could not capture authoritative verification output")
    output = bytearray()
    truncated = [False]

    def read_output() -> None:
        while True:
            chunk = pipe.read(8192)
            if not chunk:
                return
            output.extend(chunk)
            if len(output) > MAX_CONTROLLER_OUTPUT:
                del output[: len(output) - MAX_CONTROLLER_OUTPUT]
                truncated[0] = True

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        return_code = process.wait(timeout=3600)
    except subprocess.TimeoutExpired as error:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        reader.join(timeout=5)
        pipe.close()
        raise CliError("authoritative verification timed out") from error
    reader.join(timeout=5)
    pipe.close()
    if reader.is_alive():
        raise CliError("authoritative verification output did not close")
    if return_code != 0:
        decoded = output.decode("utf-8", errors="replace")
        summary = " | ".join(decoded.strip().splitlines()[-3:])
        if truncated[0]:
            summary = f"[output truncated] {summary}"
        raise CliError(f"authoritative verification failed: {summary}")


def _run_host_visual_gate(
    store: StateStore, item: QueueItem, config: OrchestrationConfig
) -> None:
    data = load_yaml_subset(CONFIG)
    browser_command = get(data, "ui_quality", "browser_review", "command", default="")
    if not isinstance(browser_command, str) or not browser_command.strip():
        raise CliError(
            "orchestrated visual review requires a configured trusted host "
            "browser-review command"
        )
    baseline = snapshot(ROOT)
    command = [os.fspath(ROOT / ".ai/tools/ui-quality.sh"), "browser"]
    process = subprocess.Popen(  # nosec B603
        command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=os.name == "posix",
    )
    pipe = process.stdout
    if pipe is None:
        raise CliError("could not capture trusted host browser-gate output")
    output = bytearray()
    truncated = [False]

    def read_output() -> None:
        while True:
            chunk = pipe.read(8192)
            if not chunk:
                return
            output.extend(chunk)
            if len(output) > MAX_CONTROLLER_OUTPUT:
                del output[: len(output) - MAX_CONTROLLER_OUTPUT]
                truncated[0] = True

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        return_code = process.wait(timeout=config.timeout_seconds)
    except subprocess.TimeoutExpired as error:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        reader.join(timeout=5)
        pipe.close()
        raise CliError("trusted host browser gate timed out") from error
    reader.join(timeout=5)
    pipe.close()
    if reader.is_alive():
        raise CliError("trusted host browser-gate output did not close")
    if return_code != 0:
        decoded = output.decode("utf-8", errors="replace")
        summary = " | ".join(decoded.strip().splitlines()[-3:])
        if truncated[0]:
            summary = f"[truncated] {summary}"
        raise CliError(f"trusted host browser gate failed: {summary}")
    observed = snapshot(ROOT)
    if observed.head_revision != baseline.head_revision:
        raise CliError("trusted host browser gate changed Git HEAD")
    delta = sorted(set().union(*changed_paths(baseline, observed)))
    prefix = f".ai/work/{item.item_id}/evidence/ui/"
    if any(not relative.startswith(prefix) for relative in delta):
        raise CliError(
            "trusted host browser gate changed paths outside the active UI evidence"
        )
    store.save_checkpoint(
        Checkpoint(
            item_id=item.item_id,
            phase=item.phase,
            queue_status=item.status,
            head_revision=observed.head_revision,
            source_digest=observed.source_digest,
            invocation_id=item.active_invocation_id,
            updated_at=iso_time(),
            branch_name=item.branch_name,
        )
    )
    store.append_event(
        item.item_id,
        "host-visual-gate",
        "controller",
        item.phase.value,
        {
            "before_digest": baseline.source_digest,
            "after_digest": observed.source_digest,
            "changed_path_count": len(delta),
        },
    )


def _run_final_closeout_verification() -> None:
    docs = ROOT / ".ai" / "tools" / "check-docs.py"
    if not docs.is_file():
        raise CliError("closeout requires .ai/tools/check-docs.py")
    result = subprocess.run(  # nosec B603
        [os.fspath(docs)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    if result.returncode != 0:
        diagnostic = " | ".join(result.stdout.strip().splitlines()[-3:])
        raise CliError(f"final documentation check failed: {diagnostic}")
    _run_verification()


def _activate_item(store: StateStore, queue: Queue, item: QueueItem) -> None:
    git = GitLifecycle(ROOT)
    position = git.preflight()
    if queue.run_git is None:
        queue.run_git = RunGitState(
            initial_branch=position.branch,
            initial_revision=position.revision,
        )
    base_revision = queue.run_git.latest_commit or queue.run_git.initial_revision
    if position.revision != base_revision:
        raise CliError("next item base does not match the linear branch chain")
    if queue.run_git.latest_branch and position.branch != queue.run_git.latest_branch:
        raise CliError("latest deliverable branch is not checked out")
    if not item.branch_name:
        item.branch_name = git.choose_branch(item.item_id, item.summary)
        item.base_revision = base_revision
        item.branch_ready = False
        store.save_queue(queue)
    elif item.base_revision != base_revision:
        raise CliError("persisted item branch base contradicts the linear chain")
    git.activate_branch(item.branch_name, base_revision)
    item.branch_ready = True
    item.status = QueueStatus.ACTIVE
    store.save_queue(queue)
    _checkpoint(store, item)


def _unsafe_commit_path(relative: str) -> bool:
    name = Path(relative).name
    return (
        relative == ".git"
        or relative.startswith(".git/")
        or relative == ".ai/orchestration"
        or relative.startswith(".ai/orchestration/")
        or relative
        in {
            ".ai/.orchestration.guard",
            ".ai/orchestration-completed.json",
            ".ai/config/project.env",
        }
        or name == ".env"
        or (name.startswith(".env.") and name != ".env.example")
    )


def _complete_closeout_commit(
    store: StateStore,
    queue: Queue,
    item: QueueItem,
) -> str:
    if (
        not item.branch_ready
        or not item.branch_name
        or item.base_revision is None
        or item.expected_closeout_digest is None
        or item.reviewed_source_digest is None
    ):
        raise CliError("closeout commit lacks reviewed branch intent")
    if item.active_invocation_id is None:
        raise CliError("closeout commit lacks its bound invocation")
    git = GitLifecycle(ROOT)
    subject = git.commit_subject(item.item_id, item.summary)
    position = git.position()
    revision: str
    if position.revision == item.base_revision:
        if position.branch != item.branch_name:
            raise CliError("closeout commit is on the wrong item branch")
        observed = snapshot(ROOT)
        if observed.source_digest != item.expected_closeout_digest:
            raise CliError("closeout workspace differs from the verified commit intent")
        expected_paths = git.changed_paths()
        unsafe = [path for path in expected_paths if _unsafe_commit_path(path)]
        if unsafe:
            raise CliError(
                "closeout delta contains runtime, secret, or Git paths: "
                + ", ".join(unsafe[:8])
            )
        tree = git.stage_exact(
            expected_paths,
            expected_source_digest=item.expected_closeout_digest,
            source_digest=lambda: snapshot(ROOT).source_digest,
        )
        if item.expected_commit_tree is None:
            item.expected_commit_tree = tree
            store.save_queue(queue)
        elif item.expected_commit_tree != tree:
            raise CliError("staged closeout tree contradicts persisted commit intent")
        if snapshot(ROOT).source_digest != item.expected_closeout_digest:
            raise CliError("closeout workspace changed after exact staging")
        revision = git.create_commit(
            subject,
            branch=item.branch_name,
            parent=item.base_revision,
            tree=item.expected_commit_tree,
        )
    else:
        if item.expected_commit_tree is None:
            raise CliError("unexpected commit exists without a persisted expected tree")
        revision = position.revision
    if item.expected_commit_tree is None:
        raise CliError("closeout commit lacks its expected tree")
    git.verify_commit(
        revision,
        branch=item.branch_name,
        parent=item.base_revision,
        tree=item.expected_commit_tree,
        subject=subject,
    )
    closed = snapshot(ROOT)
    if closed.source_digest != item.expected_closeout_digest:
        raise CliError("closeout commit changed the governed workspace")
    invocation_id = item.active_invocation_id
    events_path = store.resolve(f"runs/{item.item_id}/EVENTS.jsonl")
    events = store.read_events(item.item_id) if events_path.is_file() else []
    commit_events = [
        event
        for event in events
        if event.get("type") == "commit-created"
        and event.get("details", {}).get("commit_revision") == revision
    ]
    if len(commit_events) > 1:
        raise CliError("closeout commit appears repeatedly in event history")
    if not commit_events:
        store.append_event(
            item.item_id,
            "commit-created",
            invocation_id,
            Phase.CLOSEOUT.value,
            {
                "branch": item.branch_name,
                "parent_revision": item.base_revision,
                "commit_revision": revision,
                "commit_tree": item.expected_commit_tree,
                "commit_subject": subject,
            },
        )
    item.commit_revision = revision
    if queue.run_git is None:
        raise CliError("closeout commit lacks run Git metadata")
    queue.run_git.latest_branch = item.branch_name
    queue.run_git.latest_commit = revision
    previous = item.phase
    advance(item, Phase.DONE)
    _set_current_phase(item.phase)
    store.save_queue(queue)
    _checkpoint(store, item)
    store.append_event(
        item.item_id,
        "transition",
        invocation_id,
        previous.value,
        {
            "next_phase": Phase.DONE.value,
            "branch": item.branch_name,
            "commit_revision": revision,
            "commit_tree": item.expected_commit_tree,
            "commit_subject": subject,
        },
    )
    return revision


def _repair_completed_commit_transition(store: StateStore, queue: Queue) -> None:
    if queue.run_git is None or queue.run_git.latest_commit is None:
        return
    matches = [
        item
        for item in queue.items
        if item.commit_revision == queue.run_git.latest_commit
        and item.status is QueueStatus.COMPLETED
    ]
    if len(matches) != 1:
        return
    item = matches[0]
    events_path = store.resolve(f"runs/{item.item_id}/EVENTS.jsonl")
    if not events_path.is_file():
        return
    events = store.read_events(item.item_id)
    if not events or events[-1].get("type") != "commit-created":
        return
    event = events[-1]
    details = event.get("details", {})
    if details.get("commit_revision") != item.commit_revision:
        raise CliError("completion event contradicts the latest closeout commit")
    if (
        item.commit_revision is None
        or item.base_revision is None
        or item.expected_commit_tree is None
    ):
        raise CliError("completed item lacks its persisted commit facts")
    GitLifecycle(ROOT).verify_commit(
        item.commit_revision,
        branch=item.branch_name,
        parent=item.base_revision,
        tree=item.expected_commit_tree,
        subject=GitLifecycle.commit_subject(item.item_id, item.summary),
    )
    _checkpoint(store, item)
    store.append_event(
        item.item_id,
        "transition",
        event["invocation_id"],
        Phase.CLOSEOUT.value,
        {
            "next_phase": Phase.DONE.value,
            "branch": item.branch_name,
            "commit_revision": item.commit_revision,
            "commit_tree": item.expected_commit_tree,
            "commit_subject": details.get("commit_subject"),
        },
    )


def _completion_receipt(queue: Queue) -> dict[str, object]:
    if (
        queue.run_git is None
        or not queue.run_git.latest_branch
        or not queue.run_git.latest_commit
    ):
        raise CliError("completed run lacks its latest deliverable Git state")
    return {
        "schema_version": 1,
        "completed_at": iso_time(),
        "initial_branch": queue.run_git.initial_branch,
        "initial_revision": queue.run_git.initial_revision,
        "latest_branch": queue.run_git.latest_branch,
        "latest_commit": queue.run_git.latest_commit,
        "items": [
            {
                "id": item.item_id,
                "branch": item.branch_name,
                "commit": item.commit_revision,
            }
            for item in queue.items
        ],
    }


def _record_retry(
    store: StateStore,
    queue: Queue,
    item: QueueItem,
    config: OrchestrationConfig,
    diagnostic: str,
) -> None:
    failed_invocation_id = item.active_invocation_id
    signature = hashlib.sha256(
        f"{item.phase.value}:{diagnostic.split(':', 1)[0]}".encode()
    ).hexdigest()[:16]
    item.retry_count += 1
    item.active_invocation_id = None
    if item.failure_signature == signature:
        item.identical_failure_count += 1
    else:
        item.failure_signature = signature
        item.identical_failure_count = 1
    if (
        item.retry_count >= config.max_attempts
        or item.identical_failure_count >= config.max_identical_failures
    ):
        item.status = QueueStatus.BLOCKED
        item.next_attempt_at = None
    else:
        delay = min(2**item.retry_count, 300)
        item.next_attempt_at = iso_time(utc_now() + timedelta(seconds=delay))
    store.save_queue(queue)
    _checkpoint(store, item)
    store.append_event(
        item.item_id,
        "retryable-failure",
        failed_invocation_id or "controller",
        item.phase.value,
        {
            "signature": signature,
            "retry_count": item.retry_count,
            "status": item.status.value,
        },
    )


def _reconcile_item_baseline(
    store: StateStore,
    queue: Queue,
    checkpoint: Checkpoint | None,
    observed: RepositoryState,
    item: QueueItem | None = None,
) -> None:
    if (
        item is not None
        and item.branch_ready
        and observed.branch_name != item.branch_name
    ):
        raise CliError("active item branch is not checked out")
    if checkpoint is None:
        completed_checkpoints: list[Checkpoint] = []
        for candidate in queue.items:
            if candidate.status is not QueueStatus.COMPLETED:
                continue
            completed = store.load_checkpoint(candidate.item_id)
            if completed is not None:
                completed_checkpoints.append(completed)
        if not completed_checkpoints:
            ensure_clean(ROOT)
        elif any(
            value.head_revision == observed.head_revision
            and value.source_digest == observed.source_digest
            for value in completed_checkpoints
        ):
            return
        else:
            # A trusted owner may commit the preceding controller-promoted item.
            # The new clean HEAD becomes the explicit baseline for the next item.
            ensure_clean(ROOT)
    else:
        reconcile_checkpoint(checkpoint, observed)


def _run_once(
    store: StateStore,
    queue: Queue,
    item: QueueItem,
    config: OrchestrationConfig,
) -> str:
    checkpoint = store.load_checkpoint(item.item_id)
    observed = snapshot(ROOT)
    _reconcile_item_baseline(store, queue, checkpoint, observed, item)
    if item.phase is Phase.VISUAL_REVIEW:
        _run_host_visual_gate(store, item, config)
    if item.phase is Phase.VERIFICATION:
        verification_baseline = snapshot(ROOT)
        _run_verification()
        verified = snapshot(ROOT)
        if verified.source_digest != verification_baseline.source_digest:
            raise CliError("authoritative verification mutated the source workspace")
        advance(item, Phase.CODE_REVIEW)
        _set_current_phase(item.phase)
        review_baseline = snapshot(ROOT)
        store.write_json(
            f"runs/{item.item_id}/VERIFICATION.json",
            {
                "schema_version": SCHEMA_VERSION,
                "head_revision": verified.head_revision,
                "verified_source_digest": verified.source_digest,
                "review_source_digest": review_baseline.source_digest,
                "verified_at": iso_time(),
            },
        )
        store.save_queue(queue)
        _checkpoint(store, item)
        store.append_event(
            item.item_id,
            "verification-passed",
            "controller",
            Phase.VERIFICATION.value,
            {
                "head_revision": verified.head_revision,
                "verified_source_digest": verified.source_digest,
                "review_source_digest": review_baseline.source_digest,
                "next_phase": Phase.CODE_REVIEW.value,
            },
        )
        return "continue"
    role = role_for_phase(item.phase)
    if role is Role.CONTROLLER:
        raise CliError(f"phase {item.phase.value} has no agent action")
    if item.phase is Phase.CODE_REVIEW:
        evidence = store.read_json(f"runs/{item.item_id}/VERIFICATION.json")
        observed_review = snapshot(ROOT)
        if (
            evidence.get("head_revision") != observed_review.head_revision
            or evidence.get("review_source_digest") != observed_review.source_digest
        ):
            raise CliError("code review baseline lacks current verification evidence")
    request = _build_request(store, item, role)
    request = _replace_request_instructions(
        request, _request_instructions(store, item, role)
    )
    store.write_json(f"runs/{item.item_id}/REQUEST.json", request.to_dict())
    store.save_queue(queue)
    executor = CommandExecutor(
        ROOT,
        store,
        _executor_config(config),
    )
    result: ExecutionResult = executor.execute(request)
    handoff = result.handoff
    _consume_owner_authorizations(store, item.item_id, handoff.changed_paths)
    observed_after = snapshot(ROOT)
    if result.promoted_source_digest != observed_after.source_digest:
        raise CliError("promotion digest differs from the source workspace")
    if handoff.result is HandoffResult.NEEDS_OWNER_DECISION:
        _archive_owner_requests(store, item, handoff, observed_after.source_digest)
        item.status = QueueStatus.AWAITING_OWNER
        item.active_invocation_id = None
        store.save_queue(queue)
        _checkpoint(store, item)
        _render_owner_inbox(store, queue)
        store.append_event(
            item.item_id,
            "awaiting-owner",
            request.invocation_id,
            item.phase.value,
            {
                "decision_ids": [value.decision_id for value in handoff.owner_requests],
                "status": item.status.value,
            },
        )
        return "owner"
    if handoff.result in {
        HandoffResult.BLOCKED,
        HandoffResult.INVALID_STATE,
    }:
        item.status = QueueStatus.BLOCKED
        item.active_invocation_id = None
        store.save_queue(queue)
        _checkpoint(store, item)
        store.append_event(
            item.item_id,
            "status-change",
            request.invocation_id,
            item.phase.value,
            {
                "result": handoff.result.value,
                "status": item.status.value,
            },
        )
        return "blocked"
    if handoff.result is HandoffResult.RETRYABLE_FAILURE:
        _record_retry(store, queue, item, config, handoff.diagnostic_code)
        return "blocked" if item.status is QueueStatus.BLOCKED else "retry"
    if handoff.next_phase is None:
        raise CliError("successful handoff omitted next phase")
    if (
        item.phase in {Phase.CODE_REVIEW, Phase.VISUAL_REVIEW}
        and handoff.next_phase is Phase.CLOSEOUT
    ):
        item.reviewed_source_digest = observed_after.source_digest
    if item.phase is Phase.CLOSEOUT:
        _checkpoint(store, item)
        closed_before_verify = snapshot(ROOT)
        _run_final_closeout_verification()
        closed = snapshot(ROOT)
        if closed != closed_before_verify:
            raise CliError("final closeout verification mutated the source workspace")
        item.expected_closeout_digest = closed.source_digest
        store.save_queue(queue)
        _checkpoint(store, item)
        _complete_closeout_commit(store, queue, item)
        return "done"
    previous = item.phase
    advance(item, handoff.next_phase)
    _set_current_phase(item.phase)
    store.save_queue(queue)
    _checkpoint(store, item)
    store.append_event(
        item.item_id,
        "transition",
        request.invocation_id,
        previous.value,
        {
            "next_phase": item.phase.value,
            "output_truncated": result.output_truncated,
        },
    )
    return "done" if item.phase is Phase.DONE else "continue"


def command_intake(arguments: argparse.Namespace) -> int:
    path = Path(arguments.file)
    config = load_config()
    _require_runnable(config)
    store = StateStore(ROOT)
    # Reject legacy state before lease acquisition writes any runtime file.
    store.load_queue()
    content = _read_bounded_utf8(path, 262_144, "intake file")
    with _serialized_mutation(store, config.lease_seconds):
        existing = store.load_queue()
        incoming = parse_intake(
            content, existing_ids={item.item_id for item in existing.items}
        )
        queue = merge_intake(existing, incoming)
        store.save_queue(queue)
    _write_output(
        {"status": "accepted", "items": [item.item_id for item in incoming]},
        human=f"Accepted {len(incoming)} queue item(s).",
    )
    return EXIT_SUCCESS


def command_status(_arguments: argparse.Namespace) -> int:
    store = StateStore(ROOT)
    queue = store.load_queue()
    receipt = store.completion_receipt() if not queue.items else None
    payload = {
        "status": "completed" if receipt is not None else "ok",
        "items": [
            {
                "id": item.item_id,
                "status": item.status.value,
                "phase": item.phase.value,
                "priority": item.priority,
                "depends_on": item.depends_on,
                "branch": item.branch_name or None,
                "base_revision": item.base_revision,
                "commit_revision": item.commit_revision,
            }
            for item in queue.items
        ],
        "initial_branch": (
            queue.run_git.initial_branch if queue.run_git is not None else None
        ),
        "initial_revision": (
            queue.run_git.initial_revision if queue.run_git is not None else None
        ),
        "latest_branch": (
            receipt.get("latest_branch")
            if receipt is not None
            else (queue.run_git.latest_branch if queue.run_git is not None else None)
        ),
        "latest_commit": (
            receipt.get("latest_commit")
            if receipt is not None
            else (queue.run_git.latest_commit if queue.run_git is not None else None)
        ),
    }
    _write_output(payload, human=f"{len(queue.items)} queue item(s).")
    return EXIT_SUCCESS


def command_doctor(_arguments: argparse.Namespace) -> int:
    config = load_config()
    _require_runnable(config)
    git_position = GitLifecycle(ROOT).preflight()
    observed = snapshot(ROOT)
    if config.executor_kind == "codex":
        executor_config = _executor_config(config)
        runtime = validate_codex_runtime(executor_config)
        probe = probe_codex_runtime(
            executor_config,
            ROOT / ".ai" / "templates" / "CODEX_RESULT_SCHEMA.json",
        )
    else:
        executable = shutil.which(config.command[0])
        if executable is None:
            raise ConfigError("configured command executor was not found")
        if shutil.which("bwrap") is None or shutil.which("prlimit") is None:
            raise ConfigError("command executor requires bwrap and prlimit")
        runtime = {
            "kind": "command",
            "executable": executable,
            "version": "",
        }
        probe = {"status": "not-applicable", "diagnostic_code": ""}
    payload = {
        "status": "ready",
        "executor": runtime,
        "exec_probe": probe,
        "head_revision": observed.head_revision,
        "source_digest": observed.source_digest,
        "branch": git_position.branch,
    }
    _write_output(payload, human="Orchestration runtime is ready.")
    return EXIT_SUCCESS


def command_start(arguments: argparse.Namespace) -> int:
    command_doctor(arguments)
    intake_result = command_intake(arguments)
    if intake_result != EXIT_SUCCESS:
        return intake_result
    return command_run(arguments)


def command_run(_arguments: argparse.Namespace) -> int:
    config = load_config()
    _require_runnable(config)
    store = getattr(_arguments, "_orchestration_store", StateStore(ROOT))
    queue = getattr(_arguments, "_orchestration_queue", store.load_queue())
    if not queue.items:
        raise CliError("queue is empty; run intake first")
    lease: Lease | None = getattr(_arguments, "_orchestration_lease", None)
    takeover = False
    if lease is None:
        owner_id = f"{socket.gethostname()}:{os.getpid()}"
        lease_id = str(uuid.uuid4())
        lease, takeover = store.acquire_lease(
            owner_id,
            lease_id,
            config.lease_seconds,
            allow_takeover=False,
        )
    if lease is None:
        raise CliError("failed to acquire orchestration lease")
    active_lease = lease
    lease_id = active_lease.invocation_id
    heartbeat_stop = threading.Event()
    heartbeat_errors: list[Exception] = []

    def heartbeat() -> None:
        while not heartbeat_stop.wait(max(1, config.lease_seconds // 3)):
            try:
                store.renew_lease(active_lease, config.lease_seconds)
            except Exception as error:  # noqa: BLE001 - propagated in controller thread
                heartbeat_errors.append(error)
                return

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        _repair_completed_commit_transition(store, queue)
        if takeover:
            for candidate in queue.items:
                if candidate.status is QueueStatus.ACTIVE:
                    observed = snapshot(ROOT)
                    reconcile_checkpoint(
                        store.load_checkpoint(candidate.item_id), observed
                    )
                    store.append_event(
                        candidate.item_id,
                        "lease-takeover",
                        lease_id,
                        candidate.phase.value,
                        {"reason": "expired lease reconciled"},
                    )
                    break
        while True:
            if heartbeat_errors:
                raise CliError(f"lease heartbeat failed: {heartbeat_errors[0]}")
            item = select_next(queue)
            if item is None:
                if all(
                    candidate.status is QueueStatus.COMPLETED
                    for candidate in queue.items
                ):
                    heartbeat_stop.set()
                    heartbeat_thread.join(timeout=5)
                    if heartbeat_thread.is_alive():
                        raise CliError("lease heartbeat did not stop before cleanup")
                    if heartbeat_errors:
                        raise CliError(f"lease heartbeat failed: {heartbeat_errors[0]}")
                    receipt = _completion_receipt(queue)
                    store.fenced_cleanup(receipt)
                    _write_output(
                        {
                            "status": "completed",
                            "latest_branch": receipt["latest_branch"],
                            "latest_commit": receipt["latest_commit"],
                        },
                        human="All queue items completed.",
                    )
                    return EXIT_SUCCESS
                raise CliError("no queue item is eligible to run")
            if item.status is QueueStatus.AWAITING_OWNER:
                _write_output(
                    {"status": "awaiting-owner", "item": item.item_id},
                    human=f"Owner decision required for {item.item_id}.",
                )
                return EXIT_OWNER
            if item.status is QueueStatus.BLOCKED:
                _write_output(
                    {"status": "blocked", "item": item.item_id},
                    human=f"Queue item {item.item_id} is blocked.",
                )
                return EXIT_BLOCKED
            if item.status is QueueStatus.PENDING:
                _activate_item(store, queue, item)
            if item.next_attempt_at is not None:
                if parse_time(item.next_attempt_at) > utc_now():
                    _write_output(
                        {
                            "status": "retry-scheduled",
                            "item": item.item_id,
                            "next_attempt_at": item.next_attempt_at,
                        },
                        human=f"Retry for {item.item_id} is scheduled.",
                    )
                    return EXIT_BLOCKED
                item.next_attempt_at = None
            try:
                result = _run_once(store, queue, item, config)
            except ExecutorError as error:
                if not error.retryable:
                    raise
                _record_retry(store, queue, item, config, "executor-timeout")
                return EXIT_BLOCKED
            if result == "owner":
                return EXIT_OWNER
            if result in {"blocked", "retry"}:
                return EXIT_BLOCKED
            active_lease = store.renew_lease(active_lease, config.lease_seconds)
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=5)
        if store.resolve("LEASE.json").exists():
            store.release_lease(active_lease)


def _recover_persisted_handoff(
    store: StateStore,
    queue: Queue,
    item: QueueItem,
    config: OrchestrationConfig,
) -> bool:
    request_path = store.resolve(f"runs/{item.item_id}/REQUEST.json")
    handoff_path = store.resolve(f"runs/{item.item_id}/HANDOFF.json")
    if (
        item.active_invocation_id is None
        or not request_path.is_file()
        or not handoff_path.is_file()
    ):
        return False
    request = AgentRequest.from_dict(
        store.read_json(f"runs/{item.item_id}/REQUEST.json")
    )
    handoff = AgentHandoff.from_dict(
        store.read_json(f"runs/{item.item_id}/HANDOFF.json")
    )
    if item.branch_name and request.source_branch != item.branch_name:
        raise CliError("recoverable request is not bound to the item branch")
    promotion_path = f"runs/{item.item_id}/PROMOTION.json"
    if not store.resolve(promotion_path).is_file():
        return False
    promotion = store.read_json(promotion_path)
    if (
        promotion.get("invocation_id") != request.invocation_id
        or promotion.get("staged_digest") != handoff.staged_digest
        or promotion.get("baseline_source_digest") != request.source_digest
        or promotion.get("expected_source_digest") != handoff.staged_digest
        or promotion.get("status") not in {"prepared", "mutating", "committed"}
    ):
        return False
    if request.invocation_id != item.active_invocation_id:
        return False
    validate_handoff(request, handoff)
    observed = snapshot(ROOT)
    status = promotion.get("status")
    if status == "prepared":
        if observed.source_digest != request.source_digest:
            raise CliError(
                "prepared promotion found source drift before mutation; "
                "manual reconciliation is required"
            )
        clear_promotion_journal(store, item.item_id)
        store.resolve(promotion_path).unlink()
        return False
    if status == "mutating":
        if observed.source_digest == handoff.staged_digest:
            promotion["status"] = "committed"
            promotion["promoted_source_digest"] = observed.source_digest
            store.write_json(promotion_path, promotion)
        elif restore_promotion_journal(store, item.item_id, ROOT):
            restored = snapshot(ROOT)
            if (
                restored.head_revision != request.head_revision
                or restored.source_digest != request.source_digest
            ):
                raise CliError("promotion journal did not restore the request baseline")
            store.resolve(promotion_path).unlink()
            return False
    if promotion.get("promoted_source_digest") != observed.source_digest:
        return False
    clear_promotion_journal(store, item.item_id)
    validate_remediation_findings(ROOT, request, handoff)
    _consume_owner_authorizations(store, item.item_id, handoff.changed_paths)
    run_lifecycle_validator(ROOT)
    previous = item.phase
    if handoff.result is HandoffResult.NEEDS_OWNER_DECISION:
        _archive_owner_requests(store, item, handoff, snapshot(ROOT).source_digest)
        item.status = QueueStatus.AWAITING_OWNER
        item.active_invocation_id = None
        store.save_queue(queue)
        _checkpoint(store, item)
        _render_owner_inbox(store, queue)
    elif handoff.result in {
        HandoffResult.BLOCKED,
        HandoffResult.INVALID_STATE,
    }:
        item.status = QueueStatus.BLOCKED
        item.active_invocation_id = None
        store.save_queue(queue)
        _checkpoint(store, item)
    elif handoff.result is HandoffResult.RETRYABLE_FAILURE:
        _record_retry(store, queue, item, config, handoff.diagnostic_code)
    else:
        if handoff.next_phase is None:
            raise CliError("recoverable handoff omitted next phase")
        observed_recovered = snapshot(ROOT)
        if (
            item.phase in {Phase.CODE_REVIEW, Phase.VISUAL_REVIEW}
            and handoff.next_phase is Phase.CLOSEOUT
        ):
            item.reviewed_source_digest = observed_recovered.source_digest
        if item.phase is Phase.CLOSEOUT:
            _checkpoint(store, item)
            closed_before_verify = snapshot(ROOT)
            _run_final_closeout_verification()
            closed = snapshot(ROOT)
            if closed != closed_before_verify:
                raise CliError(
                    "final closeout verification mutated the source workspace"
                )
            item.expected_closeout_digest = closed.source_digest
            store.save_queue(queue)
            _checkpoint(store, item)
            _complete_closeout_commit(store, queue, item)
            return True
        advance(item, handoff.next_phase)
        _set_current_phase(item.phase)
        store.save_queue(queue)
        _checkpoint(store, item)
    store.append_event(
        item.item_id,
        "handoff-recovered",
        request.invocation_id,
        previous.value,
        {
            "result": handoff.result.value,
            "phase": item.phase.value,
            "status": item.status.value,
        },
    )
    return True


def command_resume(arguments: argparse.Namespace) -> int:
    config = load_config()
    _require_runnable(config)
    store = StateStore(ROOT)
    # Reject legacy state before lease acquisition writes any runtime file.
    queue = store.load_queue()
    owner_id = f"{socket.gethostname()}:{os.getpid()}"
    lease_id = str(uuid.uuid4())
    lease, takeover = store.acquire_lease(owner_id, lease_id, config.lease_seconds)
    try:
        item = select_next(queue)
        if item is not None:
            if (
                item.phase is Phase.CLOSEOUT
                and item.expected_closeout_digest is not None
            ):
                _complete_closeout_commit(store, queue, item)
                item = select_next(queue)
            if item is not None and not _recover_persisted_handoff(
                store, queue, item, config
            ):
                observed = snapshot(ROOT)
                reconcile_checkpoint(store.load_checkpoint(item.item_id), observed)
                run_lifecycle_validator(ROOT)
            if takeover and item is not None:
                store.append_event(
                    item.item_id,
                    "lease-takeover",
                    lease_id,
                    item.phase.value,
                    {"reason": "expired lease reconciled"},
                )
        setattr(arguments, "_orchestration_store", store)
        setattr(arguments, "_orchestration_queue", queue)
        setattr(arguments, "_orchestration_lease", lease)
        return command_run(arguments)
    except BaseException:
        if store.resolve("LEASE.json").exists():
            store.release_lease(lease)
        raise


def command_decisions(_arguments: argparse.Namespace) -> int:
    store = StateStore(ROOT)
    path = store.resolve("OWNER_INBOX.md")
    text = (
        path.read_text(encoding="utf-8")
        if path.is_file()
        else "# Owner inbox\n\nNo open owner decisions.\n"
    )
    print(text, end="")
    return EXIT_SUCCESS


def _parse_decision(path: Path) -> OwnerDecision:
    fields: dict[str, str] = {}
    for line in _read_bounded_utf8(path, 65_536, "decision file").splitlines():
        match = FIELD.fullmatch(line)
        if match:
            name = match.group(1).strip()
            if name in fields:
                raise CliError(f"decision file repeats field {name!r}")
            fields[name] = match.group(2).strip()
    try:
        return OwnerDecision.from_markdown_fields(fields)
    except ModelError as error:
        raise CliError(f"invalid owner decision: {error}") from error


def command_decide(arguments: argparse.Namespace) -> int:
    config = load_config()
    _require_runnable(config)
    decision_path = Path(arguments.decision_file).absolute()
    try:
        decision_path.resolve(strict=False).relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise CliError("owner decision file must be outside the repository")
    decision = _parse_decision(decision_path)
    if decision.owner != config.owner:
        raise CliError("decision owner does not match configured owner")
    store = StateStore(ROOT)
    # Reject legacy state before lease acquisition writes any runtime file.
    store.load_queue()
    with _serialized_mutation(store, config.lease_seconds):
        queue = store.load_queue()
        matches = [item for item in queue.items if item.item_id == decision.item_id]
        if len(matches) != 1:
            raise CliError("decision references an unknown queue item")
        item = matches[0]
        if (
            item.status is not QueueStatus.AWAITING_OWNER
            or item.phase is not decision.phase
        ):
            raise CliError("decision is stale for the current queue state")
        checkpoint = store.load_checkpoint(item.item_id)
        observed = snapshot(ROOT)
        if (
            checkpoint is None
            or checkpoint.source_digest != decision.state_digest
            or observed.source_digest != decision.state_digest
            or observed.head_revision != checkpoint.head_revision
        ):
            raise CliError("decision state digest does not match the current workspace")
        archive_relative = f"runs/{item.item_id}/OWNER_REQUESTS.json"
        archive = store.read_json(archive_relative).get("requests", [])
        if not isinstance(archive, list):
            raise CliError("stored owner request archive is invalid")
        records = [
            record
            for record in archive
            if isinstance(record, dict)
            and isinstance(record.get("request"), dict)
            and record["request"].get("decision_id") == decision.decision_id
        ]
        if len(records) != 1:
            raise CliError("decision ID is not uniquely archived")
        record = records[0]
        request = OwnerRequest.from_dict(record["request"])
        if (
            record.get("phase") != item.phase.value
            or record.get("state_digest") != decision.state_digest
            or decision.answer not in request.allowed_answers
        ):
            raise CliError("decision is stale or its answer is not allowed")
        relative = f"runs/{item.item_id}/OWNER_DECISIONS.json"
        values: list[dict[str, object]] = []
        if store.resolve(relative).is_file():
            raw = store.read_json(relative).get("decisions", [])
            if not isinstance(raw, list):
                raise CliError("stored owner decisions are invalid")
            values = [value for value in raw if isinstance(value, dict)]
        if any(value.get("decision_id") == decision.decision_id for value in values):
            raise CliError("decision has already been applied")
        authorized_paths = (
            request.authorized_paths
            if decision.answer in request.authorizing_answers
            else []
        )
        values.append(
            {
                "decision_id": decision.decision_id,
                "answer": decision.answer,
                "rationale": decision.rationale,
                "owner": decision.owner,
                "authorized_paths": authorized_paths,
                "consumed_paths": [],
            }
        )
        store.write_json(
            relative,
            {"schema_version": SCHEMA_VERSION, "decisions": values},
        )
        unresolved = {
            record["request"]["decision_id"]
            for record in archive
            if isinstance(record, dict)
            and record.get("phase") == item.phase.value
            and record.get("state_digest") == decision.state_digest
            and isinstance(record.get("request"), dict)
        }
        resolved_ids = {
            value["decision_id"]
            for value in values
            if isinstance(value.get("decision_id"), str)
        }
        item.status = (
            QueueStatus.ACTIVE
            if unresolved.issubset(resolved_ids)
            else QueueStatus.AWAITING_OWNER
        )
        store.save_queue(queue)
        _checkpoint(store, item)
        _render_owner_inbox(store, queue)
        store.append_event(
            item.item_id,
            "owner-decision",
            "host",
            item.phase.value,
            {
                "decision_id": decision.decision_id,
                "answer": decision.answer,
                "status": item.status.value,
            },
        )
    _write_output(
        {"status": "accepted", "decision_id": decision.decision_id},
        human=f"Accepted owner decision {decision.decision_id}.",
    )
    return EXIT_SUCCESS


def command_validate(_arguments: argparse.Namespace) -> int:
    validator = ROOT / ".ai" / "tools" / "check-orchestration-state.py"
    result = subprocess.run(  # nosec B603
        [os.fspath(validator)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    if result.returncode != 0:
        diagnostic = " | ".join(result.stdout.strip().splitlines()[-3:])
        raise CliError(f"orchestration state validation failed: {diagnostic}")
    _write_output({"status": "valid"}, human="Orchestration state is valid.")
    return EXIT_SUCCESS


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    intake = commands.add_parser("intake")
    intake.add_argument("--file", required=True)
    intake.set_defaults(handler=command_intake)
    start = commands.add_parser("start")
    start.add_argument("--file", required=True)
    start.set_defaults(handler=command_start)
    for name, handler in (
        ("doctor", command_doctor),
        ("status", command_status),
        ("run", command_run),
        ("resume", command_resume),
        ("decisions", command_decisions),
        ("validate", command_validate),
    ):
        command = commands.add_parser(name)
        command.set_defaults(handler=handler)
    decide = commands.add_parser("decide")
    decide.add_argument("--decision-file", required=True)
    decide.set_defaults(handler=command_decide)
    return value


def main() -> int:
    arguments = parser().parse_args()
    try:
        return int(arguments.handler(arguments))
    except (
        CliError,
        EngineError,
        ExecutorError,
        GitLifecycleError,
        ReconcileError,
        StoreError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        if isinstance(error, ConfigError):
            return EXIT_CONFIG
        return EXIT_BLOCKED
    except KeyboardInterrupt:
        print(
            "ERROR: interrupted safely; use resume after checking state",
            file=sys.stderr,
        )
        return EXIT_INTERNAL
    except Exception as error:  # pragma: no cover - final safe CLI boundary
        print(
            f"ERROR: internal orchestration failure: {type(error).__name__}",
            file=sys.stderr,
        )
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
