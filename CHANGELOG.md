# Changelog

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
