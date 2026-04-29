#!/usr/bin/env python3
"""hermes-meta-rubric: target-type-aware wrapper around hermes-rubric.

Synthesizes scoring policy per (intent, context, target_type) instead of
hardcoding the source-class cap (score.py:106-108) and window-bytes default
(cli.py:48). The wrapper:

1. Selects a policy from a registry keyed on target_type.
2. Invokes the underlying hermes-rubric pipeline with the policy's
   window_bytes, scope_class, intent_debias, batch flags.
3. Re-applies the policy's source_class_caps + hedge_band to per-dim scores
   AFTER the underlying tool runs, overriding the hardcoded cap-at-6 in
   score._apply_clamps.
4. Recomputes the aggregate from the policy-clamped scores.

Naming note: I picked "hermes-meta-rubric" over "hermes-adaptive-rubric"
because the value is the policy meta-layer, not adaptivity per se. The
wrapper does not learn — it dispatches.

CLI:
    python -m meta_tool.hermes_meta_rubric \
        --intent "..." --context PATH --target PATH \
        --target-type preprint-paper [--policy-file PATH] [--out PATH]

Library:
    from meta_tool.hermes_meta_rubric import (
        load_registry, select_policy, run_meta_rubric
    )
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Module-level imports of hermes_rubric internals. Kept lazy in test paths
# via dependency-injection so unit tests can run without a backend.
try:
    from hermes_rubric import backends as _backends
    from hermes_rubric.evidence import collect_evidence, read_context, read_target
    from hermes_rubric.score import compute_aggregate, score_dimensions
    from hermes_rubric.synthesize import synthesize
    from hermes_rubric.receipt import build_receipt
    _HERMES_AVAILABLE = True
except ImportError:  # pragma: no cover — only triggered if package not installed
    _HERMES_AVAILABLE = False


HERE = Path(__file__).parent
DEFAULT_REGISTRY_PATH = HERE / "policy_registry.json"


# ---------------------------------------------------------------------------
# Schema validation (lightweight; we don't pull jsonschema as a hard dep)
# ---------------------------------------------------------------------------

REQUIRED_POLICY_FIELDS = {
    "policy_id",
    "policy_version",
    "target_type_match",
    "source_class_caps",
    "window_bytes",
    "dim_weight_strategy",
    "prompt_template_id",
    "no_evidence_floor",
    "hedge_band",
    "rationale",
    "fallback_policy_id",
}

VALID_SOURCE_CLASSES = {"code", "test", "config", "doc", "readme", "other"}
VALID_WEIGHT_STRATEGIES = {"preserve", "flatten", "amplify-load-bearing"}
VALID_TEMPLATE_IDS = {"default", "prose-target", "code-artifact", "mixed"}


class PolicyError(ValueError):
    """Raised on invalid or unresolvable policy."""


def validate_policy(policy: dict[str, Any]) -> None:
    """Validate a single policy entry. Raises PolicyError on first violation."""
    missing = REQUIRED_POLICY_FIELDS - set(policy.keys())
    if missing:
        raise PolicyError(f"policy missing required fields: {sorted(missing)}")

    if not isinstance(policy["target_type_match"], list) or not policy["target_type_match"]:
        raise PolicyError("target_type_match must be a non-empty list")

    caps = policy["source_class_caps"]
    if not isinstance(caps, dict):
        raise PolicyError("source_class_caps must be an object")
    for k, v in caps.items():
        if k not in VALID_SOURCE_CLASSES:
            raise PolicyError(f"unknown source_class in caps: {k!r}")
        if v is not None and not (isinstance(v, int) and 0 <= v <= 10):
            raise PolicyError(f"cap for {k!r} must be int in [0,10] or null, got {v!r}")

    wb = policy["window_bytes"]
    if not isinstance(wb, int) or wb < 1000 or wb > 500_000:
        raise PolicyError(f"window_bytes must be int in [1000, 500000], got {wb!r}")

    if policy["dim_weight_strategy"] not in VALID_WEIGHT_STRATEGIES:
        raise PolicyError(f"dim_weight_strategy invalid: {policy['dim_weight_strategy']!r}")

    if policy["prompt_template_id"] not in VALID_TEMPLATE_IDS:
        raise PolicyError(f"prompt_template_id invalid: {policy['prompt_template_id']!r}")

    floor = policy["no_evidence_floor"]
    if not isinstance(floor, int) or not (0 <= floor <= 10):
        raise PolicyError(f"no_evidence_floor must be int in [0,10], got {floor!r}")

    band = policy["hedge_band"]
    if not isinstance(band, dict) or "lo" not in band or "hi" not in band:
        raise PolicyError("hedge_band must be {lo, hi}")
    if not (0 <= band["lo"] <= band["hi"] <= 10):
        raise PolicyError(f"hedge_band invalid: {band!r}")


# ---------------------------------------------------------------------------
# Registry loading + policy selection
# ---------------------------------------------------------------------------

def load_registry(registry_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load a policy registry (a list of policies). If no path is provided,
    derives one from the schema's `examples` block — that ships 3 baseline
    policies (preprint-paper-v1, repo-v1, default-v1)."""
    if registry_path is not None:
        p = Path(registry_path).expanduser()
        if not p.is_file():
            raise PolicyError(f"registry file not found: {p}")
        data = json.loads(p.read_text())
        if not isinstance(data, list):
            raise PolicyError("registry must be a JSON array of policies")
        for pol in data:
            validate_policy(pol)
        return data

    # Default: pull baseline policies from the schema's examples block.
    schema_path = HERE / "policy_schema.json"
    schema = json.loads(schema_path.read_text())
    policies = list(schema.get("examples", []))
    for pol in policies:
        validate_policy(pol)
    return policies


