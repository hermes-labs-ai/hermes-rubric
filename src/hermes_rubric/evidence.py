"""Stage 2: collect per-dimension evidence with explicit hedge annotation."""

import json
import re
import sys
from pathlib import Path
from typing import Any

from . import backends


class BatchParseError(ValueError):
    """Raised when a batched LLM response cannot be parsed into a dim_id-keyed array."""


class BatchTooLarge(ValueError):
    """Raised when a batched prompt would exceed the safe context ceiling."""


# Conservative input-side ceiling. Per-backend tuning lives in backends.py future work.
_BATCH_PROMPT_CEILING_CHARS = 100_000

DEFAULT_TARGET_WINDOW_BYTES = 8000

# Source-class taxonomy. Higher-authority classes should outweigh marketing prose.
SOURCE_CLASSES = ("code", "test", "config", "readme", "doc", "other")

# Weight applied during scoring — README/doc prose is down-weighted because it
# can be self-marketing. Code and tests are ground-truth.
SOURCE_CLASS_WEIGHT = {
    "code": 1.0,
    "test": 1.0,
    "config": 0.9,
    "doc": 0.7,
    "readme": 0.7,
    "other": 0.8,
}

_README_PAT = re.compile(r"(^|/)(readme|changelog|contributing|code_of_conduct)\b", re.I)
_DOC_PAT = re.compile(r"(^|/)(docs?/|.*\.rst$|AGENTS\.md|INTENT\.md|llms\.txt)", re.I)
_TEST_PAT = re.compile(r"(^|/)tests?/|(?:^|[/_])test_|_test\.", re.I)
_CODE_PAT = re.compile(r"\.(py|js|ts|go|rs|java|c|cpp|h|rb)(\b|:)", re.I)
_CONFIG_PAT = re.compile(r"(pyproject\.toml|setup\.cfg|\.ya?ml|\.toml|\.json|Dockerfile|\.env)($|:)", re.I)


def classify_source(location: str) -> str:
    """Deterministic fallback classifier for a citation location string.

    LLM may also suggest a source_class; we always run this classifier on top
    as a safety net so README prose can't be mis-classified as code.
    """
    if not location:
        return "other"
    loc = location.strip()
    if _TEST_PAT.search(loc):
        return "test"
    if _README_PAT.search(loc):
        return "readme"
    if _DOC_PAT.search(loc):
        return "doc"
    if _CONFIG_PAT.search(loc):
        return "config"
    if _CODE_PAT.search(loc):
        return "code"
    return "other"

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

