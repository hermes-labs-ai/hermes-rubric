"""Public exceptions raised by the assessment transaction."""

from __future__ import annotations

from typing import Literal

AssessmentStage = Literal[
    "backend",
    "input",
    "rubric",
    "evidence",
    "score",
    "receipt",
]


class AssessmentError(RuntimeError):
    """A failure at a stable stage of the public assessment pipeline.

    The original exception is retained as ``__cause__`` when Hermes wraps a
    lower-level failure. Callers can use ``stage`` for policy without parsing
    provider-specific exception text.
    """

    def __init__(self, stage: AssessmentStage, message: str) -> None:
        self.stage = stage
        super().__init__(message)
