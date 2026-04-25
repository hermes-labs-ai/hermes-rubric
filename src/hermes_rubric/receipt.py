"""Reproducibility receipt — prompts used, data hashes, backend, timestamp."""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from typing import Any


def build_receipt(
    intent: str,
    context_path: str,
    target_path: str,
    backend: str,
    rubric: dict[str, Any],
    evidence_list: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    target_content: str,
    context_content: str,
) -> dict[str, Any]:
    """Build a reproducibility receipt for the scoring run."""
    return {
        "receipt_version": "1.1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tool_version": "hermes-rubric 0.1.2",
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "backend": backend,
        "inputs": {
            "intent": intent,
            "context_path": context_path,
            "target_path": target_path,
            "target_hash_sha256": _sha256(target_content),
            "context_hash_sha256": _sha256(context_content),
            "target_length_chars": len(target_content),
            "context_length_chars": len(context_content),
        },
        "pipeline": {
            "stage_1_rubric_dimensions": len(rubric.get("dimensions", [])),
            "stage_1_rubric_hash_sha256": rubric_hash(rubric),
            "stage_2_evidence_items": len(evidence_list),
            "stage_3_scores": len(scores),
            "hedge_dimensions": [
                ev["dim_id"] for ev in evidence_list if ev.get("hedge")
            ],
        },
        "reproducibility_note": (
            "Same inputs + same backend + same model version + same rubric_hash should produce "
            "scores within ±1 point. A rubric_hash diff between runs means the measuring stick itself "
            "changed — scores are not directly comparable."
        ),
    }


def rubric_hash(rubric: dict[str, Any]) -> str:
    """Stable hash of the synthesized rubric — pins the measuring stick across runs.

    Uses sort_keys so field ordering doesn't perturb the hash. Covers dimensions,
    their descriptions, evidence instructions, and weights — everything that
    affects how the target is measured.
    """
    payload = json.dumps(rubric, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
