# Quickstart

## Install and choose a backend

```bash
pip install hermes-rubric
```

Automatic selection uses authenticated Claude Code or a running local Ollama instance. Cloud backends are explicit. For OpenAI:

```bash
pip install "hermes-rubric[openai]"
export OPENAI_API_KEY="..."
```

## Assess an agent output in memory

```python
from hermes_rubric import FeedbackPolicy, assess

answer = "The agent output to assess"
task = "Material claims need checkable evidence."

result = assess(
    answer,
    intent="Evaluate accuracy and evidence grounding.",
    context=task,
    target_type="agent-output",
    backend="openai-sdk",
)

print(f"aggregate: {result.aggregate}/10")
print(f"coverage: {result.coverage.status}")
print(result.feedback(FeedbackPolicy(minimum_score=7)).to_prompt())
```

Inspect citations and coverage before acting on the aggregate:

```python
for evidence in result.evidence_citations:
    print(evidence["dim_name"], evidence["citations"])

for limitation in result.coverage.limitations:
    print("coverage:", limitation)
```

## Assess a file from the CLI

```bash
hermes-rubric \
  --intent "Evaluate publication readiness" \
  --context STYLE-GUIDE.md \
  --target paper.md \
  --out result.json
```

For a deterministic bundled rubric:

```bash
hermes-rubric \
  --artifact-class repo-readme \
  --target README.md \
  --out result.json
```

## Read the result correctly

- Start with `coverage`. `partial` means some relevant material may be uninspected.
- Inspect `evidence_citations` and hedged dimensions.
- Use `per_dim_scores` and rationales before the aggregate.
- Treat the aggregate as signal, not verdict.
- Apply an explicit `FeedbackPolicy` only when your application owns a threshold.

Next: [Python API](API.md), [CLI](CLI.md), [Backends](BACKENDS.md), and [adapter contract](ADAPTERS.md).
