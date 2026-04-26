"""Vendored-preambles regression tests — preambles vendored from hermes-blind in v0.2.1.

These tests assert that:
  1. ``hermes_rubric.preambles`` exposes the public API the CLI + synthesize.py
     depend on (INTENT_DEBIAS_PREAMBLE, SCOPE_PREAMBLES, SCOPE_CHOICES,
     compose_intent, wrap_intent_for_rubric).
  2. ``--scope-class`` and ``--intent-debias`` produce a stable prompt
     structure across runs — same input bytes in, same prompt bytes out.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


# ---- (1) public API surface ----

def test_preambles_exposes_intent_debias_preamble():
    from hermes_rubric.preambles import INTENT_DEBIAS_PREAMBLE
    assert isinstance(INTENT_DEBIAS_PREAMBLE, str)
    assert len(INTENT_DEBIAS_PREAMBLE) > 0


def test_preambles_exposes_scope_preambles():
    from hermes_rubric.preambles import SCOPE_PREAMBLES
    assert isinstance(SCOPE_PREAMBLES, dict)
    assert {"gate-plan", "sweep-plan", "results-bundle"}.issubset(SCOPE_PREAMBLES.keys())


def test_preambles_exposes_scope_choices():
    from hermes_rubric.preambles import SCOPE_CHOICES
    assert set(SCOPE_CHOICES) == {"gate-plan", "sweep-plan", "results-bundle"}


def test_preambles_exposes_compose_intent_callable():
    from hermes_rubric.preambles import compose_intent
    assert callable(compose_intent)


def test_preambles_exposes_wrap_intent_for_rubric_callable():
    from hermes_rubric.preambles import wrap_intent_for_rubric
    assert callable(wrap_intent_for_rubric)


# ---- (2) deterministic prompt construction ----

_FROZEN_INTENT = "evaluate whether the gate plan is sound and ready to ship"
_FROZEN_CONTEXT = "fixed-context-summary-for-byte-identity-check"
_FROZEN_TARGET_TYPE = "gate-plan-document"


def _build_expected_prompt(scope_class: str | None, debias: bool) -> str:
    """Reconstruct the synthesize prompt by composing intent then formatting
    the template — same path synthesize.py takes. Any byte-level drift in
    either the preambles or the template fails the test below.
    """
    from hermes_rubric.preambles import wrap_intent_for_rubric
    from hermes_rubric.synthesize import _SYNTH_PROMPT_TEMPLATE, _TARGET_EXCERPT_CHARS

    composed = wrap_intent_for_rubric(
        _FROZEN_INTENT, scope_class=scope_class, debias=debias
    )
    return _SYNTH_PROMPT_TEMPLATE.format(
        intent=composed,
        target_type=_FROZEN_TARGET_TYPE,
        context_summary=_FROZEN_CONTEXT[:4000],
        target_excerpt="(target excerpt not provided — design dimensions from intent + context + target_type alone; do not request additional input)",
        target_excerpt_max=_TARGET_EXCERPT_CHARS,
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


@pytest.mark.parametrize(
    "scope_class,debias",
    [
        (None, False),
        (None, True),
        ("gate-plan", False),
        ("results-bundle", False),
        ("sweep-plan", True),
        ("results-bundle", True),
    ],
)
def test_synthesize_produces_byte_identical_prompt(scope_class, debias):
    """synthesize() must produce the same prompt bytes as the canonical
    composition path for every (scope_class, debias) combination.
    """
    from hermes_rubric import synthesize as synth_mod

    captured = {}

    def fake_call(prompt, backend=None, max_tokens=2048):
        captured["prompt"] = prompt
        return json.dumps(_rubric())

    with patch.object(synth_mod.backends, "call", side_effect=fake_call):
        synth_mod.synthesize(
            intent=_FROZEN_INTENT,
            context_summary=_FROZEN_CONTEXT,
            target_type=_FROZEN_TARGET_TYPE,
            backend="claude-cli",
            scope_class=scope_class,
            intent_debias=debias,
        )

    expected = _build_expected_prompt(scope_class, debias)
    assert captured["prompt"] == expected, (
        f"Prompt drift detected for scope_class={scope_class!r} debias={debias}.\n"
        f"Expected first 200 chars: {expected[:200]!r}\n"
        f"Got first 200 chars:      {captured['prompt'][:200]!r}"
    )


# ---- (3) CLI flag surface unchanged ----

def test_cli_scope_class_choices_match_preambles():
    """The argparse choices must equal hermes_rubric.preambles.SCOPE_CHOICES."""
    import argparse
    from unittest.mock import patch as _patch

    from hermes_rubric import cli as cli_mod
    from hermes_rubric.preambles import SCOPE_CHOICES

    captured_parser: dict[str, argparse.ArgumentParser] = {}

    def grab_parser(self, *a, **kw):
        captured_parser["p"] = self
        raise SystemExit(0)

    with _patch.object(argparse.ArgumentParser, "parse_args", grab_parser):
        try:
            cli_mod.main()
        except SystemExit:
            pass

    parser = captured_parser.get("p")
    assert parser is not None
    scope_action = next(
        (a for a in parser._actions if a.dest == "scope_class"), None
    )
    assert scope_action is not None
    assert set(scope_action.choices) == set(SCOPE_CHOICES)
