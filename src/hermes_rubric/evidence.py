"""Stage 2: collect per-dimension evidence with explicit hedge annotation."""

import json
from pathlib import Path
from typing import Any

from . import backends

_EVIDENCE_PROMPT_TEMPLATE = """\
You are an evidence collector. Your job: find observable evidence in the target content for ONE rubric dimension.

DIMENSION: {dim_name}
DESCRIPTION: {dim_description}
EVIDENCE INSTRUCTIONS: {evidence_instructions}

TARGET CONTENT (excerpt, may be truncated):
---
{target_content}
---

Instructions:
- Cite specific, observable evidence. Quote short passages (≤30 words) or reference a specific section.
- If you cannot find clear evidence for this dimension, say so explicitly — do NOT invent.
- Mark confidence as: "high" (clear direct evidence found), "medium" (indirect or partial evidence), or "low" (little or no observable evidence).
- If confidence is "low", set hedge=true.
- Do NOT score yet. Evidence collection only.

Output valid JSON only. No prose before or after.

Format:
{{
  "dim_id": "{dim_id}",
  "evidence_found": true or false,
  "confidence": "high" | "medium" | "low",
  "hedge": false,
  "citations": [
    {{"quote": "<exact short quote or section reference>", "location": "<file:line or section name>"}}
  ],
  "evidence_summary": "<1-2 sentence summary of what the evidence shows>"
}}
"""


def collect_evidence(
    rubric: dict[str, Any],
    target_content: str,
    target_path: str,
    backend: str | None = None,
) -> list[dict[str, Any]]:
    """Collect evidence for each rubric dimension. Returns list of evidence dicts."""
    evidence_list = []
    dims = rubric.get("dimensions", [])

    for dim in dims:
        ev = _collect_one(dim, target_content, target_path, backend)
        evidence_list.append(ev)

    return evidence_list


def _collect_one(
    dim: dict[str, Any],
    target_content: str,
    target_path: str,
    backend: str | None,
) -> dict[str, Any]:
    # Truncate target to keep prompts manageable
    max_chars = 6000
    excerpt = target_content[:max_chars]
    if len(target_content) > max_chars:
        excerpt += f"\n[... truncated at {max_chars} chars of {len(target_content)} total ...]"

    prompt = _EVIDENCE_PROMPT_TEMPLATE.format(
        dim_id=dim["id"],
        dim_name=dim["name"],
        dim_description=dim["description"],
        evidence_instructions=dim["evidence_instructions"],
        target_content=excerpt,
    )

    raw = backends.call(prompt, backend=backend)
    try:
        ev = _extract_json(raw)
    except ValueError:
        # Fallback: low-confidence placeholder
        ev = {
            "dim_id": dim["id"],
            "evidence_found": False,
            "confidence": "low",
            "hedge": True,
            "citations": [],
            "evidence_summary": f"Evidence collection failed (JSON parse error). Raw: {raw[:200]}",
        }

    # Enforce hedge rule: low confidence always sets hedge=true
    if ev.get("confidence") == "low":
        ev["hedge"] = True

    ev["dim_name"] = dim["name"]
    return ev


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:  # noqa: silent
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:  # noqa: silent
            pass
    raise ValueError(f"Cannot extract JSON from evidence response: {text[:300]}")


def read_target(target_path: str) -> tuple[str, str]:
    """Read target file(s). Returns (content, resolved_path)."""
    p = Path(target_path).expanduser()

    if p.is_file():
        return p.read_text(errors="replace"), str(p)

    if p.is_dir():
        # Concatenate all text files in the directory (up to 50 files, 8K chars each)
        parts = []
        count = 0
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix in (".md", ".py", ".txt", ".json", ".yaml", ".toml", ".rst"):
                try:
                    text = f.read_text(errors="replace")[:8000]
                    parts.append(f"=== {f.relative_to(p)} ===\n{text}")
                    count += 1
                    if count >= 50:
                        parts.append("[... more files truncated ...]")
                        break
                except OSError:
                    continue
        return "\n\n".join(parts), str(p)

    raise FileNotFoundError(f"Target not found: {target_path}")


def read_context(context_path: str) -> str:
    """Read context file(s) for rubric synthesis."""
    import glob as glob_mod

    p = Path(context_path).expanduser()
    if p.is_file():
        return p.read_text(errors="replace")[:8000]

    # Try glob
    matches = sorted(glob_mod.glob(str(p)))
    if matches:
        parts = []
        for m in matches[:5]:
            try:
                parts.append(Path(m).read_text(errors="replace")[:4000])
            except OSError:
                continue
        return "\n\n---\n\n".join(parts)

    return f"[context path not found: {context_path}]"
