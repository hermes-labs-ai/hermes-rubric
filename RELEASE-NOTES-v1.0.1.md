# hermes-rubric 1.0.1 release candidate

Status: unreleased. This file does not authorize a tag, push, GitHub release,
or package upload.

## Correctness fixes

- Stage 2 now uses the configured target window in both batched and
  per-dimension evidence collection. If content remains outside that window,
  the prompt identifies the truncation explicitly.
- Rubric synthesis now preserves the caller-bound `target_type`; backend output
  cannot silently replace transport metadata used by downstream receipts.
- `hermes-rubric --version`, installed package metadata, and receipt
  `tool_version` now report one matching version.

## Interpretation boundary

Hermes Rubric aggregates remain advisory signals with evidence receipts. They
are not binary pass/fail gates and do not authorize merges, releases, or
publication.
