# META-RUBRIC — frozen spec v1.0

The rubric that rubric-generators are scored against. Dimensions derived empirically from the failure-mode-taxonomy.md. Each dimension cites the failure modes that motivated it.

Built: 2026-04-23. Frozen for hermes-rubric v0.1.

## Provenance

This is an opinionated framework, not a discovered law. The full chain:

```
1,892 experiment records (research-corpus/epistemic + ai-behavior + scaffold)
+ named post-mortem incidents (hermes-handbook/)
        ↓ qualitative coding pass (LLM-assisted, manually validated against cited artifacts)
24 named failure modes (failure-mode-taxonomy.md — each cites its source artifact)
        ↓ editorial selection: which FMs map to a defensible meta-eval criterion
7 META-RUBRIC dimensions (each cites the FMs that motivate it)
```

Every FM in the taxonomy points to a specific source artifact. Every META-RUBRIC dimension points to the FMs it answers. The taxonomy is internally falsifiable (any cited artifact can be inspected by the maintainer); some artifact paths refer to private research-corpus files, so external readers must trust the citation chain rather than verify it directly. Future versions may release a public subset of the underlying experiment records to make the taxonomy externally verifiable too.

---

## How to use this

Apply the META-RUBRIC when evaluating the quality of a synthesized rubric (Stage 1 output) before trusting its Stage 3 scores. A rubric that fails the META-RUBRIC will produce scores that cannot be trusted.

**Score each dimension 0-10. Weight as specified. Aggregate = weighted average.**

---

## Dimensions

### MR-1: Domain Specificity (weight 3)
**What it measures:** The synthesized rubric's dimensions are specific to the stated (intent, target-type) pair. Generic dimensions that could apply to any document type score poorly.

**Evidence instructions:** Look at each dimension's name and evidence_instructions. If they would apply unchanged to a paper, an email, a repo, and a tool spec without modification, they are too generic. Count how many dimensions have domain-specific evidence_instructions.

**Pass:** 80%+ of dimensions have evidence_instructions that name domain-specific artifacts (e.g., "Look for test assertions in tests/ directory" not "look for quality indicators").

**Fail:** Dimensions like "Clarity", "Organization", "Usefulness" with no evidence_instructions that name specific files, section types, or observable behaviors.

**Motivated by:** FM-19 (Dimension boilerplate), FM-20 (Attractor collapse — generic rubrics collapse to the same scores regardless of target)

---

### MR-2: Discrimination Power (weight 3)
**What it measures:** Given two targets of known different quality, the rubric produces detectably different scores. A rubric that scores everything 6-8 regardless of quality has zero discrimination power.

**Evidence instructions:** Mentally simulate applying the rubric to (a) an exemplary target and (b) a weak target. Does each dimension produce a different score? If yes, discrimination power is high. Also check: are any dimensions worded such that almost any target would score 7-8 by default?

**Pass:** At least one dimension would clearly score 2-4 for a weak target and 8-10 for an exemplary target on the same criterion.

**Fail:** All dimensions would score 6-8 for any reasonable target; no dimension cleanly separates weak from strong.

