"""OpenAI Agents SDK adapter backed by the Hermes Rubric assessment transaction.

The adapter reads a completed ``RunResult`` (or a finished
``RunResultStreaming``) from the OpenAI Agents SDK, renders it into literal
Hermes target and context text, and runs the framework-neutral assessment
over that text. It never re-runs the agent or calls a model itself, and it
does not import the SDK: any object exposing the ``RunResult`` attributes
(``new_items``, ``final_output``, ``input``, ``last_agent``) is accepted, so
recorded runs and lightweight stand-ins grade through the same path.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from hermes_rubric import AssessmentResult, assess, assess_async

__all__ = ["RunEvidence", "assess_run", "assess_run_async", "render_run"]

TARGET_NAME = "openai-agents:run"
CONTEXT_NAME = "openai-agents:task"

_RUN_ATTRIBUTES = ("new_items", "final_output")
_GUARDRAIL_RESULT_ATTRIBUTES = (
    "input_guardrail_results",
    "output_guardrail_results",
    "tool_input_guardrail_results",
    "tool_output_guardrail_results",
)


@dataclass(frozen=True)
class RunEvidence:
    """Literal assessment inputs rendered from one agent run.

    ``target`` is the artifact Hermes cites and scores; ``context`` is the
    task framing used for rubric synthesis and recorded in the receipt;
    ``metadata`` holds run facts (agents, counts, guardrail tripwires, usage)
    for the caller to transport alongside the assessment.
    """

    target: str
    context: str
    metadata: dict[str, Any] = field(default_factory=dict)


def render_run(
    run: Any,
    *,
    include_trace: bool = True,
    extra_context: str | None = None,
) -> RunEvidence:
    """Render an OpenAI Agents run into Hermes target and context text.

    The target opens with the final output so it stays inside the inspected
    window even when a long trace follows. With ``include_trace`` the
    chronological run items (messages, tool calls and results, handoffs,
    reasoning summaries) follow as a numbered transcript. The context carries
    the task input, the participating agents with their instructions, a run
    summary, and any ``extra_context`` supplied by the caller.
    """
    _require_run(run)
    items = list(getattr(run, "new_items", None) or [])
    agents = _agents_in_order(run, items)
    tool_names = _tool_names_by_call_id(items)
    metadata = _metadata(run, items, agents)

    target_lines = ["# Final output", _final_output_text(run)]
    if include_trace:
        trace = [
            _render_item(index, item, tool_names)
            for index, item in enumerate(items, start=1)
        ]
        target_lines.extend(["", "# Run trace"])
        target_lines.extend(trace or ["(no run items)"])
    target = "\n".join(target_lines).rstrip() + "\n"

    context_lines = ["# Task input", _render_input(getattr(run, "input", None)), "", "# Agents"]
    context_lines.extend(f"- {name}: {_instructions_text(agent)}" for name, agent in agents)
    if not agents:
        context_lines.append("(no agents recorded)")
    guardrails = metadata["guardrails_triggered"]
    context_lines.extend(
        [
            "",
            "# Run summary",
            _summary_line(metadata),
            "Guardrail tripwires: " + (", ".join(guardrails) if guardrails else "none"),
        ]
    )
    if extra_context:
        context_lines.extend(["", "# Caller context", extra_context.strip()])
    context = "\n".join(context_lines).rstrip() + "\n"
    return RunEvidence(target=target, context=context, metadata=metadata)


def assess_run(
    run: Any,
    *,
    intent: str | None = None,
    rubric: Mapping[str, Any] | None = None,
    artifact_class: str | None = None,
    backend: str | None = None,
    target_type: str = "agent-output",
    include_trace: bool = True,
    extra_context: str | None = None,
    **assess_kwargs: Any,
) -> AssessmentResult:
    """Assess a completed OpenAI Agents run with cited Hermes evidence.

    Supply exactly one of ``intent``, ``rubric``, or ``artifact_class``, as
    with :func:`hermes_rubric.assess`. The rendered run (see
    :func:`render_run`) becomes the target and context; remaining keyword
    arguments such as ``target_window_bytes`` or ``batch`` pass through to
    :func:`hermes_rubric.assess`. Assessment errors propagate unchanged so the
    caller keeps the normalized stage.
    """
    evidence = render_run(run, include_trace=include_trace, extra_context=extra_context)
    return assess(
        evidence.target,
        intent=intent,
        rubric=rubric,
        artifact_class=artifact_class,
        backend=backend,
        context=evidence.context,
        target_type=target_type,
        target_name=TARGET_NAME,
        context_name=CONTEXT_NAME,
        **assess_kwargs,
    )


async def assess_run_async(
    run: Any,
    *,
    intent: str | None = None,
    rubric: Mapping[str, Any] | None = None,
    artifact_class: str | None = None,
    backend: str | None = None,
    target_type: str = "agent-output",
    include_trace: bool = True,
    extra_context: str | None = None,
    **assess_kwargs: Any,
) -> AssessmentResult:
    """Run :func:`assess_run` without blocking the caller's event loop."""
    evidence = render_run(run, include_trace=include_trace, extra_context=extra_context)
    return await assess_async(
        evidence.target,
        intent=intent,
        rubric=rubric,
        artifact_class=artifact_class,
        backend=backend,
        context=evidence.context,
        target_type=target_type,
        target_name=TARGET_NAME,
        context_name=CONTEXT_NAME,
        **assess_kwargs,
    )


