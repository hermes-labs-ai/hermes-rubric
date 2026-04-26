"""Class-aware rubric templates.

When --artifact-class is specified, the synthesizer SKIPS LLM rubric synthesis and
loads a deterministic dim set from the corresponding YAML. This addresses the
non-determinism issue where Stage-1 synthesis produces different dims on every run.

Each YAML defines:
  - artifact_class: identifier
  - description: one-line purpose
  - target_window_bytes: per-class override of --target-window-bytes default
  - dimensions: list of {id, name, description, evidence_instructions, weight, hedge}
  - slop_signatures: list of phrases injected into llm_fool dim's evidence pool
  - voice_priors: list of voice patterns injected into voice_match dim
  - banned_subject_patterns (optional): outreach-email only, for subject_neutrality dim
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

CLASSES_DIR = Path(__file__).parent

AVAILABLE_CLASSES = {
    "social-post",
    "show-hn-post",
    "linkedin-post",
    "outreach-email",
}


def list_classes() -> list[str]:
    """Return sorted list of available artifact classes."""
    return sorted(AVAILABLE_CLASSES)


@functools.lru_cache(maxsize=None)
def load_class(name: str) -> dict[str, Any]:
    """Load a class template by name. Raises ValueError if unknown."""
    if name not in AVAILABLE_CLASSES:
        raise ValueError(
            f"Unknown artifact class: {name!r}. "
            f"Available: {sorted(AVAILABLE_CLASSES)}"
        )
    if yaml is None:
        raise ImportError(
            "PyYAML is required for --artifact-class. Install with `pip install pyyaml`."
        )
    path = CLASSES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Class template not found: {path}")
    with open(path) as fh:
        data = yaml.safe_load(fh)
    _validate_class(data, name)
    return data


def _validate_class(data: dict[str, Any], name: str) -> None:
    required = {"artifact_class", "dimensions"}
    missing = required - set(data or {})
    if missing:
        raise ValueError(f"Class template {name!r} missing fields: {missing}")
    if data["artifact_class"] != name:
        raise ValueError(
            f"Class template name mismatch: file says {data['artifact_class']!r}, "
            f"loaded as {name!r}"
        )
    for dim in data["dimensions"]:
        for field in ("id", "name", "description", "evidence_instructions", "weight"):
            if field not in dim:
                raise ValueError(f"Dim missing field {field!r} in class {name!r}: {dim}")


def to_rubric(class_data: dict[str, Any]) -> dict[str, Any]:
    """Convert a class template into a rubric dict matching synthesize.py output shape.

    The output is exactly the shape downstream evidence/score expect, so callers can
    bypass synthesize() entirely when --artifact-class is set.
    """
    return {
        "rubric_intent": class_data.get(
            "description",
            f"Score against the {class_data['artifact_class']} class template.",
        ),
        "target_type": class_data["artifact_class"],
        "rubric_source": "class-template",  # marks deterministic source for receipts
        "dimensions": [
            {
                "id": dim["id"],
                "name": dim["name"],
                "description": dim["description"],
                "evidence_instructions": dim["evidence_instructions"],
                "weight": dim["weight"],
                "hedge": dim.get("hedge", False),
            }
            for dim in class_data["dimensions"]
        ],
    }
