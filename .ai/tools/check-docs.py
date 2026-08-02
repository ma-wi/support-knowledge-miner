#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
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
CONFIG = ROOT / ".ai" / "project.yaml"
FORBIDDEN_PLACEHOLDERS = re.compile(r"CHANGE_ME|TODO_TEMPLATE|<[A-Z][A-Z0-9_]+>")
REQUIRED_CONTEXT_FIELDS = ("Product or service", "Primary users", "Main outcome")
REQUIRED_QUALITY_DECISIONS = (
    "Minimum coverage policy",
    "Supported runtime matrix",
    "Warning-as-error policy",
    "Security severity threshold",
    "Dependency update policy",
    "Flaky-test policy",
    "CI required checks",
)
QUALITY_REVIEW_FIELD = "Project decisions reviewed"


def meaningful_lines(path: Path) -> int:
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def word_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").split())


def total_words(paths: list[Path] | set[Path]) -> int:
    return sum(word_count(path) for path in set(paths) if path.is_file())


def active_context_paths(current: Path) -> set[Path]:
    if not current.is_file():
        return set()
    text = current.read_text(encoding="utf-8")
    if is_inactive_plan(text):
        return set()
    paths = {current}
    work_value = extract_field(text, "Work directory")
    if work_value:
        candidate = (ROOT / work_value.strip().strip("`").rstrip("/")).resolve()
        try:
            candidate.relative_to((ROOT / ".ai/work").resolve())
        except ValueError:
            work_dir = None
        else:
            work_dir = candidate
        if work_dir is not None and work_dir.is_dir():
            for path in work_dir.rglob("*.md"):
                resolved = path.resolve()
                try:
                    resolved.relative_to(work_dir)
                except ValueError:
                    continue
                if resolved.is_file():
                    paths.add(resolved)
    for field in ("Requirement", "Specification", "Specifications"):
        value = extract_field(text, field)
        if not value or value.lower() == "not-required":
            continue
        for item in value.split(","):
            candidate = (ROOT / item.strip().strip("`")).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError:
                continue
            if candidate.is_file():
                paths.add(candidate)
    return paths


def markdown_links(path: Path):
    text = path.read_text(encoding="utf-8")
    for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip().split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield target


