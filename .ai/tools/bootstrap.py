#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import string

# All subprocess calls use explicit argument arrays and never enable a shell.
import subprocess  # nosec B404
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    DEFAULT_TOOL_REQUIREMENTS,
    get,
    load_yaml_subset,
    npm_lock_versions,
    npm_version_satisfies,
    parse_runtime_requirement,
    parse_version_requirement,
    requirement_to_npm as requirement_to_npm,
    runtime_satisfies,
    runtime_versions,
    select_exact_version,
    tool_requirements,
    version_satisfies,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".ai" / "project.yaml"
POLICY_PROFILE = ROOT / ".ai" / "policy-profile.yaml"

# Bounded compatibility requirements. Package managers still record exact
# resolutions in manifests and lockfiles. When updating, bump every copy together:
#   - UV_VERSION_REQUIREMENT here and `version:` in .github/workflows/ci.yml
#   - PYTHON_DEV_DEPENDENCIES here and the resolved ruff/mypy/bandit versions in
#     tools/verify.sh
#   - VITE_VERSION_REQUIREMENT / PNPM_VERSION_REQUIREMENT /
#     YARN_VERSION_REQUIREMENT /
#     REACT_QUALITY_DEPENDENCIES here
#   - runtime pins in .ai/project.yaml
# Verify every requirement resolves before committing the bump.
UV_VERSION_REQUIREMENT = DEFAULT_TOOL_REQUIREMENTS["uv"]
VITE_VERSION_REQUIREMENT = DEFAULT_TOOL_REQUIREMENTS["vite"]
PNPM_VERSION_REQUIREMENT = DEFAULT_TOOL_REQUIREMENTS["pnpm"]
YARN_VERSION_REQUIREMENT = DEFAULT_TOOL_REQUIREMENTS["yarn"]
PNPM_VERSION_RESOLUTION = "11.15.0"
YARN_VERSION_RESOLUTION = "4.17.1"
REACT_TEMPLATE = "react-ts"
SELF_REVIEW_RULES = ".aiassistant/review/self-review.md"
PYTHON_DEV_DEPENDENCIES = (
    "ruff>=0.15.22,<0.16.0",
    "mypy>=2.3.0,<3.0.0",
    "pytest>=9.1.1,<10.0.0",
    "pytest-cov>=7.1.0,<8.0.0",
    "bandit>=1.9.4,<2.0.0",
    "pip-audit>=2.10.1,<3.0.0",
    "build>=1.5.0,<2.0.0",
)
REACT_QUALITY_DEPENDENCIES = (
    "prettier@>=3.9.5 <4.0.0",
    "vitest@>=4.1.10 <5.0.0",
    "jsdom@>=29.1.1 <30.0.0",
    "@testing-library/react@>=16.3.2 <17.0.0",
    "@testing-library/jest-dom@>=6.9.1 <7.0.0",
    "@testing-library/user-event@>=14.6.1 <15.0.0",
)
CONFIG_SCHEMA = {
    "project": {"name": None},
    "runtimes": {"python": None, "node": None},
    "tool_requirements": {"uv": None, "vite": None, "pnpm": None, "yarn": None},
    "stacks": {
        "python": {"enabled": None, "directory": None},
        "react": {"enabled": None, "directory": None, "package_manager": None},
        "bash": {"enabled": None},
        "dotnet": {"enabled": None, "solution": None, "test_project": None},
    },
    "incremental_changes": {
        "default_review_cadence": None,
        "max_tasks_per_review_batch": None,
        "force_task_review_for": None,
    },
    "orchestration": {
        "enabled": None,
        "executor_kind": None,
        "executor_isolation": None,
        "executor_command": None,
        "codex_expected_version": None,
        "codex_model": None,
        "codex_reasoning_effort": None,
        "external_repository_processing_approved": None,
        "agent_timeout_seconds": None,
        "max_attempts_per_phase": None,
        "max_identical_failures": None,
        "lease_seconds": None,
        "owner": None,
    },
    "ui_quality": {
        "enabled": None,
        "frontend": {"root": None, "source_root": None},
        "design_system": {
            "document": None,
            "component_catalog": None,
        },
        "design_artifacts": {
            "allowed": None,
            "storage": None,
        },
        "require_human_approval_for": None,
        "browser_review": {
            "command": None,
            "base_url": None,
            "fallback_when_unconfigured": None,
            "viewports": None,
        },
        "visual_regression": {"enabled": None, "command": None},
        "accessibility": {"enabled": None, "command": None},
    },
    "user_facing_errors": {
        "enabled": None,
        "catalog": {"path": None},
        "frontend": {"enabled": None},
    },
    "documentation": {
        "budgets": {
            "agents_md_lines": None,
            "readme_lines": None,
            "project_context_lines": None,
            "current_plan_lines": None,
            "next_steps_items": None,
            "active_work_item_lines": None,
            "policy_lines": None,
            "role_lines": None,
            "template_lines": None,
            "worst_case_instruction_words": None,
            "worst_case_composed_template_words": None,
            "active_work_context_words": None,
        }
    },
    "quality_gates": {
        "commands": {
            "setup": None,
            "format_check": None,
            "format_apply": None,
            "lint": None,
            "test": None,
            "security": None,
            "dependency_scan": None,
            "build": None,
        }
    },
}


def reject_unknown_keys(data: object, schema: object, path: str = "") -> None:
    if not isinstance(data, dict) or not isinstance(schema, dict):
        return
    unknown = sorted(set(data) - set(schema))
    if unknown:
        location = path or "configuration root"
        raise SystemExit(f"Unknown key(s) below {location}: {', '.join(unknown)}")
    for key, value in data.items():
        reject_unknown_keys(value, schema[key], f"{path}.{key}".lstrip("."))


