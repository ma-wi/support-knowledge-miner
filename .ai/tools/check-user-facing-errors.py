#!/usr/bin/env python3
"""Validate configured user-facing error contracts without modifying the project."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    VISUAL_EVIDENCE_FIELDS,
    extract_field,
    get,
    is_inactive_plan,
    load_yaml_subset,
    resolve_frontend_source_root,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".ai" / "project.yaml"
CURRENT = ROOT / ".ai" / "CURRENT_PLAN.md"
CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
CODE_TOKEN = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
BLOCKING_PHASES = {
    "implementation",
    "verification",
    "review",
    "visual-review",
    "remediation",
    "closeout",
}
EVIDENCE_PHASES = {"verification", "review", "visual-review", "closeout"}
READY_TASK_STATUSES = {
    "ready",
    "in-progress",
    "implemented",
    "verified",
    "reviewed",
    "done",
}
CATALOG_FIELDS = (
    "Status",
    "Category",
    "Trigger",
    "HTTP status",
    "Problem type",
    "User-facing title",
    "User-facing explanation",
    "Suggested action",
    "Suggested action code",
    "Retryable",
    "UI placement",
    "Input preservation",
    "Correlation reference",
    "Security considerations",
    "Backend source",
    "API contract",
    "Frontend mapping",
    "Required tests",
)
GENERIC_MESSAGES = {
    "error",
    "fehler",
    "could not be loaded",
    "konnte nicht geladen werden",
    "something went wrong",
    "saving failed",
    "speichern fehlgeschlagen",
}
IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
}
SOURCE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".java",
    ".kt",
    ".cs",
    ".vb",
}


@dataclass(frozen=True)
class CatalogEntry:
    code: str
    fields: dict[str, str]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def resolve_below_root(value: str, label: str, errors: list[str]) -> Path | None:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        errors.append(f"{label} must stay below the repository root")
        return None
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        errors.append(f"{label} must stay below the repository root")
        return None
    return resolved


def section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^##[ \t]+{re.escape(heading)}[ \t]*$\n(.*?)(?=^##[ \t]+|\Z)",
        text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1) if match else None


def has_heading(text: str, heading: str, level: int | None = None) -> bool:
    hashes = rf"#{{{level}}}" if level is not None else r"#{2,6}"
    return (
        re.search(
            rf"^{hashes}[ \t]+{re.escape(heading)}[ \t]*$",
            text,
            re.MULTILINE | re.IGNORECASE,
        )
        is not None
    )


def table_rows(body: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if cells[0].lower() in {
            "action",
            "aktion",
            "failure",
            "error code",
            "error code / failure",
        }:
            continue
        rows.append(cells)
    return rows


def clean_code(value: str) -> str:
    return value.strip().strip("`")


def parse_catalog(text: str, errors: list[str]) -> dict[str, CatalogEntry]:
    active = section(text, "Active entries")
    if active is None:
        errors.append("error catalog must contain '## Active entries'")
        return {}
    entries: dict[str, CatalogEntry] = {}
    matches = list(
        re.finditer(
            r"^###\s+`?([A-Z][A-Z0-9_]*)`?\s*$",
            active,
            re.MULTILINE,
        )
    )
    for index, match in enumerate(matches):
        code = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(active)
        body = active[match.end() : end]
        fields: dict[str, str] = {}
        for name in CATALOG_FIELDS:
            value = extract_field(body, name)
            if name == "Required tests" and value is None:
                required_tests = re.search(
                    r"^-\s*Required tests:\s*$\n"
                    r"((?:[ \t]+-\s+.+\n?)+)",
                    body,
                    re.MULTILINE,
                )
                value = required_tests.group(1).strip() if required_tests else None
            if value is None or not value.strip():
                errors.append(f"catalog entry {code} is missing {name}")
            else:
                fields[name] = value.strip()
        if fields.get("Status") not in {"active", "deprecated"}:
            errors.append(f"catalog entry {code} has invalid Status")
        if fields.get("Status") == "deprecated":
            if not re.search(
                r"^-\s*Replacement:\s*\S.+$",
                body,
                re.MULTILINE,
            ):
                errors.append(f"deprecated catalog entry {code} needs Replacement")
            if not re.search(
                r"^-\s*Removal criterion:\s*\S.+$",
                body,
                re.MULTILINE,
            ):
                errors.append(
                    f"deprecated catalog entry {code} needs Removal criterion"
                )
        if fields.get("Status") == "active":
            explanation = (
                fields.get("User-facing explanation", "").strip().rstrip(".").lower()
            )
            if explanation in GENERIC_MESSAGES:
                errors.append(f"catalog entry {code} uses a generic explanation")
        if code in entries:
            errors.append(f"catalog contains duplicate active entry {code}")
        entries[code] = CatalogEntry(code, fields)
    return entries


def require_matrix(
    path: Path,
    text: str,
    errors: list[str],
    *,
    catalog_codes: set[str],
    block_generic: bool,
) -> set[str]:
    body = section(text, "Error-and-Recovery Matrix")
    if body is None:
        errors.append(f"{rel(path)}: missing Error-and-Recovery Matrix")
        return set()
    rows = table_rows(body)
    if not rows:
        errors.append(f"{rel(path)}: Error-and-Recovery Matrix has no data rows")
        return set()
    found: set[str] = set()
    for index, cells in enumerate(rows, 1):
        if len(cells) < 7:
            errors.append(
                f"{rel(path)}: Error-and-Recovery Matrix row {index} "
                "must contain at least action, failure, code, message, placement, "
                "recovery, and input preservation"
            )
            continue
        if any(not cell or cell in {"-", "TBD", "TODO"} for cell in cells):
            errors.append(
                f"{rel(path)}: Error-and-Recovery Matrix row {index} is incomplete"
            )
        code = clean_code(cells[2])
        if code.lower() == "not-applicable":
            if not any("reason" in cell.lower() or ":" in cell for cell in cells):
                errors.append(f"{rel(path)}: not-applicable row {index} needs a reason")
            continue
        if not CODE_PATTERN.fullmatch(code):
            errors.append(f"{rel(path)}: invalid error code {code!r}")
            continue
        found.add(code)
        if code not in catalog_codes:
            errors.append(f"{rel(path)}: active code {code} has no catalog entry")
        if block_generic:
            normalized = cells[3].strip().rstrip(".").lower()
            if normalized in GENERIC_MESSAGES:
                errors.append(
                    f"{rel(path)}: known code {code} uses generic message {cells[3]!r}"
                )
    return found


def require_plan(path: Path, text: str, errors: list[str]) -> None:
    if not has_heading(text, "Error-handling strategy", 2):
        errors.append(f"{rel(path)}: missing Error-handling strategy")
        return
    for heading in (
        "Actions covered",
        "Error contract changes",
        "Error catalog changes",
        "Frontend normalization changes",
        "Presentation components",
        "Input preservation",
        "Retry and recovery",
        "Logging and correlation",
        "Negative-test strategy",
        "Visual error-state verification",
        "Removed or superseded error behavior",
    ):
        if not has_heading(text, heading, 3):
            errors.append(f"{rel(path)}: missing error strategy heading {heading}")


def require_task(path: Path, text: str, errors: list[str]) -> None:
    if not has_heading(text, "Error and recovery implementation", 2):
        errors.append(f"{rel(path)}: missing Error and recovery implementation")
        return
    for heading in (
        "User actions covered",
        "Expected failures",
        "Unknown failure behavior",
        "Required negative tests",
    ):
        if not has_heading(text, heading, 3):
            errors.append(f"{rel(path)}: missing error task heading {heading}")
    unknown = section_for_subheading(text, "Unknown failure behavior")
    if unknown is not None:
        for field in (
            "User-facing fallback",
            "Correlation ID",
            "Retry behavior",
            "Input preservation",
            "Support behavior",
        ):
            value = extract_field(unknown, field)
            if not value or value in {"-", "TBD", "TODO"}:
                errors.append(f"{rel(path)}: incomplete unknown failure field {field}")
    tests = section_for_subheading(text, "Required negative tests")
    if tests is None:
        return
    classified = re.findall(r"^-\s+\[[ xX]\]\s+(.+)$", tests, re.MULTILINE)
    if not classified:
        errors.append(f"{rel(path)}: required negative-test list is empty")
        return
    unchecked = re.findall(r"^-\s+\[ \]\s+(.+)$", tests, re.MULTILINE)
    for item in unchecked:
        if "not-applicable" not in item.lower():
            errors.append(f"{rel(path)}: negative test is unclassified: {item}")


def section_for_subheading(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^###[ \t]+{re.escape(heading)}[ \t]*$\n(.*?)(?=^###[ \t]+|^##[ \t]+|\Z)",
        text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1) if match else None


def declared_specs(current_text: str) -> list[Path]:
    value = extract_field(current_text, "Specifications") or ""
    if not value or value.lower() == "not-required":
        return []
    result: list[Path] = []
    for item in value.split(","):
        candidate = item.strip().strip("`")
        if candidate:
            result.append(ROOT / candidate)
    return result


def source_files_below(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return [
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file()
        and candidate.suffix.lower() in SOURCE_SUFFIXES
        and not any(part in IGNORED_PARTS for part in candidate.parts)
    ]


def is_test_file(path: Path) -> bool:
    lower = path.name.lower()
    return (
        "test" in lower
        or "spec" in lower
        or "__tests__" in {part.lower() for part in path.parts}
    )


def scan_source_patterns(
    config: dict, frontend_enabled: bool, errors: list[str]
) -> None:
    roots: list[Path] = []
    python_root = get(config, "stacks", "python", "directory", default="backend")
    roots.append(ROOT / str(python_root))
    dotnet_solution = str(
        get(config, "stacks", "dotnet", "solution", default="")
    ).strip()
    if dotnet_solution:
        roots.append((ROOT / dotnet_solution).parent)
    frontend_root = ROOT / resolve_frontend_source_root(config)
    if frontend_enabled:
        roots.append(frontend_root)

    frontend_normalizers: list[Path] = []
    backend_mappers: list[Path] = []
    for root in roots:
        for path in source_files_below(root):
            if is_test_file(path):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}", text, re.DOTALL):
                errors.append(f"{rel(path)}: empty catch block")
            if re.search(
                r"except(?:\s+[^\n:]+)?\s*:\s*(?:pass|continue)\b",
                text,
                re.MULTILINE,
            ):
                errors.append(f"{rel(path)}: exception is swallowed")
            if re.search(
                r"catch\b[\s\S]{0,500}\}\s*(?:;|\n|\r)*\s*"
                r"(?:showSuccess|setSuccess|toast\.success)\s*\(",
                text,
            ):
                errors.append(f"{rel(path)}: success feedback may follow failure")
            if re.search(
                r"catch\b[\s\S]{0,300}(?:reset|clearForm)\s*\(",
                text,
            ):
                errors.append(
                    f"{rel(path)}: failed action may clear user input without a "
                    "declared preservation decision"
                )
            if frontend_enabled and re.search(
                r"(?:setError|toast(?:\.error)?|textContent)\s*\(\s*"
                r"(?:error|err|exception)\.(?:message|stack)",
                text,
                re.IGNORECASE,
            ):
                errors.append(f"{rel(path)}: raw exception detail is displayed")
            if frontend_enabled and re.search(
                r"(?:function|const|let|var|class)\s+normalizeApiError\b",
                text,
            ):
                frontend_normalizers.append(path)
            if path.is_relative_to(frontend_root):
                continue
            if re.search(
                r"(?:class\s+\w*(?:ErrorMapper|ProblemDetailsMapper)\b|"
                r"def\s+(?:map_error|to_problem_details)\b)",
                text,
            ):
                backend_mappers.append(path)
    if len(frontend_normalizers) > 1:
        locations = ", ".join(rel(path) for path in frontend_normalizers)
        errors.append(f"multiple normalizeApiError owners found: {locations}")
    if len(backend_mappers) > 1:
        locations = ", ".join(rel(path) for path in backend_mappers)
        errors.append(f"multiple backend error mapper owners found: {locations}")


def files_contain_code(paths: list[Path], code: str) -> bool:
    for path in paths:
        if code in path.read_text(encoding="utf-8", errors="replace"):
            return True
    return False


def verify_catalog_sources(
    config: dict,
    entries: dict[str, CatalogEntry],
    frontend_enabled: bool,
    errors: list[str],
) -> None:
    backend_files: list[Path] = []
    if get(config, "stacks", "python", "enabled", default=False):
        backend_files.extend(
            source_files_below(
                ROOT
                / str(
                    get(
                        config,
                        "stacks",
                        "python",
                        "directory",
                        default="backend",
                    )
                )
            )
        )
    if get(config, "stacks", "dotnet", "enabled", default=False):
        solution = str(get(config, "stacks", "dotnet", "solution", default="")).strip()
        if solution:
            backend_files.extend(source_files_below((ROOT / solution).parent))
    frontend_files = (
        source_files_below(ROOT / resolve_frontend_source_root(config))
        if frontend_enabled
        else []
    )
    contract_files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yaml", ".yml", ".json"}
        and any(token in path.name.lower() for token in ("openapi", "contract", "api"))
        and not any(part in IGNORED_PARTS or part == ".ai" for part in path.parts)
    ]
    contract_required = False
    for code, entry in entries.items():
        if entry.fields.get("Status") != "active":
            continue
        backend_source = entry.fields.get("Backend source", "not-applicable").lower()
        api_contract = entry.fields.get("API contract", "not-applicable").lower()
        frontend_mapping = entry.fields.get(
            "Frontend mapping", "not-applicable"
        ).lower()
        if "not-applicable" not in backend_source:
            if not backend_files or not files_contain_code(backend_files, code):
                errors.append(f"catalog code {code} is missing from backend sources")
        if "not-applicable" not in api_contract:
            contract_required = True
            if not contract_files or not files_contain_code(contract_files, code):
                errors.append(f"catalog code {code} is missing from API contract")
        if frontend_enabled and "not-applicable" not in frontend_mapping:
            if not frontend_files or not files_contain_code(frontend_files, code):
                errors.append(f"catalog code {code} is missing from frontend mapping")
    if contract_required and contract_files:
        contract_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in contract_files
        )
        for field in (
            "type",
            "title",
            "status",
            "detail",
            "code",
            "correlationId",
            "retryable",
            "suggestedAction",
            "fieldErrors",
        ):
            if field not in contract_text:
                errors.append(f"Problem Details API contract is missing field {field}")
    if frontend_enabled:
        normalizers = [
            path
            for path in frontend_files
            if re.search(
                r"(?:function|const|let|var|class)\s+normalizeApiError\b",
                path.read_text(encoding="utf-8", errors="replace"),
            )
        ]
        if not normalizers:
            errors.append("frontend error handling has no central normalizeApiError")
        elif not any(
            "UNEXPECTED_ERROR" in path.read_text(encoding="utf-8", errors="replace")
            for path in frontend_files
        ):
            errors.append("frontend error handling has no safe unknown-code fallback")


def verify_removed_codes(
    change_text: str, catalog: Path | None, errors: list[str]
) -> None:
    value = extract_field(change_text, "Removed error codes") or ""
    removed = {
        token
        for token in CODE_TOKEN.findall(value)
        if token not in {"NONE", "NOT_APPLICABLE"}
    }
    if not removed:
        return
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        if ".ai" in path.parts and "work" in path.parts:
            continue
        if catalog is not None and path.resolve() == catalog.resolve():
            continue
        if path.suffix.lower() not in SOURCE_SUFFIXES | {
            ".yaml",
            ".yml",
            ".json",
            ".md",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for code in sorted(removed):
            if re.search(rf"\b{re.escape(code)}\b", text):
                errors.append(f"removed error code {code} remains in {rel(path)}")


def validate_design_errors(
    work_dir: Path,
    change_text: str,
    phase: str,
    require_visual: bool,
    errors: list[str],
) -> None:
    design_class = extract_field(change_text, "Class")
    if design_class not in {"2", "3"}:
        return
    delta = work_dir / "DESIGN_DELTA.md"
    if not delta.is_file():
        errors.append(f"{rel(delta)}: required for design class {design_class}")
        return
    text = delta.read_text(encoding="utf-8")
    experience = section(text, "Error experience")
    if experience is None:
        errors.append(f"{rel(delta)}: missing Error experience")
        return
    inventory = section_for_subheading(text, "Action and failure inventory")
    if inventory is None or not table_rows(inventory):
        errors.append(f"{rel(delta)}: error action inventory has no data rows")
    if phase in EVIDENCE_PHASES and require_visual:
        tasks = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((work_dir / "tasks").glob("*.md"))
        )
        required_states = "\n".join(
            match.group(1).strip()
            for match in re.finditer(
                rf"^-[ \t]*{re.escape(VISUAL_EVIDENCE_FIELDS[1])}:"
                r"[ \t]*(.*?)[ \t]*$",
                tasks,
                re.MULTILINE | re.IGNORECASE,
            )
        ).lower()
        if "error" not in required_states and "failure" not in required_states:
            errors.append(
                "UI error verification requires an error/failure state in task "
                "visual evidence"
            )


def main() -> int:
    if not CONFIG.is_file():
        print("FAIL: .ai/project.yaml is missing")
        return 1
    config = load_yaml_subset(CONFIG)
    if get(config, "user_facing_errors", "enabled", default=False) is not True:
        print("PASS: user-facing error handling is disabled.")
        return 0

    errors: list[str] = []
    catalog_value = str(
        get(
            config,
            "user_facing_errors",
            "catalog",
            "path",
            default="docs/errors/ERROR_CATALOG.md",
        )
    )
    catalog = resolve_below_root(catalog_value, "error catalog path", errors)
    entries: dict[str, CatalogEntry] = {}
    if catalog is None or not catalog.is_file():
        errors.append(f"configured error catalog is missing: {catalog_value}")
    else:
        entries = parse_catalog(catalog.read_text(encoding="utf-8"), errors)

    frontend_enabled = (
        get(
            config,
            "user_facing_errors",
            "frontend",
            "enabled",
            default=False,
        )
        is True
    )
    if (
        get(
            config,
            "user_facing_errors",
            "validation",
            "scan_source_patterns",
            default=True,
        )
        is True
    ):
        scan_source_patterns(config, frontend_enabled, errors)

    if not CURRENT.is_file():
        errors.append(".ai/CURRENT_PLAN.md is missing")
    else:
        current_text = CURRENT.read_text(encoding="utf-8")
        if not is_inactive_plan(current_text):
            phase = (extract_field(current_text, "Status") or "").lower()
            error_routing = (
                extract_field(current_text, "Error handling") or ""
            ).strip()
            applies = error_routing == "required"
            not_applicable = error_routing.startswith("not-applicable:") and bool(
                error_routing.partition(":")[2].strip()
            )
            if phase in BLOCKING_PHASES and not applies and not not_applicable:
                errors.append(
                    "CURRENT_PLAN.md must declare 'Error handling: required' or "
                    "'Error handling: not-applicable: <reason>'."
                )
            work_value = extract_field(current_text, "Work directory")
            work_dir = (
                resolve_below_root(work_value, "work directory", errors)
                if work_value
                else None
            )
            if work_dir is None or not work_dir.is_dir():
                errors.append("active user-facing error work directory is missing")
            else:
                task_files = sorted((work_dir / "tasks").glob("*.md"))
                ready_tasks = [
                    path
                    for path in task_files
                    if extract_field(path.read_text(encoding="utf-8"), "Status")
                    in READY_TASK_STATUSES
                ]
                enforce = applies and (phase in BLOCKING_PHASES or bool(ready_tasks))
                work_type = extract_field(current_text, "Work type")
                change_value = extract_field(current_text, "Change request")
                change = (
                    resolve_below_root(change_value, "change request", errors)
                    if change_value
                    else None
                )
                change_text = (
                    change.read_text(encoding="utf-8")
                    if change is not None and change.is_file()
                    else ""
                )
                requirement_value = extract_field(current_text, "Requirement")
                requirement = (
                    resolve_below_root(requirement_value, "requirement", errors)
                    if requirement_value
                    else None
                )
                requirement_text = (
                    requirement.read_text(encoding="utf-8")
                    if requirement is not None and requirement.is_file()
                    else ""
                )
                if enforce:
                    matrix_path = (
                        change if work_type == "incremental-change" else requirement
                    )
                    matrix_text = (
                        change_text
                        if work_type == "incremental-change"
                        else requirement_text
                    )
                    if not matrix_text:
                        artifact = (
                            "change request"
                            if work_type == "incremental-change"
                            else "requirement"
                        )
                        errors.append(f"active user-facing {artifact} is missing")
                    elif matrix_path is not None:
                        require_matrix(
                            matrix_path,
                            matrix_text,
                            errors,
                            catalog_codes=set(entries),
                            block_generic=get(
                                config,
                                "user_facing_errors",
                                "validation",
                                "block_generic_message_for_known_error",
                                default=True,
                            )
                            is True,
                        )
                    plan_value = extract_field(current_text, "Plan")
                    plan = (
                        resolve_below_root(plan_value, "implementation plan", errors)
                        if plan_value
                        else None
                    )
                    if plan is None or not plan.is_file():
                        errors.append(
                            "active user-facing implementation plan is missing"
                        )
                    else:
                        plan_text = plan.read_text(encoding="utf-8")
                        require_plan(plan, plan_text, errors)
                    for task in ready_tasks:
                        require_task(task, task.read_text(encoding="utf-8"), errors)
                    if ready_tasks and "UNEXPECTED_ERROR" not in entries:
                        errors.append(
                            "ready user-facing work requires an active "
                            "UNEXPECTED_ERROR catalog entry"
                        )
                    for spec in declared_specs(current_text):
                        if not spec.is_file():
                            continue
                        spec_text = spec.read_text(encoding="utf-8")
                        if not has_heading(spec_text, "Error and recovery behavior", 2):
                            errors.append(
                                f"{rel(spec)}: missing Error and recovery behavior"
                            )
                    validate_design_errors(
                        work_dir,
                        change_text
                        if work_type == "incremental-change"
                        else plan_text
                        if plan is not None and plan.is_file()
                        else "",
                        phase,
                        get(
                            config,
                            "user_facing_errors",
                            "review",
                            "require_visual_evidence_for_ui_errors",
                            default=True,
                        )
                        is True,
                        errors,
                    )
                if applies and phase in EVIDENCE_PHASES:
                    verify_catalog_sources(config, entries, frontend_enabled, errors)
                    if work_type == "incremental-change":
                        verify_removed_codes(change_text, catalog, errors)
                    if (
                        get(
                            config,
                            "user_facing_errors",
                            "api_contract",
                            "require_correlation_id_for_unexpected",
                            default=True,
                        )
                        is True
                        and "UNEXPECTED_ERROR" in entries
                    ):
                        correlation = entries["UNEXPECTED_ERROR"].fields.get(
                            "Correlation reference", ""
                        )
                        if correlation.lower() in {
                            "",
                            "none",
                            "not-applicable",
                        }:
                            errors.append(
                                "UNEXPECTED_ERROR requires a safe correlation reference"
                            )

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(
        "PASS: user-facing error artifacts and configured static checks are valid "
        f"({len(entries)} catalog entries)."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        print(
            "FAIL: user-facing error validation encountered an unexpected error. "
            "Reference: error-gate"
        )
        raise SystemExit(1) from None
