"""The framework-neutral Hermes assessment transaction."""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from . import backends
from .classes import load_class, to_rubric
from .errors import AssessmentError, AssessmentStage
from .evidence import _utf8_prefix, collect_evidence
from .inputs import LoadedInput, load_context_path, load_target_path, load_text
from .models import AssessmentResult
from .receipt import build_receipt
from .score import compute_aggregate, score_dimensions
from .synthesize import _validate_rubric, synthesize

ProgressCallback = Callable[[str], None]


def assess(
    target: str,
    *,
    intent: str | None = None,
    context: str | None = None,
    target_name: str = "<memory>",
    context_name: str = "<memory>",
    target_type: str = "document",
    rubric: Mapping[str, Any] | None = None,
    artifact_class: str | None = None,
    backend: str | None = None,
    batch: bool = False,
    target_window_bytes: int = 8000,
    context_window_bytes: int = 8000,
    scope_class: str | None = None,
    intent_debias: bool = False,
) -> AssessmentResult:
    """Assess an in-memory target with one call.

    ``target`` and ``context`` are always literal text. Use :func:`assess_path`
    for filesystem inputs. Exactly one rubric source is used: ``rubric``,
    ``artifact_class``, or synthesis from ``intent`` plus ``context``.
    """
    try:
        target_input = load_text(target, name=target_name)
        context_input = load_text(context if context is not None else "", name=context_name)
    except (TypeError, ValueError) as exc:
        raise AssessmentError("input", str(exc)) from exc
    return _run_assessment(
        target_input,
        context_input,
        intent=intent,
        target_type=target_type,
        rubric=rubric,
        artifact_class=artifact_class,
        backend=backend,
        batch=batch,
        target_window_bytes=target_window_bytes,
        context_window_bytes=context_window_bytes,
        scope_class=scope_class,
        intent_debias=intent_debias,
    )


def assess_path(
    target_path: str | Path,
    *,
    intent: str | None = None,
    context_path: str | Path | None = None,
    target_type: str = "document",
    rubric: Mapping[str, Any] | None = None,
    artifact_class: str | None = None,
    backend: str | None = None,
    batch: bool = False,
    target_window_bytes: int = 8000,
    context_window_bytes: int = 8000,
    scope_class: str | None = None,
    intent_debias: bool = False,
    _progress: ProgressCallback | None = None,
) -> AssessmentResult:
    """Assess a target file or directory, with an optional context path/glob."""
    try:
        target_input = load_target_path(target_path, window_bytes=target_window_bytes)
        if context_path is None:
            context_input = load_text("", name="<none>")
        else:
            context_input = load_context_path(
                context_path,
                window_bytes=context_window_bytes,
            )
    except (OSError, TypeError, ValueError) as exc:
        raise AssessmentError("input", str(exc)) from exc
    return _run_assessment(
        target_input,
        context_input,
        intent=intent,
        target_type=target_type,
        rubric=rubric,
        artifact_class=artifact_class,
        backend=backend,
        batch=batch,
        target_window_bytes=target_window_bytes,
        context_window_bytes=context_window_bytes,
        scope_class=scope_class,
        intent_debias=intent_debias,
        progress=_progress,
    )


async def assess_async(target: str, **kwargs: Any) -> AssessmentResult:
    """Run :func:`assess` without blocking the caller's event loop.

    Cancellation stops waiting for the worker thread, but cannot interrupt an
    already-running synchronous provider call.
    """
    return await asyncio.to_thread(assess, target, **kwargs)


async def assess_path_async(target_path: str | Path, **kwargs: Any) -> AssessmentResult:
    """Run :func:`assess_path` without blocking the caller's event loop."""
    return await asyncio.to_thread(assess_path, target_path, **kwargs)


