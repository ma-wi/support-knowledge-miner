#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"
command_text="${BUILD_CMD:-$(detect_build)}"
run_or_skip "build" "${command_text}" "${REQUIRE_BUILD:-0}"
