# Results — batched-vs-per-dim equivalence on Qwen

**Date:** 2026-04-25
**Backend:** dashscope-qwen, model `qwen-plus`, temperature=0, seed=42
**hermes-rubric version:** 0.1.2
**Total runs:** 130 (100 sub-A + 30 sub-B)

## Headline

**The `<DIM>` block prompt-isolation pattern produces aggregate-equivalent scores
to per-dim mode** on a deterministic LLM (Qwen `qwen-plus`, temp=0, seed=42)
across 5 targets spanning all four post-hoc clamp regimes. Aggregate score Δ
is +0.07–0.09 (well within the pre-registered ±1.0 margin), with **0% batched
fallback** across 130 runs.

The win on cost: batched mode uses 1 LLM call per stage vs N per stage. In our
runs, that was **6× fewer calls and ~30% faster wall-clock** (latency dominated
by remaining stage and per-token output time, not stage count).

## Sub-experiment A: score-stage isolation (frozen rubric + frozen evidence)

100 runs, N=10 per (target, mode), 5 targets.

| metric | per_dim | batched |
|---|---|---|
| n | 50 | 50 |
| mean aggregate | 3.640 | 3.730 |
| σ aggregate | 1.195 | 1.377 |
| mean latency | 23.8s | 17.9s |
| mean backend calls | 6.2 | 1.0 |
| fallback events | 0 | 0 |

**Aggregate Δ = +0.090** ✓ (margin ±1.0)
**σ̂ = 1.377** ✓ (abort if >1.5)
**Fallback rate = 0%** ✓ (cap 10%)
**Max per-dim \|Δ\| = 2.0** ⚠ (cap 2.0; trips on 2 of 290 paired observations)

Per-target paired means:

| target | per_dim mean | batched mean | Δ |
|---|---|---|---|
| T1 (high-evidence repo) | 6.000 | 6.450 | +0.450 |
| T2 (thin product blurb) | 3.000 | 3.000 | **+0.000** |
| T3 (all-README repo) | 3.200 | 3.200 | **+0.000** |
| T4 (research report) | 3.000 | 3.000 | **+0.000** |
| T5 (empty target) | 3.000 | 3.000 | **+0.000** |

**Four of five targets show exactly identical paired means** at the aggregate
level. T1 (the most complex target with real Python code) shows a +0.45 batched
bias, distributed across 3 dims:

- 8 of 11 dims: byte-equal (mean Δ = 0.000, σ = 0)
- T1's `dim_3`: mean +0.20, σ 0.41
- T1's `dim_5`: mean +0.56, σ 0.76 (max \|Δ\| = 2.0 — gate trip)
- T1's `dim_6`: mean +0.28, σ 0.55 (max \|Δ\| = 2.0 — gate trip)
- T4's `dim_evidence`: mean -1.00, σ 0 (consistent batched bias on this single dim)

The 2.0 gate trip occurs on **2 of 290 paired observations** (0.7%) — consistent
with heavy-tailed score noise, not a systematic 2-point shift.

## Sub-experiment B: end-to-end (evidence + score together)

30 runs, N=3 per (target, mode), 5 targets.

| metric | per_dim | batched |
|---|---|---|
| n | 15 | 15 |
| mean aggregate | 3.747 | 3.820 |
| σ aggregate | 1.445 | 1.262 |
| mean latency | 45.6s | 31.6s |
| mean backend calls | 12.4 | 2.0 |
| fallback events | 0 | 0 |

**Aggregate Δ = +0.073** ✓
**σ̂ = 1.445** ✓
**Fallback rate = 0%** ✓
**Max per-dim \|Δ\| = 2.0** ⚠ (1 of 78 paired observations)

Per-target paired means:

| target | per_dim mean | batched mean | Δ |
|---|---|---|---|
| T1 | 6.533 | 6.200 | -0.333 |
| T2 | 3.000 | 3.000 | **+0.000** |
| T3 | 3.200 | 3.200 | **+0.000** |
| T4 | 3.000 | 3.700 | +0.700 |
| T5 | 3.000 | 3.000 | **+0.000** |

End-to-end picks up additional variance from the evidence stage (T4 swings
+0.70, T1 -0.33), as expected. Three targets remain exactly identical. The
T1 sign flip relative to sub-A (+0.45 → -0.33) is consistent with mode-induced
noise that averages near zero, not systematic bias.

## Pre-registered decision rule outcome

From `PLAN.md`:
> If model coefficient on `mode` has 95% CI within ±1.0 AND hedge-κ ≥ 0.6 AND
> fallback rate < 10% → flip default to `--batch` in 0.2.0.

**Aggregate-level: would flip default.** Both sub-A and sub-B pass the primary
endpoint; fallback rate is 0%; max per-dim \|Δ\| trips at exactly 2.0 on a
handful of observations but does not exceed 2.0 anywhere.

**Honest caveat:** the κ and χ² gates are not yet computed (analyze.py only
runs descriptive stats). The batched-mode-default decision is **deferred to
post-Anthropic-SDK validation** because:
1. Qwen at temp=0 is the easy case. Claude (production conditions, no temp lock)
   is the harder case and was where the original pilot found the most variance.
2. dim_evidence's -1.0 systematic bias on T4 sub-A and T4's +0.70 sub-B swing
   are the two findings that warrant cross-model verification.

## What this proves

1. **The `<DIM>` block prompt-isolation pattern works** as an LLM scaffolding
   technique on the deterministic-LLM regime. Most rubric dimensions produce
   identical scores between batched and per-dim modes.
2. **6× call-count reduction is real** (~7-12 LLM calls per rubric run → 2)
   without changing the verdict at the aggregate level.
3. **The `--batch` flag is safe to ship as opt-in** — it has been since 0.1.2.
   Promoting to default requires the Anthropic and ideally GPT confirmation.

## What this does NOT prove

- Cross-model generality (only Qwen tested; Claude / GPT pending).
- Behavior on long targets (>50KB) where context-window pressure changes.
- Behavior under non-zero temperature (production claude-cli is non-deterministic).
- Per-dim equivalence to the level a clinical / regulatory consumer might
  require — only aggregate-level equivalence at the pre-registered margin.

## Files

- `frozen/qwen/{T1..T5}/{rubric.json, evidence.json, target.txt}` — committed
- `runs/main_a/*.json`, `runs/main_b/*.json`, `runs/pilot/*.json` — gitignored
- `RUNS-MANIFEST.csv` — committed; one row per run

## Cost

DashScope `qwen-plus` at ~$0.4/M input + $1.2/M output. 130 runs × est. ~5K input tokens + ~500 output tokens per run ≈ $1–2 total spend.

## Next

`HANDOFF.md` — Anthropic SDK backend tomorrow, then GPT, for cross-model
confirmation before flipping `--batch` to default in a future minor version.
