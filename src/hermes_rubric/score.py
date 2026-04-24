"""Stage 3: score each dimension against evidence, produce aggregate."""

import json
from typing import Any

from . import backends

_SCORE_PROMPT_TEMPLATE = """\
You are a structured scorer. Score ONE rubric dimension based ONLY on the evidence provided. Do not infer beyond what the evidence shows.

DIMENSION: {dim_name}
DESCRIPTION: {dim_description}
WEIGHT: {weight} (1-3, higher = more important)

EVIDENCE:
{evidence_summary}
CONFIDENCE: {confidence}
HEDGE: {hedge}
CITATIONS:
{citations}

Scoring rules:
- Score 0-10. 0=not present/completely absent, 10=exemplary.
- If hedge=true (low-confidence evidence), the score must be in [3, 7] range — you cannot give 0 or 10 on thin evidence.
- Cite which piece of evidence drove the score.
- If evidence_found=false, score must be 1-3 at most. Never give 8+ when evidence_found=false.
- Do NOT reward surface fluency. A well-written piece with no substance scores no higher than an awkward piece with real substance.

Output valid JSON only.

Format:
{{
  "dim_id": "{dim_id}",
  "dim_name": "{dim_name}",
  "score": <0-10 integer>,
  "score_rationale": "<1-2 sentences citing specific evidence>",
  "evidence_drove_score": "<quote or citation that most influenced the score>",
  "hedge_applied": true or false
}}
"""


def score_dimensions(
    rubric: dict[str, Any],
    evidence_list: list[dict[str, Any]],
    backend: str | None = None,
) -> list[dict[str, Any]]:
    """Score each dimension. Returns list of score dicts."""
    dims_by_id = {d["id"]: d for d in rubric["dimensions"]}
    scores = []

    for ev in evidence_list:
        dim_id = ev["dim_id"]
        dim = dims_by_id.get(dim_id, {})
        s = _score_one(dim, ev, backend)
        # Enforce hedge score constraint
        if ev.get("hedge") and (s["score"] < 3 or s["score"] > 7):
            s["score"] = max(3, min(7, s["score"]))
            s["hedge_applied"] = True
            s["score_rationale"] += " [Score clamped to [3,7] due to low-confidence evidence.]"
        # Enforce no-evidence constraint
        if not ev.get("evidence_found") and s["score"] > 3:
            s["score"] = 3
            s["score_rationale"] += " [Score capped at 3: no evidence found.]"
        scores.append(s)

    return scores


def compute_aggregate(
    rubric: dict[str, Any],
    scores: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute weighted aggregate score and identify hedge dimensions."""
    scores_by_id = {s["dim_id"]: s for s in scores}

    total_weight = 0
    weighted_sum = 0.0
    hedge_dims = []
    dim_summaries = []

    for dim in rubric["dimensions"]:
        dim_id = dim["id"]
        weight = dim.get("weight", 1)
        s = scores_by_id.get(dim_id)
        if s is None:
            continue
        score = s["score"]
        weighted_sum += score * weight
        total_weight += weight
        if s.get("hedge_applied") or dim.get("hedge"):
            hedge_dims.append(dim["name"])
        dim_summaries.append({
            "dim_id": dim_id,
            "name": dim["name"],
            "score": score,
            "weight": weight,
            "hedge": s.get("hedge_applied", False),
        })

    aggregate = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0
    return {
        "aggregate": aggregate,
        "max_possible": 10.0,
        "hedge_dims": hedge_dims,
        "hedge_note": (
            f"{len(hedge_dims)} dimension(s) had thin evidence — scores for these are less reliable: "
            + ", ".join(hedge_dims)
        ) if hedge_dims else "All dimensions had sufficient evidence.",
        "dim_summaries": dim_summaries,
    }


def _score_one(
    dim: dict[str, Any],
    ev: dict[str, Any],
    backend: str | None,
) -> dict[str, Any]:
    citations_text = "\n".join(
        f"  - \"{c.get('quote', '')}\" [{c.get('location', '')}]"
        for c in ev.get("citations", [])
    ) or "  (none)"

    prompt = _SCORE_PROMPT_TEMPLATE.format(
        dim_id=ev["dim_id"],
        dim_name=dim.get("name", ev.get("dim_name", ev["dim_id"])),
        dim_description=dim.get("description", ""),
        weight=dim.get("weight", 1),
        evidence_summary=ev.get("evidence_summary", "(not available)"),
        confidence=ev.get("confidence", "low"),
        hedge=ev.get("hedge", False),
        citations=citations_text,
    )

    raw = backends.call(prompt, backend=backend)
    try:
        result = _extract_json(raw)
    except ValueError:
        result = {
            "dim_id": ev["dim_id"],
            "dim_name": dim.get("name", ev["dim_id"]),
            "score": 3,
            "score_rationale": f"Scoring failed (JSON parse error). Defaulting to 3. Raw: {raw[:200]}",
            "evidence_drove_score": "(parse error)",
            "hedge_applied": True,
        }

    # Clamp score to valid range
    result["score"] = max(0, min(10, int(result.get("score", 3))))
    return result


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:  # noqa: silent
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:  # noqa: silent
            pass
    raise ValueError(f"Cannot extract JSON from score response: {text[:300]}")
