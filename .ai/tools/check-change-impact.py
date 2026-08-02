#!/usr/bin/env python3
"""Validate active incremental-change artifacts without modifying them."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    PLAN_POINTER_PHASES,
    extract_field,
    get,
    is_inactive_plan,
    load_yaml_subset,
)

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / ".ai" / "CURRENT_PLAN.md"
CONFIG = ROOT / ".ai" / "project.yaml"
WORK_ROOT = (ROOT / ".ai" / "work").resolve()
IMPLEMENTATION_PHASES = {
    "planning",
    "implementation",
    "verification",
    "review",
    "visual-review",
    "remediation",
    "closeout",
}
ALLOWED_ACTIONS = {
    "keep",
    "modify",
    "migrate",
    "deprecate",
    "remove",
    "replace",
    "not-applicable",
}
ALLOWED_CADENCES = {"per-task", "batch", "feature"}
CHANGE_REQUEST_UI_FIELDS = ("Class", "DESIGN_DELTA.md required")
TRIGGER_PATTERNS = {
    "migration": (r"\bmigrat(?:e|ion|ing)\b",),
    "public-api": (r"\bpublic[ -]?api\b", r"\bapi contract\b"),
    "authentication": (r"\bauthentication\b", r"\bauthn\b"),
    "authorization": (r"\bauthorization\b", r"\bauthz\b"),
    "security": (r"\bsecurity\b",),
    "dependency-change": (r"\bdependenc(?:y|ies)\b",),
}
NEGATIVE_DECISION = re.compile(
    r"^(?:n/?a|not[- ]applicable|not (?:needed|required|planned)|none|"
    r"no(?:\s+(?:migration|change|changes))?(?:\s+(?:needed|required|planned))?"
    r"(?:\s*[-:.;]|$)|kein(?:e|er|en)?\s+(?:migration|änderung|änderungen)"
    r"(?:\s+(?:nötig|erforderlich|geplant))?|"
    r"nicht (?:nötig|erforderlich|geplant)|entfällt(?:\s|$))",
    re.IGNORECASE,
)
ERROR_HANDLING_LAYERS = {
    "backend domain errors",
    "backend exception mapping",
    "http problem response",
    "api contract",
    "error catalog",
    "generated client error types",
    "frontend error normalization",
    "error-code mapping",
    "field error rendering",
    "form-level error rendering",
    "component-level error state",
    "page-level error state",
    "toast or transient feedback",
    "input preservation",
    "retry and recovery actions",
    "logging and correlation",
    "negative-path tests",
    "browser or visual error evidence",
    "error-handling documentation",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def resolve_work_file(
    value: str | None, work_dir: Path, label: str, errors: list[str]
) -> Path | None:
    if not value:
        errors.append(f"CURRENT_PLAN.md must contain a '{label}' field.")
        return None
    candidate = (ROOT / value.rstrip("/")).resolve()
    try:
        candidate.relative_to(work_dir.resolve())
    except ValueError:
        errors.append(f"{label} must be below the active work directory.")
        return None
    if not candidate.is_file():
        errors.append(f"Declared {label.lower()} does not exist: {value}")
        return None
    return candidate


def parse_impact_actions(text: str) -> list[tuple[int, str, str]]:
    rows: list[tuple[int, str, str]] = []
    in_matrix = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().lower() == "## impact matrix":
            in_matrix = True
            continue
        if in_matrix and line.startswith("## "):
            break
        if not in_matrix or not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() in {"layer or concern", "---"} or set(cells[0]) == {"-"}:
            continue
        rows.append((number, cells[0], cells[2].lower()))
    return rows


def configured_review_triggers(config: dict) -> set[str]:
    value = get(
        config,
        "incremental_changes",
        "force_task_review_for",
        default="",
    )
    return {item for item in str(value).split() if item}


def active_trigger_lines(
    configured: set[str], change_text: str, impact_text: str
) -> list[tuple[str, str, int]]:
    """Find configured risk categories in active fields and impact rows."""
    matches: list[tuple[str, str, int]] = []
    for source, text in (("CHANGE.md", change_text), ("IMPACT.md", impact_text)):
        impact_rows = {
            number: action for number, _, action in parse_impact_actions(text)
        }
        for number, line in enumerate(text.splitlines(), 1):
            lowered = line.lower()
            if source == "IMPACT.md":
                action = impact_rows.get(number)
                if action is None or action in {"keep", "not-applicable"}:
                    continue
            elif re.match(r"^-\s*[^:]+:", line):
                label, value = line.split(":", 1)
                value = value.strip().lower()
                if not value or NEGATIVE_DECISION.match(value):
                    continue
                lowered = f"{label.lower()}: {value}"
            else:
                continue
            for category in sorted(configured):
                escaped = re.escape(category).replace(r"\-", "[ -]?")
                patterns = TRIGGER_PATTERNS.get(category, (rf"\b{escaped}\b",))
                triggered = any(re.search(pattern, lowered) for pattern in patterns)
                if (
                    category == "migration"
                    and source == "IMPACT.md"
                    and impact_rows.get(number) == "migrate"
                ):
                    triggered = True
                if triggered:
                    matches.append((category, source, number))
    return matches


def main() -> int:
    if not CURRENT.exists():
        print("FAIL: .ai/CURRENT_PLAN.md is missing.")
        return 1

    current_text = CURRENT.read_text(encoding="utf-8")
    if is_inactive_plan(current_text):
        print("PASS: no active incremental change declared.")
        return 0

    work_type = extract_field(current_text, "Work type")
    if work_type not in {"new-capability", "incremental-change"}:
        print(
            "FAIL: active CURRENT_PLAN.md must declare "
            "'Work type: new-capability | incremental-change'."
        )
        return 1
    if work_type != "incremental-change":
        print("PASS: active work is not an incremental change.")
        return 0

    errors: list[str] = []
    warnings: list[str] = []
    config = load_yaml_subset(CONFIG)
    ui_quality_enabled = get(config, "ui_quality", "enabled", default=False) is True
    user_errors_enabled = (
        get(config, "user_facing_errors", "enabled", default=False) is True
    )
    error_routing = (extract_field(current_text, "Error handling") or "").strip()
    error_handling_required = user_errors_enabled and error_routing == "required"
    phase = extract_field(current_text, "Status") or ""
    if user_errors_enabled and phase in IMPLEMENTATION_PHASES:
        not_applicable = error_routing.startswith("not-applicable:") and bool(
            error_routing.partition(":")[2].strip()
        )
        if error_routing != "required" and not not_applicable:
            errors.append(
                "CURRENT_PLAN.md must declare 'Error handling: required' or "
                "'Error handling: not-applicable: <reason>'."
            )
    work_dir_value = extract_field(current_text, "Work directory")
    if not work_dir_value:
        print("FAIL: CURRENT_PLAN.md must contain a 'Work directory' field.")
        return 1
    work_dir = (ROOT / work_dir_value.rstrip("/")).resolve()
    try:
        work_dir.relative_to(WORK_ROOT)
    except ValueError:
        print("FAIL: Work directory must be below .ai/work/.")
        return 1
    if not work_dir.is_dir():
        print(f"FAIL: active work directory does not exist: {work_dir_value}")
        return 1

    change = resolve_work_file(
        extract_field(current_text, "Change request"),
        work_dir,
        "Change request",
        errors,
    )

    impact_pointer = extract_field(current_text, "Change impact")
    impact = None
    if impact_pointer or phase in PLAN_POINTER_PHASES:
        impact = resolve_work_file(impact_pointer, work_dir, "Change impact", errors)

    plan_pointer = extract_field(current_text, "Plan")
    plan = None
    if plan_pointer or phase in PLAN_POINTER_PHASES:
        plan = resolve_work_file(plan_pointer, work_dir, "Plan", errors)

    if change is not None:
        change_text = change.read_text(encoding="utf-8")
        design_class = extract_field(change_text, CHANGE_REQUEST_UI_FIELDS[0])
        design_required = extract_field(change_text, CHANGE_REQUEST_UI_FIELDS[1])
        if (
            ui_quality_enabled
            and phase in PLAN_POINTER_PHASES
            and design_class not in {"0", "1", "2", "3"}
        ):
            errors.append(f"{rel(change)}: invalid or missing design Class")
        if ui_quality_enabled and (
            design_class in {"2", "3"} or design_required == "yes"
        ):
            design_delta = work_dir / "DESIGN_DELTA.md"
            if not design_delta.is_file():
                errors.append(
                    f"{rel(change)} requires {rel(design_delta)}, but it does not exist"
                )
            elif phase in IMPLEMENTATION_PHASES:
                delta_text = design_delta.read_text(encoding="utf-8")
                if extract_field(delta_text, "Status") != "approved":
                    errors.append(
                        f"{rel(design_delta)} must have Status: approved during {phase}"
                    )
        if phase in IMPLEMENTATION_PHASES:
            if extract_field(change_text, "Status") != "ready-for-implementation":
                errors.append(
                    f"{rel(change)} must be ready-for-implementation during {phase}"
                )
            if extract_field(change_text, "Ready for implementation") != "yes":
                errors.append(
                    f"{rel(change)} must declare "
                    f"'Ready for implementation: yes' during {phase}"
                )
            if extract_field(change_text, "Impact analysis accepted") != "yes":
                errors.append(
                    f"{rel(change)} must declare "
                    f"'Impact analysis accepted: yes' during {phase}"
                )

    if impact is not None:
        impact_text = impact.read_text(encoding="utf-8")
        rows = parse_impact_actions(impact_text)
        valid_rows = 0
        for line_number, layer, action in rows:
            if action in ALLOWED_ACTIONS:
                valid_rows += 1
            elif phase in IMPLEMENTATION_PHASES:
                errors.append(
                    f"{rel(impact)}:{line_number}: impact row {layer!r} "
                    f"has invalid or empty action {action!r}"
                )
        if phase in IMPLEMENTATION_PHASES:
            if error_handling_required:
                present = {layer.strip().lower() for _, layer, _ in rows}
                missing = sorted(ERROR_HANDLING_LAYERS - present)
                if missing:
                    errors.append(
                        f"{rel(impact)} is missing user-facing error impact rows: "
                        + ", ".join(missing)
                    )
            if extract_field(impact_text, "Status") != "accepted":
                errors.append(
                    f"{rel(impact)} must have Status: accepted during {phase}"
                )
            if extract_field(impact_text, "Impact analysis complete") != "yes":
                errors.append(
                    f"{rel(impact)} must declare "
                    f"'Impact analysis complete: yes' during {phase}"
                )
            no_unclassified = extract_field(
                impact_text, "No relevant references remain unclassified"
            )
            if no_unclassified != "yes":
                errors.append(
                    f"{rel(impact)} must declare no unclassified relevant "
                    f"references during {phase}"
                )
            if valid_rows == 0:
                errors.append(
                    f"{rel(impact)} must contain at least one classified impact row"
                )

    if plan is not None:
        plan_text = plan.read_text(encoding="utf-8")
        cadence = extract_field(plan_text, "Cadence")
        default_cadence = str(
            get(
                config,
                "incremental_changes",
                "default_review_cadence",
                default="batch",
            )
        )
        if cadence is None:
            warnings.append(
                f"{rel(plan)} has no review Cadence; configured default "
                f"{default_cadence!r} applies"
            )
            effective_cadence = default_cadence
        elif cadence not in ALLOWED_CADENCES:
            errors.append(f"{rel(plan)} has invalid review Cadence: {cadence!r}")
            effective_cadence = cadence
        else:
            effective_cadence = cadence

        if change is not None and impact is not None:
            detected = active_trigger_lines(
                configured_review_triggers(config),
                change.read_text(encoding="utf-8"),
                impact.read_text(encoding="utf-8"),
            )
            if detected and effective_cadence != "per-task":
                details = ", ".join(
                    f"{category} ({source}:{number})"
                    for category, source, number in detected
                )
                errors.append(
                    f"{rel(plan)} must use Cadence: per-task because configured "
                    f"review triggers were detected: {details}"
                )
        forced = (
            (extract_field(plan_text, "Forced per-task review triggers present") or "")
            .strip()
            .lower()
        )
        if (
            forced not in {"", "none", "no", "not-applicable"}
            and effective_cadence != "per-task"
        ):
            errors.append(
                f"{rel(plan)} declares forced per-task triggers "
                f"but cadence is {effective_cadence!r}"
            )

        max_batch = int(
            get(
                config,
                "incremental_changes",
                "max_tasks_per_review_batch",
                default=3,
            )
        )
        batches: Counter[str] = Counter()
        for task in sorted(work_dir.glob("tasks/*.md")):
            task_text = task.read_text(encoding="utf-8")
            batch = extract_field(task_text, "Review batch")
            if not batch:
                errors.append(f"{rel(task)}: missing Review batch field")
                continue
            batches[batch] += 1
        if effective_cadence == "batch":
            for batch, count in sorted(batches.items()):
                if count > max_batch:
                    errors.append(
                        f"review batch {batch!r} contains {count} tasks; "
                        f"configured maximum is {max_batch}"
                    )

    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: active incremental-change artifacts are structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
