"""Tests for G7: native --scope-class and --intent-debias preambles."""

import io
import json
from unittest.mock import patch

import pytest

from hermes_rubric.preambles import (
    INTENT_DEBIAS_PREAMBLE,
    SCOPE_PREAMBLES,
    compose_intent,
    detect_valence,
)


def _rubric():
    return {
        "rubric_intent": "test",
        "target_type": "x",
        "dimensions": [
            {"id": f"dim_{i}", "name": f"D{i}", "description": "d",
             "evidence_instructions": "e", "weight": 1, "hedge": False}
            for i in range(1, 4)
        ],
    }


# ----- (a) preamble injection per scope class -----

@pytest.mark.parametrize("scope", ["gate-plan", "sweep-plan", "results-bundle"])
def test_scope_class_preamble_injected(scope):
    """Each scope class injects its specific preamble verbatim."""
    composed = compose_intent("rate it", scope_class=scope)
    assert SCOPE_PREAMBLES[scope] in composed
    assert "INTENT (from framer): rate it" in composed
    # Other scopes' preambles must NOT leak in.
    for other, text in SCOPE_PREAMBLES.items():
        if other != scope:
            assert text not in composed


def test_unknown_scope_class_raises():
    with pytest.raises(ValueError, match="Unknown scope_class"):
        compose_intent("rate", scope_class="not-a-scope")


# ----- (b) intent-debias warns on valence words -----

def test_detect_valence_finds_loaded_words():
    assert "sound" in detect_valence("evaluate whether the plan is sound")
    assert "ready" in detect_valence("is this ready to ship")
    assert "rigorous" in detect_valence("how rigorous is the analysis")


def test_detect_valence_neutral_intent():
    assert detect_valence("score against the listed criteria") == []


def test_intent_debias_emits_valence_warning():
    """When intent contains valence words, a stderr warning is emitted."""
    buf = io.StringIO()
    composed = compose_intent(
        "evaluate whether the gate is sound and ready",
        intent_debias=True,
        warn_stream=buf,
    )
    err = buf.getvalue()
    assert "valence words" in err
    assert "sound" in err
    assert "ready" in err
    assert INTENT_DEBIAS_PREAMBLE in composed


def test_intent_debias_no_warning_on_neutral_intent():
    buf = io.StringIO()
    composed = compose_intent(
        "score against the listed criteria",
        intent_debias=True,
        warn_stream=buf,
    )
    assert buf.getvalue() == ""
    # Preamble still injected — debias is requested even when nothing fires.
    assert INTENT_DEBIAS_PREAMBLE in composed


# ----- preamble ordering -----

def test_preamble_order_debias_then_scope_then_intent():
    composed = compose_intent(
        "rate the gate",
        scope_class="gate-plan",
        intent_debias=True,
        warn_stream=io.StringIO(),
    )
    i_debias = composed.index(INTENT_DEBIAS_PREAMBLE)
    i_scope = composed.index(SCOPE_PREAMBLES["gate-plan"])
    i_intent = composed.index("INTENT (from framer):")
    assert i_debias < i_scope < i_intent


# ----- (c) no-flag behavior is identical -----

def test_no_flags_returns_intent_unchanged():
    intent = "evaluate against published criteria"
    assert compose_intent(intent) == intent
    assert compose_intent(intent, scope_class=None, intent_debias=False) == intent


def test_synthesize_no_flags_passes_intent_unchanged():
    """Calling synthesize() without G7 flags must produce the pre-G7 prompt."""
    from hermes_rubric import synthesize as synth_mod

    captured = {}

    def fake_call(prompt, backend=None, max_tokens=2048):
        captured["prompt"] = prompt
        return json.dumps(_rubric())

    with patch.object(synth_mod.backends, "call", side_effect=fake_call):
        synth_mod.synthesize(
            intent="evaluate against criteria",
            context_summary="ctx",
            target_type="paper",
            backend="claude-cli",
        )
    # No preamble markers present.
    assert "INTENT-DEBIAS NOTICE" not in captured["prompt"]
    assert "SCOPE-CLASS NOTICE" not in captured["prompt"]
    assert "INTENT: evaluate against criteria" in captured["prompt"]


def test_synthesize_with_scope_class_injects_preamble():
    from hermes_rubric import synthesize as synth_mod

    captured = {}

    def fake_call(prompt, backend=None, max_tokens=2048):
        captured["prompt"] = prompt
        return json.dumps(_rubric())

    with patch.object(synth_mod.backends, "call", side_effect=fake_call):
        synth_mod.synthesize(
            intent="rate this gate",
            context_summary="ctx",
            target_type="plan",
            backend="claude-cli",
            scope_class="gate-plan",
        )
    assert "SCOPE-CLASS NOTICE" in captured["prompt"]
    assert "GATE PLAN" in captured["prompt"]


def test_synthesize_with_intent_debias_injects_preamble():
    from hermes_rubric import synthesize as synth_mod

    captured = {}

    def fake_call(prompt, backend=None, max_tokens=2048):
        captured["prompt"] = prompt
        return json.dumps(_rubric())

    with patch.object(synth_mod.backends, "call", side_effect=fake_call):
        synth_mod.synthesize(
            intent="evaluate whether the design is sound",
            context_summary="ctx",
            target_type="plan",
            backend="claude-cli",
            intent_debias=True,
        )
    assert "INTENT-DEBIAS NOTICE" in captured["prompt"]
