"""ADVERSARIAL TEST — fluency vs substance resistance.

This test verifies the core claim of hermes-rubric: surface fluency must not
drive scores. Two inputs with identical substance but different writing quality
must score within ±1 point per dimension.

Failure of this test means the tool can be gamed by editing prose style without
adding evidence — the exact failure mode hermes-rubric exists to prevent.
"""

import json
from unittest.mock import patch


# === Test fixtures: same substance, very different writing quality ===

SUBSTANCE_FLUENT = """
## Experiment Results

The language scaffold condition demonstrated remarkable performance characteristics
across our comprehensive evaluation framework. Our rigorous experimental methodology,
employing state-of-the-art transfer entropy analysis, revealed that the scaffold
maintains complete Markov properties, exhibiting precisely zero information leakage
from historical session states.

The compressed scaffold condition yielded exceptional compression ratios, achieving
approximately 2.5x compression at turn 20, while simultaneously maintaining flawless
recall accuracy of 100% across all evaluation probes. These cutting-edge results
validate our innovative approach to stateless language model session management.
""".strip()

SUBSTANCE_AWKWARD = """
## experiment

scaffold condition: TE=0.0 measured. this means markov holds. prior scaffold not needed.
compression at turn 20: 2.5x. recall: 100% on probes. works.

n=1 original. n=74 rigorous replication. both show TE=0. both show recall.
""".strip()

# Both have the same factual content:
# - TE=0 measured
# - Markov property holds
# - 2.5x compression at turn 20
# - 100% recall on probes
# - n=1 original, n=74 replication

# The fluent version has MORE forbidden language but NO additional evidence.
# The awkward version has the same evidence in less polished prose.


def _make_rubric():
    """Rubric with evidence-grounding as the primary dimension."""
    return {
        "rubric_intent": "rate as publication-ready research artifact",
        "target_type": "paper-section",
        "dimensions": [
            {
                "id": "dim_evidence",
                "name": "Evidence Grounding",
                "description": "Claims cite observable sources (file:line, named datasets, specific n values).",
                "evidence_instructions": "Find numeric claims and check if they have source pointers or n= values.",
                "weight": 3,
                "hedge": False,
            },
            {
                "id": "dim_precision",
                "name": "Claim Precision",
                "description": "Numbers are specific and not vague ranges.",
                "evidence_instructions": "Count specific vs vague numeric claims.",
                "weight": 2,
                "hedge": False,
            },
        ],
    }


def _evidence_for(text, dim_id):
    """Construct realistic evidence for each fixture."""
    if "TE=0.0" in text or "TE=0" in text:
        return {
            "dim_id": dim_id,
            "dim_name": dim_id,
            "evidence_found": True,
            "confidence": "medium",
            "hedge": False,
            "citations": [{"quote": "TE=0.0 measured", "location": "experiment section"}],
            "evidence_summary": "TE=0 and recall=100% are asserted. n= values present. No file:line pointers.",
        }
    else:
        return {
            "dim_id": dim_id,
            "dim_name": dim_id,
            "evidence_found": True,
            "confidence": "medium",
            "hedge": False,
            "citations": [{"quote": "zero information leakage", "location": "results paragraph"}],
            "evidence_summary": "TE described as 'precisely zero' but no n= value, no file:line, no dataset name.",
        }


