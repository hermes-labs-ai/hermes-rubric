"""Regression checks for the trusted-publishing workflow boundary."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "publish.yml"


def _workflow() -> dict[str, object]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _named_step(steps: list[dict[str, object]], name: str) -> dict[str, object]:
    return next(step for step in steps if step.get("name") == name)


def test_publish_workflow_keeps_build_and_oidc_publication_separate():
    workflow = _workflow()
    jobs = workflow["jobs"]
    build = jobs["build"]
    publish = jobs["publish"]

    assert build["permissions"] == {"contents": "read"}
    build_steps = build["steps"]
    assert "GITHUB_REF_NAME" in _named_step(build_steps, "Verify release tag matches package version")["run"]
    assert "twine check dist/*" in _named_step(build_steps, "Build and validate package")["run"]
    assert any(
        step.get("uses", "").startswith("actions/upload-artifact@")
        and step.get("with") == {"name": "dist", "path": "dist/"}
        for step in build_steps
    )

    assert publish["needs"] == "build"
    assert publish["environment"] == "pypi"
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}
    publish_steps = publish["steps"]
    assert any(
        step.get("uses", "").startswith("actions/download-artifact@")
        and step.get("with") == {"name": "dist", "path": "dist/"}
        for step in publish_steps
    )
    assert any(
        step.get("uses", "").startswith("pypa/gh-action-pypi-publish@") for step in publish_steps
    )

    uses_lines = [line for line in WORKFLOW_PATH.read_text(encoding="utf-8").splitlines() if "uses:" in line]
    assert uses_lines
    assert all(re.search(r"@[0-9a-f]{40}\s+# v", line) for line in uses_lines)
