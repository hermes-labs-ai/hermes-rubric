# Pilot results — 2026-04-25

## Setup
- Target: T1 (`agent-convergence-scorer/src`)
- Phase: sub-exp A (score-stage isolation; frozen rubric + frozen evidence)
- N: 3 reps × 2 modes = 6 runs
- Backend: claude-cli (contextual mode — note: not bare; future runs should use `--bare` for better isolation)
- Modes alternated per rep to balance session drift

## Aggregate-level

| metric | per_dim | batched |
|---|---|---|
| n | 3 | 3 |
| mean aggregate | 5.933 | 6.133 |
| σ aggregate | 0.115 | 0.058 |
| mean latency | 67.7s | 23.4s |
| mean backend calls | 8.0 | 1.0 |
| fallback events | 0 | 0 |

- **Aggregate Δ = +0.20** (within ±1.0 margin) ✓
- **σ̂ = 0.115** (way below 1.5 abort threshold) ✓
- **Fallback rate = 0%** ✓
- **Latency 2.9× faster** in batched mode

## Per-dim deltas (batched − per_dim)

| dim_id | n | mean_Δ | σ_Δ | max\|Δ\| |
|---|---|---|---|---|
| dim_1 | 3 | +0.000 | 0.000 | 0.000 |
| dim_2 | 3 | +0.667 | **1.155** | **2.000** |
| dim_3 | 3 | +0.000 | 0.000 | 0.000 |
| dim_4 | 3 | +0.000 | 0.000 | 0.000 |
| dim_5 | 3 | +0.000 | 0.000 | 0.000 |
| dim_6 | 3 | +0.000 | 0.000 | 0.000 |
| dim_7 | 3 | **+1.000** | 0.000 | 1.000 |
| dim_8 | 3 | +0.000 | 0.000 | 0.000 |

## Findings

1. **6 of 8 dims show byte-equal score parity across modes.** The clamps and the score-stage prompt rewrite preserve scoring behavior on the majority of dimensions — strong signal.
2. **dim_2 is unstable across reps** with σ_Δ = 1.155 and max |Δ| = 2.0. Could be (a) genuine prompt-isolation effect on this dim, (b) per-dim mode noise, or (c) batched mode noise. N=3 cannot disambiguate.
3. **dim_7 has a consistent +1.0 batched bias** across all 3 reps with σ = 0. This is the cleanest candidate for a real systematic effect — small, reliably-detectable, but within the equivalence margin.
4. **Pilot acceptance: 3/4 ✓ , 1/4 ✗** — aggregate-level passes, per-dim max-Δ trips the rejection threshold. **Cannot conclude equivalence at per-dim resolution from N=3.**

## Power calc for paper-grade run

From observed σ_Δ = 1.155 on the noisy dim:
- N per cell to detect Δ=1.0 at α=0.05, power=0.80: **N ≈ 11**
- For Δ=0.5 detection: N ≈ 42
- For Δ=2.0 (the rejection threshold): N ≈ 3 (already met for that purpose)

**Recommendation for tomorrow's API-key run:** N=10–12 per (target, mode) on sub-exp A, N=5 on sub-exp B. Total ~600 calls per experiment with 5 targets.

## What this pilot does NOT establish
- Whether dim_2 instability is mode-specific or just LLM noise (N too small)
- Whether the dim_7 bias generalizes across targets (N targets = 1)
- End-to-end (sub-exp B) behavior — pilot only ran score-stage isolation
- Behavior under hedge / no-evidence / self-marketing clamps (T1 is the baseline target with no clamps active)

## Backend note
claude-cli ran in **contextual mode** (not bare). Tomorrow's paper-grade run should use `claude --bare` mode (already supported in `backends.py`) for cleaner isolation from session context.
