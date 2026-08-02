#!/usr/bin/env python3
"""Validate active UI-quality artifacts without running a browser."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    VISUAL_EVIDENCE_FIELDS,
    extract_field,
    get,
    is_inactive_plan,
    load_yaml_subset,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".ai/project.yaml"
CURRENT = ROOT / ".ai/CURRENT_PLAN.md"
WORK_ROOT = (ROOT / ".ai/work").resolve()
DESIGN_CLASSES = {"0", "1", "2", "3"}
DESIGN_STATUSES = {
    "draft",
    "ready-for-design-review",
    "changes-requested",
    "approved",
    "superseded",
}
ARTIFACT_TYPES = {
    "static-mockup",
    "clickable-html-prototype",
    "react-mock-prototype",
    "storybook-composition",
    "external-design-reference",
}
IMPLEMENTATION_PHASES = {
    "implementation",
    "verification",
    "review",
    "visual-review",
    "remediation",
    "closeout",
}
EVIDENCE_PHASES = {"verification", "review", "visual-review", "remediation", "closeout"}
DESIGN_SYSTEM_IMPACT_FIELDS = (
    "docs/design/DESIGN_SYSTEM.md impact",
    "docs/design/COMPONENT_CATALOG.md impact",
    "Tokens",
    "Accessibility",
    "Responsive behavior",
    "Existing-screen/component migration",
    "Project-wide visual-regression impact",
)
UI_TEMPLATE_FIELD_CONTRACTS = {
    "CHANGE_REQUEST_UI.md": (
        "Class",
        "Highest design class assigned",
        "Implementation-start design class",
        *VISUAL_EVIDENCE_FIELDS,
        "DESIGN_DELTA.md required",
    ),
    "IMPLEMENTATION_PLAN_UI.md": (
        "Design class",
        "Highest design class assigned",
        "Implementation-start design class",
        *VISUAL_EVIDENCE_FIELDS,
    ),
    "WORK_ITEM_UI.md": ("Design class", *VISUAL_EVIDENCE_FIELDS),
    "CHANGE_IMPACT_UI.md": (),
    "REVIEW_REPORT_UI.md": (),
    "DESIGN_DELTA.md": (
        "Design class",
        "Highest design class assigned",
        "Implementation-start design class",
        "Affected capability specifications",
        "Prototype strategy",
        "Prototype artifact type",
        "Prototype artifact or revision",
        "Change base revision",
        *DESIGN_SYSTEM_IMPACT_FIELDS,
    ),
}
VISUAL_RESULT_PHASES = {"visual-review", "closeout"}
SOURCE_SUFFIXES = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
    ".svelte",
    ".html",
    ".css",
    ".scss",
    ".json",
}
STATE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def resolve_below(
    value: str | None, boundary: Path, label: str, errors: list[str]
) -> Path | None:
    if not value:
        errors.append(f"missing {label}")
        return None
    candidate = (ROOT / value.rstrip("/")).resolve()
    try:
        candidate.relative_to(boundary.resolve())
    except ValueError:
        errors.append(f"{label} must stay below {rel(boundary)}/")
        return None
    return candidate


def configured_work_path(
    config: dict,
    work_dir: Path,
    keys: tuple[str, ...],
    default: str,
    label: str,
    errors: list[str],
) -> Path:
    configured = str(get(config, "ui_quality", *keys, default=default))
    value = configured.replace("{change_id}", work_dir.name)
    path = (ROOT / value).resolve()
    try:
        path.relative_to(work_dir.resolve())
    except ValueError:
        errors.append(
            f"configured {label} must resolve below the active work directory"
        )
    return path


def has_heading(text: str, heading: str) -> bool:
    return bool(
        re.search(
            rf"^##+\s+{re.escape(heading)}\s*$",
            text,
            re.MULTILINE | re.IGNORECASE,
        )
    )


def section_text(text: str, heading: str) -> str:
    match = re.search(
        rf"^(?P<marks>##+)\s+{re.escape(heading)}\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        return ""
    start = match.end()
    level = len(match.group("marks"))
    end = len(text)
    for candidate in re.finditer(r"^(?P<marks>##+)\s+", text[start:], re.MULTILINE):
        if len(candidate.group("marks")) <= level:
            end = start + candidate.start()
            break
    return text[start:end]


def table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(cells)
    return rows[1:] if rows else []


def git_output(*args: str) -> str | None:
    git_path = shutil.which("git")
    if not git_path:
        return None
    try:
        result = subprocess.run(  # nosec B603
            [git_path, *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def current_revision() -> str:
    return git_output("rev-parse", "HEAD") or "not-a-git-worktree"


def working_tree_fingerprint(evidence_dir: Path) -> str:
    changed = git_output("diff", "--name-only", "--no-renames", "HEAD", "--")
    untracked = git_output("ls-files", "--others", "--exclude-standard")
    if changed is None or untracked is None:
        return "not-a-git-worktree"
    paths = sorted(set(changed.splitlines()) | set(untracked.splitlines()))
    digest = hashlib.sha256()
    active_work_dir = evidence_dir.resolve().parent.parent
    for value in paths:
        if not value:
            continue
        path = (ROOT / value).resolve()
        try:
            path.relative_to(active_work_dir)
            continue
        except ValueError:
            pass
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            file_digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    file_digest.update(chunk)
            digest.update(file_digest.digest())
        else:
            digest.update(b"<deleted>")
        digest.update(b"\0")
    return digest.hexdigest()


def parse_json(path: Path, label: str, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"missing {label}: {rel(path)}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid {label} {rel(path)}: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must be a JSON object: {rel(path)}")
        return None
    return value


def validate_tasks(
    config: dict, work_dir: Path, design_class: str, errors: list[str]
) -> None:
    if design_class == "0":
        return
    tasks = sorted(work_dir.glob("tasks/*.md"))
    if not tasks:
        errors.append("UI work requires at least one task")
    headings = (
        "Component impact",
        "Existing components reused",
        "Existing components extended",
        "New shared components",
        "New feature-local components",
        "Components replaced or removed",
        "Rejected reuse options",
        "Rationale",
        "Visual evidence",
    )
    for task in tasks:
        text = task.read_text(encoding="utf-8")
        task_class = extract_field(text, "Design class")
        if task_class not in DESIGN_CLASSES:
            errors.append(f"{rel(task)}: invalid or missing Design class")
        elif int(task_class) < int(design_class):
            errors.append(f"{rel(task)}: task Design class understates parent class")
        for heading in headings:
            if not has_heading(text, heading):
                errors.append(f"{rel(task)}: missing '{heading}' section")
        shared_rows = table_rows(section_text(text, "New shared components"))
        for row in shared_rows:
            if not row or row[0].lower() == "none":
                continue
            if len(row) < 7 or any(
                not value or value.lower() in {"none", "not-applicable"}
                for value in row[:7]
            ):
                errors.append(
                    f"{rel(task)}: new shared components require complete "
                    "path/API/test/accessibility/story/catalog evidence"
                )
                continue
            catalog = ROOT / str(
                get(
                    config,
                    "ui_quality",
                    "design_system",
                    "component_catalog",
                    default="docs/design/COMPONENT_CATALOG.md",
                )
            )
            if not catalog.is_file() or row[0] not in catalog.read_text(
                encoding="utf-8"
            ):
                errors.append(
                    f"{rel(task)}: new shared component {row[0]!r} is missing "
                    "from the Component Catalog"
                )


def validate_design_delta(
    work_dir: Path,
    design_class: str,
    phase: str,
    config: dict,
    errors: list[str],
) -> None:
    if design_class not in {"2", "3"}:
        return
    path = work_dir / "DESIGN_DELTA.md"
    if not path.is_file():
        errors.append(f"design class {design_class} requires {rel(path)}")
        return
    text = path.read_text(encoding="utf-8")
    status = extract_field(text, "Status")
    if status not in DESIGN_STATUSES:
        errors.append(f"{rel(path)}: invalid or missing design Status")
    if phase == "design-review" and status not in {
        "ready-for-design-review",
        "changes-requested",
        "approved",
    }:
        errors.append(f"{rel(path)} must be ready for design review")
    if phase in IMPLEMENTATION_PHASES and status != "approved":
        errors.append(f"{rel(path)} must have Status: approved before {phase}")
    if status in {"ready-for-design-review", "approved"}:
        required_sections = (
            "Problem and user outcome",
            "Current experience",
            "Desired experience",
            "User flow",
            "Screen inventory",
            "State inventory",
            "Responsive behavior",
            "Component impact",
            "Design-system impact",
            "Accessibility requirements",
            "Prototype or mockup plan",
            "Prototype isolation",
            "Mockup or prototype evidence",
            "Prototype promotion decisions",
            "Open design decisions",
            "Approval",
        )
        for section in required_sections:
            content = section_text(text, section).strip()
            if not content:
                errors.append(f"{rel(path)} is incomplete for design review: {section}")
        for section in ("Screen inventory", "Prototype promotion decisions"):
            if not table_rows(section_text(text, section)):
                errors.append(
                    f"{rel(path)} is incomplete for design review: "
                    f"{section} requires at least one decision row"
                )
    delta_class = extract_field(text, "Design class")
    highest = extract_field(text, "Highest design class assigned")
    start = extract_field(text, "Implementation-start design class")
    if delta_class != design_class:
        errors.append(f"{rel(path)} Design class must match the parent")
    if highest not in {"2", "3"} or int(highest) < int(design_class):
        errors.append(f"{rel(path)} has invalid Highest design class assigned")
    if phase in IMPLEMENTATION_PHASES:
        if start not in {"2", "3"} or int(start) > int(design_class):
            errors.append(f"{rel(path)} has invalid implementation-start class")

    artifact_type = extract_field(text, "Prototype artifact type")
    allowed = get(config, "ui_quality", "design_artifacts", "allowed", default=[])
    if artifact_type not in ARTIFACT_TYPES or artifact_type not in allowed:
        errors.append(f"{rel(path)} selects an unsupported prototype artifact type")
    if not extract_field(text, "Affected capability specifications"):
        errors.append(f"{rel(path)} must reference affected capability specifications")
    artifact = extract_field(text, "Prototype artifact or revision")
    if not artifact:
        errors.append(f"{rel(path)} must identify the prototype artifact or revision")
    elif artifact_type == "external-design-reference":
        if not artifact.startswith(("https://", "http://")):
            errors.append(f"{rel(path)} external design reference must be an URL")
    elif artifact_type == "static-mockup":
        storage = configured_work_path(
            config,
            work_dir,
            ("design_artifacts", "storage"),
            ".ai/work/{change_id}",
            "design-artifact storage",
            errors,
        )
        artifact_path = (ROOT / artifact).resolve()
        try:
            artifact_path.relative_to(storage)
        except ValueError:
            errors.append(f"{rel(path)} static mockup must stay in configured storage")
        if phase in IMPLEMENTATION_PHASES and not artifact_path.is_file():
            errors.append(f"{rel(path)} static mockup artifact does not exist")
    if phase in IMPLEMENTATION_PHASES:
        if extract_field(text, "Decision") != "approved":
            errors.append(f"{rel(path)} Approval Decision must be approved")
        approved_artifact = extract_field(text, "Approved artifact or revision")
        if not approved_artifact:
            errors.append(f"{rel(path)} approval must identify an artifact or revision")
        elif artifact and approved_artifact != artifact:
            errors.append(f"{rel(path)} approval must reference the selected artifact")
        approvals = get(config, "ui_quality", "require_human_approval_for", default=[])
        if f"design-class-{design_class}" in approvals:
            if extract_field(text, "Approval type") != "human":
                errors.append(f"{rel(path)} requires human design approval")
        if not extract_field(text, "Approved by") or not extract_field(text, "Date"):
            errors.append(f"{rel(path)} approval identity and date are required")

    if design_class == "3":
        if extract_field(text, "Prototype strategy") != "isolated-prototype":
            errors.append("design class 3 requires an isolated prototype")
        for field in DESIGN_SYSTEM_IMPACT_FIELDS:
            value = extract_field(text, field)
            if not value or value.lower() in {"none", "not-applicable"}:
                errors.append(f"{rel(path)} class 3 requires a concrete {field}")
        if phase in {"verification", "review", "visual-review", "closeout"}:
            base_revision = extract_field(text, "Change base revision")
            if not base_revision or not re.fullmatch(r"[0-9a-fA-F]{40}", base_revision):
                errors.append(
                    f"{rel(path)} class 3 requires a full Git Change base revision"
                )
                changed = None
            else:
                changed = git_output("diff", "--name-only", base_revision, "--")
            untracked = git_output("ls-files", "--others", "--exclude-standard")
            if changed is None or untracked is None:
                errors.append(
                    "class 3 completion cannot verify maintained design-source changes "
                    "outside a Git worktree"
                )
            else:
                changed_paths = set(changed.splitlines()) | set(untracked.splitlines())
                for keys, default in (
                    (
                        ("design_system", "document"),
                        "docs/design/DESIGN_SYSTEM.md",
                    ),
                    (
                        ("design_system", "component_catalog"),
                        "docs/design/COMPONENT_CATALOG.md",
                    ),
                ):
                    configured_path = str(
                        get(config, "ui_quality", *keys, default=default)
                    )
                    if configured_path not in changed_paths:
                        errors.append(
                            "design class 3 completion requires a changed maintained "
                            f"design source: {configured_path}"
                        )


def lockfile_exists(package_dir: Path) -> bool:
    return any(
        (package_dir / name).is_file()
        for name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")
    )


def is_exact_dependency_version(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(
        re.fullmatch(
            r"v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?",
            value.strip(),
        )
    )


def dependency_is_locked(
    package_dir: Path, dependency: str, expected_version: object
) -> bool:
    if not isinstance(expected_version, str):
        return False
    package_lock = package_dir / "package-lock.json"
    if package_lock.is_file():
        try:
            lock = json.loads(package_lock.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        package_key = f"node_modules/{dependency}"
        packages = lock.get("packages", {})
        dependencies = lock.get("dependencies", {})
        if (
            isinstance(packages, dict)
            and isinstance(packages.get(package_key), dict)
            and packages[package_key].get("version") == expected_version
        ):
            return True
        if (
            isinstance(dependencies, dict)
            and isinstance(dependencies.get(dependency), dict)
            and dependencies[dependency].get("version") == expected_version
        ):
            return True
    for name in ("pnpm-lock.yaml", "yarn.lock"):
        path = package_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if dependency in text and expected_version in text:
            return True
    return False


def validate_tooling(
    config: dict,
    work_dir: Path,
    design_class: str,
    phase: str,
    errors: list[str],
) -> None:
    if design_class not in {"2", "3"} or phase not in IMPLEMENTATION_PHASES:
        return
    delta = work_dir / "DESIGN_DELTA.md"
    if not delta.is_file():
        return
    text = delta.read_text(encoding="utf-8")
    artifact_type = extract_field(text, "Prototype artifact type")
    artifact = extract_field(text, "Prototype artifact or revision")
    frontend = ROOT / str(
        get(config, "ui_quality", "frontend", "root", default="frontend")
    )
    if artifact_type == "storybook-composition":
        package = parse_json(frontend / "package.json", "frontend package.json", errors)
        if package is not None:
            dependencies = {
                **package.get("dependencies", {}),
                **package.get("devDependencies", {}),
            }
            scripts = package.get("scripts", {})
            storybook_dependencies = {
                name: value
                for name, value in dependencies.items()
                if "storybook" in name.lower()
            }
            if not storybook_dependencies:
                errors.append(
                    "Storybook composition requires an installed Storybook dependency"
                )
            for name, value in storybook_dependencies.items():
                if not is_exact_dependency_version(value):
                    errors.append(
                        f"Storybook dependency {name!r} must use an exact version"
                    )
                if not dependency_is_locked(frontend, name, value):
                    errors.append(
                        f"Storybook dependency {name!r} is missing from the lockfile"
                    )
            if not any("storybook" in name.lower() for name in scripts):
                errors.append(
                    "Storybook composition requires an executable package script"
                )
            if not lockfile_exists(frontend):
                errors.append("Storybook tooling requires an adjacent lockfile")
        if phase != "closeout":
            source_root = ROOT / str(
                get(
                    config,
                    "ui_quality",
                    "frontend",
                    "source_root",
                    default="frontend/src",
                )
            )
            prototype_stories: list[Path] = []
            for path in source_root.rglob("*"):
                if (
                    not path.is_file()
                    or ".stories." not in path.name
                    or path.stat().st_size > 2 * 1024 * 1024
                ):
                    continue
                if (
                    "prototype-only:"
                    in path.read_text(encoding="utf-8", errors="replace").lower()
                ):
                    prototype_stories.append(path)
            if not prototype_stories:
                errors.append(
                    "Storybook composition requires a prototype-only marked story"
                )
            elif artifact:
                artifact_path = (ROOT / artifact).resolve()
                if artifact_path not in {path.resolve() for path in prototype_stories}:
                    errors.append(
                        "DESIGN_DELTA.md must reference the reviewed "
                        "prototype-only Storybook story"
                    )
    if (
        artifact_type in {"clickable-html-prototype", "react-mock-prototype"}
        and phase != "closeout"
    ):
        prototype = configured_work_path(
            config,
            work_dir,
            ("prototype", "isolated_directory"),
            ".ai/work/{change_id}/prototype",
            "isolated prototype directory",
            errors,
        )
        if not prototype.is_dir():
            errors.append(f"{artifact_type} requires an isolated prototype directory")
        if artifact and (ROOT / artifact).resolve() != prototype:
            errors.append(
                "DESIGN_DELTA.md must reference the configured isolated "
                "prototype directory"
            )


def validate_prototype(
    config: dict, work_dir: Path, design_class: str, phase: str, errors: list[str]
) -> None:
    prototype = configured_work_path(
        config,
        work_dir,
        ("prototype", "isolated_directory"),
        ".ai/work/{change_id}/prototype",
        "isolated prototype directory",
        errors,
    )
    if design_class == "1" and prototype.exists():
        errors.append("design class 1 must not create an isolated prototype")
    if not prototype.exists():
        return
    frontend_root = (
        ROOT / str(get(config, "ui_quality", "frontend", "root", default="frontend"))
    ).resolve()
    source_root = (
        ROOT
        / str(
            get(
                config,
                "ui_quality",
                "frontend",
                "source_root",
                default="frontend/src",
            )
        )
    ).resolve()
    try:
        prototype.resolve().relative_to(source_root)
    except ValueError:
        pass
    else:
        errors.append(
            "isolated prototype must stay outside the production frontend source root"
        )
    readme = prototype / "README.md"
    if (
        not readme.is_file()
        or "not production code" not in readme.read_text(encoding="utf-8").lower()
    ):
        errors.append("isolated prototype requires a non-production README")
    package_path = prototype / "package.json"
    prototype_name = ""
    if package_path.is_file():
        package = parse_json(package_path, "prototype package.json", errors)
        if package is not None:
            prototype_name = str(package.get("name", ""))
            if package.get("private") is not True:
                errors.append("prototype package.json must declare private: true")
            if not prototype_name.endswith("-design-prototype"):
                errors.append("prototype package name must end in -design-prototype")
            dependencies = {
                **package.get("dependencies", {}),
                **package.get("devDependencies", {}),
            }
            for name, value in dependencies.items():
                if not is_exact_dependency_version(value):
                    errors.append(
                        f"prototype dependency {name!r} must use an exact version"
                    )
                if not dependency_is_locked(prototype, name, value):
                    errors.append(
                        f"prototype dependency {name!r} is missing from the lockfile"
                    )
    for path in prototype.rglob("*"):
        if not path.is_file() or any(part in STATE_DIRS for part in path.parts):
            continue
        if path.name == ".env.production":
            errors.append(f"{rel(path)} is forbidden in a prototype")
        if path.suffix.lower() not in SOURCE_SUFFIXES and not path.name.startswith(
            ".env"
        ):
            continue
        if path.stat().st_size > 2 * 1024 * 1024:
            errors.append(f"{rel(path)} is too large for static prototype inspection")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"PRODUCTION_API_URL|VITE_PRODUCTION_API|\.env\.production", text):
            errors.append(f"{rel(path)} references production API configuration")

    package_manifests = {ROOT / "package.json", frontend_root / "package.json"}
    for production_package in sorted(package_manifests):
        if not production_package.is_file():
            continue
        package = parse_json(
            production_package,
            f"production package.json at {rel(production_package)}",
            errors,
        )
        if package is not None:
            all_dependencies = {
                **package.get("dependencies", {}),
                **package.get("devDependencies", {}),
            }
            values = " ".join(str(value) for value in all_dependencies.values())
            if prototype_name and prototype_name in all_dependencies:
                errors.append("production package depends on the prototype package")
            if ".ai/work" in values or "/prototype" in values:
                errors.append("production package contains a prototype dependency")
            workspace_text = json.dumps(package.get("workspaces", {}))
            script_text = json.dumps(package.get("scripts", {}))
            if ".ai/work" in workspace_text:
                errors.append("prototype must not be a production workspace package")
            if ".ai/work" in script_text or "/prototype" in script_text:
                errors.append("production build/scripts must not include a prototype")
    for manifest_name in ("pnpm-workspace.yaml", "turbo.json", "nx.json"):
        manifest = ROOT / manifest_name
        if not manifest.is_file():
            continue
        text = manifest.read_text(encoding="utf-8", errors="replace")
        if ".ai/work" in text or "/prototype" in text:
            errors.append(f"{manifest_name} must not include a temporary prototype")

    if source_root.is_dir():
        for path in source_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(
                r"(?:from\s*|require\s*\(\s*|import\s*(?:\(\s*)?)"
                r"[\"'][^\"']*(?:\.ai/work|/prototype)",
                text,
            ):
                errors.append(f"{rel(path)} imports temporary prototype code")

    if phase == "closeout":
        closeout = work_dir / "CLOSEOUT.md"
        if not closeout.is_file():
            errors.append("prototype closeout requires CLOSEOUT.md")
        else:
            closeout_text = closeout.read_text(encoding="utf-8")
            if "prototype" not in closeout_text.lower():
                errors.append("CLOSEOUT.md does not classify the isolated prototype")


def valid_image_evidence(path: Path) -> bool:
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return False
    if path.stat().st_size <= 0 or path.stat().st_size > 25 * 1024 * 1024:
        return False
    try:
        with path.open("rb") as stream:
            prefix = stream.read(12)
    except OSError:
        return False
    if path.suffix.lower() == ".png":
        return prefix.startswith(b"\x89PNG\r\n\x1a\n")
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return prefix.startswith(b"\xff\xd8\xff")
    return len(prefix) >= 12 and prefix[:4] == b"RIFF" and prefix[8:12] == b"WEBP"


def validate_manifest(
    config: dict, work_dir: Path, phase: str, errors: list[str]
) -> None:
    evidence = work_dir / "evidence/ui"
    manifest_path = evidence / "manifest.json"
    manifest = parse_json(manifest_path, "UI evidence manifest", errors)
    if manifest is None:
        return
    expected_revision = current_revision()
    expected_fingerprint = working_tree_fingerprint(evidence)
    if manifest.get("application_revision") != expected_revision:
        errors.append("UI evidence manifest references a stale application revision")
    if manifest.get("working_tree_fingerprint") != expected_fingerprint:
        errors.append(
            "UI evidence manifest references a stale working-tree fingerprint"
        )
    required = (
        "change_id",
        "generated_at",
        "browser",
        "base_url",
        "execution_mode",
        "performed_by",
        "screens",
    )
    for field in required:
        if not manifest.get(field):
            errors.append(f"UI evidence manifest has missing or empty {field}")
    if manifest.get("change_id") != work_dir.name:
        errors.append("UI evidence manifest change_id does not match active work")
    if manifest.get("execution_mode") not in {"manual", "automated"}:
        errors.append("UI evidence execution_mode must be manual or automated")
    command = str(
        get(config, "ui_quality", "browser_review", "command", default="")
    ).strip()
    configured_base_url = str(
        get(config, "ui_quality", "browser_review", "base_url", default="")
    ).strip()
    if configured_base_url and manifest.get("base_url") != configured_base_url:
        errors.append("UI evidence base_url does not match configured review URL")
    fallback = get(
        config,
        "ui_quality",
        "browser_review",
        "fallback_when_unconfigured",
        default="manual-gate",
    )
    if not command and fallback == "error":
        errors.append(
            "browser review is required but no executable command is configured"
        )
    if not command and manifest.get("execution_mode") != "manual":
        errors.append("unconfigured browser review requires execution_mode: manual")
    accessibility_enabled = get(
        config, "ui_quality", "accessibility", "enabled", default=False
    )
    accessibility_command = str(
        get(config, "ui_quality", "accessibility", "command", default="")
    ).strip()
    if not command:
        if manifest.get("interaction_check") != "passed":
            errors.append("manual browser review requires interaction_check: passed")
        if accessibility_enabled and not manifest.get("accessibility_observations"):
            errors.append("manual browser review requires accessibility_observations")
    else:
        if manifest.get("execution_mode") != "automated":
            errors.append(
                "configured browser review requires execution_mode: automated"
            )
        if manifest.get("browser_command") != command:
            errors.append("UI evidence must identify the configured browser command")
        if manifest.get("command_result") != "pass":
            errors.append("configured browser command must record command_result: pass")
        if (
            accessibility_enabled
            and not accessibility_command
            and not manifest.get("accessibility_observations")
        ):
            errors.append(
                "accessibility is enabled without a command; manifest requires "
                "manual accessibility_observations"
            )
    screens = manifest.get("screens")
    if not isinstance(screens, list) or not screens:
        errors.append("UI evidence manifest requires at least one screen")
        return
    configured = get(config, "ui_quality", "browser_review", "viewports", default={})
    seen_viewports: set[tuple[int, int]] = set()
    for screen in screens:
        if not isinstance(screen, dict):
            errors.append("UI evidence screen entries must be objects")
            continue
        viewport = screen.get("viewport", {})
        width, height = viewport.get("width"), viewport.get("height")
        if not screen.get("id") or not screen.get("state"):
            errors.append("every UI evidence screen needs id and state")
        if not isinstance(width, int) or not isinstance(height, int):
            errors.append("every UI evidence screen needs a numeric viewport")
        else:
            seen_viewports.add((width, height))
        file_value = screen.get("file")
        if not isinstance(file_value, str):
            errors.append("every UI evidence screen must reference an existing file")
        else:
            file_path = (evidence / file_value).resolve()
            try:
                file_path.relative_to(evidence.resolve())
            except ValueError:
                errors.append("UI evidence file path escapes the evidence directory")
            else:
                if not file_path.is_file():
                    errors.append(
                        "every UI evidence screen must reference an existing file"
                    )
                elif not valid_image_evidence(file_path):
                    errors.append(
                        "UI evidence screenshots must be non-empty PNG, JPEG, or WebP images"
                    )
    for viewport in configured.values():
        expected = (viewport.get("width"), viewport.get("height"))
        if expected not in seen_viewports:
            errors.append(f"UI evidence is missing configured viewport {expected}")

    declared_screens: set[str] = set()
    declared_states: set[str] = set()
    declared_viewports: set[str] = set()
    for task in sorted(work_dir.glob("tasks/*.md")):
        text = task.read_text(encoding="utf-8")
        for field, target in zip(
            VISUAL_EVIDENCE_FIELDS,
            (declared_screens, declared_states, declared_viewports),
            strict=True,
        ):
            value = extract_field(text, field) or ""
            target.update(
                item.strip()
                for item in value.split(",")
                if item.strip()
                and item.strip().lower() not in {"none", "not-applicable"}
            )
    present_screens = {
        str(screen.get("id")) for screen in screens if isinstance(screen, dict)
    }
    present_states = {
        str(screen.get("state")) for screen in screens if isinstance(screen, dict)
    }
    size_to_name = {
        (value.get("width"), value.get("height")): name
        for name, value in configured.items()
    }
    present_viewports = {size_to_name.get(size, "") for size in seen_viewports}
    for missing, label in (
        (declared_screens - present_screens, "screen"),
        (declared_states - present_states, "state"),
        (declared_viewports - present_viewports, "viewport"),
    ):
        if missing:
            errors.append(
                f"UI evidence is missing required {label}(s): {', '.join(sorted(missing))}"
            )

    if phase in VISUAL_RESULT_PHASES:
        report_path = evidence / "reports/visual-review.json"
        report = parse_json(report_path, "visual-review report", errors)
        if report is None:
            return
        if report.get("verdict") != "approved":
            errors.append("required visual review must have verdict: approved")
        if report.get("application_revision") != expected_revision:
            errors.append("visual-review report references a stale revision")
        if report.get("working_tree_fingerprint") != expected_fingerprint:
            errors.append("visual-review report references a stale fingerprint")
        if not report.get("reviewer") or not report.get("reviewed_at"):
            errors.append("visual-review report requires reviewer and reviewed_at")
        findings = report.get("findings")
        if not isinstance(findings, list):
            errors.append("visual-review findings must be a list")
        else:
            if report.get("verdict") == "approved" and findings:
                errors.append("approved visual review must not retain open findings")
            for finding in findings:
                if not isinstance(finding, dict):
                    errors.append("visual-review findings must be objects")
                    continue
                required_finding_fields = (
                    "id",
                    "severity",
                    "screen",
                    "state",
                    "viewport",
                    "evidence",
                    "problem",
                    "expected",
                    "required_change",
                )
                for field in required_finding_fields:
                    if not finding.get(field):
                        errors.append(
                            f"visual-review finding requires non-empty {field}"
                        )
                if finding.get("severity") not in {"P0", "P1", "P2", "P3"}:
                    errors.append(
                        "visual-review finding severity must be P0, P1, P2, or P3"
                    )
                evidence_value = finding.get("evidence")
                if not isinstance(evidence_value, str):
                    errors.append("visual-review finding requires evidence")
                    continue
                evidence_path = (work_dir / evidence_value).resolve()
                try:
                    evidence_path.relative_to(evidence.resolve())
                except ValueError:
                    errors.append("visual-review finding evidence escapes UI evidence")
                else:
                    if not evidence_path.is_file():
                        errors.append(
                            "visual-review finding evidence file does not exist"
                        )


def validate_story_markers(
    config: dict, work_dir: Path, phase: str, errors: list[str]
) -> None:
    source_root = ROOT / str(
        get(
            config,
            "ui_quality",
            "frontend",
            "source_root",
            default="frontend/src",
        )
    )
    if not source_root.is_dir():
        return
    marker = re.compile(r"prototype-only:\s*([A-Za-z0-9._-]+)", re.IGNORECASE)
    found: list[Path] = []
    for path in source_root.rglob("*"):
        if path.is_file() and ".stories." in path.name:
            if path.stat().st_size > 2 * 1024 * 1024:
                errors.append(
                    f"{rel(path)} is too large for prototype-marker inspection"
                )
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if marker.search(text):
                found.append(path)
    if phase == "closeout" and found:
        for path in found:
            errors.append(f"{rel(path)} retains an unclassified prototype-only marker")
    elif found and not (work_dir / "DESIGN_DELTA.md").is_file():
        errors.append("prototype-only stories require DESIGN_DELTA.md")


def validate_review_transition(
    work_dir: Path, design_class: str, phase: str, errors: list[str]
) -> None:
    if design_class == "0":
        return
    reviewed_tasks: list[Path] = []
    for task in sorted(work_dir.glob("tasks/*.md")):
        status = extract_field(task.read_text(encoding="utf-8"), "Status")
        if status in {"reviewed", "done"}:
            reviewed_tasks.append(task)
    if not reviewed_tasks:
        return
    report_path = work_dir / "evidence/ui/reports/visual-review.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        report = {}
    if not isinstance(report, dict) or report.get("verdict") != "approved":
        for task in reviewed_tasks:
            errors.append(
                f"{rel(task)} cannot be {extract_field(task.read_text(encoding='utf-8'), 'Status')} "
                "before approved visual review"
            )
    if phase == "review" and reviewed_tasks:
        errors.append(
            "code-review phase cannot advance UI tasks to reviewed before the "
            "visual-review phase"
        )


def validate_closeout(config: dict, work_dir: Path, errors: list[str]) -> None:
    path = work_dir / "CLOSEOUT.md"
    if not path.is_file():
        errors.append("UI closeout requires CLOSEOUT.md")
        return
    text = path.read_text(encoding="utf-8")
    if extract_field(text, "Ready to remove temporary work") != "yes":
        errors.append(f"{rel(path)} is not ready to remove temporary work")
    if extract_field(text, "Code-review status") != "approved":
        errors.append(f"{rel(path)} requires approved code review")
    if extract_field(text, "Visual review required") == "yes":
        if extract_field(text, "Visual-review status") != "approved":
            errors.append(f"{rel(path)} requires approved visual review")
    allowed = {
        "promoted",
        "reimplemented",
        "discarded",
        "retained-as-maintained-story",
        "retained-as-permanent-design-reference",
    }
    in_table = False
    decisions = 0
    for line in text.splitlines():
        if line.strip().lower() == "## prototype-element decisions":
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in {
            "element or artifact",
            "---",
        }:
            continue
        if set(cells[0]) == {"-"}:
            continue
        decisions += 1
        if cells[1] not in allowed:
            errors.append(f"{rel(path)} has invalid prototype disposition {cells[1]!r}")
        if cells[1] == "retained-as-permanent-design-reference":
            if (
                len(cells) < 5
                or not cells[2]
                or cells[2].lower() in {"none", "not-applicable"}
                or not cells[3]
                or cells[3].lower() in {"none", "not-applicable"}
                or not cells[4]
                or cells[4].lower() in {"none", "not-applicable"}
            ):
                errors.append(
                    f"{rel(path)} retained design references require permanent "
                    "location, owner, purpose, and isolation evidence"
                )
            else:
                permanent_path = (ROOT / cells[2]).resolve()
                try:
                    permanent_path.relative_to(ROOT.resolve())
                except ValueError:
                    errors.append(
                        f"{rel(path)} retained permanent design reference must stay "
                        "inside the repository"
                    )
                else:
                    try:
                        permanent_path.relative_to(work_dir.resolve())
                    except ValueError:
                        if not permanent_path.exists():
                            errors.append(
                                f"{rel(path)} retained permanent design reference "
                                "location does not exist"
                            )
                    else:
                        errors.append(
                            f"{rel(path)} retained permanent design reference must "
                            "move outside the temporary work directory"
                        )
    if decisions == 0:
        errors.append(f"{rel(path)} must classify prototype use, including none")
    prototype = configured_work_path(
        config,
        work_dir,
        ("prototype", "isolated_directory"),
        ".ai/work/{change_id}/prototype",
        "isolated prototype directory",
        errors,
    )
    if prototype.exists():
        errors.append(
            "temporary isolated prototype must be removed or moved to its documented "
            "permanent location before closeout"
        )
    if not prototype.exists() and extract_field(text, "Removed") == "no":
        errors.append(f"{rel(path)} prototype cleanup state contradicts the filesystem")


def browser_gate_mode() -> str:
    if not CONFIG.is_file() or not CURRENT.is_file():
        return "error"
    config = load_yaml_subset(CONFIG)
    if get(config, "ui_quality", "enabled", default=False) is not True:
        return "not-required"
    current_text = CURRENT.read_text(encoding="utf-8")
    if is_inactive_plan(current_text):
        return "not-required"
    phase = extract_field(current_text, "Status") or ""
    if phase not in EVIDENCE_PHASES:
        return "not-required"
    work_value = extract_field(current_text, "Work directory")
    if not work_value:
        return "error"
    work_type = extract_field(current_text, "Work type")
    parent_value = (
        extract_field(current_text, "Change request")
        if work_type == "incremental-change"
        else extract_field(current_text, "Plan")
    )
    if not parent_value:
        return "error"
    parent = (ROOT / parent_value).resolve()
    if not parent.is_file():
        return "error"
    parent_text = parent.read_text(encoding="utf-8")
    design_class = extract_field(parent_text, "Design class") or extract_field(
        parent_text, "Class"
    )
    if design_class == "0":
        return "not-required"
    if design_class not in DESIGN_CLASSES:
        return "error"
    command = str(
        get(config, "ui_quality", "browser_review", "command", default="")
    ).strip()
    if command:
        return "automated"
    fallback = get(
        config,
        "ui_quality",
        "browser_review",
        "fallback_when_unconfigured",
        default="manual-gate",
    )
    return "manual" if fallback == "manual-gate" else "error"


def main() -> int:
    if "--browser-gate-mode" in sys.argv:
        print(browser_gate_mode())
        return 0
    if "--fingerprint" in sys.argv:
        if not CURRENT.is_file():
            print("FAIL: .ai/CURRENT_PLAN.md is missing", file=sys.stderr)
            return 1
        current_text = CURRENT.read_text(encoding="utf-8")
        work_value = extract_field(current_text, "Work directory")
        if not work_value:
            print("FAIL: active work directory is not declared", file=sys.stderr)
            return 1
        evidence = ROOT / work_value.rstrip("/") / "evidence/ui"
        print(working_tree_fingerprint(evidence))
        return 0
    if not CURRENT.is_file() or not CONFIG.is_file():
        print("FAIL: UI quality requires .ai/CURRENT_PLAN.md and .ai/project.yaml")
        return 1
    config = load_yaml_subset(CONFIG)
    if get(config, "ui_quality", "enabled", default=False) is not True:
        print("PASS: UI quality is disabled.")
        return 0
    current_text = CURRENT.read_text(encoding="utf-8")
    if is_inactive_plan(current_text):
        print("PASS: no active UI work declared.")
        return 0
    errors: list[str] = []
    work_dir = resolve_below(
        extract_field(current_text, "Work directory"),
        WORK_ROOT,
        "active work directory",
        errors,
    )
    if work_dir is None or not work_dir.is_dir():
        if work_dir is not None:
            errors.append(f"active work directory does not exist: {rel(work_dir)}")
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    phase = extract_field(current_text, "Status") or ""
    work_type = extract_field(current_text, "Work type")
    parent_path: Path | None
    if work_type == "incremental-change":
        parent_path = resolve_below(
            extract_field(current_text, "Change request"),
            work_dir,
            "change request",
            errors,
        )
    else:
        parent_path = resolve_below(
            extract_field(current_text, "Plan"),
            work_dir,
            "implementation plan",
            errors,
        )
    design_class = ""
    parent_status = ""
    if parent_path is not None and parent_path.is_file():
        parent_text = parent_path.read_text(encoding="utf-8")
        parent_status = extract_field(parent_text, "Status") or ""
        design_class = (
            extract_field(parent_text, "Design class")
            or extract_field(parent_text, "Class")
            or ""
        )
        highest = extract_field(parent_text, "Highest design class assigned")
        start = extract_field(parent_text, "Implementation-start design class")
        if design_class not in DESIGN_CLASSES:
            errors.append(f"{rel(parent_path)}: invalid or missing design class")
        if highest not in DESIGN_CLASSES or (
            design_class in DESIGN_CLASSES and int(highest) < int(design_class)
        ):
            errors.append(f"{rel(parent_path)}: invalid highest design class")
        if phase in IMPLEMENTATION_PHASES and (
            start not in DESIGN_CLASSES
            or design_class not in DESIGN_CLASSES
            or int(start) > int(design_class)
        ):
            errors.append(f"{rel(parent_path)}: invalid implementation-start class")
        if design_class == "1" and phase in IMPLEMENTATION_PHASES:
            for field in (
                "Existing pattern/components reused",
                "Applicable design-system rule",
            ):
                value = extract_field(parent_text, field)
                if not value or value.lower() in {"none", "not-applicable"}:
                    errors.append(
                        f"{rel(parent_path)}: design class 1 requires concrete {field}"
                    )
    else:
        errors.append("active UI work has no readable parent artifact")

    if design_class in DESIGN_CLASSES:
        if phase not in {"discovery", "design-draft", "design-review"}:
            validate_tasks(config, work_dir, design_class, errors)
        validate_design_delta(work_dir, design_class, phase, config, errors)
        readiness_statuses = (
            {"ready-for-implementation"}
            if work_type == "incremental-change"
            else {"accepted", "in-progress", "completed"}
        )
        if design_class in {"2", "3"} and parent_status in readiness_statuses:
            delta = work_dir / "DESIGN_DELTA.md"
            delta_status = (
                extract_field(delta.read_text(encoding="utf-8"), "Status")
                if delta.is_file()
                else None
            )
            if delta_status != "approved":
                parent_label = rel(parent_path) if parent_path else "parent artifact"
                errors.append(
                    f"{parent_label} cannot be implementation-ready before "
                    "design approval"
                )
        validate_tooling(config, work_dir, design_class, phase, errors)
        validate_prototype(config, work_dir, design_class, phase, errors)
        validate_story_markers(config, work_dir, phase, errors)
        validate_review_transition(work_dir, design_class, phase, errors)
        if design_class != "0" and phase in EVIDENCE_PHASES:
            validate_manifest(config, work_dir, phase, errors)
        if design_class != "0" and phase == "closeout":
            validate_closeout(config, work_dir, errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: active UI-quality artifacts are structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
