#!/usr/bin/env python3
"""Expose validated project runtime versions to CI without third-party packages."""

from __future__ import annotations

import argparse
import platform
import re
import shutil
import subprocess  # nosec B404 - fixed local executable --version probes only
from pathlib import Path

from _common import (
    load_yaml_subset,
    parse_runtime_requirement,
    runtime_versions,
    select_exact_version,
    select_exact_runtime_version,
    tool_requirements,
    runtime_satisfies,
    version_satisfies,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".ai" / "project.yaml"


def configured_requirements(config: dict) -> dict[str, str]:
    requirements = runtime_versions(config)
    requirements["uv"] = tool_requirements(config)["uv"]
    return requirements


def exact_resolutions(requirements: dict[str, str]) -> dict[str, str]:
    resolutions: dict[str, str] = {}
    for name, requirement in requirements.items():
        resolution = (
            select_exact_runtime_version(requirement, name)
            if name in {"python", "node"}
            else select_exact_version(requirement)
        )
        if resolution is None:
            raise SystemExit(
                f"{name} requirement {requirement!r} has no deterministic inclusive "
                "lower-bound resolution; use an exact value or an inclusive minimum"
            )
        resolutions[name] = resolution
    return resolutions


def github_output_lines(
    requirements: dict[str, str], resolutions: dict[str, str]
) -> str:
    """Render exact CI selections alongside the original validated grammar."""
    return "".join(
        f"{name}={resolutions[name]}\n{name}_requirement={requirement}\n"
        for name, requirement in requirements.items()
    )


def executable_version(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise SystemExit(f"Cannot verify {name}: executable not found on PATH")
    result = subprocess.run(  # nosec B603
        [executable, "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    match = re.search(
        r"(?<![0-9A-Za-z.+-])v?(\d+\.\d+\.\d+)(?![0-9A-Za-z.+-])",
        result.stdout,
    )
    if result.returncode != 0 or match is None:
        raise SystemExit(f"Cannot verify {name}: invalid --version output")
    return match.group(1)


def verify_resolution(name: str, requirement: str, expected_resolution: str) -> None:
    observed = (
        platform.python_version() if name == "python" else executable_version(name)
    )
    if name in {"python", "node"}:
        parsed_requirement = parse_runtime_requirement(requirement, name)
        satisfies = parsed_requirement is not None and runtime_satisfies(
            observed, name, [parsed_requirement]
        )
    else:
        satisfies = version_satisfies(observed, requirement)
    if observed != expected_resolution or not satisfies:
        raise SystemExit(
            f"{name} resolved to {observed}, expected exact resolution "
            f"{expected_resolution} satisfying requirement {requirement!r}"
        )
    print(
        f"Verified {name} resolution {observed} satisfies requirement {requirement!r}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--github-output",
        type=Path,
        help="append exact resolutions and original requirements to this output file",
    )
    parser.add_argument(
        "--verify",
        action="append",
        choices=("python", "node", "uv"),
        default=[],
        help="verify one installed runtime/tool against its exact CI resolution",
    )
    arguments = parser.parse_args()
    config = load_yaml_subset(CONFIG)
    requirements = configured_requirements(config)
    resolutions = exact_resolutions(requirements)
    for name in arguments.verify:
        verify_resolution(name, requirements[name], resolutions[name])
    if arguments.verify and arguments.github_output is None:
        return
    lines = github_output_lines(requirements, resolutions)
    for name, resolution in resolutions.items():
        print(
            f"Selected exact {name} resolution {resolution} for requirement "
            f"{requirements[name]!r}"
        )
    if arguments.github_output is None:
        print(lines, end="")
        return
    with arguments.github_output.open("a", encoding="utf-8", newline="\n") as output:
        output.write(lines)


if __name__ == "__main__":
    main()
