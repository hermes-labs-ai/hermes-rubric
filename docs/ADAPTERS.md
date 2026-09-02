# Adapter contract

Hermes is framework-neutral. An adapter should be thin enough that the same assessment transaction can be used from any runtime.

## Responsibilities

The adapter owns:

- extracting the runtime output and relevant task context;
- choosing a frozen rubric, artifact class, or synthesis inputs;
- setting backend, byte budgets, timeouts, and cancellation behavior;
- applying caller policy such as advisory feedback, bounded revision, human review, or a tripwire;
- choosing fail-open or fail-closed behavior;
- enforcing attempt limits and recording runtime/attempt metadata.

Hermes owns:

- rubric selection and validation;
- cited evidence collection and citation validation;
- scoring clamps and aggregation;
- coverage, normalized stage errors, and the core receipt;
- deterministic feedback classification and prompt rendering.

## Minimal shape

```python
from hermes_rubric import AssessmentError, FeedbackPolicy, assess


def evaluate_runtime_output(output: str, task_context: str):
    try:
        result = assess(
            output,
            intent="Evaluate accuracy and support for material claims.",
            context=task_context,
            target_type="agent-output",
        )
    except AssessmentError as error:
        return {"status": "needs_runtime_policy", "stage": error.stage}

    feedback = result.feedback(FeedbackPolicy(minimum_score=7))
    return {"assessment": result.to_dict(), "feedback": feedback.to_dict()}
```

This function deliberately does not retry or mutate an agent. A runtime-specific layer may do so with an explicit attempt limit.

## Invariants

- Import only documented public names from `hermes_rubric`.
- Do not convert `coverage_gap` into an artifact defect.
- Do not add a hidden global pass threshold.
- Preserve `schema_version`, coverage, and the receipt when transporting results.
- Do not promise cancellation of a synchronous provider already running in `assess_async()`.

Framework integrations remain optional extras over this stable contract. The
Inspect AI scorer below is the first bundled adapter; Hermes does not claim
bundled LangChain, OpenAI Agents, Semantic Kernel, or PydanticAI adapters.

## Inspect AI scorer

Install the optional scorer integration:

```bash
pip install "hermes-rubric[inspect]"
```

Inspect registers it as `hermes_rubric/hermes_rubric_scorer`, so it can score
new tasks or re-score an existing eval log without changing the evaluated
agent:

```bash
inspect score run.eval \
  --scorer hermes_rubric/hermes_rubric_scorer \
  -S intent="Assess whether the answer is accurate and evidence-supported."
```

From Python, use the same scorer in a task:

```python
from hermes_rubric.integrations.inspect_ai import hermes_rubric_scorer

scorer = hermes_rubric_scorer(
    rubric=frozen_rubric,
    backend="openai-sdk",
)
```

The numeric `Score.value` uses Hermes' 0-10 aggregate scale. The full
assessment—including citations, coverage facts, and receipt—is stored under
`Score.metadata["hermes_rubric"]`. The adapter does not define a pass
threshold or retry the evaluated agent. Assessment errors fail scoring by
default; `fail_on_error=False` records a visible unscored sample instead.
