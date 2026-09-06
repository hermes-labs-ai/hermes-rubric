"""Stage 3: score each dimension against evidence, produce aggregate."""

import json
import sys
from typing import Any

from . import backends
from .evidence import (
    SOURCE_CLASS_WEIGHT,
    BatchParseError,
    BatchTooLarge,
    _extract_json_array,
)

_BATCH_PROMPT_CEILING_CHARS = 100_000

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


_BATCHED_SCORE_PROMPT_TEMPLATE = """\
You are a structured scorer. Score EACH rubric dimension below based ONLY on the evidence inside its <DIM> block.

Treat each <DIM> block as ISOLATED. Do not let evidence from one <DIM> influence another.
Process all dimensions in one pass.

DIMENSIONS:
{dim_blocks}

Scoring rules (apply per <DIM>):
- Score 0-10. 0=not present/completely absent, 10=exemplary.
- If hedge=true (low-confidence evidence), the score must be in [3, 7] — you cannot give 0 or 10 on thin evidence.
- Cite which piece of evidence drove the score, drawn ONLY from that <DIM>'s citations block.
- If evidence_found=false, score must be 1-3 at most. Never give 8+ when evidence_found=false.
- Do NOT reward surface fluency. A well-written piece with no substance scores no higher than an awkward piece with real substance.

Output a JSON ARRAY. One element per <DIM>. Order is irrelevant — dim_id is the key.
Each element MUST include "dim_id" matching exactly one <DIM id="..."> above.
Do not invent dim_ids. Do not omit any dim_id.

Output valid JSON only. No prose before or after.

Each element format:
{{
  "dim_id": "<id matching a <DIM id='...'>>",
  "dim_name": "<name>",
  "score": <0-10 integer>,
  "score_rationale": "<1-2 sentences citing specific evidence from THIS dim's block>",
  "evidence_drove_score": "<quote or citation from THIS dim's block>",
  "hedge_applied": true or false
}}
"""


def _pin_dimension_identity(
    score: dict[str, Any],
    ev: dict[str, Any],
    dim: dict[str, Any],
) -> dict[str, Any]:
    """Complete the Stage-3 shape and pin identity to the synthesized rubric."""
    score["dim_id"] = dim.get("id", ev["dim_id"])
    score["dim_name"] = dim.get("name", ev.get("dim_name", ev["dim_id"]))
    score.setdefault("score_rationale", "")
    score.setdefault("evidence_drove_score", "")
    score.setdefault("hedge_applied", False)
    return score


def _apply_clamps(s: dict[str, Any], ev: dict[str, Any]) -> dict[str, Any]:
    """Apply hedge / no-evidence / self-marketing clamps. Mirrors original loop body."""
    if ev.get("hedge") and (s["score"] < 3 or s["score"] > 7):
        s["score"] = max(3, min(7, s["score"]))
        s["hedge_applied"] = True
        s["score_rationale"] += " [Score clamped to [3,7] due to low-confidence evidence.]"
    if not ev.get("evidence_found") and s["score"] > 3:
        s["score"] = 3
        s["score_rationale"] += " [Score capped at 3: no evidence found.]"
    if _only_self_marketing(ev) and s["score"] > 6:
        s["score"] = 6
        s["score_rationale"] += " [Score capped at 6: all citations are README/doc (self-marketing); no code/test evidence.]"
    s["citation_source_weight"] = _citation_source_weight(ev)
    s["score"] = max(0, min(10, int(s.get("score", 3))))
    return s


def score_dimensions(
    rubric: dict[str, Any],
    evidence_list: list[dict[str, Any]],
    backend: str | None = None,
    batch: bool = False,
) -> list[dict[str, Any]]:
    """Score each dimension. Returns list of score dicts.

    If batch=True, attempt one LLM call for all dimensions; fall back to per-dim
    on parse failure or oversize prompt. dim_id-keyed reassembly preserves
    rubric dim order regardless of mode.
    """
    dims_by_id = {d["id"]: d for d in rubric["dimensions"]}

    if batch and len(evidence_list) > 1:
        try:
            return _score_batched(dims_by_id, evidence_list, backend)
        except (BatchParseError, BatchTooLarge) as e:
            print(f"[hermes-rubric] batched score failed ({e.__class__.__name__}); "
                  f"falling back to per-dim", file=sys.stderr)

    scores = []
    for ev in evidence_list:
        dim_id = ev["dim_id"]
        dim = dims_by_id.get(dim_id, {})
        s = _score_one(dim, ev, backend)
        s = _pin_dimension_identity(s, ev, dim)
        scores.append(_apply_clamps(s, ev))

    return scores


