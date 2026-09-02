"""Pinned-rubric loading and receipt provenance."""

import copy
import json
import sys

import pytest

from hermes_rubric import assess_path
from hermes_rubric import assessment as assessment_mod
from hermes_rubric import cli as cli_mod
from hermes_rubric.receipt import rubric_hash
from hermes_rubric.synthesize import load_pinned
from tests.test_assessment_api import RUBRIC


@pytest.fixture
def controlled_pipeline(monkeypatch):
    def fake_evidence(**kwargs):
        return [
            {
                "dim_id": dim["id"],
                "dim_name": dim["name"],
                "evidence_found": True,
                "confidence": "high",
                "hedge": False,
                "citations": [{"quote": "answer", "location": kwargs["target_path"]}],
                "evidence_summary": "answer inspected",
            }
            for dim in kwargs["rubric"]["dimensions"]
        ]

    def fake_scores(**kwargs):
        return [
            {
                "dim_id": dim["id"],
                "dim_name": dim["name"],
                "score": 8,
                "score_rationale": "controlled",
                "evidence_drove_score": "answer",
                "hedge_applied": False,
            }
            for dim in kwargs["rubric"]["dimensions"]
        ]

    monkeypatch.setattr(assessment_mod, "collect_evidence", fake_evidence)
    monkeypatch.setattr(assessment_mod, "score_dimensions", fake_scores)
    monkeypatch.setattr(assessment_mod.backends, "detect", lambda: "controlled")


def test_load_pinned_accepts_bare_and_prior_result(tmp_path):
    bare = tmp_path / "rubric.json"
    prior = tmp_path / "result.json"
    bare.write_text(json.dumps(RUBRIC))
    prior.write_text(json.dumps({"rubric": RUBRIC, "aggregate": 7.0}))

    assert load_pinned(bare) == RUBRIC
    assert load_pinned(prior) == RUBRIC


def test_load_pinned_rejects_invalid_inputs(tmp_path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[1, 2]")
    with pytest.raises(ValueError, match="must be an object"):
        load_pinned(invalid)
    with pytest.raises(FileNotFoundError, match="pinned rubric file not found"):
        load_pinned(tmp_path / "missing.json")


def test_pinned_assessment_preserves_hash_and_records_source(
    controlled_pipeline, tmp_path
):
    target = tmp_path / "target.md"
    target.write_text("answer")
    frozen = copy.deepcopy(RUBRIC)

    result = assess_path(
        target,
        rubric=frozen,
        backend="controlled",
        _rubric_provenance="pinned:prior.json",
    )

    assert result.rubric == RUBRIC
    assert rubric_hash(result.rubric) == rubric_hash(RUBRIC)
    assert result.receipt["pipeline"]["stage_1_rubric_source"] == "pinned:prior.json"
    assert result.receipt["pipeline"]["stage_1_rubric_hash_sha256"] == rubric_hash(RUBRIC)


def test_cli_pin_defaults_intent_and_context(controlled_pipeline, monkeypatch, tmp_path):
    target = tmp_path / "target.md"
    pinned = tmp_path / "prior.json"
    output = tmp_path / "output.json"
    target.write_text("answer")
    pinned.write_text(json.dumps({"rubric": RUBRIC}))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hermes-rubric",
            "--target",
            str(target),
            "--pin-rubric",
            str(pinned),
            "--backend",
            "ollama-local",
            "--out",
            str(output),
        ],
    )

    cli_mod.main()
    payload = json.loads(output.read_text())
    assert payload["rubric"] == RUBRIC
    assert payload["receipt"]["inputs"]["intent"] == RUBRIC["rubric_intent"]
    assert payload["receipt"]["inputs"]["context_path"] == str(target)
    assert payload["receipt"]["pipeline"]["stage_1_rubric_source"] == f"pinned:{pinned}"


def test_cli_rejects_two_deterministic_sources(monkeypatch, tmp_path):
    target = tmp_path / "target.md"
    pinned = tmp_path / "rubric.json"
    target.write_text("answer")
    pinned.write_text(json.dumps(RUBRIC))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hermes-rubric",
            "--target",
            str(target),
            "--pin-rubric",
            str(pinned),
            "--artifact-class",
            "repo-readme",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        cli_mod.main()
    assert exc_info.value.code == 2
