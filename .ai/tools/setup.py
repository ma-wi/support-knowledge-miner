#!/usr/bin/env python3
"""Offline inspection and approved desired-state setup for generated projects."""

from __future__ import annotations

import argparse
import copy
import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess  # nosec B404 - explicit local commands only after approval
import sys
import tempfile
import tomllib
from datetime import date
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bootstrap as bootstrap_tool  # noqa: E402
from _common import get, load_yaml_subset  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ".ai/project.yaml"
PROFILE_PATH = ".ai/policy-profile.yaml"
QUALITY_PATH = ".ai/policies/QUALITY_GATES.md"
CONTEXT_PATH = ".ai/PROJECT_CONTEXT.md"
SECURITY_PATH = "SECURITY.md"
LOCK_PATH = ".ai/.setup.lock"
CATALOG_PATH = ROOT / ".ai/policies/setup-controls.json"
PLAN_SCHEMA_VERSION = 1
BOOTSTRAP_STEP_ORDER = ("configure", "python", "react")
RUNTIME_COMPONENT = r"[0-9]{1,4}"
SCAN_FILE_LIMIT = 20_000
SCAN_ENTRY_LIMIT = 50_000
SCAN_BYTE_LIMIT = 1_048_576
PLAN_BYTE_LIMIT = 8_388_608
IGNORED_DIRECTORIES = {
    ".git",
    ".ai",
    ".agents",
    ".aiassistant",
    ".idea",
    ".vscode",
    ".cursor",
    ".claude",
    ".codex",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    "build",
    "dist",
    "target",
    ".next",
}
STACKS = ("python", "react", "bash", "dotnet")
GATE_NAMES = (
    "setup",
    "format_check",
    "format_apply",
    "lint",
    "test",
    "security",
    "dependency_scan",
    "build",
)
SETUP_OWNED_PATHS = {
    CONFIG_PATH,
    PROFILE_PATH,
    QUALITY_PATH,
    CONTEXT_PATH,
    SECURITY_PATH,
}
MANAGED_START = "<!-- guided-setup:policy-profile:start -->"
MANAGED_END = "<!-- guided-setup:policy-profile:end -->"
SECURITY_CONTACT_START = "<!-- guided-setup:security-contact:start -->"
SECURITY_CONTACT_END = "<!-- guided-setup:security-contact:end -->"
CONTEXT_FIELDS = {
    "product": "Product or service",
    "primary_users": "Primary users",
    "main_outcome": "Main outcome",
    "deployment_environment": "Deployment environment",
    "data_classification": "Data classification",
    "identities_authorization": "Identities and authorization",
    "distribution_model": "Distribution model",
}


class SetupError(RuntimeError):
    """A stable setup failure with a CLI exit category."""

    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


def stable_json(value: object, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
        separators=None if pretty else (",", ":"),
    )


def inspection_digest(inspection: dict[str, Any]) -> str:
    bound = copy.deepcopy(inspection)
    scan = bound.get("scan")
    if isinstance(scan, dict):
        scan.pop("files_considered", None)
    return digest_bytes(stable_json(bound).encode("utf-8"))


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def current_digest(path: Path) -> str | None:
    return digest_bytes(path.read_bytes()) if path.is_file() else None


def current_path_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.is_file():
        return "file"
    if path.is_dir():
        return "directory-empty" if not any(path.iterdir()) else "directory-nonempty"
    return "other"


def current_mode(path: Path) -> int | None:
    return path.stat().st_mode & 0o7777 if path.exists() else None


def contained_path(root: Path, relative: str) -> Path:
    if relative not in SETUP_OWNED_PATHS:
        raise SetupError(f"Plan targets a non-setup-owned path: {relative}")
    root = root.resolve()
    candidate = root / relative
    cursor = root
    for part in Path(relative).parts:
        cursor /= part
        if cursor.is_symlink():
            raise SetupError(f"Setup-owned path must not use symlinks: {relative}", 3)
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as error:
        raise SetupError(f"Plan path leaves the repository: {relative}") from error
    return candidate


def contained_project_path(root: Path, relative: str) -> Path:
    """Resolve one previewed application path without allowing boundary escapes."""
    candidate_relative = Path(relative)
    if (
        not relative
        or candidate_relative.is_absolute()
        or ".." in candidate_relative.parts
    ):
        raise SetupError(f"Project mutation path leaves the repository: {relative!r}")
    root = root.resolve()
    cursor = root
    for part in candidate_relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise SetupError(
                f"Project mutation path must not use symlinks: {relative}", 3
            )
    try:
        cursor.resolve(strict=False).relative_to(root)
    except ValueError as error:
        raise SetupError(
            f"Project mutation path leaves the repository: {relative}"
        ) from error
    return cursor


def project_mutation_preview(
    root: Path,
    *,
    stack: str,
    path: str,
    action: str,
    condition: str,
    glob: str | None = None,
) -> dict[str, object]:
    target = contained_project_path(root, path)
    preview: dict[str, object] = {
        "stack": stack,
        "path": path,
        "action": action,
        "condition": condition,
        "base_state": current_path_state(target),
        "base_sha256": current_digest(target),
        "base_mode": current_mode(target),
    }
    if glob is not None:
        members = []
        if target.is_dir():
            for member in sorted(target.glob(glob)):
                relative_member = relative(root, member)
                contained_member = contained_project_path(root, relative_member)
                members.append(
                    {
                        "path": relative_member,
                        "state": current_path_state(contained_member),
                        "sha256": current_digest(contained_member),
                        "mode": current_mode(contained_member),
                    }
                )
        preview["glob"] = glob
        preview["base_members"] = members
    return preview


def bounded_files(root: Path) -> Iterator[Path]:
    """Yield bounded, regular, non-symlink repository files without following links."""
    seen = 0
    entries = 0
    resolved_root = root.resolve()
    for directory, names, files in os.walk(root, followlinks=False):
        names[:] = sorted(
            name
            for name in names
            if name not in IGNORED_DIRECTORIES
            and not (Path(directory) / name).is_symlink()
        )
        entries += len(names) + len(files)
        if entries > SCAN_ENTRY_LIMIT:
            raise SetupError(
                f"Repository scan exceeds {SCAN_ENTRY_LIMIT} entries; narrow the "
                "repository before setup.",
                3,
            )
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                continue
            try:
                path.resolve().relative_to(resolved_root)
                path.stat()
            except (OSError, ValueError):
                continue
            seen += 1
            if seen > SCAN_FILE_LIMIT:
                raise SetupError(
                    f"Repository scan exceeds {SCAN_FILE_LIMIT} files; narrow the "
                    "repository before setup.",
                    3,
                )
            yield path


def read_bounded_text(path: Path) -> str:
    try:
        if path.stat().st_size > SCAN_BYTE_LIMIT:
            raise SetupError(
                f"Inspection input exceeds {SCAN_BYTE_LIMIT} bytes: {path}", 3
            )
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise SetupError(f"Inspection input is not UTF-8 text: {path}", 3) from error


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def evidence(path: str, kind: str, detail: str) -> dict[str, str]:
    return {"path": path, "kind": kind, "detail": detail}


def confidence_for(items: list[dict[str, str]], manifest_kinds: set[str]) -> str:
    if any(item["kind"] in manifest_kinds for item in items):
        return "high"
    if len(items) >= 2:
        return "medium"
    if items:
        return "low"
    return "none"


def parse_runtime_version(value: str, runtime: str) -> tuple[int, ...] | None:
    pattern = (
        rf"{RUNTIME_COMPONENT}\.{RUNTIME_COMPONENT}"
        rf"(?:\.{RUNTIME_COMPONENT})?"
        if runtime == "python"
        else rf"{RUNTIME_COMPONENT}\.{RUNTIME_COMPONENT}\.{RUNTIME_COMPONENT}"
    )
    normalized = value.strip().removeprefix("v")
    if re.fullmatch(pattern, normalized) is None:
        return None
    return tuple(int(part) for part in normalized.split("."))


def parse_runtime_requirement(
    requirement: str, runtime: str
) -> list[tuple[str, tuple[int, ...]]] | None:
    """Parse a conservative intersection of Python/Node comparison clauses."""
    text = requirement.strip()
    version_pattern = (
        rf"{RUNTIME_COMPONENT}\.{RUNTIME_COMPONENT}"
        rf"(?:\.{RUNTIME_COMPONENT})?"
        if runtime == "python"
        else rf"{RUNTIME_COMPONENT}\.{RUNTIME_COMPONENT}\.{RUNTIME_COMPONENT}"
    )
    if re.fullmatch(version_pattern, text):
        parsed = parse_runtime_version(text, runtime)
        return [("==", parsed)] if parsed is not None else None
    separator = r"\s*,\s*" if runtime == "python" else r"(?:\s*,\s*|\s+)"
    raw_clauses = re.split(separator, text)
    if not raw_clauses or any(not clause for clause in raw_clauses):
        return None
    clauses: list[tuple[str, tuple[int, ...]]] = []
    for raw_clause in raw_clauses:
        match = re.fullmatch(rf"(==|>=|<=|>|<|~=)\s*({version_pattern})", raw_clause)
        if match is None:
            return None
        version = parse_runtime_version(match.group(2), runtime)
        if version is None:
            return None
        clauses.append((match.group(1), version))
    return clauses


def normalized_version(version: tuple[int, ...], width: int = 3) -> tuple[int, ...]:
    return (*version, *((0,) * (width - len(version))))


def runtime_satisfies(
    candidate: str,
    runtime: str,
    requirements: list[list[tuple[str, tuple[int, ...]]]],
) -> bool:
    parsed_candidate = parse_runtime_version(candidate, runtime)
    if parsed_candidate is None:
        return False
    actual = normalized_version(parsed_candidate)
    for clauses in requirements:
        for operator, expected_version in clauses:
            expected = normalized_version(expected_version)
            if operator == "==" and actual != expected:
                return False
            if operator == ">=" and actual < expected:
                return False
            if operator == ">" and actual <= expected:
                return False
            if operator == "<=" and actual > expected:
                return False
            if operator == "<" and actual >= expected:
                return False
            if operator == "~=":
                upper = (
                    (expected[0] + 1, 0, 0)
                    if len(expected_version) == 2
                    else (expected[0], expected[1] + 1, 0)
                )
                if actual < expected or actual >= upper:
                    return False
    return True


def requirement_candidate(
    runtime: str, clauses: list[tuple[str, tuple[int, ...]]]
) -> str | None:
    for operator, version in clauses:
        if operator in {"==", ">=", "~="}:
            candidate = ".".join(str(part) for part in version)
            if runtime == "node" and len(version) != 3:
                return None
            return candidate
    return None


def runtime_finding(
    runtime: str,
    pins: list[tuple[str, dict[str, str]]],
    requirements: list[list[tuple[str, tuple[int, ...]]]],
    all_evidence: list[dict[str, str]],
    ambiguities: list[dict[str, str]],
    unsupported_requirement: bool,
) -> dict[str, Any]:
    """Select only a runtime proven compatible with every supported constraint."""
    if unsupported_requirement:
        return {
            "detected": True,
            "value": None,
            "confidence": "none",
            "evidence": all_evidence,
        }
    pin_values = sorted({item[0] for item in pins})
    if len(pin_values) > 1:
        ambiguities.append(
            {
                "kind": f"{runtime}-runtime",
                "detail": f"Conflicting {runtime} runtime pins found: "
                + ", ".join(pin_values),
            }
        )
        return {
            "detected": True,
            "value": None,
            "confidence": "none",
            "evidence": all_evidence,
        }
    if pin_values:
        selected = pin_values[0]
        if runtime_satisfies(selected, runtime, requirements):
            return {
                "detected": True,
                "value": selected,
                "confidence": "high",
                "evidence": all_evidence,
            }
        ambiguities.append(
            {
                "kind": f"{runtime}-runtime",
                "detail": f"Pinned {runtime} runtime {selected} does not satisfy "
                "all detected manifest requirements",
            }
        )
        return {
            "detected": True,
            "value": None,
            "confidence": "none",
            "evidence": all_evidence,
        }
    candidates = {
        candidate
        for clauses in requirements
        if (candidate := requirement_candidate(runtime, clauses)) is not None
        and runtime_satisfies(candidate, runtime, requirements)
    }
    if len(candidates) != 1:
        if all_evidence:
            detail = (
                f"Conflicting compatible {runtime} runtime candidates found: "
                + ", ".join(sorted(candidates))
                if candidates
                else f"No exact {runtime} runtime can be safely selected from "
                "the detected requirements"
            )
            ambiguities.append({"kind": f"{runtime}-runtime", "detail": detail})
        return {
            "detected": bool(all_evidence),
            "value": None,
            "confidence": "none",
            "evidence": all_evidence,
        }
    return {
        "detected": True,
        "value": next(iter(candidates)),
        "confidence": "medium",
        "evidence": all_evidence,
    }


