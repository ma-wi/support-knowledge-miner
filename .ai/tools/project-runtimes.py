#!/usr/bin/env python3
"""Expose validated project runtime versions to CI without third-party packages."""

from __future__ import annotations

import argparse
from pathlib import Path

from _common import load_yaml_subset, runtime_versions

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".ai" / "project.yaml"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--github-output",
        type=Path,
        help="append python and node outputs to this GitHub Actions output file",
    )
    arguments = parser.parse_args()
    versions = runtime_versions(load_yaml_subset(CONFIG))
    lines = "".join(f"{runtime}={version}\n" for runtime, version in versions.items())
    if arguments.github_output is None:
        print(lines, end="")
        return
    with arguments.github_output.open("a", encoding="utf-8", newline="\n") as output:
        output.write(lines)


if __name__ == "__main__":
    main()
