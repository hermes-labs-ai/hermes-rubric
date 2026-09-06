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
Inspect AI scorer and the OpenAI Agents SDK adapter below are the bundled
adapters; Hermes does not claim bundled LangChain, Semantic Kernel, or
PydanticAI adapters.

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

## OpenAI Agents SDK adapter

Install the optional adapter:

```bash
pip install "hermes-rubric[openai-agents]"
```

The adapter grades a completed `RunResult` (or a finished
`RunResultStreaming`) from `Runner.run`, `Runner.run_sync`, or
`Runner.run_streamed`. It reads the run only: it never re-runs the agent,
never calls a model itself, and the module imports without the SDK, so
recorded runs and test stand-ins that expose the same attributes grade
through the same path.

```python
from agents import Agent, Runner
from hermes_rubric.integrations.openai_agents import assess_run_async

run = await Runner.run(agent, "What is the weather in Lisbon?")
result = await assess_run_async(
    run,
    intent="Answer accurately and ground every claim in the tool results.",
    backend="ollama-local",
)
print(result.aggregate, result.coverage.status)
```

`assess_run(run, ...)` is the synchronous form. Both accept exactly one of
`intent`, `rubric`, or `artifact_class`, plus `backend`, `target_type`
(default `agent-output`), `include_trace`, `extra_context`, and any further
`assess()` keyword such as `target_window_bytes` or `batch`.

`render_run(run)` returns the exact text Hermes will see, as a `RunEvidence`
with `target`, `context`, and `metadata`:

- **target** opens with the final output (structured outputs are rendered as
  sorted compact JSON), then a numbered chronological trace of messages, tool
  calls with arguments, tool results, handoffs, and reasoning (the summary
  when the model emitted one, otherwise the reasoning text).
  Putting the final output first keeps it inside the inspected window when a
  long trace follows; check `coverage.status` before treating an uncited
  trace line as absent.
- **context** carries the task input, each participating agent with its
  instructions, a run summary, guardrail tripwires, and `extra_context`.
  Tripwires cover input and output guardrails plus tool guardrails that
  rejected content or raised.
- **metadata** records the final agent, agents in order, item and model
  response counts, tool-call and handoff counts, guardrail tripwires, and
  token usage when the SDK reports it. Transport it beside `result.to_dict()`;
  it is not part of the Hermes receipt.

The receipt names the target `openai-agents:run` and the context
`openai-agents:task`. The adapter defines no pass threshold and does not
retry or mutate the agent; assessment errors propagate with their stage.

The bundled tests drive a real `Runner.run` through the SDK's
`agents.testing.ScriptedModel`, so the adapter is exercised against genuine
run items without a model or API key.
