#!/usr/bin/env python3
"""Shared helpers for the .ai/tools scripts.

These helpers are deliberately dependency-free so every tool can import them
whether it is executed as a script (its directory is on ``sys.path``) or loaded
in-process by the template test suite.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

# Plan phases in which a temporary PLAN.md pointer must already exist. Earlier
# phases (discovery, specification) legitimately precede plan creation, so a
# missing pointer is not an error there.
PLAN_POINTER_PHASES = {
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
VISUAL_EVIDENCE_FIELDS = (
    "Required screens",
    "Required states",
    "Required viewports",
)
RUNTIME_VERSION_PATTERNS = {
    "python": re.compile(r"\d+\.\d+(?:\.\d+)?"),
    "node": re.compile(r"\d+\.\d+\.\d+"),
}
VERSION_COMPONENT = r"[0-9]{1,4}"
VERSION_REQUIREMENT_MAX_LENGTH = 256
VERSION_REQUIREMENT_MAX_CLAUSES = 8
DEFAULT_TOOL_REQUIREMENTS = {
    "uv": ">=0.11.29,<0.12.0",
    "vite": ">=9.1.1,<10.0.0",
    "pnpm": ">=11.15.0,<12.0.0",
    "yarn": ">=4.17.1,<5.0.0",
}
Version = tuple[int, ...]
VersionClause = tuple[str, Version]


def parse_numeric_version(
    value: str,
    *,
    minimum_components: int = 3,
    maximum_components: int = 3,
    allow_v_prefix: bool = False,
) -> Version | None:
    """Parse a bounded numeric version without importing an ecosystem parser."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if allow_v_prefix:
        text = text.removeprefix("v")
    parts = text.split(".")
    if not minimum_components <= len(parts) <= maximum_components:
        return None
    if any(re.fullmatch(VERSION_COMPONENT, part) is None for part in parts):
        return None
    return tuple(int(part) for part in parts)


def normalized_version(version: Version, width: int = 3) -> Version:
    return (*version, *((0,) * (width - len(version))))


def _prefix_upper(version: Version, width: int) -> Version:
    prefix = list(version)
    prefix[-1] += 1
    return normalized_version(tuple(prefix), width)


def _interval_is_nonempty(
    lower: Version,
    lower_inclusive: bool,
    upper: Version | None,
    upper_inclusive: bool,
) -> bool:
    if upper is None:
        return lower_inclusive or _next_version(lower) is not None
    candidate = lower
    if not lower_inclusive:
        next_candidate = _next_version(lower)
        if next_candidate is None:
            return False
        candidate = next_candidate
    return candidate < upper or (candidate == upper and upper_inclusive)


def _next_version(version: Version) -> Version | None:
    candidate = list(version)
    for index in range(len(candidate) - 1, -1, -1):
        if candidate[index] < 9_999:
            candidate[index] += 1
            for trailing in range(index + 1, len(candidate)):
                candidate[trailing] = 0
            return tuple(candidate)
    return None


def _requirement_interval(
    clauses: list[VersionClause], width: int
) -> tuple[Version, bool, Version | None, bool]:
    lower = (0,) * width
    lower_inclusive = True
    upper: Version | None = None
    upper_inclusive = False

    def merge_lower(candidate: Version, inclusive: bool) -> None:
        nonlocal lower, lower_inclusive
        if candidate > lower:
            lower, lower_inclusive = candidate, inclusive
        elif candidate == lower:
            lower_inclusive = lower_inclusive and inclusive

    def merge_upper(candidate: Version, inclusive: bool) -> None:
        nonlocal upper, upper_inclusive
        if upper is None or candidate < upper:
            upper, upper_inclusive = candidate, inclusive
        elif candidate == upper:
            upper_inclusive = upper_inclusive and inclusive

    for operator, raw_version in clauses:
        version = normalized_version(raw_version, width)
        if operator == "==":
            merge_lower(version, True)
            merge_upper(version, True)
        elif operator == ">=":
            merge_lower(version, True)
        elif operator == ">":
            merge_lower(version, False)
        elif operator == "<=":
            merge_upper(version, True)
        elif operator == "<":
            merge_upper(version, False)
        elif operator == "~=":
            merge_lower(version, True)
            compatible_prefix = (
                raw_version[:-1] if len(raw_version) > 2 else raw_version[:1]
            )
            merge_upper(_prefix_upper(compatible_prefix, width), False)
    return lower, lower_inclusive, upper, upper_inclusive


