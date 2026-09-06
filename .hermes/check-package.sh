#!/usr/bin/env bash
# Mirror CI's package job with fresh artifacts and isolated install environments.
set -euo pipefail
cd "$(dirname "$0")/.."
unset ANTHROPIC_API_KEY OPENAI_API_KEY DASHSCOPE_API_KEY GOOGLE_GEMINI_API_KEY GOOGLE_API_KEY

package_tmp="$(mktemp -d)"
trap 'rm -rf -- "$package_tmp"' EXIT
python3 -m build --outdir "$package_tmp/dist"
python3 -m twine check "$package_tmp"/dist/*

python3 -m venv "$package_tmp/wheel-venv"
"$package_tmp/wheel-venv/bin/python" -m pip install "$package_tmp"/dist/*.whl
"$package_tmp/wheel-venv/bin/hermes-rubric" --help

tar -xzf "$package_tmp"/dist/hermes_rubric-*.tar.gz -C "$package_tmp"
python3 -m venv "$package_tmp/sdist-venv"
cd "$package_tmp"/hermes_rubric-*
"$package_tmp/sdist-venv/bin/python" -m pip install '.[inspect,openai-agents]' pytest pytest-mock
"$package_tmp/sdist-venv/bin/python" -m pytest tests/ -q