def select_policy(target_type: str, registry: list[dict[str, Any]]) -> dict[str, Any]:
    """First-match-wins on target_type_match. Falls through to the
    wildcard '*' policy if no exact match. Raises PolicyError if neither
    exists."""
    target_type = (target_type or "").strip()
    # First pass: exact match
    for pol in registry:
        if target_type in pol["target_type_match"]:
            return pol
    # Second pass: wildcard
    for pol in registry:
        if "*" in pol["target_type_match"]:
            return pol
    raise PolicyError(
        f"no policy matches target_type={target_type!r} and no '*' fallback present"
    )


# ---------------------------------------------------------------------------
# Policy-aware re-clamp (overrides score._apply_clamps cap-at-6)
# ---------------------------------------------------------------------------

def _citation_dominant_class(ev: dict[str, Any]) -> str | None:
    """Return the source_class that dominates this evidence's citations,
    or None if there are no citations. Tie-break: code > test > config >
    doc > readme > other (ground-truth-first)."""
    cits = ev.get("citations") or []
    if not cits:
        return None
    counts: dict[str, int] = {}
    for c in cits:
        if isinstance(c, dict):
            sc = c.get("source_class", "other")
            counts[sc] = counts.get(sc, 0) + 1
    if not counts:
        return None
    priority = ["code", "test", "config", "doc", "readme", "other"]
    max_count = max(counts.values())
    for cls in priority:
        if counts.get(cls, 0) == max_count:
            return cls
    return None


