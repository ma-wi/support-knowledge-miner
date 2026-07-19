#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"
command_text="${SECURITY_CMD:-$(detect_security)}"
run_or_skip "security checks" "${command_text}" "${REQUIRE_SECURITY:-0}"
