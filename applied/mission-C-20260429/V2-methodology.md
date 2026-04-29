# V2 Methodology — Hungarian-Matched Cosine on Dim-Description Embeddings

**Status:** Written BEFORE any embedding code, per Metacognitive Framework Constraint 2.
**Component:** Mission C V2 — deterministic rubric-equivalence metric.
**Author:** Mission C Opus subagent, 2026-04-29.

---

## 1. Embedding Model — Choice and Rationale

**Chosen model:** `nomic-embed-text` (Nomic v1.5), served locally via Ollama at `http://localhost:11434/api/embeddings`. Output dimension: 768.

**Why this model is philosophically appropriate for the rubric-dim semantic space:**

1. **Granularity match.** Rubric dimensions consist of a `name` (~3-8 words) plus a `description` (~10-30 words) plus `evidence_instructions` (~10-30 words). This is sentence-to-short-paragraph granularity — exactly the granularity nomic-embed-text was trained for (sentence and short-document retrieval). Token-level word2vec would lose compositional meaning ("epistemic accountability" ≠ "accountability + epistemic"). Document-level models trained on long-form text would over-smooth and miss the discriminating phrase.

2. **No same-family LLM-judge bias.** The whole point of V2 is to escape the JSS critique that same-family LLMs (Claude judging Claude) carry shared priors. nomic-embed-text is a contrastively-trained encoder, not an instruction-following LLM. It does not share Claude's instruction-following or Anthropic-specific priors. We accept that we ARE substituting one model's prior for another's (encoder bias for LLM-judge bias), and Constraint 2 sanity check exists precisely to catch the case where that substitution produces a meaningless threshold.

3. **Already in stack.** `feedback_zero_llm_first.md` and the canonical-tools index already place nomic-embed-text as the project's standard embedding. Reusing the same encoder elsewhere in the stack (cogito-ergo, hermeneutic compile-index) means our threshold lives in a vector-space the rest of HAL also interrogates — calibration generalizes.

4. **Determinism.** Ollama with fixed model + seed produces deterministic embeddings for the same input. This is required for the run-1 vs run-2 same-input scoring to be reproducible across a session.

**Embedding input format per dim:** `name + ". " + description + " " + evidence_instructions`. Concatenation, not separate embeddings, because the three fields jointly define what the dimension measures; a name like "Rigor" embedded alone is nearly content-free.

---

## 2. Random-Permutation Null Distribution — Mathematical Specification

### 2.1 Setup

Let R₁, R₂, ..., R_K be K rubrics (K = 5 same-input runs in this experiment). Each rubric R_k has m_k dimensions; each dimension has an embedded description vector v ∈ ℝ⁷⁶⁸.

For two rubrics R_a and R_b, define the dim-similarity matrix:

    M_{a,b}[i,j] = cosine(v_{a,i}, v_{b,j})

with cosine(u, w) = (u·w) / (‖u‖‖w‖) ∈ [-1, 1] (in practice [0, 1] for normalized text embeddings of related semantic content; nomic-embed embeddings are not strictly non-negative but text-encoder cosines very rarely go below 0 for natural English).

### 2.2 Hungarian-Matched Cosine

We want a single similarity score for the *rubric pair*, not for individual dim pairs. Greedy max-pair matching is biased: a single dominant dim could anchor the match. Instead, we compute the **Hungarian-optimal one-to-one matching** that maximizes total similarity:

    π* = argmax_π Σ_i M_{a,b}[i, π(i)]

where π ranges over injective maps from rows of R_a to columns of R_b. We use scipy's `linear_sum_assignment(-M)` (it minimizes; negate to maximize).

The Hungarian-matched cosine score is:

    H(R_a, R_b) = (1/min(m_a, m_b)) · Σ_i M_{a,b}[i, π*(i)]

Range: [-1, 1]; for sane embeddings of related rubrics, [0.3, 1.0].

### 2.3 Same-Input Distribution

For our K = 5 runs we compute H(R_a, R_b) for all C(5,2) = 10 unordered pairs. This is the **same-input distribution**: distribution of similarity scores when the synthesizer is asked the SAME question 5 times. Under H1-C, this distribution should concentrate above the null threshold (next subsection).

### 2.4 Random-Permutation Null Distribution

The null question: *what would the Hungarian-matched cosine look like for unrelated rubrics, controlled for the embedding model's baseline vocabulary bias?*

**Permutation construction:**
- Pool ALL dim descriptions across all 5 rubrics: total D = m₁ + m₂ + ... + m₅ ≈ 30-40 dims.
- For each random pair, sample without replacement two disjoint groups of size m̄ = round(mean(m_k)) (≈ 6-7 dims) from the pool.
- Compute H on this synthetic-rubric pair.
- Repeat N ≥ 100 times → null sample {H_null,1, ..., H_null,N}.

