#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

usage() {
  printf 'Usage: %s verify|browser|accessibility|visual-regression\n' "$0" >&2
}

case "${1:-}" in
  verify)
    accessibility_enabled="${ACCESSIBILITY_ENABLED:-}"
    visual_regression_enabled="${VISUAL_REGRESSION_ENABLED:-}"
    if [[ -z "${accessibility_enabled}" && -n "${ACCESSIBILITY_CMD:-}" ]]; then
      accessibility_enabled=1
    fi
    if [[ -z "${visual_regression_enabled}" && -n "${VISUAL_REGRESSION_CMD:-}" ]]; then
      visual_regression_enabled=1
    fi
    gate_mode="$("${SCRIPT_DIR}/check-ui-quality.py" --browser-gate-mode)"
    case "${gate_mode}" in
      not-required)
        log "UI browser procedure: not required for the active work phase"
        ;;
      manual)
        log "UI browser procedure: manual gate; static evidence validation follows"
        if [[ "${accessibility_enabled:-0}" == "1" && -n "${ACCESSIBILITY_CMD:-}" ]]; then
          run_or_skip "accessibility review" "${ACCESSIBILITY_CMD}" 1
        elif [[ "${accessibility_enabled:-0}" == "1" ]]; then
          log "accessibility review: manual observations required in UI evidence"
        fi
        if [[ "${visual_regression_enabled:-0}" == "1" ]]; then
          run_or_skip "visual regression" "${VISUAL_REGRESSION_CMD}" 1
        fi
        ;;
      automated)
        run_or_skip "browser review" "${BROWSER_REVIEW_CMD:-}" 1
        if [[ "${accessibility_enabled:-0}" == "1" && -n "${ACCESSIBILITY_CMD:-}" ]]; then
          run_or_skip "accessibility review" "${ACCESSIBILITY_CMD}" 1
        elif [[ "${accessibility_enabled:-0}" == "1" ]]; then
          log "accessibility review: manual observations required in UI evidence"
        fi
        if [[ "${visual_regression_enabled:-0}" == "1" ]]; then
          run_or_skip "visual regression" "${VISUAL_REGRESSION_CMD}" 1
        fi
        ;;
      *)
        fail "required UI browser procedure is not configured"
        exit 1
        ;;
    esac
    ;;
  browser)
    run_or_skip "browser review" "${BROWSER_REVIEW_CMD:-}" 1
    ;;
  accessibility)
    run_or_skip "accessibility review" "${ACCESSIBILITY_CMD:-}" 1
    ;;
  visual-regression)
    run_or_skip "visual regression" "${VISUAL_REGRESSION_CMD:-}" 1
    ;;
  *)
    usage
    exit 2
    ;;
esac
