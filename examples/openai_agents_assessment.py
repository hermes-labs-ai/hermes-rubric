"""Grade a completed OpenAI Agents SDK run with Hermes Rubric.

Requires ``pip install "hermes-rubric[openai-agents]"``. The agent side below
uses the SDK's own ``ScriptedModel`` so it runs offline; the grading side uses
whatever Hermes backend you select (``backend=None`` auto-detects Claude Code
or local Ollama). Swap the scripted model for a real one to grade live runs.
"""

from __future__ import annotations

import asyncio

from agents import Agent, RunConfig, Runner, function_tool
from agents.testing import ScriptedModel, assistant_message, function_call

from hermes_rubric import AssessmentError, FeedbackPolicy
from hermes_rubric.integrations.openai_agents import assess_run_async, render_run


@function_tool
def lookup_weather(city: str) -> str:
    """Return the current weather for a city."""
    return f"{city}: 21C, clear"


agent = Agent(
    name="Weather",
    instructions="Answer weather questions using tool evidence.",
    tools=[lookup_weather],
)

scripted = ScriptedModel(
    [
        [function_call("lookup_weather", {"city": "Lisbon"}, call_id="call_1")],
        [assistant_message("Lisbon is 21C and clear.")],
    ]
)


async def main() -> None:
    run = await Runner.run(
        agent,
        "What is the weather in Lisbon?",
        run_config=RunConfig(model=scripted, tracing_disabled=True),
    )

    # Inspect what Hermes will see before grading (final output first, then the trace).
    evidence = render_run(run)
    print(evidence.target)
    print(evidence.metadata)

    try:
        result = await assess_run_async(
            run,
            intent="Answer accurately and ground every claim in the tool results.",
            backend=None,  # or "ollama-local", "claude-cli", "openai-sdk", ...
        )
    except AssessmentError as error:
        print(f"assessment failed at stage {error.stage}: {error}")
        return

    print(result.aggregate, result.coverage.status)
    print(result.feedback(FeedbackPolicy(minimum_score=7)).to_prompt())


if __name__ == "__main__":
    asyncio.run(main())
