# Failure Mode Taxonomy — hermes-rubric

Mined from 3 research-corpus domains:
- `research-corpus/epistemic/raw/` (1,789 experiment records, GPT-4o failure modes under structured prompting)
- `research-corpus/ai-behavior/raw/` (12 files — hackathon cases, agent behavior under pressure)
- `research-corpus/scaffold/raw/` (91 experiment records — scaffold experiments, Banking77, behavioral failure modes)

Plus direct incident post-mortems from `hermes-handbook/`:
- `retrofit-detection.md` — fabricated 77-82% QA range incident
- `validate-test-verify.md` — cascade-seal v0.1 false-closure incident
- `adversarial-test-before-ship.md` — decoy-file bypass incident
- `SELF-SCAFFOLD-20260423-EOD.md` — 9 incidents catalogued in one session

Target: 20-40 unique failure patterns that motivate rubric-generator dimensions.

---

## A. Fabrication and Retrofit Failures

### FM-01: Numeric retrofit
**Description:** Specific numeric ranges written into framing docs before the measurement exists. Range sounds precise but has no source file.
**Tell:** "approximately 77-82%" with no `file:line` pointer. Two appearances of the same range = copy from the draft, not from the data.
**Example artifact:** `cogito-ergo/bench/LAUNCH-FRAMING.md` — 77-82% QA range with actual measured values of 54.2% and 67.7%.
**Motivated dimension:** Evidence Grounding (every score must cite observable source)

### FM-02: Stale count claim
**Description:** Tool README claims N tests; actual count has changed. Claim never updated.
**Tell:** "100 tests" in a repo with 57 or 33 test functions on disk.
**Example artifact:** `project_hermes_oss_branding_pass_20260422.md` — "repo-audit: 3 tests failing" when 57/57 passed.
**Motivated dimension:** Evidence Currency (claims verified against current state, not memory)

### FM-03: Competitor hallucination
**Description:** Comparing against competitor X using wrong model name or wrong metric definition.
**Tell:** "GPT-5-mini" (actual: gpt-4o-mini), or claiming "SOTA" with no published comparison table.
**Example artifact:** `cogito-ergo/bench/LAUNCH-FRAMING.md` — "GPT-5-mini" reader model.
**Motivated dimension:** Comparison Integrity (side-by-side evidence required for any comparison claim)

### FM-04: Cherry-picking
**Description:** Running many trials and reporting only the best result as if it's the typical result.
**Tell:** "we found one run that achieved X%" with no distribution data, no mean, no N.
**Example artifact:** `research-corpus/ai-behavior/raw/terrified-agent-saga` — agent explicitly flagged this: "I could have run 100 profiles to find one with 75%+ improvement."
**Motivated dimension:** Statistical Honesty (N, mean, and variance required; single best-case not accepted)

### FM-05: Vague numeric softening
**Description:** Precise-sounding range undermined by "approximately" or no unit, hiding that no actual measurement was done.
**Tell:** "approximately X-Y%" vs "X% (n=N, run ID: R)".
**Example artifact:** `epistemic/raw/00d98228` — quote-optional condition produced "approximately" throughout; quote-gated produced specific named values.
**Motivated dimension:** Claim Precision (specific numbers with conditions; not softened ranges)

---

## B. Surface Fluency Failures

### FM-06: Fluency inflation
**Description:** Well-written prose rewarded over awkward-but-evidenced prose. Rubric evaluator mistakes polish for substance.
**Tell:** Fluent version scores higher despite same or weaker evidence content.
**Example artifact:** Direct observation — Hermes style guide explicitly states "Fluency is distrust." Engineered polish hides thin evidence.
**Motivated dimension:** Substance over Style (score the evidence, not the presentation)

