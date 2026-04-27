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

Replace `STYLE-GUIDE.md` with any rubric context you have (or omit `--context` — the rubric will be synthesized from `--intent` alone).

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
      "citation": "paper.md:42",
      "quote": "TE≈0 (Markov), measured across 7 models"
    }
  ],
  "per_dim_scores": [
    {"dim_id": "claim_density", "score": 8, "rationale": "3 citations with file:line pointers"},
    {"dim_id": "reproducibility", "score": 4, "rationale": "hedged — no reproduction command found", "hedged": true}
  ],
  "aggregate": 6.5,
  "hedge_dims": ["reproducibility"],
  "hedge_note": "1 dimension had thin evidence — score less reliable: reproducibility",
  "receipt": {
    "backend": "claude-cli",
    "timestamp_utc": "2026-04-26T14:32:00Z",
    "input_hashes": {"target": "sha256:...", "context": "sha256:..."}
  }
}
```

**What to look at first:**

- `hedge_dims` — dimensions where evidence was thin. If a dimension you care about is hedged, that's the signal to act on, not the aggregate.
- `evidence_citations` — every score ties back to a quote or file:line. This is the audit trail.
- `aggregate` — weighted score (0-10). Signal, not verdict.

## Common use cases

**Score a PR against a code-review rubric:**
```bash
hermes-rubric \
    --intent "rate this PR for production-readiness" \
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
    --target paper.md \
    --out result.json
```

## Python library

```python
from hermes_rubric import synthesize_rubric, collect_evidence, score_all, compute_aggregate

rubric = synthesize_rubric(intent="...", context_text="...", target_type="paper")
evidence = collect_evidence(rubric, target_text="...")
scores = score_all(rubric, evidence, target_text="...")
result = compute_aggregate(rubric, scores)

print(result["aggregate"])       # 8.7
print(result["hedge_dims"])      # ["reproducibility"]
print(result["evidence_citations"])  # [{dim_id, citation, quote}, ...]
```

## Calibration dataset

The `calibration/` directory ships with:
- `dataset.jsonl` — 7 labeled cases across paper-quality, tool-fit, and deploy-readiness domains (all targets are publicly available artifacts)
- `META-RUBRIC.md` — the rubric for evaluating rubric generators; 7 dimensions, each motivated by a specific LLM failure mode
- `failure-mode-taxonomy.md` — 24 failure modes mined from 1,976+ experiments