**Why this null is correct:**
- Same vocabulary distribution (all dims drawn from the same synthesizer's outputs on this exact intent).
- Same dim count (≈ same-size matching).
- Same embedding model (no extrinsic vocabulary).
- Different *semantic alignment*: random pairing destroys the structural correspondence between the matched dims, so any residual high cosine is pure embedding-space vocabulary overlap.

If the embedding model assigns high cosine to *any* two dims drawn from the rubric pool simply because they share generic words ("evidence", "scoring", "claim"), the null distribution will reflect that and the threshold will rise to compensate. This is the protective property that defends against substituting LLM-judge bias for embedding-space bias.

### 2.5 Threshold and Pass Criterion

    threshold = mean(null) + 2 × std(null)

A same-input pair score H(R_a, R_b) ≥ threshold → reject the null at ~97.5% one-sided (assuming approximate normality of the null; if the null is skewed we ALSO report the empirical 97.5th percentile and pass only if both bounds are crossed).

**Pre-registered pass condition (per PRE-REGISTRATION):**
- All 10 same-input pairs ≥ 0.7 cosine (absolute floor — calibration anchor)
- All 10 same-input pairs ≥ threshold (statistical anchor)
- Threshold passes sanity check (next subsection)

### 2.6 Sanity Check (Constraint 2 — load-bearing)

The threshold is suspect in two regimes:

| Regime | Diagnosis | Action |
|---|---|---|
| threshold < 0.30 | Null is too low — embedding model assigns near-zero similarity even between vocabulary-overlapping rubric dims. Means same-input passing the threshold is almost vacuous. | HALT V2. |
| threshold > 0.95 | Null is suspiciously high — embedding model collapses everything from this domain to near-identical vectors. Means same-input passing the threshold is automatic and meaningless. | HALT V2. |
| 0.30 ≤ threshold ≤ 0.95 | Discriminating regime — embedding model retains semantic resolution within this domain. Threshold is informative. | PROCEED. |

If HALT, log to `V2-halt-log.md` with: null distribution mean, std, min, max, percentiles {25, 50, 75, 95, 97.5}; threshold value; example random-pair scores; and a flag for whether the suspicion is low-domain-resolution or high-domain-resolution.

**Why this sanity check is necessary, not optional.** Per Roli's framework directive: "We do not trade LLM-judge bias for embedding-space bias." If the null distribution is degenerate, the threshold is meaningless even if the same-input pairs technically clear it. The check forces us to validate that the embedding-space measurement is a meaningful signal *before* we use it to validate same-input rubric stability.

---

## 3. Implementation Plan

1. Synthesize 5 rubrics with identical inputs:
   - intent: "audit this paper for epistemic accountability and hygiene"
   - context: paper abstract or front-matter (use the existing META-RUBRIC paper or a stub)
   - target_type: preprint-paper
   - Store at `V2-rubrics/run-1.json` ... `run-5.json`.

2. Embed each dim's text (`name + ". " + description + " " + evidence_instructions`) via Ollama nomic-embed-text. Cache embeddings keyed by SHA256 of the input string for reproducibility.

3. Compute the same-input distribution: H(R_a, R_b) for all 10 unordered pairs.

4. Build the random-permutation null: pool all dims, sample N=200 random rubric pairs (each of size m̄ ≈ mean of m_k), compute H for each.

5. Compute threshold = mean(null) + 2 × std(null). Run sanity check.

6. If sanity passes: report same-input distribution vs null. Pass if all same-input ≥ max(0.7, threshold).

7. If sanity fails: HALT, log to `V2-halt-log.md`. Mark V2 component as failed for Phase 1 self-rubric.

8. Save full results to `V2-results.json`: rubrics summary, same-input pair scores, null sample summary, threshold, sanity verdict, pass/fail.

---

## 4. Risks Pre-Identified

- **Risk: Local LLM synthesizer flaky / slow.** If `synthesize()` hits a backend that errors, V2 cannot generate the 5 rubrics. Mitigation: try the local Ollama backend with a small qwen model; if synthesis fails, fall back to manually-authored 5 minimally-varied rubrics that test the metric's discriminative power without relying on stochastic LLM output. Document fallback in receipt.

- **Risk: nomic-embed-text degenerate on rubric domain.** If all rubric dims live in a tiny region of embedding space (everything is "evaluate something, find evidence, score 0-10"), the null will be high and the threshold will fail the sanity check. This is exactly the case Constraint 2 protects against, and we will HALT rather than declare false success.

- **Risk: K=5 is small for a null.** The same-input distribution has only 10 points. We compensate by making the null large (N≥200). The same-input distribution is descriptive (does it cluster high?), the null is the statistical spine.

- **Risk: Hungarian on different-size matrices.** If m_a ≠ m_b, the matching is over min(m_a, m_b) pairs. We normalize by min(m_a, m_b) so the score is comparable across pair sizes. Already specified above.

---

## 5. What Would Falsify This Approach

The approach is falsified if:
- Sanity check halts (threshold uninformative) — V2 logged as failed-component.
- Same-input distribution is BELOW the threshold (synthesis is unstable; the rubric-equivalence claim itself fails — this is a signal about the synthesizer, not about V2's metric).
- Same-input distribution is ABOVE 0.95 for all pairs AND null mean is ALSO ≥ 0.85 — would mean the embedding can't tell same-input from random-input rubrics. Sanity check should already catch this.

A pass requires: 10/10 same-input pairs ≥ max(0.7, threshold) AND threshold in (0.30, 0.95). Anything else is a halt or a fail.