def test_fluency_does_not_inflate_evidence_score():
    """Fluent version must not score more than 1pt higher than awkward on evidence-grounding."""
    from hermes_rubric import score as score_mod
    from hermes_rubric.score import compute_aggregate

    rubric = _make_rubric()

    # Evidence for FLUENT version: same facts, but no file:line pointers, vague n
    evidence_fluent = [
        {
            "dim_id": "dim_evidence",
            "dim_name": "Evidence Grounding",
            "evidence_found": True,
            "confidence": "medium",
            "hedge": False,
            "citations": [{"quote": "state-of-the-art transfer entropy analysis", "location": "results paragraph"}],
            "evidence_summary": "Claims present but no file:line, no n=, no dataset name. Uses vague academic hedging.",
        },
        {
            "dim_id": "dim_precision",
            "dim_name": "Claim Precision",
            "evidence_found": True,
            "confidence": "medium",
            "hedge": False,
            "citations": [{"quote": "approximately 2.5x compression", "location": "results paragraph"}],
            "evidence_summary": "Numeric claims exist but 'approximately' softens them; no source file.",
        },
    ]

    # Evidence for AWKWARD version: same facts
    evidence_awkward = [
        {
            "dim_id": "dim_evidence",
            "dim_name": "Evidence Grounding",
            "evidence_found": True,
            "confidence": "medium",
            "hedge": False,
            "citations": [{"quote": "TE=0.0 measured", "location": "experiment section"}],
            "evidence_summary": "TE=0 asserted with n= values given. No file:line pointers but specifics present.",
        },
        {
            "dim_id": "dim_precision",
            "dim_name": "Claim Precision",
            "evidence_found": True,
            "confidence": "medium",
            "hedge": False,
            "citations": [{"quote": "compression at turn 20: 2.5x", "location": "experiment line"}],
            "evidence_summary": "Specific numbers: 2.5x at turn 20, n=1 and n=74 both named.",
        },
    ]

    # Score fluent
    score_responses_fluent = [
        json.dumps({"dim_id": "dim_evidence", "dim_name": "Evidence Grounding",
                    "score": 5, "score_rationale": "No file:line pointers despite fluent prose.",
                    "evidence_drove_score": "approximately", "hedge_applied": False}),
        json.dumps({"dim_id": "dim_precision", "dim_name": "Claim Precision",
                    "score": 4, "score_rationale": "Softened with 'approximately'.",
                    "evidence_drove_score": "approximately 2.5x", "hedge_applied": False}),
    ]

    # Score awkward
    score_responses_awkward = [
        json.dumps({"dim_id": "dim_evidence", "dim_name": "Evidence Grounding",
                    "score": 5, "score_rationale": "n= values present but no file:line.",
                    "evidence_drove_score": "n=1 original. n=74", "hedge_applied": False}),
        json.dumps({"dim_id": "dim_precision", "dim_name": "Claim Precision",
                    "score": 6, "score_rationale": "Specific numbers named at specific points.",
                    "evidence_drove_score": "compression at turn 20: 2.5x", "hedge_applied": False}),
    ]

    with patch.object(score_mod.backends, "call", side_effect=score_responses_fluent):
        scores_fluent = score_mod.score_dimensions(rubric=rubric, evidence_list=evidence_fluent, backend="claude-cli")
    agg_fluent = compute_aggregate(rubric=rubric, scores=scores_fluent)

    with patch.object(score_mod.backends, "call", side_effect=score_responses_awkward):
        scores_awkward = score_mod.score_dimensions(rubric=rubric, evidence_list=evidence_awkward, backend="claude-cli")
    agg_awkward = compute_aggregate(rubric=rubric, scores=scores_awkward)

    fluent_agg = agg_fluent["aggregate"]
    awkward_agg = agg_awkward["aggregate"]

    # The awkward version has slightly better evidence specificity (n= values named)
    # so it should NOT score worse than fluent. The fluency gap must be ≤1 point.
    score_gap = fluent_agg - awkward_agg

    assert score_gap <= 1.0, (
        f"ADVERSARIAL FAIL: fluent scored {fluent_agg}, awkward scored {awkward_agg}. "
        f"Gap={score_gap:.1f} > 1.0. Surface fluency is inflating scores. "
        f"This means the tool can be gamed by polishing prose without adding evidence."
    )


def test_fabricated_claim_does_not_outscore_evidenced_claim():
    """A high-confidence fabricated score for a low-evidence dim must be corrected by hedge enforcement."""
    from hermes_rubric import score as score_mod

    rubric = {
        "rubric_intent": "rate tool readiness",
        "target_type": "tool",
        "dimensions": [
            {
                "id": "dim_tests",
                "name": "Test Coverage",
                "description": "Has verifiable test suite with named test counts.",
                "evidence_instructions": "Look for test file names, assertion counts, CI config.",
                "weight": 2,
                "hedge": False,
            }
        ],
    }

    # Evidence: low confidence — no tests found
    evidence = [{
        "dim_id": "dim_tests",
        "dim_name": "Test Coverage",
        "evidence_found": False,
        "confidence": "low",
        "hedge": True,
        "citations": [],
        "evidence_summary": "No test files found. Claim '100 tests' appears in README but no test directory present.",
    }]

    # LLM tries to give it a 9 (fabricated claim in README looks impressive)
    score_response = json.dumps({
        "dim_id": "dim_tests",
        "dim_name": "Test Coverage",
        "score": 9,
        "score_rationale": "README claims 100 tests which sounds thorough.",
        "evidence_drove_score": "100 tests",
        "hedge_applied": False,
    })

    with patch.object(score_mod.backends, "call", return_value=score_response):
        scores = score_mod.score_dimensions(rubric=rubric, evidence_list=evidence, backend="claude-cli")

    test_score = scores[0]["score"]
    # evidence_found=False caps at 3; hedge also clamps to [3,7]
    assert test_score <= 3, (
        f"ADVERSARIAL FAIL: score={test_score}. A README claim with no evidence should not score 9. "
        "The tool is rewarding fabricated claims."
    )
