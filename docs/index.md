# hermes-rubric

Hermes Rubric is a framework-neutral, evidence-first assessment primitive for agent outputs and applications.

```python
from hermes_rubric import FeedbackPolicy, assess

result = assess(
    target=agent_output,
    intent="Evaluate accuracy and evidence grounding.",
    context=task_context,
    target_type="agent-output",
)

feedback = result.feedback(FeedbackPolicy(minimum_score=7))
```

The public transaction selects or synthesizes a rubric, collects validated citations, scores only against accepted evidence, and returns coverage plus a receipt. Hermes measures and explains; callers own thresholds, retries, and runtime actions.

Version 1.1 retains a UTF-8-safe prefix strategy for evidence collection and reports partial coverage explicitly. The aggregate is signal, not verdict.

[Install](install.md) · [Quickstart](quickstart.md) · [Python API](API.md) · [Architecture](ARCHITECTURE.md) · [Adapter contract](ADAPTERS.md)
