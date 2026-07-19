#!/usr/bin/env python3
"""Validate temporary agent work artifacts without modifying them."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    PLAN_POINTER_PHASES,
    extract_field,
    is_inactive_plan,
)

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / ".ai" / "CURRENT_PLAN.md"
WORK_ROOT = (ROOT / ".ai" / "work").resolve()
SPEC_ROOT = (ROOT / "docs" / "specifications").resolve()
VALID_STATUSES = {
    "draft",
    "ready",
    "in-progress",
    "blocked",
    "implemented",
    "verified",
    "reviewed",
    "done",
}
VALID_PHASES = {
    "discovery",
    "specification",
    "planning",
    "implementation",
    "verification",
    "review",
    "remediation",
    "closeout",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def resolve_below(
    value: str, boundary: Path, label: str, errors: list[str]
) -> Path | None:
    candidate = (ROOT / value.rstrip("/")).resolve()
    try:
        candidate.relative_to(boundary)
    except ValueError:
        errors.append(f"{label} must be below {rel(boundary)}/.")
        return None
    return candidate


def main() -> int:
    if not CURRENT.exists():
        print("FAIL: .ai/CURRENT_PLAN.md is missing.")
        return 1

    current_text = CURRENT.read_text(encoding="utf-8")
    if is_inactive_plan(current_text):
        print("PASS: no active temporary work declared.")
        return 0

    errors: list[str] = []
    work_dir_value = extract_field(current_text, "Work directory")
    spec_value = extract_field(current_text, "Specification")
    plan_value = extract_field(current_text, "Plan")
    current_status = extract_field(current_text, "Status")
    if current_status not in VALID_PHASES:
        errors.append(f"CURRENT_PLAN.md has invalid Status: {current_status!r}")

    if not work_dir_value:
        errors.append("CURRENT_PLAN.md must contain a 'Work directory' field.")
        work_dir = None
    else:
        work_dir = resolve_below(work_dir_value, WORK_ROOT, "Work directory", errors)
        if work_dir is not None and not work_dir.is_dir():
            errors.append(f"Declared work directory does not exist: {work_dir_value}")

    if spec_value and spec_value.lower() != "not-required":
        spec = resolve_below(spec_value, SPEC_ROOT, "Durable specification", errors)
        if spec is not None and not spec.is_file():
            errors.append(f"Declared specification does not exist: {spec_value}")
        elif spec is not None:
            spec_text = spec.read_text(encoding="utf-8")
            spec_status = extract_field(spec_text, "Status")
            ready = extract_field(spec_text, "Ready for implementation")
            implementation_phases = {
                "planning",
                "implementation",
                "verification",
                "review",
                "remediation",
                "closeout",
            }
            if current_status in implementation_phases:
                if spec_status != "ready-for-implementation":
                    errors.append(
                        f"Specification must be ready-for-implementation during {current_status}; found '{spec_status}'"
                    )
                if ready != "yes":
                    errors.append(
                        f"Specification must declare 'Ready for implementation: yes' during {current_status}"
                    )

    if not plan_value:
        if current_status in PLAN_POINTER_PHASES:
            errors.append("CURRENT_PLAN.md must contain a 'Plan' field.")
    else:
        plan_boundary = work_dir if work_dir is not None else ROOT.resolve()
        plan = resolve_below(plan_value, plan_boundary, "Declared plan", errors)
        if plan is not None and not plan.is_file():
            errors.append(f"Declared plan does not exist: {plan_value}")
        elif plan is not None:
            if (
                work_dir
                and work_dir.is_dir()
                and plan.parent.resolve() != work_dir.resolve()
            ):
                errors.append(
                    "Declared plan must be directly inside the active work directory."
                )
            plan_text = plan.read_text(encoding="utf-8")
            change_class = extract_field(plan_text, "Change class")
            if change_class == "significant" and (
                not spec_value or spec_value.lower() == "not-required"
            ):
                errors.append("Significant work requires a durable specification.")

    task_files = (
        sorted(work_dir.glob("tasks/*.md")) if work_dir and work_dir.is_dir() else []
    )
    for task_file in task_files:
        text = task_file.read_text(encoding="utf-8")
        status = extract_field(text, "Status")
        if status is None:
            errors.append(f"{rel(task_file)}: missing Status field")
        elif status not in VALID_STATUSES:
            errors.append(
                f"{rel(task_file)}: invalid status '{status}'; "
                f"expected one of {', '.join(sorted(VALID_STATUSES))}"
            )

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print(
        f"PASS: active work state is structurally valid; {len(task_files)} task file(s) checked."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