def require_filled_fields(
    path: Path, fields: tuple[str, ...], label: str, messages: list[str]
) -> None:
    if not path.is_file():
        messages.append(f"required {label} file is missing: {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8")
    for field in fields:
        match = re.search(
            rf"^-[ \t]*{re.escape(field)}:[ \t]*([^\r\n]*)$",
            text,
            re.MULTILINE,
        )
        if match is None or not match.group(1).strip():
            messages.append(f"{label} field is incomplete: {field}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    data = load_yaml_subset(CONFIG)
    template_state = (
        str(get(data, "project", "name", default="CHANGE_ME")) == "CHANGE_ME"
    )
    budgets = get(data, "documentation", "budgets", default={}) or {}
    ui_quality_enabled = get(data, "ui_quality", "enabled", default=False) is True
    orchestration_enabled = get(data, "orchestration", "enabled", default=False) is True
    user_errors_enabled = (
        get(data, "user_facing_errors", "enabled", default=False) is True
    )

    if not template_state:
        require_filled_fields(
            ROOT / ".ai/PROJECT_CONTEXT.md",
            REQUIRED_CONTEXT_FIELDS,
            "project context",
            warnings,
        )
        require_filled_fields(
            ROOT / ".ai/policies/QUALITY_GATES.md",
            REQUIRED_QUALITY_DECISIONS,
            "quality decision",
            errors,
        )
        quality_path = ROOT / ".ai/policies/QUALITY_GATES.md"
        if quality_path.is_file():
            quality_text = quality_path.read_text(encoding="utf-8")
            reviewed = re.search(
                rf"^-[ \t]*{re.escape(QUALITY_REVIEW_FIELD)}:[ \t]*([^\r\n]*)$",
                quality_text,
                re.MULTILINE,
            )
            if reviewed is None or reviewed.group(1).strip().lower() != "yes":
                errors.append(
                    "quality decisions require explicit review: set "
                    "'Project decisions reviewed: yes'"
                )
        security = ROOT / "SECURITY.md"
        if not security.is_file():
            errors.append("required security reporting file is missing: SECURITY.md")
        elif FORBIDDEN_PLACEHOLDERS.search(
            security.read_text(encoding="utf-8", errors="replace")
        ):
            errors.append("security reporting contact is incomplete: SECURITY.md")

    if ui_quality_enabled:
        design_system = ROOT / str(
            get(
                data,
                "ui_quality",
                "design_system",
                "document",
                default="docs/design/DESIGN_SYSTEM.md",
            )
        )
        component_catalog = ROOT / str(
            get(
                data,
                "ui_quality",
                "design_system",
                "component_catalog",
                default="docs/design/COMPONENT_CATALOG.md",
            )
        )
        require_filled_fields(
            design_system,
            ("Primary component foundation",),
            "design system",
            errors,
        )
        if not component_catalog.is_file():
            errors.append(
                "required component catalog file is missing: "
                f"{component_catalog.relative_to(ROOT)}"
            )
        configured = {design_system.resolve(), component_catalog.resolve()}
        for name in ("DESIGN_SYSTEM.md", "COMPONENT_CATALOG.md"):
            for path in ROOT.rglob(name):
                if path.resolve() not in configured and not any(
                    part in {".git", ".ai", "node_modules"} for part in path.parts
                ):
                    errors.append(
                        "parallel design source conflicts with configured canonical "
                        f"document: {path.relative_to(ROOT)}"
                    )

    if template_state or ui_quality_enabled:
        for name in (
            "UI_QUALITY.md",
            "UI_QUALITY_PROTOTYPES.md",
            "UI_QUALITY_VISUAL.md",
        ):
            path = ROOT / ".ai/policies" / name
            if not path.is_file():
                errors.append(
                    f"required routed UI policy is missing: {path.relative_to(ROOT)}"
                )

    if user_errors_enabled:
        error_policy = ROOT / ".ai/policies/USER_FACING_ERROR_HANDLING.md"
        if not error_policy.is_file():
            errors.append(
                "required user-facing error policy is missing: "
                ".ai/policies/USER_FACING_ERROR_HANDLING.md"
            )
        error_catalog = ROOT / str(
            get(
                data,
                "user_facing_errors",
                "catalog",
                "path",
                default="docs/errors/ERROR_CATALOG.md",
            )
        )
        if not error_catalog.is_file():
            errors.append(
                f"required error catalog is missing: {error_catalog.relative_to(ROOT)}"
            )
        else:
            for path in ROOT.rglob("ERROR_CATALOG.md"):
                if path.resolve() != error_catalog.resolve() and not any(
                    part in {".git", ".ai", "node_modules"} for part in path.parts
                ):
                    errors.append(
                        "parallel error catalog conflicts with configured canonical "
                        f"document: {path.relative_to(ROOT)}"
                    )

    if template_state or user_errors_enabled:
        required_error_policies = ["USER_FACING_ERROR_HANDLING.md"]
        if template_state or get(
            data,
            "user_facing_errors",
            "api_contract",
            "enabled",
            default=True,
        ):
            required_error_policies.append("USER_FACING_ERROR_API.md")
        if template_state or get(
            data,
            "user_facing_errors",
            "frontend",
            "enabled",
            default=False,
        ):
            required_error_policies.append("USER_FACING_ERROR_FRONTEND.md")
        for name in required_error_policies:
            path = ROOT / ".ai/policies" / name
            if not path.is_file():
                errors.append(
                    f"required routed error policy is missing: {path.relative_to(ROOT)}"
                )

    if template_state:
        for name in (
            "CHANGE_IMPACT_ERRORS.md",
            "CHANGE_IMPACT_UI.md",
            "CHANGE_REQUEST_ERRORS.md",
            "CHANGE_REQUEST_UI.md",
            "IMPLEMENTATION_PLAN_ERRORS.md",
            "IMPLEMENTATION_PLAN_UI.md",
            "FEATURE_SPEC_ERRORS.md",
            "REQUIREMENTS_ERRORS.md",
            "REVIEW_REPORT_ERRORS.md",
            "REVIEW_REPORT_UI.md",
            "WORK_ITEM_ERRORS.md",
            "WORK_ITEM_UI.md",
        ):
            path = ROOT / ".ai/templates" / name
            if not path.is_file():
                errors.append(
                    f"required conditional template annex is missing: {path.relative_to(ROOT)}"
                )

    budget_files = {
        "agents_md_lines": ROOT / "AGENTS.md",
        "readme_lines": ROOT / "README.md",
        "project_context_lines": ROOT / ".ai/PROJECT_CONTEXT.md",
        "current_plan_lines": ROOT / ".ai/CURRENT_PLAN.md",
    }
    for key, path in budget_files.items():
        limit = budgets.get(key)
        if isinstance(limit, int) and path.exists():
            count = meaningful_lines(path)
            if count > limit:
                warnings.append(
                    f"{path.relative_to(ROOT)} has {count} nonblank lines; budget is {limit}"
                )

    next_limit = budgets.get("next_steps_items")
    next_path = ROOT / ".ai/NEXT_STEPS.md"
    if isinstance(next_limit, int) and next_path.exists():
        items = sum(
            1
            for line in next_path.read_text(encoding="utf-8").splitlines()
            if re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
        )
        if items > next_limit:
            warnings.append(
                f"{next_path.relative_to(ROOT)} has {items} list items; budget is {next_limit}"
            )

    work_limit = budgets.get("active_work_item_lines")
    if isinstance(work_limit, int):
        for path in sorted((ROOT / ".ai/work").glob("*/tasks/*.md")):
            count = meaningful_lines(path)
            if count > work_limit:
                warnings.append(
                    f"{path.relative_to(ROOT)} has {count} nonblank lines; budget is {work_limit}"
                )

    for budget_key, directory in (
        ("policy_lines", ROOT / ".ai/policies"),
        ("role_lines", ROOT / ".ai/roles"),
        ("template_lines", ROOT / ".ai/templates"),
    ):
        limit = budgets.get(budget_key)
        if not isinstance(limit, int):
            continue
        for path in sorted(directory.glob("*.md")):
            count = meaningful_lines(path)
            if count > limit:
                warnings.append(
                    f"{path.relative_to(ROOT)} has {count} nonblank lines; budget is {limit}"
                )

    common_instruction_paths = [
        ROOT / "AGENTS.md",
        ROOT / ".ai/project.yaml",
        ROOT / ".ai/PROJECT_CONTEXT.md",
        ROOT / ".ai/policies/WORKFLOW.md",
        ROOT / ".ai/policies/REVIEW_LENSES.md",
        ROOT / ".ai/policies/SECURITY_GUIDELINES.md",
        ROOT / ".ai/policies/DEPENDENCY_POLICY.md",
        ROOT / ".ai/policies/DOCUMENTATION_RULES.md",
        ROOT / ".ai/policies/QUALITY_GATES.md",
    ]
    if orchestration_enabled:
        common_instruction_paths.append(ROOT / ".ai/policies/ORCHESTRATION.md")
    if user_errors_enabled:
        common_instruction_paths.append(
            ROOT / ".ai/policies/USER_FACING_ERROR_HANDLING.md"
        )
        if get(
            data,
            "user_facing_errors",
            "api_contract",
            "enabled",
            default=True,
        ):
            common_instruction_paths.append(
                ROOT / ".ai/policies/USER_FACING_ERROR_API.md"
            )
        if get(
            data,
            "user_facing_errors",
            "frontend",
            "enabled",
            default=False,
        ):
            common_instruction_paths.append(
                ROOT / ".ai/policies/USER_FACING_ERROR_FRONTEND.md"
            )
    if ui_quality_enabled:
        common_instruction_paths.extend(
            [
                ROOT / ".ai/policies/UI_QUALITY.md",
                ROOT / ".ai/policies/UI_QUALITY_PROTOTYPES.md",
                ROOT / ".ai/policies/UI_QUALITY_VISUAL.md",
            ]
        )
    always_rule = ROOT / ".aiassistant/rules/project-conventions.md"
    routed_rules = [
        path
        for path in (ROOT / ".aiassistant/rules").glob("*.md")
        if path != always_rule
    ]
    routed_rule_words = max((word_count(path) for path in routed_rules), default=0)
    role_routes: list[tuple[str, int]] = []
    for role in sorted((ROOT / ".ai/roles").glob("*.md")):
        for work_type in ("new-capability", "incremental-change"):
            paths = [*common_instruction_paths, role, always_rule]
            if work_type == "incremental-change":
                paths.append(ROOT / ".ai/policies/INCREMENTAL_CHANGE_WORKFLOW.md")
            if role.name == "IMPLEMENTER.md":
                paths.append(ROOT / ".aiassistant/review/self-review.md")
            role_routes.append(
                (f"{role.stem}:{work_type}", total_words(paths) + routed_rule_words)
            )
    routed_label, routed_words = (
        max(role_routes, key=lambda item: item[1])
        if role_routes
        else (
            "base:no-role",
            total_words([*common_instruction_paths, always_rule]) + routed_rule_words,
        )
    )
    instruction_limit = budgets.get("worst_case_instruction_words")
    if isinstance(instruction_limit, int) and routed_words > instruction_limit:
        warnings.append(
            f"worst-case routed instruction context ({routed_label}) has "
            f"{routed_words} words; budget is {instruction_limit}"
        )

    template_root = ROOT / ".ai/templates"
    base_template_sets = {
        "new-capability": [
            "REQUIREMENTS.md",
            "FEATURE_SPEC.md",
            "IMPLEMENTATION_PLAN.md",
            "WORK_ITEM.md",
            "REVIEW_REPORT.md",
        ],
        "incremental-change": [
            "CHANGE_REQUEST.md",
            "CHANGE_IMPACT.md",
            "IMPLEMENTATION_PLAN.md",
            "WORK_ITEM.md",
            "REVIEW_REPORT.md",
        ],
    }
    template_routes: list[tuple[str, int]] = []
    for route, names in base_template_sets.items():
        routed_names = list(names)
        if user_errors_enabled:
            routed_names.extend(
                (
                    ["REQUIREMENTS_ERRORS.md", "FEATURE_SPEC_ERRORS.md"]
                    if route == "new-capability"
                    else ["CHANGE_REQUEST_ERRORS.md", "CHANGE_IMPACT_ERRORS.md"]
                )
            )
            routed_names.extend(
                [
                    "IMPLEMENTATION_PLAN_ERRORS.md",
                    "WORK_ITEM_ERRORS.md",
                    "REVIEW_REPORT_ERRORS.md",
                ]
            )
        if ui_quality_enabled:
            if route == "incremental-change":
                routed_names.extend(["CHANGE_REQUEST_UI.md", "CHANGE_IMPACT_UI.md"])
            routed_names.extend(
                [
                    "IMPLEMENTATION_PLAN_UI.md",
                    "WORK_ITEM_UI.md",
                    "REVIEW_REPORT_UI.md",
                    "DESIGN_DELTA.md",
                    "CLOSEOUT.md",
                ]
            )
        template_routes.append(
            (
                route,
                total_words([template_root / name for name in routed_names]),
            )
        )
    template_label, template_words = max(template_routes, key=lambda item: item[1])
    template_limit = budgets.get("worst_case_composed_template_words")
    if isinstance(template_limit, int) and template_words > template_limit:
        warnings.append(
            f"worst-case composed template context ({template_label}) has "
            f"{template_words} words; budget is {template_limit}"
        )

    active_words = total_words(active_context_paths(ROOT / ".ai/CURRENT_PLAN.md"))
    active_limit = budgets.get("active_work_context_words")
    if isinstance(active_limit, int) and active_words > active_limit:
        warnings.append(
            f"active work context has {active_words} words; budget is {active_limit}"
        )

    checked_roots = [
        ROOT / "README.md",
        ROOT / "SECURITY.md",
        ROOT / "AGENTS.md",
        ROOT / ".ai",
        ROOT / "docs",
    ]
    for entry in checked_roots:
        paths = (
            [entry]
            if entry.is_file()
            else list(entry.rglob("*.md")) + list(entry.rglob("*.yaml"))
        )
        for path in paths:
            if path.name.endswith(".example") or "templates" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if FORBIDDEN_PLACEHOLDERS.search(text):
                message = f"template placeholder remains in {path.relative_to(ROOT)}"
                (warnings if template_state else errors).append(message)

    for path in list(ROOT.rglob("*.md")):
        if any(part in {".git", ".venv", "node_modules"} for part in path.parts):
            continue
        for target in markdown_links(path):
            target_path = (path.parent / target).resolve()
            try:
                target_path.relative_to(ROOT.resolve())
            except ValueError:
                continue
            if not target_path.exists():
                errors.append(
                    f"broken local link in {path.relative_to(ROOT)}: {target}"
                )

    current = ROOT / ".ai/CURRENT_PLAN.md"
    if current.exists():
        text = current.read_text(encoding="utf-8")
        if not is_inactive_plan(text):
            status = extract_field(text, "Status")
            needs_plan = status in PLAN_POINTER_PHASES
            if "Work directory:" not in text or (needs_plan and "Plan:" not in text):
                errors.append(
                    "CURRENT_PLAN.md is active but lacks Work directory or Plan pointer"
                )

    print("Documentation consistency check")
    print(
        "Context metrics: "
        f"routed={routed_words} ({routed_label}), "
        f"templates={template_words} ({template_label}), active={active_words}"
    )
    for message in warnings:
        print(f"WARN: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: no documentation errors; {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