def _score_batched(
    dims_by_id: dict[str, dict[str, Any]],
    evidence_list: list[dict[str, Any]],
    backend: str | None,
) -> list[dict[str, Any]]:
    dim_blocks = []
    for ev in evidence_list:
        dim = dims_by_id.get(ev["dim_id"], {})
        citations_text = "\n".join(
            f"  - \"{c.get('quote', '')}\" [{c.get('location', '')}] ({c.get('source_class','other')})"
            for c in ev.get("citations", [])
        ) or "  (none)"
        dim_blocks.append(
            f'<DIM id="{ev["dim_id"]}">\n'
            f'NAME: {dim.get("name", ev.get("dim_name", ev["dim_id"]))}\n'
            f'DESCRIPTION: {dim.get("description", "")}\n'
            f'WEIGHT: {dim.get("weight", 1)} (1-3, higher = more important)\n'
            f'EVIDENCE_SUMMARY: {ev.get("evidence_summary", "(not available)")}\n'
            f'CONFIDENCE: {ev.get("confidence", "low")}\n'
            f'HEDGE: {ev.get("hedge", False)}\n'
            f'CITATIONS:\n{citations_text}\n'
            f'</DIM>'
        )
    prompt = _BATCHED_SCORE_PROMPT_TEMPLATE.format(dim_blocks="\n".join(dim_blocks))
    if len(prompt) > _BATCH_PROMPT_CEILING_CHARS:
        raise BatchTooLarge(
            f"batched score prompt {len(prompt)} chars exceeds ceiling {_BATCH_PROMPT_CEILING_CHARS}"
        )

    raw = backends.call(prompt, backend=backend)
    expected_ids = {ev["dim_id"] for ev in evidence_list}
    parsed = _extract_json_array(raw, expected_ids)
    by_id = {item["dim_id"]: item for item in parsed if isinstance(item, dict) and "dim_id" in item}
    missing_ids = expected_ids - by_id.keys()
    if missing_ids:
        raise BatchParseError(
            f"batched score response missing dim_ids {sorted(missing_ids)}"
        )

    scores = []
    for ev in evidence_list:
        dim = dims_by_id.get(ev["dim_id"], {})
        s = by_id[ev["dim_id"]]
        # Fill non-identity contract fields from defaults.
        s.setdefault("score_rationale", "")
        s.setdefault("evidence_drove_score", "")
        s.setdefault("hedge_applied", False)
        try:
            s["score"] = _coerce_score(s, ev["dim_id"])
        except ValueError as exc:
            raise BatchParseError(str(exc)) from exc
        s = _pin_dimension_identity(s, ev, dim)
        scores.append(_apply_clamps(s, ev))
    return scores


def _only_self_marketing(ev: dict[str, Any]) -> bool:
    """True iff every citation is readme/doc (no code/test/config evidence)."""
    cits = ev.get("citations") or []
    if not cits:
        return False
    ground_truth = {"code", "test", "config"}
    for c in cits:
        sc = c.get("source_class", "other") if isinstance(c, dict) else "other"
        if sc in ground_truth:
            return False
    # All are readme / doc / other
    return any(isinstance(c, dict) and c.get("source_class") in ("readme", "doc") for c in cits)


def _citation_source_weight(ev: dict[str, Any]) -> float:
    """Weighted average of source-class weights across the evidence's citations.
    1.0 = all ground-truth (code/test); 0.7 = all README/doc; 0.0 = no citations."""
    cits = ev.get("citations") or []
    if not cits:
        return 0.0
    weights = [
        SOURCE_CLASS_WEIGHT.get(c.get("source_class", "other"), 0.8)
        for c in cits
        if isinstance(c, dict)
    ]
    return round(sum(weights) / len(weights), 2) if weights else 0.0


def compute_aggregate(
    rubric: dict[str, Any],
    scores: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute weighted aggregate score and identify hedge dimensions.

    Robustness: stage-3 LLMs sometimes drift and return the dim NAME in the
    `dim_id` field instead of the synthesized `dim_N` id (caught 2026-04-26
    when an aggregate=0.0 was reported despite per-dim scores in [2,6]).
    Falls back to dim-name lookup, then case+whitespace-normalized lookup.
    Mismatches are surfaced via `id_mismatch_count` in the return dict
    rather than silently zeroing the aggregate.
    """
    scores_by_id = {s["dim_id"]: s for s in scores if s.get("dim_id")}
    scores_by_name = {s["dim_name"]: s for s in scores if s.get("dim_name")}
    scores_by_norm_name = {
        s.get("dim_name", "").lower().replace(" ", "_").replace("-", "_"): s
        for s in scores if s.get("dim_name")
    }

    total_weight = 0
    weighted_sum = 0.0
    hedge_dims = []
    dim_summaries = []
    id_mismatch_count = 0

    for dim in rubric["dimensions"]:
        dim_id = dim["id"]
        dim_name = dim.get("name", "")
        weight = dim.get("weight", 1)
        s = scores_by_id.get(dim_id)
        if s is None:
            # Fallback 1: LLM put dim NAME in dim_id field
            s = scores_by_id.get(dim_name) or scores_by_name.get(dim_name)
            if s is not None:
                id_mismatch_count += 1
        if s is None:
            # Fallback 2: case + whitespace + dash normalization
            norm = dim_name.lower().replace(" ", "_").replace("-", "_")
            s = scores_by_id.get(norm) or scores_by_norm_name.get(norm)
            if s is not None:
                id_mismatch_count += 1
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
        "id_mismatch_count": id_mismatch_count,
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
    result = _extract_json(raw)

    # Clamp score to valid range
    result["score"] = max(0, min(10, _coerce_score(result, ev["dim_id"])))
    return result


def _coerce_score(result: Any, dim_id: str) -> int:
    try:
        return int(result["score"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid or missing score in response for dimension {dim_id!r}"
        ) from exc


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
