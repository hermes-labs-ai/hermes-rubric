"""DEPRECATED shim — preambles moved to ``hermes_blind`` in v0.1.3.

The bias-compensation strings (intent-debias and scope-class preambles)
that used to live here are now first-class in the ``hermes-blind``
package, where they belong (same domain as the [HERMES-BLIND] wrapper).

This module is kept for one migration cycle as a thin re-export so that
external callers importing from ``hermes_rubric.preambles`` continue to
work. New code should import from ``hermes_blind`` directly.

Will be removed in hermes-rubric v0.2.0.
"""
from __future__ import annotations

from hermes_blind.preambles import (  # noqa: F401  (re-exports)
    INTENT_DEBIAS_PREAMBLE,
    SCOPE_CHOICES,
    SCOPE_PREAMBLES,
    VALENCE_WORDS,
    compose_intent,
    detect_valence,
    intent_debias,
    scope_class_preamble,
    wrap_intent_for_rubric,
)

__all__ = [
    "INTENT_DEBIAS_PREAMBLE",
    "SCOPE_PREAMBLES",
    "SCOPE_CHOICES",
    "VALENCE_WORDS",
    "compose_intent",
    "detect_valence",
    "intent_debias",
    "scope_class_preamble",
    "wrap_intent_for_rubric",
]
