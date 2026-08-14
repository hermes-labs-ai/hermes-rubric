"""Framework-neutral Hermes assessment example."""

from __future__ import annotations

from hermes_rubric import AssessmentError, FeedbackPolicy, assess


def assess_agent_output(agent_output: str, task_context: str) -> dict:
    """Return portable assessment and feedback dictionaries."""
    try:
        result = assess(
            agent_output,
            intent="Answer accurately and support material claims with checkable evidence.",
            context=task_context,
            target_type="agent-output",
        )
    except AssessmentError as error:
        return {"error_stage": error.stage, "message": str(error)}

    feedback = result.feedback(FeedbackPolicy(minimum_score=7.0))
    return {
        "assessment": result.to_dict(),
        "feedback": feedback.to_dict(),
        "revision_prompt": feedback.to_prompt(),
    }
