# Changelog

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