def validate_config(data: dict) -> None:
    reject_unknown_keys(data, CONFIG_SCHEMA)
    runtime_versions(data)
    tool_requirements(data)
    project_name = get(data, "project", "name", default="CHANGE_ME")
    if (
        not isinstance(project_name, str)
        or not project_name.strip()
        or any(ord(character) < 32 for character in project_name)
        or len(project_name) > 128
    ):
        raise SystemExit(
            "project.name must be a non-empty single-line string up to 128 characters"
        )
    react_managers = {"npm", "pnpm", "yarn"}
    review_cadences = {"per-task", "batch", "feature"}

    react_manager = str(get(data, "stacks", "react", "package_manager", default="npm"))
    if react_manager not in react_managers:
        raise SystemExit(
            f"Unsupported stacks.react.package_manager: {react_manager}. Allowed: {sorted(react_managers)}"
        )
    review_cadence = str(
        get(
            data,
            "incremental_changes",
            "default_review_cadence",
            default="batch",
        )
    )
    if review_cadence not in review_cadences:
        raise SystemExit(
            "Unsupported incremental_changes.default_review_cadence: "
            f"{review_cadence}. Allowed: {sorted(review_cadences)}"
        )
    max_batch = get(
        data,
        "incremental_changes",
        "max_tasks_per_review_batch",
        default=3,
    )
    if not isinstance(max_batch, int) or not 1 <= max_batch <= 10:
        raise SystemExit(
            "incremental_changes.max_tasks_per_review_batch must be an integer "
            "between 1 and 10"
        )
    forced = get(
        data,
        "incremental_changes",
        "force_task_review_for",
        default="",
    )
    if not isinstance(forced, str):
        raise SystemExit(
            "incremental_changes.force_task_review_for must be a space-separated string"
        )
    orchestration_enabled = get(data, "orchestration", "enabled", default=False)
    if not isinstance(orchestration_enabled, bool):
        raise SystemExit("orchestration.enabled must be true or false")
    executor_kind = get(data, "orchestration", "executor_kind", default="command")
    if executor_kind not in {"command", "codex"}:
        raise SystemExit("orchestration.executor_kind must be 'command' or 'codex'")
    isolation_default = "codex-sandbox" if executor_kind == "codex" else "bwrap"
    executor_isolation = get(
        data, "orchestration", "executor_isolation", default=isolation_default
    )
    required_isolation = "codex-sandbox" if executor_kind == "codex" else "bwrap"
    if executor_isolation != required_isolation:
        raise SystemExit(
            "orchestration.executor_isolation must be "
            f"'{required_isolation}' for executor_kind '{executor_kind}'"
        )
    executor_command = get(data, "orchestration", "executor_command", default=[])
    if (
        not isinstance(executor_command, list)
        or any(
            not isinstance(argument, str) or not argument
            for argument in executor_command
        )
        or len(executor_command) > 32
    ):
        raise SystemExit(
            "orchestration.executor_command must be a list of at most 32 "
            "non-empty strings"
        )
    if orchestration_enabled and not executor_command:
        raise SystemExit(
            "orchestration.executor_command must be configured when orchestration "
            "is enabled"
        )
    if executor_kind == "codex":
        if len(executor_command) != 1 or any(
            character in executor_command[0] for character in "{}"
        ):
            raise SystemExit(
                "Codex executor_command must contain exactly one executable "
                "without placeholders"
            )
        expected_version = get(
            data, "orchestration", "codex_expected_version", default=""
        )
        if not isinstance(expected_version, str) or (
            expected_version and parse_version_requirement(expected_version) is None
        ):
            raise SystemExit(
                "orchestration.codex_expected_version must be empty or an exact "
                "or bounded numeric version requirement"
            )
        model = get(data, "orchestration", "codex_model", default="")
        if not isinstance(model, str) or len(model) > 128:
            raise SystemExit("orchestration.codex_model must be a short string")
        reasoning = get(data, "orchestration", "codex_reasoning_effort", default="high")
        if reasoning not in {"low", "medium", "high", "xhigh"}:
            raise SystemExit(
                "orchestration.codex_reasoning_effort must be low, medium, high, "
                "or xhigh"
            )
        external_approved = get(
            data,
            "orchestration",
            "external_repository_processing_approved",
            default=False,
        )
        if not isinstance(external_approved, bool):
            raise SystemExit(
                "orchestration.external_repository_processing_approved must be "
                "true or false"
            )
        if orchestration_enabled and not external_approved:
            raise SystemExit(
                "Codex orchestration requires explicit external repository "
                "processing approval"
            )
    if (
        orchestration_enabled
        and get(data, "ui_quality", "enabled", default=False) is True
        and not str(
            get(
                data,
                "ui_quality",
                "browser_review",
                "command",
                default="",
            )
        ).strip()
    ):
        raise SystemExit(
            "orchestrated UI quality requires "
            "ui_quality.browser_review.command for the trusted host gate"
        )
    allowed_placeholders = {
        "request",
        "handoff",
        "workspace",
        "role",
        "invocation_id",
    }
    formatter = string.Formatter()
    for argument in executor_command if executor_kind == "command" else []:
        try:
            parsed = list(formatter.parse(argument))
            placeholders = {field for _, field, _, _ in parsed if field is not None}
            invalid_format = any(
                format_spec or conversion
                for _, field, format_spec, conversion in parsed
                if field is not None
            )
            rendered = argument.format_map(
                {name: "value" for name in allowed_placeholders}
            )
        except (KeyError, ValueError):
            raise SystemExit(
                "orchestration.executor_command contains a malformed placeholder"
            ) from None
        if (
            placeholders - allowed_placeholders
            or invalid_format
            or "{" in rendered
            or "}" in rendered
        ):
            raise SystemExit(
                "orchestration.executor_command contains an unknown, escaped, or "
                "formatted placeholder"
            )
    for key, default, maximum in (
        ("agent_timeout_seconds", 1800, 86_400),
        ("max_attempts_per_phase", 3, 20),
        ("max_identical_failures", 2, 20),
        ("lease_seconds", 3600, 86_400),
    ):
        value = get(data, "orchestration", key, default=default)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= maximum
        ):
            raise SystemExit(
                f"orchestration.{key} must be an integer between 1 and {maximum}"
            )
    if get(data, "orchestration", "lease_seconds", default=3600) <= get(
        data, "orchestration", "agent_timeout_seconds", default=1800
    ):
        raise SystemExit(
            "orchestration.lease_seconds must be greater than "
            "orchestration.agent_timeout_seconds"
        )
    owner = get(data, "orchestration", "owner", default="OWNER")
    if not isinstance(owner, str) or not owner.strip() or len(owner) > 128:
        raise SystemExit("orchestration.owner must be a non-empty short string")
    for label, value, allow_dot in (
        (
            "stacks.python.directory",
            get(data, "stacks", "python", "directory", default="backend"),
            True,
        ),
        (
            "stacks.react.directory",
            get(data, "stacks", "react", "directory", default="frontend"),
            True,
        ),
        (
            "stacks.dotnet.solution",
            get(data, "stacks", "dotnet", "solution", default=""),
            True,
        ),
        (
            "stacks.dotnet.test_project",
            get(data, "stacks", "dotnet", "test_project", default=""),
            not get(data, "stacks", "dotnet", "enabled", default=False),
        ),
    ):
        validate_repository_path(str(value), label, allow_empty=allow_dot)
    if get(data, "stacks", "python", "enabled", default=False):
        validate_python_package_directory(
            str(get(data, "stacks", "python", "directory", default="backend"))
        )
    validate_ui_quality_config(data)
    validate_user_facing_errors_config(data)
    commands = get(data, "quality_gates", "commands", default={})
    if not isinstance(commands, dict):
        raise SystemExit("quality_gates.commands must be a mapping")
    for name, command in commands.items():
        if (
            not isinstance(command, str)
            or any(ord(character) < 32 for character in command)
            or len(command) > 2_000
        ):
            raise SystemExit(
                f"quality_gates.commands.{name} must be a bounded single-line string"
            )


