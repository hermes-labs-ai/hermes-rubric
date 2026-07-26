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

### `synthesize.synthesize(intent, context_summary, target_type, target_excerpt) -> Rubric`

Calls the configured backend to produce a rubric for the artifact. Returns a `Rubric` object with `dimensions` (list of `Dimension`).

### `evidence.collect_evidence(rubric, target_content, target_path, target_window_bytes=8000) -> list[Evidence]`

For each dimension in the rubric, asks the backend to find a citation in `target_content`. The configured target window is the sole Stage-2 visibility cap for both per-dimension and batched evidence prompts; any hidden tail is identified by an explicit truncation marker. Returns a list of `Evidence` objects with `dim_id`, `citation` (path:line or quoted passage), and `quote` (the text).

Dimensions where evidence is thin get `quote = "<thin>"` and `hedge = True`.

### `score.score_dimensions(rubric, evidence_list) -> list[Score]`

For each dimension + evidence pair, asks the backend to score 0-10 based only on the evidence. Hedged dimensions clamp to [3, 7]. Returns list of `Score` objects with `dim_id`, `score`, `rationale`.

### `score.compute_aggregate(rubric, scores) -> dict`

Computes the weighted aggregate, builds the receipt, and packages everything into the output dict (same shape as the CLI JSON output).

## Class-aware mode

```python
from hermes_rubric.classes import load_class

rubric = load_class("social-post")
# Skips Stage 1; rubric is loaded from hermes_rubric/classes/social-post.yaml
```

Then proceed with `collect_evidence` and the rest as normal.

## Backend selection

```python
from hermes_rubric.backends import get_backend, register

# Get the auto-detected backend
backend = get_backend()

# Or force one
from hermes_rubric.backends.claude_cli import ClaudeCLIBackend
backend = ClaudeCLIBackend()

# Register a custom backend
class MyBackend:
    name = "my-backend"
    def call(self, prompt, max_tokens=2048):
        ...
    def detect_available(self):
        ...

register(MyBackend())
```

See [`BACKENDS.md`](BACKENDS.md) for the full plugin protocol.

## Cohen's κ between two runs

```python
from hermes_rubric.kappa import compute_kappa

kappa, n = compute_kappa(result_a_json, result_b_json)
print(f"κ={kappa:.3f} (n={n})")
```

Same as the `hermes-rubric kappa` CLI subcommand.

## Type definitions

```python
from hermes_rubric.types import Dimension, Rubric, Evidence, Score

@dataclass
class Dimension:
    id: str
    name: str
    description: str
    weight: int  # 1-3
    voice_priors: list[str] = field(default_factory=list)

@dataclass
class Rubric:
    dimensions: list[Dimension]
    target_type: str
    source: str  # "synthesized" or "class:<name>"

@dataclass
class Evidence:
    dim_id: str
    citation: str  # path:line or "<quoted passage>"
    quote: str
    hedge: bool = False

@dataclass
class Score:
    dim_id: str
    score: int  # 0-10
    rationale: str
    hedged: bool = False
```

## Source

- `src/hermes_rubric/synthesize.py`
- `src/hermes_rubric/evidence.py`
- `src/hermes_rubric/score.py`
- `src/hermes_rubric/types.py`
- `src/hermes_rubric/backends/`
- `src/hermes_rubric/classes/`

## When to use the library vs the CLI

- **CLI:** scoring artifacts ad-hoc, in CI pipelines, in notebooks
- **Library:** embedding scoring into a larger Python workflow, building custom rubric synthesis steps, integrating with non-standard backends
