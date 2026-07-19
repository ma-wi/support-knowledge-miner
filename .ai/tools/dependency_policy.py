#!/usr/bin/env python3
"""Fail-closed direct-dependency and lockfile policy checks."""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from pathlib import Path

# parse_xml bounds input and rejects DTD/entity declarations before parsing.
from xml.etree import ElementTree  # nosec B405

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".ai" / "config"
IGNORED_PARTS = {
    ".ai",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "target",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "1" if default else "0")
    if value not in {"0", "1"}:
        raise ValueError(f"{name} must be 0 or 1, found {value!r}")
    return value == "1"


def entries(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def manifests(name: str) -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob(name)
        if not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)
    )


def add(
    result: list[tuple[str, str | None, Path]],
    ecosystem: str,
    name: str,
    version: str | None,
    source: Path,
) -> None:
    normalized = name.strip()
    if ecosystem in {"npm", "pypi"}:
        normalized = normalized.lower().replace("_", "-")
    if normalized:
        result.append(
            (f"{ecosystem}:{normalized}", version.strip() if version else None, source)
        )


def add_poetry_dependency(
    result: list[tuple[str, str | None, Path]],
    errors: list[str],
    name: str,
    value: object,
    source: Path,
) -> None:
    if name.lower() == "python":
        return
    if isinstance(value, str):
        add(result, "pypi", name, value, source)
        return
    if not isinstance(value, dict):
        errors.append(
            f"unsupported dependency syntax in {rel(source)}: {name!r}={value!r}"
        )
        return
    source_keys = {"git", "path", "url", "source", "branch", "tag", "rev"}
    present_source_keys = sorted(source_keys.intersection(value))
    if present_source_keys:
        errors.append(
            f"remote or mutable source: pypi:{name} uses {', '.join(present_source_keys)} "
            f"({rel(source)})"
        )
        return
    allowed_keys = {"version", "markers", "python", "extras", "optional"}
    unknown = sorted(set(value) - allowed_keys)
    if unknown:
        errors.append(
            f"unsupported dependency syntax in {rel(source)}: "
            f"pypi:{name} uses {', '.join(unknown)}"
        )
        return
    version = value.get("version")
    if not isinstance(version, str):
        errors.append(
            f"unsupported dependency syntax in {rel(source)}: "
            f"pypi:{name} requires a string version"
        )
        return
    add(result, "pypi", name, version, source)


def add_cargo_dependencies(
    result: list[tuple[str, str | None, Path]],
    errors: list[str],
    values: object,
    source: Path,
) -> None:
    if not isinstance(values, dict):
        errors.append(
            f"unsupported dependency section in {rel(source)}: expected a table"
        )
        return
    for name, value in values.items():
        if isinstance(value, str):
            add(result, "cargo", name, value, source)
            continue
        if not isinstance(value, dict):
            errors.append(
                f"unsupported dependency syntax in {rel(source)}: {name!r}={value!r}"
            )
            continue
        source_keys = {"git", "path", "branch", "tag", "rev", "registry"}
        present_source_keys = sorted(source_keys.intersection(value))
        if present_source_keys:
            errors.append(
                f"remote or mutable source: cargo:{name} uses {', '.join(present_source_keys)} "
                f"({rel(source)})"
            )
            continue
        allowed_keys = {
            "version",
            "features",
            "optional",
            "default-features",
            "package",
        }
        unknown = sorted(set(value) - allowed_keys)
        if unknown:
            errors.append(
                f"unsupported dependency syntax in {rel(source)}: "
                f"cargo:{name} uses {', '.join(unknown)}"
            )
            continue
        version = value.get("version")
        if not isinstance(version, str):
            errors.append(
                f"unsupported dependency syntax in {rel(source)}: "
                f"cargo:{name} requires a string version"
            )
            continue
        add(result, "cargo", name, version, source)


def parse_xml(path: Path, errors: list[str]) -> ElementTree.Element | None:
    try:
        content = path.read_bytes()
        if len(content) > 5_000_000:
            raise ValueError("XML manifest exceeds the 5 MB safety limit")
        upper_content = content.upper()
        if b"<!DOCTYPE" in upper_content or b"<!ENTITY" in upper_content:
            raise ValueError("DTD and entity declarations are forbidden in manifests")
        # Input is bounded and DTD/entity declarations were rejected above.
        return ElementTree.fromstring(content)  # nosec B314
    except (ElementTree.ParseError, OSError, ValueError) as exc:
        errors.append(f"cannot parse {rel(path)}: {exc}")
        return None


