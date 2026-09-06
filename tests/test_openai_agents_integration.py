"""Contract tests for the optional OpenAI Agents SDK adapter.

The first group uses lightweight stand-ins and runs without the SDK. The
second group is skipped unless ``openai-agents`` is installed; it drives a
real ``Runner.run`` through the SDK's own ``ScriptedModel`` so no model or
API key is involved, then grades the resulting ``RunResult`` end to end with
a local scripted Hermes backend.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from hermes_rubric import backends
from hermes_rubric.errors import AssessmentError
from hermes_rubric.integrations import openai_agents as integration
from hermes_rubric.models import AssessmentResult, CoverageReport

RUBRIC = {
    "rubric_intent": "Check that the answer is grounded in tool evidence.",
    "target_type": "agent-output",
    "dimensions": [
        {
            "id": dim_id,
            "name": name,
            "description": description,
            "evidence_instructions": "Quote the trace line that supports the answer.",
            # Source: calibration/META-RUBRIC.md:112-115 (weight-1 convention).
            "weight": 1,
            "hedge": False,
        }
        for dim_id, name, description in (
            ("grounding", "Tool grounding", "The final answer matches the tool results (FM-01 Numeric retrofit; FM-08 Source anchoring)."),
            ("routing", "Routing", "The run reached the agent equipped for the task (FM-19 Dimension boilerplate; FM-23 Anchor drift)."),
            ("directness", "Directness", "The final answer addresses the user's question (FM-08 Source anchoring; FM-22 Evidence scope creep)."),
        )
    ],
}


# --- stand-ins (no SDK) ------------------------------------------------------


def _agent(name: str, instructions):
    return SimpleNamespace(name=name, instructions=instructions)


def _fake_run(final_output="Lisbon is 21C and clear."):
    triage = _agent("Triage", "Route weather questions to the specialist.")
    specialist = _agent("Specialist", "Answer weather questions\nusing tool evidence.")
    items = [
        SimpleNamespace(
            type="handoff_call_item",
            agent=triage,
            raw_item={"type": "function_call", "name": "transfer_to_specialist", "arguments": "{}", "call_id": "h1"},
        ),
        SimpleNamespace(
            type="handoff_output_item",
            agent=triage,
            source_agent=triage,
            target_agent=specialist,
            raw_item={"type": "function_call_output", "call_id": "h1", "output": '{"assistant": "Specialist"}'},
        ),
        SimpleNamespace(
            type="reasoning_item",
            agent=specialist,
            raw_item={"type": "reasoning", "summary": [{"text": "Need the live weather."}]},
        ),
        SimpleNamespace(
            type="tool_call_item",
            agent=specialist,
            raw_item={"type": "function_call", "name": "lookup_weather", "arguments": '{"city":"Lisbon"}', "call_id": "c1"},
        ),
        SimpleNamespace(
            type="tool_call_output_item",
            agent=specialist,
            output="Lisbon: 21C, clear",
            raw_item={"type": "function_call_output", "call_id": "c1", "output": "Lisbon: 21C, clear"},
        ),
        SimpleNamespace(
            type="message_output_item",
            agent=specialist,
            raw_item={"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": final_output if isinstance(final_output, str) else "done"}]},
        ),
    ]
    return SimpleNamespace(
        input="What is the weather in Lisbon?",
        new_items=items,
        raw_responses=[object(), object(), object()],
        final_output=final_output,
        last_agent=specialist,
        input_guardrail_results=[
            SimpleNamespace(
                guardrail=SimpleNamespace(name="pii_screen"),
                output=SimpleNamespace(tripwire_triggered=True),
            )
        ],
        output_guardrail_results=[],
        context_wrapper=SimpleNamespace(
            usage=SimpleNamespace(requests=3, input_tokens=120, output_tokens=40, total_tokens=160)
        ),
    )


def _result() -> AssessmentResult:
    return AssessmentResult(
        rubric={"title": "Evidence"},
        evidence_citations=[{"source": "target", "quote": "21C"}],
        per_dim_scores=[{"dim_id": "grounding", "score": 8}],
        aggregate=8.0,
        max_possible=10.0,
        hedge_dims=[],
        hedge_note="",
        dim_summaries=[{"dim_id": "grounding", "name": "Tool grounding", "score": 8}],
        receipt={"rubric_hash": "abc"},
        coverage=CoverageReport(status="complete", strategy="utf8_prefix", visible_bytes=1, total_bytes=1),
    )


def test_render_run_puts_final_output_first_then_numbered_trace():
    evidence = integration.render_run(_fake_run())

    assert evidence.target.startswith("# Final output\nLisbon is 21C and clear.\n")
    assert "[1] Triage handoff call transfer_to_specialist({})" in evidence.target
    assert "[2] Triage handoff Triage -> Specialist" in evidence.target
    assert "[3] Specialist reasoning summary: Need the live weather." in evidence.target
    assert '[4] Specialist tool call lookup_weather({"city":"Lisbon"})' in evidence.target
    assert "[5] Specialist tool result lookup_weather: Lisbon: 21C, clear" in evidence.target
    assert "[6] Specialist message: Lisbon is 21C and clear." in evidence.target


def test_render_run_context_carries_task_agents_summary_and_guardrails():
    evidence = integration.render_run(_fake_run(), extra_context="Grader note: be strict.")

    assert "# Task input\nWhat is the weather in Lisbon?" in evidence.context
    assert "- Triage: Route weather questions to the specialist." in evidence.context
    assert "- Specialist: Answer weather questions using tool evidence." in evidence.context
    assert "3 model responses, 1 tool calls, 1 handoffs, 6 run items; final agent Specialist." in evidence.context
    assert "Guardrail tripwires: pii_screen" in evidence.context
    assert "# Caller context\nGrader note: be strict." in evidence.context
    assert evidence.metadata == {
        "final_agent": "Specialist",
        "agents": ["Triage", "Specialist"],
        "run_items": 6,
        "model_responses": 3,
        "tool_calls": 1,
        "handoffs": 1,
        "final_output_type": "str",
        "guardrails_triggered": ["pii_screen"],
        "usage": {"requests": 3, "input_tokens": 120, "output_tokens": 40, "total_tokens": 160},
    }


def test_render_run_can_omit_trace_and_handles_structured_final_output():
    @dataclass
    class Forecast:
        city: str
        celsius: int

    evidence = integration.render_run(_fake_run(final_output=Forecast("Lisbon", 21)), include_trace=False)

    assert evidence.target == '# Final output\n{"celsius":21,"city":"Lisbon"}\n'
    assert evidence.metadata["final_output_type"] == "Forecast"


def test_render_run_renders_input_item_lists():
    run = _fake_run()
    run.input = [
        {"role": "user", "content": "First question"},
        {"role": "user", "content": [{"type": "input_text", "text": "Second question"}]},
        {"type": "function_call_output", "call_id": "x", "output": "prior"},
    ]

    evidence = integration.render_run(run)

    assert "- user: First question\n- user: Second question\n- function_call_output: " in evidence.context


def test_render_run_reports_tool_guardrail_interventions():
    """Tool guardrails record a `behavior`, not a `tripwire_triggered` flag."""
    run = _fake_run()
    run.tool_input_guardrail_results = [
        SimpleNamespace(
            guardrail=SimpleNamespace(name="secrets_screen"),
            output=SimpleNamespace(behavior={"type": "reject_content", "message": "blocked"}),
        ),
        SimpleNamespace(
            guardrail=SimpleNamespace(name="length_screen"),
            output=SimpleNamespace(behavior={"type": "allow"}),
        ),
    ]
    run.tool_output_guardrail_results = [
        SimpleNamespace(
            guardrail=SimpleNamespace(name="leak_screen"),
            output=SimpleNamespace(behavior={"type": "raise_exception"}),
        )
    ]

    evidence = integration.render_run(run)

    assert evidence.metadata["guardrails_triggered"] == [
        "pii_screen",
        "secrets_screen",
        "leak_screen",
    ]
    assert "Guardrail tripwires: pii_screen, secrets_screen, leak_screen" in evidence.context


def test_render_run_names_an_unnamed_guardrail_from_its_accessor():
    run = _fake_run()
    run.input_guardrail_results = [
        SimpleNamespace(
            guardrail=SimpleNamespace(name=None, get_name=lambda: "screen_for_pii"),
            output=SimpleNamespace(tripwire_triggered=True),
        )
    ]

    assert integration.render_run(run).metadata["guardrails_triggered"] == ["screen_for_pii"]


def test_render_run_uses_the_resolved_tool_name_and_call_id_for_hosted_calls():
    """Hosted calls carry no `name` and may key their output off `id`."""
    agent = _agent("Operator", "Drive the computer.")
    call = SimpleNamespace(
        type="tool_call_item",
        agent=agent,
        tool_name="run_shell",
        call_id="shell_1",
        raw_item={"type": "shell_call", "id": "shell_1", "action": {"command": ["ls"]}},
    )
    output = SimpleNamespace(
        type="tool_call_output_item",
        agent=agent,
        call_id="shell_1",
        output="README.md",
        raw_item={"type": "shell_call_output", "id": "shell_1", "output": "README.md"},
    )
    run = _fake_run()
    run.new_items = [call, output]

    evidence = integration.render_run(run)

    assert '[1] Operator tool call run_shell({"action":{"command":["ls"]}})' in evidence.target
    assert "[2] Operator tool result run_shell: README.md" in evidence.target


def test_render_run_falls_back_to_reasoning_content_when_no_summary():
    run = _fake_run()
    run.new_items = [
        SimpleNamespace(
            type="reasoning_item",
            agent=_agent("Specialist", "Answer."),
            raw_item={
                "type": "reasoning",
                "summary": [],
                "content": [{"type": "reasoning_text", "text": "Check the tool first."}],
            },
        )
    ]

    evidence = integration.render_run(run)

    assert "[1] Specialist reasoning: Check the tool first." in evidence.target


def test_render_run_rejects_objects_that_are_not_runs():
    with pytest.raises(TypeError, match="RunResult"):
        integration.render_run({"final_output": "text"})


def test_assess_run_maps_rendered_run_into_assess(monkeypatch):
    captured = {}

    def fake_assess(target, **kwargs):
        captured["target"] = target
        captured.update(kwargs)
        return _result()

    monkeypatch.setattr(integration, "assess", fake_assess)

    result = integration.assess_run(
        _fake_run(), rubric=RUBRIC, backend="openai-sdk", target_window_bytes=4000
    )

    assert result.aggregate == 8.0
    assert captured["target"].startswith("# Final output\nLisbon is 21C and clear.")
    assert "What is the weather in Lisbon?" in captured["context"]
    assert captured["rubric"] == RUBRIC
    assert captured["backend"] == "openai-sdk"
    assert captured["target_type"] == "agent-output"
    assert captured["target_window_bytes"] == 4000
    assert captured["target_name"] == "openai-agents:run"
    assert captured["context_name"] == "openai-agents:task"


@pytest.mark.parametrize("name", ["context", "target", "target_name", "context_name"])
def test_assess_run_rejects_adapter_owned_kwargs(name):
    with pytest.raises(TypeError, match="adapter-owned"):
        integration.assess_run(_fake_run(), intent="Check grounding.", **{name: "override"})


@pytest.mark.parametrize("name", ["context", "target", "target_name", "context_name"])
def test_assess_run_async_rejects_adapter_owned_kwargs(name):
    with pytest.raises(TypeError, match="adapter-owned"):
        asyncio.run(integration.assess_run_async(_fake_run(), intent="Check grounding.", **{name: "override"}))


def test_assess_run_async_uses_assess_async_and_propagates_stage_errors(monkeypatch):
    captured = {}

    async def fake_assess_async(target, **kwargs):
        captured["target"] = target
        captured.update(kwargs)
        return _result()

    monkeypatch.setattr(integration, "assess_async", fake_assess_async)
    result = asyncio.run(integration.assess_run_async(_fake_run(), intent="Check grounding."))
    assert result.aggregate == 8.0
    assert captured["intent"] == "Check grounding."

    async def fail(target, **kwargs):
        raise AssessmentError("evidence", "provider unavailable")

    monkeypatch.setattr(integration, "assess_async", fail)
    with pytest.raises(AssessmentError) as excinfo:
        asyncio.run(integration.assess_run_async(_fake_run(), intent="Check grounding."))
    assert excinfo.value.stage == "evidence"


# --- real SDK runs (skipped without openai-agents) ---------------------------


class _ScriptedGrader:
    """Local Hermes backend that answers evidence and score prompts deterministically."""

    name = "scripted-grader"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def call(self, prompt: str, max_tokens: int) -> str:
        self.prompts.append(prompt)
        dim_id = re.search(r'"dim_id": "([^"]+)"', prompt).group(1)
        if '"score_rationale"' in prompt:
            return json.dumps(
                {
                    "dim_id": dim_id,
                    "dim_name": dim_id,
                    "score": 8,
                    "score_rationale": "The answer restates the tool result.",
                    "evidence_drove_score": "Lisbon: 21C, clear",
                    "hedge_applied": False,
                }
            )
        # Cite the section that actually encloses the quote (the run trace, not the final output).
        quote_at = prompt.index("tool result lookup_weather: Lisbon: 21C, clear")
        section = re.findall(r'<SECTION id="([^"]+)"', prompt[:quote_at])[-1]
        return json.dumps(
            {
                "dim_id": dim_id,
                "evidence_found": True,
                "confidence": "high",
                "hedge": False,
                "citations": [
                    {
                        "quote": "Lisbon: 21C, clear",
                        "evidence_id": section,
                        "location": "tool result",
                        "source_class": "other",
                    }
                ],
                "evidence_summary": "The tool result matches the final answer.",
            }
        )

    def model_id(self) -> str:
        return "scripted-grader-1"

    def availability(self) -> bool:
        return True


@pytest.fixture
def sdk(monkeypatch):
    agents = pytest.importorskip("agents")
    testing = pytest.importorskip("agents.testing")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return agents, testing


def _build_agents(agents):
    @agents.function_tool
    def lookup_weather(city: str) -> str:
        """Return the current weather for a city."""
        return f"{city}: 21C, clear"

    specialist = agents.Agent(
        name="Specialist",
        instructions="Answer weather questions using tool evidence.",
        tools=[lookup_weather],
    )
    triage = agents.Agent(
        name="Triage",
        instructions="Route weather questions to the specialist.",
        handoffs=[specialist],
    )
    return triage


def _scripted_model(testing):
    return testing.ScriptedModel(
        [
            [testing.function_call("transfer_to_specialist", "{}", call_id="call_h1")],
            [testing.function_call("lookup_weather", {"city": "Lisbon"}, call_id="call_1")],
            [testing.assistant_message("Lisbon is 21C and clear.")],
        ]
    )


def _run_config(agents, model):
    return agents.RunConfig(model=model, tracing_disabled=True)


def test_sdk_run_result_renders_real_items(sdk):
    agents, testing = sdk
    model = _scripted_model(testing)

    run = asyncio.run(
        agents.Runner.run(
            _build_agents(agents),
            "What is the weather in Lisbon?",
            run_config=_run_config(agents, model),
        )
    )
    model.assert_complete()
    evidence = integration.render_run(run)

    assert evidence.target.startswith("# Final output\nLisbon is 21C and clear.\n")
    assert "[1] Triage handoff call transfer_to_specialist({})" in evidence.target
    assert "[2] Triage handoff Triage -> Specialist" in evidence.target
    assert '[3] Specialist tool call lookup_weather({"city":"Lisbon"})' in evidence.target
    assert "[4] Specialist tool result lookup_weather: Lisbon: 21C, clear" in evidence.target
    assert "[5] Specialist message: Lisbon is 21C and clear." in evidence.target
    assert "- Triage: Route weather questions to the specialist." in evidence.context
    assert "- Specialist: Answer weather questions using tool evidence." in evidence.context
    assert evidence.metadata["final_agent"] == "Specialist"
    assert evidence.metadata["agents"] == ["Triage", "Specialist"]
    assert evidence.metadata["tool_calls"] == 1
    assert evidence.metadata["handoffs"] == 1
    assert evidence.metadata["model_responses"] == 3
    assert evidence.metadata["guardrails_triggered"] == []
    assert evidence.metadata["usage"]["requests"] == 3


def test_sdk_streaming_run_result_renders_after_completion(sdk):
    agents, testing = sdk
    model = _scripted_model(testing)

    async def stream():
        result = agents.Runner.run_streamed(
            _build_agents(agents),
            "What is the weather in Lisbon?",
            run_config=_run_config(agents, model),
        )
        async for _event in result.stream_events():
            pass
        return result

    run = asyncio.run(stream())
    evidence = integration.render_run(run)

    assert evidence.target.startswith("# Final output\nLisbon is 21C and clear.\n")
    assert "[4] Specialist tool result lookup_weather: Lisbon: 21C, clear" in evidence.target
    assert evidence.metadata["final_agent"] == "Specialist"


def test_sdk_run_grades_end_to_end_with_local_backend(sdk):
    agents, testing = sdk
    grader = _ScriptedGrader()
    backends.register(grader, replace=True)

    run = asyncio.run(
        agents.Runner.run(
            _build_agents(agents),
            "What is the weather in Lisbon?",
            run_config=_run_config(agents, _scripted_model(testing)),
        )
    )
    result = integration.assess_run(run, rubric=RUBRIC, backend="scripted-grader")

    assert result.aggregate == 8.0
    assert result.coverage.status == "complete"
    assert [score["dim_id"] for score in result.per_dim_scores] == ["grounding", "routing", "directness"]
    assert result.evidence_citations[0]["citations"][0]["quote"] == "Lisbon: 21C, clear"
    assert result.receipt["inputs"]["target_path"] == "openai-agents:run"
    assert result.receipt["inputs"]["context_path"] == "openai-agents:task"
    assert len(grader.prompts) == 6  # three evidence calls, then three score calls
    assert all("Lisbon: 21C, clear" in prompt for prompt in grader.prompts[:3])
    payload = json.loads(result.to_json())
    assert payload["aggregate"] == 8.0


def test_sdk_tool_guardrail_rejection_is_reported(sdk):
    """A real `ToolGuardrailFunctionOutput` exposes no `tripwire_triggered`."""
    agents, testing = sdk
    from agents.tool_guardrails import (
        ToolGuardrailFunctionOutput,
        ToolInputGuardrailResult,
        tool_input_guardrail,
    )

    @tool_input_guardrail(name="secrets_screen")
    def secrets_screen(data):  # pragma: no cover - inspected, never invoked
        return ToolGuardrailFunctionOutput.allow()

    run = asyncio.run(
        agents.Runner.run(
            _build_agents(agents),
            "What is the weather in Lisbon?",
            run_config=_run_config(agents, _scripted_model(testing)),
        )
    )
    rejection = ToolGuardrailFunctionOutput.reject_content("blocked: secret in arguments")
    assert not hasattr(rejection, "tripwire_triggered")
    run.tool_input_guardrail_results = [
        ToolInputGuardrailResult(guardrail=secrets_screen, output=rejection)
    ]

    evidence = integration.render_run(run)

    assert evidence.metadata["guardrails_triggered"] == ["secrets_screen"]
    assert "Guardrail tripwires: secrets_screen" in evidence.context


def test_sdk_hosted_tool_call_and_reasoning_content_render(sdk):
    """Hosted calls carry no `name`; reasoning may arrive without a summary."""
    agents, _testing = sdk
    from openai.types.responses import ResponseComputerToolCall
    from openai.types.responses.response_reasoning_item import ResponseReasoningItem

    agent = agents.Agent(name="Operator", instructions="Drive the computer.")
    reasoning = agents.items.ReasoningItem(
        agent=agent,
        raw_item=ResponseReasoningItem(
            id="rs_1",
            type="reasoning",
            summary=[],
            content=[{"type": "reasoning_text", "text": "Take a screenshot first."}],
        ),
    )
    call = agents.items.ToolCallItem(
        agent=agent,
        raw_item=ResponseComputerToolCall(
            id="cu_1",
            call_id="call_cu_1",
            type="computer_call",
            status="completed",
            action={"type": "screenshot"},
            pending_safety_checks=[],
        ),
        _resolved_tool_name="computer_use",
    )
    output = agents.items.ToolCallOutputItem(
        agent=agent,
        raw_item={"type": "computer_call_output", "call_id": "call_cu_1", "output": {}},
        output="screenshot captured",
    )
    run = SimpleNamespace(
        input="Show me the screen.",
        new_items=[reasoning, call, output],
        raw_responses=[],
        final_output="Done.",
        last_agent=agent,
    )

    evidence = integration.render_run(run)

    assert "[1] Operator reasoning: Take a screenshot first." in evidence.target
    assert "[2] Operator tool call computer_use(" in evidence.target
    assert "[3] Operator tool result computer_use: screenshot captured" in evidence.target
