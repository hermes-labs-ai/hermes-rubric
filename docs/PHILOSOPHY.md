# Philosophy: why hermes-rubric is shaped the way it is

The thesis behind the design. Skip if you just want to install and use it - see the [README](https://github.com/hermes-labs-ai/hermes-rubric#readme). Read if you want to understand why the three-stage scaffold exists, why fluency outscores substance in raw LLM scoring, and why the receipts matter more than the score.

## The problem: fluency wins in raw LLM scoring

Ask an LLM to score something on a 0-10 scale. The model doesn't know your evaluation context, so it falls back on what it's optimized for: text quality signals. Well-written garbage outscores substantive-but-rough work. Re-run the same input - the number shifts because the prompt produces a different reasoning chain each time. There's no audit trail. There's no way to argue with the score.

This isn't a prompt-engineering issue. It's structural: a single-prompt scoring call has no commitment device that prevents the LLM from rewarding fluency.

## The fix: three sequential stages with commitment between them

1. **Synthesize a domain rubric** from the user's intent + context + target type. Outputs the dimension list with weights.
2. **Collect per-dimension evidence citations** - quoted passages or `file:line` references from the target. Dimensions where evidence is thin get marked.
3. **Score against the rubric and the evidence only.** Fabricated claims (no evidence) cap at ≤3. Hedged dimensions clamp to [3, 7].

The scaffold is the commitment device. By the time the LLM scores, it's already committed to a rubric (Stage 1) and citations (Stage 2). Stage 3 has nowhere to hide weak evidence behind fluency.

## The wider thesis: linguistic infrastructure, not model tuning

This tool is an instance of a wider Hermes Labs thesis: AI reliability is a question of linguistic infrastructure, not model tuning.

Most "improve the LLM's output" interventions try to make the model smarter (RLHF, finetuning, better prompts). hermes-rubric goes the other direction: leave the model alone, engineer the language layer above it. The model's outputs become structured artifacts (rubric, citations, scores) that can be inspected, reproduced, and audited. The LLM is treated as an interpretive engine, not a smart oracle.

Hermes Rubric applies a narrower engineering idea: the rubric, citations, and receipt externalize the state needed to inspect a scoring run. The model remains an interpretive engine rather than the source of truth.

The engineering follow-on for evaluation: when language is the substrate, scoring is interpretive engineering. The artifact is the score plus its citations plus its receipts. The LLM is the engine, not the source of truth.

## Why "evidence-first" is the load-bearing word

Most LLM-as-judge tools score in one prompt. They claim consistency by averaging multiple runs or by using temperature=0. hermes-rubric makes a different claim: structurally enforce that scores are derivative of evidence, not of fluency.

The two adversarial gates in `tests/test_adversarial.py` are the test surface for this claim:

- `test_fluency_does_not_inflate_evidence_score` - a fluent rewrite of weak evidence must not outscore a substantive-but-rough version by more than 1 point.
- `test_fabricated_claim_does_not_outscore_evidenced_claim` - claims without supporting evidence are capped at ≤3.

If those tests fail, the build breaks. The scaffold is contractually enforced.

## What this is not

- **Not a prompt-optimization technique.** The wins come from structure, not phrasing.
- **Not a benchmark of LLM quality.** The same model gets different scores on different artifacts; that's the design.
- **Not a substitute for human review on high-stakes decisions.** The score and receipts are an input to human judgment, not a replacement.
- **Not deterministic across rubric synthesis.** Stage 1 is LLM-driven; same intent + context can produce slightly different dim sets. Use `--artifact-class <name>` to keep the dimension set fixed across runs.

## Further reading

- [`BENCHMARKS.md`](BENCHMARKS.md) - the reproducibility data and per-backend κ
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - the three-stage scaffold internals
- [Failure-mode taxonomy](https://github.com/hermes-labs-ai/hermes-rubric/blob/main/calibration/failure-mode-taxonomy.md) - the committed failure modes and source pointers
- [About Hermes Labs](https://github.com/hermes-labs-ai/hermes-rubric/blob/main/ABOUT.md) - project context and the wider thesis
