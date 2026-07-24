#!/usr/bin/env python3
"""Validate active incremental-change artifacts without modifying them."""

from __future__ import annotations

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

    phase = extract_field(current_text, "Status") or ""
    change = resolve_work_file(
        extract_field(current_text, "Change request"),
        work_dir,
        "Change request",
        errors,
    )

    impact_pointer = extract_field(current_text, "Change impact")
    impact = None
    if impact_pointer or phase in PLAN_POINTER_PHASES:
        impact = resolve_work_file(
            impact_pointer, work_dir, "Change impact", errors
        )

    plan_pointer = extract_field(current_text, "Plan")
    plan = None
    if plan_pointer or phase in PLAN_POINTER_PHASES:
        plan = resolve_work_file(plan_pointer, work_dir, "Plan", errors)

    if change is not None:
        change_text = change.read_text(encoding="utf-8")
        design_class = extract_field(change_text, "Class")
        design_required = extract_field(change_text, "DESIGN_DELTA.md required")
        if phase in PLAN_POINTER_PHASES and design_class not in {"0", "1", "2", "3"}:
            errors.append(f"{rel(change)}: invalid or missing design Class")
        if design_class in {"2", "3"} or design_required == "yes":
            design_delta = work_dir / "DESIGN_DELTA.md"
            if not design_delta.is_file():
                errors.append(
                    f"{rel(change)} requires {rel(design_delta)}, but it does not exist"
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
        if cadence not in ALLOWED_CADENCES:
            errors.append(
                f"{rel(plan)} has invalid or missing review Cadence: {cadence!r}"
            )
        forced = (
            extract_field(plan_text, "Forced per-task review triggers present")
            or ""
        ).strip().lower()
        if forced not in {"", "none", "no", "not-applicable"} and cadence != "per-task":
            errors.append(
                f"{rel(plan)} declares forced per-task triggers "
                f"but cadence is {cadence!r}"
            )

        config = load_yaml_subset(CONFIG)
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
        if cadence == "batch":
            for batch, count in sorted(batches.items()):
                if count > max_batch:
                    errors.append(
                        f"review batch {batch!r} contains {count} tasks; "
                        f"configured maximum is {max_batch}"
                    )

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: active incremental-change artifacts are structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
