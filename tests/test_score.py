"""Tests for scoring stage, including hedge enforcement."""

import json
import pytest
from unittest.mock import patch


def _make_rubric():
    return {
        "rubric_intent": "rate paper quality",
        "target_type": "paper",
        "dimensions": [
            {"id": "dim_1", "name": "Evidence Grounding", "description": "Claims cite sources.",
             "evidence_instructions": "Look for pointers.", "weight": 3, "hedge": False},
            {"id": "dim_2", "name": "Precision", "description": "Numbers are specific.",
             "evidence_instructions": "Find numbers.", "weight": 2, "hedge": False},
            {"id": "dim_3", "name": "Limitations", "description": "Limitations named.",
             "evidence_instructions": "Limitations section.", "weight": 1, "hedge": True},
        ]
    }


def _make_evidence(dim_id, confidence="high", hedge=False, found=True):
    return {
        "dim_id": dim_id,
        "dim_name": dim_id,
        "evidence_found": found,
        "confidence": confidence,
        "hedge": hedge,
        "citations": [{"quote": "results show 96.4%", "location": "file:line 42"}],
        "evidence_summary": "Clear evidence found in results section.",
    }


def _make_score_response(dim_id, score):
    return json.dumps({
        "dim_id": dim_id,
        "dim_name": dim_id,
        "score": score,
        "score_rationale": "Based on evidence.",
        "evidence_drove_score": "quote from results",
        "hedge_applied": False,
    })


def test_hedge_clamps_score_to_midrange():
    """Hedged dimensions cannot score 0-2 or 8-10."""
    from hermes_rubric import score as score_mod

    rubric = _make_rubric()
    evidence_list = [
        _make_evidence("dim_1", confidence="high", hedge=False),
        _make_evidence("dim_2", confidence="high", hedge=False),
        _make_evidence("dim_3", confidence="low", hedge=True),
    ]

    score_responses = [
        _make_score_response("dim_1", 9),
        _make_score_response("dim_2", 7),
        _make_score_response("dim_3", 9),  # should be clamped to 7
    ]

    with patch.object(score_mod.backends, "call", side_effect=score_responses):
        scores = score_mod.score_dimensions(rubric=rubric, evidence_list=evidence_list, backend="claude-cli")

    dim3_score = next(s for s in scores if s["dim_id"] == "dim_3")
    assert dim3_score["score"] <= 7, f"Hedge not applied: score={dim3_score['score']}"
    assert dim3_score["score"] >= 3


def test_no_evidence_caps_score():
    """evidence_found=false caps score at 3."""
    from hermes_rubric import score as score_mod

    rubric = _make_rubric()
    evidence_list = [
        _make_evidence("dim_1", found=False, confidence="low", hedge=True),
        _make_evidence("dim_2", found=True, confidence="high", hedge=False),
        _make_evidence("dim_3", found=True, confidence="medium", hedge=True),
    ]

    score_responses = [
        _make_score_response("dim_1", 8),  # should be capped at 3
        _make_score_response("dim_2", 8),
        _make_score_response("dim_3", 5),
    ]

    with patch.object(score_mod.backends, "call", side_effect=score_responses):
        scores = score_mod.score_dimensions(rubric=rubric, evidence_list=evidence_list, backend="claude-cli")

    dim1_score = next(s for s in scores if s["dim_id"] == "dim_1")
    assert dim1_score["score"] <= 3, f"No-evidence cap not applied: score={dim1_score['score']}"


@pytest.mark.parametrize(
    ("raw", "expected_score"),
    [
        (json.dumps({"score": 8}), 8),
        (json.dumps({"dim_id": "wrong", "dim_name": "Drifted", "score": 8}), 8),
        ("not json", 3),
    ],
    ids=["identity-omitted", "identity-drifted", "parse-fallback"],
)
def test_per_dimension_scores_pin_canonical_dimension_identity(raw, expected_score):
    """The synthesized rubric, not Stage 3 output, owns dimension identity."""
    from hermes_rubric import score as score_mod

    rubric = _make_rubric()
    evidence_list = [_make_evidence("dim_1")]

    with patch.object(score_mod.backends, "call", return_value=raw):
        scores = score_mod.score_dimensions(
            rubric=rubric,
            evidence_list=evidence_list,
            backend="stub",
        )

    assert scores[0]["dim_id"] == "dim_1"
    assert scores[0]["dim_name"] == "Evidence Grounding"
    assert scores[0]["score"] == expected_score
    assert "score_rationale" in scores[0]
    assert "evidence_drove_score" in scores[0]
    assert "hedge_applied" in scores[0]


def test_per_dimension_omitted_fields_still_apply_hedge_clamp():
    """An incomplete Stage-3 response remains safe to clamp."""
    from hermes_rubric import score as score_mod

    rubric = _make_rubric()
    evidence_list = [_make_evidence("dim_1", hedge=True)]

    with patch.object(score_mod.backends, "call", return_value=json.dumps({"score": 10})):
        scores = score_mod.score_dimensions(
            rubric=rubric,
            evidence_list=evidence_list,
            backend="stub",
        )

    assert scores[0]["score"] == 7
    assert scores[0]["hedge_applied"] is True
    assert "clamped" in scores[0]["score_rationale"]


def test_aggregate_weighted():
    """Aggregate respects dimension weights."""
    from hermes_rubric import score as score_mod

    rubric = _make_rubric()
    # dim_1 weight=3, dim_2 weight=2, dim_3 weight=1
    scores = [
        {"dim_id": "dim_1", "score": 10, "hedge_applied": False},
        {"dim_id": "dim_2", "score": 0, "hedge_applied": False},
        {"dim_id": "dim_3", "score": 5, "hedge_applied": True},
    ]
    result = score_mod.compute_aggregate(rubric=rubric, scores=scores)
    # (10*3 + 0*2 + 5*1) / 6 = 35/6 ≈ 5.8
    assert result["aggregate"] == pytest.approx(35 / 6, abs=0.2)


def test_hedge_dims_reported_in_aggregate():
    """Hedged dimensions are reported in the aggregate output."""
    from hermes_rubric import score as score_mod

    rubric = _make_rubric()
    scores = [
        {"dim_id": "dim_1", "score": 8, "hedge_applied": False},
        {"dim_id": "dim_2", "score": 7, "hedge_applied": False},
        {"dim_id": "dim_3", "score": 5, "hedge_applied": True},
    ]
    result = score_mod.compute_aggregate(rubric=rubric, scores=scores)
    assert len(result["hedge_dims"]) > 0
