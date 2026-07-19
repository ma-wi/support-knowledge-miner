#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

run_or_skip "CI dependency setup" "${SETUP_CMD:-}" "${REQUIRE_SETUP:-1}"