def parse_version_requirement(
    requirement: str,
    *,
    minimum_components: int = 3,
    maximum_components: int = 3,
    allow_compatible: bool = False,
    allow_space_separator: bool = False,
    allow_empty: bool = False,
) -> list[VersionClause] | None:
    """Parse a conservative intersection of bounded numeric comparison clauses."""
    if not isinstance(requirement, str):
        return None
    text = requirement.strip()
    if not text:
        return [] if allow_empty else None
    if len(text) > VERSION_REQUIREMENT_MAX_LENGTH:
        return None
    bare = parse_numeric_version(
        text,
        minimum_components=minimum_components,
        maximum_components=maximum_components,
    )
    if bare is not None:
        return [("==", bare)]
    separator = r"(?:\s*,\s*|\s+)" if allow_space_separator else r"\s*,\s*"
    raw_clauses = re.split(separator, text)
    if (
        not raw_clauses
        or len(raw_clauses) > VERSION_REQUIREMENT_MAX_CLAUSES
        or any(not clause for clause in raw_clauses)
    ):
        return None
    operators = r"==|>=|<=|>|<" + (r"|~=" if allow_compatible else "")
    clauses: list[VersionClause] = []
    for raw_clause in raw_clauses:
        match = re.fullmatch(rf"({operators})\s*(.+)", raw_clause)
        if match is None:
            return None
        version = parse_numeric_version(
            match.group(2),
            minimum_components=minimum_components,
            maximum_components=maximum_components,
        )
        if version is None:
            return None
        clauses.append((match.group(1), version))
    lower, lower_inclusive, upper, upper_inclusive = _requirement_interval(
        clauses, maximum_components
    )
    if not _interval_is_nonempty(lower, lower_inclusive, upper, upper_inclusive):
        return None
    return clauses


def clauses_satisfied(
    candidate: Version, clauses: list[VersionClause], *, width: int = 3
) -> bool:
    actual = normalized_version(candidate, width)
    for operator, raw_expected in clauses:
        expected = normalized_version(raw_expected, width)
        if operator == "==":
            if actual != expected:
                return False
        elif operator == ">=" and actual < expected:
            return False
        elif operator == ">" and actual <= expected:
            return False
        elif operator == "<=" and actual > expected:
            return False
        elif operator == "<" and actual >= expected:
            return False
        elif operator == "~=":
            prefix = raw_expected[:-1] if len(raw_expected) > 2 else raw_expected[:1]
            if actual < expected or actual >= _prefix_upper(prefix, width):
                return False
    return True


def clauses_intersect(*requirements: list[VersionClause], width: int = 3) -> bool:
    clauses = [clause for requirement in requirements for clause in requirement]
    if not clauses:
        return True
    lower, lower_inclusive, upper, upper_inclusive = _requirement_interval(
        clauses, width
    )
    return _interval_is_nonempty(lower, lower_inclusive, upper, upper_inclusive)


def select_exact_version(
    requirement: str,
    *,
    minimum_components: int = 3,
    maximum_components: int = 3,
) -> str | None:
    """Select the deterministic inclusive lower bound of a requirement."""
    clauses = parse_version_requirement(
        requirement,
        minimum_components=minimum_components,
        maximum_components=maximum_components,
    )
    if clauses is None or not clauses:
        return None
    return select_exact_from_clauses(clauses, width=maximum_components)


def select_exact_from_clauses(
    clauses: list[VersionClause], *, width: int = 3
) -> str | None:
    """Select an exact inclusive lower bound from already validated clauses."""
    if not any(operator in {"==", ">=", ">", "~="} for operator, _ in clauses):
        return None
    lower, lower_inclusive, _upper, _upper_inclusive = _requirement_interval(
        clauses, width
    )
    if not lower_inclusive or not clauses_satisfied(lower, clauses, width=width):
        return None
    return ".".join(str(part) for part in lower)


