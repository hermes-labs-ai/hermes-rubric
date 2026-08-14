"""Public typed-result and serialization contract."""

from __future__ import annotations

import json

from hermes_rubric import SCHEMA_VERSION, AssessmentResult, CoverageReport


def _result() -> AssessmentResult:
    return AssessmentResult(
        rubric={"dimensions": []},
        evidence_citations=[],
        per_dim_scores=[],
        aggregate=0.0,
        max_possible=10.0,
        hedge_dims=[],
        hedge_note="none",
        dim_summaries=[],
        receipt={"id": "fixed"},
        coverage=CoverageReport(
            status="complete",
            strategy="utf8-prefix",
            visible_bytes=3,
            total_bytes=3,
            considered_sources=1,
            total_sources=1,
        ),
    )


def test_result_preserves_legacy_surface_and_adds_schema_and_coverage():
    payload = _result().to_dict()
    assert list(payload) == [
        "rubric",
        "evidence_citations",
        "per_dim_scores",
        "aggregate",
        "max_possible",
        "hedge_dims",
        "hedge_note",
        "dim_summaries",
        "receipt",
        "schema_version",
        "coverage",
    ]
    assert payload["schema_version"] == SCHEMA_VERSION == "1.0"
    assert payload["coverage"]["status"] == "complete"


def test_result_serialization_is_deterministic():
    result = _result()
    assert result.to_json() == result.to_json()
    assert json.loads(result.to_json()) == result.to_dict()


def test_result_json_preserves_legacy_ascii_escaping():
    result = _result()
    result.rubric["rubric_intent"] = "café"
    assert "caf\\u00e9" in result.to_json()