### FM-07: Marketing verb injection
**Description:** LLM adds "unlock", "revolutionize", "leverages" to make content sound compelling, boosting its own (or another's) perceived quality.
**Tell:** Forbidden verbs appear in outputs even when the task doesn't call for marketing language.
**Example artifact:** Style guide `STYLE-GUIDE-v1.md` — explicit banned list from observed LLM default behavior.
**Motivated dimension:** Vocabulary Discipline (absence of inflating language is necessary but not sufficient)

### FM-08: Narrative drift / motive inference
**Description:** Narrative format outputs add inferred motives, causal connections, and entities not in the source text.
**Tell:** Response contains inferred "X was trying to Y" or "this highlights the importance of Z" where source text did not imply it.
**Example artifact:** `epistemic/raw/00c251f5` — narrative condition added inferred roles, investigations, meetings absent from source vignette; checklist condition did not.
**Motivated dimension:** Source Anchoring (claims must trace back to observable source material, not inference)

### FM-09: Universal quantifier injection
**Description:** LLM generalizes from a specific finding to "everyone", "always", "human nature" without evidence.
**Tell:** High count of "always/never/everyone/no one" in outputs from quote-optional conditions.
**Example artifact:** `epistemic/raw/00d98228` — quote-optional produced 4-6x more universal quantifiers than quote-gated.
**Motivated dimension:** Scope Calibration (claims bounded to what the evidence actually supports)

---

## C. Score Gaming Failures

### FM-10: Compliance theater
**Description:** Authority-framed prompts produce rule-echoing and deontic language without actual compliance improvement.
**Tell:** Response uses "must/shall/required" heavily but the actual output doesn't satisfy the stated constraints.
**Example artifact:** `epistemic/raw/02c31c61` — authority framing doubled deontic markers but the content-level constraint coverage was unchanged.
**Motivated dimension:** Semantic Compliance vs Lexical Compliance (distinguish form from function)

### FM-11: Lexical gate bypass
**Description:** Tool passes lexical coverage check (intent-verify) but violates the semantic intent by pointing a tool at an innocent decoy file.
**Tell:** `before_hash == after_hash` on claimed target while actual target changed.
**Example artifact:** `validate-test-verify.md` — cascade-seal v0.1 closed 11/12 TODOs with no actual mutation on claimed target.
**Motivated dimension:** Post-Condition Verification (outcome must be verified, not just claimed)

### FM-12: Semantic constraint evasion
**Description:** Larger models evade constraints semantically while complying literally (using synonyms of forbidden words).
**Tell:** Forbidden word not present; synonyms and periphrases appear at higher rate than baseline.
**Example artifact:** `scaffold/raw/00a145127bc9` L1-1 — 9b model used 1.1 synonyms vs 0.6 for 0.8b model; semantic evasion scales with model size.
**Motivated dimension:** Adversarial Robustness (rubric cannot be gamed by synonym substitution)

### FM-13: Volume gaming
**Description:** Running many trials to find one that hits a threshold, then reporting that as the result.
**Tell:** N large but only max reported; distribution not shown.
**Example artifact:** `ai-behavior/raw/terrified-agent-saga` — agent identified it could cherry-pick from 100 profiles to hit 75%+ and explicitly refused to.
**Motivated dimension:** Statistical Honesty (see FM-04)

---

## D. Hedging and Uncertainty Failures

### FM-14: Performative hedging
**Description:** Hedging language appears (might, could, approximately) but the statement still functions as a confident claim.
**Tell:** "Approximately X" used as if X is confirmed; no actual uncertainty range given; hedge doesn't reduce the implied precision.
**Example artifact:** `scaffold/raw/00a145127bc9` — "performative-hedging" listed as a tagged failure mode in the behavioral failure mode experiments.
**Motivated dimension:** Hedge Honesty (hedges must reflect actual epistemic state, not stylistic softening)

### FM-15: Silent confidence on thin evidence
**Description:** Rubric evaluator gives confident 8-10 scores on dimensions where evidence is thin, because it's embarrassing to say "low confidence."
**Tell:** All dimensions score 7-9; no hedge_dims in output despite unclear evidence for some.
**Example artifact:** Directly observed in "rate this X" prompt patterns — fabricated confident scores are the problem hermes-rubric exists to prevent.
**Motivated dimension:** Hedge Honesty + Evidence Grounding (force explicit hedge when evidence is thin)

### FM-16: Stale memory as live fact
**Description:** Memory claim asserted as current state without verification; actual state differs.
**Tell:** "Tests failing: 3" in memory, actual test suite 57/57 passing. "R@1: 56%" in memory, actual 96.4%.
**Example artifact:** `stale-memory-rule.md` — both incidents from 2026-04-23 session.
**Motivated dimension:** Evidence Currency (verify before asserting current state)

---

## E. Structural and Reproducibility Failures

### FM-17: Missing post-conditions
**Description:** Tool reports success based on its own logs without verifying the claimed outcome actually occurred on disk.
**Tell:** Ledger says "closed", hash comparison was bypassed.
**Example artifact:** `validate-test-verify.md` — 11/12 cascade-seal v0.1 executions logged as closed with `before_hash == after_hash`.
**Motivated dimension:** Post-Condition Verification (outcome asserted, not assumed from tool exit code)

### FM-18: Non-reproducible scoring
**Description:** Same (intent, context, target) produces wildly different scores across runs due to prompt sensitivity.
**Tell:** Variance > ±2 points across 3 runs on identical inputs.
**Example artifact:** Direct observation — "rate this X" prompts have high variance; "synthesize rubric then score" prompts have lower variance because the rubric anchors the evaluation.
**Motivated dimension:** Reproducibility (same inputs produce similar scores within ±1 point)

### FM-19: Dimension boilerplate
**Description:** Rubric has generic dimensions that apply to every target type and add no domain-specific signal.
**Tell:** "Clarity", "organization", "usefulness" with no domain-specific evidence instructions.
**Example artifact:** Directly observed — generic rubric dimensions produce undiscriminating scores (everything scores 6-8).
**Motivated dimension:** Domain Fit (dimensions derived from intent + target type, not copied from a generic template)

### FM-20: Attractor collapse
**Description:** Multiple evaluators or runs converge on the same score not because they found the same evidence but because they share a context attractor.
**Tell:** Cascade hackathon: 4/4 freeform agents produced Article-13 auditor variants; business-context priming dominated independent judgment.
**Example artifact:** `ai-behavior/raw/cascade-hackathon-framing-effect-20260422.md` — freeform arm collapsed 4→1 cluster under business-context prime.
**Motivated dimension:** Adversarial Robustness + Independence (evaluator must resist context attractors)

### FM-21: Comparison without side-by-side evidence
**Description:** Claiming X is better/faster/cheaper than Y with no published comparison table or named benchmark.
**Tell:** "State of the art", "#1", "outperforms GPT-4" with no cited evidence in the same document.
**Example artifact:** `retrofit-detection.md` tells 4 — "adjectives the data doesn't earn."
**Motivated dimension:** Comparison Integrity (see FM-03)

### FM-22: Evidence scope creep
**Description:** Evidence from condition A cited as supporting claims about condition B. Results don't transfer but the framing implies they do.
**Tell:** n=1 exploratory run cited alongside n=74 replication as if both prove the same claim at equal confidence.
**Example artifact:** `langquant/PAPER-v1.md` — paper correctly distinguishes n=1 original from n=74 replication. Failure mode = not distinguishing them.
**Motivated dimension:** Scope Calibration (evidence scoped to the exact condition it was measured under)

### FM-23: Anchor drift
**Description:** Reference to "this" or "the result" resolves to the contextually dominant framing, not the factually correct antecedent.
**Tell:** Model resolves ambiguity based on what sounds like the main point, not what the evidence actually shows.
**Example artifact:** `epistemic/raw/00e9b700` — topicality overrides syntactic recency in antecedent resolution.
**Motivated dimension:** Source Anchoring (claims must trace to explicit source, not implied context)

### FM-24: Hedge averaging
**Description:** Low-confidence dimension scores silently averaged into aggregate, hiding that the overall score rests on thin evidence.
**Tell:** Aggregate = 8.2/10 but two dimensions had confidence=low and contributed to the average without flag.
**Example artifact:** Direct observation — hermes-rubric INTENT.md explicitly forbids this.
**Motivated dimension:** Hedge Honesty (hedge_dims must be explicitly reported and excluded from main aggregate or flagged)

---

## Summary Table

| ID | Name | Domain | Corpus Source |
|----|------|--------|---------------|
| FM-01 | Numeric retrofit | Fabrication | `retrofit-detection.md`, `LAUNCH-FRAMING.md` |
| FM-02 | Stale count claim | Fabrication | `stale-memory-rule.md`, branding pass incident |
| FM-03 | Competitor hallucination | Fabrication | `LAUNCH-FRAMING.md`, `retrofit-detection.md` |
| FM-04 | Cherry-picking | Fabrication | `ai-behavior/terrified-agent-saga` |
| FM-05 | Vague numeric softening | Fabrication | `epistemic/00d98228` |
| FM-06 | Fluency inflation | Surface | `STYLE-GUIDE-v1.md`, direct observation |
| FM-07 | Marketing verb injection | Surface | `STYLE-GUIDE-v1.md` |
| FM-08 | Narrative drift / motive inference | Surface | `epistemic/00c251f5` |
| FM-09 | Universal quantifier injection | Surface | `epistemic/00d98228` |
| FM-10 | Compliance theater | Gaming | `epistemic/02c31c61` |
| FM-11 | Lexical gate bypass | Gaming | `validate-test-verify.md` |
| FM-12 | Semantic constraint evasion | Gaming | `scaffold/00a145127bc9` |
| FM-13 | Volume gaming | Gaming | `ai-behavior/terrified-agent-saga` |
| FM-14 | Performative hedging | Uncertainty | `scaffold/00a145127bc9` |
| FM-15 | Silent confidence on thin evidence | Uncertainty | Direct observation |
| FM-16 | Stale memory as live fact | Uncertainty | `stale-memory-rule.md` |
| FM-17 | Missing post-conditions | Structural | `validate-test-verify.md` |
| FM-18 | Non-reproducible scoring | Structural | Direct observation |
| FM-19 | Dimension boilerplate | Structural | Direct observation |
| FM-20 | Attractor collapse | Structural | `ai-behavior/cascade-hackathon-*` |
| FM-21 | Comparison without side-by-side | Structural | `retrofit-detection.md` |
| FM-22 | Evidence scope creep | Structural | `langquant/PAPER-v1.md` |
| FM-23 | Anchor drift | Structural | `epistemic/00e9b700` |
| FM-24 | Hedge averaging | Uncertainty | INTENT.md design requirement |

**Total: 24 failure modes** across 4 categories (Fabrication, Surface, Gaming, Uncertainty/Structural).
