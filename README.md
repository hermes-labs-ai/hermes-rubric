# hermes-rubric

Score AI artifacts with receipts, not vibes.

[![PyPI](https://img.shields.io/pypi/v/hermes-rubric)](https://pypi.org/project/hermes-rubric/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-rubric)](https://pypi.org/project/hermes-rubric/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml)
[![Hermes Seal](https://img.shields.io/badge/hermes--seal-verified-purple)](https://hermes-labs.ai)

For builders shipping AI artifacts (papers, PRs, prompts, cold emails, lead dossiers) where you need a defensible score with citations, not an unaudited LLM judgment. Built for the case where "the model said 8.7" doesn't survive review.

## Install

```bash
pip install hermes-rubric
```

By default, the CLI auto-detects Claude Code first, then local Ollama; see [Backends](docs/BACKENDS.md) for requirements and alternatives.

## Quick start

```bash
hermes-rubric \
  --intent "rate this paper for publication-readiness" \
  --context STYLE-GUIDE.md \
  --target paper.md \
  --out result.json
```

Truncated output:

```json
{
  "aggregate": 8.7,
  "max_possible": 10.0,
  "hedge_dims": ["Reproducibility"],
  "hedge_note": "1 dimension(s) had thin evidence — scores for these are less reliable: Reproducibility",
  "per_dim_scores": [
    {"dim_id": "claim_density", "score": 8, "score_rationale": "..."}
  ],
  "evidence_citations": [
    {
      "dim_id": "claim_density",
      "evidence_found": true,
      "citations": [
        {
          "quote": "...",
          "evidence_id": "S1:E1",
          "location": "S1:E1 — Whole document",
          "source_class": "doc"
        }
      ]
    }
  ],
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

What the keys mean:

- `aggregate` - weighted score (0-10). Signal, not verdict.
- `hedge_dims` - dimensions where evidence was thin. Scores in these dims clamp to `[3, 7]`. The more hedged dims, the less you should trust the aggregate.
- `evidence_citations` - each score carries quoted evidence, its `evidence_id`, and a runtime-canonicalized location and source class. This is the audit trail.
- `receipt` - records backend, timestamp, and input hashes. The demonstrated agreement is batch-versus-per-dimension scoring on five fixtures; Stage-1 synthesis remains non-deterministic.

## What it does

Ask an LLM to score something. You get `8.4/10`. No audit trail, no idea why, drift on rerun. Fluency outscores substance.

hermes-rubric replaces that with three stages: synthesize a rubric, collect evidence citations, score only against the evidence. Every score ships with a citation list (see the JSON above). Dimensions where evidence is thin get clamped and flagged. Batch and per-dimension scoring agreed within the pre-registered margin on five fixtures; that does not make Stage-1 synthesis deterministic.

## Key features

- **Audit trail per dimension.** Every score ties to quoted evidence with a runtime-canonicalized location. No more headline numbers without backing.
- **Hedge-on-thin-evidence.** Dimensions with weak evidence are clamped to `[3, 7]` and flagged. The model can't bury weak evidence under a confident number.
- **Adversarial gates.** Two tests fail the build if fluency outscores substance, or if fabricated claims outscore evidenced ones.
- **Reproducibility receipts.** Record input hashes, backend, and timestamp. The demonstrated result is batch-versus-per-dimension agreement on five fixtures, not a general rerun guarantee.
- **Class-aware mode.** `--artifact-class social-post` uses a fixed rubric template instead of LLM synthesis, keeping the dimension set stable across runs.
- **7 backends out of the box.** Claude Code CLI, Ollama, DashScope Qwen, Gemini HTTP, OpenAI HTTP, OpenAI SDK, and Google GenAI SDK, plus a plugin entry point for your own.

## Evaluation evidence

The committed [2026-04-25 report](experiments/batch-equiv-2026-04-25/RESULTS.md) documents a bounded batch-versus-per-dimension comparison on five fixtures. Raw run JSON is not included, so this repository does not currently support a from-clone recomputation claim. The test suite also includes two adversarial gates.

## When to use it

- Scoring artifacts where fluency-vs-substance divergence matters: papers, proposals, PRs, cold emails, lead dossiers
- You need an audit trail. "The model said 8.7" isn't enough; you need to know why
- You're calibrating against a specific style guide and generic "quality vibes" won't do
- You need receipts and fixed rubric dimensions to compare and defend repeated scoring runs

## When not to use it

- Binary pass/fail gates (use a deterministic linter)
- Single-sentence inputs (no evidence surface to cite)
- Volume-over-fidelity scoring where cost matters more than rigor
- Adversarial scoring where the author controls both the artifact and the rubric synthesis

## Documentation

- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) - the linguistic-state thesis behind the design
- [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) - Cohen's κ methodology, per-backend breakdown, paired-run details
- [`docs/CLI.md`](docs/CLI.md) - all flags, subcommands, environment variables
- [`docs/BACKENDS.md`](docs/BACKENDS.md) - 7 built-in backends + plugin entry-point protocol
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - three-stage scaffold internals
- [`docs/API.md`](docs/API.md) - Python library reference
- [`AGENTS.md`](AGENTS.md) - integration guide for AI agents and coding assistants
- [`llms.txt`](llms.txt) - LLM-readable project summary
- [`calibration/`](calibration/) - 7 labeled cases, meta-rubric, 24-failure-mode taxonomy
- [`experiments/`](experiments/) - historical evaluation reports and run manifests

## Examples

Three worked examples ship in-repo:

- [`evals/wedge-variance/`](evals/wedge-variance/) - variance comparison: hermes-rubric aggregate vs raw 0-10 LLM rating
- [`applied/papers-20260423.md`](applied/papers-20260423.md) - two published Zenodo papers scored on publication-readiness
- [`calibration/dataset.jsonl`](calibration/dataset.jsonl) - 7 labeled cases used for cross-backend κ measurement

## Library usage

```python
from hermes_rubric.synthesize import synthesize
from hermes_rubric.evidence import collect_evidence
from hermes_rubric.score import score_dimensions, compute_aggregate

rubric = synthesize(intent="...", context_summary="...", target_type="paper", target_excerpt="...")
evidence = collect_evidence(rubric=rubric, target_content="...", target_path="paper.md")
scores = score_dimensions(rubric=rubric, evidence_list=evidence)
result = compute_aggregate(rubric=rubric, scores=scores)
```

Full API reference: [`docs/API.md`](docs/API.md).

## Contributing

```bash
git clone https://github.com/hermes-labs-ai/hermes-rubric && cd hermes-rubric
pip install -e ".[dev]"
pytest
```

The suite includes two adversarial gates and a documentation-consistency gate. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

## Enterprise

For custom AI-reliability engagements, on-prem deployments, or audit-grade evaluation pipelines: roli@hermes-labs.ai · https://lpci.ai

## About

hermes-rubric is part of the Hermes Labs reliability stack for the agent era. Founder: Rolando (Roli) Bosch. See [`ABOUT.md`](ABOUT.md) for the canonical bio and company context. Cite as: Bosch, R. (2026). *Hermes Labs: AI reliability infrastructure for autonomous agents.* https://hermes-labs.ai
