#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shlex
import shutil

# All subprocess calls use explicit argument arrays and never enable a shell.
import subprocess  # nosec B404
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import get, load_yaml_subset  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".ai" / "project.yaml"

# Pinned tool versions. These are intentionally exact for reproducible bootstraps.
# When updating, bump every copy together and re-run template verification:
#   - UV_VERSION here and `version:` in .github/workflows/ci.yml
#   - PYTHON_DEV_DEPENDENCIES here and the pinned ruff/mypy/bandit in
#     .ai/tools/verify-template.sh
#   - VITE_VERSION / PNPM_VERSION / YARN_VERSION /
#     REACT_QUALITY_DEPENDENCIES here
#   - runtime pins in .python-version and .node-version
# Verify each version resolves on its registry before committing the bump.
UV_VERSION = "0.11.29"
VITE_VERSION = "9.1.1"
PNPM_VERSION = "11.15.0"
YARN_VERSION = "4.17.1"
REACT_TEMPLATE = "react-ts"
SELF_REVIEW_RULES = ".aiassistant/review/self-review.md"
PYTHON_DEV_DEPENDENCIES = (
    "ruff==0.15.22",
    "mypy==2.3.0",
    "pytest==9.1.1",
    "pytest-cov==7.1.0",
    "bandit==1.9.4",
    "pip-audit==2.10.1",
    "build==1.5.0",
)
REACT_QUALITY_DEPENDENCIES = (
    "prettier@3.9.5",
    "vitest@4.1.10",
    "jsdom@29.1.1",
    "@testing-library/react@16.3.2",
    "@testing-library/jest-dom@6.9.1",
    "@testing-library/user-event@14.6.1",
)
CONFIG_SCHEMA = {
    "project": {"name": None},
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
    "engineering_knowledge": {"enabled": None},
    "documentation": {
        "budgets": {
            "agents_md_lines": None,
            "project_context_lines": None,
            "current_plan_lines": None,
            "next_steps_items": None,
            "active_work_item_lines": None,
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
    if len(path.parts) != 1:
        raise SystemExit(
            "stacks.python.directory must be one top-level importable Python package "
            f"name, for example 'backend': {value!r}"
        )
    package_name = path.name
    if not package_name.isidentifier() or package_name.startswith("_"):
        raise SystemExit(
            "stacks.python.directory must be one top-level importable Python package "
            f"name, for example 'backend': {value!r}"
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


def generate_env(data: dict) -> str:
    setup: list[str] = []
    fmt_check: list[str] = []
    fmt_apply: list[str] = []
    lint: list[str] = []
    tests: list[str] = []
    security: list[str] = []
    dependency_scans: list[str] = []
    build: list[str] = []

    if get(data, "stacks", "python", "enabled", default=False):
        run = "uv run --locked"
        directory = str(get(data, "stacks", "python", "directory", default="backend"))
        target = shell_quote(directory)
        setup += ["uv sync --locked --all-groups"]
        fmt_check += [f"{run} ruff format --check {target} tests"]
        fmt_apply += [f"{run} ruff format {target} tests"]
        lint += [
            f"{run} ruff check {target} tests",
            f"{run} mypy {target} tests",
        ]
        tests += [f"{run} python -m pytest"]
        security += [f"{run} bandit -q -r {target}"]
        dependency_scans += [f"{run} pip-audit"]
        build += ["uv build"]

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
        dependency_scans += [prefix + manager + " audit --audit-level=high"]
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
        lint += [f"dotnet build {target} --no-restore -warnaserror"]
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

    commands = {
        "SETUP_CMD": chain(setup),
        "FORMAT_CHECK_CMD": chain(fmt_check),
        "FORMAT_APPLY_CMD": chain(fmt_apply),
        "LINT_CMD": chain(lint),
        "TEST_CMD": chain(tests),
        "SECURITY_CMD": chain(security),
        "DEPENDENCY_SCAN_CMD": chain(dependency_scans),
        "BUILD_CMD": chain(build),
    }
    flags = {
        "REQUIRE_SETUP": bool(setup),
        "REQUIRE_FORMAT_CHECK": bool(fmt_check),
        "REQUIRE_LINT": bool(lint),
        "REQUIRE_TEST": bool(tests),
        "REQUIRE_SECURITY": bool(security),
        "REQUIRE_DEPENDENCY_POLICY": True,
        "REQUIRE_DEPENDENCY_SCANNERS": bool(dependency_scans),
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


def ensure_setuptools_package_discovery(pyproject: Path, package_name: str) -> None:
    text = pyproject.read_text(encoding="utf-8")
    parsed = tomllib.loads(text)
    setuptools = parsed.get("tool", {}).get("setuptools", {})
    if "packages" in setuptools or "py-modules" in setuptools:
        return
    pyproject.write_text(
        text.rstrip()
        + "\n\n[tool.setuptools.packages.find]\n"
        + f'include = ["{package_name}"]\n',
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

    uv_path = shutil.which("uv")
    if not uv_path:
        raise SystemExit(
            "uv is required for the configured Python bootstrap but was not found on PATH"
        )
    # uv_path is resolved to an executable and no shell is used.
    installed_uv_output = subprocess.run(  # nosec
        [uv_path, "--version"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    installed_uv = installed_uv_output.removeprefix("uv ").split()[0]
    if installed_uv != UV_VERSION:
        raise SystemExit(
            f"This template requires uv {UV_VERSION}, but PATH provides {installed_uv}. "
            "Install the required version before bootstrap."
        )

    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        run_command(["uv", "init", "--bare", "--no-workspace", "."], ROOT)

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
        run_command(["uv", "add", "--dev", *missing], ROOT)
    else:
        run_command(["uv", "sync"], ROOT)

    backend.mkdir(parents=True, exist_ok=True)
    init_file = backend / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Application backend package."""\n', encoding="utf-8")

    tests_dir = ROOT / "tests"
    tests_dir.mkdir(exist_ok=True)
    smoke_test = tests_dir / "test_backend.py"
    package_name = backend.name
    ensure_setuptools_package_discovery(pyproject, package_name)
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


def configure_react_quality(frontend: Path, manager: str = "npm") -> None:
    package_json = frontend / "package.json"
    if not package_json.exists():
        raise SystemExit(f"React bootstrap did not create {package_json}")
    data = json.loads(package_json.read_text(encoding="utf-8"))
    if manager == "pnpm":
        data["packageManager"] = f"pnpm@{PNPM_VERSION}"
    elif manager == "yarn":
        data["packageManager"] = f"yarn@{YARN_VERSION}"
    scripts = data.setdefault("scripts", {})
    scripts.update(
        {
            "format": "prettier --write .",
            "format:check": "prettier --check .",
            "typecheck": "tsc -b",
            "test": "vitest run",
            "test:watch": "vitest",
        }
    )
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
    if not shutil.which(manager):
        raise SystemExit(
            f"{manager} is required for the configured React bootstrap but was not found on PATH"
        )
    node_path = shutil.which("node")
    if not node_path:
        raise SystemExit("Node.js is required for the configured React bootstrap")
    node_version_file = ROOT / ".node-version"
    if not node_version_file.is_file():
        raise SystemExit(
            "React is enabled but .node-version is missing; add it before bootstrap."
        )
    expected_node = node_version_file.read_text(encoding="utf-8").strip()
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
    if installed_node != expected_node:
        raise SystemExit(
            f"Configured Node.js version is {expected_node}, but PATH provides {installed_node}. "
            "Install the configured version before bootstrap."
        )

    frontend = validate_repository_path(directory, "stacks.react.directory")
    if frontend is None:
        raise SystemExit("stacks.react.directory must not be empty")
    create_cmd, install_cmd, add_dev_cmd = package_manager_commands(
        manager, directory, REACT_TEMPLATE, VITE_VERSION
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
    configure_react_quality(frontend, manager)
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
    state = (
        "enabled"
        if get(data, "engineering_knowledge", "enabled", default=False)
        else "disabled"
    )
    block = f"\n{marker}\n\n- Project name: `{name}`\n- Enabled stacks: `{stacks}`\n- Engineering knowledge MCP: `engineering-knowledge` ({state})\n- Configuration source: `.ai/project.yaml`\n"
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
        "2. Record the required decisions in `.ai/policies/QUALITY_GATES.md` and configure branch protection.\n\n"
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


def create_project_readme(data: dict) -> None:
    path = ROOT / "README.md"
    if path.exists():
        return
    name = str(get(data, "project", "name", default="Project"))
    stacks = ", ".join(enabled_stack_names(data)) or "none"
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

## Security

See `.ai/policies/SECURITY_GUIDELINES.md`.

"""
    path.write_text(content, encoding="utf-8")


def create_idea() -> None:
    idea = ROOT / ".idea"
    idea.mkdir(exist_ok=True)
    (idea / "vcs.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<project version="4">\n  <component name="VcsDirectoryMappings">\n    <mapping directory="$PROJECT_DIR$" vcs="Git" />\n  </component>\n</project>\n',
        encoding="utf-8",
    )


def main() -> None:
    data = load_yaml_subset(CONFIG)
    validate_config(data)
    create_project_readme(data)
    bootstrap_python(data)
    bootstrap_react(data)
    (ROOT / ".ai/config/project.defaults.env").write_text(
        generate_env(data), encoding="utf-8"
    )
    update_context(data)
    update_next_steps()
    create_decisions_scaffold()
    create_idea()
    for path in (ROOT / ".ai/tools").glob("*.sh"):
        path.chmod(path.stat().st_mode | 0o111)
    print("[bootstrap] Created README.md when missing")
    print("[bootstrap] Initialized configured Python and React project tooling")
    print("[bootstrap] Generated versioned .ai/config/project.defaults.env")
    print("[bootstrap] Updated .ai/PROJECT_CONTEXT.md")
    print("[bootstrap] Updated project-readiness next steps")
    print("[bootstrap] Created .ai/DECISIONS.md when missing")
    print("[bootstrap] Created .idea/vcs.xml")
    print("[bootstrap] AI rules are ready under .aiassistant/rules/")
    print("[bootstrap] One manual IntelliJ setting remains:")
    print("  Settings > Tools > AI Assistant > Project Settings")
    print(f"  Path to rules for AI Self-Review: $PROJECT_DIR$/{SELF_REVIEW_RULES}")
    print("[bootstrap] Install the required tools, then run ./.ai/tools/verify.sh")


if __name__ == "__main__":
    main()
