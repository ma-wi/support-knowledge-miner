#!/usr/bin/env python3
"""Read-only validation for optional orchestration runtime state."""

from __future__ import annotations

import os
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import get, load_yaml_subset  # noqa: E402
from orchestration.engine import (  # noqa: E402
    ALLOWED_TRANSITIONS,
    EngineError,
    select_next,
    validate_handoff,
    validate_queue,
)
from orchestration.executor import (  # noqa: E402
    ExecutorError,
    validate_remediation_findings,
)
from orchestration.git_lifecycle import GitLifecycle, GitLifecycleError  # noqa: E402
from orchestration.model import (  # noqa: E402
    AgentHandoff,
    AgentRequest,
    HandoffResult,
    Lease,
    ModelError,
    OwnerRequest,
    Phase,
    QueueItem,
    QueueStatus,
)
from orchestration.reconcile import (  # noqa: E402
    ReconcileError,
    reconcile_checkpoint,
    run_lifecycle_validator,
    snapshot,
    validate_current_plan_binding,
)
from orchestration.store import StateStore, StoreError, parse_time  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIGEST = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40,64}$")


def _validate_run_state(store: StateStore, item: QueueItem) -> None:
    item_id = item.item_id
    request_path = f"runs/{item_id}/REQUEST.json"
    handoff_path = f"runs/{item_id}/HANDOFF.json"
    request = (
        store.load(request_path, AgentRequest.from_dict)
        if store.resolve(request_path).is_file()
        else None
    )
    handoff = (
        store.load(handoff_path, AgentHandoff.from_dict)
        if store.resolve(handoff_path).is_file()
        else None
    )
    if (
        request is not None
        and item.branch_name
        and request.source_branch != item.branch_name
    ):
        raise StoreError("agent request is not bound to the active item branch")
    if handoff is not None:
        if request is None:
            raise StoreError("handoff exists without its request")
        validate_handoff(request, handoff)
    active_invocation = item.active_invocation_id
    if active_invocation is not None and (
        request is None or request.invocation_id != active_invocation
    ):
        raise StoreError("active invocation does not match the persisted request")
    promotion_path = f"runs/{item_id}/PROMOTION.json"
    if store.resolve(promotion_path).is_file():
        if handoff is None:
            raise StoreError("promotion marker exists without a handoff")
        promotion = store.read_json(promotion_path)
        if set(promotion) != {
            "schema_version",
            "invocation_id",
            "staged_digest",
            "baseline_source_digest",
            "expected_source_digest",
            "promoted_source_digest",
            "status",
        }:
            raise StoreError("promotion marker has invalid fields")
        if (
            promotion.get("schema_version") != 1
            or promotion.get("invocation_id") != handoff.invocation_id
            or promotion.get("staged_digest") != handoff.staged_digest
            or promotion.get("baseline_source_digest") != handoff.source_digest
            or promotion.get("expected_source_digest") != handoff.staged_digest
            or not isinstance(promotion.get("promoted_source_digest"), str)
            or (
                promotion.get("status") == "committed"
                and not DIGEST.fullmatch(promotion["promoted_source_digest"])
            )
            or (
                promotion.get("status") in {"prepared", "mutating"}
                and promotion.get("promoted_source_digest") != ""
            )
            or promotion.get("status") not in {"prepared", "mutating", "committed"}
        ):
            raise StoreError("promotion marker contradicts its handoff")
        if (
            handoff.result is HandoffResult.NEEDS_REMEDIATION
            and promotion.get("promoted_source_digest") == snapshot(ROOT).source_digest
        ):
            if request is None:
                raise StoreError("remediation promotion exists without its request")
            validate_remediation_findings(ROOT, request, handoff)
    verification_path = f"runs/{item_id}/VERIFICATION.json"
    if store.resolve(verification_path).is_file():
        verification = store.read_json(verification_path)
        if set(verification) != {
            "schema_version",
            "head_revision",
            "verified_source_digest",
            "review_source_digest",
            "verified_at",
        }:
            raise StoreError("verification evidence has invalid fields")
        if (
            verification.get("schema_version") != 1
            or not isinstance(verification.get("head_revision"), str)
            or not REVISION.fullmatch(verification["head_revision"])
            or any(
                not isinstance(verification.get(name), str)
                or not DIGEST.fullmatch(verification[name])
                for name in ("verified_source_digest", "review_source_digest")
            )
            or not isinstance(verification.get("verified_at"), str)
        ):
            raise StoreError("verification evidence has invalid values")
        parse_time(verification["verified_at"])
    elif item.phase in {
        Phase.CODE_REVIEW,
        Phase.VISUAL_REVIEW,
        Phase.REMEDIATION,
        Phase.CLOSEOUT,
    }:
        raise StoreError("post-verification phase lacks verification evidence")
    decisions_path = f"runs/{item_id}/OWNER_DECISIONS.json"
    requests_path = f"runs/{item_id}/OWNER_REQUESTS.json"
    allowed: dict[str, OwnerRequest] = {}
    if store.resolve(requests_path).is_file():
        archive = store.read_json(requests_path)
        if (
            set(archive) != {"schema_version", "requests"}
            or archive.get("schema_version") != 1
            or not isinstance(archive.get("requests"), list)
        ):
            raise StoreError("owner request archive has invalid fields")
        for record in archive["requests"]:
            if not isinstance(record, dict) or set(record) != {
                "phase",
                "state_digest",
                "request",
            }:
                raise StoreError("owner request archive entry has invalid fields")
            try:
                Phase(record["phase"])
            except (TypeError, ValueError) as error:
                raise StoreError("owner request archive phase is invalid") from error
            if not isinstance(record.get("state_digest"), str) or not DIGEST.fullmatch(
                record["state_digest"]
            ):
                raise StoreError("owner request archive digest is invalid")
            owner_request = OwnerRequest.from_dict(record["request"])
            if owner_request.decision_id in allowed:
                raise StoreError("owner request archive repeats a decision ID")
            allowed[owner_request.decision_id] = owner_request
    if store.resolve(decisions_path).is_file():
        if not allowed:
            raise StoreError("owner decisions exist without an owner request archive")
        decisions = store.read_json(decisions_path)
        if (
            set(decisions) != {"schema_version", "decisions"}
            or decisions.get("schema_version") != 1
        ):
            raise StoreError("owner decisions have invalid fields")
        values = decisions.get("decisions")
        if not isinstance(values, list):
            raise StoreError("owner decisions must be a list")
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, dict) or set(value) != {
                "decision_id",
                "answer",
                "rationale",
                "owner",
                "authorized_paths",
                "consumed_paths",
            }:
                raise StoreError("owner decision entry has invalid fields")
            decision_id = value.get("decision_id")
            if (
                not isinstance(decision_id, str)
                or decision_id not in allowed
                or decision_id in seen
                or not all(
                    isinstance(value.get(name), str) and value[name]
                    for name in ("answer", "rationale", "owner")
                )
                or not isinstance(value.get("authorized_paths"), list)
                or not isinstance(value.get("consumed_paths"), list)
                or not all(isinstance(path, str) for path in value["authorized_paths"])
                or not all(isinstance(path, str) for path in value["consumed_paths"])
                or not set(value["consumed_paths"]).issubset(value["authorized_paths"])
            ):
                raise StoreError("owner decision entry has invalid values")
            owner_request = allowed[decision_id]
            if value["answer"] not in owner_request.allowed_answers:
                raise StoreError("owner decision answer was not allowed")
            expected_paths = (
                owner_request.authorized_paths
                if value["answer"] in owner_request.authorizing_answers
                else []
            )
            if value["authorized_paths"] != expected_paths:
                raise StoreError("owner decision path authorization is inconsistent")
            seen.add(decision_id)