def version_satisfies(
    candidate: str,
    requirement: str,
    *,
    minimum_components: int = 3,
    maximum_components: int = 3,
    allow_v_prefix: bool = False,
) -> bool:
    parsed_candidate = parse_numeric_version(
        candidate,
        minimum_components=minimum_components,
        maximum_components=maximum_components,
        allow_v_prefix=allow_v_prefix,
    )
    clauses = parse_version_requirement(
        requirement,
        minimum_components=minimum_components,
        maximum_components=maximum_components,
    )
    return (
        parsed_candidate is not None
        and clauses is not None
        and clauses_satisfied(parsed_candidate, clauses, width=maximum_components)
    )


def requirement_to_npm(requirement: str) -> str:
    """Translate the common numeric conjunction to npm's space-separated form."""
    clauses = parse_version_requirement(requirement)
    if clauses is None or not clauses:
        raise ValueError("invalid numeric version requirement")
    if len(clauses) == 1 and clauses[0][0] == "==":
        return ".".join(str(part) for part in clauses[0][1])
    return " ".join(
        f"{operator}{'.'.join(str(part) for part in version)}"
        for operator, version in clauses
    )


def parse_npm_requirement(requirement: str) -> list[VersionClause] | None:
    """Parse the bounded npm subset used for template lockfile evidence."""
    text = requirement.strip()
    if text.startswith(("^", "~")):
        version = parse_numeric_version(text[1:])
        if version is None:
            return None
        lower = ".".join(str(part) for part in version)
        if text.startswith("~"):
            upper = (version[0], version[1] + 1, 0)
        elif version[0] > 0:
            upper = (version[0] + 1, 0, 0)
        elif version[1] > 0:
            upper = (0, version[1] + 1, 0)
        else:
            upper = (0, 0, version[2] + 1)
        text = f">={lower} <{'.'.join(str(part) for part in upper)}"
    return parse_version_requirement(text, allow_space_separator=True)


def npm_version_satisfies(candidate: str, requirement: str) -> bool:
    """Match exact, bounded, caret, or tilde npm requirements for lock evidence."""
    clauses = parse_npm_requirement(requirement)
    parsed_candidate = parse_numeric_version(candidate.removeprefix("v"))
    return (
        parsed_candidate is not None
        and clauses is not None
        and clauses_satisfied(parsed_candidate, clauses)
    )


def _unquoted_lock_value(value: str) -> str:
    result = value.strip()
    if len(result) >= 2 and result[0] == result[-1] and result[0] in {"'", '"'}:
        return result[1:-1]
    return result


def _direct_lock_fields(
    lines: list[str], header_index: int, header_indent: int
) -> dict[str, str]:
    fields: dict[str, str] = {}
    direct_indent: int | None = None
    for body_line in lines[header_index + 1 :]:
        if not body_line.strip():
            continue
        body_prefix = body_line[: len(body_line) - len(body_line.lstrip(" \t"))]
        body_indent = len(body_prefix.expandtabs(8))
        if body_indent <= header_indent:
            break
        if direct_indent is None:
            direct_indent = body_indent
        if body_indent != direct_indent:
            continue
        field = re.fullmatch(r"\s*(specifier|version):\s*(.+?)\s*", body_line)
        if field is not None:
            fields[field.group(1)] = _unquoted_lock_value(field.group(2))
    return fields


