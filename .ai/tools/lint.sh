#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"
command_text="${LINT_CMD:-$(detect_lint)}"
run_or_skip "lint and static analysis" "${command_text}" "${REQUIRE_LINT:-0}"
