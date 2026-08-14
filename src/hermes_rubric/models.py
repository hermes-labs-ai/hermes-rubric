"""Typed public models for portable Hermes assessments."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

SCHEMA_VERSION = "1.0"
FindingKind = Literal["quality_gap", "evidence_gap", "coverage_gap"]


@dataclass(frozen=True)
class CoverageReport:
    """What the evidence stage could inspect for this assessment."""

    status: Literal["complete", "partial"]
    strategy: str
    visible_bytes: int | None
    total_bytes: int | None
    considered_sources: int | None = None
    total_sources: int | None = None
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "strategy": self.strategy,
            "visible_bytes": self.visible_bytes,
            "total_bytes": self.total_bytes,
            "considered_sources": self.considered_sources,
            "total_sources": self.total_sources,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class Finding:
    """One policy-aware, transportable next-step finding."""

    kind: FindingKind
    message: str
    action: str
    dimension_id: str | None = None
    dimension_name: str | None = None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "message": self.message,
            "action": self.action,
        }
        if self.dimension_id is not None:
            result["dimension_id"] = self.dimension_id
        if self.dimension_name is not None:
            result["dimension_name"] = self.dimension_name
        if self.score is not None:
            result["score"] = self.score
        return result


@dataclass(frozen=True)
class FeedbackPolicy:
    """Caller policy for turning measurements into feedback.

    Hermes does not define a default pass/fail threshold. A quality finding is
    created only when ``minimum_score`` is explicitly supplied by the caller.
    """

    minimum_score: float | None = None
    include_strengths: bool = True
    max_findings: int = 20

    def __post_init__(self) -> None:
        if self.minimum_score is not None:
            if isinstance(self.minimum_score, bool) or not isinstance(
                self.minimum_score, (int, float)
            ):
                raise TypeError("minimum_score must be a number or None")
            if not 0 <= float(self.minimum_score) <= 10:
                raise ValueError("minimum_score must be between 0 and 10")
        if isinstance(self.max_findings, bool) or self.max_findings < 1:
            raise ValueError("max_findings must be a positive integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimum_score": self.minimum_score,
            "include_strengths": self.include_strengths,
            "max_findings": self.max_findings,
        }


@dataclass(frozen=True)
class FeedbackPacket:
    """Deterministic feedback that a caller may pass to a revising agent."""

    findings: tuple[Finding, ...]
    policy: FeedbackPolicy
    strengths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
            "strengths": list(self.strengths),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_prompt(self) -> str:
        lines = [
            "Revise or re-check the artifact using this Hermes assessment feedback.",
            "Preserve claims and sections that are already supported.",
        ]
        if self.strengths:
            lines.append("Supported strengths to preserve:")
            lines.extend(f"- {strength}" for strength in self.strengths)
        if not self.findings:
            lines.append("No feedback findings were produced under the caller's policy.")
            return "\n".join(lines)
        lines.append("Findings:")
        for finding in self.findings:
            label = finding.dimension_name or finding.dimension_id or "assessment"
            lines.append(
                f"- [{finding.kind}] {label}: {finding.message} "
                f"Next action: {finding.action}"
            )
        lines.append(
            "Treat coverage gaps as requests to inspect more material, not as proof "
            "that the artifact is defective."
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class AssessmentResult:
    """Typed top-level result with the legacy JSON fields preserved."""

    rubric: dict[str, Any]
    evidence_citations: list[dict[str, Any]]
    per_dim_scores: list[dict[str, Any]]
    aggregate: float
    max_possible: float
    hedge_dims: list[str]
    hedge_note: str
    dim_summaries: list[dict[str, Any]]
    receipt: dict[str, Any]
    coverage: CoverageReport
    schema_version: str = field(default=SCHEMA_VERSION)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rubric": self.rubric,
            "evidence_citations": self.evidence_citations,
            "per_dim_scores": self.per_dim_scores,
            "aggregate": self.aggregate,
            "max_possible": self.max_possible,
            "hedge_dims": self.hedge_dims,
            "hedge_note": self.hedge_note,
            "dim_summaries": self.dim_summaries,
            "receipt": self.receipt,
            "schema_version": self.schema_version,
            "coverage": self.coverage.to_dict(),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def feedback(self, policy: FeedbackPolicy | None = None) -> FeedbackPacket:
        from .feedback import build_feedback

        return build_feedback(self, policy or FeedbackPolicy())
