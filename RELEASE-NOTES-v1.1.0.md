# Hermes Rubric v1.1.0 — Portable Assessment Core

Version 1.1 makes Hermes callable as one framework-neutral assessment transaction: pass an in-memory agent output or a filesystem target, then receive cited evidence, scores, coverage, feedback, and a receipt.

## What is new

- `assess()` and `assess_path()` public entry points for literal text and explicit path inputs.
- `assess_async()` and `assess_path_async()` wrappers that keep synchronous providers off an event loop.
- `AssessmentResult` with attribute access, stable `to_dict()` / `to_json()`, and result schema version `1.0`.
- Three rubric sources: synthesis, a deterministic artifact class, or a caller-provided frozen rubric.
- `CoverageReport` with complete/partial status, byte and source facts, and plain-language limitations.
- `AssessmentError.stage` for backend, input, rubric, evidence, score, and receipt failures.
- `FeedbackPolicy`, `Finding`, and `FeedbackPacket`, separating quality, evidence, and coverage gaps.
- CLI delegation to the same public transaction while preserving established flags and JSON keys.
- A framework-neutral adapter contract and agent-output example.

## Product boundary

Hermes measures and explains. The caller owns thresholds, retries, runtime mutation, fail-open/fail-closed behavior, and human review. Version 1.1 does not add an autonomous revision loop or a framework dependency.

## Coverage boundary

Evidence collection still uses a UTF-8-safe prefix window, 8,000 bytes by default. Version 1.1 reports that limit; it does not claim full-document retrieval. A partial coverage result means missing evidence may be uninspected and should not automatically trigger an artifact rewrite.

## Compatibility

Existing stage functions remain importable. CLI flags, stage exit codes, default JSON behavior, backend auto-detection priority, evidence acceptance, hedge enforcement, no-evidence caps, source-authority weighting, and legacy output keys remain in place. New JSON fields are additive.

## Upgrade

```bash
pip install --upgrade hermes-rubric
```

Start with the [README](README.md), [Python API](docs/API.md), or [adapter contract](docs/ADAPTERS.md).
