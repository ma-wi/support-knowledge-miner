#!/usr/bin/env bash
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if grep -qE "^[[:space:]]*name:[[:space:]]*['\"]?CHANGE_ME['\"]?[[:space:]]*$" "${SCRIPT_DIR}/../project.yaml"; then
  if [[ -x "${SCRIPT_DIR}/verify-template.sh" ]]; then
    exec "${SCRIPT_DIR}/verify-template.sh"
  fi
  printf '%s\n' 'Project bootstrap is required before verification.' >&2
  exit 1
fi

failures=0

# Full verification is reproducible and uses only committed policy/commands.
# Local overrides remain available to individual focused gate scripts.
export AGENT_TEMPLATE_IGNORE_LOCAL_OVERRIDES=1

run_gate() {
  local name="$1"
  shift
  printf '\n=== %s ===\n' "${name}"
  if "$@"; then
    printf '=== %s: PASS ===\n' "${name}"
  else
    printf '=== %s: FAIL ===\n' "${name}" >&2
    failures=$((failures + 1))
  fi
}

run_gate "work-state" "${SCRIPT_DIR}/check-work-state.py"
run_gate "documentation" "${SCRIPT_DIR}/check-docs.py"
run_gate "setup" "${SCRIPT_DIR}/ci-setup.sh"
run_gate "format" "${SCRIPT_DIR}/format.sh" --check
run_gate "lint" "${SCRIPT_DIR}/lint.sh"
run_gate "tests" "${SCRIPT_DIR}/test.sh"
run_gate "dependency policy" "${SCRIPT_DIR}/check-dependencies.sh"
run_gate "security" "${SCRIPT_DIR}/security.sh"
run_gate "build" "${SCRIPT_DIR}/build.sh"

printf '\n'
if ((failures > 0)); then
  printf 'Verification failed: %d gate(s) failed.\n' "${failures}" >&2
  exit 1
fi

printf 'Verification completed without gate failures.\n'
