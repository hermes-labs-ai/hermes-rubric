# Changelog

## [1.1.0] — 2026-08-14 — portable assessment core

- Add one-call in-memory and path APIs: `assess`, `assess_path`, and async wrappers.
- Add typed top-level results with stable serialization and result schema `1.0`.
- Support caller-provided frozen rubrics alongside synthesis and artifact classes.
- Report complete/partial evidence coverage, byte/source facts, and limitations.
- Normalize public errors by pipeline stage while preserving exception causes.
- Add caller-policy feedback with quality, evidence, and coverage gap kinds.
- Delegate the CLI to the shared public orchestrator while preserving existing flags,
  exit behavior, and output keys.
- Lead documentation with the agent/application integration path and state the
  current prefix-window limitation explicitly.
- Add release notes, an adapter contract, and a portable agent-output example.

## [1.0.2] — 2026-08-04 — scoring identity and integration clarity

- Pin Stage-3 dimension IDs and names to the synthesized rubric across
  per-dimension, batched, missing-result, and parse-fallback paths.
- Publish dedicated Documentation and Changelog links in package metadata.
- State the backend requirement before the first README command.
- Align quickstart commands and Python imports with the current CLI and API.
- Clarify which paths are local, which cloud backends are optional, and which
  stages remain non-deterministic.
- Remove unsupported recomputation and retired research claims from current
  public documentation.
- Add an OIDC Trusted Publishing workflow for PyPI releases.

## 1.0.1 — 2026-07-26 — correctness patch

- Honor the configured target window throughout both Stage-2 evidence paths
  instead of silently applying a second 6,000-character cap.
- Preserve the caller-bound rubric `target_type` rather than allowing backend
  output to reclassify it.
- Implement `hermes-rubric --version` and derive receipt `tool_version` from
  the same runtime version surface.

## 1.0.0 — 2026-04-28 — first official release

The repo has been public since 2026-04-24 as a 0.9-era preview. v1.0.0 is the first tagged release on PyPI + GitHub Releases, headlined by class-aware rubric templates.

The 0.1.x and 0.2.0 entries below were internal-only iterations toward v1.0.

### What v1.0 includes (vs the 0.9-era preview)

Added `--artifact-class <name>` flag. When set, Stage-1 LLM rubric synthesis is bypassed and a deterministic dim set is loaded from a YAML template. The same input + same class produces the same dim set across runs — addressing the non-determinism observed in v0.1.x where Stage-1 synthesized different dims on every run.

### New classes (4)

- `social-post` — X / Twitter / Bluesky. Voice + platform-fit dominate.
- `show-hn-post` — Hacker News launch posts. Substance + fab-block dominate.
- `linkedin-post` — LinkedIn announcements. Procurement-voice + defensibility dominate.
- `outreach-email` — Cold sales emails. Quote-first opener + voice-match dominate.

Each class template includes 7-9 fixed dimensions with weights and evidence instructions, a class-specific slop-signature list (injected into `llm_fool` dim), and voice priors (injected into `voice_match` dim). `outreach-email` adds `banned_subject_patterns` for the `subject_neutrality` dim.

### CLI

- `--artifact-class` flag added; back-compat preserved (omitted = v0.1 behavior)
- `--intent` and `--context` optional when `--artifact-class` is set

### Internal

- New `hermes_rubric.classes` module
- 9 new tests in `tests/test_classes.py`; full suite 109 passed, 2 skipped
- pyyaml added as runtime dependency

### Why

Observed in v0.1.x: scoring the same artifact 3 times produced 3 different rubric hashes because the LLM invented dims fresh each run. Aggregate scores varied 5.4–6.2 across runs, with no way to compare them dim-by-dim. Class-aware preloading determinizes Stage-1: the dim set comes from YAML, not from the LLM.

### Back-compat

All existing CLI calls work unchanged. Receipts include a new `rubric.rubric_source` field (`"class-template"` when applicable; absent otherwise).

## 0.1.3 — 2026-04-25

- **Refactor:** Bias-compensation preambles (intent-debias, scope-class)
  moved out of `hermes_rubric.preambles` and into the upstream
  `hermes-blind` package (which is the bias-compensation domain).
- New runtime dependency: `hermes-blind>=0.1.1`.
- `hermes_rubric.preambles` is now a thin re-export shim for the
  `hermes_blind.preambles` module. External callers importing from the
  old path keep working for one migration cycle. Will be removed in
  v0.2.0.
- CLI surface is unchanged: `hermes-rubric --scope-class
  {gate-plan,sweep-plan,results-bundle} --intent-debias` parses and
  behaves identically to v0.1.2.
- Behavior byte-identical to v0.1.2 — verified by 6-combo
  frozen-prompt regression test in `tests/test_preambles_shim.py`.
- 73 tests green (was 62 + 11 new shim/byte-identity tests).

## 0.1.2 — 2026-04-25

- `--batch` flag: one LLM call per stage (evidence + score), reducing 2N+1 calls per run to 3
- Prompt-layer isolation via per-`<DIM>` blocks with explicit "score only within your block" invariant
- dim_id-keyed reassembly; rubric dim order re-imposed in `compute_aggregate` regardless of LLM return order
- Auto-fallback to per-dim mode on JSON parse failure or oversize prompt; mode logged in receipt
- All clamps preserved byte-for-byte (hedge [3,7], no-evidence cap 3, self-marketing cap 6); consolidated in `_apply_clamps`
- 8 new tests in `tests/test_batch.py` covering reassembly, missing-dim fallback, parse-failure fallback, clamp suffix preservation, and per-dim-vs-batched golden equivalence on a frozen rubric fixture
- Default behavior byte-identical to 0.1.x; `--batch` is opt-in

## 0.1.0 — 2026-04-23

Initial release.

- Three-stage pipeline: rubric synthesis, evidence collection, scoring
- Auto-backend detection: claude-cli (preferred), ollama-local (fallback)
- Hedge enforcement: low-confidence dimensions clamped to [3,7]; no-evidence dimensions capped at ≤3
- Reproducibility receipt in every output
- 14 tests (5 backends, 3 synthesize, 4 score, 2 adversarial)
- Adversarial tests confirm fluency-vs-substance resistance and no-evidence cap
- Calibration dataset: 15 cases, 5 domains
- META-RUBRIC: 7 dimensions from 24 corpus-derived failure modes
- Applied: 4-paper scoring (langquant, cogito-ergo, 2 Zenodo papers)
- Handbook entry: `evidence-first-rubric-synthesis.md`
