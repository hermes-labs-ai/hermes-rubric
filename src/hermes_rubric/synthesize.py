"""Stage 1: synthesize a rubric from (intent, context, target_type)."""

import json
from typing import Any

from . import backends
from .preambles import wrap_intent_for_rubric

_SYNTH_PROMPT_TEMPLATE = """\
You are a rubric generator. Your job: produce a structured evaluation rubric for the given intent and context.

INTENT: {intent}
TARGET TYPE: {target_type}
CONTEXT SUMMARY:
{context_summary}

TARGET EXCERPT (the artifact whose dimensions you are designing — first {target_excerpt_max} chars; the full target will be evaluated in a later stage, you do NOT need to score it now):
{target_excerpt}

Requirements:
- Produce 5-8 dimensions that are SPECIFIC to this intent and domain. Do not produce generic dimensions that apply to everything.
- Each dimension must have a NAME, a one-sentence DESCRIPTION of what it measures, and EVIDENCE INSTRUCTIONS (how to find observable evidence for this dimension in the target).
- Dimensions must be DISCRIMINATING: a weak and strong target must score differently. If two targets would always get the same score, drop that dimension.
- Do NOT invent dimensions for things you cannot observe in the target.
- Hedge where evidence may be thin: mark optional dimensions with "hedge: true".

Output valid JSON only. No prose before or after. Do NOT ask for additional input — the target excerpt above is sufficient context to design the rubric.

Format:
{{
  "rubric_intent": "<one-line restatement of the goal>",
  "target_type": "<type>",
  "dimensions": [
    {{
      "id": "dim_1",
      "name": "<short name>",
      "description": "<what it measures>",
      "evidence_instructions": "<where and how to look>",
      "weight": <1-3 integer, 3=most important>,
      "hedge": false
    }}
  ]
}}
"""


_TARGET_EXCERPT_CHARS = 2000


def synthesize(
    intent: str,
    context_summary: str,
    target_type: str,
    backend: str | None = None,
    *,
    scope_class: str | None = None,
    intent_debias: bool = False,
    target_excerpt: str = "",
) -> dict[str, Any]:
    """Produce a rubric dict from intent + context summary + target type.

    ``scope_class`` and ``intent_debias`` (G7) prepend optional preambles to
    the intent before formatting. ``target_excerpt`` (added 2026-04-26) passes
    the first ~2000 chars of the target to the synthesizer so models that
    refuse-to-generate-without-target (Haiku) can produce a rubric. When both
    scope/debias unset and target_excerpt empty, the call is identical to
    v0.1.x behavior except for the new prompt section labeled
    "TARGET EXCERPT (...)" which most non-pedantic models will treat as
    additional context.
    """
    composed_intent = wrap_intent_for_rubric(
        intent,
        scope_class=scope_class,
        debias=intent_debias,
    )
    prompt = _SYNTH_PROMPT_TEMPLATE.format(
        intent=composed_intent,
        target_type=target_type,
        context_summary=context_summary[:4000],
        target_excerpt=target_excerpt[:_TARGET_EXCERPT_CHARS] if target_excerpt else "(target excerpt not provided — design dimensions from intent + context + target_type alone; do not request additional input)",
        target_excerpt_max=_TARGET_EXCERPT_CHARS,
    )
    raw = backends.call(prompt, backend=backend)
    # Extract JSON from response (may have leading/trailing prose from some backends)
    rubric = _extract_json(raw, "rubric")
    # ``target_type`` is caller-bound input metadata, not a field the backend
    # may reclassify while synthesizing the rubric.
    rubric["target_type"] = target_type
    _validate_rubric(rubric)
    return rubric


def _extract_json(text: str, kind: str) -> dict[str, Any]:
    """Best-effort JSON extraction from LLM output."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:  # noqa: silent
        pass
    # Try to find the outermost {} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:  # noqa: silent
            pass
    raise ValueError(f"Could not extract valid JSON from {kind} LLM output. Raw: {text[:500]}")


def _validate_rubric(rubric: dict) -> None:
    required = {"rubric_intent", "dimensions"}
    missing = required - set(rubric.keys())
    if missing:
        raise ValueError(f"Rubric missing required fields: {missing}")
    dims = rubric.get("dimensions", [])
    if len(dims) < 3:
        raise ValueError(f"Rubric has only {len(dims)} dimensions — minimum 3 required.")
    for i, d in enumerate(dims):
        for field in ("id", "name", "description", "evidence_instructions"):
            if field not in d:
                raise ValueError(f"Dimension {i} missing field '{field}'")
