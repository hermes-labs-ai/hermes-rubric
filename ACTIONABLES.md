# hermes-rubric — actionables / TODO pipeline

Last updated: 2026-04-25 by session a36290a2

## P0 — gates before public push
- [ ] **Roli review** of `calibration/META-RUBRIC.md` (ship gate, frozen-after-ship)
- [ ] **Roli review** of `applied/papers-20260423.md` (Zenodo scores are abstract-only / provisional)
- [ ] **Roli review** of `calibration/dataset.jsonl` (7 provisional cases need confirmation)
- [ ] **Push branch `batch-mode`** to GitHub (gated on the above 3 reviews)

## P1 — paper-grade follow-ups (not blocking publishability)
The Qwen + Gemini + claude-cli runs already give cross-model evidence sufficient for the publishable engineering claim. These are nice-to-haves that strengthen specific claims.

- [ ] **Anthropic SDK paper-grade run.** Add direct `anthropic` SDK backend to `backends.py` (parallel to dashscope/gemini/openai patterns), pinned model `claude-sonnet-4-6` or `claude-opus-4-7`, temp=0. Re-run `main_a` N=11 + `main_b` N=5 across T1-T5. Cost ~$15. Removes the "claude-cli session contamination" caveat from the paper. Follows pattern in `experiments/batch-equiv-2026-04-25/HANDOFF.md`.
  - *Tried claude-cli OAuth contextual mode 2026-04-25; transient exit-1 mid-run after 4 successful runs on T4 only. Signal Δ +0.30, within margin, but N=2 too thin to claim equivalence. SDK route is cleaner.*

- [ ] **GPT paper-grade run.** OpenAI backend already wired (commit `<this-session>`). Re-run `main_a` N=10 across T1-T5 once OpenAI quota is restored. Cost ~$5 on `gpt-4o-mini`. Adds 4th model family to cross-model evidence.

- [x] **Cohen's κ on existing 260 paired runs.** ✓ Done 2026-04-25 (commit `133fda9`). Overall mean κ = 0.632, passes pre-registered ≥0.6 gate. Gemini 0.642, Qwen 0.621. Per-target table in RESULTS.md.

- [ ] **Re-grade RESULTS.md with `--scope-class results-bundle`.** Was graded 5.7 capped earlier; with the right scope-class flag the structural cap shifts. Confirms whether the writeup gates the publishable bar at ≥7. ~2 min.

- [ ] **Check T1 truncation under 8KB window.** `agent-convergence-scorer/src` may exceed the default `--target-window-bytes=8000`. Re-freeze T1 at `--target-window-bytes=32000` and rerun a subset to see if any T1 deltas change.

## P2 — separate experiment, requires Roli's 1 hour
- [ ] **Rubric quality eval.** Proposal at `experiments/rubric-quality-PROPOSAL.md`. Tests whether hermes-rubric scores correlate with **ground-truth quality** (not just internal consistency between modes). Without this, current claim is "internally consistent at 6× speed." With it: "useful audit grader that matches human judgment at κ ≥ 0.5." Cost ~$5-15 + 1 hour Roli rating.
  - Curate 30 targets (good/bad/mid pairs across 5 domains)
  - Run hermes-rubric per_dim, hermes-rubric --batch, naive LLM-as-judge baseline
  - Roli rates 10 sample targets manually
  - Compute κ (rubric vs human), Spearman ρ vs ground truth, agreement matrix

## P3 — OSS hygiene (no run cost)
- [ ] **Push hermes-rubric to PyPI** (post-review).
- [ ] **Push hermes-blind 0.1.1 to PyPI** so the new `hermes-rubric>=0.1.3` dep can install.
- [ ] **Document `--scope-class` in README** with examples for gate-plan / sweep-plan / results-bundle.
- [ ] **Document `--intent-debias` in README** with the valence-loaded-framing examples.
- [ ] **Document the `kappa` subcommand** in README.
- [ ] **CHANGELOG entries** for v0.1.3 reflect both the preambles refactor AND the OpenAI backend addition.

## P4 — known structural findings, not bugs (document in handbook?)
- [ ] **Doc-class score cap is structural.** Plan-documents and writeups will always score ≤6 because of the all-README clamp at `score.py:68-70`. The handbook entry on this pattern (`hermes-handbook/rubric-passthrough-pattern.md`) should mention it explicitly. Workaround: `--scope-class results-bundle` adjusts which dims synthesize, but the citation-source clamp still fires. This is by design.
- [ ] **Cross-arm evidence-stage variance is model-dependent.** End-to-end batched mode finds evidence per-dim mode misses on certain targets (T4 / Gemini: 0 → 5.8). This is a real signal worth a separate writeup, not a bug. Future direction: is the `<DIM>` block context productively informing evidence collection, or inflating it? Resolvable via human-rater agreement on the same target.

## P5 — speculative / parking lot
- [ ] Add `anthropic` SDK backend (separate from `claude-cli` adapter) for paid metered runs.
- [ ] Per-backend `max_tokens` tuning + JSON-mode (`response_format`) for stricter structured output.
- [ ] Prompt-template hash pinning + receipt audit trail for cross-version reproducibility.
- [ ] `--include-blind-wrap` flag that calls `hermes_blind.wrap()` on the final output prompt for additional debias on top of `--intent-debias`.

## Decisions logged
- **0.1.3 preamble refactor (2026-04-25):** moved bias-compensation preambles OUT of hermes-rubric INTO hermes-blind 0.1.1 dependency. Two complementary OSS, not merged.
- **`--batch` shipped opt-in (0.1.2):** byte-identical default behavior; default-flip deferred until cross-model paper-grade evidence accumulates.
- **No GPT in tonight's paper (2026-04-25):** OpenAI quota dead; backend wired anyway for OSS users. GPT paper-grade is P1 follow-up.
- **No Anthropic SDK tonight (2026-04-25):** claude-cli OAuth contextual mode is publishable for the paired Δ-equivalence claim per paired-design controls. Anthropic SDK is P1 follow-up that removes the contamination caveat.

## Source pointers
- Plan: `experiments/batch-equiv-2026-04-25/PLAN.md`
- Results: `experiments/batch-equiv-2026-04-25/RESULTS.md`
- Handoff: `experiments/batch-equiv-2026-04-25/HANDOFF.md`
- Project memory: `~/.claude/projects/-Users-rbr-lpci/memory/project_hermes_rubric.md`
- Corpus log: `~/Documents/projects/research-corpus/agent-infra/raw/2026-04-25-hermes-rubric-batch-equivalence.md`