def main() -> int:
    try:
        config = load_yaml_subset(ROOT / ".ai" / "project.yaml")
        enabled = get(config, "orchestration", "enabled", default=False)
        if not isinstance(enabled, bool):
            raise StoreError("orchestration.enabled must be true or false")
        executor_kind = get(config, "orchestration", "executor_kind", default="command")
        if executor_kind not in {"command", "codex"}:
            raise StoreError("orchestration.executor_kind is unsupported")
        executor_command = get(config, "orchestration", "executor_command", default=[])
        if enabled and (not isinstance(executor_command, list) or not executor_command):
            raise StoreError(
                "enabled orchestration requires a configured executor_command"
            )
        if executor_kind == "codex" and (
            not isinstance(executor_command, list) or len(executor_command) != 1
        ):
            raise StoreError(
                "Codex orchestration requires exactly one executor executable"
            )
        if (
            enabled
            and executor_kind == "codex"
            and get(
                config,
                "orchestration",
                "external_repository_processing_approved",
                default=False,
            )
            is not True
        ):
            raise StoreError(
                "Codex orchestration requires external repository processing approval"
            )
        browser_command = get(
            config,
            "ui_quality",
            "browser_review",
            "command",
            default="",
        )
        if (
            enabled
            and get(config, "ui_quality", "enabled", default=False) is True
            and (not isinstance(browser_command, str) or not browser_command.strip())
        ):
            raise StoreError(
                "orchestrated UI quality requires a trusted host browser command"
            )
        store = StateStore(ROOT)
        if not store.root.exists():
            receipt = store.completion_receipt()
            if receipt is not None:
                lifecycle = GitLifecycle(ROOT)
                if (
                    lifecycle.ref_target(receipt["latest_branch"])
                    != receipt["latest_commit"]
                ):
                    raise StoreError(
                        "completion receipt differs from its latest deliverable branch"
                    )
                for item in receipt["items"]:
                    if lifecycle.ref_target(item["branch"]) != item["commit"]:
                        raise StoreError(
                            "completion receipt contains a moved or removed item branch"
                        )
                print("PASS: orchestration is complete with a valid delivery receipt.")
                return 0
            print(
                "PASS: orchestration is "
                + ("enabled with empty state." if enabled else "disabled.")
            )
            return 0
        queue = store.load_queue()
        validate_queue(queue)
        if queue.run_git is None and any(
            item.status is not QueueStatus.PENDING for item in queue.items
        ):
            raise StoreError("activated orchestration state lacks run Git metadata")
        if queue.run_git is not None:
            lifecycle = GitLifecycle(ROOT)
            if (
                lifecycle.ref_target(queue.run_git.initial_branch)
                != queue.run_git.initial_revision
            ):
                raise StoreError("initial run branch was moved or removed")
            for item in queue.items:
                if not item.branch_name:
                    continue
                expected_ref = item.commit_revision or item.base_revision
                if lifecycle.ref_target(item.branch_name) != expected_ref:
                    raise StoreError(
                        f"item branch was moved or removed: {item.item_id}"
                    )
                if item.commit_revision is not None:
                    facts = lifecycle.commit_facts(item.commit_revision)
                    if (
                        facts.parents != [item.base_revision]
                        or facts.tree != item.expected_commit_tree
                        or facts.subject
                        != GitLifecycle.commit_subject(item.item_id, item.summary)
                    ):
                        raise StoreError(
                            f"item closeout commit is inconsistent: {item.item_id}"
                        )
        current = select_next(queue)
        for item in queue.items:
            _validate_run_state(store, item)
            checkpoint = store.load_checkpoint(item.item_id)
            if item.status is QueueStatus.PENDING:
                if checkpoint is not None:
                    raise StoreError("pending queue item unexpectedly has a checkpoint")
                continue
            if checkpoint is None:
                raise StoreError("non-pending queue item has no checkpoint")
            if (
                checkpoint.phase is not item.phase
                or checkpoint.queue_status is not item.status
                or checkpoint.branch_name != item.branch_name
            ):
                raise StoreError("queue item and checkpoint state disagree")
            if item is current:
                reconcile_checkpoint(checkpoint, snapshot(ROOT))
                closed_closeout = False
                if item.phase is Phase.CLOSEOUT:
                    promotion_path = f"runs/{item.item_id}/PROMOTION.json"
                    if store.resolve(promotion_path).is_file():
                        promotion = store.read_json(promotion_path)
                        closed_closeout = (
                            promotion.get("status") == "committed"
                            and promotion.get("promoted_source_digest")
                            == checkpoint.source_digest
                        )
                if not closed_closeout:
                    validate_current_plan_binding(ROOT, item.item_id, item.phase)
        runs = store.resolve("runs")
        if runs.is_dir():
            known = {item.item_id for item in queue.items}
            orphaned = sorted(
                path.name
                for path in runs.iterdir()
                if path.is_dir() and path.name not in known
            )
            if orphaned:
                raise StoreError("orphan orchestration run(s): " + ", ".join(orphaned))
        lease = store.resolve("LEASE.json")
        if lease.is_file():
            store.load("LEASE.json", Lease.from_dict)
        for item in queue.items:
            events = store.resolve(f"runs/{item.item_id}/EVENTS.jsonl")
            if events.is_file():
                event_values = store.read_events(item.item_id)
                event_phase = Phase.INTAKE
                event_status = QueueStatus.PENDING
                last_time = None
                for event in event_values:
                    event_time = parse_time(event["time"])
                    if last_time is not None and event_time < last_time:
                        raise StoreError("event timestamps are not monotonic")
                    last_time = event_time
                    previous = Phase(event["previous_state"])
                    if previous is not event_phase:
                        raise StoreError(
                            "event history has a discontinuous phase chain"
                        )
                    if event["type"] in {"transition", "verification-passed"}:
                        next_phase = event["details"].get("next_phase")
                        try:
                            target = Phase(next_phase)
                        except (TypeError, ValueError) as error:
                            raise StoreError(
                                "transition event has an invalid next phase"
                            ) from error
                        if target not in ALLOWED_TRANSITIONS[previous]:
                            raise StoreError(
                                "transition event records a forbidden phase change"
                            )
                        event_phase = target
                        event_status = (
                            QueueStatus.COMPLETED
                            if target is Phase.DONE
                            else QueueStatus.ACTIVE
                        )
                    elif event["type"] == "awaiting-owner":
                        decision_ids = event["details"].get("decision_ids")
                        if (
                            not isinstance(decision_ids, list)
                            or not decision_ids
                            or not all(
                                isinstance(value, str) and value
                                for value in decision_ids
                            )
                            or event["details"].get("status")
                            != QueueStatus.AWAITING_OWNER.value
                        ):
                            raise StoreError(
                                "awaiting-owner event has invalid decision details"
                            )
                        event_status = QueueStatus.AWAITING_OWNER
                    elif event["type"] in {
                        "owner-decision",
                        "retryable-failure",
                        "status-change",
                    }:
                        try:
                            recorded_status = QueueStatus(
                                event["details"].get("status")
                            )
                        except (TypeError, ValueError) as error:
                            raise StoreError(
                                "status event has an invalid resulting status"
                            ) from error
                        if event["type"] == "owner-decision":
                            if (
                                not isinstance(event["details"].get("decision_id"), str)
                                or not isinstance(event["details"].get("answer"), str)
                                or recorded_status
                                not in {
                                    QueueStatus.ACTIVE,
                                    QueueStatus.AWAITING_OWNER,
                                }
                            ):
                                raise StoreError(
                                    "owner-decision event has invalid details"
                                )
                        elif event["type"] == "status-change":
                            try:
                                result = HandoffResult(event["details"].get("result"))
                            except (TypeError, ValueError) as error:
                                raise StoreError(
                                    "status-change event has an invalid result"
                                ) from error
                            if (
                                result
                                not in {
                                    HandoffResult.BLOCKED,
                                    HandoffResult.INVALID_STATE,
                                }
                                or recorded_status is not QueueStatus.BLOCKED
                            ):
                                raise StoreError(
                                    "status-change event has inconsistent details"
                                )
                        elif recorded_status not in {
                            QueueStatus.ACTIVE,
                            QueueStatus.BLOCKED,
                        }:
                            raise StoreError(
                                "retry event has an invalid resulting status"
                            )
                        event_status = recorded_status
                    elif event["type"] == "handoff-recovered":
                        try:
                            recovered_phase = Phase(event["details"].get("phase"))
                            recovered_status = QueueStatus(
                                event["details"].get("status")
                            )
                            recovered_result = HandoffResult(
                                event["details"].get("result")
                            )
                        except (TypeError, ValueError) as error:
                            raise StoreError(
                                "recovery event has invalid resulting state"
                            ) from error
                        if (
                            recovered_phase is not previous
                            and recovered_phase not in ALLOWED_TRANSITIONS[previous]
                        ):
                            raise StoreError(
                                "recovery event records a forbidden phase change"
                            )
                        if recovered_result is HandoffResult.COMPLETED:
                            expected_status = (
                                QueueStatus.COMPLETED
                                if recovered_phase is Phase.DONE
                                else QueueStatus.ACTIVE
                            )
                            consistent = (
                                recovered_phase is not previous
                                and recovered_phase in ALLOWED_TRANSITIONS[previous]
                                and recovered_phase is not Phase.REMEDIATION
                                and recovered_status is expected_status
                            )
                        elif recovered_result is HandoffResult.NEEDS_REMEDIATION:
                            consistent = (
                                recovered_phase is Phase.REMEDIATION
                                and recovered_phase in ALLOWED_TRANSITIONS[previous]
                                and recovered_status is QueueStatus.ACTIVE
                            )
                        elif recovered_result is HandoffResult.NEEDS_OWNER_DECISION:
                            consistent = (
                                recovered_phase is previous
                                and recovered_status is QueueStatus.AWAITING_OWNER
                            )
                        elif recovered_result in {
                            HandoffResult.BLOCKED,
                            HandoffResult.INVALID_STATE,
                        }:
                            consistent = (
                                recovered_phase is previous
                                and recovered_status is QueueStatus.BLOCKED
                            )
                        else:
                            consistent = (
                                recovered_phase is previous
                                and recovered_status
                                in {QueueStatus.ACTIVE, QueueStatus.BLOCKED}
                            )
                        if not consistent:
                            raise StoreError(
                                "recovery event result contradicts phase or status"
                            )
                        event_phase = recovered_phase
                        event_status = recovered_status
                    elif event["type"] == "host-visual-gate":
                        details = event["details"]
                        if (
                            previous is not Phase.VISUAL_REVIEW
                            or not isinstance(details.get("before_digest"), str)
                            or not DIGEST.fullmatch(details["before_digest"])
                            or not isinstance(details.get("after_digest"), str)
                            or not DIGEST.fullmatch(details["after_digest"])
                            or isinstance(details.get("changed_path_count"), bool)
                            or not isinstance(details.get("changed_path_count"), int)
                            or details["changed_path_count"] < 0
                        ):
                            raise StoreError(
                                "host visual-gate event has invalid details"
                            )
                    elif event["type"] == "commit-created":
                        details = event["details"]
                        if (
                            previous is not Phase.CLOSEOUT
                            or not isinstance(details.get("branch"), str)
                            or not isinstance(details.get("parent_revision"), str)
                            or not REVISION.fullmatch(details["parent_revision"])
                            or not isinstance(details.get("commit_revision"), str)
                            or not REVISION.fullmatch(details["commit_revision"])
                            or not isinstance(details.get("commit_tree"), str)
                            or not REVISION.fullmatch(details["commit_tree"])
                            or not isinstance(details.get("commit_subject"), str)
                            or not details["commit_subject"]
                        ):
                            raise StoreError(
                                "closeout commit event has invalid details"
                            )
                if event_phase is not item.phase:
                    raise StoreError("event history does not match the queue phase")
                if event_status is not item.status:
                    raise StoreError("event history does not match the queue status")
        if not enabled:
            active = [
                item for item in queue.items if item.status is not QueueStatus.COMPLETED
            ]
            if active:
                raise StoreError("disabled orchestration has non-empty active state")
            print("PASS: orchestration is disabled with no active state.")
            return 0
        if (
            current is not None
            and current.phase is not Phase.INTAKE
            and os.environ.get("AGENT_ORCHESTRATION_SKIP_WORK_STATE") != "1"
        ):
            run_lifecycle_validator(ROOT)
        print(f"PASS: orchestration state is valid; {len(queue.items)} queue item(s).")
        return 0
    except (
        EngineError,
        ExecutorError,
        ModelError,
        ReconcileError,
        StoreError,
        GitLifecycleError,
    ) as error:
        print(f"FAIL: orchestration state is invalid: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