def inspect_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = list(bounded_files(root))
    by_name: dict[str, list[Path]] = {}
    for path in files:
        by_name.setdefault(path.name.lower(), []).append(path)

    stack_evidence: dict[str, list[dict[str, str]]] = {stack: [] for stack in STACKS}
    conflicts: list[dict[str, str]] = []
    ambiguities: list[dict[str, str]] = []
    identities: list[tuple[str, str]] = []
    dependency_manifests: list[str] = []
    source_roots: dict[str, list[str]] = {stack: [] for stack in STACKS}
    python_package_directories: list[str] = []
    package_managers: list[dict[str, str]] = []
    quality_commands: list[dict[str, str]] = []
    dependency_names: set[str] = set()
    runtime_evidence: dict[str, list[dict[str, str]]] = {
        "python": [],
        "node": [],
    }
    runtime_pins: dict[str, list[tuple[str, dict[str, str]]]] = {
        "python": [],
        "node": [],
    }
    runtime_requirements: dict[str, list[list[tuple[str, tuple[int, ...]]]]] = {
        "python": [],
        "node": [],
    }
    unsupported_runtime_requirements: set[str] = set()

    for runtime, names in (
        ("python", (".python-version",)),
        ("node", (".node-version", ".nvmrc")),
    ):
        for name in names:
            for path in by_name.get(name, []):
                raw = read_bounded_text(path).strip()
                item = evidence(
                    relative(root, path),
                    f"{runtime}-runtime-pin",
                    f"Declared {runtime} runtime {raw!r}",
                )
                runtime_evidence[runtime].append(item)
                pin_version = parse_runtime_version(raw, runtime)
                if pin_version is not None:
                    candidate = ".".join(str(part) for part in pin_version)
                    runtime_pins[runtime].append((candidate, item))
                else:
                    ambiguities.append(
                        {
                            "kind": f"{runtime}-runtime-requirement",
                            "detail": f"{relative(root, path)} does not contain one "
                            f"supported exact {runtime} runtime version",
                        }
                    )

    python_manifests = (
        "pipfile",
        "poetry.lock",
        "pyproject.toml",
        "requirements.txt",
        "uv.lock",
    )
    for name in python_manifests:
        for path in by_name.get(name, []):
            rel = relative(root, path)
            stack_evidence["python"].append(
                evidence(rel, "python-manifest", f"Found {name}")
            )
            dependency_manifests.append(rel)
    for path in files:
        rel = relative(root, path)
        suffix = path.suffix.lower()
        if suffix == ".py":
            stack_evidence["python"].append(
                evidence(rel, "python-source", "Python source file")
            )
            parts = Path(rel).parts
            root_name = parts[0] if len(parts) > 1 else "."
            if root_name not in source_roots["python"]:
                source_roots["python"].append(root_name)
            if (
                path.name == "__init__.py"
                and len(parts) >= 2
                and root_name not in {"test", "tests"}
            ):
                package_parts = (
                    parts[:2] if root_name == "src" and len(parts) >= 3 else parts[:1]
                )
                package_directory = Path(*package_parts).as_posix()
                if package_directory not in python_package_directories:
                    python_package_directories.append(package_directory)
        if suffix == ".sh":
            stack_evidence["bash"].append(
                evidence(rel, "bash-source", "Shell source file")
            )
            root_name = rel.split("/", 1)[0] if "/" in rel else "."
            if root_name not in source_roots["bash"]:
                source_roots["bash"].append(root_name)
        if suffix.lower() in {".sln", ".slnx", ".csproj", ".vbproj", ".fsproj"}:
            kind = (
                "dotnet-solution" if suffix in {".sln", ".slnx"} else "dotnet-project"
            )
            stack_evidence["dotnet"].append(evidence(rel, kind, f"Found {suffix} file"))
            if rel.rsplit("/", 1)[0] not in source_roots["dotnet"]:
                source_roots["dotnet"].append(
                    rel.rsplit("/", 1)[0] if "/" in rel else "."
                )

    pyprojects = by_name.get("pyproject.toml", [])
    for path in pyprojects:
        try:
            parsed = tomllib.loads(read_bounded_text(path))
        except (tomllib.TOMLDecodeError, SetupError) as error:
            conflicts.append(
                {
                    "path": relative(root, path),
                    "kind": "malformed-manifest",
                    "detail": str(error),
                }
            )
            continue
        project = parsed.get("project", {})
        if isinstance(project, dict) and isinstance(project.get("name"), str):
            identities.append((relative(root, path), project["name"]))
        if isinstance(project, dict) and isinstance(
            project.get("requires-python"), str
        ):
            requirement = project["requires-python"]
            item = evidence(
                relative(root, path),
                "python-runtime-requirement",
                f"project.requires-python = {requirement!r}",
            )
            runtime_evidence["python"].append(item)
            clauses = parse_runtime_requirement(requirement, "python")
            if clauses is not None:
                runtime_requirements["python"].append(clauses)
            else:
                unsupported_runtime_requirements.add("python")
                ambiguities.append(
                    {
                        "kind": "python-runtime-requirement",
                        "detail": f"{relative(root, path)} has a Python requirement "
                        "that cannot be mapped to an exact supported runtime",
                    }
                )
        dependencies = (
            project.get("dependencies", []) if isinstance(project, dict) else []
        )
        if isinstance(dependencies, list):
            dependency_names.update(
                re.split(r"[\s<>=!~;\[]", item, maxsplit=1)[0].lower()
                for item in dependencies
                if isinstance(item, str)
            )
        tool = parsed.get("tool", {})
        if isinstance(tool, dict):
            for command, marker in (
                ("ruff format --check .", "ruff"),
                ("ruff check .", "ruff"),
                ("python -m pytest", "pytest"),
                ("mypy .", "mypy"),
            ):
                if marker in tool:
                    quality_commands.append(
                        {
                            "path": relative(root, path),
                            "gate": command.split()[0],
                            "command": command,
                            "source": "detected-fact",
                        }
                    )

    react_roots: list[str] = []
    manager_by_root: dict[str, str] = {}
    for path in by_name.get("package.json", []):
        rel = relative(root, path)
        dependency_manifests.append(rel)
        try:
            parsed_json = json.loads(read_bounded_text(path))
        except (json.JSONDecodeError, SetupError) as error:
            conflicts.append(
                {"path": rel, "kind": "malformed-manifest", "detail": str(error)}
            )
            continue
        if not isinstance(parsed_json, dict):
            conflicts.append(
                {
                    "path": rel,
                    "kind": "malformed-manifest",
                    "detail": "package.json root must be an object",
                }
            )
            continue
        package_name = parsed_json.get("name")
        if isinstance(package_name, str) and package_name:
            identities.append((rel, package_name))
        package_dependencies: dict[str, object] = {}
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            dependency_group = parsed_json.get(key, {})
            if isinstance(dependency_group, dict):
                package_dependencies.update(dependency_group)
        dependency_names.update(str(item).lower() for item in package_dependencies)
        package_root = path.parent
        root_rel = relative(root, package_root) if package_root != root else "."
        manager_markers = (
            ("pnpm", package_root / "pnpm-lock.yaml"),
            ("yarn", package_root / "yarn.lock"),
            ("npm", package_root / "package-lock.json"),
        )
        found = [
            manager
            for manager, marker in manager_markers
            if marker.is_file() and not marker.is_symlink()
        ]
        if len(found) > 1:
            conflicts.append(
                {
                    "path": root_rel,
                    "kind": "package-manager-conflict",
                    "detail": f"Multiple lockfile families found: {', '.join(found)}",
                }
            )
        elif found:
            manager_by_root[root_rel] = found[0]
            package_managers.append(
                {
                    "root": root_rel,
                    "manager": found[0],
                    "source": "detected-fact",
                }
            )
        manager = found[0] if len(found) == 1 else "npm"
        if "react" in package_dependencies:
            stack_evidence["react"].append(
                evidence(rel, "react-manifest", "package.json declares React")
            )
            react_roots.append(root_rel)
            if root_rel not in source_roots["react"]:
                source_roots["react"].append(root_rel)
        scripts = parsed_json.get("scripts", {})
        if isinstance(scripts, dict):
            for script, gate in (
                ("format:check", "format_check"),
                ("format", "format_apply"),
                ("lint", "lint"),
                ("test", "test"),
                ("build", "build"),
                ("typecheck", "lint"),
            ):
                if isinstance(scripts.get(script), str):
                    command = (
                        f"yarn {script}"
                        if manager == "yarn"
                        else f"{manager} run {script}"
                    )
                    quality_commands.append(
                        {
                            "path": rel,
                            "gate": gate,
                            "command": command,
                            "source": "detected-fact",
                        }
                    )
        engines = parsed_json.get("engines", {})
        if isinstance(engines, dict) and isinstance(engines.get("node"), str):
            requirement = engines["node"]
            item = evidence(
                rel,
                "node-runtime-requirement",
                f"engines.node = {requirement!r}",
            )
            runtime_evidence["node"].append(item)
            clauses = parse_runtime_requirement(requirement, "node")
            if clauses is not None:
                runtime_requirements["node"].append(clauses)
            else:
                unsupported_runtime_requirements.add("node")
                ambiguities.append(
                    {
                        "kind": "node-runtime-requirement",
                        "detail": f"{rel} has a Node.js requirement that cannot be "
                        "mapped to an exact supported runtime",
                    }
                )

    for name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock"):
        dependency_manifests.extend(
            relative(root, path) for path in by_name.get(name, [])
        )
    for path in files:
        if path.suffix.lower() in {".csproj", ".vbproj", ".fsproj"}:
            dependency_manifests.append(relative(root, path))

    if len(set(react_roots)) > 1:
        ambiguities.append(
            {
                "kind": "multiple-react-roots",
                "detail": "Choose the frontend root: "
                + ", ".join(sorted(set(react_roots))),
            }
        )
    managers = {
        manager_by_root[root] for root in react_roots if root in manager_by_root
    }
    if len(managers) > 1:
        ambiguities.append(
            {
                "kind": "react-package-manager",
                "detail": "React roots use different package managers; select one root",
            }
        )

    runtimes = {
        runtime: runtime_finding(
            runtime,
            runtime_pins[runtime],
            runtime_requirements[runtime],
            runtime_evidence[runtime],
            ambiguities,
            runtime in unsupported_runtime_requirements,
        )
        for runtime in ("python", "node")
    }
    for runtime, finding in runtimes.items():
        finding["pins"] = sorted({value for value, _ in runtime_pins[runtime]})
        finding["requirements_supported"] = (
            runtime not in unsupported_runtime_requirements
        )
        finding["constraints"] = [
            [
                {
                    "operator": operator,
                    "version": ".".join(str(part) for part in version),
                }
                for operator, version in clauses
            ]
            for clauses in runtime_requirements[runtime]
        ]

    identity_values = {value for _, value in identities}
    if len(identity_values) > 1:
        ambiguities.append(
            {
                "kind": "project-identity",
                "detail": "Multiple manifest names found: "
                + ", ".join(sorted(identity_values)),
            }
        )
    identity: dict[str, Any] = (
        {
            "value": identities[0][1],
            "confidence": "high",
            "evidence": [
                evidence(path, "manifest-name", value) for path, value in identities
            ],
        }
        if len(identity_values) == 1
        else {"value": None, "confidence": "none", "evidence": []}
    )

    network_markers = {
        "fastapi",
        "flask",
        "django",
        "starlette",
        "express",
        "next",
        "aspnetcore",
        "microsoft.aspnetcore",
    }
    network_dependencies = sorted(
        dependency
        for dependency in dependency_names
        if any(marker in dependency for marker in network_markers)
    )
    deployment_files = sorted(
        relative(root, path)
        for path in files
        if path.name.lower()
        in {"dockerfile", "compose.yaml", "compose.yml", "kubernetes.yaml"}
        or path.suffix.lower() in {".bicep"}
    )

    config_state: dict[str, object] = {
        "present": False,
        "valid": False,
        "error": None,
    }
    config_path = root / CONFIG_PATH
    config_data: dict[str, Any] | None = None
    if config_path.is_file():
        config_state["present"] = True
        try:
            if config_path.is_symlink():
                raise SetupError("Configuration must not be a symbolic link", 3)
            if config_path.stat().st_size > SCAN_BYTE_LIMIT:
                raise SetupError(f"Configuration exceeds {SCAN_BYTE_LIMIT} bytes", 3)
            config_data = load_yaml_subset(config_path)
            bootstrap_tool.validate_config(config_data)
            config_state["valid"] = True
        except (OSError, SetupError, SystemExit) as error:
            config_state["error"] = str(error)

    stale_defaults = False
    defaults_path = root / ".ai/config/project.defaults.env"
    policy_profile: dict[str, Any] | None = None
    policy_state: dict[str, object] = {
        "present": (root / PROFILE_PATH).is_file(),
        "valid": False,
        "error": None,
    }
    try:
        loaded_policy = bootstrap_tool.load_policy_profile(root)
        if loaded_policy is not None:
            policy_profile = loaded_policy
        policy_state["valid"] = True
    except SystemExit as error:
        policy_state["error"] = str(error)
        conflicts.append(
            {
                "path": PROFILE_PATH,
                "kind": "invalid-policy-profile",
                "detail": str(error),
            }
        )
    if config_data is not None and config_state["valid"]:
        try:
            expected = bootstrap_tool.generate_env(config_data, policy_profile)
            stale_defaults = (
                not defaults_path.is_file()
                or defaults_path.read_text(encoding="utf-8") != expected
            )
        except (OSError, SystemExit):
            stale_defaults = True

    placeholders: list[dict[str, str]] = []
    readiness_checks = (
        (CONFIG_PATH, "project.name", lambda text: '"CHANGE_ME"' in text),
        (
            ".ai/PROJECT_CONTEXT.md",
            "Product or service",
            lambda text: (
                re.search(r"(?m)^-\s*Product or service:\s*$", text) is not None
            ),
        ),
        (
            ".ai/PROJECT_CONTEXT.md",
            "Primary users",
            lambda text: re.search(r"(?m)^-\s*Primary users:\s*$", text) is not None,
        ),
        (
            ".ai/PROJECT_CONTEXT.md",
            "Main outcome",
            lambda text: re.search(r"(?m)^-\s*Main outcome:\s*$", text) is not None,
        ),
        (
            ".ai/PROJECT_CONTEXT.md",
            "Deployment environment",
            lambda text: (
                re.search(r"(?m)^-\s*Deployment environment:\s*$", text) is not None
            ),
        ),
        (
            ".ai/PROJECT_CONTEXT.md",
            "Data classification",
            lambda text: (
                re.search(r"(?m)^-\s*Data classification:\s*$", text) is not None
            ),
        ),
        (
            ".ai/PROJECT_CONTEXT.md",
            "Identities and authorization",
            lambda text: (
                re.search(r"(?m)^-\s*Identities and authorization:\s*$", text)
                is not None
            ),
        ),
        (
            ".ai/PROJECT_CONTEXT.md",
            "Distribution model",
            lambda text: (
                re.search(r"(?m)^-\s*Distribution model:\s*$", text) is not None
            ),
        ),
        (
            ".ai/PROJECT_CONTEXT.md",
            "Security and privacy constraints",
            lambda text: (
                re.search(r"(?m)^-\s*Security and privacy constraints:\s*$", text)
                is not None
            ),
        ),
        (
            SECURITY_PATH,
            "security reporting contact",
            lambda text: "CHANGE_ME_SECURITY_CONTACT" in text,
        ),
        (
            QUALITY_PATH,
            "project decisions reviewed",
            lambda text: "Project decisions reviewed: no" in text,
        ),
    )
    for rel, marker, incomplete in readiness_checks:
        path = root / rel
        if path.is_file():
            try:
                text = read_bounded_text(path)
            except SetupError:
                continue
            if incomplete(text):
                placeholders.append(
                    {"path": rel, "marker": marker, "status": "incomplete"}
                )

    stacks: dict[str, dict[str, Any]] = {}
    manifest_kinds = {
        "python": {"python-manifest"},
        "react": {"react-manifest"},
        "bash": {"bash-source"},
        "dotnet": {"dotnet-solution", "dotnet-project"},
    }
    for stack in STACKS:
        items = stack_evidence[stack]
        stacks[stack] = {
            "detected": bool(items),
            "confidence": confidence_for(items, manifest_kinds[stack]),
            "evidence": items[:100],
            "source_roots": sorted(source_roots[stack]),
        }
        if stack == "python":
            stacks[stack]["package_directories"] = sorted(python_package_directories)

    required_tools: set[str] = set()
    if stacks["python"]["detected"]:  # type: ignore[index]
        required_tools.add("uv")
    if stacks["react"]["detected"]:  # type: ignore[index]
        required_tools.add(next(iter(managers), "npm"))
        required_tools.add("node")
    if stacks["bash"]["detected"]:  # type: ignore[index]
        required_tools.update({"shellcheck", "bats"})
    if stacks["dotnet"]["detected"]:  # type: ignore[index]
        required_tools.add("dotnet")
    if (
        policy_profile is not None
        and get(
            policy_profile,
            "controls",
            "secret_scanning",
            "value",
            default="required",
        )
        == "required"
    ):
        required_tools.add("gitleaks")
    missing_tools = [
        {
            "tool": tool,
            "instruction": f"Install {tool} through the platform's trusted package "
            "or runtime manager, then rerun doctor.",
        }
        for tool in sorted(required_tools)
        if shutil.which(tool) is None
    ]

    unused_configured = []
    if config_data is not None:
        for stack in STACKS:
            if (
                get(config_data, "stacks", stack, "enabled", default=False)
                and not stacks[stack]["detected"]
            ):
                unused_configured.append(
                    {
                        "stack": stack,
                        "detail": f"{stack} is enabled but no current local evidence "
                        "was detected; absence is not approval to disable it",
                    }
                )

    return {
        "schema_version": 1,
        "root": ".",
        "scan": {
            "files_considered": len(files),
            "file_limit": SCAN_FILE_LIMIT,
            "entry_limit": SCAN_ENTRY_LIMIT,
            "byte_limit": SCAN_BYTE_LIMIT,
            "ignored_directories": sorted(IGNORED_DIRECTORIES),
            "network_access": False,
            "repository_code_executed": False,
        },
        "project_identity": identity,
        "stacks": stacks,
        "source_roots": source_roots,
        "runtimes": runtimes,
        "package_managers": package_managers,
        "dependency_manifests": sorted(set(dependency_manifests)),
        "quality_commands": quality_commands,
        "applicability": {
            "ui": bool(stack_evidence["react"]),
            "user_facing_errors": bool(stack_evidence["react"] or network_dependencies),
            "network_service": bool(network_dependencies),
            "external_inputs": bool(network_dependencies),
            "deployment": bool(deployment_files),
            "deployment_evidence": deployment_files,
            "network_dependency_evidence": network_dependencies,
        },
        "risk_inputs": {
            "exposure": (
                "network-service-evidence"
                if network_dependencies
                else "no-network-service-evidence"
            ),
            "data_sensitivity": "unknown",
            "identities_and_authorization": "unknown",
            "primary_users": "unknown",
            "distribution": ("deployment-evidence" if deployment_files else "unknown"),
            "dependencies": (
                "manifests-detected" if dependency_manifests else "none-detected"
            ),
            "threat_surface_inference": (
                "external-inputs-likely" if network_dependencies else "limited-evidence"
            ),
        },
        "configuration": config_state,
        "policy_profile": policy_state,
        "apparently_unused_configuration": unused_configured,
        "generated_defaults_stale": stale_defaults,
        "readiness": {
            "complete": not placeholders,
            "incomplete_fields": placeholders,
        },
        "missing_tools": missing_tools,
        "ambiguities": ambiguities,
        "conflicts": conflicts,
    }


def yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def render_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = []

    def render(mapping: dict[str, Any], indent: int) -> None:
        for key, value in mapping.items():
            prefix = " " * indent + f"{key}:"
            if isinstance(value, dict):
                lines.append(prefix)
                render(value, indent + 2)
            else:
                lines.append(f"{prefix} {yaml_scalar(value)}")

    render(data, 0)
    return "\n".join(lines) + "\n"


def set_nested(data: dict[str, Any], keys: tuple[str, ...], value: object) -> None:
    current = data
    for key in keys[:-1]:
        child = current.setdefault(key, {})
        if not isinstance(child, dict):
            raise SetupError(f"Cannot set {'.'.join(keys)} below scalar {key}")
        current = child
    current[keys[-1]] = value


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}".strip(".")
        if isinstance(value, dict):
            result.update(flatten(value, path))
        else:
            result[path] = value
    return result


def parse_assignments(values: list[str] | None, label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise SetupError(f"{label} requires NAME=VALUE: {item}")
        key, value = item.split("=", 1)
        if not key or key in result:
            raise SetupError(f"Invalid or duplicate {label} assignment: {item}")
        result[key] = value
    return result


def load_catalog(root: Path) -> dict[str, Any]:
    path = root / ".ai/policies/setup-controls.json"
    try:
        if path.is_symlink():
            raise SetupError("Policy control catalog must not be a symbolic link", 3)
        path.resolve().relative_to(root.resolve())
        catalog = json.loads(read_bounded_text(path))
    except (OSError, ValueError, json.JSONDecodeError, SetupError) as error:
        raise SetupError(f"Policy control catalog is invalid: {error}", 3) from error
    if catalog.get("schema_version") != 1 or not isinstance(
        catalog.get("controls"), list
    ):
        raise SetupError("Unsupported policy control catalog schema", 3)
    return catalog


def load_profile_data(root: Path) -> dict[str, Any]:
    path = root / PROFILE_PATH
    if not path.is_file():
        return {}
    try:
        if path.is_symlink():
            raise SetupError("Existing policy profile must not be a symbolic link", 3)
        path.resolve().relative_to(root.resolve())
        if path.stat().st_size > SCAN_BYTE_LIMIT:
            raise SetupError(
                f"Existing policy profile exceeds {SCAN_BYTE_LIMIT} bytes", 3
            )
        data = load_yaml_subset(path)
    except (OSError, ValueError, SystemExit) as error:
        raise SetupError(f"Existing policy profile is invalid: {error}", 3) from error
    if not isinstance(data, dict):
        raise SetupError("Existing policy profile root must be a mapping", 3)
    return data


def profile_controls(root: Path) -> dict[str, dict[str, str]]:
    controls = load_profile_data(root).get("controls", {})
    if not isinstance(controls, dict):
        raise SetupError("Existing policy profile controls must be a mapping", 3)
    return {name: value for name, value in controls.items() if isinstance(value, dict)}


def profile_exceptions(root: Path) -> dict[str, dict[str, str]]:
    exceptions = load_profile_data(root).get("temporary_exceptions", {})
    if not isinstance(exceptions, dict):
        raise SetupError(
            "Existing policy profile temporary_exceptions must be a mapping", 3
        )
    return {
        name: value for name, value in exceptions.items() if isinstance(value, dict)
    }


def recommended_policy(control_id: str, inspection: dict[str, Any]) -> tuple[str, str]:
    dependencies = bool(inspection["dependency_manifests"])
    network = bool(inspection["applicability"]["network_service"])
    code = any(inspection["stacks"][stack]["detected"] for stack in STACKS)
    python_or_dotnet = any(
        inspection["stacks"][stack]["detected"] for stack in ("python", "dotnet")
    )
    if control_id == "static_security":
        return (
            (
                "required",
                "Supported code or external inputs need static security analysis",
            )
            if python_or_dotnet or network
            else (
                "not_applicable",
                "No supported security-analyzer target or external input was detected",
            )
        )
    if control_id == "secret_scanning":
        return (
            (
                "required",
                "Dependencies, deployment, or network exposure can carry secrets",
            )
            if dependencies or network or inspection["applicability"]["deployment"]
            else (
                "not_applicable",
                "No dependency, deployment, credential, or service evidence was detected",
            )
        )
    if control_id == "dependency_scanning":
        return (
            ("required", "Dependency manifests were detected")
            if dependencies
            else ("not_applicable", "No dependency manifest was detected")
        )
    if control_id == "dependency_vulnerability_threshold":
        return "high", "Retain the versioned high-severity blocking baseline"
    if control_id == "warning_treatment":
        return (
            ("errors", "Detected code should keep warnings actionable")
            if code
            else ("warnings", "No project code was detected")
        )
    if control_id == "authentication":
        return (
            ("required", "Network service evidence may include protected operations")
            if network
            else (
                "not_applicable",
                "No network service or protected operation was detected",
            )
        )
    if control_id == "availability":
        return (
            ("required", "Network service or external input evidence was detected")
            if network
            else ("not_applicable", "No externally reachable service was detected")
        )
    raise SetupError(f"No recommendation rule for policy control {control_id}", 3)


def risk_profile(inspection: dict[str, Any]) -> str:
    if inspection["applicability"]["network_service"]:
        return "public-service-review"
    if inspection["dependency_manifests"]:
        return "private-internal"
    return "local-prototype"


def render_profile(
    mode: str,
    risk: str,
    controls: dict[str, dict[str, str]],
    exceptions: dict[str, dict[str, str]],
) -> str:
    data: dict[str, Any] = {
        "schema_version": 1,
        "mode": mode,
        "risk_profile": risk,
        "controls": {},
    }
    for control_id in sorted(controls):
        data["controls"][control_id] = controls[control_id]
    if exceptions:
        data["temporary_exceptions"] = {
            control_id: exceptions[control_id] for control_id in sorted(exceptions)
        }
    return render_yaml(data)


def managed_policy_block(
    mode: str,
    risk: str,
    controls: dict[str, dict[str, str]],
    exceptions: dict[str, dict[str, str]],
) -> str:
    lines = [
        MANAGED_START,
        "## Guided setup policy profile",
        "",
        f"- Decision mode: `{mode}`",
        f"- Risk profile: `{risk}`",
        "- Decisions:",
    ]
    for control_id in sorted(controls):
        decision = controls[control_id]
        lines.append(
            f"  - `{control_id}` = `{decision['value']}` "
            f"({decision['source']}): {markdown_inline(decision['rationale'])}"
        )
    if exceptions:
        lines.append("- Temporary exceptions:")
        for control_id in sorted(exceptions):
            exception = exceptions[control_id]
            lines.append(
                f"  - `{control_id}`: owner "
                f"`{markdown_inline(exception['owner'])}`, review "
                f"`{exception['review_date']}`, follow-up: "
                f"{markdown_inline(exception['follow_up'])}"
            )
    lines.extend(
        [
            "- Canonical structured source: `.ai/policy-profile.yaml`",
            MANAGED_END,
        ]
    )
    return "\n".join(lines)


def replace_managed(text: str, block: str) -> str:
    if MANAGED_START in text or MANAGED_END in text:
        if text.count(MANAGED_START) != 1 or text.count(MANAGED_END) != 1:
            raise SetupError("Managed policy markers are malformed", 3)
        start = text.index(MANAGED_START)
        end = text.index(MANAGED_END, start) + len(MANAGED_END)
        return text[:start] + block + text[end:]
    return text.rstrip() + "\n\n" + block + "\n"


def validate_project_text(value: str, label: str) -> str:
    normalized = value.strip()
    if (
        not normalized
        or any(ord(character) < 32 for character in value)
        or len(normalized) > 500
    ):
        raise SetupError(
            f"{label} must be a non-empty single line up to 500 characters"
        )
    return normalized


def markdown_inline(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def update_context_fields(text: str, values: dict[str, str]) -> str:
    unknown = set(values) - set(CONTEXT_FIELDS)
    if unknown:
        raise SetupError(
            "Unknown project context field(s): " + ", ".join(sorted(unknown))
        )
    updated = text
    for key, raw_value in values.items():
        label = CONTEXT_FIELDS[key]
        value = validate_project_text(raw_value, f"context.{key}")
        pattern = re.compile(rf"(?m)^-\s*{re.escape(label)}:.*$")
        if pattern.search(updated) is None:
            raise SetupError(f"Project context field is missing: {label}", 3)
        updated = pattern.sub(f"- {label}: {value}", updated, count=1)
    return updated


def update_security_contact(text: str, raw_contact: str) -> str:
    contact = validate_project_text(raw_contact, "security contact")
    if "`" in contact or "guided-setup:" in contact:
        raise SetupError(
            "security contact must not contain Markdown backticks or setup markers"
        )
    block = f"{SECURITY_CONTACT_START}\n`{contact}`\n{SECURITY_CONTACT_END}"
    if SECURITY_CONTACT_START in text or SECURITY_CONTACT_END in text:
        if (
            text.count(SECURITY_CONTACT_START) != 1
            or text.count(SECURITY_CONTACT_END) != 1
        ):
            raise SetupError("Managed security-contact markers are malformed", 3)
        start = text.index(SECURITY_CONTACT_START)
        end = text.index(SECURITY_CONTACT_END, start) + len(SECURITY_CONTACT_END)
        return text[:start] + block + text[end:]
    if "`CHANGE_ME_SECURITY_CONTACT`" not in text:
        raise SetupError(
            "SECURITY.md has no managed contact region or legacy contact placeholder",
            3,
        )
    return text.replace("`CHANGE_ME_SECURITY_CONTACT`", block, 1)


def default_config(root: Path) -> dict[str, Any]:
    path = root / CONFIG_PATH
    if not path.is_file():
        raise SetupError(f"Required setup configuration is missing: {CONFIG_PATH}", 3)
    try:
        data = load_yaml_subset(path)
        bootstrap_tool.validate_config(data)
    except SystemExit as error:
        raise SetupError(f"Project configuration is invalid: {error}", 3) from error
    return data


def build_plan(
    root: Path,
    *,
    mode: str,
    project_name: str | None = None,
    enable_stacks: list[str] | None = None,
    disable_stacks: list[str] | None = None,
    package_manager: str | None = None,
    python_directory: str | None = None,
    react_directory: str | None = None,
    python_runtime: str | None = None,
    node_runtime: str | None = None,
    gate_values: dict[str, str] | None = None,
    policy_values: dict[str, str] | None = None,
    policy_rationales: dict[str, str] | None = None,
    dotnet_solution: str | None = None,
    dotnet_test_project: str | None = None,
    temporary_exceptions: dict[str, str] | None = None,
    exception_owner: str | None = None,
    exception_review_date: str | None = None,
    exception_follow_up: str | None = None,
    context_values: dict[str, str] | None = None,
    security_contact: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    inspection = inspect_repository(root)
    if inspection["conflicts"]:
        raise SetupError(
            "Inspection found conflicts; resolve them before planning: "
            + "; ".join(item["detail"] for item in inspection["conflicts"]),
            3,
        )
    current = default_config(root)
    desired = copy.deepcopy(current)
    unresolved: list[dict[str, str]] = [
        *inspection["ambiguities"],
        *(
            {
                "kind": f"apparently-unused:{item['stack']}",
                "detail": item["detail"],
            }
            for item in inspection["apparently_unused_configuration"]
        ),
    ]
    enable = set(enable_stacks or [])
    disable = set(disable_stacks or [])
    overlap = enable & disable
    if overlap:
        raise SetupError(
            "A stack cannot be enabled and disabled together: "
            + ", ".join(sorted(overlap))
        )
    for stack in (*enable, *disable):
        if stack not in STACKS:
            raise SetupError(f"Unsupported stack: {stack}")

    if project_name is not None:
        if (
            not project_name.strip()
            or any(ord(character) < 32 for character in project_name)
            or len(project_name) > 128
        ):
            raise SetupError(
                "Project name must be a non-empty string up to 128 characters"
            )
        set_nested(desired, ("project", "name"), project_name.strip())
    elif get(current, "project", "name", default="CHANGE_ME") == "CHANGE_ME":
        identity = inspection["project_identity"]
        if mode == "recommended" and identity["confidence"] == "high":
            set_nested(desired, ("project", "name"), identity["value"])
        else:
            unresolved.append(
                {
                    "kind": "project-name",
                    "detail": "No project name was approved; CHANGE_ME remains",
                }
            )

    if mode == "recommended":
        for stack in STACKS:
            finding = inspection["stacks"][stack]
            if finding["detected"] and finding["confidence"] == "high":
                if (
                    stack == "react"
                    and len(finding["source_roots"]) != 1
                    and react_directory is None
                ):
                    unresolved.append(
                        {
                            "kind": "react-directory",
                            "detail": "Detected multiple React roots; select one "
                            "with --react-directory before enablement",
                        }
                    )
                    continue
                if stack == "dotnet":
                    detected_tests = [
                        item
                        for item in finding["evidence"]
                        if item["kind"] == "dotnet-project"
                        and "test" in item["path"].lower()
                    ]
                    if len(detected_tests) != 1 and dotnet_test_project is None:
                        unresolved.append(
                            {
                                "kind": "dotnet-test-project",
                                "detail": "Detected .NET, but a unique test project "
                                "must be selected before enablement",
                            }
                        )
                        continue
                enable.add(stack)

    for stack in sorted(enable):
        set_nested(desired, ("stacks", stack, "enabled"), True)
    for stack in sorted(disable):
        set_nested(desired, ("stacks", stack, "enabled"), False)

    python_enabled = bool(get(desired, "stacks", "python", "enabled", default=False))
    if python_enabled:
        python_roots = inspection["stacks"]["python"]["source_roots"]
        python_packages = inspection["stacks"]["python"]["package_directories"]
        usable_python_roots = [
            item
            for item in python_roots
            if item != "." and item not in {"test", "tests"}
        ]
        selected_python_root = python_directory
        if selected_python_root is None and len(python_packages) == 1:
            selected_python_root = python_packages[0]
        if (
            selected_python_root is None
            and not python_packages
            and len(usable_python_roots) == 1
        ):
            selected_python_root = usable_python_roots[0]
        if selected_python_root is not None:
            set_nested(
                desired,
                ("stacks", "python", "directory"),
                selected_python_root,
            )
        elif inspection["stacks"]["python"]["detected"]:
            unresolved.append(
                {
                    "kind": "python-directory",
                    "detail": "Detected Python, but its import package/source "
                    "directory is ambiguous or cannot be represented; select "
                    "the exact target with --python-directory",
                }
            )

    for runtime, explicit_value in (
        ("python", python_runtime),
        ("node", node_runtime),
    ):
        detected_runtime = inspection["runtimes"][runtime]
        selected_runtime = explicit_value
        serialized_constraints = detected_runtime["constraints"]
        parsed_constraints = [
            [
                (
                    item["operator"],
                    tuple(int(part) for part in item["version"].split(".")),
                )
                for item in clauses
            ]
            for clauses in serialized_constraints
        ]
        if explicit_value is not None and (
            not detected_runtime["requirements_supported"]
            or not runtime_satisfies(
                explicit_value,
                runtime,
                parsed_constraints,
            )
        ):
            raise SetupError(
                f"Explicit {runtime} runtime {explicit_value!r} is invalid or "
                "does not satisfy all detected manifest requirements"
            )
        if explicit_value is not None and any(
            not runtime_satisfies(
                explicit_value,
                runtime,
                [[("==", parse_runtime_version(pin, runtime) or ())]],
            )
            for pin in detected_runtime["pins"]
        ):
            raise SetupError(
                f"Explicit {runtime} runtime {explicit_value!r} conflicts with "
                "an existing exact runtime pin; setup does not update pin files"
            )
        if selected_runtime is None and detected_runtime["confidence"] in {
            "high",
            "medium",
        }:
            selected_runtime = detected_runtime["value"]
        if selected_runtime is not None:
            set_nested(desired, ("runtimes", runtime), selected_runtime)
        elif detected_runtime["detected"]:
            unresolved.append(
                {
                    "kind": f"{runtime}-runtime",
                    "detail": f"Detected {runtime} runtime evidence is ambiguous or "
                    f"incompatible; select one with --{runtime}-runtime",
                }
            )

    react_enabled = bool(get(desired, "stacks", "react", "enabled", default=False))
    if react_enabled:
        roots = inspection["stacks"]["react"]["source_roots"]
        selected_react_root = react_directory or (roots[0] if len(roots) == 1 else None)
        if selected_react_root is not None:
            react_root = selected_react_root
            source_root = "src" if react_root == "." else f"{react_root}/src"
            set_nested(desired, ("stacks", "react", "directory"), react_root)
            set_nested(desired, ("ui_quality", "frontend", "root"), react_root)
            set_nested(
                desired,
                ("ui_quality", "frontend", "source_root"),
                source_root,
            )
        detected_managers = {
            item["manager"]
            for item in inspection["package_managers"]
            if item["root"]
            in ([selected_react_root] if selected_react_root is not None else roots)
        }
        selected_manager = package_manager or (
            next(iter(detected_managers)) if len(detected_managers) == 1 else None
        )
        if selected_manager:
            if selected_manager not in {"npm", "pnpm", "yarn"}:
                raise SetupError(
                    f"Unsupported React package manager: {selected_manager}"
                )
            set_nested(
                desired,
                ("stacks", "react", "package_manager"),
                selected_manager,
            )
        set_nested(desired, ("ui_quality", "enabled"), True)
        set_nested(desired, ("user_facing_errors", "enabled"), True)
        set_nested(desired, ("user_facing_errors", "frontend", "enabled"), True)
    elif "react" in disable:
        set_nested(desired, ("ui_quality", "enabled"), False)
        set_nested(desired, ("user_facing_errors", "frontend", "enabled"), False)

    dotnet_solutions = [
        item["path"]
        for item in inspection["stacks"]["dotnet"]["evidence"]
        if item["kind"] == "dotnet-solution"
    ]
    dotnet_tests = [
        item["path"]
        for item in inspection["stacks"]["dotnet"]["evidence"]
        if item["kind"] == "dotnet-project" and "test" in item["path"].lower()
    ]
    if get(desired, "stacks", "dotnet", "enabled", default=False):
        if dotnet_solution is not None:
            set_nested(desired, ("stacks", "dotnet", "solution"), dotnet_solution)
        elif len(dotnet_solutions) == 1:
            set_nested(desired, ("stacks", "dotnet", "solution"), dotnet_solutions[0])
        if dotnet_test_project is not None:
            set_nested(
                desired,
                ("stacks", "dotnet", "test_project"),
                dotnet_test_project,
            )
        elif len(dotnet_tests) == 1:
            set_nested(desired, ("stacks", "dotnet", "test_project"), dotnet_tests[0])
        if not get(desired, "stacks", "dotnet", "test_project", default=""):
            unresolved.append(
                {
                    "kind": "dotnet-test-project",
                    "detail": "Select a .NET test project before bootstrap",
                }
            )

    gates = gate_values or {}
    for gate, command in gates.items():
        if gate not in GATE_NAMES:
            raise SetupError(f"Unsupported quality gate: {gate}")
        if any(ord(character) < 32 for character in command) or len(command) > 2_000:
            raise SetupError(
                f"Quality gate command is not a bounded single line: {gate}"
            )
        set_nested(desired, ("quality_gates", "commands", gate), command)

    try:
        bootstrap_tool.validate_config(desired)
    except SystemExit as error:
        raise SetupError(f"Planned configuration is invalid: {error}", 3) from error

    catalog = load_catalog(root)
    catalog_controls = {
        item["id"]: item for item in catalog["controls"] if isinstance(item, dict)
    }
    immutable = {
        item["id"]
        for item in catalog.get("immutable_floor", [])
        if isinstance(item, dict)
    }
    requested_policy = dict(policy_values or {})
    forbidden = immutable & set(requested_policy)
    if forbidden:
        raise SetupError(
            "Immutable safety controls cannot be configured: "
            + ", ".join(sorted(forbidden))
        )
    unknown = set(requested_policy) - set(catalog_controls)
    if unknown:
        raise SetupError("Unknown policy control(s): " + ", ".join(sorted(unknown)))

    exception_values = temporary_exceptions or {}
    unknown_exceptions = set(exception_values) - set(catalog_controls)
    if unknown_exceptions:
        raise SetupError(
            "Unknown temporary-exception control(s): "
            + ", ".join(sorted(unknown_exceptions))
        )
    existing_exceptions = profile_exceptions(root)
    if mode == "defaults" and exception_values:
        raise SetupError(
            "Temporary exceptions are incompatible with --policy-mode defaults; "
            "use recommended or custom so the relaxation remains explicit."
        )
    exceptions: dict[str, dict[str, str]] = (
        {}
        if mode == "defaults"
        else {
            control_id: dict(value)
            for control_id, value in existing_exceptions.items()
            if control_id not in requested_policy
        }
    )
    if exception_values:
        if not exception_owner or not exception_owner.strip():
            raise SetupError("Temporary exceptions require --exception-owner")
        if not exception_review_date:
            raise SetupError("Temporary exceptions require --exception-review-date")
        try:
            review_date = date.fromisoformat(exception_review_date)
        except ValueError as error:
            raise SetupError("--exception-review-date must use YYYY-MM-DD") from error
        if review_date < date.today():
            raise SetupError("Temporary exception review date must not be in the past")
        if not exception_follow_up or not exception_follow_up.strip():
            raise SetupError("Temporary exceptions require --exception-follow-up")
        normalized_owner = validate_project_text(
            exception_owner, "temporary exception owner"
        )
        normalized_follow_up = validate_project_text(
            exception_follow_up, "temporary exception follow-up"
        )
        for control_id, value in exception_values.items():
            if value not in catalog_controls[control_id]["allowed"]:
                raise SetupError(
                    f"Unsupported temporary exception {control_id}={value}"
                )
            if control_id in requested_policy:
                raise SetupError(
                    f"{control_id} cannot be both a policy answer and exception"
                )
            requested_policy[control_id] = value
            policy_rationales = dict(policy_rationales or {})
            policy_rationales[control_id] = (
                f"Temporary exception owned by {normalized_owner} until "
                f"{exception_review_date}: {normalized_follow_up}"
            )
            exceptions[control_id] = {
                "value": value,
                "owner": normalized_owner,
                "review_date": exception_review_date,
                "follow_up": normalized_follow_up,
                "scope": "repository",
            }
    for control_id, exception in exceptions.items():
        review = exception.get("review_date")
        try:
            expired = (
                not isinstance(review, str) or date.fromisoformat(review) < date.today()
            )
        except ValueError:
            expired = True
        if expired:
            raise SetupError(
                f"Temporary exception {control_id} is expired or malformed; "
                "renew it with --temporary-exception or resolve it with --policy.",
                3,
            )

    existing_controls = profile_controls(root)
    decisions: dict[str, dict[str, str]] = {}
    policy_rationales = policy_rationales or {}
    for control_id, control in catalog_controls.items():
        allowed = [str(item) for item in control["allowed"]]
        default = str(control["default"])
        requested = requested_policy.get(control_id)
        if requested is None and control_id in exceptions:
            requested = exceptions[control_id].get("value")
        if requested == "skip":
            prior = existing_controls.get(control_id)
            selected_value = (prior.get("value") or default) if prior else default
            decisions[control_id] = {
                "value": selected_value,
                "source": "skipped",
                "rationale": "Question skipped; retained existing value or template default.",
                "scope": "repository",
            }
            unresolved.append(
                {
                    "kind": f"policy:{control_id}",
                    "detail": "Policy question skipped; no relaxation was inferred",
                }
            )
            continue
        if requested in {"recommended", "delegate"}:
            selected_value, selected_rationale = recommended_policy(
                control_id, inspection
            )
            decision_source = "assistant-recommendation"
        elif requested == "default":
            selected_value = default
            decision_source = "template-default"
            selected_rationale = "Explicitly retained the versioned template default."
        elif requested is not None:
            selected_value = requested
            decision_source = (
                "temporary-exception"
                if control_id in exceptions
                else "explicit-user-choice"
            )
            selected_rationale = policy_rationales.get(
                control_id,
                existing_controls.get(control_id, {}).get("rationale", ""),
            )
        elif mode == "recommended":
            selected_value, selected_rationale = recommended_policy(
                control_id, inspection
            )
            decision_source = "assistant-recommendation"
        elif mode == "custom":
            prior = existing_controls.get(control_id)
            selected_value = (prior.get("value") or default) if prior else default
            decision_source = "existing-choice" if prior else "template-default"
            selected_rationale = (
                prior.get("rationale", "Retained existing decision")
                if prior
                else "No custom answer supplied; retained the safe template default."
            )
            unresolved.append(
                {
                    "kind": f"policy:{control_id}",
                    "detail": "Custom decision not supplied; safe current/default value retained",
                }
            )
        else:
            selected_value = default
            decision_source = "template-default"
            selected_rationale = "Applied the complete versioned template baseline."
        if selected_value not in allowed:
            raise SetupError(
                f"Unsupported value for {control_id}: {selected_value}; "
                f"allowed: {allowed}"
            )
        selected_rationale = validate_project_text(
            selected_rationale, f"policy rationale for {control_id}"
        )
        default_index = allowed.index(default)
        relaxed = allowed.index(selected_value) > default_index
        if (
            requested is not None
            and relaxed
            and control.get("relaxation_requires_rationale")
            and not selected_rationale.strip()
        ):
            raise SetupError(
                f"Relaxing {control_id} to {selected_value} requires "
                f"--policy-rationale {control_id}=TEXT"
            )
        decisions[control_id] = {
            "value": selected_value,
            "source": decision_source,
            "rationale": selected_rationale,
            "scope": "repository",
        }

    risk = risk_profile(inspection) if mode == "recommended" else "unassessed"
    profile_text = render_profile(mode, risk, decisions, exceptions)
    config_text = render_yaml(desired)
    block = managed_policy_block(mode, risk, decisions, exceptions)
    desired_files = {
        CONFIG_PATH: config_text,
        PROFILE_PATH: profile_text,
    }
    quality_path = contained_path(root, QUALITY_PATH)
    if quality_path.is_file():
        desired_files[QUALITY_PATH] = replace_managed(
            read_bounded_text(quality_path), block
        )
    security_path = contained_path(root, SECURITY_PATH)
    if security_path.is_file():
        security_text = read_bounded_text(security_path)
        if security_contact is not None:
            security_text = update_security_contact(security_text, security_contact)
        desired_files[SECURITY_PATH] = replace_managed(security_text, block)
    elif security_contact is not None:
        raise SetupError(f"Required security document is missing: {SECURITY_PATH}", 3)
    context_values = context_values or {}
    if context_values:
        context_path = contained_path(root, CONTEXT_PATH)
        if not context_path.is_file():
            raise SetupError(f"Required project context is missing: {CONTEXT_PATH}", 3)
        desired_files[CONTEXT_PATH] = update_context_fields(
            read_bounded_text(context_path), context_values
        )

    resolved_readiness = {
        CONTEXT_FIELDS[key] for key in context_values if key in CONTEXT_FIELDS
    }
    if get(desired, "project", "name", default="CHANGE_ME") != "CHANGE_ME":
        resolved_readiness.add("project.name")
    if security_contact is not None:
        resolved_readiness.add("security reporting contact")
    existing_unresolved_kinds = {item["kind"] for item in unresolved}
    for field in inspection["readiness"]["incomplete_fields"]:
        marker = field["marker"]
        kind = f"readiness:{marker}"
        if marker not in resolved_readiness and kind not in existing_unresolved_kinds:
            unresolved.append(
                {
                    "kind": kind,
                    "detail": f"{field['path']}: {marker} remains incomplete",
                }
            )

    before_flat = flatten(current)
    after_flat = flatten(desired)
    changes: list[dict[str, object]] = []
    explicit_fields = {
        field
        for field, supplied in (
            ("project.name", project_name),
            ("runtimes.python", python_runtime),
            ("runtimes.node", node_runtime),
            ("stacks.python.directory", python_directory),
            ("stacks.react.directory", react_directory),
            ("stacks.react.package_manager", package_manager),
            ("stacks.dotnet.solution", dotnet_solution),
            ("stacks.dotnet.test_project", dotnet_test_project),
        )
        if supplied is not None
    }
    for key in sorted(set(before_flat) | set(after_flat)):
        before = before_flat.get(key)
        after = after_flat.get(key)
        if before == after:
            continue
        explicit = key in explicit_fields or (
            len(key.split(".")) > 1
            and key.split(".")[0] == "stacks"
            and key.split(".")[1] in (enable | disable)
        )
        material = (key.endswith(".enabled") and after is False) or key.startswith(
            "quality_gates."
        )
        changes.append(
            {
                "field": key,
                "before": before,
                "after": after,
                "source": (
                    "explicit-user-choice"
                    if explicit or key.startswith("quality_gates.")
                    else "assistant-recommendation"
                ),
                "material": material,
                "rationale": (
                    "Explicitly requested desired state"
                    if explicit
                    else "Coupled or evidence-based configuration reconciliation"
                ),
            }
        )
    if context_values:
        context_text = read_bounded_text(contained_path(root, CONTEXT_PATH))
        for key, raw_value in sorted(context_values.items()):
            label = CONTEXT_FIELDS.get(key, key)
            match = re.search(rf"(?m)^-\s*{re.escape(label)}:\s*(.*)$", context_text)
            changes.append(
                {
                    "field": f"context.{key}",
                    "before": match.group(1).strip() if match else None,
                    "after": validate_project_text(raw_value, f"context.{key}"),
                    "source": "explicit-user-choice",
                    "material": False,
                    "rationale": "Approved project-specific readiness fact",
                }
            )
    if security_contact is not None:
        changes.append(
            {
                "field": "security.reporting_contact",
                "before": (
                    "incomplete"
                    if "CHANGE_ME_SECURITY_CONTACT" in read_bounded_text(security_path)
                    else "configured"
                ),
                "after": "configured",
                "source": "explicit-user-choice",
                "material": False,
                "rationale": "Approved private vulnerability reporting route",
            }
        )
    for control_id, decision in sorted(decisions.items()):
        before = existing_controls.get(control_id, {}).get("value")
        if before != decision["value"]:
            allowed = catalog_controls[control_id]["allowed"]
            default = catalog_controls[control_id]["default"]
            relaxed = allowed.index(decision["value"]) > allowed.index(default)
            changes.append(
                {
                    "field": f"policy.{control_id}",
                    "before": before,
                    "after": decision["value"],
                    "source": decision["source"],
                    "material": relaxed,
                    "rationale": decision["rationale"],
                }
            )
    for control_id in sorted(set(existing_exceptions) | set(exceptions)):
        planned_exception = exceptions.get(control_id)
        if existing_exceptions.get(control_id) != planned_exception:
            changes.append(
                {
                    "field": f"temporary_exception.{control_id}",
                    "before": existing_exceptions.get(control_id),
                    "after": planned_exception,
                    "source": (
                        "template-default"
                        if planned_exception is None
                        else "explicit-user-choice"
                    ),
                    "material": True,
                    "rationale": (
                        "Removed the temporary relaxation to apply the complete "
                        "versioned template baseline"
                        if planned_exception is None
                        else "Time-bounded exception with owner, review date, and follow-up"
                    ),
                }
            )

    file_changes = []
    for relative_path, content in sorted(desired_files.items()):
        target = contained_path(root, relative_path)
        before_hash = current_digest(target)
        after_hash = digest_bytes(content.encode("utf-8"))
        if before_hash != after_hash:
            file_changes.append(
                {
                    "path": relative_path,
                    "base_sha256": before_hash,
                    "content": content,
                    "result_sha256": after_hash,
                }
            )

    bootstrap_operations: list[dict[str, object]] = []
    project_file_mutations: list[dict[str, object]] = []
    project_dependencies: dict[str, list[str]] = {}
    for path, action, condition in (
        (
            "README.md",
            "create the generated project README",
            "only when README.md is missing; preserve an existing README",
        ),
        (
            ".ai/config/project.defaults.env",
            "rewrite generated quality-gate defaults from approved configuration",
            "when configure bootstrap is selected",
        ),
        (
            ".ai/PROJECT_CONTEXT.md",
            "rewrite the managed bootstrap-configuration summary",
            "when configure bootstrap is selected",
        ),
        (
            ".ai/NEXT_STEPS.md",
            "replace the seeded bootstrap task with project-readiness follow-ups",
            "only while the seeded bootstrap instruction is present",
        ),
        (
            ".ai/DECISIONS.md",
            "create the operational-decisions scaffold",
            "only when the file is missing",
        ),
        (
            ".idea",
            "create the local IntelliJ project-state directory",
            "only when the directory is missing",
        ),
        (
            ".idea/vcs.xml",
            "rewrite the local IntelliJ VCS mapping",
            "when configure bootstrap is selected",
        ),
    ):
        project_file_mutations.append(
            project_mutation_preview(
                root,
                stack="configure",
                path=path,
                action=action,
                condition=condition,
            )
        )
    project_file_mutations.append(
        project_mutation_preview(
            root,
            stack="configure",
            path=".ai/tools",
            action="make the exact previewed set of shell tools executable",
            condition="when configure bootstrap is selected",
            glob="*.sh",
        )
    )
    if get(desired, "stacks", "python", "enabled", default=False):
        python_version = str(get(desired, "runtimes", "python"))
        python_directory_value = str(
            get(desired, "stacks", "python", "directory", default="backend")
        )
        python_package_target = contained_project_path(root, python_directory_value)
        scaffold_python_package = not python_package_target.exists()
        python_package_name = Path(python_directory_value).name
        python_dependencies = list(bootstrap_tool.PYTHON_DEV_DEPENDENCIES)
        project_dependencies["python"] = python_dependencies
        bootstrap_operations.extend(
            [
                {
                    "stack": "python",
                    "cwd": ".",
                    "argv": [
                        "uv",
                        "init",
                        "--python",
                        python_version,
                        "--bare",
                        "--no-workspace",
                        "--no-pin-python",
                        ".",
                    ],
                    "condition": "only when pyproject.toml is missing",
                },
                {
                    "stack": "python",
                    "cwd": ".",
                    "argv": [
                        "uv",
                        "add",
                        "--python",
                        python_version,
                        "--dev",
                        *python_dependencies,
                    ],
                    "condition": "only for pinned development dependencies not already declared",
                },
            ]
        )
        python_mutations = [
            (
                python_directory_value,
                "create the explicitly approved Python package directory",
                "only when the configured target is missing",
            ),
            (
                "pyproject.toml",
                "create or update Python metadata and development dependencies"
                + (
                    f", including setuptools discovery for {python_directory_value}"
                    if scaffold_python_package
                    else "; preserve existing package-discovery choices"
                ),
                "when missing metadata or dependencies require reconciliation",
            ),
            (
                "uv.lock",
                "create or update the uv lockfile",
                "when uv resolves or synchronizes dependencies",
            ),
            (
                ".venv",
                "create or update the project-local Python environment",
                "when uv resolves or synchronizes dependencies",
            ),
        ]
        if scaffold_python_package:
            python_mutations.append(
                (
                    "tests",
                    "create the Python test directory",
                    "only when the configured package target is missing",
                )
            )
            python_mutations.append(
                (
                    f"{python_directory_value}/__init__.py",
                    "create the explicitly approved package initializer",
                    "only because the configured package target is missing",
                )
            )
            smoke_path = f"tests/test_{python_package_name}.py"
            if not contained_project_path(root, smoke_path).exists():
                python_mutations.append(
                    (
                        smoke_path,
                        f"create an import smoke test for {python_package_name}",
                        "only because both the configured package target and "
                        "smoke test are missing",
                    )
                )
        for path, action, condition in python_mutations:
            project_file_mutations.append(
                project_mutation_preview(
                    root,
                    stack="python",
                    path=path,
                    action=action,
                    condition=condition,
                )
            )
    if get(desired, "stacks", "react", "enabled", default=False):
        directory = str(
            get(desired, "stacks", "react", "directory", default="frontend")
        )
        manager = str(get(desired, "stacks", "react", "package_manager", default="npm"))
        create, install, add_dev = bootstrap_tool.package_manager_commands(
            manager,
            directory,
            bootstrap_tool.REACT_TEMPLATE,
            bootstrap_tool.VITE_VERSION,
        )
        react_dependencies = list(bootstrap_tool.REACT_QUALITY_DEPENDENCIES)
        project_dependencies["react"] = react_dependencies
        bootstrap_operations.extend(
            [
                {
                    "stack": "react",
                    "cwd": ".",
                    "argv": create,
                    "condition": "only when the configured frontend directory is missing",
                },
                {
                    "stack": "react",
                    "cwd": directory,
                    "argv": install,
                    "condition": "when React bootstrap is selected",
                },
                {
                    "stack": "react",
                    "cwd": directory,
                    "argv": [*add_dev, *react_dependencies],
                    "condition": "only for pinned quality dependencies not already declared",
                },
            ]
        )
        package_path = f"{directory}/package.json"
        package_target = contained_project_path(root, package_path)
        existing_script_names: list[str] = []
        missing_script_names = [
            "format",
            "format:check",
            "typecheck",
            "test",
            "test:watch",
        ]
        if package_target.is_file():
            package_data = json.loads(read_bounded_text(package_target))
            package_scripts = package_data.get("scripts", {})
            if isinstance(package_scripts, dict):
                existing_script_names = sorted(
                    name for name in missing_script_names if name in package_scripts
                )
                missing_script_names = [
                    name for name in missing_script_names if name not in package_scripts
                ]
        lock_name = {
            "npm": "package-lock.json",
            "pnpm": "pnpm-lock.yaml",
            "yarn": "yarn.lock",
        }[manager]
        react_mutations = [
            (
                directory,
                "create the complete pinned Vite React scaffold tree",
                "only when package.json is missing; preserve an existing "
                "application tree",
            ),
            (
                package_path,
                "preserve existing scripts"
                + (
                    f" ({', '.join(existing_script_names)})"
                    if existing_script_names
                    else ""
                )
                + (
                    "; add only missing quality scripts "
                    f"({', '.join(missing_script_names)})"
                    if missing_script_names
                    else "; no quality-script replacement"
                )
                + "; add missing pinned development dependencies and package-manager metadata",
                "when React bootstrap is selected",
            ),
            (
                f"{directory}/{lock_name}",
                f"create or update the {manager} lockfile",
                "when dependencies are installed or synchronized",
            ),
            (
                f"{directory}/node_modules",
                "create or update project-local JavaScript dependency state",
                "when the selected package manager uses node_modules",
            ),
            (
                f"{directory}/src/test/setup.ts",
                "create the Vitest DOM setup",
                "only when the file is missing",
            ),
            (
                f"{directory}/src/App.test.tsx",
                "create the application smoke test",
                "only when the file is missing",
            ),
            (
                f"{directory}/vitest.config.ts",
                "create the Vitest configuration",
                "only when the file is missing",
            ),
        ]
        if manager == "yarn":
            react_mutations.extend(
                [
                    (
                        f"{directory}/.yarn",
                        "create or update project-local Yarn state",
                        "when required by the configured Yarn linker",
                    ),
                    (
                        f"{directory}/.pnp.cjs",
                        "create or update Yarn Plug'n'Play resolution state",
                        "when the configured Yarn linker uses Plug'n'Play",
                    ),
                    (
                        f"{directory}/.pnp.loader.mjs",
                        "create or update the Yarn Plug'n'Play loader",
                        "when the configured Yarn linker requires it",
                    ),
                ]
            )
        for path, action, condition in react_mutations:
            project_file_mutations.append(
                project_mutation_preview(
                    root,
                    stack="react",
                    path=path,
                    action=action,
                    condition=condition,
                )
            )

    plan: dict[str, Any] = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "policy_catalog_schema": catalog["schema_version"],
        "policy_catalog_sha256": current_digest(
            root / ".ai/policies/setup-controls.json"
        ),
        "policy_mode": mode,
        "inspection": inspection,
        "inspection_sha256": inspection_digest(inspection),
        "changes": changes,
        "file_changes": file_changes,
        "unresolved": unresolved,
        "cleanup_recommendations": [
            {
                "stack": stack,
                "status": "not-applied",
                "detail": "Review obsolete generated tooling separately; setup "
                "never deletes application source, manifests, lockfiles, or "
                "project documentation.",
            }
            for stack in sorted(disable)
        ],
        "follow_up_preview": {
            "configuration_command": (
                "python .ai/tools/bootstrap.py --steps configure --no-install"
            ),
            "project_local_dependency_operations": bootstrap_operations,
            "project_file_mutations": project_file_mutations,
            "project_local_dependencies": project_dependencies,
            "missing_global_prerequisites": inspection["missing_tools"],
            "verification_command": "./.ai/tools/verify.sh",
            "network_required_only_when_installation_is_approved": bool(
                bootstrap_operations
            ),
        },
        "approval": {
            "required": True,
            "material_changes": [item["field"] for item in changes if item["material"]],
        },
    }
    plan["plan_id"] = digest_bytes(stable_json(plan).encode("utf-8"))[:20]
    return plan


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.setup-", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextlib.contextmanager
def setup_lock(root: Path) -> Iterator[None]:
    lock = root / LOCK_PATH
    if lock.parent.is_symlink():
        raise SetupError("Setup lock parent must not be a symbolic link", 3)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise SetupError(
            "Another setup apply may be active. If no setup process is running, "
            f"remove {LOCK_PATH} and retry.",
            3,
        ) from error
    identity = os.fstat(descriptor)
    try:
        os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        yield
    finally:
        os.close(descriptor)
        try:
            current = lock.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                lock.unlink()
        except FileNotFoundError:
            pass


def apply_file_changes(root: Path, plan: dict[str, Any]) -> list[str]:
    changes = plan.get("file_changes")
    if not isinstance(changes, list):
        raise SetupError("Plan file_changes must be a list")
    if len(changes) > len(SETUP_OWNED_PATHS):
        raise SetupError("Plan contains too many setup-owned file changes")
    prepared: list[tuple[Path, bytes, bytes | None]] = []
    seen_paths: set[str] = set()
    for change in changes:
        if not isinstance(change, dict):
            raise SetupError("Plan contains an invalid file change")
        relative_path = change.get("path")
        content = change.get("content")
        if not isinstance(relative_path, str) or not isinstance(content, str):
            raise SetupError("Plan file change is missing path or content")
        if relative_path in seen_paths:
            raise SetupError(f"Plan targets a setup-owned file twice: {relative_path}")
        seen_paths.add(relative_path)
        target = contained_path(root, relative_path)
        expected_base = change.get("base_sha256")
        if current_digest(target) != expected_base:
            raise SetupError(
                f"Setup-owned file changed after planning: {relative_path}; "
                "create a new plan.",
                3,
            )
        encoded = content.encode("utf-8")
        if len(encoded) > SCAN_BYTE_LIMIT:
            raise SetupError(
                f"Planned file exceeds {SCAN_BYTE_LIMIT} bytes: {relative_path}"
            )
        if digest_bytes(encoded) != change.get("result_sha256"):
            raise SetupError(f"Plan content digest is invalid: {relative_path}")
        prepared.append(
            (target, encoded, target.read_bytes() if target.is_file() else None)
        )

    applied: list[tuple[Path, bytes | None, str]] = []
    try:
        for target, content, backup in prepared:
            atomic_write(target, content)
            applied.append((target, backup, digest_bytes(content)))
    except OSError as error:
        for target, backup, written_digest in reversed(applied):
            try:
                if current_digest(target) != written_digest:
                    continue
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write(target, backup)
            except OSError:
                pass
        raise SetupError(f"Atomic setup apply failed and was rolled back: {error}", 4)
    return [target.relative_to(root).as_posix() for target, _, _ in prepared]


def validate_plan(plan: dict[str, Any], approval: str) -> None:
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise SetupError("Unsupported setup plan schema")
    supplied_id = plan.get("plan_id")
    if not isinstance(supplied_id, str) or supplied_id != approval:
        raise SetupError("Approval must exactly match the plan_id")
    unsigned = dict(plan)
    del unsigned["plan_id"]
    expected = digest_bytes(stable_json(unsigned).encode("utf-8"))[:20]
    if supplied_id != expected:
        raise SetupError("Plan identifier does not match the plan content")


def normalize_bootstrap_steps(value: str) -> tuple[str, ...]:
    parts = [item.strip() for item in value.split(",")]
    if not parts or any(not item for item in parts):
        raise SetupError(
            "--bootstrap-steps must be none, all, or a comma-separated subset "
            "of configure, python, and react"
        )
    selected = set(parts)
    if selected == {"none"}:
        return ()
    if selected == {"all"}:
        return BOOTSTRAP_STEP_ORDER
    if selected & {"none", "all"}:
        raise SetupError(
            "--bootstrap-steps none/all cannot be combined with individual steps"
        )
    unknown = selected - set(BOOTSTRAP_STEP_ORDER)
    if unknown:
        raise SetupError("Unknown bootstrap step(s): " + ", ".join(sorted(unknown)))
    return tuple(step for step in BOOTSTRAP_STEP_ORDER if step in selected)


def validate_followup_bases(
    root: Path, plan: dict[str, Any], selected_steps: tuple[str, ...]
) -> None:
    """Bind selected application mutations to the exact approved file bases."""
    selected = set(selected_steps)
    if not selected:
        return
    mutations = plan.get("follow_up_preview", {}).get("project_file_mutations")
    if not isinstance(mutations, list):
        raise SetupError("Plan is missing the project-file bootstrap preview")
    for mutation in mutations:
        if not isinstance(mutation, dict) or mutation.get("stack") not in selected:
            continue
        path = mutation.get("path")
        if not isinstance(path, str):
            raise SetupError("Plan contains an invalid project-file mutation")
        target = contained_project_path(root, path)
        expected_state = mutation.get("base_state")
        if not isinstance(expected_state, str):
            raise SetupError(
                f"Plan mutation is missing its filesystem state binding: {path}"
            )
        if current_path_state(target) != expected_state:
            raise SetupError(
                f"Bootstrap target changed after planning: {path}; create a new plan.",
                3,
            )
        if current_digest(target) != mutation.get("base_sha256"):
            raise SetupError(
                f"Bootstrap target changed after planning: {path}; create a new plan.",
                3,
            )
        if current_mode(target) != mutation.get("base_mode"):
            raise SetupError(
                f"Bootstrap target mode changed after planning: {path}; "
                "create a new plan.",
                3,
            )
        glob = mutation.get("glob")
        if glob is not None:
            if not isinstance(glob, str) or not isinstance(
                mutation.get("base_members"), list
            ):
                raise SetupError(f"Plan contains an invalid glob binding: {path}")
            current = project_mutation_preview(
                root,
                stack=str(mutation["stack"]),
                path=path,
                action="validation",
                condition="validation",
                glob=glob,
            )
            if current["base_members"] != mutation["base_members"]:
                raise SetupError(
                    f"Bootstrap target members changed after planning: {path}; "
                    "create a new plan.",
                    3,
                )


def run_followup(
    root: Path,
    *,
    selected_steps: tuple[str, ...],
    no_install: bool,
    verify: bool,
) -> dict[str, object]:
    result: dict[str, object] = {"bootstrap": "skipped", "verification": "skipped"}
    if selected_steps:
        command = [
            sys.executable,
            os.fspath(root / ".ai/tools/bootstrap.py"),
            "--steps",
            ",".join(selected_steps),
        ]
        if no_install:
            command.append("--no-install")
        completed = subprocess.run(  # nosec B603
            command, cwd=root, check=False, text=True, capture_output=True
        )
        if completed.stdout:
            print(completed.stdout, file=sys.stderr, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        if completed.returncode != 0:
            raise SetupError(
                "Configuration was applied, but bootstrap failed. Resume with: "
                + " ".join(command),
                4,
            )
        result["bootstrap"] = "passed"
    if verify:
        bash = shutil.which("bash")
        if bash is None:
            raise SetupError(
                "Configuration was applied, but verification needs bash. Install "
                "Git Bash/WSL or run ./.ai/tools/verify.sh on a supported host.",
                4,
            )
        command = [bash, os.fspath(root / ".ai/tools/verify.sh")]
        completed = subprocess.run(  # nosec B603
            command, cwd=root, check=False, text=True, capture_output=True
        )
        if completed.stdout:
            print(completed.stdout, file=sys.stderr, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        if completed.returncode != 0:
            raise SetupError(
                "Configuration was applied, but verification failed. Resume with "
                "./.ai/tools/verify.sh after resolving the reported failures.",
                4,
            )
        result["verification"] = "passed"
    return result


def apply_plan(
    root: Path,
    plan: dict[str, Any],
    approval: str,
    *,
    bootstrap_steps: str = "none",
    no_install: bool = False,
    verify: bool = False,
) -> dict[str, object]:
    validate_plan(plan, approval)
    selected_steps = normalize_bootstrap_steps(bootstrap_steps)
    resolved_root = root.resolve()
    with setup_lock(resolved_root):
        catalog = load_catalog(resolved_root)
        if plan.get("policy_catalog_schema") != catalog.get("schema_version"):
            raise SetupError(
                "Policy catalog changed after planning; create a new plan.", 3
            )
        if plan.get("policy_catalog_sha256") != current_digest(
            resolved_root / ".ai/policies/setup-controls.json"
        ):
            raise SetupError(
                "Policy catalog changed after planning; create a new plan.", 3
            )
        current_inspection = inspect_repository(resolved_root)
        if inspection_digest(current_inspection) != plan.get("inspection_sha256"):
            raise SetupError(
                "Material project evidence changed after planning; create a new plan.",
                3,
            )
        validate_followup_bases(resolved_root, plan, selected_steps)
        applied = apply_file_changes(resolved_root, plan)
        followup = run_followup(
            resolved_root,
            selected_steps=selected_steps,
            no_install=no_install,
            verify=verify,
        )
    return {
        "status": "applied" if applied else "no-op",
        "plan_id": approval,
        "applied": applied,
        "skipped": [
            item["detail"] for item in plan.get("unresolved", []) if "detail" in item
        ],
        "blocked": [],
        **followup,
    }


def doctor(root: Path) -> tuple[dict[str, Any], int]:
    inspection = inspect_repository(root)
    findings: list[dict[str, str]] = []
    if (root / LOCK_PATH).exists() or (root / LOCK_PATH).is_symlink():
        findings.append(
            {
                "severity": "blocking",
                "code": "setup-lock-present",
                "detail": "A setup apply may be active. If no setup process is "
                f"running, remove {LOCK_PATH} and rerun doctor.",
            }
        )
    if not inspection["configuration"]["valid"]:
        findings.append(
            {
                "severity": "blocking",
                "code": "invalid-configuration",
                "detail": str(inspection["configuration"]["error"]),
            }
        )
    if inspection["conflicts"]:
        findings.extend(
            {
                "severity": "blocking",
                "code": item["kind"],
                "detail": item["detail"],
            }
            for item in inspection["conflicts"]
        )
    if inspection["generated_defaults_stale"]:
        findings.append(
            {
                "severity": "incomplete",
                "code": "stale-generated-defaults",
                "detail": "Run python .ai/tools/setup.py plan, apply it, then "
                "resume bootstrap with --steps configure --no-install.",
            }
        )
    findings.extend(
        {
            "severity": "incomplete",
            "code": "missing-prerequisite",
            "detail": item["instruction"],
        }
        for item in inspection["missing_tools"]
    )
    findings.extend(
        {
            "severity": "incomplete",
            "code": "readiness-field",
            "detail": f"{item['path']}: {item['marker']}",
        }
        for item in inspection["readiness"]["incomplete_fields"]
    )
    try:
        exceptions = profile_exceptions(root)
    except SetupError as error:
        findings.append(
            {
                "severity": "blocking",
                "code": "invalid-policy-profile",
                "detail": str(error),
            }
        )
        exceptions = {}
    for control_id, exception in exceptions.items():
        review = exception.get("review_date")
        try:
            expired = (
                not isinstance(review, str) or date.fromisoformat(review) < date.today()
            )
        except ValueError:
            expired = True
        if expired:
            findings.append(
                {
                    "severity": "blocking",
                    "code": "expired-temporary-exception",
                    "detail": f"{control_id} must be reviewed before setup is ready",
                }
            )
    status = (
        "blocked"
        if any(item["severity"] == "blocking" for item in findings)
        else "incomplete"
        if findings
        else "ready"
    )
    return {"schema_version": 1, "status": status, "findings": findings}, (
        3 if status == "blocked" else 0
    )


def write_plan(path: Path, plan: dict[str, Any]) -> None:
    atomic_write(path, (stable_json(plan, pretty=True) + "\n").encode("utf-8"))


def resolve_plan_output(root: Path, requested: Path) -> Path:
    output = requested if requested.is_absolute() else root / requested
    resolved = output.resolve(strict=False)
    try:
        relative_output = resolved.relative_to(root.resolve())
    except ValueError as error:
        raise SetupError("Plan output must stay below the repository root") from error
    allowed = relative_output == Path(".ai/setup-plan.json") or (
        len(relative_output.parts) >= 3
        and relative_output.parts[:2] == (".ai", "setup")
        and relative_output.suffix == ".json"
    )
    if not allowed:
        raise SetupError(
            "Plan output must be .ai/setup-plan.json or a JSON file below .ai/setup/"
        )
    return resolved


def plan_from_arguments(root: Path, arguments: argparse.Namespace) -> dict[str, Any]:
    return build_plan(
        root,
        mode=arguments.policy_mode,
        project_name=arguments.project_name,
        enable_stacks=arguments.enable_stack,
        disable_stacks=arguments.disable_stack,
        package_manager=arguments.package_manager,
        python_directory=arguments.python_directory,
        react_directory=arguments.react_directory,
        python_runtime=arguments.python_runtime,
        node_runtime=arguments.node_runtime,
        gate_values=parse_assignments(arguments.set_gate, "--set-gate"),
        policy_values=parse_assignments(arguments.policy, "--policy"),
        policy_rationales=parse_assignments(
            arguments.policy_rationale, "--policy-rationale"
        ),
        dotnet_solution=arguments.dotnet_solution,
        dotnet_test_project=arguments.dotnet_test_project,
        temporary_exceptions=parse_assignments(
            arguments.temporary_exception, "--temporary-exception"
        ),
        exception_owner=arguments.exception_owner,
        exception_review_date=arguments.exception_review_date,
        exception_follow_up=arguments.exception_follow_up,
        context_values=parse_assignments(arguments.context, "--context"),
        security_contact=arguments.security_contact,
    )


def add_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--policy-mode",
        choices=("defaults", "recommended", "custom"),
        default="recommended",
    )
    parser.add_argument("--project-name")
    parser.add_argument("--enable-stack", action="append", default=[])
    parser.add_argument("--disable-stack", action="append", default=[])
    parser.add_argument(
        "--package-manager", choices=("npm", "pnpm", "yarn"), default=None
    )
    parser.add_argument("--python-directory")
    parser.add_argument("--react-directory")
    parser.add_argument("--python-runtime")
    parser.add_argument("--node-runtime")
    parser.add_argument("--set-gate", action="append", default=[])
    parser.add_argument("--policy", action="append", default=[])
    parser.add_argument("--policy-rationale", action="append", default=[])
    parser.add_argument("--dotnet-solution")
    parser.add_argument("--dotnet-test-project")
    parser.add_argument("--temporary-exception", action="append", default=[])
    parser.add_argument("--exception-owner")
    parser.add_argument("--exception-review-date")
    parser.add_argument("--exception-follow-up")
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--security-contact")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect, plan, apply, and diagnose project template setup.",
        epilog=(
            "Exit codes: 0 successful operation (doctor may still report incomplete); "
            "2 invalid input or approval; 3 conflict, drift, or unsafe inspection "
            "state; 4 apply follow-up/bootstrap/verification failure."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser(
        "inspect", help="Inspect bounded local evidence without executing project code."
    )
    inspect_parser.add_argument("--json", action="store_true")
    plan_parser = subparsers.add_parser(
        "plan", help="Create a deterministic, reviewable desired-state plan."
    )
    add_plan_arguments(plan_parser)
    plan_parser.add_argument("--output", type=Path)
    apply_parser = subparsers.add_parser(
        "apply", help="Atomically apply an exact approved plan."
    )
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--approve", required=True)
    apply_parser.add_argument(
        "--bootstrap-steps",
        default="none",
        help="none, configure, or a comma-separated bootstrap step list",
    )
    apply_parser.add_argument("--no-install", action="store_true")
    apply_parser.add_argument("--verify", action="store_true")
    doctor_parser = subparsers.add_parser(
        "doctor", help="Report setup drift, missing tools, and readiness blockers."
    )
    doctor_parser.add_argument("--json", action="store_true")
    wizard_parser = subparsers.add_parser(
        "wizard", help="Manually guide inspection, preview, approval, and follow-up."
    )
    add_plan_arguments(wizard_parser)
    wizard_parser.add_argument("--yes", action="store_true")
    wizard_parser.add_argument("--no-install", action="store_true")
    wizard_parser.add_argument("--bootstrap-steps", default="configure")
    wizard_parser.add_argument("--verify", action="store_true")
    return parser


def print_inspection_summary(inspection: dict[str, Any]) -> None:
    print("[setup] Detected local project evidence:")
    for stack in STACKS:
        item = inspection["stacks"][stack]
        print(
            f"  - {stack}: {'detected' if item['detected'] else 'not detected'} "
            f"({item['confidence']} confidence)"
        )
    if inspection["ambiguities"]:
        print("[setup] Ambiguities:")
        for item in inspection["ambiguities"]:
            print(f"  - {item['detail']}")
    if inspection["missing_tools"]:
        print("[setup] Missing prerequisites:")
        for item in inspection["missing_tools"]:
            print(f"  - {item['tool']}: {item['instruction']}")


def policy_question_relevant(control_id: str, inspection: dict[str, Any]) -> bool:
    dependencies = bool(inspection["dependency_manifests"])
    network = bool(inspection["applicability"]["network_service"])
    code = any(inspection["stacks"][stack]["detected"] for stack in STACKS)
    python_or_dotnet = any(
        inspection["stacks"][stack]["detected"] for stack in ("python", "dotnet")
    )
    if control_id == "static_security":
        return python_or_dotnet or network
    if control_id == "secret_scanning":
        return dependencies or network or inspection["applicability"]["deployment"]
    if control_id in {
        "dependency_scanning",
        "dependency_vulnerability_threshold",
    }:
        return dependencies
    if control_id == "warning_treatment":
        return code
    if control_id in {"authentication", "availability"}:
        return network
    return False


def run_wizard(root: Path, arguments: argparse.Namespace) -> int:
    inspection = inspect_repository(root)
    print(f"[setup] Policy mode: {arguments.policy_mode}")
    print_inspection_summary(inspection)
    if inspection["conflicts"]:
        raise SetupError(
            "Resolve inspection conflicts before guided setup: "
            + "; ".join(item["detail"] for item in inspection["conflicts"]),
            3,
        )
    if (
        arguments.project_name is None
        and not arguments.yes
        and get(default_config(root), "project", "name", default="CHANGE_ME")
        == "CHANGE_ME"
    ):
        answer = input(
            "Project name (optional; press Enter to leave visibly incomplete): "
        ).strip()
        if answer:
            arguments.project_name = answer
    if not arguments.yes:
        incomplete_markers = {
            item["marker"] for item in inspection["readiness"]["incomplete_fields"]
        }
        supplied_context = set(parse_assignments(arguments.context, "--context"))
        for key, label in CONTEXT_FIELDS.items():
            if key in supplied_context or label not in incomplete_markers:
                continue
            answer = input(
                f"{label} (optional; press Enter to leave visibly incomplete): "
            ).strip()
            if answer:
                arguments.context.append(f"{key}={answer}")
        if (
            arguments.security_contact is None
            and "security reporting contact" in incomplete_markers
        ):
            answer = input(
                "Private security reporting contact (optional; press Enter to "
                "leave visibly incomplete): "
            ).strip()
            if answer:
                arguments.security_contact = answer
        python_roots = inspection["stacks"]["python"]["package_directories"] or [
            item
            for item in inspection["stacks"]["python"]["source_roots"]
            if item != "." and item not in {"test", "tests"}
        ]
        if len(python_roots) > 1 and arguments.python_directory is None:
            answer = input(
                "Python source directory (optional; detected "
                + ", ".join(python_roots)
                + "; press Enter to leave unresolved): "
            ).strip()
            if answer:
                arguments.python_directory = answer
        for runtime in ("python", "node"):
            finding = inspection["runtimes"][runtime]
            argument_name = f"{runtime}_runtime"
            if (
                finding["detected"]
                and finding["value"] is None
                and getattr(arguments, argument_name) is None
            ):
                answer = input(
                    f"{runtime.capitalize()} runtime (optional exact version; "
                    "press Enter to leave unresolved): "
                ).strip()
                if answer:
                    setattr(arguments, argument_name, answer)
        react_roots = inspection["stacks"]["react"]["source_roots"]
        if len(react_roots) > 1 and arguments.react_directory is None:
            answer = input(
                "React root (optional; detected "
                + ", ".join(react_roots)
                + "; press Enter to leave unresolved): "
            ).strip()
            if answer:
                arguments.react_directory = answer
        dotnet_evidence = inspection["stacks"]["dotnet"]["evidence"]
        dotnet_solutions = [
            item["path"]
            for item in dotnet_evidence
            if item["kind"] == "dotnet-solution"
        ]
        dotnet_tests = [
            item["path"]
            for item in dotnet_evidence
            if item["kind"] == "dotnet-project" and "test" in item["path"].lower()
        ]
        if len(dotnet_solutions) > 1 and arguments.dotnet_solution is None:
            answer = input(
                "Dotnet solution (optional; detected "
                + ", ".join(dotnet_solutions)
                + "; press Enter to leave unresolved): "
            ).strip()
            if answer:
                arguments.dotnet_solution = answer
        if len(dotnet_tests) > 1 and arguments.dotnet_test_project is None:
            answer = input(
                "Dotnet test project (optional; detected "
                + ", ".join(dotnet_tests)
                + "; press Enter to leave unresolved): "
            ).strip()
            if answer:
                arguments.dotnet_test_project = answer
        if arguments.policy_mode == "custom":
            supplied = set(parse_assignments(arguments.policy, "--policy"))
            catalog = load_catalog(root)
            for control in catalog["controls"]:
                control_id = control["id"]
                if control_id in supplied or not policy_question_relevant(
                    control_id, inspection
                ):
                    continue
                allowed = ", ".join(control["allowed"])
                answer = input(
                    f"{control_id} ({allowed}; default/recommended/skip; Enter skips): "
                ).strip()
                arguments.policy.append(f"{control_id}={answer if answer else 'skip'}")
                if answer in control["allowed"]:
                    default_index = control["allowed"].index(control["default"])
                    if control["allowed"].index(answer) > default_index:
                        rationale = input(
                            f"Rationale for relaxing {control_id} "
                            "(Enter to skip the relaxation): "
                        ).strip()
                        if rationale:
                            arguments.policy_rationale.append(
                                f"{control_id}={rationale}"
                            )
                        else:
                            arguments.policy[-1] = f"{control_id}=skip"
    if (
        not arguments.yes
        and not arguments.no_install
        and arguments.bootstrap_steps == "configure"
    ):
        answer = (
            input(
                "Also run configured stack scaffolding and project-local dependency "
                "installation after apply? [y/N] "
            )
            .strip()
            .lower()
        )
        if answer in {"y", "yes"}:
            arguments.bootstrap_steps = "all"
    if not arguments.yes and not arguments.verify:
        answer = input("Run full verification after apply? [y/N] ").strip().lower()
        arguments.verify = answer in {"y", "yes"}
    plan = plan_from_arguments(root, arguments)
    print(f"[setup] Plan: {plan['plan_id']}")
    if plan["changes"]:
        for change in plan["changes"]:
            material = " [material]" if change["material"] else ""
            print(
                f"  - {change['field']}: {change['before']!r} -> "
                f"{change['after']!r} ({change['source']}){material}"
            )
    else:
        print("  - No desired-state changes.")
    if plan["file_changes"]:
        print("[setup] Setup-owned files in the exact approved write set:")
        for file_change in plan["file_changes"]:
            print(f"  - {file_change['path']} -> sha256:{file_change['result_sha256']}")
    if plan["unresolved"]:
        print("[setup] Skipped or unresolved:")
        for item in plan["unresolved"]:
            print(f"  - {item['detail']}")
    if plan["cleanup_recommendations"]:
        print("[setup] Separate cleanup recommendations (not applied):")
        for item in plan["cleanup_recommendations"]:
            print(f"  - {item['stack']}: {item['detail']}")
    operations = plan["follow_up_preview"]["project_local_dependency_operations"]
    if operations:
        print("[setup] Project-local installation preview (runs only if selected):")
        for operation in operations:
            print(
                f"  - ({operation['cwd']}) "
                f"{shlex.join(operation['argv'])}; {operation['condition']}"
            )
    mutations = plan["follow_up_preview"]["project_file_mutations"]
    if mutations:
        print("[setup] Project-file bootstrap preview (runs only if selected):")
        for mutation in mutations:
            print(
                f"  - {mutation['path']}: {mutation['action']}; {mutation['condition']}"
            )
    print(
        "[setup] Follow-up preview: bootstrap="
        f"{arguments.bootstrap_steps}, "
        f"installation={'disabled' if arguments.no_install else 'allowed'}, "
        f"verification={'selected' if arguments.verify else 'skipped'}"
    )
    approved = arguments.yes
    if not approved:
        answer = input(f"Apply exactly plan {plan['plan_id']}? [y/N] ").strip().lower()
        approved = answer in {"y", "yes"}
    if not approved:
        print("[setup] Plan was not applied. No setup-owned file changed.")
        return 0
    result = apply_plan(
        root,
        plan,
        plan["plan_id"],
        bootstrap_steps=arguments.bootstrap_steps,
        no_install=arguments.no_install,
        verify=arguments.verify,
    )
    print(stable_json(result, pretty=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "inspect":
            result = inspect_repository(ROOT)
            print(
                stable_json(result, pretty=True)
                if arguments.json
                else stable_json(result, pretty=True)
            )
            return 0
        if arguments.command == "plan":
            plan = plan_from_arguments(ROOT, arguments)
            if arguments.output:
                output = resolve_plan_output(ROOT, arguments.output)
                write_plan(output, plan)
            print(stable_json(plan, pretty=True))
            return 0
        if arguments.command == "apply":
            try:
                plan_path = resolve_plan_output(ROOT, arguments.plan)
                requested_plan = (
                    arguments.plan
                    if arguments.plan.is_absolute()
                    else ROOT / arguments.plan
                )
                if requested_plan.is_symlink():
                    raise SetupError("Setup plan must not be a symbolic link")
                if plan_path.stat().st_size > PLAN_BYTE_LIMIT:
                    raise SetupError(f"Setup plan exceeds {PLAN_BYTE_LIMIT} bytes")
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise SetupError(f"Could not read setup plan: {error}") from error
            if not isinstance(plan, dict):
                raise SetupError("Setup plan root must be an object")
            result = apply_plan(
                ROOT,
                plan,
                arguments.approve,
                bootstrap_steps=arguments.bootstrap_steps,
                no_install=arguments.no_install,
                verify=arguments.verify,
            )
            print(stable_json(result, pretty=True))
            return 0
        if arguments.command == "doctor":
            result, exit_code = doctor(ROOT)
            print(stable_json(result, pretty=True))
            return exit_code
        if arguments.command == "wizard":
            return run_wizard(ROOT, arguments)
        parser.error("unsupported command")
    except SetupError as error:
        print(f"[setup] ERROR: {error}", file=sys.stderr)
        return error.exit_code
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
