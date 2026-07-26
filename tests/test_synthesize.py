"""Tests for rubric synthesis stage."""

import json
from unittest.mock import patch

import pytest


def _make_rubric(dims=None):
    if dims is None:
        dims = [
            {
                "id": "dim_1",
                "name": "Evidence Grounding",
                "description": "Claims cite observable sources.",
                "evidence_instructions": "Look for file:line pointers, DOIs, or named datasets.",
                "weight": 3,
                "hedge": False,
            },
            {
                "id": "dim_2",
                "name": "Claim Precision",
                "description": "Numeric claims are specific, not vague.",
                "evidence_instructions": "Find numeric ranges and check if sources are named.",
                "weight": 2,
                "hedge": False,
            },
            {
                "id": "dim_3",
                "name": "Limitation Disclosure",
                "description": "Limitations are named explicitly.",
                "evidence_instructions": "Look for a limitations section or inline caveats.",
                "weight": 2,
                "hedge": True,
            },
        ]
    return {
        "rubric_intent": "Rate the paper as a publication-ready research artifact",
        "target_type": "paper",
        "dimensions": dims,
    }


def test_synthesize_returns_valid_rubric():
    """Synthesize returns a dict with required fields."""
    from hermes_rubric import synthesize as synth_mod

    mock_rubric = _make_rubric()
    with patch.object(synth_mod.backends, "call", return_value=json.dumps(mock_rubric)):
        result = synth_mod.synthesize(
            intent="rate as publication-ready",
            context_summary="style guide content",
            target_type="paper",
            backend="claude-cli",
        )

    assert "dimensions" in result
    assert len(result["dimensions"]) == 3
    assert result["rubric_intent"] != ""


def test_synthesize_preserves_the_configured_target_type():
    """Backend output cannot silently replace caller-bound target metadata."""
    from hermes_rubric import synthesize as synth_mod

    mock_rubric = _make_rubric()
    mock_rubric["target_type"] = "paper-preprint"
    with patch.object(synth_mod.backends, "call", return_value=json.dumps(mock_rubric)):
        result = synth_mod.synthesize(
            intent="rate as publication-ready",
            context_summary="style guide content",
            target_type="results-bundle",
            backend="claude-cli",
        )

    assert result["target_type"] == "results-bundle"


def test_synthesize_validates_minimum_dimensions():
    """Synthesize rejects rubric with fewer than 3 dimensions."""
    from hermes_rubric import synthesize as synth_mod

    bad_rubric = _make_rubric(dims=[
        {"id": "dim_1", "name": "A", "description": "x", "evidence_instructions": "y", "weight": 1}
    ])
    with patch.object(synth_mod.backends, "call", return_value=json.dumps(bad_rubric)):
        with pytest.raises(ValueError, match="minimum 3 required"):
            synth_mod.synthesize(
                intent="rate",
                context_summary="",
                target_type="paper",
                backend="claude-cli",
            )


def test_synthesize_extracts_json_from_prose():
    """Synthesize can extract JSON even when LLM adds prose around it."""
    from hermes_rubric import synthesize as synth_mod

    mock_rubric = _make_rubric()
    raw_with_prose = f"Here is the rubric:\n{json.dumps(mock_rubric)}\nHope this helps!"
    with patch.object(synth_mod.backends, "call", return_value=raw_with_prose):
        result = synth_mod.synthesize(
            intent="rate",
            context_summary="",
            target_type="paper",
            backend="claude-cli",
        )
    assert "dimensions" in result
