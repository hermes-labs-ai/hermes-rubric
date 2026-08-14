# Architecture

Hermes measures and explains. Adapters apply caller policy. Runtimes act.

```text
runtime output -> thin adapter -> Hermes core -> evidence + score + feedback
                         ^                         |
                         |------ caller policy ---|
```

This boundary lets the same measuring instrument, evidence semantics, coverage report, and receipt travel across runtimes without making a framework part of the core.

## Public transaction

`assess()` and `assess_path()` own the canonical pipeline:

```text
explicit input
    -> select or synthesize rubric
    -> collect and validate cited evidence
    -> score only against accepted evidence
    -> aggregate + coverage + receipt
    -> AssessmentResult
```

The CLI is a compatibility adapter over `assess_path()`. Runtime integrations should call public APIs only; they should not reproduce this orchestration.

## Rubric stage

One measuring-stick source is active for a transaction:

- synthesis from intent and context;
- a deterministic bundled artifact class; or
- a caller-provided frozen rubric.

Synthesized rubrics are LLM-driven and may differ across runs. A receipt hashes the effective rubric, but a hash makes change visible—it does not make different rubrics comparable.

## Evidence stage

For every dimension, Hermes asks the backend to cite observable material. The runtime validates citation IDs and exact quoted text before accepting them. Source classes distinguish code, tests, configuration, README prose, documentation, and other material.

Version 1.1 retains the UTF-8-safe prefix strategy. It does not add chunked retrieval. `CoverageReport` prevents a hidden tail or directory exclusion from silently becoming negative evidence.

## Score stage

Scoring receives the rubric and accepted evidence, not the raw target. Existing mechanical constraints remain in force:

- low-confidence evidence clamps a dimension to the hedge range;
- no accepted evidence caps the score;
- README- or documentation-only support receives lower authority than code or test evidence;
- rubric dimension identity wins over provider output drift.

The aggregate is a weighted summary, not a default verdict.

## Result and receipt

`AssessmentResult` types the stable top-level surface while retaining the established nested dictionaries for backwards compatibility. It serializes to the same legacy JSON keys plus `schema_version` and `coverage`.

The receipt records input hashes, backend, rubric hash/source, schema version, and coverage facts. It makes a run inspectable. It does not prove provider determinism, full visibility, or correctness of the assessed artifact.

## Feedback boundary

`result.feedback(policy)` classifies the next problem as:

- a quality gap supported by inspected evidence;
- an evidence gap caused by missing or hedged support; or
- a coverage gap caused by incomplete visibility.

Only caller policy supplies a minimum score. Hermes produces instructions but never decides to pass, retries an agent, or mutates runtime state.

## Adapter rules

An adapter:

1. passes runtime output and context to the public API;
2. chooses explicit policy, retry limits, timeouts, and fail-open/fail-closed behavior;
3. translates `AssessmentError.stage` without parsing raw provider text;
4. records runtime-specific attempt metadata outside the core result;
5. never duplicates evidence or scoring logic.

See [ADAPTERS.md](ADAPTERS.md).
