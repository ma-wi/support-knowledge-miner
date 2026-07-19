#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ "${1:-}" == "--check" ]]; then
  command_text="${FORMAT_CHECK_CMD:-$(detect_format_check)}"
  run_or_skip "format check" "${command_text}" "${REQUIRE_FORMAT_CHECK:-0}"
else
  command_text="${FORMAT_APPLY_CMD:-$(detect_format_apply)}"
  run_or_skip "format apply" "${command_text}" "${REQUIRE_FORMAT_CHECK:-0}"
fi