def _run_assessment(
    target_input: LoadedInput,
    context_input: LoadedInput,
    *,
    intent: str | None,
    target_type: str,
    rubric: Mapping[str, Any] | None,
    artifact_class: str | None,
    backend: str | None,
    batch: bool,
    target_window_bytes: int,
    context_window_bytes: int,
    scope_class: str | None,
    intent_debias: bool,
    progress: ProgressCallback | None = None,
) -> AssessmentResult:
    _validate_mode(
        intent=intent,
        context=context_input.content,
        rubric=rubric,
        artifact_class=artifact_class,
        target_window_bytes=target_window_bytes,
        context_window_bytes=context_window_bytes,
    )
    context_for_synthesis, _ = _utf8_prefix(
        context_input.content,
        context_window_bytes,
    )

    try:
        selected_backend = backend or backends.detect()
    except Exception as exc:  # noqa: BLE001 - normalize provider/plugin failures
        _raise_stage("backend", exc)
    _emit(progress, f"backend: {selected_backend}")
    _emit(progress, f"target: {target_input.display_name} ({len(target_input.content)} chars)")
    _emit(progress, f"context: {context_input.display_name} ({len(context_input.content)} chars)")

    try:
        if rubric is not None:
            _emit(progress, "Stage 1: using caller-provided rubric (synthesis bypassed)...")
            selected_rubric = copy.deepcopy(dict(rubric))
            _validate_rubric(selected_rubric)
            selected_rubric["rubric_source"] = "provided"
        elif artifact_class is not None:
            _emit(
                progress,
                f"Stage 1: loading class template {artifact_class!r} (synthesis bypassed)...",
            )
            selected_rubric = to_rubric(load_class(artifact_class))
        else:
            _emit(progress, "Stage 1: synthesizing rubric...")
            selected_rubric = synthesize(
                intent=intent or "",
                context_summary=context_for_synthesis,
                target_type=target_type,
                backend=selected_backend,
                scope_class=scope_class,
                intent_debias=intent_debias,
                target_excerpt=target_input.content,
            )
    except Exception as exc:  # noqa: BLE001 - stable public stage boundary
        _raise_stage("rubric", exc)
    _emit(progress, f"  rubric: {len(selected_rubric['dimensions'])} dimensions")

    try:
        coverage = target_input.coverage(target_window_bytes)
        _emit(progress, "Stage 2: collecting evidence...")
        evidence_list = collect_evidence(
            rubric=selected_rubric,
            target_content=target_input.content,
            target_path=target_input.display_name,
            backend=selected_backend,
            batch=batch,
            target_window_bytes=target_window_bytes,
        )
    except Exception as exc:  # noqa: BLE001 - stable public stage boundary
        _raise_stage("evidence", exc)
    hedge_count = sum(1 for item in evidence_list if item.get("hedge"))
    _emit(progress, f"  evidence: {len(evidence_list)} dimensions, {hedge_count} hedged")

    try:
        _emit(progress, "Stage 3: scoring dimensions...")
        scores = score_dimensions(
            rubric=selected_rubric,
            evidence_list=evidence_list,
            backend=selected_backend,
            batch=batch,
        )
        aggregate_data = compute_aggregate(rubric=selected_rubric, scores=scores)
    except Exception as exc:  # noqa: BLE001 - stable public stage boundary
        _raise_stage("score", exc)
    _emit(progress, f"  aggregate: {aggregate_data['aggregate']}/10")

    try:
        backend_label = selected_backend
        if selected_backend == "claude-cli":
            backend_label = backends.claude_cli_mode()
        if batch:
            backend_label = f"{backend_label}+batch"
        receipt = build_receipt(
            intent=intent
            or (
                f"Score against the {artifact_class} class template."
                if artifact_class is not None
                else selected_rubric.get("rubric_intent", "")
            ),
            context_path=context_input.display_name,
            target_path=target_input.display_name,
            backend=backend_label,
            rubric=selected_rubric,
            evidence_list=evidence_list,
            scores=scores,
            target_content=target_input.content,
            context_content=context_input.content,
            coverage=coverage.to_dict(),
        )
    except Exception as exc:  # noqa: BLE001 - stable public stage boundary
        _raise_stage("receipt", exc)

    return AssessmentResult(
        rubric=selected_rubric,
        evidence_citations=evidence_list,
        per_dim_scores=scores,
        aggregate=aggregate_data["aggregate"],
        max_possible=aggregate_data.get("max_possible", 10.0),
        hedge_dims=aggregate_data["hedge_dims"],
        hedge_note=aggregate_data["hedge_note"],
        dim_summaries=aggregate_data["dim_summaries"],
        receipt=receipt,
        coverage=coverage,
    )


def _validate_mode(
    *,
    intent: str | None,
    context: str,
    rubric: Mapping[str, Any] | None,
    artifact_class: str | None,
    target_window_bytes: int,
    context_window_bytes: int,
) -> None:
    try:
        for name, value in (
            ("target_window_bytes", target_window_bytes),
            ("context_window_bytes", context_window_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if rubric is not None and artifact_class is not None:
            raise ValueError("rubric and artifact_class are mutually exclusive")
        if intent is not None and not isinstance(intent, str):
            raise TypeError("intent must be a string or None")
        if rubric is not None and not isinstance(rubric, Mapping):
            raise TypeError("rubric must be a mapping")
        if rubric is None and artifact_class is None:
            if not intent:
                raise ValueError("intent is required when synthesizing a rubric")
            if not context:
                raise ValueError("context is required when synthesizing a rubric")
    except (TypeError, ValueError) as exc:
        raise AssessmentError("input", str(exc)) from exc


def _raise_stage(stage: AssessmentStage, exc: Exception) -> None:
    if isinstance(exc, AssessmentError):
        raise exc
    raise AssessmentError(stage, str(exc)) from exc


def _emit(callback: ProgressCallback | None, message: str) -> None:
    if callback is not None:
        callback(message)
