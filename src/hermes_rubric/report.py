"""Deterministic, backend-free presentation of an existing assessment."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .models import AssessmentResult


def _text(value: Any) -> str:
    """Keep assessment-authored text literal in a Markdown report."""
    text = html.escape(str(value), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", " ".join(text.split()))


def _number(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("assessment scores must be finite numbers")
    if not math.isfinite(value):
        raise ValueError("assessment scores must be finite numbers")
    return str(value)


def render_markdown(result: AssessmentResult | Mapping[str, Any]) -> str:
    """Render stored values without rescoring, applying policy, or calling a model.

    Legacy results without coverage metadata are explicitly marked unknown.
    The original result, JSON schema, and ordering are preserved.
    """
    data = result.to_dict() if isinstance(result, AssessmentResult) else result
    if not isinstance(data, Mapping):
        raise ValueError("assessment must be a JSON object or AssessmentResult")
    try:
        scores = data["per_dim_scores"]
        evidence = data["evidence_citations"]
        aggregate = _number(data["aggregate"])
        maximum = _number(data["max_possible"])
    except KeyError as exc:
        raise ValueError(f"missing assessment field: {exc.args[0]}") from exc
    if not isinstance(scores, list) or not isinstance(evidence, list):
        raise ValueError("per_dim_scores and evidence_citations must be arrays")
    evidence_by_id: dict[str, Mapping[str, Any]] = {}
    for item in evidence:
        if not isinstance(item, Mapping) or not isinstance(item.get("dim_id"), str):
            raise ValueError("each evidence item must have a string dim_id")
        if item["dim_id"] in evidence_by_id:
            raise ValueError(f"duplicate evidence dim_id: {item['dim_id']}")
        evidence_by_id[item["dim_id"]] = item

    coverage = data.get("coverage")
    if coverage is not None and not isinstance(coverage, Mapping):
        raise ValueError("coverage must be an object")
    coverage = coverage or {}
    status = coverage.get("status", "unknown (not recorded)")
    lines = ["# Hermes Rubric assessment", "", "## Coverage", "",
             f"**Status:** {_text(status)}"]
    if coverage.get("strategy"):
        lines.append(f"**Strategy:** {_text(coverage['strategy'])}")
    for label, visible, total in (
        ("Bytes inspected", "visible_bytes", "total_bytes"),
        ("Sources considered", "considered_sources", "total_sources"),
    ):
        if coverage.get(visible) is not None or coverage.get(total) is not None:
            shown = coverage.get(visible)
            available = coverage.get(total)
            lines.append(f"**{label}:** {_text(shown if shown is not None else 'not recorded')} / "
                         f"{_text(available if available is not None else 'not recorded')}")
    limitations = coverage.get("limitations", [])
    if not isinstance(limitations, (list, tuple)):
        raise ValueError("coverage limitations must be an array")
    lines.extend(f"- {_text(limitation)}" for limitation in limitations)
    if status != "complete":
        lines.extend(["", "Uninspected material is not evidence of an absent feature or defect."])
    lines.extend(["", "## Scores", "", f"**Aggregate:** {aggregate} / {maximum}",
                  "", "The aggregate is a measurement, not a pass/fail verdict."])
    hedge_ids = data.get("hedge_dims", [])
    seen_scores: set[str] = set()
    for score in scores:
        if not isinstance(score, Mapping) or not isinstance(score.get("dim_id"), str):
            raise ValueError("each score must have a string dim_id")
        dim_id = score["dim_id"]
        if dim_id in seen_scores:
            raise ValueError(f"duplicate score dim_id: {dim_id}")
        seen_scores.add(dim_id)
        ev = evidence_by_id.get(dim_id, {})
        lines.extend(["", f"### {_text(score.get('dim_name', dim_id))} ({_text(dim_id)})", "",
                      f"**Score:** {_number(score.get('score'))}"])
        hedged = bool(score.get("hedge_applied") or ev.get("hedge") or dim_id in hedge_ids)
        lines.append(f"**Hedged:** {'yes' if hedged else 'no'}")
        found = ev.get("evidence_found")
        lines.append(f"**Evidence found:** {'yes' if found is True else 'no' if found is False else 'not recorded'}")
        for label, value in (("Rationale", score.get("score_rationale")),
                             ("Evidence driving score", score.get("evidence_drove_score")),
                             ("Evidence summary", ev.get("evidence_summary"))):
            if value:
                lines.append(f"**{label}:** {_text(value)}")
        citations = ev.get("citations", [])
        if not isinstance(citations, list) or any(not isinstance(c, Mapping) for c in citations):
            raise ValueError("citations must be an array of objects")
        lines.extend(f"- {_text(c.get('location', 'location not recorded'))}: "
                     f"{_text(c.get('quote', 'quote not recorded'))}" for c in citations)
    if data.get("hedge_note"):
        lines.extend(["", f"**Hedge note:** {_text(data['hedge_note'])}"])
    receipt = data.get("receipt", {})
    if not isinstance(receipt, Mapping):
        raise ValueError("receipt must be an object")
    lines.extend(["", "## Receipt", ""])
    if receipt:
        # Fenced JSON preserves the complete recorded identity/provenance, including
        # backend-specific fields, without inventing a fresh receipt or timestamp.
        serialized = json.dumps(dict(receipt), indent=2, ensure_ascii=False, sort_keys=True,
                                allow_nan=False)
        fence = "`" * max(3, max((len(m[0]) + 1 for m in re.finditer(r"`+", serialized)), default=3))
        lines.extend([f"{fence}json", serialized, fence])
    else:
        lines.append("No receipt was recorded.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes-rubric render",
                                     description="Render existing assessment JSON as Markdown; no backend calls.")
    parser.add_argument("result", help="Assessment JSON file, or - for stdin")
    parser.add_argument("--out", help="Write Markdown to a file instead of stdout")
    args = parser.parse_args(argv)
    try:
        source = sys.stdin.read() if args.result == "-" else Path(args.result).expanduser().read_text(encoding="utf-8")
        output = render_markdown(json.loads(source))
        if args.out:
            destination = Path(args.out).expanduser()
            if args.result != "-":
                original = Path(args.result).expanduser()
                if (destination.resolve() == original.resolve()
                        or (destination.exists() and destination.samefile(original))):
                    raise ValueError("output must differ from the source assessment JSON")
            destination.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR rendering assessment: {exc}", file=sys.stderr)
        return 2
    return 0