POLICY_VALUES = {
    "static_security": {"required", "not_applicable"},
    "secret_scanning": {"required", "not_applicable"},
    "dependency_scanning": {"required", "not_applicable"},
    "dependency_vulnerability_threshold": {"moderate", "high", "critical"},
    "warning_treatment": {"errors", "warnings"},
    "authentication": {"required", "not_applicable"},
    "availability": {"required", "not_applicable"},
}


def load_policy_profile(root: Path | None = None) -> dict | None:
    """Load the optional project-owned profile; absence preserves legacy behavior."""
    root = ROOT if root is None else root
    path = root / ".ai/policy-profile.yaml"
    if not path.is_file():
        return None
    if path.is_symlink():
        raise SystemExit(".ai/policy-profile.yaml must not be a symbolic link")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise SystemExit(
            ".ai/policy-profile.yaml must stay below the repository root"
        ) from error
    if path.stat().st_size > 1_048_576:
        raise SystemExit(".ai/policy-profile.yaml must not exceed 1048576 bytes")
    data = load_yaml_subset(path)
    if data.get("schema_version") != 1:
        raise SystemExit(".ai/policy-profile.yaml schema_version must be 1")
    if data.get("mode") not in {"defaults", "recommended", "custom"}:
        raise SystemExit(
            ".ai/policy-profile.yaml mode must be defaults, recommended, or custom"
        )
    controls = data.get("controls")
    if not isinstance(controls, dict):
        raise SystemExit(".ai/policy-profile.yaml controls must be a mapping")
    unknown = sorted(set(controls) - set(POLICY_VALUES))
    if unknown:
        raise SystemExit("Unknown policy profile control(s): " + ", ".join(unknown))
    missing = sorted(set(POLICY_VALUES) - set(controls))
    if missing:
        raise SystemExit("Missing policy profile control(s): " + ", ".join(missing))
    for control, allowed in POLICY_VALUES.items():
        decision = controls[control]
        if not isinstance(decision, dict):
            raise SystemExit(f"Policy control {control} must be a mapping")
        value = decision.get("value")
        if value not in allowed:
            raise SystemExit(
                f"Unsupported policy value {control}={value!r}; allowed: "
                f"{sorted(allowed)}"
            )
        for field in ("source", "rationale", "scope"):
            if (
                not isinstance(decision.get(field), str)
                or not decision[field].strip()
                or any(ord(character) < 32 for character in decision[field])
                or len(decision[field]) > 500
            ):
                raise SystemExit(
                    f"Policy control {control}.{field} must be a bounded "
                    "single-line string"
                )
    return data


def policy_value(profile: dict | None, control: str, default: str) -> str:
    if profile is None:
        return default
    return str(get(profile, "controls", control, "value", default=default))


