# Proposal: rubric-quality eval (separate experiment, not yet started)

**Status:** Proposal only. Not run. Drafted 2026-04-25 after batch-equivalence experiment surfaced the gap.

## What's missing
The 2026-04-25 batch-equivalence experiment proved that hermes-rubric's two scoring modes agree at aggregate level. It did **not** prove that hermes-rubric scores correlate with anything outside hermes-rubric. The tool could be internally consistent and still wrong.

## Question
Do hermes-rubric scores correlate with (a) human judgment on the same targets, (b) ground-truth quality on curated good/bad pairs, (c) baseline LLM-as-judge with no rubric?

## Design sketch

### Targets (~30)
Curated pairs across 5 domains: Python repos, research papers, plans, blog posts, READMEs.
Each domain has 6 targets: 2 known-good, 2 known-bad, 2 mid. Source from existing public repos / arXiv / OSS examples to avoid Hermes-internal bias.

### Raters (4)
1. **hermes-rubric** with synthesized rubric (its current production behavior).
2. **hermes-rubric --batch** (controls for the 2026-04-25 finding — does the per-dim shift on T1 generalize?).
3. **Naive LLM-as-judge** baseline: same model, no rubric, prompt = "rate 0-10, one sentence rationale."
4. **Human (you)** on a sample of 10 of the 30 targets. Rate 0-10 with notes.

### Metrics
- **Cohen's κ** between hermes-rubric and human on the 10-target sample (primary).
- **Spearman ρ** between each rater and the curated quality label (good/bad/mid as 9/3/6).
- **Agreement matrix:** hermes-rubric vs naive LLM-as-judge — do they disagree on real things or just on calibration?
- **Inter-mode agreement** within hermes-rubric: per_dim vs batched on this corpus, to extend the 2026-04-25 result beyond the 5-target experiment.

### Pre-registered acceptance
- Spearman ρ(hermes-rubric, ground-truth) ≥ 0.6 → "rubric works."
- Cohen's κ(hermes-rubric, human) ≥ 0.5 → "rubric matches human judgment moderately."
- hermes-rubric Spearman > naive LLM-as-judge Spearman by ≥ 0.1 → "rubric adds value over naive."
- All three pass → "hermes-rubric is a useful audit grader."
- Any fail → which one tells you what to fix.

### Cost
~30 targets × 3 LLM raters × 1 paid backend (Sonnet 4.6 or qwen-plus). ~120 LLM rubric runs ≈ ~$5-15.
Plus ~1 hour of your time rating 10 targets manually.
Wall-clock: ~1 day end-to-end.

### Output
- `experiments/rubric-quality-2026-04-26/RESULTS.md` with the four metrics + per-target table.
- Logged to `~/Documents/projects/research-corpus/agent-infra/raw/`.
- Decision: keep / fix / replace hermes-rubric in the Hermes audit-evidence stack.

## What this enables for paper / positioning
- "hermes-rubric is internally consistent across modes (2026-04-25)" + "and matches human judgment at κ ≥ 0.5 (2026-04-26)" = a defensible audit-grader claim.
- Without (b), hermes-rubric is a well-engineered LLM-as-judge wrapper. With (b), it's a measurably-useful audit grader.

## Why this isn't tonight
- Requires curated good/bad pairs (sourcing time).
- Requires human-rater step (your 1 hour).
- Tonight's batch-equivalence work + cross-model run is a clean engineering result that stands on its own.

Defer to you: schedule for tomorrow / this week, or park.
