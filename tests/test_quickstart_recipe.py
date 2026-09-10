"""The quickstart recipe must stay runnable and keep its published invariants.

`docs/quickstart.md` gives a reader with no checkout one complete synthetic
assessment and then tells them which properties of the result they may assert.
This module is the gate on that promise:

* the documented target is extracted from the doc itself, so the recipe cannot
  drift from what is published;
* the documented CLI invocation still names a real class template and passes an
  explicit ``--backend``, because automatic backend selection must never be
  inherited by a pasted recipe;
* the structural invariants the doc licenses — schema version, one score per
  rubric dimension, one evidence entry per score, the no-evidence and hedge
  clamps, coverage, receipt — hold end to end.

**This is a plumbing test.** The backend is a stub, so nothing here says
anything about a real model's scores, and no assertion pins a score value. A
live receipt is a separate artifact.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hermes_rubric import __version__, assess_path
from hermes_rubric import backends as backends_mod
from hermes_rubric.classes import load_class, to_rubric

DOC = Path(__file__).resolve().parent.parent / "docs" / "quickstart.md"
ARTIFACT_CLASS = "social-post"


def _doc_text() -> str:
    return DOC.read_text(encoding="utf-8")


def _quickstart_target() -> str:
    bodies = re.findall(r"<<'EOF'\n(.*?)\nEOF\n", _doc_text(), re.DOTALL)
    assert bodies, "docs/quickstart.md must publish a self-contained target heredoc"
    return bodies[0]


def _quickstart_command() -> str:
    match = re.search(r"^hermes-rubric \\\n(?:.*\\\n)*.*$", _doc_text(), re.MULTILINE)
    assert match, "docs/quickstart.md must publish a hermes-rubric invocation"
    return match.group(0)


def test_quickstart_command_pins_a_class_template_and_an_explicit_backend():
    command = _quickstart_command()
    assert f"--artifact-class {ARTIFACT_CLASS}" in command
    assert "--backend " in command, (
        "the published recipe must pass an explicit --backend so a pasted "
        "command cannot inherit automatic backend selection"
    )


@pytest.fixture
def stub_backend(monkeypatch):
    """Answer both pipeline stages deterministically, without a model.

    Citations must carry an ``evidence_id`` that resolves to a section of the
    real target and a quote that actually appears in it — otherwise
    ``_normalize_evidence`` rejects every citation and forces
    ``evidence_found: false`` on every dimension, which would make the clamp
    assertions below pass for the wrong reason. The stub therefore reads the
    section id and a real quote straight out of the prompt it is given.
    """
    template = to_rubric(load_class(ARTIFACT_CLASS))
    by_name = {dim["name"]: dim for dim in template["dimensions"]}
    ids = [dim["id"] for dim in template["dimensions"]]
    # One dimension returns no evidence at all and is hedged (both clamps
    # apply); a second has real evidence but low confidence (hedge clamp only).
    no_evidence_id, hedged_id = ids[0], ids[1]

    def _dim_for(prompt: str) -> dict:
        for name, dim in by_name.items():
            if f"DIMENSION: {name}\n" in prompt:
                return dim
        raise AssertionError("stub backend could not identify the dimension")

    def _section(prompt: str) -> tuple[str, str]:
        match = re.search(
            r'<SECTION id="([^"]+)"[^>]*>\n(.*?)\n</SECTION>', prompt, re.DOTALL
        )
        assert match, "evidence prompt must expose a citable section"
        section_id, body = match.group(1), match.group(2)
        quote = next(line for line in body.splitlines() if line.strip())
        return section_id, quote.strip()

    def fake_call(prompt: str, backend: str | None = None, max_tokens: int = 2048) -> str:
        dim = _dim_for(prompt)
        if prompt.startswith("You are an evidence collector"):
            if dim["id"] == no_evidence_id:
                return json.dumps({
                    "dim_id": dim["id"],
                    "evidence_found": False,
                    "confidence": "low",
                    "hedge": True,
                    "citations": [],
                    "evidence_summary": "nothing observable for this dimension",
                })
            section_id, quote = _section(prompt)
            return json.dumps({
                "dim_id": dim["id"],
                "evidence_found": True,
                "confidence": "low" if dim["id"] == hedged_id else "high",
                "hedge": dim["id"] == hedged_id,
                "citations": [
                    {
                        # `code` keeps the self-marketing clamp (which caps
                        # doc-only citations at 6) out of the way, so the hedge
                        # clamp is the only thing that can pull the stub's 10
                        # down into [3, 7].
                        "evidence_id": section_id,
                        "quote": quote,
                        "location": section_id,
                        "source_class": "code",
                    }
                ],
                "evidence_summary": "quoted the opening claim",
            })
        assert prompt.startswith("You are a structured scorer")
        # Deliberately over-score, so the clamps must do the work.
        return json.dumps({
            "dim_id": dim["id"],
            "score": 10,
            "score_rationale": "stub",
            "evidence_drove_score": "stub",
            "hedge_applied": False,
        })

    monkeypatch.setattr(backends_mod, "call", fake_call)
    return {"no_evidence_id": no_evidence_id, "hedged_id": hedged_id}


def test_quickstart_recipe_holds_its_published_invariants(stub_backend, tmp_path):
    target = tmp_path / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")

    result = assess_path(
        target,
        intent=f"Score against the {ARTIFACT_CLASS} class template.",
        context_path=target,
        artifact_class=ARTIFACT_CLASS,
        backend="stub",
    )
    payload = result.to_dict()

    assert payload["schema_version"]

    rubric_ids = [dim["id"] for dim in payload["rubric"]["dimensions"]]
    score_ids = [score["dim_id"] for score in payload["per_dim_scores"]]
    evidence_ids = [item["dim_id"] for item in payload["evidence_citations"]]
    assert score_ids == rubric_ids
    assert sorted(evidence_ids) == sorted(rubric_ids)

    # The two clamps are independent, so a dimension that is both hedged and
    # evidence-free must satisfy BOTH bounds, not whichever one is checked
    # first. Checking them with `elif` would let a future regression push the
    # intersection below 3 unnoticed.
    evidence_by_id = {item["dim_id"]: item for item in payload["evidence_citations"]}
    scores_by_id = {score["dim_id"]: score["score"] for score in payload["per_dim_scores"]}

    # Non-degeneracy guard. If citations were rejected, every dimension would
    # come back evidence-free and clamp to 3, and the assertions below would
    # pass without ever exercising the hedge clamp.
    hedged = evidence_by_id[stub_backend["hedged_id"]]
    assert hedged["evidence_found"] is True
    assert hedged["citations"], "the hedged dimension must keep a real citation"
    assert hedged["hedge"] is True
    for dim_id, score in scores_by_id.items():
        evidence = evidence_by_id[dim_id]
        if not evidence["evidence_found"]:
            assert score <= 3, f"no-evidence clamp must survive ({dim_id})"
        if evidence["hedge"]:
            assert 3 <= score <= 7, f"hedge clamp must survive ({dim_id})"

    # The stub makes this dimension hedged *and* evidence-free: both clamps
    # apply, and their intersection is exactly 3.
    intersection = stub_backend["no_evidence_id"]
    assert evidence_by_id[intersection]["hedge"] is True
    assert evidence_by_id[intersection]["evidence_found"] is False
    assert scores_by_id[intersection] == 3

    assert 3 <= scores_by_id[stub_backend["hedged_id"]] <= 7

    coverage = payload["coverage"]
    assert coverage["status"] == "complete"
    assert coverage["limitations"] == []

    receipt = payload["receipt"]
    assert receipt["tool_version"].startswith("hermes-rubric ")
    assert receipt["backend"] == "stub"
    assert receipt["pipeline"]["stage_1_rubric_source"] == "class-template"
    assert len(receipt["pipeline"]["stage_1_rubric_hash_sha256"]) == 64
    assert receipt["inputs"]["target_path"].endswith("post.md")


def test_quickstart_pins_the_packaged_release():
    """The published install must stay pinned to the version it documents.

    A floating `pip install hermes-rubric` stops being release-matched the
    moment a new version ships. Pinning is only honest while the pin tracks
    the package, so this fails the release that forgets to bump the doc.
    """
    text = _doc_text()
    assert f"pip install hermes-rubric=={__version__}" in text
    assert f"hermes-rubric {__version__}" in text, (
        "the documented `--version` output must match the packaged version"
    )


def test_quickstart_cites_a_source_for_its_operational_numbers():
    """AGENTS.md rule 5: numeric claims carry a pointer to their source."""
    text = _doc_text()
    for pointer in (
        "src/hermes_rubric/backends.py",
        "src/hermes_rubric/cli.py",
        "src/hermes_rubric/score.py",
        "src/hermes_rubric/classes/social-post.yaml",
    ):
        assert pointer in text, f"missing source pointer: {pointer}"


def test_quickstart_labels_the_backend_prerequisites():
    text = _doc_text()
    for backend in ("ollama-local", "claude-cli", "openai-sdk"):
        assert backend in text
    assert "OPENAI_API_KEY" in text