def apply_policy_clamps(
    scores: list[dict[str, Any]],
    evidence_list: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-clamp per-dim scores using the policy's caps + hedge_band.

    This deliberately runs AFTER hermes-rubric's _apply_clamps. The original
    cap-at-6-on-README-only is already applied at this point; we LIFT it
    when the policy says null (no cap) for that source class. Also rewrites
    the rationale string to record the policy decision.
    """
    ev_by_id = {ev["dim_id"]: ev for ev in evidence_list}
    caps = policy["source_class_caps"]
    band = policy["hedge_band"]
    floor = policy["no_evidence_floor"]

    out = []
    for s in scores:
        ev = ev_by_id.get(s.get("dim_id"), {})
        # 1. Re-apply hedge band
        if ev.get("hedge"):
            new = max(band["lo"], min(band["hi"], s["score"]))
            if new != s["score"]:
                s["score"] = new
                s["score_rationale"] = (
                    s.get("score_rationale", "")
                    + f" [meta-rubric: hedge clamped to [{band['lo']},{band['hi']}].]"
                )
        # 2. Re-apply no-evidence floor
        if not ev.get("evidence_found") and s["score"] > floor:
            s["score"] = floor
            s["score_rationale"] += f" [meta-rubric: no-evidence floor={floor}.]"
        # 3. Override cap-at-6 from original tool when policy says null
        dom = _citation_dominant_class(ev)
        if dom is not None:
            cap = caps.get(dom)
            # Detect that the original tool already capped at 6 for self-marketing
            # citations (its hardcoded behavior). If our policy says null, we
            # restore the un-capped score using the un-clamped rationale tag
            # left behind by score._apply_clamps.
            rat = s.get("score_rationale", "")
            if cap is None and "Score capped at 6" in rat:
                # The original tool cannot be inverted (the original score is
                # already lost). Mark the dim as meta-rubric-uncap-eligible
                # and bump the score by 2 (heuristic recovery: original cap
                # was 6, plausible un-capped range 7-8 for prose targets).
                s["score"] = min(10, s["score"] + 2)
                s["score_rationale"] = rat + (
                    f" [meta-rubric: source-class={dom!r} cap lifted by policy "
                    f"{policy['policy_id']!r}; +2 recovery applied.]"
                )
            elif cap is not None and s["score"] > cap:
                s["score"] = cap
                s["score_rationale"] = rat + (
                    f" [meta-rubric: source-class={dom!r} capped at {cap} by policy "
                    f"{policy['policy_id']!r}.]"
                )
        s["meta_policy_id"] = policy["policy_id"]
        s["meta_dominant_source_class"] = dom
        out.append(s)
    return out


def apply_weight_strategy(rubric: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Mutate rubric dim weights per policy's dim_weight_strategy."""
    strat = policy["dim_weight_strategy"]
    if strat == "preserve":
        return rubric
    rubric = json.loads(json.dumps(rubric))  # deep-copy
    for dim in rubric.get("dimensions", []):
        if strat == "flatten":
            dim["weight"] = 1
        elif strat == "amplify-load-bearing":
            if dim.get("load_bearing"):
                dim["weight"] = min(3, dim.get("weight", 1) + 1)
    return rubric


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------

def load_rubric_file(rubric_file_path: str | Path) -> dict[str, Any]:
    """Load a pre-synthesized rubric from a JSON file. Validates the rubric
    structure matches what `synthesize()` would produce (rubric_intent +
    dimensions array with id/name/description/evidence_instructions on each
    dim). Raises ValueError on mismatch.

    Used by `run_meta_rubric(rubric_file=...)` to skip the LLM-synthesis stage
    entirely. The motivating use-case is rubric-equivalence experiments where
    the same rubric must be re-applied across many runs without LLM variance,
    and Mission-C-style validation harnesses where rubrics are sealed inputs
    rather than per-run outputs.
    """
    p = Path(rubric_file_path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"rubric file not found: {p}")
    rubric = json.loads(p.read_text())
    # Reuse synthesize._validate_rubric for shape parity
    from hermes_rubric.synthesize import _validate_rubric
    _validate_rubric(rubric)
    return rubric


def run_meta_rubric(
    intent: str,
    context_path: str,
    target_path: str,
    target_type: str,
    registry: list[dict[str, Any]] | None = None,
    backend: str | None = None,
    rubric_file: str | Path | None = None,
) -> dict[str, Any]:
    """Run the meta-rubric end-to-end. Returns a dict with the same shape as
    hermes-rubric output, plus a `meta_policy` block recording which policy
    was applied.

    If ``rubric_file`` is provided, the synthesis stage is skipped and the
    rubric is loaded from disk. The rest of the pipeline (collect_evidence,
    score, apply_policy_clamps) runs unchanged. The receipt records the
    rubric source as ``"file:<path>"`` so downstream auditors can tell a
    skip-synthesis run from a fresh-synthesis run.
    """
    if not _HERMES_AVAILABLE:
        raise RuntimeError("hermes_rubric package not importable; cannot run pipeline")

    if registry is None:
        registry = load_registry()
    policy = select_policy(target_type, registry)

    # Resolve backend
    backend = backend or _backends.detect()

    # Read inputs with policy-driven window
    target_content, resolved_target = read_target(
        target_path, window_bytes=policy["window_bytes"]
    )
    context_content = read_context(
        context_path, window_bytes=policy["window_bytes"]
    )

    # Stage 1: synthesize rubric (or load from file)
    if rubric_file is not None:
        rubric = load_rubric_file(rubric_file)
        rubric_source = f"file:{Path(rubric_file).expanduser()}"
    else:
        rubric = synthesize(
            intent=intent,
            context_summary=context_content,
            target_type=target_type,
            backend=backend,
            scope_class=policy.get("scope_class"),
            intent_debias=bool(policy.get("intent_debias", False)),
            target_excerpt=target_content,
        )
        rubric_source = "synthesized"
    rubric = apply_weight_strategy(rubric, policy)

    # Stage 2: collect evidence
    evidence_list = collect_evidence(
        rubric=rubric,
        target_content=target_content,
        target_path=resolved_target,
        backend=backend,
        batch=bool(policy.get("batch", False)),
    )

    # Stage 3: score (with original clamps)
    scores = score_dimensions(
        rubric=rubric, evidence_list=evidence_list,
        backend=backend, batch=bool(policy.get("batch", False)),
    )

    # Stage 4: re-clamp per policy
    scores = apply_policy_clamps(scores, evidence_list, policy)

    aggregate_data = compute_aggregate(rubric=rubric, scores=scores)

    receipt = build_receipt(
        intent=intent, context_path=context_path, target_path=target_path,
        backend=f"{backend}+meta-rubric:{policy['policy_id']}",
        rubric=rubric, evidence_list=evidence_list, scores=scores,
        target_content=target_content, context_content=context_content,
    )

    return {
        "rubric": rubric,
        "evidence_citations": evidence_list,
        "per_dim_scores": scores,
        "aggregate": aggregate_data["aggregate"],
        "max_possible": 10.0,
        "hedge_dims": aggregate_data["hedge_dims"],
        "hedge_note": aggregate_data["hedge_note"],
        "dim_summaries": aggregate_data["dim_summaries"],
        "receipt": receipt,
        "meta_policy": {
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "window_bytes": policy["window_bytes"],
            "source_class_caps": policy["source_class_caps"],
            "rationale": policy["rationale"],
            "rubric_source": rubric_source,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hermes-meta-rubric",
        description=(
            "Target-type-aware wrapper around hermes-rubric. Selects scoring "
            "policy from a registry keyed on --target-type, then invokes the "
            "underlying pipeline with policy-driven caps + window."
        ),
    )
    parser.add_argument("--intent", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--target-type", required=True)
    parser.add_argument("--policy-file", default=None,
                        help="Path to a custom policy registry JSON. Default: schema examples.")
    parser.add_argument("--rubric-file", default=None,
                        help="Path to a pre-synthesized rubric JSON. When provided, "
                             "skips the LLM synthesis stage and uses this rubric verbatim. "
                             "Used for rubric-equivalence experiments and sealed-rubric reuse.")
    parser.add_argument("--out", default=None, help="Output JSON. Default: stdout.")
    parser.add_argument("--backend", default=None)
    args = parser.parse_args(argv)

    registry = load_registry(args.policy_file)
    result = run_meta_rubric(
        intent=args.intent,
        context_path=args.context,
        target_path=args.target,
        target_type=args.target_type,
        registry=registry,
        backend=args.backend,
        rubric_file=args.rubric_file,
    )
    output_json = json.dumps(result, indent=2)
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_json)
        print(f"wrote {out_path}", file=sys.stderr)
    else:
        print(output_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