def pnpm_lock_versions(text: str, dependency: str, requirement: str) -> set[str]:
    """Return a pnpm resolution bound to a direct importer specifier."""
    lines = text.splitlines()
    versions: set[str] = set()
    ancestors: list[tuple[int, str]] = []
    direct_groups = {"dependencies", "devDependencies", "optionalDependencies"}
    excluded_roots = {"packages", "snapshots"}
    for index, line in enumerate(lines):
        header = re.fullmatch(r"(?P<indent>[ \t]*)(?P<key>.+):\s*", line)
        if header is None:
            continue
        indentation = len(header.group("indent").expandtabs(8))
        while ancestors and ancestors[-1][0] >= indentation:
            ancestors.pop()
        key = _unquoted_lock_value(header.group("key"))
        ancestor_keys = [item[1] for item in ancestors]
        root_importer = (
            len(ancestor_keys) == 3
            and ancestor_keys[0] == "importers"
            and ancestor_keys[1] == "."
            and ancestor_keys[2] in direct_groups
        )
        legacy_root = len(ancestor_keys) == 1 and ancestor_keys[0] in direct_groups
        if (
            key == dependency
            and (root_importer or legacy_root)
            and not excluded_roots.intersection(ancestor_keys)
        ):
            fields = _direct_lock_fields(lines, index, indentation)
            if fields.get("specifier") == requirement.strip():
                version = re.fullmatch(
                    r"(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?"
                    r"(?:\+[0-9A-Za-z.-]+)?)(?:\([^\n]*\))?",
                    fields.get("version", ""),
                )
                if version is not None:
                    versions.add(version.group(1))
        ancestors.append((indentation, key))
    return versions


def yarn_lock_versions(text: str, dependency: str, requirement: str) -> set[str]:
    """Return a Yarn resolution bound to the declared npm descriptor."""
    lines = text.splitlines()
    versions: set[str] = set()
    target = f"{dependency}@npm:{requirement.strip()}"
    for index, line in enumerate(lines):
        header = re.fullmatch(r"(?P<key>[^ \t].+):\s*", line)
        if header is None:
            continue
        key = _unquoted_lock_value(header.group("key"))
        position = key.find(target)
        if position < 0:
            continue
        before = key[:position]
        after = key[position + len(target) :]
        if (before and not before.endswith(", ")) or (
            after and not after.startswith(", ")
        ):
            continue
        fields = _direct_lock_fields(lines, index, 0)
        version = re.fullmatch(
            r"(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)",
            fields.get("version", ""),
        )
        if version is not None:
            versions.add(version.group(1))
    return versions


