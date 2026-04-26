# Repeatability finding — interpretation

**Generated:** 2026-04-26 (from existing batch-equiv-2026-04-25 data, no new LLM calls)
**Source data:** `evals/repeatability/REPEATABILITY-TABLE.md`

## What we can claim (with this data alone)

- Aggregate scores ARE stable across reps **when target evidence is rich** (T1 high-evidence Python repo: σ 0.55-1.10 in main_b's 6 reps).
- Aggregate scores are **stable-by-degeneracy on empty input** (T5: σ=0.000, model returns 3.0 every time — likely a hedge-floor cap firing, not a real signal).
- Aggregate scores **vary by ±1.5 score-points** for thin-evidence targets (T2 product blurb, T3 README-only repo, T4 markdown report).

## What we CANNOT claim (with this data alone)

- **"Lower variance than raw LLM rating."** Mean σ across cells = 1.107. Published naive LLM-as-judge variance estimates are 1.0-2.0 on 0-10 scales. **This data does not establish that hermes-rubric is more stable than `claude --print "rate this 0-10"`.** That comparison is Gap 1 in `EVAL-COVERAGE.md` and remains to be run.
- **"Rubric framework rescues thin-evidence cases."** Thin-evidence targets (T2, T3, T4) show σ ≥ 1.4. The hedge-on-thin-evidence convention reduces some variance vs unhedged, but this data alone doesn't quantify that reduction.

## What this data IS good for

- **Customer-facing honesty:** "hermes-rubric is reliable for evidence-rich targets (σ < 1.0); use with caution on thin-evidence targets."
- **Pre-G9 baseline:** when G9 (cross-backend κ study) runs, this gives the per-target reliability floor against which the κ correlations can be interpreted.
- **Mode-equivalence floor:** batched and per_dim modes show similar σ patterns within target × run, which is the engineering-equivalence claim already proven.

## What's different about T1 main_b (the σ < 1 case)

T1 is the only target with σ consistently <1.0 across modes and runs. T1 = `agent-convergence-scorer/src` (high-evidence Python repo with file:line citations possible). Suggests: hermes-rubric's stability scales with target's evidence-availability — **which is exactly what the framework's design intends** ("evidence-first scoring"). When evidence exists, scoring is stable. When evidence is thin, hedging kicks in but variance remains.

## Honest framing for FLAGSHIP-SPEC update

The "lower variance than raw LLM rating" wedge in `FLAGSHIP-SPEC.md` should be qualified as: *"reduces variance under evidence-rich conditions, with explicit hedging on thin-evidence inputs to surface uncertainty rather than fabricate confidence."* The clean head-to-head vs raw LLM rating remains unrun (Gap 1).

## Action items derived from this finding

1. Run Gap 1 (variance vs raw LLM rating) when claude-cli load drops — currently throttled
2. Update FLAGSHIP-SPEC's wedge language to qualified form (cheap edit, do tomorrow)
3. Consider including this repeatability table in any G2/G3/G4 customer-facing material — it's both honest and useful
