# Mission C Phase 1 — Failed-Component R&D Output

**Status:** Phase 1 BELOW FLOOR (7/10) and V=0 condition tripped (V3=0). Phase 2 NOT entered, per pre-registration.
**Date:** 2026-04-29.
**Audience:** langquant project (per pre-registration directive: "halt at Phase 1, document each failed component as R&D output for langquant project").

---

## V2 — Hungarian-matched cosine, partial-pass R&D yield

### What worked
- Mechanical pipeline is correct: 5 same-input synth → 34 dim embeddings via nomic-embed-text → all C(5,2)=10 pairwise Hungarian-matched cosines computed → permutation null at N=200 → 2σ threshold derived → Constraint 2 sanity-check applied (PASS, threshold in [0.30, 0.95]).
- Same-input pairs cluster above the absolute pre-registered floor of 0.7 (min 0.78, mean 0.82).
- Same-input mean exceeds null mean directionally (0.82 > 0.80).

### What didn't work
- Same-input vs null separation is only ~0.5σ — well below the 2σ statistical-significance threshold the methodology added.
- Null mean is **0.80**: nomic-embed-text places ANY two random rubric dims at ~0.80 cosine. The embedding model has limited discriminative resolution on rubric-domain prose because all dims share rubric-shaped vocabulary (evidence, scoring, dimension, citation, etc.).

### langquant R&D implications
1. **Don't pretend semantic-equivalence is a black-box embedding question.** A domain-tuned encoder (nomic fine-tuned on rubric-vs-rubric pairs) would compress the in-domain null and lift the same-input separation. Without that, generic encoders are too coarse for this measurement.
2. **The Hungarian matching mechanism is fine** — the issue is the embedding feature space, not the assignment. If you have a better feature space (LangQuant's signal-fingerprint topology, structured-feature concatenations, sparse rubric tokens), the same Hungarian wrapper would produce stronger separation.
3. **Permutation-null sanity is load-bearing.** Constraint 2's 0.30/0.95 sanity rule is correct in shape but coarse in resolution: it would catch a pathological collapse but not a partial-degeneracy regime like the one observed here. A finer rule (e.g. "null std must exceed X% of (1 - null_mean)") might surface the partial case before it produces weak verdicts.

### Reusable artifact
`_v2_analysis.py` is a clean reusable Hungarian-matched-cosine null-distribution harness. Drop in a different embedding model + a different rubric corpus, run, get results. Useful for langquant's empirical evaluation of feature-space alternatives.

---

## V3 — hermeneutic Stage 1, all-pass collapse R&D yield

### What worked
- `hermeneutic gate` runs without exception on rubric dim text.
- Gate fires correctly on adversarial rubric-shaped text containing "definitely" / "comprehensive" / "production-ready" — sanity confirmed.

### What didn't work
- ALL 7 rubric dim descriptions pass the gate. Differentiation criterion failed.

### langquant R&D implications
1. **`hermeneutic` was scoped for AI-output risk patterns, not for rubric-criterion text.** The mismatch is real and structural, not a bug. Routing rubric dim text through hermeneutic's existing rules is a category error.
2. **A domain-fit version would build a rubric-criterion-quality regex layer.** Patterns to consider:
   - Vague evidence instructions ("look for things related to X") vs specific ones ("count citations matching pattern Y") — vagueness as a measurable signal.
   - Universal quantifiers in description ("measures all aspects of X") that signal undiscriminating dims.
   - Numeric specificity in evidence instructions: thresholded test (good) vs. holistic vibe check (bad).
   - Description-evidence alignment (description claims X is measured; evidence instructions actually look for Y).
3. **`hermeneutic`'s Stage 2 (LLM-based) might catch what Stage 1 misses** for rubric domain — but that re-introduces an LLM judge, defeating the deterministic pre-filter goal.

### Reusable artifact
The all-pass collapse pattern itself is a useful diagnostic: any time a regex gate is applied to a domain it wasn't designed for, the failure mode is uniform output, not noisy output. langquant should add this as a known anti-pattern in the gate-deployment playbook.

---

## V1 — clean PASS, langquant doesn't need it

V1's `--rubric-file` flag works; not langquant R&D. (Listed for completeness; this section is empty by design.)

## V4 — clean PASS within architectural constraints

`hermes-seal` cannot grant a single file because grant requires repo-level category manifests. Verification of an already-sealed repo (which contains the pre-registration file) produces exit-0 cleanly. Mission C explored the architectural boundary and named it; not langquant R&D. (Listed for completeness.)

---

## Cross-component finding

The two failed/partial components (V2 and V3) share a single root cause: **a tool built for one input domain produces uninformative output when applied to an adjacent-but-different input domain.**

- V2: nomic-embed-text built for general-purpose semantic retrieval; applied to rubric-criterion vocabulary (a tight sub-domain) → discriminative resolution drops from "high" to "low".
- V3: hermeneutic regex built for AI-output risk patterns; applied to rubric-criterion text → no patterns fire because the input is a different content class.

For langquant: when wrapping an existing tool, the I/O quarantine boundary is also a domain-fit boundary. A clean wrapper around a tool whose input domain doesn't match the wrapped use-case will produce results that are mechanically valid (no exceptions thrown) but semantically null. The bias-substitution rule (Constraint 2 in this mission) needs to be expanded: not just "are we trading judge bias for embedding bias?" but also "is our wrapped tool even calibrated for the input we're feeding it?"

This is a Mission C R&D yield, not a Mission C failure. The pre-registration's halt-and-document mechanism is what surfaced it.
