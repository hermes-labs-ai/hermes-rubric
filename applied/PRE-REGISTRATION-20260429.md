# Pre-Registration — META-RUBRIC v1 Mission B + Mission C

**Date sealed:** 2026-04-29 10:15 PT
**Author:** Rolando Bosch, Hermes Labs (LPCI Innovations LLC)
**Binding metacognitive framework:** `applied/METACOGNITIVE-FRAMEWORK-20260429.md`
**Sealed before any mission execution.** Retrofit detection: any change to this document after Mission B or Mission C begins must be logged with timestamp + rationale; modifications constitute pre-registration violation.

---

## Mission B — META-RUBRIC v1 Paper Hardening

**Hypothesis (H1-B):** removing §6 (Adaptive Implementation) and §7 (Recursive Audit Results) from `paper.md` and `paper.tex`, applying 5 structural fixes from `adversarial-skeptic-verdict.md`, adding 5 missing citations with verified arxiv abstracts, and re-running adversarial Opus review will produce a paper with adversarial verdict ≤30% FIX-BEFORE-SHIP or PUBLISH-AS-IS.

**Null hypothesis (H0-B):** the same operations leave the paper at >30% FIX-BEFORE-SHIP because the structural critiques (n=7 calibration, MR-2 unfalsifiability, §4 instrument-window contradiction) are not fully addressable by the planned scope.

**Pre-registered success rubric:**

| Criterion | Pass condition | Weight |
|---|---|---|
| §6 / §7 cleanly cut, no orphan references in §1-§5 or abstract | grep on full paper.md finds zero "Adaptive Implementation", "Recursive Audit Results", "meta-tool" claim references in §1-§5 | 3 |
| §4 instrument-window paragraph reframed | no internal contradiction (claims protections worked AND scorer was unanchored on unseen content) | 3 |
| MR-2 in-paper falsification condition | specific testable claim in §3.2, not just deferred to follow-up | 3 |
| 5 missing citations added with verification | each has bib entry + arxiv abstract excerpt in `RELATED-WORK-VERIFICATION.md` + inline cite at the specific sentence it supports (per Phantom Limb constraint) | 2 |
| "Smallest set sufficient" → "minimum set we have used" | already applied 2026-04-29 02:00 PT, verify still in place | 1 |
| Recompile clean | 0 undefined refs, 0 LaTeX errors | 2 |
| Adversarial Opus CLI verdict | ≤30% FIX-BEFORE-SHIP OR PUBLISH-AS-IS, on the recompiled paper | 3 |
| Phantom Limb check passed | abstract + intro do not rely on removed §6/§7 content; preceding/following paragraphs of cuts have sound transitions | 2 |

**Floor: 14/19. Below floor: report to Roli, do not auto-ship.**

**Phantom Limb specific verifications (per Constraint 3):**
- Read paper.md lines 11-26 (abstract + intro through §1) verbatim. List any sentence that references the meta-tool empirically. Either rewrite or remove.
- Read paper.md sections immediately before and after the cut points. Confirm transitions read coherently.
- For each new citation: paste the specific sentence the cite is attached to + the arxiv abstract excerpt; verify the abstract supports the sentence.

**Banned actions:** any GitHub push, any modification outside hermes-rubric or hermes-content/papers/meta-rubric/, any modification to ~/.claude/, any commit on behalf of Mission C.

**Halt triggers:** test failure, banned action attempted, scratchpad failure (unresolved verification scratchpad), 90 min without commit, 5 commits done.

---

## Mission C — Hermes-Native Pilot Validation (Phase 1)

**Hypothesis (H1-C):** at least 3 of 4 Hermes-native components validate as deterministic alternatives to JSS-style same-family LLM-judge methodology for measuring rubric synthesis stability.

**Null hypothesis (H0-C):** ≥2 components fail validation; the Hermes-native rebuild is not viable as currently scoped; document failed components as R&D output for langquant project.

**Pre-registered Phase 1 success rubric:**

| Component | Pass criterion | Weight |
|---|---|---|
| **V1 `--rubric-file` flag** | Wrapper accepts JSON rubric file path, skips `synthesize()` call, scoring stage runs to completion. Existing 21/21 tests still pass. | 3 |
| **V2 Hungarian-matched cosine on embeddings** | Same-input rubric pairs (3 same-input runs) score ≥0.7 cosine; different-input pairs score below the random-permutation null threshold; threshold derivation (per Constraint 2) is mathematically justified, not artificially low/perfect. | 3 |
| **V3 hermeneutic Stage 1 pre-filter** | Regex gate runs without exception on 7 dim descriptions from one rubric. Differentiated output: at least one dim flagged AND at least one not flagged (gates differentiate, not collapse to all-pass or all-fail). | 2 |
| **V4 hermes-seal local pre-registration** | This file (`PRE-REGISTRATION-20260429.md`) is sealable via local `hermes-seal` invocation. Seal verification produces exit-0. | 2 |

**Floor for Phase 2 commitment: 8/10 with no component scoring 0. Below floor: halt at Phase 1, document each failed component as R&D output for langquant project; do NOT proceed to Phase 2.**

**Embedding & Math Justification (per Constraint 2) — Mission C MUST document:**
1. Which embedding model is used. Justification for choice (semantic granularity match for rubric-dimension descriptions).
2. Random-permutation null methodology: how dim-description tokens are permuted, sample size, expected null distribution shape.
3. Threshold derivation with mathematical logic. Sanity check: threshold > random-baseline mean by ≥2 standard deviations.
4. If threshold is suspiciously low or suspiciously perfect (>0.95 or <0.3), HALT and flag — embedding-space bias substituted for LLM-judge bias.

**Banned actions:** any GitHub push, any modification outside hermes-rubric/, any paper edits (Mission B's lane), any modification to ~/.claude/, any spawn of further autonomous agents.

**Halt triggers:** any V-component fails its sanity check, scratchpad failure, banned action attempted, 90 min without commit on Phase 1.

---

## Coordination — sync points

1. **Mission B HOLDS** any §6/§7 cut until Mission C Phase 1 verdict is in.
2. **If Mission C Phase 1 succeeds (8/10+):** Mission B and Mission C are jointly evaluated by Roli. Option C-full path becomes possible (keep §6/§7, reframe Hermes-native).
3. **If Mission C Phase 1 fails (<8/10 or any V=0):** Mission B proceeds with cuts. Mission C halts at Phase 1, R&D output documented.
4. **HAL coordinator does not auto-merge.** Roli oversees any integration.

---

## Report back triggers (per Constraint 5)

HAL coordinator reports to Roli ONLY when:
- Phase 1 of Mission C is complete (verdict in)
- Critical halt-trigger tripped on either mission
- Scratchpad failure on either mission

No status updates between these events.

---

## Retrofit detection

This pre-registration is committed BEFORE missions spawn. Modifications after spawn must:
- Be timestamped
- Include rationale
- Be flagged in HAL's report-back
- NOT change rubric thresholds or hypothesis directionality

Per Constraint 4 (I/O Quarantine), neither mission modifies this file. Only HAL coordinator may amend with explicit retrofit-flag.
