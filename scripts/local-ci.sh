#!/bin/bash
# Shared native test contract for contributors, the CI matrix, and Hermes Gate.
# Packaging is checked separately by .hermes/check-package.sh (Gate full).
#
# Catches CI-fatal issues BEFORE pushing. Run before every push.
#
# Exits 0 if all checks pass; 1 otherwise.

set -uo pipefail
cd "$(dirname "$0")/.."

GREEN=$'\033[32m'
RED=$'\033[31m'
RESET=$'\033[0m'

FAIL=0

run() {
    local name="$1"; shift
    echo ""
    echo "=== $name ==="
    if "$@"; then
        echo "${GREEN}PASS${RESET}: $name"
    else
        echo "${RED}FAIL${RESET}: $name"
        FAIL=$((FAIL+1))
        return 1
    fi
}

# Resolve the same test extras that CI installs. Stream diagnostics directly and
# trust pip's exit status; parsing ERROR text can invert failures under pipefail.
run "dependency-resolvability dry-run" \
    python3 -m pip install --dry-run -e '.[dev,inspect,openai-agents]' pytest-mock

# Missing integration extras must fail before importorskip can hide real SDK tests.
# This is a separate process so imports cannot interfere with tests that unload SDKs.
if ! run "required test dependencies" python3 -c '
import agents.testing
import inspect_ai
import pytest
import pytest_mock
'; then
    echo "Install test dependencies: python3 -m pip install -e '.[dev,inspect,openai-agents]' pytest-mock"
    exit 1
fi

# Keep the existing E4/E7/E9/F lint contract across Ruff default-rule changes.
run "ruff check src/ tests/" python3 -m ruff check --select E4,E7,E9,F src/ tests/

# One full suite proves both the test contract and the no-provider-key contract.
# Remove keys for the entire child process without reading or printing values.
run "pytest with all API keys unset" env \
    -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u DASHSCOPE_API_KEY \
    -u GOOGLE_GEMINI_API_KEY -u GOOGLE_API_KEY \
    python3 -m pytest tests/ -q

echo ""
echo "==================================="
if [[ $FAIL -eq 0 ]]; then
    echo "${GREEN}ALL CHECKS PASSED${RESET}"
    exit 0
else
    echo "${RED}FAILED: $FAIL check(s) — DO NOT PUSH${RESET}"
    exit 1
fi