def require_string_list(value: object, label: str, allowed: set[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        raise SystemExit(f"{label} must be a non-empty inline list")
    if any(not isinstance(item, str) or item not in allowed for item in value):
        raise SystemExit(
            f"{label} contains unsupported values; allowed: {sorted(allowed)}"
        )
    if len(value) != len(set(value)):
        raise SystemExit(f"{label} must not contain duplicates")
    return value


def validate_user_facing_errors_config(data: dict) -> None:
    if "user_facing_errors" not in data:
        return
    enabled = get(data, "user_facing_errors", "enabled", default=True)
    if not isinstance(enabled, bool):
        raise SystemExit("user_facing_errors.enabled must be true or false")
    if enabled is False and set(data["user_facing_errors"]) == {"enabled"}:
        return

    frontend_enabled = get(
        data, "user_facing_errors", "frontend", "enabled", default=False
    )
    if not isinstance(frontend_enabled, bool):
        raise SystemExit("user_facing_errors.frontend.enabled must be true or false")

    catalog_path = get(
        data,
        "user_facing_errors",
        "catalog",
        "path",
        default="docs/errors/ERROR_CATALOG.md",
    )
    if not isinstance(catalog_path, str):
        raise SystemExit("user_facing_errors.catalog.path must be a string")
    validate_repository_path(catalog_path, "user_facing_errors.catalog.path")


def validate_ui_quality_config(data: dict) -> None:
    if "ui_quality" not in data:
        return
    enabled = get(data, "ui_quality", "enabled", default=False)
    if not isinstance(enabled, bool):
        raise SystemExit("ui_quality.enabled must be true or false")
    if enabled is False and set(data["ui_quality"]) == {"enabled"}:
        return

    artifact_types = {
        "static-mockup",
        "clickable-html-prototype",
        "react-mock-prototype",
        "storybook-composition",
        "external-design-reference",
    }
    require_string_list(
        get(data, "ui_quality", "design_artifacts", "allowed", default=[]),
        "ui_quality.design_artifacts.allowed",
        artifact_types,
    )
    approvals = require_string_list(
        get(data, "ui_quality", "require_human_approval_for", default=[]),
        "ui_quality.require_human_approval_for",
        {"design-class-2", "design-class-3"},
    )
    if "design-class-3" not in approvals:
        raise SystemExit(
            "ui_quality.require_human_approval_for must include design-class-3"
        )

    path_labels = (
        ("frontend.root", ("frontend", "root"), False),
        ("frontend.source_root", ("frontend", "source_root"), False),
        ("design_system.document", ("design_system", "document"), False),
        (
            "design_system.component_catalog",
            ("design_system", "component_catalog"),
            False,
        ),
    )
    resolved: dict[str, Path] = {}
    for label, keys, allow_empty in path_labels:
        value = str(get(data, "ui_quality", *keys, default=""))
        path = validate_repository_path(
            value, f"ui_quality.{label}", allow_empty=allow_empty
        )
        if path is not None:
            resolved[label] = path
    root = resolved["frontend.root"]
    source_root = resolved["frontend.source_root"]
    if get(data, "stacks", "react", "enabled", default=False) is True:
        react_root = validate_repository_path(
            str(get(data, "stacks", "react", "directory", default="frontend")),
            "stacks.react.directory",
        )
        if react_root is not None and root != react_root:
            print(
                "WARN: ui_quality.frontend.root differs from stacks.react.directory; "
                "source scanners use ui_quality.frontend.source_root.",
                file=sys.stderr,
            )
    try:
        source_root.relative_to(root)
    except ValueError as exc:
        raise SystemExit(
            "ui_quality.frontend.source_root must be inside ui_quality.frontend.root"
        ) from exc

    for label, keys in (("design_artifacts.storage", ("design_artifacts", "storage")),):
        value = str(get(data, "ui_quality", *keys, default=""))
        if "{change_id}" not in value:
            raise SystemExit(f"ui_quality.{label} must contain {{change_id}}")
        normalized = value.replace("{change_id}", "CHANGE_ID")
        path = validate_repository_path(normalized, f"ui_quality.{label}")
        if path is None:
            raise SystemExit(f"ui_quality.{label} must not be empty")
        work_root = (ROOT / ".ai/work").resolve()
        try:
            path.relative_to(work_root)
        except ValueError as exc:
            raise SystemExit(f"ui_quality.{label} must stay below .ai/work/") from exc
    fallback = get(
        data,
        "ui_quality",
        "browser_review",
        "fallback_when_unconfigured",
        default="manual-gate",
    )
    if fallback not in {"manual-gate", "error"}:
        raise SystemExit(
            "ui_quality.browser_review.fallback_when_unconfigured must be "
            "manual-gate or error"
        )
    viewports = get(data, "ui_quality", "browser_review", "viewports", default={})
    if not isinstance(viewports, dict) or not viewports:
        raise SystemExit("ui_quality.browser_review.viewports must not be empty")
    for name, viewport in viewports.items():
        if not isinstance(name, str) or not name or not isinstance(viewport, dict):
            raise SystemExit("ui_quality browser viewport entries are invalid")
        for dimension in ("width", "height"):
            dimension_value = viewport.get(dimension)
            if not isinstance(dimension_value, int) or dimension_value <= 0:
                raise SystemExit(
                    f"ui_quality.browser_review.viewports.{name}.{dimension} "
                    "must be a positive integer"
                )

    for label, keys in (
        ("browser_review.command", ("browser_review", "command")),
        ("browser_review.base_url", ("browser_review", "base_url")),
        ("visual_regression.command", ("visual_regression", "command")),
        ("accessibility.command", ("accessibility", "command")),
    ):
        if not isinstance(get(data, "ui_quality", *keys, default=""), str):
            raise SystemExit(f"ui_quality.{label} must be a string")

    visual_regression_enabled = get(
        data, "ui_quality", "visual_regression", "enabled", default=False
    )
    if not isinstance(visual_regression_enabled, bool):
        raise SystemExit("ui_quality.visual_regression.enabled must be true or false")
    accessibility_enabled = get(
        data, "ui_quality", "accessibility", "enabled", default=False
    )
    if not isinstance(accessibility_enabled, bool):
        raise SystemExit("ui_quality.accessibility.enabled must be true or false")

    if visual_regression_enabled:
        command = get(data, "ui_quality", "visual_regression", "command", default="")
        if not isinstance(command, str) or not command.strip():
            raise SystemExit(
                "ui_quality.visual_regression.command is required when enabled"
            )


def validate_repository_path(
    value: str, label: str, *, allow_empty: bool = False
) -> Path | None:
    value = value.strip()
    if not value:
        if allow_empty:
            return None
        raise SystemExit(f"{label} must not be empty")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SystemExit(f"{label} must stay below the repository root: {value!r}")
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(
            f"{label} must stay below the repository root: {value!r}"
        ) from exc
    return resolved


def validate_python_package_directory(value: str) -> None:
    path = Path(value.strip())
    if not path.parts or any(
        not part.isidentifier() or part.startswith("_") for part in path.parts
    ):
        raise SystemExit(
            "stacks.python.directory must be a repository-relative Python "
            "source/package path whose segments are importable identifiers, "
            f"for example 'backend' or 'src/myapp': {value!r}"
        )


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def chain(commands: list[str]) -> str:
    return " && ".join(f"({command})" for command in commands)


IGNORED_SCRIPT_DIRS = {
    ".git",
    ".ai",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "target",
}


def project_shell_scripts() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.sh")
        if path.is_file()
        and not any(part in IGNORED_SCRIPT_DIRS for part in path.parts)
    ]


def generate_env(data: dict, policy_profile: dict | None = None) -> str:
    setup: list[str] = []
    fmt_check: list[str] = []
    fmt_apply: list[str] = []
    lint: list[str] = []
    tests: list[str] = []
    security: list[str] = []
    dependency_scans: list[str] = []
    build: list[str] = []
    dependency_threshold = policy_value(
        policy_profile, "dependency_vulnerability_threshold", "high"
    )
    warnings_as_errors = (
        policy_value(policy_profile, "warning_treatment", "errors") == "errors"
    )

    if get(data, "stacks", "python", "enabled", default=False):
        python_version = runtime_versions(data)["python"]
        uv = f"UV_PYTHON={shell_quote(python_version)} uv"
        run = f"{uv} run --locked"
        directory = str(get(data, "stacks", "python", "directory", default="backend"))
        target = shell_quote(directory)
        setup += [f"{uv} sync --locked --all-groups"]
        fmt_check += [f"{run} ruff format --check {target} tests"]
        fmt_apply += [f"{run} ruff format {target} tests"]
        lint += [
            f"{run} ruff check {target} tests",
            f"{run} mypy {target} tests",
        ]
        tests += [f"{run} python -m pytest"]
        security += [f"{run} bandit -q -r {target}"]
        dependency_scans += [f"{run} pip-audit"]
        build += [f"{uv} build"]

    if get(data, "stacks", "react", "enabled", default=False):
        directory = str(get(data, "stacks", "react", "directory", default="frontend"))
        manager = str(get(data, "stacks", "react", "package_manager", default="npm"))
        runner = {"npm": "npm run", "pnpm": "pnpm run", "yarn": "yarn"}.get(
            manager, f"{manager} run"
        )
        prefix = f"cd {shell_quote(directory)} && "
        install_command = {
            "npm": "npm ci",
            "pnpm": "pnpm install --frozen-lockfile",
            "yarn": "yarn install --immutable",
        }[manager]
        setup += [prefix + install_command]
        fmt_check += [prefix + runner + " format:check"]
        fmt_apply += [prefix + runner + " format"]
        lint += [prefix + runner + " lint", prefix + runner + " typecheck"]
        tests += [prefix + runner + " test"]
        audit_command = {
            "npm": f"npm audit --audit-level={dependency_threshold}",
            "pnpm": f"pnpm audit --audit-level={dependency_threshold}",
            "yarn": f"yarn npm audit --severity {dependency_threshold}",
        }[manager]
        dependency_scans += [prefix + audit_command]
        build += [prefix + runner + " build"]

    if get(data, "stacks", "bash", "enabled", default=False):
        shell_script_count = len(project_shell_scripts())
        lint += [
            "find . -type f -name '*.sh' -not -path './.git/*' -not -path './.ai/*' -print0 | xargs -0 -r shellcheck"
        ]
        if shell_script_count:
            tests += [
                "test -d tests/shell || { printf 'Bash scripts were found, but tests/shell is missing. Add Bats tests or disable stacks.bash.enabled.\\n' >&2; exit 1; }; bats tests/shell"
            ]

    if get(data, "stacks", "dotnet", "enabled", default=False):
        solution = str(get(data, "stacks", "dotnet", "solution", default="") or ".")
        test_project = str(get(data, "stacks", "dotnet", "test_project"))
        target = shell_quote(solution)
        test_target = shell_quote(test_project)
        setup += [f"dotnet restore {target} --locked-mode"]
        fmt_check += [f"dotnet format {target} --verify-no-changes"]
        fmt_apply += [f"dotnet format {target}"]
        warning_flag = " -warnaserror" if warnings_as_errors else ""
        lint += [f"dotnet build {target} --no-restore{warning_flag}"]
        tests += [
            "result_dir=$(mktemp -d) && "
            "trap 'rm -rf \"$result_dir\"' EXIT && "
            f"dotnet test {test_target} --no-restore "
            '--logger "trx;LogFileName=agent-template.trx" '
            '--results-directory "$result_dir" && '
            'grep -Eq \'total="[1-9][0-9]*"\' "$result_dir/agent-template.trx"'
        ]
        vulnerable_packages = (
            f"dotnet list {target} package --vulnerable --include-transitive"
        )
        dependency_scans += [vulnerable_packages]
        build += [f"dotnet build {target} --no-restore"]
        powershell_files = [
            path
            for pattern in ("*.ps1", "*.psm1", "*.psd1")
            for path in ROOT.rglob(pattern)
            if path != ROOT / ".ai" / "tools" / "create-project.ps1"
            and not any(
                part in {".git", ".venv", "node_modules"} for part in path.parts
            )
        ]
        if powershell_files:
            lint += [
                'pwsh -NoProfile -Command "Invoke-ScriptAnalyzer -Path . -Recurse -Severity Warning,Error"'
            ]
            tests += [
                "find tests/powershell -type f -name '*.Tests.ps1' -print -quit 2>/dev/null | grep -q . && "
                'pwsh -NoProfile -Command "Invoke-Pester tests/powershell -CI"'
            ]

    if policy_profile is not None:
        if (
            policy_value(policy_profile, "static_security", "required")
            == "not_applicable"
        ):
            security = []
        if policy_value(policy_profile, "secret_scanning", "required") == "required":
            security += ["gitleaks detect --source . --no-banner"]
        if (
            policy_value(policy_profile, "dependency_scanning", "required")
            == "not_applicable"
        ):
            dependency_scans = []

    custom_commands = get(data, "quality_gates", "commands", default={})
    command_lists = {
        "setup": setup,
        "format_check": fmt_check,
        "format_apply": fmt_apply,
        "lint": lint,
        "test": tests,
        "security": security,
        "dependency_scan": dependency_scans,
        "build": build,
    }
    for gate, command in custom_commands.items():
        if command:
            command_lists[gate].append(command)

    commands = {
        "SETUP_CMD": chain(setup),
        "FORMAT_CHECK_CMD": chain(fmt_check),
        "FORMAT_APPLY_CMD": chain(fmt_apply),
        "LINT_CMD": chain(lint),
        "TEST_CMD": chain(tests),
        "SECURITY_CMD": chain(security),
        "DEPENDENCY_SCAN_CMD": chain(dependency_scans),
        "BUILD_CMD": chain(build),
        "BROWSER_REVIEW_CMD": str(
            get(data, "ui_quality", "browser_review", "command", default="")
        ),
        "VISUAL_REGRESSION_CMD": str(
            get(data, "ui_quality", "visual_regression", "command", default="")
        ),
        "VISUAL_REGRESSION_ENABLED": (
            "1"
            if get(data, "ui_quality", "visual_regression", "enabled", default=False)
            else "0"
        ),
        "ACCESSIBILITY_CMD": str(
            get(data, "ui_quality", "accessibility", "command", default="")
        ),
        "ACCESSIBILITY_ENABLED": (
            "1"
            if get(data, "ui_quality", "accessibility", "enabled", default=False)
            else "0"
        ),
    }
    require_security = bool(security)
    require_dependency_scanners = bool(dependency_scans)
    if policy_profile is not None:
        require_security = any(
            policy_value(policy_profile, control, "required") == "required"
            for control in ("static_security", "secret_scanning")
        )
        require_dependency_scanners = (
            policy_value(policy_profile, "dependency_scanning", "required")
            == "required"
        )
    flags = {
        "REQUIRE_SETUP": bool(setup),
        "REQUIRE_FORMAT_CHECK": bool(fmt_check),
        "REQUIRE_LINT": bool(lint),
        "REQUIRE_TEST": bool(tests),
        "REQUIRE_SECURITY": require_security,
        "REQUIRE_DEPENDENCY_POLICY": True,
        "REQUIRE_DEPENDENCY_SCANNERS": require_dependency_scanners,
        "REQUIRE_BUILD": bool(build),
    }
    result = [
        "# Generated by .ai/tools/bootstrap.py from .ai/project.yaml.",
        "# Commit this file; put machine-local overrides in .ai/config/project.env.",
        "",
    ]
    result += [f"{key}={shell_quote(value)}" for key, value in commands.items()]
    result += [f"{key}={1 if value else 0}" for key, value in flags.items()]
    return "\n".join(result) + "\n"


def run_command(command: list[str], cwd: Path) -> None:
    print(f"[bootstrap] Running in {cwd}: {shlex.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)  # nosec B603


def executable_version(executable: str, label: str) -> str:
    result = subprocess.run(  # nosec B603
        [executable, "--version"],
        text=True,
        capture_output=True,
        check=True,
    )
    match = re.search(
        r"(?<![0-9A-Za-z.+-])(\d+\.\d+\.\d+)(?![0-9A-Za-z.+-])",
        result.stdout.strip(),
    )
    if match is None:
        raise SystemExit(f"{label} did not report a numeric three-part version")
    return match.group(1)


def python_package_name(specification: str) -> str:
    return (
        re.split(r"[<>=!~;\[]", specification, maxsplit=1)[0]
        .strip()
        .lower()
        .replace("_", "-")
    )


def npm_package_name(specification: str) -> str:
    if specification.startswith("@"):
        return (
            specification.rsplit("@", 1)[0]
            if specification.count("@") > 1
            else specification
        )
    return specification.split("@", 1)[0]


def npm_package_requirement(specification: str) -> str:
    name = npm_package_name(specification)
    marker = len(name) + 1
    return specification[marker:] if len(specification) >= marker else ""


def validate_python_lock_resolutions() -> None:
    lock_path = ROOT / "uv.lock"
    if not lock_path.is_file():
        raise SystemExit("Python bootstrap did not create the exact uv.lock resolution")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = lock.get("package", [])
    versions: dict[str, set[str]] = {}
    if isinstance(packages, list):
        for package in packages:
            if not isinstance(package, dict):
                continue
            name, version = package.get("name"), package.get("version")
            if isinstance(name, str) and isinstance(version, str):
                versions.setdefault(name.lower().replace("_", "-"), set()).add(version)
    for specification in PYTHON_DEV_DEPENDENCIES:
        name = python_package_name(specification)
        requirement = specification[len(name) :]
        resolved = sorted(
            version
            for version in versions.get(name, set())
            if version_satisfies(version, requirement)
        )
        if not resolved:
            raise SystemExit(
                f"uv.lock has no exact {name} resolution satisfying {requirement!r}"
            )
        print(
            f"[bootstrap] Resolved {name} {', '.join(resolved)} within "
            f"requirement {requirement!r}"
        )


def validate_react_lock_resolutions(frontend: Path) -> None:
    for specification in REACT_QUALITY_DEPENDENCIES:
        name = npm_package_name(specification)
        requirement = npm_package_requirement(specification)
        resolved = sorted(
            version
            for version in npm_lock_versions(frontend, name, requirement)
            if npm_version_satisfies(version, requirement)
        )
        if not resolved:
            raise SystemExit(
                f"React lockfile has no exact {name} resolution satisfying "
                f"{requirement!r}"
            )
        print(
            f"[bootstrap] Resolved {name} {', '.join(resolved)} within "
            f"requirement {requirement!r}"
        )


def validate_existing_package_manager(
    frontend: Path, manager: str, requirement: str | None
) -> None:
    package_json = frontend / "package.json"
    if not package_json.is_file():
        return
    data = json.loads(package_json.read_text(encoding="utf-8"))
    declared = data.get("packageManager")
    if declared is None:
        return
    if not isinstance(declared, str):
        raise SystemExit(f"packageManager must be a string: {package_json}")
    match = re.fullmatch(r"([^@]+)@(\d+\.\d+\.\d+)(?:\+[^\s]+)?", declared)
    if match is None or match.group(1) != manager:
        raise SystemExit(
            f"Existing packageManager {declared!r} conflicts with configured "
            f"package manager {manager!r}"
        )
    if requirement is not None and not version_satisfies(match.group(2), requirement):
        raise SystemExit(
            f"Existing packageManager {declared!r} does not satisfy "
            f"tool_requirements.{manager} {requirement!r}"
        )


def ensure_setuptools_package_discovery(pyproject: Path, package_path: str) -> None:
    text = pyproject.read_text(encoding="utf-8")
    parsed = tomllib.loads(text)
    setuptools = parsed.get("tool", {}).get("setuptools", {})
    if "packages" in setuptools or "py-modules" in setuptools:
        return
    path = Path(package_path)
    source_root = path.parent.as_posix()
    where = f'where = ["{source_root}"]\n' if source_root != "." else ""
    pyproject.write_text(
        text.rstrip()
        + "\n\n[tool.setuptools.packages.find]\n"
        + where
        + f'include = ["{path.name}"]\n',
        encoding="utf-8",
    )


def enabled_stack_names(data: dict) -> list[str]:
    stacks = get(data, "stacks", default={})
    if not isinstance(stacks, dict):
        return []
    return [
        name
        for name, settings in stacks.items()
        if isinstance(settings, dict) and settings.get("enabled") is True
    ]


def bootstrap_python(data: dict) -> None:
    if not get(data, "stacks", "python", "enabled", default=False):
        return
    directory = str(get(data, "stacks", "python", "directory", default="backend"))
    backend = validate_repository_path(directory, "stacks.python.directory")
    if backend is None:
        raise SystemExit("stacks.python.directory must not be empty")
    package_target_existed = backend.exists()
    if package_target_existed and not backend.is_dir():
        raise SystemExit(
            f"Configured Python source/package path is not a directory: {backend}"
        )
    python_version = runtime_versions(data)["python"]

    uv_path = shutil.which("uv")
    if not uv_path:
        raise SystemExit(
            "uv is required for the configured Python bootstrap but was not found on PATH"
        )
    # uv_path is resolved to an executable and no shell is used.
    installed_uv = executable_version(uv_path, "uv")
    uv_requirement = tool_requirements(data)["uv"]
    if not version_satisfies(installed_uv, uv_requirement):
        raise SystemExit(
            f"This template requires uv {uv_requirement}, but PATH provides "
            f"{installed_uv}. Install a compatible version before bootstrap."
        )

    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        run_command(
            [
                "uv",
                "init",
                "--python",
                python_version,
                "--bare",
                "--no-workspace",
                "--no-pin-python",
                ".",
            ],
            ROOT,
        )

    parsed = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    declared = parsed.get("dependency-groups", {}).get("dev", [])
    declared_names = {
        re.split(r"[<>=!~;\[]", str(item), maxsplit=1)[0]
        .strip()
        .lower()
        .replace("_", "-")
        for item in declared
    }
    missing = [
        package
        for package in PYTHON_DEV_DEPENDENCIES
        if python_package_name(package) not in declared_names
    ]
    if missing:
        run_command(["uv", "add", "--python", python_version, "--dev", *missing], ROOT)
    else:
        run_command(["uv", "sync", "--python", python_version], ROOT)
    validate_python_lock_resolutions()

    if not package_target_existed:
        backend.mkdir(parents=True)
        init_file = backend / "__init__.py"
        init_file.write_text('"""Application backend package."""\n', encoding="utf-8")

        tests_dir = ROOT / "tests"
        tests_dir.mkdir(exist_ok=True)
        package_name = backend.name
        smoke_test = tests_dir / f"test_{package_name}.py"
        ensure_setuptools_package_discovery(pyproject, directory)
        if not smoke_test.exists():
            smoke_test.write_text(
                f"import {package_name}\n\n\n"
                "def test_backend_package_imports() -> None:\n"
                f"    assert {package_name} is not None\n",
                encoding="utf-8",
            )


def package_manager_commands(
    manager: str, directory: str, template: str, creator_version: str
) -> tuple[list[str], list[str], list[str]]:
    if manager == "npm":
        return (
            [
                "npm",
                "create",
                f"vite@{creator_version}",
                directory,
                "--",
                "--template",
                template,
                "--no-interactive",
            ],
            ["npm", "install"],
            ["npm", "install", "--save-dev"],
        )
    if manager == "pnpm":
        return (
            [
                "pnpm",
                "dlx",
                f"create-vite@{creator_version}",
                directory,
                "--template",
                template,
                "--no-interactive",
            ],
            ["pnpm", "install"],
            ["pnpm", "add", "--save-dev"],
        )
    return (
        [
            "yarn",
            "dlx",
            f"create-vite@{creator_version}",
            directory,
            "--template",
            template,
            "--no-interactive",
        ],
        ["yarn", "install"],
        ["yarn", "add", "--dev"],
    )


def configure_react_quality(
    frontend: Path, manager: str = "npm", manager_version: str = ""
) -> None:
    package_json = frontend / "package.json"
    if not package_json.exists():
        raise SystemExit(f"React bootstrap did not create {package_json}")
    original = package_json.read_text(encoding="utf-8")
    data = json.loads(original)
    changed = False
    if manager == "pnpm":
        if "packageManager" not in data:
            data["packageManager"] = (
                f"pnpm@{manager_version or PNPM_VERSION_RESOLUTION}"
            )
            changed = True
    elif manager == "yarn":
        if "packageManager" not in data:
            data["packageManager"] = (
                f"yarn@{manager_version or YARN_VERSION_RESOLUTION}"
            )
            changed = True
    scripts = data.setdefault("scripts", {})
    if not isinstance(scripts, dict):
        raise SystemExit(f"package.json scripts must be an object: {package_json}")
    for name, command in {
        "format": "prettier --write .",
        "format:check": "prettier --check .",
        "typecheck": "tsc -b",
        "test": "vitest run",
        "test:watch": "vitest",
    }.items():
        if name not in scripts:
            scripts[name] = command
            changed = True
    if changed:
        package_json.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    test_dir = frontend / "src" / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    setup = test_dir / "setup.ts"
    if not setup.exists():
        setup.write_text(
            'import "@testing-library/jest-dom/vitest";\n', encoding="utf-8"
        )

    smoke_test = frontend / "src" / "App.test.tsx"
    if not smoke_test.exists():
        smoke_test.write_text(
            'import { render } from "@testing-library/react";\n'
            'import { expect, test } from "vitest";\n'
            'import App from "./App";\n\n'
            'test("renders the application shell", () => {\n'
            "  const { container } = render(<App />);\n"
            "  expect(container).not.toBeEmptyDOMElement();\n"
            "});\n",
            encoding="utf-8",
        )

    vitest_config = frontend / "vitest.config.ts"
    if not vitest_config.exists():
        vitest_config.write_text(
            'import react from "@vitejs/plugin-react";\n'
            'import { defineConfig } from "vitest/config";\n\n'
            "export default defineConfig({\n"
            "  plugins: [react()],\n"
            "  test: {\n"
            '    environment: "jsdom",\n'
            '    setupFiles: ["./src/test/setup.ts"],\n'
            "  },\n"
            "});\n",
            encoding="utf-8",
        )


def bootstrap_react(data: dict) -> None:
    if not get(data, "stacks", "react", "enabled", default=False):
        return

    directory = str(get(data, "stacks", "react", "directory", default="frontend"))
    manager = str(get(data, "stacks", "react", "package_manager", default="npm"))
    manager_path = shutil.which(manager)
    if not manager_path:
        raise SystemExit(
            f"{manager} is required for the configured React bootstrap but was not found on PATH"
        )
    node_path = shutil.which("node")
    if not node_path:
        raise SystemExit("Node.js is required for the configured React bootstrap")
    expected_node = runtime_versions(data)["node"]
    # node_path is resolved to an executable and no shell is used.
    installed_node = (
        subprocess.run(  # nosec
            [node_path, "--version"],
            text=True,
            capture_output=True,
            check=True,
        )
        .stdout.strip()
        .removeprefix("v")
    )
    node_requirement = parse_runtime_requirement(expected_node, "node")
    if node_requirement is None or not runtime_satisfies(
        installed_node, "node", [node_requirement]
    ):
        raise SystemExit(
            f"Configured Node.js requirement in .ai/project.yaml is {expected_node}, "
            f"but PATH provides {installed_node}. Install a compatible version "
            "before bootstrap."
        )

    manager_version = ""
    configured_tools = tool_requirements(data)
    manager_requirement = {
        "pnpm": configured_tools["pnpm"],
        "yarn": configured_tools["yarn"],
    }.get(manager)
    if manager_requirement is not None:
        manager_version = executable_version(manager_path, manager)
        if not version_satisfies(manager_version, manager_requirement):
            raise SystemExit(
                f"This template requires {manager} {manager_requirement}, but PATH "
                f"provides {manager_version}. Install a compatible version before "
                "bootstrap."
            )
        print(
            f"[bootstrap] Resolved {manager} executable {manager_version} within "
            f"requirement {manager_requirement!r}"
        )

    frontend = validate_repository_path(directory, "stacks.react.directory")
    if frontend is None:
        raise SystemExit("stacks.react.directory must not be empty")
    validate_existing_package_manager(frontend, manager, manager_requirement)
    vite_resolution = select_exact_version(configured_tools["vite"])
    if vite_resolution is None:
        raise SystemExit(
            "tool_requirements.vite needs an exact or inclusive-lower-bound "
            "requirement so bootstrap can preview the exact scaffold resolution"
        )
    create_cmd, install_cmd, add_dev_cmd = package_manager_commands(
        manager,
        directory,
        REACT_TEMPLATE,
        vite_resolution,
    )
    created_frontend = False
    if not (frontend / "package.json").exists():
        if frontend.exists() and any(frontend.iterdir()):
            raise SystemExit(
                f"Cannot scaffold React into non-empty directory without package.json: {frontend}"
            )
        run_command(create_cmd, ROOT)
        created_frontend = True

    run_command(install_cmd, frontend)

    package_data = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    installed = set(package_data.get("dependencies", {})) | set(
        package_data.get("devDependencies", {})
    )
    missing = [
        package
        for package in REACT_QUALITY_DEPENDENCIES
        if npm_package_name(package) not in installed
    ]
    if missing:
        run_command([*add_dev_cmd, *missing], frontend)
    validate_react_lock_resolutions(frontend)
    configure_react_quality(frontend, manager, manager_version)
    if created_frontend:
        format_command = {
            "npm": ["npm", "run", "format"],
            "pnpm": ["pnpm", "run", "format"],
            "yarn": ["yarn", "format"],
        }[manager]
        run_command(format_command, frontend)


def update_context(data: dict) -> None:
    path = ROOT / ".ai/PROJECT_CONTEXT.md"
    if not path.is_file():
        raise SystemExit(
            "Expected .ai/PROJECT_CONTEXT.md is missing; restore it before bootstrap."
        )
    text = path.read_text(encoding="utf-8")
    marker = "## Bootstrap configuration"
    name = get(data, "project", "name", default="CHANGE_ME")
    stacks = ", ".join(enabled_stack_names(data)) or "none"
    runtimes = runtime_versions(data)
    ui_state = (
        "enabled" if get(data, "ui_quality", "enabled", default=False) else "disabled"
    )
    error_state = (
        "enabled"
        if get(data, "user_facing_errors", "enabled", default=False)
        else "disabled"
    )
    error_frontend_state = (
        "enabled"
        if get(
            data,
            "user_facing_errors",
            "frontend",
            "enabled",
            default=False,
        )
        else "disabled"
    )
    orchestration_state = (
        "enabled"
        if get(data, "orchestration", "enabled", default=False)
        else "disabled"
    )
    block = (
        f"\n{marker}\n\n"
        f"- Project name: `{name}`\n"
        f"- Enabled stacks: `{stacks}`\n"
        f"- Python runtime: `{runtimes['python']}`\n"
        f"- Node.js runtime: `{runtimes['node']}`\n"
        f"- UI quality workflow: {ui_state}\n"
        f"- Repository-native orchestration: {orchestration_state}\n"
        f"- User-facing error handling: {error_state}; frontend checks "
        f"{error_frontend_state}\n"
        "- Configuration source: `.ai/project.yaml`\n"
    )
    text = (
        text.split(marker)[0].rstrip() + block
        if marker in text
        else text.rstrip() + "\n" + block
    )
    path.write_text(text, encoding="utf-8")


def update_next_steps() -> None:
    path = ROOT / ".ai/NEXT_STEPS.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if "Run bootstrap and commit the generated" not in text:
        return
    path.write_text(
        "# Next steps\n\n"
        "Keep at most 5-10 prioritized actionable items. Remove completed or obsolete entries.\n\n"
        "## Prioritized\n\n"
        "1. Complete the purpose and project-specific fields in `.ai/PROJECT_CONTEXT.md`.\n"
        "2. Replace the private reporting contact in `SECURITY.md`.\n"
        "3. Review the seeded decisions in `.ai/policies/QUALITY_GATES.md`, set "
        "`Project decisions reviewed: yes`, and configure branch protection.\n\n"
        "## Blockers\n\n"
        "- Full verification remains blocked until the required project-readiness fields are complete.\n\n"
        "## Residual risks\n\n"
        "- Stack-specific verification has not yet been exercised for this concrete project.\n",
        encoding="utf-8",
    )


def create_decisions_scaffold() -> None:
    path = ROOT / ".ai/DECISIONS.md"
    if path.exists():
        return
    path.write_text(
        "# Operational decisions\n\n"
        "Use this file only for small current operating decisions that do not justify an ADR. "
        "Remove decisions that no longer apply.\n\n"
        "| Date | Decision | Rationale | Scope/source |\n"
        "|---|---|---|---|\n",
        encoding="utf-8",
    )


def create_project_readme(data: dict) -> bool:
    path = ROOT / "README.md"
    if path.exists():
        return False
    name = str(get(data, "project", "name", default="Project"))
    stacks = ", ".join(enabled_stack_names(data)) or "none"
    orchestration = ""
    if get(data, "orchestration", "enabled", default=False) is True:
        orchestration = """
## Repository-native orchestration

The optional orchestrator is enabled. It runs the canonical lifecycle through
isolated agent invocations while the trusted host retains verification, browser,
owner-decision, lease, and promotion control.

```bash
python .ai/tools/orchestrate.py doctor
python .ai/tools/orchestrate.py start --file backlog.md
python .ai/tools/orchestrate.py status
python .ai/tools/orchestrate.py resume
python .ai/tools/orchestrate.py decisions
cp .ai/templates/OWNER_DECISION.md /tmp/owner-decision.md
python .ai/tools/orchestrate.py decide --decision-file /tmp/owner-decision.md
python .ai/tools/orchestrate.py validate
```

See `.ai/policies/ORCHESTRATION.md` for Codex configuration, external-processing
approval, trust boundaries, recovery, the trusted host browser gate used by
orchestrated visual review, legacy command-executor requirements, and why decision
files stay outside the repository. `doctor` runs one synthetic Codex turn without
project source or queue content to validate the production Exec flags and schema.
"""
    content = f"""# {name}

## Purpose

Describe what this project does, who it serves, and the problem it solves.

## Technology

Enabled stacks: `{stacks}`. See `.ai/project.yaml` and `.ai/PROJECT_CONTEXT.md` for project constraints.

## Setup

Document the exact installation and environment setup for users and developers.

## Run

Document how to start the application or execute its primary workflow.

## Verification

Run the repository quality gates with:

```bash
./.ai/tools/verify.sh
```

## Configuration

Document required environment variables and configuration files. Do not place secrets in this repository.

## Architecture

See `docs/architecture/overview.md` and `docs/architecture/decisions/`.

## UI quality

When `.ai/project.yaml` enables UI quality, maintain
`docs/design/DESIGN_SYSTEM.md` and `docs/design/COMPONENT_CATALOG.md` and follow
`.ai/policies/UI_QUALITY.md`. Selected UI tools must be installed and locked before
their gates can pass.

{orchestration}

## Security

See `.ai/policies/SECURITY_GUIDELINES.md` for engineering rules and `SECURITY.md`
for the private vulnerability-reporting process.

    """
    path.write_text(content, encoding="utf-8")
    return True


def create_idea() -> None:
    idea = ROOT / ".idea"
    idea.mkdir(exist_ok=True)
    (idea / "vcs.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<project version="4">\n  <component name="VcsDirectoryMappings">\n    <mapping directory="$PROJECT_DIR$" vcs="Git" />\n  </component>\n</project>\n',
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap configured project stacks and generated defaults."
    )
    parser.add_argument(
        "--steps",
        default="configure,python,react",
        help="Comma-separated subset of configure,python,react (default: all).",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Skip stack scaffolding and dependency installation.",
    )
    arguments = parser.parse_args(argv)
    steps = {item.strip() for item in arguments.steps.split(",") if item.strip()}
    unknown = steps - {"configure", "python", "react"}
    if unknown or not steps:
        parser.error(
            "--steps must contain configure, python, and/or react; unknown: "
            + ", ".join(sorted(unknown))
        )
    if CONFIG.is_symlink():
        raise SystemExit(".ai/project.yaml must not be a symbolic link")
    try:
        CONFIG.resolve().relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit(
            ".ai/project.yaml must stay below the repository root"
        ) from error
    if CONFIG.stat().st_size > 1_048_576:
        raise SystemExit(".ai/project.yaml must not exceed 1048576 bytes")
    data = load_yaml_subset(CONFIG)
    validate_config(data)
    policy_profile = load_policy_profile()
    installed: list[str] = []
    if not arguments.no_install and "python" in steps:
        bootstrap_python(data)
        installed.append("python")
    if not arguments.no_install and "react" in steps:
        bootstrap_react(data)
        installed.append("react")
    if "configure" in steps:
        created_readme = create_project_readme(data)
        (ROOT / ".ai/config/project.defaults.env").write_text(
            generate_env(data, policy_profile), encoding="utf-8"
        )
        update_context(data)
        update_next_steps()
        create_decisions_scaffold()
        create_idea()
        for path in (ROOT / ".ai/tools").glob("*.sh"):
            path.chmod(path.stat().st_mode | 0o111)
        print(
            "[bootstrap] Created README.md"
            if created_readme
            else "[bootstrap] Kept existing README.md"
        )
        print("[bootstrap] Generated versioned .ai/config/project.defaults.env")
        print("[bootstrap] Updated project context and readiness files")
        print("[bootstrap] Created local IDE state and decisions when missing")
    if installed:
        print("[bootstrap] Initialized project tooling for: " + ", ".join(installed))
    elif arguments.no_install:
        print("[bootstrap] Skipped scaffolding and dependency installation")
    print("[bootstrap] AI rules are ready under .aiassistant/rules/")
    if "configure" in steps:
        print("[bootstrap] One manual IntelliJ setting remains:")
        print("  Settings > Tools > AI Assistant > Project Settings")
        print(f"  Path to rules for AI Self-Review: $PROJECT_DIR$/{SELF_REVIEW_RULES}")
    print("[bootstrap] Install the required tools, then run ./.ai/tools/verify.sh")


if __name__ == "__main__":
    main()
