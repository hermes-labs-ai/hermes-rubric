# Scope-Class Auto-Detection Design

> Problem: tonight, n=4 distinct artifact kinds (orchestration-plan,
> eval-coverage-audit, tomorrow-task-list, fix-proposal) failed cleanly
> through the rubric because their `target_type` didn't match a
> registered scope class, and the synthesizer fell back to
> scaffold-experiment dims. Real recurring bug, not one-off
> miscalibration.
>
> Function: make the rubric input-context-aware. Currently the
> synthesizer is *output-context-aware* (scope-class preambles direct
> what dimensions to generate), but consumes `target_type` as a string
> the user supplies. Add a Stage 0 classification step that *infers*
> scope class from target content, with explicit fallback + conflict
> reporting.
>
> Scope class for THIS doc: fix-proposal — yes, the same scope class
> that doesn't yet have a preamble. The rubric will fall back to
> sweep-plan when it grades this design, which is exactly the failure
> mode being fixed. Acknowledged.

## What's broken (recap from session 478d8591, 2026-04-26)

Current pipeline:
```
user supplies (intent, context_path, target_path, target_type, scope_class)
  ↓
synthesize.py: prompt synthesizer with scope-class preamble (if any) + target_type label
  ↓
synthesizer reads target → generates 5-8 dimensions → scores
```

Failure mode: when `target_type` doesn't map to a registered scope class
in `~/bin/hermes-rubric-blinded.py`'s `_SCOPE_PREAMBLES` dict, the
preamble is empty, and the synthesizer falls back to scaffold-experiment
dims (placebo arms, factor crossing, etc.) — even when the target is
clearly a process rubric, a tomorrow-task-list, a fix proposal, etc.

n=4 distinct misfires tonight:
- orchestration-plan (PLAN-NOW.md, scored 4.9 with 5/8 hedged)
- eval-coverage-audit (the one before this, also same family)
- tomorrow-task-list (backlog rubric scored 3.8 with 4/8 hedged on
  "Adaptive-n Rule Rigor"-style dims)
- fix-proposal (rubriception fix doc scored 3.0 with 8/8 hedged)

## Proposed mechanism — Stage 0: scope-class classification

Insert a Stage 0 between user invocation and synthesize:

```
Stage 0: classify target → emit (auto_scope_class, confidence)
  ↓
if user-supplied scope_class:
    if matches auto_scope_class: proceed with user-supplied
    if differs: emit warning, proceed with auto_scope_class (or user-overrides via --strict)
if user did NOT supply scope_class:
    if confidence ≥ 0.8: proceed with auto_scope_class
    if confidence < 0.8: refuse-to-grade with diagnostic message listing candidates
```

The Stage 0 classifier is itself a small LLM call (Haiku, ~5s) with a
prompt like:

```
Classify the following target into one of the registered scope classes
or report UNREGISTERED. Output: {"scope_class": "<class>", "confidence":
0.0-1.0, "reasoning": "<one sentence>"}.

Registered classes:
- gate-plan: narrow gate decisions
- sweep-plan: full pre-registered design
- results-bundle: post-execution artifacts
- process-rubric: rubric grading behavior
- corpus-record: research write-up
- session-quality-eval: full-session evaluation
- UNREGISTERED: target doesn't match any of the above

TARGET (first 2000 chars):
<excerpt>
```

The classifier IS itself a small registry-mediated thing, but it's a
single read-only call, no per-dimension dimension generation, no
recursive scope confusion.

## Why this solves the n=4 problem

Each of tonight's 4 misfires would have been classified UNREGISTERED
with high confidence by Stage 0. The pipeline would have refused-to-grade
or fallen back to a closer-fit class with an explicit warning — instead
of silently generating scaffold-experiment dims and producing 3-5/10
aggregates that look like artifact failures but are actually instrument
failures.

Specifically:
- "tomorrow-task-list" → UNREGISTERED, confidence 0.95, reasoning "list
  of next-action items with first-move commands; no experimental design
  structure" → orchestrator sees the warning, knows the rubric isn't the
  right tool, decides whether to add the class or use a different tool
- "orchestration-plan" → UNREGISTERED with high confidence, similar path
- "fix-proposal" → UNREGISTERED, similar
- "eval-coverage-audit" → likely classified as sweep-plan (closest match)
  with medium confidence; emits warning that gives orchestrator visibility

## Implementation sketch (≤200 LOC)

1. Add `synthesize.classify_scope_class(target_text)` function:
   - 1 LLM call to Haiku
   - Returns `(scope_class, confidence, reasoning)` tuple
   - 5s timeout, falls through to ("UNREGISTERED", 0.0, "classifier failed")
2. Modify CLI: if `--scope-class` not set, run Stage 0 first.
3. Modify CLI: if `--scope-class` set AND auto-detect differs by ≥1 class,
   print warning unless `--scope-class-strict` is also set.
4. Add `--no-auto-detect` flag for callers who want the current behavior.
5. Add 5-cell test fixture covering the 4 misfire-types + 1 happy-path
   gate-plan, asserting Stage 0 produces expected classifications with
   confidence ≥0.7.

## What this does NOT do

- Doesn't auto-add scope classes to the registry — that's still a
  human decision (see no-noun-phrase rule).
- Doesn't replace user-supplied scope class when one is given.
- Doesn't classify mid-rubric (only Stage 0); per-dim generation still
  uses the chosen scope class as before.
- Doesn't help when target text is shorter than ~500 chars (classifier
  needs evidence; very short targets get UNREGISTERED).

## Verification contract

Test `test_stage0_classifier.py` with fixtures:
- gate-plan example → classified gate-plan, confidence ≥0.7
- sweep-plan example → classified sweep-plan, confidence ≥0.7
- corpus-record example → classified corpus-record, confidence ≥0.7
- a tomorrow-task-list example → UNREGISTERED, confidence ≥0.7
- 100-char target → UNREGISTERED, confidence <0.5

Test `test_cli_scope_warning.py`:
- pass mismatched user `--scope-class sweep-plan` on a process-rubric target
  → warning emitted, run proceeds (unless --scope-class-strict)
- pass `--scope-class-strict` with mismatch → exit 2 with diagnostic

## Cost / risk

- Adds 1 Haiku call (~5s) to every rubric run that doesn't supply
  `--scope-class`. Cost: negligible.
- Risk: classifier itself is an LLM, so it has an error rate. Mitigation:
  confidence threshold, warning instead of hard-refuse, override flag.
- Risk: introduces a new abstraction layer. Mitigation: 1 file, ~150
  LOC, testable, reversible.

## Pre-registered decision rule for the rubric on this doc

If the rubric (which will use sweep-plan fallback because there's no
`fix-proposal` scope class — exactly the bug this design fixes)
scores ≥6 with majority dims at structural cap → ship the design as a
NEXT-UP entry for tomorrow, gate implementation on user signoff.
If the rubric scores <6 with real (uncapped) gaps → iterate the design
once, max 1 retry.
If the rubric scores <6 with all-hedged out-of-scope rationales → that
IS the proof-of-concept that the bug is real; ship the design anyway,
flag the rubric output as itself an instance of the failure mode.
