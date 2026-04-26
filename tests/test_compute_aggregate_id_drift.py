"""Regression test for stage-3 LLM dim_id drift in compute_aggregate.

Stage-3 LLMs sometimes return the dim NAME in the `dim_id` field instead of
the synthesized `dim_N` id. Without name-fallback in compute_aggregate,
this silently zeroes the aggregate when all dims drift (or biases it
upward when only some drift, by dropping the drifted-and-typically-lower
dims from the weighted average).

Caught 2026-04-26: eval-coverage rubric showed aggregate=0.0 despite per-dim
scores in [2,6]. id_mismatch_count was 7-of-7. The fallback chain
(by-id → by-name → by-normalized-name) recovered the correct aggregate (5.6).
"""

from __future__ import annotations

from hermes_rubric.score import compute_aggregate


def _rubric():
    return {
        "rubric_intent": "test",
        "target_type": "test",
        "dimensions": [
            {"id": "dim_1", "name": "Audience Mapping", "weight": 3,
             "description": "x", "evidence_instructions": "y", "hedge": False},
            {"id": "dim_2", "name": "Mechanism Isolation", "weight": 2,
             "description": "x", "evidence_instructions": "y", "hedge": False},
            {"id": "dim_3", "name": "Cross-Audience Consolidation", "weight": 1,
             "description": "x", "evidence_instructions": "y", "hedge": False},
        ],
    }


def test_aggregate_with_id_drift_recovers():
    """All 3 dims have LLM-drifted dim_ids (returning name-as-id). Without
    fallback, aggregate would be 0.0. With fallback, it's the real
    weighted average."""
    scores = [
        {"dim_id": "Audience Mapping", "dim_name": "Audience Mapping",
         "score": 6, "hedge_applied": False},
        {"dim_id": "Mechanism Isolation", "dim_name": "Mechanism Isolation",
         "score": 6, "hedge_applied": False},
        {"dim_id": "Cross-Audience Consolidation", "dim_name": "Cross-Audience Consolidation",
         "score": 2, "hedge_applied": False},
    ]
    result = compute_aggregate(_rubric(), scores)
    # weighted avg = (6*3 + 6*2 + 2*1) / (3+2+1) = 32/6 = 5.333... → rounded to 5.3
    assert result["aggregate"] == 5.3, f"expected 5.3, got {result['aggregate']}"
    assert result["id_mismatch_count"] == 3
    assert len(result["dim_summaries"]) == 3


def test_aggregate_with_no_drift_unchanged():
    """No drift: synthesized dim_ids match scoring dim_ids exactly. Aggregate
    is computed normally, no mismatches."""
    scores = [
        {"dim_id": "dim_1", "dim_name": "Audience Mapping",
         "score": 6, "hedge_applied": False},
        {"dim_id": "dim_2", "dim_name": "Mechanism Isolation",
         "score": 6, "hedge_applied": False},
        {"dim_id": "dim_3", "dim_name": "Cross-Audience Consolidation",
         "score": 2, "hedge_applied": False},
    ]
    result = compute_aggregate(_rubric(), scores)
    assert result["aggregate"] == 5.3
    assert result["id_mismatch_count"] == 0


def test_aggregate_with_partial_drift_does_not_drop_dims():
    """Only some dim_ids drift. Without fallback, those dims are silently
    dropped from the aggregate. With fallback, they contribute correctly."""
    scores = [
        {"dim_id": "dim_1", "dim_name": "Audience Mapping",
         "score": 6, "hedge_applied": False},
        # This one drifted: weight 2, score 6, would be dropped without fallback
        {"dim_id": "Mechanism Isolation", "dim_name": "Mechanism Isolation",
         "score": 6, "hedge_applied": False},
        # And this one: weight 1, score 2, would also be dropped
        {"dim_id": "Cross-Audience Consolidation", "dim_name": "Cross-Audience Consolidation",
         "score": 2, "hedge_applied": False},
    ]
    result = compute_aggregate(_rubric(), scores)
    # With dropping: only dim_1 (weight 3, score 6) contributes → aggregate = 6.0
    # With fallback: all 3 contribute → aggregate = 5.3
    assert result["aggregate"] == 5.3, (
        f"partial drift produced {result['aggregate']} — fallback didn't fire "
        "for the drifted dims; aggregate was biased upward by dropping them"
    )
    assert result["id_mismatch_count"] == 2


def test_aggregate_with_normalized_name_drift():
    """LLM returned dim_id with case + dash drift (e.g., 'mechanism_isolation'
    when the rubric named it 'Mechanism Isolation'). The normalized-name
    fallback should still match."""
    scores = [
        {"dim_id": "dim_1", "dim_name": "Audience Mapping",
         "score": 6, "hedge_applied": False},
        {"dim_id": "mechanism_isolation", "dim_name": "Mechanism Isolation",
         "score": 6, "hedge_applied": False},
        {"dim_id": "cross-audience-consolidation", "dim_name": "Cross-Audience Consolidation",
         "score": 2, "hedge_applied": False},
    ]
    result = compute_aggregate(_rubric(), scores)
    assert result["aggregate"] == 5.3
    assert result["id_mismatch_count"] == 2


def test_aggregate_zero_when_no_scores():
    """Edge case: no scores at all → aggregate is 0.0 (the legitimate one)."""
    result = compute_aggregate(_rubric(), [])
    assert result["aggregate"] == 0.0
    assert result["id_mismatch_count"] == 0
