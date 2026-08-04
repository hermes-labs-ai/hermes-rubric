# Architecture

The three-stage scaffold and how the pieces fit.

## Three sequential stages

```
┌─────────────────────┐
│ Stage 1: Synthesize │  intent + context + target_type → rubric
└──────────┬──────────┘
           │ rubric (dim list, weights, voice priors)
           ▼
┌─────────────────────┐
│ Stage 2: Evidence   │  rubric × target → per-dim citations
└──────────┬──────────┘
           │ evidence list (citations or "thin evidence")
           ▼
┌─────────────────────┐
│ Stage 3: Score      │  rubric × evidence → per-dim scores
└──────────┬──────────┘
           │ scores (clamped where evidence thin)
           ▼
┌─────────────────────┐
│ Aggregate + receipt │  scores × weights → final number + audit trail
└─────────────────────┘
```

Each stage is a separate LLM call, with the output of the prior stage as committed context. By Stage 3, the LLM has nowhere to hide weak evidence behind fluency - it scores against a rubric it already committed to and citations it already collected.

## Stage 1: rubric synthesis

Inputs:
- `intent` (one-sentence goal)
- `context` (file with style guide, scope, or domain context)
- `target_type` (label, e.g. `paper`, `tool`, `repo`)
- `target_excerpt` (truncated content from the target)

Output: a rubric with 4-8 dimensions, each with:
- `id` (snake-case identifier)
- `name` (human-readable)
- `description` (what the dim measures)
- `weight` (1-3, integer)
- `voice_priors` (optional: tone signals to weight)

Reproducibility: NOT deterministic across runs. Same intent + context can produce slightly different dim sets. Use `--artifact-class <name>` to keep the dimension set fixed across runs.

Module: `src/hermes_rubric/synthesize.py`

## Stage 2: evidence collection

Inputs:
- The synthesized rubric from Stage 1
- The full target content
- The target path (for `file:line` citations)

Output: one evidence record per dimension with `dim_id`, `evidence_found`, `citations`, `evidence_summary`, confidence, and hedge fields. Each accepted citation carries an exact quote and canonical evidence pointer. Thin evidence sets `hedge: true`.

Reproducibility: this stage is LLM-driven and may return different citations on rerun. The receipt binds the rubric, target, and backend so differences remain inspectable.

Module: `src/hermes_rubric/evidence.py`

## Stage 3: scoring

Inputs:
- The synthesized rubric
- The evidence list

Output: a list of `{dim_id, score, rationale}` records. Score is 0-10 integer.

Caps applied:
- **Hedged dimensions clamp to [3, 7].** Cannot score 8+ or 0-2 with thin evidence.
- **Fabricated claims cap at ≤3.** A score that asserts something not present in the evidence list is rejected.

Module: `src/hermes_rubric/score.py`

## Aggregation + receipt

Inputs:
- The rubric (with weights)
- The scores

Output:
```json
{
  "rubric": {"dimensions": [...]},
  "evidence_citations": [...],
  "per_dim_scores": [...],
  "aggregate": 8.7,
  "max_possible": 10.0,
  "hedge_dims": ["Reproducibility"],
  "hedge_note": "1 dimension(s) had thin evidence — scores for these are less reliable: Reproducibility",
  "dim_summaries": [...],
  "receipt": {
    "tool_version": "hermes-rubric 1.0.2",
    "backend": "claude-cli-contextual",
    "inputs": {"target_hash_sha256": "...", "context_hash_sha256": "..."},
    "pipeline": {"stage_1_rubric_hash_sha256": "..."}
  }
}
```

This output is truncated. The `receipt` is the load-bearing audit trail: it binds input hashes, backend, and rubric hash. It makes reruns comparable; it does not guarantee identical scores.

Module: `src/hermes_rubric/score.py`

## Adversarial gates

Two tests in `tests/test_adversarial.py` enforce the scaffold's contract:

- `test_fluency_does_not_inflate_evidence_score` - a fluent rewrite of weak evidence must not outscore a substantive-but-rough version by more than 1 point
- `test_fabricated_claim_does_not_outscore_evidenced_claim` - claims without supporting evidence are capped at ≤3

Build fails if either gate fails.

## Class-aware mode

`--artifact-class <name>` skips Stage 1 and uses a YAML class template at `hermes_rubric/classes/<name>.yaml`:

```yaml
name: social-post
target_type: post
dimensions:
  - id: hook
    name: Hook
    weight: 3
    description: ...
  - id: payoff
    name: Payoff
    weight: 2
    ...
voice_priors:
  - "lowercase casual"
  - "no marketing adjectives"
slop_signatures:
  - "leverage"
  - "powerful"
  - "comprehensive"
```

Same input + same class = same rubric across runs. Stages 2 and 3 still run normally.

## Why it works

- **Sequential commitment.** Stage 1 commits to a rubric. Stage 2 commits to citations. Stage 3 has to score against both - can't optimize for fluency in isolation.
- **Hedging as a first-class output.** Thin evidence isn't hidden behind a confident number. It's flagged in `hedge_dims` and the aggregate carries that signal.
- **Receipts as the product.** The score is the headline; the audit trail is the differentiator. Receipts make reruns comparable without claiming identical output.

See [`PHILOSOPHY.md`](PHILOSOPHY.md) for the wider Hermes Labs thesis behind this design.