# --- rendering helpers -----------------------------------------------------


def _require_run(run: Any) -> None:
    missing = [name for name in _RUN_ATTRIBUTES if not hasattr(run, name)]
    if missing:
        raise TypeError(
            "expected an OpenAI Agents SDK RunResult (or a finished "
            f"RunResultStreaming); {type(run).__name__} lacks {', '.join(missing)}"
        )


def _render_item(index: int, item: Any, tool_names: Mapping[str, str]) -> str:
    kind = getattr(item, "type", None) or type(item).__name__
    prefix = f"[{index}] {_agent_name(getattr(item, 'agent', None))}"
    raw = getattr(item, "raw_item", None)
    if kind == "message_output_item":
        return f"{prefix} message: {_message_text(raw)}"
    if kind == "tool_call_item":
        return f"{prefix} tool call {_call_name(raw)}({_call_arguments(raw)})"
    if kind == "tool_call_output_item":
        name = tool_names.get(str(_field(raw, "call_id")), "tool")
        output = getattr(item, "output", None)
        if output is None:
            output = _field(raw, "output")
        return f"{prefix} tool result {name}: {_text(output)}"
    if kind == "handoff_call_item":
        return f"{prefix} handoff call {_call_name(raw)}({_call_arguments(raw)})"
    if kind == "handoff_output_item":
        source = _agent_name(getattr(item, "source_agent", None))
        target = _agent_name(getattr(item, "target_agent", None))
        return f"{prefix} handoff {source} -> {target}"
    if kind == "reasoning_item":
        return f"{prefix} reasoning summary: {_reasoning_text(raw) or '(none)'}"
    return f"{prefix} {kind}: {_compact_json(_dump(raw))}"


def _render_input(value: Any) -> str:
    if value is None:
        return "(none)"
    if isinstance(value, str):
        return value
    lines = []
    for entry in value:
        role = _field(entry, "role")
        if role is not None:
            lines.append(f"- {role}: {_content_text(_field(entry, 'content'))}")
            continue
        kind = _field(entry, "type") or type(entry).__name__
        lines.append(f"- {kind}: {_compact_json(_dump(entry))}")
    return "\n".join(lines) if lines else "(none)"


def _final_output_text(run: Any) -> str:
    output = getattr(run, "final_output", None)
    if output is None:
        return "(no final output)"
    return _text(output)


def _message_text(raw: Any) -> str:
    content = _field(raw, "content")
    if content is None:
        return _text(raw)
    return _content_text(content)


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for part in content:
        text = _field(part, "text")
        if text is None:
            refusal = _field(part, "refusal")
            text = f"[refusal] {refusal}" if refusal is not None else _compact_json(_dump(part))
        parts.append(str(text))
    return "".join(parts)


def _reasoning_text(raw: Any) -> str:
    summary = _field(raw, "summary") or []
    return " ".join(str(_field(part, "text") or "") for part in summary).strip()


def _call_name(raw: Any) -> str:
    name = _field(raw, "name")
    if name:
        return str(name)
    return str(_field(raw, "type") or "call")


