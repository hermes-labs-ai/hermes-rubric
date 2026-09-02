"""Contract tests for the optional Inspect AI scorer."""

from __future__ import annotations

import asyncio

from inspect_ai.model import ModelName, ModelOutput
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState

from hermes_rubric.errors import AssessmentError
from hermes_rubric.integrations import inspect_ai as integration
from hermes_rubric.models import AssessmentResult, CoverageReport


def _state() -> TaskState:
    return TaskState(
        model=ModelName("mock/model"),
        sample_id="sample-1",
        epoch=1,
        input="Explain the observation and cite the supplied evidence.",
        messages=[],
        output=ModelOutput.from_content("mock/model", "The measured value is 4."),
    )


def _result() -> AssessmentResult:
    return AssessmentResult(
        rubric={"title": "Evidence"},
        evidence_citations=[{"source": "target", "quote": "value is 4"}],
        per_dim_scores=[{"dim_id": "d1", "score": 8}],
        aggregate=8.0,
        max_possible=10.0,
        hedge_dims=[],
        hedge_note="",
        dim_summaries=[{"dim_id": "d1", "name": "Support", "score": 8}],
        receipt={"rubric_hash": "abc"},
        coverage=CoverageReport(
            status="complete",
            strategy="utf8_prefix",
            visible_bytes=24,
            total_bytes=24,
        ),
    )


def test_scorer_maps_inspect_sample_and_preserves_receipt(monkeypatch):
    captured = {}

    async def fake_assess(target, **kwargs):
        captured["target"] = target
        captured.update(kwargs)
        return _result()

    monkeypatch.setattr(integration, "assess_async", fake_assess)

    score = asyncio.run(
        integration.hermes_rubric_scorer(
            intent="Assess evidence support.", backend="openai-sdk"
        )(_state(), Target("The reference value is 4."))
    )

    assert score.value == 8.0
    assert score.metadata["hermes_rubric"]["receipt"]["rubric_hash"] == "abc"
    assert captured["target"] == "The measured value is 4."
    assert "Explain the observation" in captured["context"]
    assert "The reference value is 4" in captured["context"]


def test_scorer_can_record_visible_unscored_failure(monkeypatch):
    async def fail(*args, **kwargs):
        raise AssessmentError("evidence", "provider unavailable")

    monkeypatch.setattr(integration, "assess_async", fail)

    score = asyncio.run(
        integration.hermes_rubric_scorer(
            intent="Assess evidence support.", fail_on_error=False
        )(_state(), Target("The reference value is 4."))
    )

    assert score.metadata == {
        "hermes_rubric": {
            "status": "error",
            "reason": "grader_failed",
            "stage": "evidence",
        }
    }
