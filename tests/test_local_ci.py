"""Exercise the native CI shell contract without installing or calling providers."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_KEYS = (
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DASHSCOPE_API_KEY",
    "GOOGLE_GEMINI_API_KEY", "GOOGLE_API_KEY",
)


@pytest.fixture
def native_ci(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy2(ROOT / "scripts/local-ci.sh", scripts / "local-ci.sh")
    tools = tmp_path / "bin"
    tools.mkdir()
    # Handle both the historical standalone pip/ruff and interpreter-bound tools.
    stub = tools / "python3"
    stub.write_text("""#!/bin/bash
case "$*" in
  *pip*|*--dry-run*)
    echo "resolver $*" >> "$CALL_LOG"
    echo "${RESOLVER_OUTPUT:-resolution clean}"
    exit "${RESOLVER_STATUS:-0}" ;;
  *ruff*|check*)
    echo ruff >> "$CALL_LOG"
    if [[ ${RUFF_STATUS:-0} != 0 ]]; then echo 'No module named ruff'; fi
    exit "${RUFF_STATUS:-0}" ;;
  '-m pytest'*)
    echo pytest >> "$CALL_LOG"
    for key in ANTHROPIC_API_KEY OPENAI_API_KEY DASHSCOPE_API_KEY GOOGLE_GEMINI_API_KEY GOOGLE_API_KEY; do
      if printenv "$key" >/dev/null; then echo "provider key present"; exit 91; fi
    done
    exit "${PYTEST_STATUS:-0}" ;;
  *)
    echo preflight >> "$CALL_LOG"
    if [[ ${SDK_STATUS:-0} != 0 ]]; then echo 'Missing required SDK'; fi
    exit "${SDK_STATUS:-0}" ;;
esac
""")
    stub.chmod(0o755)
    for name in ("pip", "ruff"):
        (tools / name).symlink_to(stub)
    log = tmp_path / "calls"

    def invoke(**overrides):
        env = {key: value for key, value in os.environ.items() if key not in PROVIDER_KEYS}
        env.update(PATH=f"{tools}:/usr/bin:/bin", CALL_LOG=str(log), **overrides)
        result = subprocess.run(
            ["/bin/bash", str(scripts / "local-ci.sh")],
            env=env, capture_output=True, text=True, check=False,
        )
        return result, log.read_text().splitlines() if log.exists() else []

    return invoke


@pytest.mark.parametrize("output", ["ERROR: unsatisfiable dependency", "resolver unavailable"])
def test_resolver_failure_cannot_pass(native_ci, output):
    result, calls = native_ci(RESOLVER_STATUS="1", RESOLVER_OUTPUT=output)
    assert result.returncode != 0, result.stdout
    assert output in result.stdout
    assert len([call for call in calls if call.startswith("resolver")]) == 1


def test_success_uses_required_extras_and_one_keyless_suite(native_ci):
    result, calls = native_ci(**dict.fromkeys(PROVIDER_KEYS, "test-placeholder"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[0].startswith("resolver -m pip install --dry-run -e .[dev,inspect,openai-agents]")
    assert calls.count("preflight") == 1
    assert calls.count("ruff") == 1
    assert calls.count("pytest") == 1


def test_success_does_not_parse_error_words(native_ci):
    result, _ = native_ci(RESOLVER_OUTPUT="ERROR is a package's descriptive text")
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    "overrides, diagnostic",
    [({"SDK_STATUS": "1"}, "Missing required SDK"),
     ({"RUFF_STATUS": "1"}, "No module named ruff"),
     ({"PYTEST_STATUS": "1"}, "FAIL")],
)
def test_required_checks_cannot_be_skipped(native_ci, overrides, diagnostic):
    result, calls = native_ci(**overrides)
    assert result.returncode != 0, result.stdout
    assert diagnostic in result.stdout
    if "SDK_STATUS" in overrides:
        assert "pytest" not in calls
