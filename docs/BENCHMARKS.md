# Benchmarks

Bounded evaluation evidence for hermes-rubric.

## Available evidence

The committed [2026-04-25 report](https://github.com/hermes-labs-ai/hermes-rubric/blob/main/experiments/batch-equiv-2026-04-25/RESULTS.md) documents a batch-versus-per-dimension comparison on five fixtures. Raw run JSON is gitignored and not included, so this repository does not currently support a from-clone recomputation claim.

## Test-set composition

5 fixture targets (T1–T5) spanning three artifact-quality domains:

- Paper-quality scoring
- Deploy-readiness scoring
- Email-quality scoring

Full target list at [`experiments/batch-equiv-2026-04-25/RESULTS.md`](https://github.com/hermes-labs-ai/hermes-rubric/blob/main/experiments/batch-equiv-2026-04-25/RESULTS.md).

## What the κ measures

`hermes-rubric kappa --run1 <run_a.json> --run2 <run_b.json>` computes Cohen's κ between two completed runs on the same target. The metric answers: "how much do two scoring runs agree above chance?"

The committed report is bounded evidence about **batch-vs-per-dim behavior** on its fixtures, not a generalization claim across all artifact domains. Cross-domain κ (paper-quality vs deploy-readiness vs lead-score) is on the roadmap (see `experiments/rubric-quality-PROPOSAL.md`).

## Variance comparison

[`evals/wedge-variance/`](https://github.com/hermes-labs-ai/hermes-rubric/tree/main/evals/wedge-variance) contains a runner and historical outputs comparing Hermes aggregate scores with raw 0–10 LLM ratings on the same target and backend. Interpret only the observations and limitations recorded with that run.

## Worked examples

[`applied/papers-20260423.md`](https://github.com/hermes-labs-ai/hermes-rubric/blob/main/applied/papers-20260423.md) - two publicly published Zenodo papers scored on publication-readiness:

| Paper | Aggregate |
|---|---|
| Taxonomy of Epistemic Failure Modes | 6.9 |
| Asymmetric Burden of Proof | 6.5 |

Each score has a full rubric + citations + per-dimension rationale in the file.

## Calibration set

[`calibration/dataset.jsonl`](https://github.com/hermes-labs-ai/hermes-rubric/blob/main/calibration/dataset.jsonl) - 7 labeled cases across paper-quality, tool-fit, and deploy-readiness. All targets are publicly available artifacts (Zenodo papers, public OSS tools).

[`calibration/META-RUBRIC.md`](https://github.com/hermes-labs-ai/hermes-rubric/blob/main/calibration/META-RUBRIC.md) - the rubric for evaluating rubric generators. 7 dimensions, each motivated by a specific LLM failure mode from the failure-mode taxonomy.

[`calibration/failure-mode-taxonomy.md`](https://github.com/hermes-labs-ai/hermes-rubric/blob/main/calibration/failure-mode-taxonomy.md) - the committed failure-mode taxonomy and its source pointers.

## Known limitations

- **κ measured on 5 fixture targets only.** Evidence for batch-vs-per-dim equivalence on this set, not yet a generalization claim across all domains.
- **Stage-1 rubric synthesis is not deterministic.** Same intent + context can produce slightly different dim sets. Use `--artifact-class <name>` to keep the dimension set fixed across runs.
- **Raw paired-run JSON is not committed.** Treat the report as a historical result, not a from-clone rerun guarantee.
