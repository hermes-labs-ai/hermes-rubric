# Quickstart

Three commands from zero to a scored artifact with an audit trail.

## Step 1: Install

```bash
pip install hermes-rubric
```

## Step 2: Run on any text artifact

```bash
hermes-rubric \
    --intent "rate this as a publication-ready research artifact" \
    --context STYLE-GUIDE.md \
    --target paper.md \
    --out result.json
```

Replace `STYLE-GUIDE.md` with the standards or requirements the rubric should apply. `--context` is required unless you use a bundled `--artifact-class` template.

## Step 3: Read the output

```json
{
  "rubric": {
    "dimensions": [
      {"id": "claim_density", "weight": 3, "description": "Every numeric claim has a source"},
      {"id": "reproducibility", "weight": 2, "description": "Enough to re-run the experiment"}
    ]
  },
  "evidence_citations": [
    {
      "dim_id": "claim_density",
      "evidence_found": true,
      "citations": [
        {
          "quote": "The evaluation includes a reproducible comparison command.",
          "evidence_id": "S1:E1",
          "location": "S1:E1 — Whole document",
          "source_class": "doc"
        }
      ]
    }
  ],
  "per_dim_scores": [
    {"dim_id": "claim_density", "score": 8, "score_rationale": "3 citations with evidence pointers"},
    {"dim_id": "reproducibility", "score": 4, "score_rationale": "hedged — no reproduction command found", "hedge_applied": true}
  ],
  "aggregate": 6.5,
  "hedge_dims": ["reproducibility"],
  "hedge_note": "1 dimension(s) had thin evidence — scores for these are less reliable: Reproducibility",
  "dim_summaries": [
    {"dim_id": "claim_density", "name": "Claim Density", "score": 8, "weight": 3, "hedge": false}
  ],
  "receipt": {
    "tool_version": "hermes-rubric 1.0.2",
    "backend": "claude-cli-contextual",
    "inputs": {"target_hash_sha256": "...", "context_hash_sha256": "..."},
    "pipeline": {"stage_1_rubric_hash_sha256": "..."}
  }
}
```

The output above is truncated to its most useful fields.

**What to look at first:**

- `hedge_dims` — dimensions where evidence was thin. If a dimension you care about is hedged, that's the signal to act on, not the aggregate.
- `evidence_citations` — every score ties back to a quote or file:line. This is the audit trail.
- `aggregate` — weighted score (0-10). Signal, not verdict.

## Common use cases

**Score a PR against a code-review rubric:**
```bash
hermes-rubric \
    --intent "rate this PR for production-readiness" \
    --context CONTRIBUTING.md \
    --target pr-description.md \
    --out pr-score.json
```

**Score a cold email for quality gates:**
```bash
hermes-rubric \
    --intent "rate this cold email for distinctiveness and evidence grounding" \
    --context email-style-guide.md \
    --target draft.md \
    --scope-class gate-plan \
    --out email-score.json
```

**Batch mode (one LLM call per stage, faster):**
```bash
hermes-rubric --batch \
    --intent "rate this for publication-readiness" \
    --context STYLE-GUIDE.md \
    --target paper.md \
    --out result.json
```

## Python library

```python
from hermes_rubric.synthesize import synthesize
from hermes_rubric.evidence import collect_evidence
from hermes_rubric.score import score_dimensions, compute_aggregate

rubric = synthesize(
    intent="...",
    context_summary="...",
    target_type="paper",
    target_excerpt="...",
)
evidence = collect_evidence(
    rubric=rubric,
    target_content="...",
    target_path="paper.md",
)
scores = score_dimensions(rubric=rubric, evidence_list=evidence)
result = compute_aggregate(rubric=rubric, scores=scores)

print(result["aggregate"])       # 8.7
print(result["hedge_dims"])      # ["reproducibility"]
print(evidence)                   # [{dim_id, citations, evidence_summary, ...}, ...]
```

## Calibration dataset

The `calibration/` directory ships with:
- `dataset.jsonl` — 7 labeled cases across paper-quality, tool-fit, and deploy-readiness domains (all targets are publicly available artifacts)
- `META-RUBRIC.md` — the rubric for evaluating rubric generators; 7 dimensions, each motivated by a specific LLM failure mode
- `failure-mode-taxonomy.md` — 24 failure modes mined from 1,976+ experiments
