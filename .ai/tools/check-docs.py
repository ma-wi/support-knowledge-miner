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
INCOMPLETE_SECURITY_MARKERS = (
    "Replace this section with the project's private security reporting channel",
    "Document supported release lines and security-update policy",
)
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


def meaningful_lines(path: Path) -> int:
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def markdown_links(path: Path):
    text = path.read_text(encoding="utf-8")
    for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip().split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield target


def require_filled_fields(
    path: Path, fields: tuple[str, ...], label: str, errors: list[str]
) -> None:
    if not path.is_file():
        errors.append(f"required {label} file is missing: {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8")
    for field in fields:
        match = re.search(
            rf"^-[ \t]*{re.escape(field)}:[ \t]*([^\r\n]*)$",
            text,
            re.MULTILINE,
        )
        if match is None or not match.group(1).strip():
            errors.append(f"{label} field is incomplete: {field}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    data = load_yaml_subset(CONFIG)
    template_state = (
        str(get(data, "project", "name", default="CHANGE_ME")) == "CHANGE_ME"
    )
    budgets = get(data, "documentation", "budgets", default={}) or {}

    if not template_state:
        security_path = ROOT / "SECURITY.md"
        if not security_path.is_file():
            errors.append("required security policy is missing: SECURITY.md")
        else:
            security_text = security_path.read_text(encoding="utf-8")
            if not re.search(
                r"^-\s*Status:\s*ready\s*$", security_text, re.MULTILINE
            ) or any(marker in security_text for marker in INCOMPLETE_SECURITY_MARKERS):
                errors.append("security reporting channel is incomplete in SECURITY.md")
        require_filled_fields(
            ROOT / ".ai/PROJECT_CONTEXT.md",
            REQUIRED_CONTEXT_FIELDS,
            "project context",
            errors,
        )
        require_filled_fields(
            ROOT / ".ai/policies/QUALITY_GATES.md",
            REQUIRED_QUALITY_DECISIONS,
            "quality decision",
            errors,
        )

    budget_files = {
        "agents_md_lines": ROOT / "AGENTS.md",
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

    checked_roots = [
        ROOT / "README.md",
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
