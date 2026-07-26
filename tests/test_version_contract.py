"""Tests for the coherent package, CLI, and receipt version contract."""

from __future__ import annotations

import importlib.metadata
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_rubric import __version__
from hermes_rubric.receipt import build_receipt

ROOT = Path(__file__).resolve().parents[1]


def _receipt() -> dict:
    return build_receipt(
        intent="test",
        context_path="context.txt",
        target_path="target.txt",
        backend="controlled-fake",
        rubric={
            "rubric_intent": "test",
            "target_type": "repo",
            "dimensions": [],
        },
        evidence_list=[],
        scores=[],
        target_content="public target",
        context_content="public context",
    )


def test_source_cli_and_receipt_versions_agree():
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (src_path, env.get("PYTHONPATH")) if part
    )
    cli = subprocess.run(
        [sys.executable, "-m", "hermes_rubric.cli", "--version"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert cli.stdout.strip() == f"hermes-rubric {__version__}"
    assert _receipt()["tool_version"] == f"hermes-rubric {__version__}"


def test_pyproject_version_matches_runtime():
    match = re.search(
        r'^version = "([^"]+)"$',
        (ROOT / "pyproject.toml").read_text(),
        flags=re.MULTILINE,
    )

    assert match is not None
    assert match.group(1) == __version__


def test_installed_distribution_metadata_matches_runtime():
    try:
        installed_version = importlib.metadata.version("hermes-rubric")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("distribution metadata is absent in a source-only checkout")

    assert installed_version == __version__
