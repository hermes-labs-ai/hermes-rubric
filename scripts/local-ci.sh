#!/bin/bash
# scripts/local-ci.sh — mirror of .github/workflows/ci.yml that runs locally.
#
# Catches CI-fatal issues BEFORE pushing. Run before every push.
#
# Exits 0 if all checks pass; 1 otherwise.

set -uo pipefail
cd "$(dirname "$0")/.."

GREEN=$'\033[32m'
RED=$'\033[31m'
YELLOW=$'\033[33m'
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
    fi
}

# 1. dependency resolvability — the failure mode that broke CI on b8d5f5e
echo ""
echo "=== dependency-resolvability dry-run ==="
if pip install --dry-run -e . 2>&1 | grep -q "ERROR\|No matching distribution"; then
    echo "${RED}FAIL${RESET}: dependency resolution would fail (CI install will fail)"
    pip install --dry-run -e . 2>&1 | grep -E "ERROR|No matching" | head -3
    FAIL=$((FAIL+1))
else
    echo "${GREEN}PASS${RESET}: dependency resolution clean"
fi

# 2. ruff lint (if available)
if command -v ruff >/dev/null 2>&1; then
    run "ruff check src/ tests/" ruff check src/ tests/
else
    echo "${YELLOW}WARN${RESET}: ruff not installed; skipping. brew install ruff or pip install ruff."
fi

# 3. pytest (matches the CI matrix command)
run "pytest tests/" bash -c "PYTHONPATH=src python3 -m pytest tests/ -q"

# 4. pytest with no API keys (matches CI's "Verify no API key required" job)
run "pytest with all API keys unset" bash -c "
    unset ANTHROPIC_API_KEY OPENAI_API_KEY DASHSCOPE_API_KEY GOOGLE_GEMINI_API_KEY GOOGLE_API_KEY
    PYTHONPATH=src python3 -m pytest tests/ -q
"

echo ""
echo "==================================="
if [[ $FAIL -eq 0 ]]; then
    echo "${GREEN}ALL CHECKS PASSED${RESET} — safe to push."
    exit 0
else
    echo "${RED}FAILED: $FAIL check(s) — DO NOT PUSH${RESET}"
    exit 1
fi
