# hermes-rubric repeatability table — batch-equivalence experiment

**Source:** `~/Documents/projects/hermes-rubric/experiments/batch-equiv-2026-04-25/runs/{main_a,main_b}/*.json`
**Generated:** 2026-04-26 (from existing data, no new LLM calls)
**Question answered:** how stable are aggregate rubric scores across re-runs of the same target?

## σ across reps per (target × mode × backend-run)

| Target | Mode | Run | n | Mean | σ | Min | Max | Range |
|---|---|---|---|---|---|---|---|---|
| T1 | batched | main_a | 20 | 8.225 | 1.824 | 6.20 | 10.00 | 3.80 |
| T1 | batched | main_b | 6 | 5.700 | 0.548 | 5.20 | 6.20 | 1.00 |
| T1 | per_dim | main_a | 20 | 7.100 | 1.129 | 6.00 | 8.20 | 2.20 |
| T1 | per_dim | main_b | 6 | 7.367 | 0.916 | 6.40 | 8.20 | 1.80 |
| T2 | batched | main_a | 20 | 4.450 | 1.488 | 3.00 | 5.90 | 2.90 |
| T2 | batched | main_b | 9 | 5.000 | 1.500 | 3.00 | 6.00 | 3.00 |
| T2 | per_dim | main_a | 20 | 4.450 | 1.488 | 3.00 | 5.90 | 2.90 |
| T2 | per_dim | main_b | 9 | 4.933 | 1.450 | 3.00 | 5.90 | 2.90 |
| T3 | batched | main_a | 20 | 4.600 | 1.436 | 3.20 | 6.00 | 2.80 |
| T3 | batched | main_b | 8 | 4.825 | 1.346 | 3.20 | 5.80 | 2.60 |
| T3 | per_dim | main_a | 20 | 4.600 | 1.436 | 3.20 | 6.00 | 2.80 |
| T3 | per_dim | main_b | 9 | 5.067 | 1.400 | 3.20 | 6.00 | 2.80 |
| T4 | batched | main_a | 22 | 1.845 | 1.842 | 0.00 | 5.30 | 5.30 |
| T4 | batched | main_b | 9 | 5.100 | 1.054 | 3.50 | 5.80 | 2.30 |
| T4 | per_dim | main_a | 22 | 1.818 | 1.790 | 0.00 | 5.10 | 5.10 |
| T4 | per_dim | main_b | 9 | 1.000 | 1.500 | 0.00 | 3.00 | 3.00 |
| T5 | batched | main_a | 20 | 3.000 | 0.000 | 3.00 | 3.00 | 0.00 |
| T5 | batched | main_b | 6 | 3.000 | 0.000 | 3.00 | 3.00 | 0.00 |
| T5 | per_dim | main_a | 20 | 3.000 | 0.000 | 3.00 | 3.00 | 0.00 |
| T5 | per_dim | main_b | 6 | 3.000 | 0.000 | 3.00 | 3.00 | 0.00 |

## Cross-cell σ summary

- Total cells: 20
- Cells with n>1 (σ computable): 20
- Mean σ across cells: 1.107
- Median σ across cells: 1.418
- Max σ: 1.842
- Min σ: 0.000

## Interpretation

σ ≈ 0 means scores are byte-identical across reps (deterministic in scoring stage).
σ < 0.5 means scores are stable within ±0.5 score-points.
σ ≥ 1.0 means scores are unreliable for that target/mode.

**Honest caveat:** these runs all use seed=42, temperature=0 — so σ measures only the
upstream LLM's own residual non-determinism (kernel scheduling under temp=0 still yields
byte-divergent outputs at near-tie tokens, ~1-3% by published estimates), not the broader
rubric-tool variance under realistic deployment.
