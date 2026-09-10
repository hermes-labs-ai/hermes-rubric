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
import shlex
import sys
from pathlib import Path

import pytest

from hermes_rubric import __version__, assess_path
from hermes_rubric import cli as cli_mod
from hermes_rubric import backends as backends_mod
from hermes_rubric.classes import load_class, to_rubric

DOC = Path(__file__).resolve().parent.parent / "docs" / "quickstart.md"
ARTIFACT_CLASS = "social-post"
# The backend the published command names. The stub answers the calls, but the
# assessment is driven through this backend name so the recipe under test is
# the documented one rather than a placeholder.
DOCUMENTED_BACKEND = "ollama-local"


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
    seen_backends: list[str | None] = []
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
        seen_backends.append(backend)
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
    return {
        "no_evidence_id": no_evidence_id,
        "hedged_id": hedged_id,
        "seen_backends": seen_backends,
    }


def _documented_argv(target: Path, out: Path) -> list[str]:
    """The published command, tokenised, with its /tmp paths redirected.

    Built from the doc rather than hand-written, so the argv under test is the
    one a reader copies.
    """
    command = _quickstart_command().replace("\\\n", " ")
    argv = shlex.split(command)
    assert argv[0] == "hermes-rubric"
    substitutions = {"/tmp/post.md": str(target), "/tmp/result.json": str(out)}
    return [substitutions.get(token, token) for token in argv[1:]]


def _assess(target: Path):
    """Run the assessment exactly as the published command does."""
    return assess_path(
        target,
        intent=f"Score against the {ARTIFACT_CLASS} class template.",
        context_path=target,
        artifact_class=ARTIFACT_CLASS,
        backend=DOCUMENTED_BACKEND,
    )


def test_quickstart_command_omits_intent_and_context():
    """The recipe must stay self-contained: no user file, no undefined flag."""
    command = _quickstart_command()
    assert f"--backend {DOCUMENTED_BACKEND}" in command
    assert "--intent" not in command
    assert "--context" not in command
    assert "--target /tmp/post.md" in command


def test_rubric_hash_is_stable_across_two_runs(stub_backend, tmp_path):
    """The doc pins rubric selection, not scores; prove the hash half.

    Two runs of the same published command over the same target must produce
    the same `stage_1_rubric_hash_sha256`, which is what makes the caveat about
    differing scores meaningful rather than an excuse for drift.
    """
    target = tmp_path / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")

    first = _assess(target).to_dict()
    second = _assess(target).to_dict()

    def _hash(payload):
        return payload["receipt"]["pipeline"]["stage_1_rubric_hash_sha256"]

    assert _hash(first) == _hash(second)
    assert len(_hash(first)) == 64
    assert first["receipt"]["pipeline"]["stage_1_rubric_source"] == "class-template"
    assert [d["id"] for d in first["rubric"]["dimensions"]] == [
        d["id"] for d in second["rubric"]["dimensions"]
    ]


def test_quickstart_recipe_holds_its_published_invariants(
    stub_backend, tmp_path, monkeypatch
):
    target = tmp_path / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")

    # Drive the published command through the real CLI entry point: argv is
    # parsed from the doc, the backend is the documented one (answered by the
    # stub), and the assertions read the JSON the CLI actually wrote.
    out = tmp_path / "result.json"
    argv = _documented_argv(target, out)
    assert "--intent" not in argv and "--context" not in argv
    assert argv[argv.index("--backend") + 1] == DOCUMENTED_BACKEND

    monkeypatch.setattr(sys, "argv", ["hermes-rubric", *argv])
    cli_mod.main()

    assert out.is_file(), "the published --out path must be written"
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert stub_backend["seen_backends"], "the stub must have answered the calls"
    assert set(stub_backend["seen_backends"]) == {DOCUMENTED_BACKEND}

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
    assert receipt["backend"] == DOCUMENTED_BACKEND
    assert receipt["pipeline"]["stage_1_rubric_source"] == "class-template"
    assert len(receipt["pipeline"]["stage_1_rubric_hash_sha256"]) == 64
    assert receipt["inputs"]["target_path"].endswith("post.md")
    # The published command passes no --context, so the CLI must fill it from
    # the target; otherwise the recipe silently assesses against nothing.
    assert receipt["inputs"]["context_path"] == receipt["inputs"]["target_path"]
    assert receipt["inputs"]["context_hash_sha256"] == receipt["inputs"]["target_hash_sha256"]


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
        # the documented --version output
        "src/hermes_rubric/__init__.py",
        # the two-run nondeterminism statement
        "src/hermes_rubric/receipt.py",
    ):
        assert pointer in text, f"missing source pointer: {pointer}"


def test_version_pointer_names_where_the_version_actually_lives():
    """The cited file must really define the version the doc publishes."""
    source = (
        Path(__file__).resolve().parent.parent
        / "src" / "hermes_rubric" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert f'__version__ = "{__version__}"' in source
    assert f"`hermes-rubric {__version__}`" in _doc_text()


def test_nondeterminism_pointer_names_where_the_note_actually_lives(
    stub_backend, tmp_path
):
    """The cited file must really emit the note, and the note must reach the result."""
    source = (
        Path(__file__).resolve().parent.parent
        / "src" / "hermes_rubric" / "receipt.py"
    ).read_text(encoding="utf-8")
    assert "reproducibility_note" in source

    target = tmp_path / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")
    note = _assess(target).to_dict()["receipt"]["reproducibility_note"]

    assert "not deterministic" in note
    assert "not directly comparable" in note


def test_quickstart_labels_the_backend_prerequisites():
    text = _doc_text()
    for backend in ("ollama-local", "claude-cli", "openai-sdk"):
        assert backend in text
    assert "OPENAI_API_KEY" in text


def test_nondeterminism_claim_does_not_overstate_the_receipt(stub_backend, tmp_path):
    """The note warns about rubric hashes and Stage 1; it is not a scores proof.

    Earlier wording ("Each result says so itself") implied the receipt
    demonstrates that scores vary between runs. It does not — the class
    template bypasses Stage 1 and the hash is identical across runs.
    """
    text = _doc_text()
    assert "does not\ndemonstrate that" in text
    assert "Each result says so itself" not in text

    target = tmp_path / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")
    note = _assess(target).to_dict()["receipt"]["reproducibility_note"]

    # What the note actually covers, and what it does not.
    assert "rubric_hash" in note
    assert "Stage-1 rubric synthesis is not deterministic" in note
    assert "not directly comparable" in note
    # It never claims run-to-run score variance for an unchanged rubric hash.
    assert "two runs" not in note
    assert "can differ" not in note


def test_exit_guidance_separates_success_from_failures_and_usage_errors():
    """Exit 2 is shared between Stage 1 and argparse; the doc must say so."""
    text = " ".join(_doc_text().split())
    assert "Exit `0` means the pipeline completed and produced that output" in text
    assert "a low aggregate still exits `0`" in text
    assert "Exit `2` is shared" in text
    assert "argparse also uses it for a CLI usage error" in text
    assert "prints `usage:`" in text and "prints `ERROR in Stage 1`" in text
