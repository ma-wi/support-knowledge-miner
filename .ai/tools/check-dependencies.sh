#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

python_cmd="${PYTHON_CMD:-}"
if [[ -z "${python_cmd}" ]]; then
  if has_command python3; then python_cmd=python3
  elif has_command python; then python_cmd=python
  fi
fi
if [[ -n "${python_cmd}" ]]; then
  policy_command="DEPENDENCY_ALLOWLIST_MODE=${DEPENDENCY_ALLOWLIST_MODE:-0} REQUIRE_LOCKFILES=${REQUIRE_LOCKFILES:-1} REJECT_FLOATING_VERSIONS=${REJECT_FLOATING_VERSIONS:-1} ${python_cmd} .ai/tools/dependency_policy.py"
else
  policy_command=""
fi
run_or_skip "dependency policy" "${policy_command}" "${REQUIRE_DEPENDENCY_POLICY:-1}"

scanner_commands=()
if has_command osv-scanner; then
  scanner_commands+=('osv-scanner scan source --recursive .')
fi
if has_command trivy; then
  scanner_commands+=('trivy fs --scanners vuln,secret,misconfig,license --severity UNKNOWN,HIGH,CRITICAL --exit-code 1 .')
fi
if [[ -n "${DEPENDENCY_REPUTATION_CMD:-}" ]]; then
  scanner_commands+=("${DEPENDENCY_REPUTATION_CMD}")
fi
if [[ -n "${DEPENDENCY_SCAN_CMD:-}" ]]; then
  scanner_commands+=("${DEPENDENCY_SCAN_CMD}")
fi

if ((${#scanner_commands[@]} == 0)); then
  run_or_skip "dependency vulnerability/reputation scans" "" "${REQUIRE_DEPENDENCY_SCANNERS:-0}"
else
  joined="$(join_with_and "${scanner_commands[@]}")"
  run_command "dependency vulnerability/reputation scans" "${joined}"
fi
