# hermes-rubric — Eval Coverage Audit

> What evals would make hermes-rubric provably valuable to OSS users,
> Series A funders, paper reviewers, and enterprise buyers — and what
> we already have. MVP gap-fill identified for tonight's session.
>
> Scope class: sweep-plan (audit-of-evals, identifying gaps).

## Audiences and what convinces each

| Audience | Convincing eval | We have? |
|---|---|---|
| OSS users | Tests green, install works, quickstart produces sensible output on a real domain | ✅ 76 tests, PyPI, applied/papers run |
| Series A funders | Cross-backend reliability (Cohen's κ ≥ 0.6); demonstrably-lower-variance vs raw LLM rating | ⚠ κ tool shipped (G1); reliability *study* (G9) not yet executed; variance-vs-raw comparison missing |
| Paper reviewers | Pre-registered methodology, calibration against ground truth, comparison vs baselines (G-Eval, Prometheus, raw LLM rating), effect size + CIs | ❌ all four missing in measured form; FLAGSHIP-SPEC drafts the study but no data |
| Enterprise buyers | Reproducible, multi-backend, audit trail (rubric+evidence+score+receipt) defensible offline, EU AI Act / ISO 42001 mapping | ⚠ multi-backend ✅; receipt ✅; clause-mapping (G6) not yet written |

## What we already have (file-at-path verifiable)

- **Mechanical tests:** 76 passing, ~69 test functions, ruff clean
- **N=130 batched-mode equivalence** on Qwen + Gemini (parallel session): aggregate Δ within ±1.0 score-points; 2.9-4.9× speedup at no quality cost; logged at `~/Documents/projects/research-corpus/agent-infra/raw/2026-04-25-hermes-rubric-batch-equivalence.md`
- **5 self-rubric audits** under `rubric-runs/` (5.4-5.7/10 across phase1-iters; 5.5/10 adversarial; 4.6→5.7→6.2/10 on this session's FLAGSHIP-SPEC iter chain)
- **24-mode failure taxonomy** at `calibration/failure-mode-taxonomy.md`
- **Meta-rubric** at `calibration/META-RUBRIC.md`
- **4-paper applied run** at `applied/papers-20260423.md` (Asymmetric Burden, Epistemic Taxonomy, LangQuant LPCI, cogito LongMemEval)
- **Cohen's κ subcommand** (G1) shipped tonight, regression-tested
- **3 native scope classes** in cross-tool wrapper (`gate-plan`, `sweep-plan`, `results-bundle`); 3 added late tonight (`process-rubric`, `corpus-record`, `session-quality-eval`)
- **Reproducibility receipt** with prompt sha256 + backend + timestamp + git SHA
- **FLAGSHIP-SPEC** with 12-week roadmap; G1+G7+G8 shipped, G2-G6+G9+G10 open

## Gaps that MATTER for "showing it works" (ordered by leverage × cheapness)

### Gap 1 — Variance vs raw LLM rating (the wedge claim)
- **Claim:** "evidence-first structured scoring produces lower variance than direct LLM rating"
- **Status:** untested directly. The N=130 batch-equivalence proves internal consistency BETWEEN MODES, not vs raw LLM rating.
- **MVP eval:** same target × same backend × n=10 with hermes-rubric vs n=10 with `claude --print "rate this 0-10"`. Compute σ for each. Report ratio.
- **Cost:** ~20 min wall + $0 marginal via Haiku
- **What it shows:** the wedge claim is real (or isn't — null result acceptable)

### Gap 2 — Confabulated-input adversarial test
- **Claim:** "fabricated claims can't outscore cited ones"
- **Status:** there's an adversarial test in the test suite (mentioned in FLAGSHIP-SPEC's anti-fabrication contract); coverage details unclear.
- **MVP eval:** craft a target with known fabrications + ground-truth labels, run hermes-rubric, verify fabricated dims are auto-flagged `hedge=true` and capped at score=3.
- **Cost:** ~15 min
- **What it shows:** the mechanical evidence-gate works as advertised

### Gap 3 — Effect-size table on existing rubric-runs
- **Claim:** "audit trail produces N-stable scores"
- **Status:** 5+ self-rubric runs exist under `rubric-runs/`. σ across runs not yet aggregated.
- **MVP eval:** read all rubric-runs JSON, group by (intent, target), compute σ on aggregate, report effect-size table.
- **Cost:** ~10 min, all data on disk
- **What it shows:** how stable are scores across re-runs of the same target? The N-test of repeatability.

### Gap 4 — Calibration vs ground-truth (deferred — needs data)
- **Claim:** "hermes-rubric scores agree with human raters"
- **Status:** no human-rated calibration dataset exists for the in-house corpus
- **MVP eval:** would need 1-2 hours of human rating + a comparison script. Not cheap-tonight.
- **Disposition:** defer to G9 (cross-backend κ study) where consensus-of-multiple-LLMs is the proxy ground truth. Honest framing: until human-rated data exists, calibration is internal-consistency only.

### Gap 5 — vs baseline academic rubric-LLM-judge (G-Eval, Prometheus)
- **Claim:** "we beat existing academic methods"
- **Status:** not benchmarked
- **Cost:** non-trivial. Defer to G9 / paper preprint phase.

## MVP plan for tonight (filling Gaps 1-3)

Rationale: these three together prove the wedge, the contract, and repeatability — the three things FLAGSHIP-SPEC's positioning depends on. Together: ~45 min wall, $0 marginal, all reversible markdown + small Python scripts. Per pre-committed auto-execute rule: scores ≥7 reversible → execute.

**Concrete deliverables:**
1. `evals/wedge-variance-comparison/` — hermes-rubric vs raw LLM rating on 1 target × Haiku × n=10 each
2. `evals/adversarial-confabulation-test/` — ground-truth-labeled target, run, verify hedge-flagging
3. `evals/repeatability-table/` — aggregation of existing rubric-runs into σ-per-target

Each gets a small README + the data + a one-paragraph summary. Total ~6 files. No new commits to source code. Pure eval-evidence accumulation.

## What would NOT be in scope for tonight's MVP

- G9 full reliability study (1-2 weeks)
- G6 EU AI Act / ISO 42001 mapping (3-5 days)
- Human-rated calibration corpus (off-thesis)
- Beating G-Eval / Prometheus (paper-track)

## Pre-registered decision rule

If the variance comparison (Gap 1 MVP) shows hermes-rubric variance < raw LLM rating variance by ≥30% → wedge claim has empirical support, document and ship in NEXT-UP.md as G9-precursor.
If variance ≥ raw LLM rating → null result, ship honestly per binding null-result publication commitment, downgrade FLAGSHIP-SPEC's variance-reduction language.
If adversarial-confabulation test shows fabrications NOT flagged → real bug; halt and surface to user.
If repeatability table shows σ > 1.5 across runs → "stable scores" claim weakened, document in FLAGSHIP-SPEC.
</thinking>

Run hermes-rubric-blinded on this so we audit the audit before executing — the standing convention.
