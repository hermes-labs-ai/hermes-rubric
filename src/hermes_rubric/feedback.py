"""Policy-neutral feedback derived from an assessment result."""

from __future__ import annotations

from .models import AssessmentResult, FeedbackPacket, FeedbackPolicy, Finding


def build_feedback(result: AssessmentResult, policy: FeedbackPolicy) -> FeedbackPacket:
    evidence_by_id = {
        item.get("dim_id"): item for item in result.evidence_citations if item.get("dim_id")
    }
    findings: list[Finding] = []
    strengths: list[str] = []

    for score in result.per_dim_scores:
        dim_id = score.get("dim_id")
        name = score.get("dim_name") or dim_id or "Unnamed dimension"
        evidence = evidence_by_id.get(dim_id, {})
        has_accepted_evidence = bool(evidence.get("evidence_found")) and bool(
            evidence.get("citations")
        )
        hedged = bool(evidence.get("hedge")) or evidence.get("confidence") == "low"

        if not has_accepted_evidence or hedged:
            reason = (
                "accepted evidence is missing"
                if not has_accepted_evidence
                else "the available evidence is low-confidence or hedged"
            )
            findings.append(
                Finding(
                    kind="evidence_gap",
                    dimension_id=dim_id,
                    dimension_name=name,
                    score=_numeric_score(score.get("score")),
                    message=f"{reason.capitalize()} for this dimension.",
                    action="Provide checkable evidence or inspect this dimension manually.",
                )
            )
            continue

        numeric_score = _numeric_score(score.get("score"))
        if policy.minimum_score is not None and numeric_score is not None:
            if numeric_score < float(policy.minimum_score):
                findings.append(
                    Finding(
                        kind="quality_gap",
                        dimension_id=dim_id,
                        dimension_name=name,
                        score=numeric_score,
                        message=(
                            f"Inspected evidence supports score {numeric_score:g}, below the "
                            f"caller threshold {float(policy.minimum_score):g}."
                        ),
                        action="Revise the artifact for this dimension, retaining supported strengths.",
                    )
                )
            elif policy.include_strengths:
                strengths.append(f"{name} ({numeric_score:g}/10)")

    coverage_finding: Finding | None = None
    if result.coverage.status != "complete":
        limitation = " ".join(result.coverage.limitations) or (
            "The evidence stage could not establish complete target visibility."
        )
        coverage_finding = Finding(
            kind="coverage_gap",
            message=limitation,
            action="Expand or rerun inspection before treating missing evidence as absence.",
        )

    dimension_limit = policy.max_findings - (1 if coverage_finding is not None else 0)
    bounded_findings = findings[:dimension_limit]
    if coverage_finding is not None:
        bounded_findings.append(coverage_finding)
    return FeedbackPacket(
        findings=tuple(bounded_findings),
        policy=policy,
        strengths=tuple(strengths),
    )


def _numeric_score(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