def _call_arguments(raw: Any) -> str:
    arguments = _field(raw, "arguments")
    if arguments is not None:
        return _text(arguments)
    dumped = _dump(raw)
    if isinstance(dumped, dict):
        dumped = {k: v for k, v in dumped.items() if k not in {"id", "type", "name", "status"}}
    return _compact_json(dumped)


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return _compact_json(_dump(value))


def _dump(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _dump(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump(v) for v in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _dump(model_dump(exclude_none=True))
        except TypeError:
            return _dump(model_dump())
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _dump(dataclasses.asdict(value))
    return str(value)


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _field(obj: Any, key: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


def _agent_name(agent: Any) -> str:
    if agent is None:
        return "agent"
    name = getattr(agent, "name", None)
    return str(name) if name else type(agent).__name__


def _instructions_text(agent: Any) -> str:
    instructions = getattr(agent, "instructions", None)
    if instructions is None:
        return "(no instructions)"
    if isinstance(instructions, str):
        return " ".join(instructions.split())
    if callable(instructions):
        return "(dynamic instructions)"
    return " ".join(str(instructions).split())


def _last_agent(run: Any) -> Any:
    try:
        return getattr(run, "last_agent", None)
    except Exception:  # noqa: BLE001 - SDK may have released a weak reference
        return None


def _agents_in_order(run: Any, items: list[Any]) -> list[tuple[str, Any]]:
    ordered: dict[str, Any] = {}
    for item in items:
        for candidate in (
            getattr(item, "agent", None),
            getattr(item, "source_agent", None),
            getattr(item, "target_agent", None),
        ):
            if candidate is not None:
                ordered.setdefault(_agent_name(candidate), candidate)
    last = _last_agent(run)
    if last is not None:
        ordered.setdefault(_agent_name(last), last)
    return list(ordered.items())


def _tool_names_by_call_id(items: list[Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for item in items:
        if getattr(item, "type", None) in {"tool_call_item", "handoff_call_item"}:
            raw = getattr(item, "raw_item", None)
            call_id = _field(raw, "call_id")
            if call_id is not None:
                names[str(call_id)] = _call_name(raw)
    return names


def _guardrails_triggered(run: Any) -> list[str]:
    triggered = []
    for attribute in _GUARDRAIL_RESULT_ATTRIBUTES:
        for result in getattr(run, attribute, None) or []:
            output = getattr(result, "output", None)
            if getattr(output, "tripwire_triggered", False):
                guardrail = getattr(result, "guardrail", None)
                name = getattr(guardrail, "name", None) or attribute
                triggered.append(str(name))
    return triggered


def _usage(run: Any) -> dict[str, int] | None:
    usage = getattr(getattr(run, "context_wrapper", None), "usage", None)
    if usage is None:
        return None
    facts = {}
    for key in ("requests", "input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage, key, None)
        if isinstance(value, int) and not isinstance(value, bool):
            facts[key] = value
    return facts or None


def _metadata(run: Any, items: list[Any], agents: list[tuple[str, Any]]) -> dict[str, Any]:
    kinds = [getattr(item, "type", None) for item in items]
    last = _last_agent(run)
    final_output = getattr(run, "final_output", None)
    metadata: dict[str, Any] = {
        "final_agent": _agent_name(last) if last is not None else None,
        "agents": [name for name, _ in agents],
        "run_items": len(items),
        "model_responses": len(getattr(run, "raw_responses", None) or []),
        "tool_calls": kinds.count("tool_call_item"),
        "handoffs": kinds.count("handoff_call_item"),
        "final_output_type": type(final_output).__name__ if final_output is not None else None,
        "guardrails_triggered": _guardrails_triggered(run),
    }
    usage = _usage(run)
    if usage is not None:
        metadata["usage"] = usage
    return metadata


def _summary_line(metadata: Mapping[str, Any]) -> str:
    final_agent = metadata.get("final_agent") or "unknown"
    return (
        f"{metadata['model_responses']} model responses, {metadata['tool_calls']} tool calls, "
        f"{metadata['handoffs']} handoffs, {metadata['run_items']} run items; "
        f"final agent {final_agent}."
    )
