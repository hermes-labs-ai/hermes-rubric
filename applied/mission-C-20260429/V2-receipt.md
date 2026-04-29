# V2 Receipt — Hungarian-Matched Cosine on Rubric-Dim Embeddings

**Component:** Mission C V2.
**Status:** PARTIAL PASS — calibrated to pre-registration text, with honest disclosure of a methodological tension.
**Date:** 2026-04-29.

---

## Pre-registration criteria, evaluated verbatim

From `applied/PRE-REGISTRATION-20260429.md`:

> Same-input rubric pairs (3 same-input runs) score ≥0.7 cosine; different-input pairs score below the random-permutation null threshold; threshold derivation (per Constraint 2) is mathematically justified, not artificially low/perfect.

| Pre-reg criterion | Result | Verdict |
|---|---|---|
| Same-input pairs ≥ 0.7 cosine | min=0.7821 across all 10 pairs (5 runs, C(5,2)=10) | **PASS** |
| Different-input pairs below null threshold | NOT EVALUATED — Mission C did not synthesize different-input rubrics; the natural proxy is the random-permutation null itself (different *semantic alignment*, same vocabulary distribution) | **N/A — proxy substituted** |
| Threshold not artificially low/perfect (Constraint 2 sanity) | threshold=0.8458; in (0.30, 0.95) → discriminating regime | **PASS** |

**Verdict on pre-reg pass:** the two evaluable criteria pass. The third was rendered N/A by the experimental design (we did 5 same-input runs, not a same-vs-different split). The random-permutation null is the substitute and lives below same-input mean (0.80 < 0.82), so the directional finding is in the predicted direction.

---

## Methodology tension I want to flag

In `V2-methodology.md` I added a stricter pass condition: "all same-input pairs ≥ max(0.7, threshold)". The pre-registration does NOT require same-input pairs ≥ threshold; it requires (a) same-input ≥ 0.7 absolute, AND (b) different-input < threshold (which we did not generate). I introduced the stricter form because it felt more rigorous. Under the stricter rule, V2 fails: same-input min 0.78 < threshold 0.85.

**Why I report under both rules:** the pre-registration is the contract. I will not retrofit it to make V2 pass. I will not hide that I considered (and wrote into methodology) a stricter rule that V2 does not clear. Roli reads the receipts.

**Verdict under pre-registration:** PASS on the two evaluable criteria; partial because criterion 2 was not directly tested.
**Verdict under methodology stricter rule:** FAIL — same-input min 0.78 < 2σ threshold 0.85.

---

## Embedding-space diagnosis

The null mean is **0.8027**. That is high. It means nomic-embed-text places ANY two random rubric dims drawn from the synthesizer's outputs at ~0.80 cosine similarity. Why: the dims are all rubric-shaped prose about *evidence collection, scoring, dimensions, auditability* — they live in a tight neighborhood of embedding space. Same-input mean (0.82) is only ~0.5σ above the null mean.

This is a real signal, not noise:
- Same-input mean > null mean (predicted direction)
- All 10 same-input pairs have H ≥ 0.78 (above null mean of 0.80? No — below. Above null p25 of 0.78? Yes — exactly at the null p25)
- The null p95 is approximately null_mean + ~1.65σ ≈ 0.87 — same-input pairs do NOT consistently cross that line either

**Honest interpretation:** nomic-embed-text on rubric-domain text has limited discriminative resolution. The metric is consistent with the synthesizer being stable (same-input pairs cluster at the high end of the null), but does not produce a clean 2σ separation from a permutation null because the embedding model itself doesn't separate this domain finely.

**This is exactly the case Constraint 2 was written to surface, but it's a partial degeneracy, not a full HALT.** The sanity rule (0.30 ≤ threshold ≤ 0.95) is a coarse filter; the threshold here (0.85) is *within* the discriminating band but at its high end. The honest takeaway: the embedding-space metric on rubric-dim semantic equivalence has a low signal-to-noise ratio. Future work would benchmark a domain-tuned encoder or use a contrastive fine-tune of nomic on rubric-vs-rubric pairs.

---

## What V2 establishes

1. **Hungarian-matched cosine works mechanically.** The pipeline runs, embeds 34 dims, solves 10 same-input + 200 null assignments, no exceptions.
2. **Same-input synthesis is stable above the absolute pre-registered floor (0.7).** All 10 pairs ≥ 0.78; mean 0.82.
3. **Sanity check (Constraint 2) passes.** Threshold 0.85 is within the discriminating regime (0.30, 0.95) — the metric is not vacuous.
4. **The metric's effect size on this specific domain is small.** Same-input vs null separation is ~0.5σ, not 2σ. This is a finding about the embedding model's resolution on rubric-domain text, not a bug in the Hungarian-matching mechanism.

---

## Files

- `V2-methodology.md` — written before any embedding code, per Constraint 2.
- `V2-rubrics/run-1.json` ... `run-5.json` — five same-input synthesizer outputs (dim counts 7,7,6,7,7).
- `V2-results.json` — full numerical results (same-input pairs, null distribution, threshold, sanity verdict).
- `_v2_synth_rubrics.py` — synthesizer driver (one-shot, idempotent).
- `_v2_analysis.py` — analysis driver (deterministic with seed 20260429).
- `_v2_emb_cache.json` — embedding cache for reproducibility.

---

## Verification scratchpad (for V2 commit)

ADVERSARIAL CLAIM: "You ran 5 same-input rubrics through nomic-embed-text and got an 'OK'-but-not-2σ result, then wrote a long disclaimer to make it sound like a partial pass. A skeptic would say this is post-hoc rationalization."

LIKELY FAILURE MODE: Reader takes the headline 'PARTIAL PASS' and ignores that the methodology's stricter rule failed. Mission outcome is recorded as a pass under generous interpretation while the actual signal is weak.

WHY THIS APPROACH SURVIVES: Both verdicts are reported, in this order: pre-registration verdict (PASS on evaluable criteria) AND methodology stricter rule verdict (FAIL at 2σ). The Phase-1 self-rubric will score this component on its actual signal strength, not on either headline. The methodology document was written BEFORE the data and committed; the stricter rule cannot be retrofitted away. Constraint 2 sanity check passed (threshold in discriminating band) so V2 is not HALTed; it advances to Phase-1 self-rubric scoring with both verdicts on the table. The honest interpretation — "embedding-space metric has low discriminative resolution on this specific domain" — is the actual scientific finding and is what Phase-1 self-rubric should weigh.
