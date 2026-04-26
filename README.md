# hermes-rubric

**Language scaffolds hold state. LLM scores don't — unless you force them to.**

[![PyPI](https://img.shields.io/pypi/v/hermes-rubric.svg)](https://pypi.org/project/hermes-rubric/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-rubric.svg)](https://pypi.org/project/hermes-rubric/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml)
[![Hermes Seal](https://img.shields.io/badge/hermes--seal-verified-blue)](https://github.com/hermes-labs-ai/hermes-rubric)

The LPCI thesis (proved March 2026) showed that a stateless LLM maintains coherent state through language scaffolding alone — the artifact is the memory, not the model. hermes-rubric applies the same insight to scoring: the rubric and evidence citations are the audit trail. The number at the end means something only because the scaffold forced evidence collection before scoring.

Without a scaffold, LLMs reward fluency. Well-written garbage outscores substantive-but-rough work. Re-run and the number shifts. No way to argue with it.

hermes-rubric fixes that. One-line value prop: **evidence-first structured scoring that synthesizes a domain rubric, collects citations per dimension, then scores against evidence — not surface quality**.

**30-second pitch:** LLM scoring is fluency-biased by default. hermes-rubric imposes a three-stage scaffold (rubric synthesis → evidence collection → evidence-only scoring) that breaks the bias. Each score has a citation trail. Hedge flags mark thin-evidence dimensions. Same input → scores within ±1. The result is a score you can reproduce and defend.

**5-minute install:**
```bash
pip install hermes-rubric
hermes-rubric \
    --intent "rate this as a publication-ready research artifact" \
    --context paper.md \
    --target paper.md \
    --out result.json
# aggregate, hedge_dims, evidence_citations, receipt — all in result.json
```

**Class-aware mode (v0.2)** — when you score the same kind of artifact repeatedly, use a class template to skip Stage-1 LLM synthesis entirely. The dim set is fixed across runs, scores are diff-able, and class-specific slop signatures + voice priors are pre-injected:

```bash
hermes-rubric --artifact-class social-post --target post.md --out result.json
# Available classes: social-post, show-hn-post, linkedin-post, outreach-email
```

Each class template lives at `hermes_rubric/classes/<name>.yaml` — open them to see exactly which dims, weights, and slop signatures are applied. Custom classes can be added by dropping a YAML in the same directory.

## Pain

- You asked a model to score a paper / PR / email / lead and the score felt high. Later you read the thing and it wasn't that good.
- The model rewards fluency — well-written garbage outscores substantive-but-rough work.
- Re-running the same input gives you 7.2, then 8.4, then 6.9. No audit trail. No way to argue with it.
- You want to calibrate against a style guide or a rubric, but the model ignores your context and defaults to generic "academic quality" vibes.
- You need to justify the score to someone else and all you have is a number.

## How it's different

Most "rate this X" prompts hallucinate — the model generates a confident score grounded in surface signals (fluency, length, vocabulary) instead of evidence. hermes-rubric forces a three-stage path before any number is produced:

1. **Synthesize a rubric** from your intent, context, and target type. Domain-specific, not a generic template.
2. **Collect evidence** per dimension. Citation required (`file:line`, quoted passage, or named artifact). Dimensions without evidence are explicitly hedged.
3. **Score against the rubric and evidence only.** Fabricated claims can't outscore cited ones — enforced by adversarial test.

## Install

```bash
pip install hermes-rubric
```

Python 3.10+. No API key required — works with Claude Code (`claude` CLI) or a local Ollama model.

## Quick start

```bash
hermes-rubric \
    --intent "rate this as a publication-ready research artifact" \
    --context STYLE-GUIDE.md \
    --target paper.md \
    --out result.json
```

Output:

```json
{
  "rubric": {"dimensions": [{"id": "claim_density", "weight": 3}, ...]},
  "evidence_citations": [
    {"dim_id": "claim_density", "citation": "paper.md:42", "quote": "..."}
  ],
  "per_dim_scores": [{"dim_id": "claim_density", "score": 8, "rationale": "..."}, ...],
  "aggregate": 8.7,
  "hedge_dims": ["Reproducibility"],
  "hedge_note": "1 dimension had thin evidence — score less reliable: Reproducibility",
  "receipt": {"backend": "claude-cli", "timestamp_utc": "...", "input_hashes": {...}}
}
```

## What the output means

- **`aggregate`** — weighted score (0-10). Signal, not verdict.
- **`hedge_dims`** — dimensions where evidence was thin. Scores in these dims are clamped to [3,7]. The more hedged dimensions, the less you should trust the aggregate.
- **`evidence_citations`** — every score ties back to a quoted passage or file:line. This is the audit trail.
- **`receipt`** — same inputs + same backend should produce scores within ±1 across runs.

## Backends

Auto-detected in priority order:

1. **`claude-cli`** — `claude --print` subprocess. Highest consistency. Requires Claude Code installed.
2. **`ollama-local`** — local Ollama inference. Zero cost, works offline. Requires `qwen3.5:9b` or similar pulled.

Force a backend:

```bash
hermes-rubric --backend ollama-local ...
```

## Library usage

```python
from hermes_rubric import synthesize_rubric, collect_evidence, score_all, compute_aggregate

rubric = synthesize_rubric(intent="...", context_text="...", target_type="paper")
evidence = collect_evidence(rubric, target_text="...")
scores = score_all(rubric, evidence, target_text="...")
result = compute_aggregate(rubric, scores)
```

## When to use it

- You're scoring artifacts where fluency-vs-substance divergence matters (papers, proposals, PRs, cold emails, lead dossiers).
- You need an audit trail — "the model said 8.7" isn't enough, you need to know *why*.
- You're calibrating against a specific style guide or rubric and generic "quality vibes" won't do.
- You want the same input to produce a score you can reproduce and defend.

## When not to use it

- Binary pass/fail gates — use a deterministic linter instead.
- Single-sentence inputs — there's no evidence surface for the rubric to cite.
- Scoring at high volume where cost matters more than fidelity — use a cheaper heuristic.
- Adversarial scoring where the author controls both the artifact and the rubric synthesis.

## Calibration

- **`calibration/dataset.jsonl`** — 15 labeled cases across 5 domains (paper-quality, tool-fit, deploy-readiness, email-quality, lead-score).
- **`calibration/META-RUBRIC.md`** — the rubric for evaluating rubric generators. 7 dimensions, each motivated by a specific LLM failure mode.
- **`calibration/failure-mode-taxonomy.md`** — 24 failure modes mined from the Hermes Labs research corpus (1,789+ experiments).

## Applied example

**`applied/papers-20260423.md`** — four papers scored on publication-readiness:

| Paper | Aggregate |
|---|---|
| cogito-ergo LongMemEval | 9.1 |
| LangQuant LPCI | 8.7 |
| Taxonomy of Epistemic Failure Modes | 6.9 |
| Asymmetric Burden of Proof | 6.5 |

Each score has a full rubric + citations + per-dimension rationale in the file.

## Running the tests

```bash
git clone https://github.com/hermes-labs-ai/hermes-rubric
cd hermes-rubric
pip install -e ".[dev]"
pytest
```

14 tests, including 2 adversarial:

- `test_fluency_does_not_inflate_evidence_score` — a fluent rewrite of weak evidence must not outscore a substantive-but-rough version by more than 1 point.
- `test_fabricated_claim_does_not_outscore_evidenced_claim` — README claims without supporting evidence are capped at ≤3.

## License

MIT — see [LICENSE](LICENSE).

---

## About Hermes Labs

[Hermes Labs](https://hermes-labs.ai) builds AI audit infrastructure for enterprise AI systems — EU AI Act readiness, ISO 42001 evidence bundles, continuous compliance monitoring, agent-level risk testing. We work with teams shipping AI into regulated environments.

**Our OSS philosophy — read this if you're deciding whether to depend on us:**

- **Everything we release is free, forever.** MIT or Apache-2.0. No "open core," no SaaS tier upsell, no paid version with the features you actually need. You can run this repo commercially, without talking to us.
- **We open-source our own infrastructure.** The tools we release are what Hermes Labs uses internally — we don't publish demo code, we publish production code.
- **We sell audit work, not licenses.** If you want an ANNEX-IV pack, an ISO 42001 evidence bundle, gap analysis against the EU AI Act, or agent-level red-teaming delivered as a report, that's at [hermes-labs.ai](https://hermes-labs.ai). If you just want the code to run it yourself, it's right here.

**The Hermes Labs OSS audit stack** (public, production-grade, no SaaS):

**Static audit** (before deployment)
- [**lintlang**](https://github.com/hermes-labs-ai/lintlang) — Static linter for AI agent configs, tool descriptions, system prompts. `pip install lintlang`
- [**scaffold-lint**](https://github.com/hermes-labs-ai/scaffold-lint) — Static linter for LLM prompt scaffolds. `pip install scaffold-lint`
- [**rule-audit**](https://github.com/hermes-labs-ai/rule-audit) — Static prompt audit — contradictions, coverage gaps, priority ambiguities
- [**intent-verify**](https://github.com/hermes-labs-ai/intent-verify) — Repo intent verification + spec-drift checks
- [**repo-audit**](https://github.com/hermes-labs-ai/repo-audit) — Multi-signal repo readiness check

**Runtime observability** (while the agent runs)
- [**little-canary**](https://github.com/hermes-labs-ai/little-canary) — Prompt injection detection via sacrificial canary-model probes
- [**suy-sideguy**](https://github.com/hermes-labs-ai/suy-sideguy) — Runtime policy guard — user-space enforcement + forensic reports
- [**colony-probe**](https://github.com/hermes-labs-ai/colony-probe) — Prompt confidentiality audit — detects system-prompt reconstruction

**Scoring & regression** (to prove what changed)
- [**hermes-rubric**](https://github.com/hermes-labs-ai/hermes-rubric) — Evidence-first structured scoring (this tool). `pip install hermes-rubric`
- [**hermes-jailbench**](https://github.com/hermes-labs-ai/hermes-jailbench) — Jailbreak regression benchmark. `pip install hermes-jailbench`
- [**agent-convergence-scorer**](https://github.com/hermes-labs-ai/agent-convergence-scorer) — Score how similar N agent outputs are. `pip install agent-convergence-scorer`

**Supporting infra**
- [**claude-router**](https://github.com/hermes-labs-ai/claude-router) · [**zer0dex**](https://github.com/hermes-labs-ai/zer0dex) · [**forgetted**](https://github.com/hermes-labs-ai/forgetted) · [**quick-gate-python**](https://github.com/hermes-labs-ai/quick-gate-python) · [**quick-gate-js**](https://github.com/hermes-labs-ai/quick-gate-js) · [**hermes-seal**](https://github.com/hermes-labs-ai/hermes-seal)

Natural pairing: `scaffold-lint` catches *how much* scaffolding you have. `lintlang` catches *how well-structured* it is. `rule-audit` catches *what the rules contradict*. `hermes-rubric` scores the thing the agent finally produced — with citations.

---

Built by [Hermes Labs](https://hermes-labs.ai) · [@roli-lpci](https://github.com/roli-lpci)