**Motivated by:** FM-06 (Fluency inflation — rubrics that don't discriminate reward surface polish), FM-19 (Boilerplate dimensions are non-discriminating by construction)

---

### MR-3: Evidence Anchoring (weight 3)
**What it measures:** Every rubric dimension specifies WHERE to look and WHAT to look for — not just WHAT to assess. Each dimension's evidence_instructions names specific artifact types, file locations, or observable behaviors.

**Evidence instructions:** Read each dimension's evidence_instructions. Does it name WHERE to look? (e.g., "the tests/ directory", "the limitations section", "the CLAIMS.md file") Does it say WHAT counts as evidence? (e.g., "a file:line pointer", "an n= value", "a named dataset")

**Pass:** 100% of dimensions have evidence_instructions that a human could execute mechanically — find X in Y location.

**Fail:** evidence_instructions says "assess quality of..." or "evaluate whether..." without naming where evidence would be found.

**Motivated by:** FM-01 (Numeric retrofit — no evidence_instructions means scores can be invented), FM-15 (Silent confidence — no evidence anchor forces fabrication)

---

### MR-4: Hedge Honesty (weight 2)
**What it measures:** The rubric correctly identifies which dimensions may have thin evidence for the target type, and marks them with hedge=true proactively rather than waiting for the evidence stage to discover this.

**Evidence instructions:** Check: does the rubric have any dimensions marked hedge=true? Are they appropriate (dimensions where evidence would typically be indirect or missing for this target type)? Or are they all hedge=false (over-confident)?

**Pass:** At least one dimension carries hedge=true if the target type makes any dimension structurally difficult to evidence (e.g., "reproducibility" for a paper where the code is not included).

**Fail:** All hedge=false for a target type where at least some dimensions are inherently harder to evidence. Over-confident rubric signals the generator didn't think about evidence availability.

**Motivated by:** FM-14 (Performative hedging), FM-15 (Silent confidence on thin evidence), FM-24 (Hedge averaging — hedge must be declared upfront, not discovered after averaging)

---

### MR-5: Adversarial Robustness (weight 2)
**What it measures:** The rubric cannot be gamed by surface manipulation — fluency, vocabulary choice, volume of text, or deontic theater. Dimensions assess substance observables, not style signals.

**Evidence instructions:** For each dimension, ask: "Could a bad actor score 8+ by just rewriting the prose, adding more text, or adding compliance-sounding language?" If yes, the dimension is gameable. Dimensions should require citing specific measured values, named artifacts, or structural elements that cannot be fabricated cheaply.

**Pass:** 0 dimensions are purely style-based (e.g., no dimension scores "tone" or "professionalism" as a primary criterion without tying it to a specific observable output).

**Fail:** Any dimension that would score higher simply because the text is longer, uses more technical vocabulary, or avoids informal language.

**Motivated by:** FM-06 (Fluency inflation), FM-07 (Marketing verb injection), FM-10 (Compliance theater), FM-12 (Semantic constraint evasion)

---

### MR-6: Scope Calibration (weight 2)
**What it measures:** Each rubric dimension is scoped to what the evidence can actually show. Dimensions don't overreach (claiming to measure X when only Y is observable). No dimension extrapolates from single-condition data to universal claims.

**Evidence instructions:** For each dimension, ask: does its description match what its evidence_instructions can actually find? If evidence_instructions says "look for n= values" but description says "assess whether the experiment generalizes universally", that's scope overreach.

**Pass:** Dimension description and evidence_instructions match in scope. No dimension claims to measure something that requires data not present in the target.

**Fail:** Dimension claims to assess "production readiness" from a README-only target, or claims to measure "generalizability" from a single-condition experiment.

**Motivated by:** FM-09 (Universal quantifier injection — dimensions shouldn't score universal claims from local evidence), FM-22 (Evidence scope creep — single-condition evidence cannot support multi-condition claims)

---

### MR-7: Reproducibility (weight 1)
**What it measures:** The same (intent, context_summary, target_type) should produce similar rubrics across runs. This is a property of the rubric-generator, not the rubric content. Low reproducibility means scores will differ arbitrarily across runs.

**Evidence instructions:** Run the synthesis stage 3 times on identical inputs. Compare: do the same dimension categories appear? Are the names recognizably similar? Is the weight ordering consistent? Variance tolerance: ±1 dimension, names within the same semantic cluster.

**Pass:** 3 runs produce rubrics with 80%+ overlapping dimension categories and consistent weight ordering for top-2 dimensions.

**Fail:** Run 1 produces "Evidence Grounding, Statistical Honesty, Scope" and Run 3 produces "Readability, Completeness, Tone" — fundamentally different frameworks for the same input.

**Motivated by:** FM-18 (Non-reproducible scoring — the whole chain must be stable, starting at synthesis)

---

## Scoring the META-RUBRIC itself

| Dimension | Weight |
|---|---|
| MR-1 Domain Specificity | 3 |
| MR-2 Discrimination Power | 3 |
| MR-3 Evidence Anchoring | 3 |
| MR-4 Hedge Honesty | 2 |
| MR-5 Adversarial Robustness | 2 |
| MR-6 Scope Calibration | 2 |
| MR-7 Reproducibility | 1 |
| **Total weight** | **16** |

**Aggregate = sum(score_i × weight_i) / 16**

**Rubric passes META-RUBRIC at 7.0/10 aggregate with no dimension below 5.**

---

## What the META-RUBRIC does NOT measure

- Whether the rubric's final scores are correct (that depends on evidence quality + target)
- Whether the target is good (that is Stage 3's job)
- Whether the rubric generator's prompts are optimally worded
- Subjective quality of dimension names or descriptions

The META-RUBRIC measures structural soundness of the generated rubric. A structurally sound rubric can still produce wrong scores if evidence collection fails. A structurally broken rubric will produce wrong scores even with good evidence.
