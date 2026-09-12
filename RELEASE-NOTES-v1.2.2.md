# Hermes Rubric v1.2.2 — OpenAI Agents SDK adapter and a scoring-fallback fix

Version 1.2.2 adds a native, optional adapter for the
[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) and fixes
a scoring-stage bug where malformed responses could silently become
fallback scores.

## What is new

- Install with `pip install "hermes-rubric[openai-agents]"`.
- Grade a completed `RunResult` (or a finished `RunResultStreaming`) from
  `Runner.run`, `Runner.run_sync`, or `Runner.run_streamed` with
  `assess_run` / `assess_run_async` from
  `hermes_rubric.integrations.openai_agents`.
- The adapter reads the run only: it never re-runs the agent and never calls
  a model itself. It does not import the SDK, so recorded runs and
  lightweight stand-ins exposing the same attributes grade through the same
  path.
- Tool guardrail rejections, SDK-resolved names for hosted tool calls, and
  reasoning text emitted without a summary all reach the rendered evidence
  and context Hermes scores against.
- Fixed: malformed or incomplete scoring responses can no longer be
  converted into fallback scores that enter an aggregate. Batch mode still
  retries per-dimension before surfacing a score-stage failure.
- The PyPI project page's long description is rebuilt from the current
  README, so it now includes the `hermes-rubric[openai-agents]` adapter
  paragraph alongside the existing Inspect AI mention.

## Product boundary

The OpenAI Agents SDK owns agent execution, tool orchestration, and
guardrails. Hermes Rubric remains a stateless evidence-first assessment
transaction: the adapter renders one completed run into cited text and
scores it. It defines no pass threshold, does not retry or mutate the
agent, and does not turn a score into authorization.

## Upgrade

```bash
pip install --upgrade "hermes-rubric[openai-agents]"
```

See the [adapter documentation](docs/ADAPTERS.md) for CLI and Python
examples.