def read_dependencies(errors: list[str]) -> list[tuple[str, str | None, Path]]:
    found: list[tuple[str, str | None, Path]] = []
    central_nuget_versions: dict[str, str] = {}

    for props in manifests("Directory.Packages.props"):
        root = parse_xml(props, errors)
        if root is None:
            continue
        for version_entry in root.findall(".//PackageVersion"):
            name = version_entry.get("Include") or version_entry.get("Update") or ""
            central_version = (
                version_entry.get("Version") or version_entry.findtext("Version") or ""
            )
            if name:
                central_nuget_versions[name.lower()] = central_version

    for package_json in manifests("package.json"):
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"cannot parse {rel(package_json)}: {exc}")
            continue
        for section in (
            "dependencies",
            "devDependencies",
            "optionalDependencies",
            "peerDependencies",
        ):
            for name, version in (data.get(section) or {}).items():
                if not isinstance(version, str):
                    errors.append(
                        f"unsupported dependency syntax in {rel(package_json)}: {name!r} must have a string version"
                    )
                    continue
                add(found, "npm", name, version, package_json)

    for requirements in manifests("requirements*.txt"):
        for number, raw in enumerate(
            requirements.read_text(encoding="utf-8").splitlines(), 1
        ):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = re.fullmatch(
                r"([A-Za-z0-9_.-]+)(?:\[[A-Za-z0-9_.-]+(?:,[A-Za-z0-9_.-]+)*\])?\s*([<>=!~].*)?",
                line.split(";")[0].strip(),
            )
            if match:
                add(found, "pypi", match.group(1), match.group(2), requirements)
            else:
                errors.append(
                    f"unsupported dependency syntax in {rel(requirements)}:{number}: {line!r}"
                )

    for pyproject in manifests("pyproject.toml"):
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            errors.append(f"cannot parse {rel(pyproject)}: {exc}")
            continue
        groups: list[object] = list(
            (data.get("project", {}).get("dependencies", []) or [])
        )
        for values in (
            data.get("project", {}).get("optional-dependencies", {}) or {}
        ).values():
            groups.extend(values or [])
        for values in (data.get("dependency-groups", {}) or {}).values():
            groups.extend(values or [])
        for specification in groups:
            if not isinstance(specification, str):
                errors.append(
                    f"unsupported dependency syntax in {rel(pyproject)}: {specification!r}"
                )
                continue
            match = re.fullmatch(
                r"([A-Za-z0-9_.-]+)(?:\[[A-Za-z0-9_.-]+(?:,[A-Za-z0-9_.-]+)*\])?\s*(.*)",
                specification,
            )
            if match:
                add(found, "pypi", match.group(1), match.group(2), pyproject)
            else:
                errors.append(
                    f"unsupported dependency syntax in {rel(pyproject)}: {specification!r}"
                )
        poetry = data.get("tool", {}).get("poetry", {}) or {}
        poetry_sections: list[object] = [
            poetry.get("dependencies", {}) or {},
            poetry.get("dev-dependencies", {}) or {},
        ]
        for group in (poetry.get("group", {}) or {}).values():
            if isinstance(group, dict):
                poetry_sections.append(group.get("dependencies", {}) or {})
            else:
                errors.append(
                    f"unsupported Poetry group syntax in {rel(pyproject)}: {group!r}"
                )
        for poetry_section in poetry_sections:
            if not isinstance(poetry_section, dict):
                errors.append(
                    f"unsupported Poetry dependency section in {rel(pyproject)}"
                )
                continue
            for name, value in poetry_section.items():
                add_poetry_dependency(found, errors, str(name), value, pyproject)

    for project in [
        *manifests("*.csproj"),
        *manifests("*.vbproj"),
        *manifests("*.fsproj"),
    ]:
        root = parse_xml(project, errors)
        if root is None:
            continue
        for reference in root.findall(".//PackageReference"):
            name = reference.get("Include") or reference.get("Update") or ""
            nuget_version = (
                reference.get("Version")
                or reference.findtext("Version")
                or central_nuget_versions.get(name.lower())
            )
            add(found, "nuget", name, nuget_version, project)

    for pom in manifests("pom.xml"):
        root = parse_xml(pom, errors)
        if root is None:
            continue
        namespace = {"m": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
        prefix = "m:" if namespace else ""
        for dependency in root.findall(
            f".//{prefix}dependencies/{prefix}dependency", namespace
        ):
            group = dependency.findtext(f"{prefix}groupId", namespaces=namespace) or ""
            artifact = (
                dependency.findtext(f"{prefix}artifactId", namespaces=namespace) or ""
            )
            maven_version = dependency.findtext(
                f"{prefix}version", namespaces=namespace
            )
            if group and artifact:
                add(found, "maven", f"{group}:{artifact}", maven_version, pom)

    for cargo in manifests("Cargo.toml"):
        try:
            data = tomllib.loads(cargo.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            errors.append(f"cannot parse {rel(cargo)}: {exc}")
            continue
        cargo_section_names = (
            "dependencies",
            "dev-dependencies",
            "build-dependencies",
        )
        for section in cargo_section_names:
            add_cargo_dependencies(found, errors, data.get(section, {}) or {}, cargo)
        workspace = data.get("workspace", {}) or {}
        if isinstance(workspace, dict):
            add_cargo_dependencies(
                found, errors, workspace.get("dependencies", {}) or {}, cargo
            )
        targets = data.get("target", {}) or {}
        if isinstance(targets, dict):
            for target in targets.values():
                if not isinstance(target, dict):
                    errors.append(
                        f"unsupported Cargo target syntax in {rel(cargo)}: {target!r}"
                    )
                    continue
                for section in cargo_section_names:
                    add_cargo_dependencies(
                        found, errors, target.get(section, {}) or {}, cargo
                    )

    for gomod in manifests("go.mod"):
        in_block = False
        for raw in gomod.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line == "require (":
                in_block = True
                continue
            if in_block and line == ")":
                in_block = False
                continue
            if line.startswith("require "):
                line = line[len("require ") :]
            elif not in_block:
                continue
            parts = line.split()
            if len(parts) >= 2:
                add(found, "go", parts[0], parts[1], gomod)

    return sorted(set(found), key=lambda item: (item[0], str(item[2]), item[1] or ""))


def check_lockfiles(errors: list[str]) -> None:
    checks = [
        (
            "package.json",
            (
                "package-lock.json",
                "pnpm-lock.yaml",
                "yarn.lock",
                "bun.lock",
                "bun.lockb",
            ),
            "Node.js",
        ),
        (
            "pyproject.toml",
            ("uv.lock", "poetry.lock", "pdm.lock", "pylock.toml"),
            "Python",
        ),
        ("Cargo.toml", ("Cargo.lock",), "Rust"),
        ("go.mod", ("go.sum",), "Go"),
    ]
    for manifest_name, candidates, label in checks:
        for manifest in manifests(manifest_name):
            if not any(
                (manifest.parent / candidate).exists() for candidate in candidates
            ):
                errors.append(
                    f"{label}: lock/integrity file missing next to {rel(manifest)} "
                    f"({', '.join(candidates)})"
                )
    for project in [
        *manifests("*.csproj"),
        *manifests("*.vbproj"),
        *manifests("*.fsproj"),
    ]:
        if not (
            (project.parent / "packages.lock.json").exists()
            or (ROOT / "packages.lock.json").exists()
        ):
            errors.append(f".NET: packages.lock.json missing for {rel(project)}")


def floating(version: str | None) -> bool:
    # Reproducibility in this template comes from mandatory, committed lockfiles
    # (REQUIRE_LOCKFILES), not from exact manifest pins. Version ranges such as
    # "^1.2" or ">=1.0,<2" are therefore accepted; only genuinely unpinned or
    # unresolvable specifiers (``*``/``latest``/``x``/empty, remote URLs, or
    # environment-variable interpolation) are rejected here. Remote/mutable
    # sources are handled separately by ``remote_or_mutable``.
    if version is None:
        return True
    value = version.strip().lower()
    return (
        value in {"", "*", "latest", "x"}
        or value.startswith(("git+", "http://", "https://"))
        or re.search(r"(^|[.])x($|[.])", value) is not None
        or "$" in value
    )


def remote_or_mutable(version: str | None) -> bool:
    if version is None:
        return False
    value = version.strip().lower()
    return "://" in value or value.startswith(
        (
            "@ git+",
            "@ http:",
            "@ https:",
            "@ file:",
            "git+",
            "git:",
            "git@",
            "github:",
            "gitlab:",
            "bitbucket:",
            "http:",
            "https:",
            "file:",
            "link:",
            "ssh:",
        )
    )


def main() -> int:
    errors: list[str] = []
    try:
        allow_mode = env_bool("DEPENDENCY_ALLOWLIST_MODE", False)
        require_lockfiles = env_bool("REQUIRE_LOCKFILES", True)
        reject_floating = env_bool("REJECT_FLOATING_VERSIONS", True)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    deny = entries(CONFIG / "dependency-denylist.txt")
    allow = entries(CONFIG / "dependency-allowlist.txt")
    dependencies = read_dependencies(errors)
    for coordinate, version, source in dependencies:
        location = rel(source)
        if coordinate in deny:
            errors.append(f"denied dependency: {coordinate} ({location})")
        if allow_mode and coordinate not in allow:
            errors.append(f"dependency not on allow-list: {coordinate} ({location})")
        if remote_or_mutable(version):
            errors.append(
                f"remote or mutable source: {coordinate} ({version!r}, {location})"
            )
        if reject_floating and floating(version):
            errors.append(
                f"floating or unpinned version: {coordinate} ({version!r}, {location})"
            )
    if require_lockfiles:
        check_lockfiles(errors)

    print(f"Dependency policy inspected {len(dependencies)} direct dependency entries.")
    for coordinate, version, source in dependencies:
        print(f"  {coordinate}{' ' + version if version else ''} [{rel(source)}]")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Dependency policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
