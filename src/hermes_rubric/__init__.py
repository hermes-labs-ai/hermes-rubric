"""hermes-rubric — evidence-first structured scoring."""

__version__ = "1.2.0"

from .assessment import assess, assess_async, assess_path, assess_path_async
from .errors import AssessmentError
from .models import (
    SCHEMA_VERSION,
    AssessmentResult,
    CoverageReport,
    FeedbackPacket,
    FeedbackPolicy,
    Finding,
)

__all__ = [
    "SCHEMA_VERSION",
    "AssessmentError",
    "AssessmentResult",
    "CoverageReport",
    "FeedbackPacket",
    "FeedbackPolicy",
    "Finding",
    "__version__",
    "assess",
    "assess_async",
    "assess_path",
    "assess_path_async",
]
