# V3 Receipt — hermeneutic Stage 1 Pre-Filter on Rubric-Dim Descriptions

**Component:** Mission C V3.
**Status:** FAIL on pre-registration "differentiated output" criterion. Honest disclosure of mechanism + domain mismatch.
**Date:** 2026-04-29.

---

## What V3 was supposed to do

Run `hermeneutic` Stage 1 (regex gate, zero-LLM) on the 7 dim descriptions from one V2-saved rubric. Pre-registration pass criterion:

> Regex gate runs without exception on 7 dim descriptions from one rubric. Differentiated output: at least one dim flagged AND at least one not flagged (gates differentiate, not collapse to all-pass or all-fail).

---

## Source: V2-rubrics/run-1.json

7 dimensions, all sourced from a synthesizer-produced rubric for the META-RUBRIC paper:

| dim_id | name |
|---|---|
| dim_1 | README Citation Ratio |
| dim_2 | Prose-Grounding Justification |
| dim_3 | Source Class Diversity |
| dim_4 | Self-Marketing Citation Disclosure |
| dim_5 | Configuration Transparency |
| dim_6 | Test Evidence Linkage |
| dim_7 | Code Example Completeness |

Each dim's text was concatenated as `name. description evidence_instructions` and run through `hermeneutic gate --draft <file>`.

---

## Results

| dim_id | gate verdict | severity | rules fired |
|---|---|---|---|
| dim_1 | PASS | — | none |
| dim_2 | PASS | — | none |
| dim_3 | PASS | — | none |
| dim_4 | PASS | — | none |
| dim_5 | PASS | — | none |
| dim_6 | PASS | — | none |
| dim_7 | PASS | — | none |

**All-pass collapse. Pre-registration "differentiated output" criterion: FAIL.**

---

## Why this happened — the mechanism

`hermeneutic`'s Stage 1 regex patterns (in `hermeneutic/gates/regex.py`) are calibrated to detect risk patterns in **AI assistant draft output**, not in rubric dim descriptions. Sample patterns:

- `completion_with_number` — "shipped 95%", "all 21 tests passed"
- `subagent_passthrough` — "the subagent confirmed..."
- `unhedged_certainty` — "definitely", "absolutely", "always"
- `fluent_summary_no_evidence` — "comprehensive", "production-ready", "robust"
- `scope_expansion` — "also", "while I'm at it", "bonus"

These are signals of *AI overclaiming behavior*. Rubric dim descriptions, by construction, are domain-neutral evaluation criteria authored by a synthesizer prompt that explicitly demands specific, observable measurements. They don't contain "definitely" or "shipped" or completion claims — they are the evaluation framework, not the evaluation output.

**Sanity check that the gate is not broken:**

```
$ echo "Comprehensive Coverage. The system definitely measures all aspects with production-ready scoring." \
    | hermeneutic gate
RISK — highest severity: med
  [med] unhedged_certainty: 'definitely'
  [low] fluent_summary_no_evidence: 'Comprehensive'
  [low] fluent_summary_no_evidence: 'production-ready'
```

Gate fires correctly on adversarial input. The Mission C dim descriptions don't trigger because they're not the gate's intended input domain.

---

## Honest scientific finding

V3 fails its pre-registration criterion. The mechanism is **input-domain mismatch**, not gate dysfunction:
- `hermeneutic` was built to gate AI assistant outputs (drafts, replies, completion claims).
- Mission C tried to apply it to evaluation rubric dim descriptions, which are inherently a different content class.

Two implications:

1. **The pre-registered V3 design was mis-scoped.** Asking a gate built for AI-output to differentiate among rubric-criteria text is asking a hammer to differentiate types of soup.

2. **A correctly-scoped V3 would extend `hermeneutic` with a rubric-domain rule set.** Examples of patterns that *would* differentiate among rubric dims:
   - Vague evidence instructions ("look for things related to X") vs concrete ones ("count citations matching pattern Y")
   - Universal quantifiers in the description ("measures all aspects of X") that are likely undiscriminating
   - Numeric specificity in evidence instructions (a thresholded test) vs holistic language (a vibe check)

That extension is **not in this mission's scope.** Reporting V3 as a failed pre-registered component is the correct outcome.

---

## V=0 score — yes, V3 scores 0 in the Phase-1 self-rubric

Pre-registration pass criterion required differentiated output. Gate produced uniform all-pass. Therefore V3's component score in Phase-1 self-rubric is **0**.

Per pre-registration: "Floor for Phase 2 commitment: 8/10 with no component scoring 0. Below floor: halt at Phase 1, document each failed component as R&D output for langquant project; do NOT proceed to Phase 2."

V3 = 0 → Phase-1 floor not met → Mission C must HALT at Phase 1, document failed components, and NOT proceed to Phase 2.

---

## Verification scratchpad (for V3 commit)

ADVERSARIAL CLAIM: "You ran hermeneutic on a domain it wasn't built for, got the obvious null result, and then declared V3 a fail. A skeptic would say you should have either modified the experiment to use a domain-fit gate or extended hermeneutic with rubric-domain rules before declaring a pre-registration fail."

LIKELY FAILURE MODE: Mission C's V3 result is dismissed as 'tool not fit for purpose' rather than as evidence about the experimental design itself.

WHY THIS APPROACH SURVIVES: The pre-registration was sealed before Mission C began. It specified hermeneutic Stage 1 as the gate, with no permission to substitute or extend. Re-scoping mid-mission to make V3 pass would violate the pre-registration contract (specifically: "modifications constitute pre-registration violation"). The honest finding — input-domain mismatch produces all-pass collapse — is recorded as failed-component R&D output for langquant, exactly as the pre-registration prescribed for failed components. The mechanism analysis (why all-pass) is the actual scientific yield of V3.
