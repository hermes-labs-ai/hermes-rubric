"""One-call public assessment contract."""

from __future__ import annotations

import asyncio
import copy
import json
import sys

import pytest

from hermes_rubric import AssessmentError, assess, assess_async, assess_path
from hermes_rubric import assessment as assessment_mod
from hermes_rubric import cli as cli_mod

RUBRIC = {
    "rubric_intent": "Check an answer",
    "target_type": "agent-output",
    "dimensions": [
        {
            "id": f"dim_{index}",
            "name": f"Dimension {index}",
            "description": "Observable quality",
            "evidence_instructions": "Inspect the answer",
            "weight": 1,
            "hedge": False,
        }
        for index in range(1, 4)
    ],
}


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
    monkeypatch.setattr(
        assessment_mod.backends,
        "claude_cli_mode",
        lambda: "claude-cli-bare",
    )


def test_assess_accepts_memory_names_and_preserves_full_result(controlled_pipeline):
    frozen = copy.deepcopy(RUBRIC)
    result = assess(
        "answer",
        context="task",
        target_name="agent-output.md",
        context_name="task.txt",
        target_type="agent-output",
        rubric=frozen,
    )
    assert result.aggregate == 8.0
    assert result.receipt["inputs"]["target_path"] == "agent-output.md"
    assert result.receipt["inputs"]["context_path"] == "task.txt"
    assert result.rubric["rubric_source"] == "provided"
    assert frozen == RUBRIC
    assert set(result.to_dict()) >= {
        "rubric",
        "evidence_citations",
        "per_dim_scores",
        "aggregate",
        "receipt",
        "coverage",
        "schema_version",
    }


def test_sync_async_semantic_parity(controlled_pipeline):
    sync = assess("answer", rubric=RUBRIC, backend="controlled").to_dict()
    async_result = asyncio.run(
        assess_async("answer", rubric=RUBRIC, backend="controlled")
    ).to_dict()
    sync["receipt"].pop("timestamp_utc")
    async_result["receipt"].pop("timestamp_utc")
    assert sync == async_result


def test_assess_path_supports_file_and_directory(controlled_pipeline, tmp_path):
    file_path = tmp_path / "answer.md"
    file_path.write_text("answer")
    assert assess_path(file_path, rubric=RUBRIC).coverage.status == "complete"
    directory = tmp_path / "repo"
    directory.mkdir()
    (directory / "README.md").write_text("answer")
    assert assess_path(directory, rubric=RUBRIC).receipt["inputs"]["target_path"] == str(
        directory
    )


def test_synthesized_mode_requires_intent_and_context(controlled_pipeline):
    with pytest.raises(AssessmentError) as exc_info:
        assess("answer")
    assert exc_info.value.stage == "input"
    assert "intent is required" in str(exc_info.value)


def test_synthesized_mode_honors_utf8_context_window(
    controlled_pipeline,
    monkeypatch,
):
    captured = {}

    def fake_synthesize(**kwargs):
        captured.update(kwargs)
        return copy.deepcopy(RUBRIC)

    monkeypatch.setattr(assessment_mod, "synthesize", fake_synthesize)
    result = assess(
        "answer",
        intent="inspect",
        context="ééé",
        context_window_bytes=5,
        backend="controlled",
    )
    assert result.aggregate == 8.0
    assert captured["context_summary"] == "éé"


def test_rubric_sources_are_mutually_exclusive(controlled_pipeline):
    with pytest.raises(AssessmentError) as exc_info:
        assess("answer", rubric=RUBRIC, artifact_class="repo-readme")
    assert exc_info.value.stage == "input"
    assert "mutually exclusive" in str(exc_info.value)


def test_artifact_class_needs_no_intent_or_context(controlled_pipeline):
    result = assess("answer", artifact_class="repo-readme")
    assert result.rubric["rubric_source"] == "class-template"


def test_cli_and_api_share_the_same_result_contract(
    controlled_pipeline,
    monkeypatch,
    tmp_path,
):
    target = tmp_path / "README.md"
    output = tmp_path / "result.json"
    target.write_text("answer")
    direct = assess_path(
        target,
        context_path=target,
        artifact_class="repo-readme",
        backend="ollama-local",
    ).to_dict()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hermes-rubric",
            "--target",
            str(target),
            "--artifact-class",
            "repo-readme",
            "--backend",
            "ollama-local",
            "--out",
            str(output),
        ],
    )
    cli_mod.main()
    cli_payload = json.loads(output.read_text())
    direct["receipt"].pop("timestamp_utc")
    cli_payload["receipt"].pop("timestamp_utc")
    assert cli_payload == direct


@pytest.mark.parametrize(
    ("attribute", "stage"),
    [("collect_evidence", "evidence"), ("score_dimensions", "score")],
)
def test_stage_failures_are_normalized_and_chained(
    controlled_pipeline,
    monkeypatch,
    attribute,
    stage,
):
    cause = LookupError("controlled failure")

    def fail(**kwargs):
        raise cause

    monkeypatch.setattr(assessment_mod, attribute, fail)
    with pytest.raises(AssessmentError) as exc_info:
        assess("answer", rubric=RUBRIC, backend="controlled")
    assert exc_info.value.stage == stage
    assert exc_info.value.__cause__ is cause
