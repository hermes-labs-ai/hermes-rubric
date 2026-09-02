"""Inspect AI scorer backed by the Hermes Rubric assessment transaction."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from inspect_ai.scorer import Score, Scorer, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState

from hermes_rubric import AssessmentError, assess_async


@scorer(metrics=[mean(), stderr()])
def hermes_rubric_scorer(
    *,
    intent: str | None = None,
    rubric: Mapping[str, Any] | None = None,
    artifact_class: str | None = None,
    backend: str | None = None,
    target_type: str = "agent-output",
    fail_on_error: bool = True,
) -> Scorer:
    """Score Inspect model output with cited Hermes Rubric evidence.

    Supply exactly one of ``intent``, ``rubric``, or ``artifact_class``. The
    Inspect sample input and target become assessment context; the model's
    completion is the artifact being assessed. Scores retain Hermes' 0-10
    scale and preserve the complete assessment in Inspect score metadata.

    By default an assessment failure fails the scorer. Set ``fail_on_error``
    to false to record a visible unscored sample instead.
    """

    async def score(state: TaskState, target: Target) -> Score:
        context = (
            f"Inspect sample input:\n{state.input_text}\n\n"
            f"Inspect reference target:\n{target.text}"
        )
        try:
            result = await assess_async(
                state.output.completion,
                intent=intent,
                rubric=rubric,
                artifact_class=artifact_class,
                backend=backend,
                context=context,
                target_type=target_type,
            )
        except (AssessmentError, RuntimeError) as error:
            if fail_on_error:
                raise
            return Score.unscored(
                answer=state.output.completion,
                explanation=str(error),
                metadata={
                    "hermes_rubric": {
                        "status": "error",
                        "reason": "grader_failed",
                        "stage": getattr(error, "stage", None),
                    }
                },
            )

        payload = result.to_dict()
        return Score(
            value=result.aggregate,
            answer=state.output.completion,
            explanation=_explanation(payload),
            metadata={"hermes_rubric": payload},
        )

    return score


def _explanation(payload: Mapping[str, Any]) -> str:
    coverage = payload["coverage"]
    lines = [
        f"Hermes Rubric aggregate: {payload['aggregate']}/{payload['max_possible']}",
        f"Evidence coverage: {coverage['status']}",
    ]
    lines.extend(
        f"- {item.get('name', item.get('dim_id', 'dimension'))}: "
        f"{item.get('score', 'unscored')}"
        for item in payload["dim_summaries"]
    )
    return "\n".join(lines)
