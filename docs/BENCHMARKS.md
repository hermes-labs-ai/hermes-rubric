# Benchmarks

Cross-model agreement and reproducibility data for hermes-rubric.

## Headline number

**Cross-model Cohen's κ = 0.629** (62.9% chance-corrected agreement) across 96 paired runs on the batch-equivalence test set. Passes the pre-registered ≥0.6 reproducibility floor.

## Per-backend breakdown

| Backend | κ | N (paired runs) |
|---|---|---|
| Gemini 2.5 Flash | 0.642 | 47 |
| Qwen-Plus | 0.621 | 47 |
| Claude (Anthropic SDK) | 0.527 | 2 |

Claude κ at N=2 is too few pairs for a stable estimate — included for transparency only. Deferred Claude paper-grade run noted in `ACTIONABLES.md`.

## Test-set composition

5 fixture targets (T1–T5) spanning three artifact-quality domains:

- Paper-quality scoring
- Deploy-readiness scoring
- Email-quality scoring

Full target list at [`experiments/batch-equiv-2026-04-25/RESULTS.md`](../experiments/batch-equiv-2026-04-25/RESULTS.md).

## Reproduce

```bash
git clone https://github.com/hermes-labs-ai/hermes-rubric && cd hermes-rubric
python experiments/batch-equiv-2026-04-25/compute_kappa.py
# Per-target κ table, per-backend mean, overall mean. Should match RESULTS.md.
```

If the script's output doesn't match this number, file an issue. The chain is broken and we want to know.

## What the κ measures

`hermes-rubric kappa <run_a.json> <run_b.json>` computes Cohen's κ between two completed runs on the same target. The metric answers: "how much do two scoring runs agree above chance?"

κ = 0.629 on this test set is evidence for **batch-vs-per-dim equivalence**, not yet a generalization claim across all artifact domains. Cross-domain κ (paper-quality vs deploy-readiness vs lead-score) is on the roadmap (see `experiments/rubric-quality-PROPOSAL.md`).

## Variance comparison

[`evals/wedge-variance/`](../evals/wedge-variance/) compares hermes-rubric's `aggregate` score against raw 0–10 LLM ratings on the same target × same backend. Demonstrates the variance-reduction wedge with a reproducible runner.

## Worked examples

[`applied/papers-20260423.md`](../applied/papers-20260423.md) - two publicly published Zenodo papers scored on publication-readiness:

| Paper | Aggregate |
|---|---|
| Taxonomy of Epistemic Failure Modes | 6.9 |
| Asymmetric Burden of Proof | 6.5 |

Each score has a full rubric + citations + per-dimension rationale in the file.

## Calibration set

[`calibration/dataset.jsonl`](../calibration/dataset.jsonl) - 7 labeled cases across paper-quality, tool-fit, and deploy-readiness. All targets are publicly available artifacts (Zenodo papers, public OSS tools).

[`calibration/META-RUBRIC.md`](../calibration/META-RUBRIC.md) - the rubric for evaluating rubric generators. 7 dimensions, each motivated by a specific LLM failure mode from the failure-mode taxonomy.

[`calibration/failure-mode-taxonomy.md`](../calibration/failure-mode-taxonomy.md) - 24 failure modes mined from the Hermes Labs research corpus (1,892 experiment records + named post-mortem incidents). Each FM cites a source artifact.

## Known limitations

- **κ measured on 5 fixture targets only.** Evidence for batch-vs-per-dim equivalence on this set, not yet a generalization claim across all domains.
- **Stage-1 rubric synthesis is not deterministic.** Same intent + context can produce slightly different dim sets. Use `--artifact-class <name>` for full reproducibility on repeated artifact types.
- **Anthropic SDK backend has only N=2 Claude pairs in the cross-model figure.** Larger run is on the roadmap.
