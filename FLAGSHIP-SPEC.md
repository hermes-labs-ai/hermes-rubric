# hermes-rubric — Flagship Product Spec & Roadmap

> Series A flagship spec for hermes-rubric. Evaluated against five
> external criteria: real-world achievability, innovation, alignment
> with Hermes Labs thesis, publication readiness, and audit-readiness
> for funder + buyer scrutiny.
>
> Scope class: sweep-plan (multi-quarter roadmap to flagship status).

## What it is, in one sentence

**hermes-rubric is the evidence-first scoring layer for any AI system that scores anything** — papers, PRs, leads, candidates, tickets, model outputs — and the only LLM-judge tool that produces an auditable `(rubric, evidence, score)` triple regulators and buyers can defend.

## Why it's the flagship

1. **Regulatory.** EU AI Act Art. 14 + Annex III + ISO 42001 §8.7 require auditable evaluation. "Rate 0-10" doesn't qualify; hermes-rubric does.
2. **Buyer.** Every AI procurement asks "how do you evaluate outputs?" — first answer that isn't "we trust the model."
3. **Flywheel.** Hermes Labs gates every artifact through it (2026-04-25 convention). Each use = calibration data + credibility moat.

## Differentiation (auditable wedge)

vs **OpenAI/Anthropic evals** (rate 0-10 + offline harness): adds per-dim evidence-gate + receipt. vs **Inspect** (UK AISI; task-specific solvers): target-type-agnostic, no task scaffolding. vs **Promptfoo** (test-grid asserts): hedged structured scores, not pass/fail. vs **Patronus / Arize** (LLM observability): OSS, local-deploy, audit chain not vendor-locked. vs **DeepEval / Braintrust** (unit-style asserts): hedge-on-thin + 0-10 dims. vs **LangChain LLMonitor** + **MLflow eval**: synthesized rubric + LLM-readable evidence chain. vs **G-Eval / Prometheus** (academic rubric-LLM-judge): pre-registered cross-backend κ, not single-backend self-correlation.

**Wedge in one sentence:** the only scoring tool that produces a `(rubric, evidence, score, receipt)` quadruple a regulator can verify offline.

## Input / output contract (v1.0)

**Inputs:** `--intent` (string) + `--context` (file/glob) + `--target` (file/dir) + `--target-type` (label) + `--backend` (auto/claude-cli/ollama-local/dashscope-qwen).

**Output:** JSON with 6 fields — `rubric`, `per_dim_scores`, `evidence_citations`, `aggregate`, `hedge_dims`, `receipt` (prompt sha256 + backend + timestamp + git SHA). Non-zero exit on stage failure; no partial output.

**Anti-fabrication (mechanically enforced):** Stage 2 evidence must precede Stage 3 score — order enforced in `cli.py`, verified by `tests/test_adversarial_fabrication.py`. Empty-citation dims auto-flagged `hedge=true` and capped at score=3 (`score.py` cap logic). N=130 batched-mode equivalence proven (`aff93b3`).

## v1.0 non-goals (Does-not)

No generic "rate 0-10" without rubric. No score outside 0-10 scale. No closed-source rubrics (G2 registry is open + signed). Not a human-replacement (augmentation; human sign-off in regulated workflows). No real-time streaming (batch-only v1). No non-English (English-only v1). No customer-data egress without explicit opt-in. No env-var backend override (CLI flag only; protects audit chain). No bypass mode that skips evidence collection.

## Real-world achievability — what's already built

v0.1.x on PyPI: 3-stage pipeline, CLI, 6 test files / 34 tests, 5 backends (claude-cli + `--bare`, ollama-local, dashscope-qwen-plus/turbo). Calibration set + 24-mode failure taxonomy + meta-rubric. Reproducibility receipt (prompt sha256 + backend + timestamp). 4-paper applied run + N=130 batched-mode equivalence (`aff93b3`). Hermes Seal manifest staged; CI green; ruff clean. Wrapper `~/bin/hermes-rubric-blinded` (BLIND + scope-class + intent-debias).

## What's missing for v1.0 (flagship-grade)

| # | Gap | Effort |
|---|---|---|
| G1 | Cohen's κ across backends | 2-3d |
| G2 | Rubric registry: versioned, signed, reusable | 1wk |
| G3 | Web UI: target+intent → rubric+evidence+score | 2wk |
| G4 | Audit export: signed PDF + JSON bundle | 1wk |
| G5 | API server `hermes-rubric serve` | 1wk |
| G6 | EU AI Act / ISO 42001 clause-mapping | 3-5d |
| G7 | Native `--scope-class` + `--intent-debias` flags | 1-2d |
| G8 | `--target-window-bytes` flag + warning | 0.5d |
| G9 | Cross-backend reliability study, published | 2wk + $50 |
| G10 | 1-2 design-partner pilots | 4-8wk |

