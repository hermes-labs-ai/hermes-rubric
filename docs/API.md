# Python API

The public API is a stable assessment transaction: explicit inputs, one execution boundary, a typed result, truthful coverage, and optional caller-policy feedback.

## In-memory assessment

```python
from hermes_rubric import FeedbackPolicy, assess

result = assess(
    target="The agent output to assess",
    intent="Check accuracy and evidence grounding.",
    context="Material claims need checkable support.",
    target_name="agent-output.md",
    context_name="task-context.md",
    target_type="agent-output",
    backend="ollama-local",
)

print(result.aggregate)
print(result.coverage.to_dict())
print(result.feedback(FeedbackPolicy(minimum_score=7)).to_prompt())
```

`target` and `context` are literal strings. Hermes never guesses whether an arbitrary string is a path.

## Path assessment

```python
from hermes_rubric import assess_path

result = assess_path(
    "src/",
    intent="Assess this implementation against its stated contract.",
    context_path="SPEC.md",
    target_type="repo",
    target_window_bytes=32000,
)
```

`target_path` accepts a file or directory. `context_path` accepts a file or glob. Directory loading retains the established eligible-suffix and source-count limits and reports exclusions through `result.coverage`.

## Rubric sources

Exactly one source is active:

- `rubric=<mapping>`: copy and minimally validate a caller-provided frozen rubric.
- `artifact_class=<name>`: load a bundled deterministic class template.
- neither: synthesize from non-empty `intent` and `context`.

`rubric` and `artifact_class` are mutually exclusive. Frozen-rubric and class-template modes do not require intent or context.

## Function parameters

`assess()` accepts:

```text
target
intent=None, context=None
target_name="<memory>", context_name="<memory>"
target_type="document"
rubric=None, artifact_class=None
backend=None, batch=False
target_window_bytes=8000, context_window_bytes=8000
scope_class=None, intent_debias=False
```

`assess_path()` accepts the same pipeline options, replacing the in-memory inputs and logical names with `target_path` and `context_path`.

## Async wrappers

`assess_async()` and `assess_path_async()` have the same semantics. They use `asyncio.to_thread` so synchronous providers do not block the caller's event loop. Cancelling the await does not stop a provider request already executing in the worker thread.

## `AssessmentResult`

Stable top-level attributes:

- `rubric`
- `evidence_citations`
- `per_dim_scores`
- `aggregate`
- `max_possible`
- `hedge_dims`
- `hedge_note`
- `dim_summaries`
- `receipt`
- `schema_version`
- `coverage`

`to_dict()` and `to_json()` preserve the established CLI JSON keys. `schema_version` is the result-contract version and is independent of the package version.

## `CoverageReport`

Coverage reports:

- `status`: `complete` or `partial`
- `strategy`: currently `utf8-prefix`
- `visible_bytes` and `total_bytes`, or `null` where an exact fact cannot be established
- `considered_sources` and `total_sources`
- `limitations`: plain-language exclusions and uncertainty

The current engine does not claim full-document inspection when a prefix or source limit applies.

## Feedback

```python
from hermes_rubric import FeedbackPolicy

packet = result.feedback(FeedbackPolicy(minimum_score=7.0))
print(packet.to_dict())
print(packet.to_prompt())
```

Findings use `quality_gap`, `evidence_gap`, or `coverage_gap`. Quality findings require a caller threshold and accepted, unhedged evidence. Feedback is deterministic and does not execute a revision loop.

## Errors

`AssessmentError` exposes a stable `stage`:

```python
from hermes_rubric import AssessmentError, assess

try:
    result = assess("...", rubric=frozen_rubric)
except AssessmentError as error:
    print(error.stage)  # backend, input, rubric, evidence, score, or receipt
    print(error.__cause__)
```

This lets adapters choose fail-open, fail-closed, retry, or human-review behavior without parsing exception strings.

## Legacy stage functions

The existing modules remain importable for advanced composition:

- `hermes_rubric.synthesize.synthesize`
- `hermes_rubric.evidence.collect_evidence`
- `hermes_rubric.score.score_dimensions`
- `hermes_rubric.score.compute_aggregate`
- `hermes_rubric.backends`

New integrations should prefer the public transaction so orchestration, coverage, receipts, and error semantics do not drift.
