# HANDOFF — paper-grade run (tomorrow)

## State at handoff (2026-04-25 evening)
- hermes-rubric 0.1.2 shipped on branch `batch-mode` with `--batch` flag.
- Experiment scaffolded at `experiments/batch-equiv-2026-04-25/`.
- T1 frozen (`frozen/T1/{rubric,evidence,target}.json|txt`).
- T2/T3/T5 fixtures created. T4 points at `applied/`.
- Pilot run on T1 only, N=3 sub-A. Results: `RESULTS-pilot.md`.

## Pilot signal (from real LLM, claude-cli contextual)
- Aggregate Δ = +0.20 (within ±1.0).
- 6/8 dims byte-equal. dim_2 swings ±2.0 (σ_Δ=1.16). dim_7 consistent +1.0.
- Power calc says **N=11 per cell** is needed to detect a 1.0-point per-dim Δ at 80% power given observed σ.

## What to run tomorrow with API key

### 1. Switch backend to direct API
Currently `backends.py` supports `claude-cli` and `ollama-local`. For paper-grade:
- Add a third backend option: direct Anthropic SDK with `claude-sonnet-4-6` (or `claude-opus-4-7` for the paper if budget allows).
- Captures `model` field per receipt (closes the "model_id pinning" gap that hermes-rubric flagged in the plan grading).
- Set `temperature=0` for determinism.
- Reference: feedback memory says default to Sonnet 4.6 unless explicitly Opus.

### 2. Freeze remaining targets
```bash
cd ~/Documents/projects/hermes-rubric
.venv/bin/python experiments/batch-equiv-2026-04-25/runner.py freeze --targets T2,T3,T4,T5 --backend <new-backend>
```

### 3. Main experiment
```bash
.venv/bin/python experiments/batch-equiv-2026-04-25/runner.py main_a --n 11 --backend <new-backend>
.venv/bin/python experiments/batch-equiv-2026-04-25/runner.py main_b --n 5 --backend <new-backend>
```
Expect ~880 LLM calls total (5 targets × 11 reps × 2 modes × ~8 calls per_dim avg, batched is 1).

### 4. Validation (free, local)
```bash
.venv/bin/python experiments/batch-equiv-2026-04-25/runner.py validate --backend ollama-local --n 3
```
With ollama temp=0 + seed=42, batched and per_dim should produce identical scores per dim. Any non-zero variance = code bug.

### 5. Analyze
```bash
.venv/bin/python experiments/batch-equiv-2026-04-25/analyze.py --phase main_a
.venv/bin/python experiments/batch-equiv-2026-04-25/analyze.py --phase main_b
```
For paper-grade stats (mixed-effects model), install statsmodels and add a `--mixed` flag to `analyze.py` (currently parked).

### 6. Decision
Per the pre-registered decision tree in `PLAN.md`:
- All gates pass → flip `--batch` to default in 0.2.0 (real minor bump).
- Sub-A passes, sub-B fails → ship `--batch-score-only` only.
- Anything else → keep opt-in, document bias direction.

## Open issues to address before paper

1. **claude-cli ran in contextual, not bare mode** during the pilot. Use `claude --bare` (or new SDK backend) for paper.
2. **Hermes-blind not applied per call.** The plan says paired comparison cancels session bias, but for a paper this should be tightened: wrap every call with `hermes_blind.wrap(prompt)`.
3. **statsmodels mixed-effects** not yet wired into `analyze.py`. Currently aggregates with stdev; paper needs the `score ~ mode + (1|target/dim_id)` fit with 95% CI on the mode coefficient.
4. **Hedge-flag κ and clamp χ²** computed in `analyze.py`: not yet implemented. Need scipy.stats.

## Cost estimate
- Sonnet 4.6 at ~$3/M input + $15/M output, average ~3K input + 200 output tokens per rubric call.
- Pilot 27 calls ≈ 27 × $0.012 ≈ $0.33.
- Main exp ~880 calls ≈ $11.
- Validation free (ollama).
- Total paper-grade run: **~$15–20** end-to-end.

## Files committed tonight
- `experiments/batch-equiv-2026-04-25/PLAN.md`
- `experiments/batch-equiv-2026-04-25/runner.py`
- `experiments/batch-equiv-2026-04-25/analyze.py`
- `experiments/batch-equiv-2026-04-25/HANDOFF.md` (this)
- `experiments/batch-equiv-2026-04-25/RESULTS-pilot.md`
- `experiments/batch-equiv-2026-04-25/fixtures/T2_blurb.md`, `T3_readme_only/README.md`, `T5_empty.md`
- `experiments/batch-equiv-2026-04-25/frozen/T1/{rubric,evidence,target}.json|txt`
- `experiments/batch-equiv-2026-04-25/.gitignore` (excludes `runs/`)

## Files NOT committed (gitignored)
- `runs/pilot/*.json` — 6 raw pilot run files
