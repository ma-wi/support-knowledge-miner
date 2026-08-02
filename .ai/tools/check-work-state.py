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
    "design-draft",
    "design-review",
    "implementation",
    "verification",
    "review",
    "visual-review",
    "remediation",
    "closeout",
}
IMPLEMENTATION_PHASES = {
    "implementation",
    "verification",
    "review",
    "visual-review",
    "remediation",
    "closeout",
}
READY_OR_LATER = {
    "ready",
    "in-progress",
    "implemented",
    "verified",
    "reviewed",
    "done",
}
VERIFIED_OR_LATER = {"verified", "reviewed", "done"}
SECURITY_ASSURANCE_FIELDS = (
    "Security triggers",
    "Assets and data classes",
    "Trust boundaries and untrusted inputs",
    "Authorization model",
    "Threats and abuse cases",
    "Mitigations",
    "Security verification",
    "Residual security risk",
    "Specialist security review",
)
PLACEHOLDER_VALUES = {
    "",
    "<reason>",
    "<required | not-required: reason>",
    "required | not-required: <reason>",
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


def has_reason(value: str, prefix: str) -> bool:
    normalized = value.strip()
    if not normalized.lower().startswith(f"{prefix}:"):
        return False
    reason = normalized.split(":", 1)[1].strip()
    return bool(reason) and reason.lower() not in PLACEHOLDER_VALUES


def validate_security_routing(text: str, label: str, errors: list[str]) -> str | None:
    assurance = extract_field(text, "Security assurance")
    if assurance is None:
        errors.append(
            f"{label}: missing Security assurance field; expected 'required' or "
            "'not-required: <reason>'"
        )
        return None
    normalized = assurance.lower()
    if normalized == "required":
        return normalized
    if has_reason(assurance, "not-required"):
        return "not-required"
    errors.append(
        f"{label}: Security assurance must be 'required' or 'not-required: <reason>'"
    )
    return None


def validate_required_field(
    text: str, field: str, label: str, errors: list[str]
) -> None:
    value = extract_field(text, field)
    if value is None or value.lower() in PLACEHOLDER_VALUES:
        errors.append(f"{label}: missing completed '{field}' field")
        return
    if value.lower() == "not-applicable":
        errors.append(f"{label}: '{field}' requires a reason when not applicable")


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
    spec_value = extract_field(current_text, "Specifications") or extract_field(
        current_text, "Specification"
    )
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

    declared_specs: list[str] = []
    plan_text_for_security: str | None = None
    plan_label_for_security: str | None = None
    if spec_value and spec_value.lower() != "not-required":
        declared_specs = [
            item.strip().strip("`") for item in spec_value.split(",") if item.strip()
        ]
        for declared_spec in declared_specs:
            spec = resolve_below(
                declared_spec, SPEC_ROOT, "Durable specification", errors
            )
            if spec is not None and not spec.is_file():
                errors.append(f"Declared specification does not exist: {declared_spec}")
            elif spec is not None:
                spec_text = spec.read_text(encoding="utf-8")
                spec_status = extract_field(spec_text, "Status")
                ready = extract_field(spec_text, "Ready for implementation")
                implementation_phases = {"planning", *IMPLEMENTATION_PHASES}
                if current_status in implementation_phases:
                    if spec_status != "ready-for-implementation":
                        errors.append(
                            "Specification must be ready-for-implementation during "
                            f"{current_status}; found {spec_status!r} in {declared_spec}"
                        )
                    if ready != "yes":
                        errors.append(
                            "Specification must declare "
                            "'Ready for implementation: yes' during "
                            f"{current_status}: {declared_spec}"
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
            plan_text_for_security = plan_text
            plan_label_for_security = rel(plan)
            change_class = extract_field(plan_text, "Change class")
            if change_class == "significant" and not declared_specs:
                errors.append("Significant work requires a durable specification.")

    task_files = (
        sorted(work_dir.glob("tasks/*.md")) if work_dir and work_dir.is_dir() else []
    )
    task_statuses = [
        extract_field(task_file.read_text(encoding="utf-8"), "Status")
        for task_file in task_files
    ]
    if current_status in IMPLEMENTATION_PHASES or any(
        status in READY_OR_LATER for status in task_statuses
    ):
        if plan_text_for_security is not None and plan_label_for_security is not None:
            validate_security_routing(
                plan_text_for_security, plan_label_for_security, errors
            )
            validate_required_field(
                plan_text_for_security,
                "Security triggers",
                plan_label_for_security,
                errors,
            )
            validate_required_field(
                plan_text_for_security, "Threat model", plan_label_for_security, errors
            )
            validate_required_field(
                plan_text_for_security,
                "Specialist security review",
                plan_label_for_security,
                errors,
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
        elif status in READY_OR_LATER:
            task_label = rel(task_file)
            assurance = validate_security_routing(text, task_label, errors)
            if assurance == "required":
                for field in SECURITY_ASSURANCE_FIELDS:
                    validate_required_field(text, field, task_label, errors)
            if status in VERIFIED_OR_LATER:
                pre_review = extract_field(text, "Adversarial pre-review")
                if pre_review != "passed":
                    errors.append(
                        f"{task_label}: verified work requires "
                        "'Adversarial pre-review: passed'"
                    )
                validate_required_field(text, "Pre-review lenses", task_label, errors)
                validate_required_field(text, "Pre-review evidence", task_label, errors)
                open_findings = extract_field(text, "Open P0/P1 findings")
                if open_findings != "none":
                    errors.append(
                        f"{task_label}: verified work requires "
                        "'Open P0/P1 findings: none'"
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
