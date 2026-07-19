#!/usr/bin/env python3
"""Shared helpers for the .ai/tools scripts.

These helpers are deliberately dependency-free so every tool can import them
whether it is executed as a script (its directory is on ``sys.path``) or loaded
in-process by the template test suite.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

# Plan phases in which a temporary PLAN.md pointer must already exist. Earlier
# phases (discovery, specification) legitimately precede plan creation, so a
# missing pointer is not an error there.
PLAN_POINTER_PHASES = {
    "planning",
    "implementation",
    "verification",
    "review",
    "remediation",
    "closeout",
}


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


def extract_field(text: str, field: str) -> str | None:
    match = re.search(
        rf"^-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE
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