Each citation MUST include a source_class tag describing WHERE the evidence came from:
- "code"   — source code (e.g. src/*.py, functions, classes, logic)
- "test"   — a test file that asserts behavior
- "config" — config/manifest (pyproject.toml, yaml, json schemas, dotfiles)
- "readme" — README/CHANGELOG/CONTRIBUTING/CODE_OF_CONDUCT
- "doc"    — prose documentation (docs/*, *.rst, AGENTS.md, INTENT.md, llms.txt)
- "other"  — none of the above

Code and test citations are ground-truth; README and doc citations are self-description
and may be marketing. Tag accurately — a later step down-weights README/doc evidence.

Output valid JSON only. No prose before or after.

Format:
{{
  "dim_id": "{dim_id}",
  "evidence_found": true or false,
  "confidence": "high" | "medium" | "low",
  "hedge": false,
  "citations": [
    {{"quote": "<exact short quote or section reference>", "location": "<file:line or section name>", "source_class": "code|test|config|readme|doc|other"}}
  ],
  "evidence_summary": "<1-2 sentence summary of what the evidence shows>"
}}
"""


_BATCHED_EVIDENCE_PROMPT_TEMPLATE = """\
You are an evidence collector. For EACH dimension below, find observable evidence in the target content.

Treat each <DIM> block as ISOLATED. Evidence relevant to one dimension must NOT influence another.
Process all dimensions in one pass.

TARGET CONTENT (excerpt, may be truncated):
---
{target_content}
---

DIMENSIONS:
{dim_blocks}

Instructions:
- For each <DIM>, cite specific, observable evidence. Quote short passages (<=30 words) or reference a specific section.
- If you cannot find clear evidence for a given dimension, say so explicitly for THAT dimension — do NOT invent.
- Mark confidence per dimension: "high" (clear direct evidence), "medium" (indirect/partial), "low" (little/none).
- If confidence is "low", set hedge=true.
- Do NOT score yet. Evidence collection only.

Each citation MUST include source_class: "code"|"test"|"config"|"readme"|"doc"|"other".
Code/test/config are ground-truth; README/doc may be marketing.

Output a JSON ARRAY. One element per <DIM>. Order is irrelevant — dim_id is the key.
Each element MUST include "dim_id" matching exactly one <DIM id="..."> above.
Do not invent dim_ids. Do not omit any dim_id.

Output valid JSON only. No prose before or after.

Each element format:
{{
  "dim_id": "<id matching a <DIM id='...'>>",
  "evidence_found": true or false,
  "confidence": "high" | "medium" | "low",
  "hedge": false,
  "citations": [
    {{"quote": "<short quote or section reference>", "location": "<file:line or section>", "source_class": "code|test|config|readme|doc|other"}}
  ],
  "evidence_summary": "<1-2 sentence summary>"
}}
"""


def collect_evidence(
    rubric: dict[str, Any],
    target_content: str,
    target_path: str,
    backend: str | None = None,
    batch: bool = False,
    target_window_bytes: int = DEFAULT_TARGET_WINDOW_BYTES,
) -> list[dict[str, Any]]:
    """Collect evidence for each rubric dimension. Returns list of evidence dicts.

    If batch=True, attempt one LLM call for all dimensions; fall back to per-dim
    on parse failure or oversize prompt. Result order matches rubric dim order
    via dim_id-keyed reassembly regardless of mode. ``target_window_bytes`` is
    the single Stage-2 visibility limit in both modes.
    """
    dims = rubric.get("dimensions", [])

    if batch and len(dims) > 1:
        try:
            return _collect_batched(
                dims,
                target_content,
                target_path,
                backend,
                target_window_bytes,
            )
        except (BatchParseError, BatchTooLarge) as e:
            print(f"[hermes-rubric] batched evidence failed ({e.__class__.__name__}); "
                  f"falling back to per-dim", file=sys.stderr)

    evidence_list = []
    for dim in dims:
        ev = _collect_one(
            dim,
            target_content,
            target_path,
            backend,
            target_window_bytes,
        )
        evidence_list.append(ev)
    return evidence_list


def _utf8_prefix(text: str, window_bytes: int) -> tuple[str, bool]:
    """Return the largest UTF-8-safe prefix within ``window_bytes``."""
    encoded = text.encode("utf-8")
    if len(encoded) <= window_bytes:
        return text, False
    return encoded[:window_bytes].decode("utf-8", errors="ignore"), True


def _target_excerpt(target_content: str, target_window_bytes: int) -> str:
    """Apply the configured Stage-2 byte window and disclose any invisible tail."""
    if (
        isinstance(target_window_bytes, bool)
        or not isinstance(target_window_bytes, int)
        or target_window_bytes < 1
    ):
        raise ValueError("target_window_bytes must be a positive integer")
    excerpt, truncated = _utf8_prefix(target_content, target_window_bytes)
    if truncated:
        excerpt += (
            f"\n[... truncated at configured target window "
            f"{target_window_bytes} bytes of {len(target_content.encode('utf-8'))} total ...]"
        )
    return excerpt


def _collect_batched(
    dims: list[dict[str, Any]],
    target_content: str,
    target_path: str,
    backend: str | None,
    target_window_bytes: int,
) -> list[dict[str, Any]]:
    excerpt = _target_excerpt(target_content, target_window_bytes)

    dim_blocks = "\n".join(
        f'<DIM id="{d["id"]}">\n'
        f'NAME: {d["name"]}\n'
        f'DESCRIPTION: {d["description"]}\n'
        f'EVIDENCE INSTRUCTIONS: {d["evidence_instructions"]}\n'
        f'</DIM>'
        for d in dims
    )

    prompt = _BATCHED_EVIDENCE_PROMPT_TEMPLATE.format(
        target_content=excerpt,
        dim_blocks=dim_blocks,
    )
    if len(prompt) > _BATCH_PROMPT_CEILING_CHARS:
        raise BatchTooLarge(
            f"batched evidence prompt {len(prompt)} chars exceeds ceiling {_BATCH_PROMPT_CEILING_CHARS}"
        )

    raw = backends.call(prompt, backend=backend)
    expected_ids = {d["id"] for d in dims}
    parsed = _extract_json_array(raw, expected_ids)
    by_id = {item["dim_id"]: item for item in parsed if isinstance(item, dict) and "dim_id" in item}

    evidence_list = []
    for dim in dims:
        ev = by_id.get(dim["id"])
        if ev is None:
            ev = {
                "dim_id": dim["id"],
                "evidence_found": False,
                "confidence": "low",
                "hedge": True,
                "citations": [],
                "evidence_summary": f"Evidence missing from batched response for {dim['id']}.",
            }
        ev = _normalize_evidence(ev, dim)
        evidence_list.append(ev)
    return evidence_list


def _normalize_evidence(ev: dict[str, Any], dim: dict[str, Any]) -> dict[str, Any]:
    """Apply hedge rule, source-class safety net, and dim_name pinning to one evidence dict."""
    if ev.get("confidence") == "low":
        ev["hedge"] = True

    citations = ev.get("citations") or []
    for c in citations:
        if isinstance(c, dict):
            suggested = c.get("source_class")
            fallback = classify_source(c.get("location", ""))
            if fallback != "other":
                c["source_class"] = fallback
            elif suggested in SOURCE_CLASSES:
                c["source_class"] = suggested
            else:
                c["source_class"] = "other"
    ev["citations"] = citations
    ev["source_class_mix"] = _source_class_mix(citations)
    ev["dim_name"] = dim["name"]
    return ev


def _extract_json_array(text: str, expected_dim_ids: set[str]) -> list[dict[str, Any]]:
    """Parse a JSON array response. Validates that returned dim_ids overlap expected set.

    Missing dim_ids are tolerated (caller routes to fallback). Extra dim_ids are dropped.
    Raises BatchParseError if the response is not a JSON array or contains zero
    matching dim_ids.
    """
    text = text.strip()
    arr = None
    try:
        arr = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                arr = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    if not isinstance(arr, list):
        raise BatchParseError(f"batched response is not a JSON array: {text[:200]}")

    matched = [
        item for item in arr
        if isinstance(item, dict) and item.get("dim_id") in expected_dim_ids
    ]
    if not matched:
        raise BatchParseError(
            f"batched response contains zero matching dim_ids (expected {sorted(expected_dim_ids)})"
        )
    return matched


def _collect_one(
    dim: dict[str, Any],
    target_content: str,
    target_path: str,
    backend: str | None,
    target_window_bytes: int,
) -> dict[str, Any]:
    excerpt = _target_excerpt(target_content, target_window_bytes)

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
        ev = {
            "dim_id": dim["id"],
            "evidence_found": False,
            "confidence": "low",
            "hedge": True,
            "citations": [],
            "evidence_summary": f"Evidence collection failed (JSON parse error). Raw: {raw[:200]}",
        }
    return _normalize_evidence(ev, dim)


def _source_class_mix(citations: list[dict[str, Any]]) -> dict[str, int]:
    mix = {k: 0 for k in SOURCE_CLASSES}
    for c in citations:
        sc = c.get("source_class", "other") if isinstance(c, dict) else "other"
        if sc in mix:
            mix[sc] += 1
    return mix


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


def _warn_truncation(path: str, actual_bytes: int, window_bytes: int) -> None:
    """Emit a stderr warning when a target file is silently truncated."""
    import sys
    lost = actual_bytes - window_bytes
    sys.stderr.write(
        f"[hermes-rubric] WARNING: target file exceeds --target-window-bytes "
        f"({actual_bytes} > {window_bytes}); last {lost} bytes will not be visible to the "
        f"rubric. Consider a tighter gate-card style artifact "
        f"(see hermes-handbook/rubric-passthrough-pattern.md). [{path}]\n"
    )


def read_target(target_path: str, window_bytes: int = DEFAULT_TARGET_WINDOW_BYTES) -> tuple[str, str]:
    """Read target file(s). Returns (content, resolved_path).

    Files larger than ``window_bytes`` are silently visible-only up to that
    cap; a stderr warning is emitted so the caller knows evidence beyond the
    window is invisible to the rubric.
    """
    p = Path(target_path).expanduser()

    if p.is_file():
        # Single-file mode: surface full content to the caller, but warn if
        # the file is larger than the configured window. Downstream stages
        # are responsible for honoring the window when they construct prompts.
        text = p.read_text(errors="replace")
        if len(text.encode("utf-8")) > window_bytes:
            _warn_truncation(str(p), len(text.encode("utf-8")), window_bytes)
        return text, str(p)

    if p.is_dir():
        # Concatenate all text files in the directory (up to 50 files,
        # window_bytes UTF-8 bytes each).
        parts = []
        count = 0
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix in (".md", ".py", ".txt", ".json", ".yaml", ".toml", ".rst"):
                try:
                    raw = f.read_text(errors="replace")
                    raw_bytes = len(raw.encode("utf-8"))
                    if raw_bytes > window_bytes:
                        _warn_truncation(str(f), raw_bytes, window_bytes)
                    text, _ = _utf8_prefix(raw, window_bytes)
                    parts.append(f"=== {f.relative_to(p)} ===\n{text}")
                    count += 1
                    if count >= 50:
                        parts.append("[... more files truncated ...]")
                        break
                except OSError:
                    continue
        return "\n\n".join(parts), str(p)

    raise FileNotFoundError(f"Target not found: {target_path}")


def read_context(context_path: str, window_bytes: int = DEFAULT_TARGET_WINDOW_BYTES) -> str:
    """Read context file(s) for rubric synthesis."""
    import glob as glob_mod

    p = Path(context_path).expanduser()
    if p.is_file():
        raw = p.read_text(errors="replace")
        raw_bytes = len(raw.encode("utf-8"))
        if raw_bytes > window_bytes:
            _warn_truncation(str(p), raw_bytes, window_bytes)
        return _utf8_prefix(raw, window_bytes)[0]

    # Try glob
    matches = sorted(glob_mod.glob(str(p)))
    if matches:
        parts = []
        # Per-file budget when concatenating multiple matches: half the window,
        # preserving the historical 8000 -> 4000 ratio.
        per_file = max(1, window_bytes // 2)
        for m in matches[:5]:
            try:
                raw = Path(m).read_text(errors="replace")
                raw_bytes = len(raw.encode("utf-8"))
                if raw_bytes > per_file:
                    _warn_truncation(str(m), raw_bytes, per_file)
                parts.append(_utf8_prefix(raw, per_file)[0])
            except OSError:
                continue
        return "\n\n---\n\n".join(parts)

    return f"[context path not found: {context_path}]"