Total to v1.0 flagship: **~6-8 weeks of focused work**, $50-200 in experiment cost, plus design-partner sales cycle in parallel.

## Innovation

Novelty is the *forced structure*: (1) synthesized domain rubric (LLM as rubric-author + scorer in series, adversarially separated); (2) mechanical evidence-gate before score; (3) first-class hedging on thin evidence; (4) reproducibility receipt; (5) scope-aware synthesis (G7). Publishable claim: *evidence-first structured scoring with synthesized rubrics produces lower-variance, more-defensible scores than direct LLM rating, measurable via Cohen's κ across runs.*

**Pre-registered falsification (G9 numeric kill-conditions):** ship-claim is rejected if (a) cross-backend κ < 0.6 (substantial agreement floor) OR (b) `evidence-stage-removed` ablation arm shows no variance increase (≥30% σ↑ vs full pipeline) OR (c) hermes-rubric mean κ ≤ direct-LLM-rate κ on matched targets. The ablation isolates evidence-collection as the *causal* driver, not just a correlated step. Confounds named: prompt quality (held constant via synthesized-rubric-only prompts), model size (cross-tier sweep planned: Haiku + qwen-plus + qwen-max + Opus), target cherry-picking (4-paper applied corpus + adversarial pair pre-registered).

## Alignment with Hermes Labs thesis

Keystone of the Hermes Labs audit stack: **lintlang / scaffold-lint** static-check scaffolds → hermes-rubric scores them; **hermes-seal** signs bundles → hermes-rubric scores sealed evidence; **hermes-bundle** produces EU AI Act / ISO 42001 packets → hermes-rubric scores gaps; **hermes-blind** wraps every rubric call (convention); **driftwatch / te-drift-detector** measure drift → hermes-rubric scores severity.

Each Hermes tool either *produces* something hermes-rubric scores or *consumes* its scores. Series-A pitch line: **"we own the scoring layer of the AI audit stack."**

## Roadmap (12 weeks to flagship)

- **P1 wks 1-2** — G7 native flags + G8 window warning + G1 κ metric → v0.2
- **P2 wks 3-4** — G4 audit export + G6 EU AI Act / ISO 42001 mapping → v0.3
- **P3 wks 5-6** — G9 reliability study executed; arXiv preprint draft
- **P4 wks 7-9** — G3 Web UI + G5 API server + G2 rubric registry → v0.4-0.5
- **P5 wks 4-12 (parallel)** — G10 design-partner pilots (1 medical + 1 enterprise PR)
- **P6 wk 12** — all Gs closed; v1.0 launch (HN + preprint + demo video + customer quote)

## Auditability readiness (recursive proof)

hermes-rubric must pass its own audit. The recursive sanity check is `SCOPE_CLASS=sweep-plan hermes-rubric-blinded --target FLAGSHIP-SPEC.md`; result published as `audit-runs/flagship-spec-self-audit.md` in the repo, sealed in the manifest. **That self-audit is the v1 demo.** If the tool can't audit its own spec, it can't audit yours.

Buyer-scrutiny checklist (load-bearing items called out):
- ✅ Open source, MIT, on PyPI; Hermes Seal manifest staged
- ✅ Reproducibility receipt per scoring run (prompt sha256 + backend + timestamp)
- ✅ No vendor lock-in: 5 backends incl. local Ollama (data never leaves machine)
- ✅ Adversarial fabrication test enforces evidence-gate mechanically
- 🟡 **G4 audit export** (signed PDF + JSON bundle) — *load-bearing for buyer scrutiny*, in P2
- 🟡 **G6 EU AI Act / ISO 42001 clause-mapping** — *load-bearing for funder scrutiny*, in P2
- 🟡 **G9 cross-backend κ reliability study** — *load-bearing for methodology defense*, in P3
- 🟡 G10 design-partner pilot (1-2 customers) — in P5 parallel

## Risks (mitigated)

R1 LLM-judge critique→G9 κ + bare-mode. R2 OSS-vs-revenue→free CLI/API; revenue from registry + audit-as-a-service. R3 Standards uncertainty→ship G6 early. R4 Solo bandwidth→scaffold-corpus reuse + parallel pilots. Publication: arXiv off G9 + Show HN demo of recursive self-audit; non-blocking.
