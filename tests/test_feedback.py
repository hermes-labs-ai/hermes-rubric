"""Policy-neutral quality, evidence, and coverage feedback."""

from __future__ import annotations

from hermes_rubric import AssessmentResult, CoverageReport, FeedbackPolicy


def _result(*, partial: bool = True) -> AssessmentResult:
    return AssessmentResult(
        rubric={"dimensions": []},
        evidence_citations=[
            {
                "dim_id": "quality",
                "evidence_found": True,
                "confidence": "high",
                "hedge": False,
                "citations": [{"quote": "proof"}],
            },
            {
                "dim_id": "evidence",
                "evidence_found": False,
                "confidence": "low",
                "hedge": True,
                "citations": [],
            },
        ],
        per_dim_scores=[
            {"dim_id": "quality", "dim_name": "Quality", "score": 5},
            {"dim_id": "evidence", "dim_name": "Evidence", "score": 3},
        ],
        aggregate=4.0,
        max_possible=10.0,
        hedge_dims=["Evidence"],
        hedge_note="thin",
        dim_summaries=[],
        receipt={},
        coverage=CoverageReport(
            status="partial" if partial else "complete",
            strategy="utf8-prefix",
            visible_bytes=8,
            total_bytes=12 if partial else 8,
            limitations=("Tail not inspected.",) if partial else (),
        ),
    )


def test_feedback_separates_all_three_gap_kinds():
    packet = _result().feedback(FeedbackPolicy(minimum_score=7))
    assert [finding.kind for finding in packet.findings] == [
        "quality_gap",
        "evidence_gap",
        "coverage_gap",
    ]
    assert packet.to_json() == packet.to_json()


def test_coverage_only_gap_never_becomes_revision_instruction():
    result = _result()
    packet = result.feedback()
    coverage = next(finding for finding in packet.findings if finding.kind == "coverage_gap")
    assert "rerun inspection" in coverage.action
    assert "Revise the artifact" not in coverage.action
    assert "coverage gaps as requests to inspect more material" in packet.to_prompt()


def test_quality_gap_requires_explicit_threshold_and_accepted_evidence():
    assert "quality_gap" not in {finding.kind for finding in _result().feedback().findings}
    packet = _result(partial=False).feedback(FeedbackPolicy(minimum_score=7))
    quality = [finding for finding in packet.findings if finding.kind == "quality_gap"]
    assert [finding.dimension_id for finding in quality] == ["quality"]


def test_coverage_gap_is_retained_when_finding_budget_is_one():
    packet = _result().feedback(FeedbackPolicy(minimum_score=7, max_findings=1))
    assert [finding.kind for finding in packet.findings] == ["coverage_gap"]