def npm_lock_versions(package_dir: Path, dependency: str, requirement: str) -> set[str]:
    """Return exact resolutions bound to a direct package requirement."""
    versions: set[str] = set()
    package_lock = package_dir / "package-lock.json"
    if package_lock.is_file():
        try:
            lock = json.loads(package_lock.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return set()
        package_key = f"node_modules/{dependency}"
        packages = lock.get("packages", {})
        dependencies = lock.get("dependencies", {})
        root_matches = False
        if isinstance(packages, dict) and isinstance(packages.get(""), dict):
            root_package = packages[""]
            root_matches = any(
                isinstance(root_package.get(group), dict)
                and root_package[group].get(dependency) == requirement.strip()
                for group in (
                    "dependencies",
                    "devDependencies",
                    "optionalDependencies",
                    "peerDependencies",
                )
            )
        legacy_lock = lock.get("lockfileVersion") == 1 and not packages
        if root_matches and isinstance(packages.get(package_key), dict):
            version = packages[package_key].get("version")
            if isinstance(version, str):
                versions.add(version)
        if (
            legacy_lock
            and isinstance(dependencies, dict)
            and isinstance(dependencies.get(dependency), dict)
        ):
            version = dependencies[dependency].get("version")
            if isinstance(version, str):
                versions.add(version)
    pnpm_lock = package_dir / "pnpm-lock.yaml"
    if pnpm_lock.is_file() and pnpm_lock.stat().st_size:
        versions.update(
            pnpm_lock_versions(
                pnpm_lock.read_text(encoding="utf-8", errors="replace"),
                dependency,
                requirement,
            )
        )
    yarn_lock = package_dir / "yarn.lock"
    if yarn_lock.is_file() and yarn_lock.stat().st_size:
        versions.update(
            yarn_lock_versions(
                yarn_lock.read_text(encoding="utf-8", errors="replace"),
                dependency,
                requirement,
            )
        )
    return versions


def parse_runtime_version(value: str, runtime: str) -> Version | None:
    return parse_numeric_version(
        value,
        minimum_components=2 if runtime == "python" else 3,
        maximum_components=3,
        allow_v_prefix=True,
    )


def parse_runtime_requirement(
    requirement: str, runtime: str
) -> list[VersionClause] | None:
    return parse_version_requirement(
        requirement,
        minimum_components=2 if runtime == "python" else 3,
        maximum_components=3,
        allow_compatible=True,
        allow_space_separator=runtime == "node",
    )


def select_exact_runtime_version(requirement: str, runtime: str) -> str | None:
    clauses = parse_runtime_requirement(requirement, runtime)
    if clauses is None:
        return None
    return select_exact_from_clauses(clauses)


def runtime_satisfies(
    candidate: str, runtime: str, requirements: list[list[VersionClause]]
) -> bool:
    parsed_candidate = parse_runtime_version(candidate, runtime)
    return parsed_candidate is not None and all(
        clauses_satisfied(parsed_candidate, clauses) for clauses in requirements
    )


def requirement_candidate(runtime: str, clauses: list[VersionClause]) -> str | None:
    for operator, version in clauses:
        if operator in {"==", ">=", "~="}:
            candidate = ".".join(str(part) for part in version)
            if runtime == "node" and len(version) != 3:
                return None
            return candidate
    return None


def parse_scalar(value: str):
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value in {"null", "~"}:
        return None
    if value.startswith(("[", "{", "'", '"')):
        return ast.literal_eval(value)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def load_yaml_subset(path: Path) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if (
            not raw.strip()
            or raw.lstrip().startswith("#")
            or raw.strip().startswith("- ")
        ):
            continue
        if "\t" in raw or ":" not in raw:
            raise SystemExit(f"Unsupported YAML at {path}:{number}")
        indent = len(raw) - len(raw.lstrip(" "))
        while indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        key, value = raw.strip().split(":", 1)
        if value.strip():
            parent[key] = parse_scalar(value)
        else:
            parent[key] = {}
            stack.append((indent, parent[key]))
    return root


def get(data: dict, *keys: str, default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def runtime_versions(config: dict) -> dict[str, str]:
    """Return validated exact or bounded runtime requests from project.yaml."""
    result: dict[str, str] = {}
    for runtime in RUNTIME_VERSION_PATTERNS:
        value = get(config, "runtimes", runtime)
        if (
            not isinstance(value, str)
            or parse_runtime_requirement(value, runtime) is None
        ):
            raise SystemExit(
                f"runtimes.{runtime} must be an exact or bounded numeric "
                "version requirement"
            )
        result[runtime] = value
    return result


def tool_requirements(config: dict) -> dict[str, str]:
    """Return validated tool requirements, with defaults for legacy configs."""
    configured = get(config, "tool_requirements", default={})
    if not isinstance(configured, dict):
        raise SystemExit("tool_requirements must be a mapping")
    unknown = sorted(set(configured) - set(DEFAULT_TOOL_REQUIREMENTS))
    if unknown:
        raise SystemExit("Unknown tool requirement(s): " + ", ".join(unknown))
    result: dict[str, str] = {}
    for tool, default in DEFAULT_TOOL_REQUIREMENTS.items():
        requirement = configured.get(tool, default)
        if (
            not isinstance(requirement, str)
            or parse_version_requirement(requirement) is None
        ):
            raise SystemExit(
                f"tool_requirements.{tool} must be an exact or bounded numeric "
                "version requirement"
            )
        result[tool] = requirement
    return result


def resolve_frontend_source_root(config: dict) -> Path:
    """Return the one configured frontend source root used by source scanners."""
    react_root = str(
        get(config, "stacks", "react", "directory", default="frontend")
    ).rstrip("/")
    configured = get(
        config,
        "ui_quality",
        "frontend",
        "source_root",
        default=f"{react_root}/src",
    )
    return Path(str(configured))


def extract_field(text: str, field: str) -> str | None:
    match = re.search(
        rf"^-[ \t]*{re.escape(field)}:[ \t]*(.*?)[ \t]*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip().strip("`")


def is_inactive_plan(text: str) -> bool:
    """Return True when CURRENT_PLAN.md declares no active temporary work.

    Both the ``No active requirement.`` sentinel and a ``Status: idle`` field
    mark an inactive plan; the two lifecycle checkers must agree on this.
    """
    if "No active requirement." in text:
        return True
    status = extract_field(text, "Status")
    return status is not None and status.lower() == "idle"
