# Python API reference

Library usage for embedding hermes-rubric in your own code.

## Quick example

```python
from hermes_rubric.synthesize import synthesize
from hermes_rubric.evidence import collect_evidence
from hermes_rubric.score import score_dimensions, compute_aggregate

rubric = synthesize(
    intent="rate this as a publication-ready research artifact",
    context_summary="...",
    target_type="paper",
    target_excerpt="...",
)

evidence = collect_evidence(
    rubric=rubric,
    target_content="...",
    target_path="paper.md",
)

scores = score_dimensions(rubric=rubric, evidence_list=evidence)
result = compute_aggregate(rubric=rubric, scores=scores)

print(result["aggregate"])  # 8.7
print(result["hedge_dims"])  # ["Reproducibility"]
```

## Stages

### `synthesize.synthesize(intent, context_summary, target_type, target_excerpt) -> dict`

Calls the configured backend to produce a rubric dictionary with a `dimensions` list.

### `evidence.collect_evidence(rubric, target_content, target_path, target_window_bytes=8000) -> list[dict]`

For each dimension in the rubric, asks the backend to find citations in `target_content`. The configured target window is the sole Stage-2 visibility cap for both per-dimension and batched evidence prompts; any hidden tail is identified by an explicit truncation marker. Each returned dictionary includes the dimension ID and name, accepted citation dictionaries, evidence summary, confidence, and hedge state.

Dimensions where evidence is thin return no accepted citations and set `hedge = True`.

### `score.score_dimensions(rubric, evidence_list) -> list[dict]`

For each dimension and evidence pair, asks the backend to score 0-10 based only on the evidence. Hedged dimensions clamp to [3, 7]. Returned dictionaries include `dim_id`, `dim_name`, `score`, `score_rationale`, and `hedge_applied`.

### `score.compute_aggregate(rubric, scores) -> dict`

Computes the weighted aggregate, hedge summary, dimension summaries, and ID-mismatch count. The CLI combines this dictionary with the rubric, evidence, scores, and receipt to produce its final JSON output.

## Class-aware mode

```python
from hermes_rubric.classes import load_class, to_rubric

rubric = to_rubric(load_class("social-post"))
# Skips Stage 1; rubric is loaded from hermes_rubric/classes/social-post.yaml
```

Then proceed with `collect_evidence` and the rest as normal.

## Backend selection

```python
from hermes_rubric.backends import detect, get_backend, register

# Get the auto-detected backend
backend = get_backend(detect())

# Or force one
backend = get_backend("ollama-local")

# Register a custom backend
class MyBackend:
    name = "my-backend"
    def call(self, prompt, max_tokens=2048):
        ...
    def model_id(self): return "my-model"
    def availability(self): return True

register(MyBackend())
```

See [`BACKENDS.md`](BACKENDS.md) for the full plugin protocol.

## Cohen's κ between two runs

```python
from hermes_rubric.agreement import cohens_kappa

report = cohens_kappa(result_a_json, result_b_json)
print(f"κ={report['mean_kappa']:.3f} (n={report['matched_dims']})")
```

Same as the `hermes-rubric kappa` CLI subcommand.

## Data shapes

The current Python API returns JSON-shaped dictionaries and lists rather than exported dataclass types. The field descriptions above and the CLI JSON example define the public data shape.

## Source

- `src/hermes_rubric/synthesize.py`
- `src/hermes_rubric/evidence.py`
- `src/hermes_rubric/score.py`
- `src/hermes_rubric/backends.py`
- `src/hermes_rubric/classes/`

## When to use the library vs the CLI

- **CLI:** scoring artifacts ad-hoc, in CI pipelines, in notebooks
- **Library:** embedding scoring into a larger Python workflow, building custom rubric synthesis steps, integrating with non-standard backends
