# hermes-rubric

Evidence-first structured scoring. Three stages before any number is produced.

Most "rate this X" prompts hallucinate. The model generates a confident score grounded in surface signals — fluency, length, vocabulary — not in the actual evidence. hermes-rubric forces a different path:

1. **Synthesize a rubric** from your intent, context, and target type. Not a generic template. A domain-specific evaluation plan.
2. **Collect evidence** per dimension before scoring. Citation required: file:line, quoted passage, or named artifact. Low-confidence dimensions are explicitly hedged.
3. **Score against the rubric and evidence only.** No surface fluency. No vibes. Every score has an audit trail.

## Requirements

No API key required. Works with Claude Code (claude CLI) or Ollama locally.

- Claude Code installed: `claude --print` → automatically used as backend
- Ollama with qwen3.5 model: `ollama pull qwen3.5:9b` → fallback backend

## Install

```bash
pip install -e .
```

## Usage

```bash
hermes-rubric \
    --intent "rate the paper as a publication-ready research artifact" \
    --context path/to/STYLE-GUIDE-v1.md \
    --target path/to/paper.md \
    --out result.json \
    --verbose
```

Output JSON:

```json
{
  "rubric": {"dimensions": [...]},
  "evidence_citations": [...],
  "per_dim_scores": [...],
  "aggregate": 8.7,
  "hedge_dims": ["Reproducibility"],
  "hedge_note": "1 dimension had thin evidence — score less reliable: Reproducibility",
  "receipt": {"backend": "claude-cli", "timestamp_utc": "...", "input_hashes": {...}}
}
```

## What the output means

- `aggregate`: weighted average score (0-10). Use as a signal, not a verdict.
- `hedge_dims`: dimensions where evidence was thin. Scores in these dims are clamped to [3,7]. Trust the overall score less when this list is long.
- `receipt`: reproducibility receipt. Same inputs + same backend should produce scores within ±1 point across runs.

## Backends

Auto-detected in this priority order:

1. `claude-cli` — `claude --print` subprocess. Consistent quality. Requires Claude Code.
2. `ollama-local` — local Ollama inference. Zero cost, works offline. Requires `qwen3.5:14b` or smaller installed.

Force a backend:

```bash
hermes-rubric --backend ollama-local ...
```

## Calibration

`calibration/dataset.jsonl` — 15 cases across 5 domains (paper-quality, tool-fit, deploy-readiness, email-quality, lead-score) with human-labeled reference scores.

`calibration/META-RUBRIC.md` — the rubric for evaluating rubric generators. 7 dimensions, each motivated by specific LLM failure modes documented in `calibration/failure-mode-taxonomy.md`.

`calibration/failure-mode-taxonomy.md` — 24 failure modes mined from the Hermes Labs research corpus (1,789+ experiments).

## Applied example

`applied/papers-20260423.md` — four papers scored on publication-readiness: cogito-ergo LongMemEval (9.1), LangQuant LPCI (8.7), Taxonomy of Epistemic Failure Modes (6.9), Asymmetric Burden of Proof (6.5).

## Test

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

14 tests including 2 adversarial tests. The adversarial tests verify:
- Surface fluency does not inflate scores (fluent version must not outscore evidenced version by >1 point)
- Fabricated README claims with no evidence cap at score ≤3

## Part of the Hermes Labs audit stack

- [lintlang](https://github.com/hermes-labs-ai/lintlang) — static linter for agent code
- [scaffold-lint](https://github.com/hermes-labs-ai/scaffold-lint) — linter for scaffold YAML
- [intent-verify](https://github.com/hermes-labs-ai/intent-verify) — lexical coverage gate for INTENT.md
- [hermes-repo-audit](https://pypi.org/project/hermes-repo-audit/) — multi-signal repo readiness check
- **hermes-rubric** — evidence-first structured scoring (this tool)
