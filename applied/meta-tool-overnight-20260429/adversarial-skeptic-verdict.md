# Adversarial Skeptic Review — VERDICT: FIX BEFORE SHIP (70%)

**Reviewer:** fresh-context Opus via claude CLI, no prior conversation context
**Time:** 2026-04-29 02:00 PT
**Distribution:** 70% FIX-BEFORE-SHIP / 5% PUBLISH-AS-IS / 25% DO-NOT-PUBLISH

## Primary concern (verbatim)

> The paper proposes a frozen normative rubric-of-rubrics with a 7.0 pass-floor while every empirical demonstration the paper offers (self-grade 6.8, paper runs 6.5/6.9, meta-tool runs 5.5/4.8, self-on-paper 4.4–4.6) lands below that floor — and each failure is reframed as evidence the framework is working, which is special pleading at the level of the central claim.

## Secondary concerns (verbatim, prioritized)

1. **Unfalsifiable-by-construction.** Every below-floor outcome is interpreted as the instrument "doing its job." There is no specified outcome inside the paper's own runs that would count as failure of the META-RUBRIC. §9 names a future falsification floor, but v1 reports zero passing runs.

2. **n=7 calibration, 3 provisional, no inter-rater, single backend, single synthesizer family.** The paper concedes but still presents seven dimensions as "the smallest set sufficient" — a sufficiency claim that requires evidence not in this paper.

3. **MR-2 (Discrimination Power) circularity.** §3.2 invokes Albert's Münchhausen trilemma to "plant a flag." Citing Albert does not discharge the methodological burden; it relabels it. The load-bearing axiom is untested.

4. **Internal contradiction on §4 instrument-truncation.** Paper claims (a) protections correctly hedged, AND (b) "misleadingly low … on a paper the protections themselves think is fine." If the instrument cannot see the target, the rubric has no basis to "think" anything; positive rationales on unseen content suggest the scorer was not in fact evidence-anchored. Undercuts MR-3.

5. **§7 is a negative result dressed as confirmation.** Meta-tool scored 0.7 LOWER than original. `prompt_template_id` admitted unwired. +2 heuristic admitted as irrecoverable score loss. v1 of the meta-tool does not yet do the thing §6 claims it does.

6. **Reproducibility gap on headline 6.8 self-grade.** Pinned to one JSON receipt at SHA e4d96c1 and explicitly cannot be re-derived because synthesis is non-deterministic.

7. **Private-corpus citations.** Central rhetorical move ("each dimension grounded in a named failure mode from a corpus") not externally checkable for the rubric-specific extension beyond the 1,461 prior corpus.

8. **Literature gaps.** Prometheus / Prometheus-2, PandaLM, JudgeLM, FLASK, BiGGen-Bench, Bavaresco et al., Stureborg et al. directly adjacent to "auditing the rubric/judge" — uncited.

9. **"Epistemic engineering"** coined and promoted in §9 without prior-art search; the term may be in active use elsewhere.

10. **Weights (3/3/3/2/2/2/1) and 7.0/min-5 thresholds** presented as load-bearing but derivation is editorial; no sensitivity analysis.

## Required fixes (verbatim, prioritized)

1. §1/§9: drop "smallest set … sufficient" or restate as "minimum set we have used"; sufficiency is unproven.
2. §3.2: state an in-paper falsification condition for the foundationalist axiom, not just for the follow-up. As written, MR-2 is unfalsifiable in v1.
3. §4 + §6: explicitly label both as negative/null results for v1 (every reported aggregate is below the paper's own pass floor) and remove the "instrument doing its job" framing where it substitutes for evidence.
4. §7: retitle as a null result on cap-removal; either wire `prompt_template_id` or remove the meta-tool from the contribution list and move to "future work."
5. §2 / Table 1: add Prometheus-2, FLASK, JudgeLM, PandaLM, BiGGen-Bench; correct the implication that no prior framework does per-aspect rubric audit.
6. §4.3 or wherever: either run inter-rater on the n=7 set or remove "calibration" framing; current set is illustrative, not calibrating.
7. Add a single-page appendix listing the 24 FM-IDs with public-only descriptions so the FM-* citations in §3 are externally checkable without the private corpus.
8. Remove the duplicated author/affiliation block at the top.

## Triage

**MECHANICAL fixes (can be done autonomously, low risk):**
- Fix 1: rephrase "smallest set sufficient" — find/replace + voice check
- Fix 8: remove duplicated author block — verify in source, delete duplicate
- Add citations (Prometheus-2, FLASK, JudgeLM, PandaLM, BiGGen-Bench) — fetch arxiv abstracts, add to bibliography, insert refs in §2
- Fix 7: write FM-* appendix from public taxonomy file at `~/Documents/projects/hermes-rubric/calibration/failure-mode-taxonomy.md`

**JUDGMENT-HEAVY fixes (require Roli's morning eyes):**
- Fix 2: write the in-paper falsification condition for MR-2 (philosophical claim phrasing — Roli's voice required)
- Fix 3: reframe §4 / §6 as null-result narratives (load-bearing change to the paper's central thesis — Roli's call)
- Fix 4: decide whether to wire `prompt_template_id` (engineering work, half-session) OR remove meta-tool from contributions and move to future work (load-bearing scope decision)
- Fix 6: decide whether to run inter-rater on n=7 (real work, multi-day) OR remove "calibration" framing and replace with "illustrative"
- "Epistemic engineering" prior-art search (decision based on what's found)

## Honest verdict

**Paper is NOT ready for upload tonight.** The adversarial review surfaced load-bearing structural critiques that require Roli's voice + scope judgment to resolve. v1 in current state would ship with the FIX-BEFORE-SHIP verdict's primary concern un-addressed: the framework is unfalsifiable-by-construction in this paper's own runs.

**What to do at morning:**
1. Read this verdict file in full
2. Decide on the four judgment-heavy fixes above
3. Apply mechanical fixes 1, 7, 8 + citation additions (15-30 min each)
4. Re-run adversarial review after revisions; iterate until verdict shifts to PUBLISH-AS-IS or FIX-BEFORE-SHIP <30%
5. Then upload

The mission's claim of "wake to working flagship" was overstated. The build IS done; the paper is COMPILED; but the paper is NOT skeptic-pass-ready. Honest framing requires saying so.
