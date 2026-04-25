# Experiment Plan v2: Batched-vs-per-dim equivalence in hermes-rubric 0.1.2

## Question
Does `--batch` mode produce score outputs statistically equivalent to per-dim mode on real LLM backends, across realistic targets including failure-mode triggers?

## Equivalence margin justification
The pre-registered margin is **±1.0 score-points** for the mixed-effects coefficient on `mode`. Justification:
- The rubric's clamp granularity is 1 point (`score.py:99` clamps to integer; `score.py:111` enforces `int(...)`). A delta below 1.0 is below the score's measurement resolution.
- Inter-rater agreement on 0-10 rubric scales in published LLM-eval work routinely shows σ ≈ 0.7-1.0 within a single rater across reps (this is the noise floor of LLM scoring, not a property of batching). Effects below this can't be reliably distinguished from rater noise.
- Acceptance margin (1.0) = noise floor; rejection margin (2.0, the CI-exclusion threshold) = double the noise floor, the smallest delta that could plausibly affect a downstream user decision.

## Hypothesis (pre-registered)
H0: For the score-stage primary endpoint, the mixed-effects coefficient on `mode` has 95% CI within ±1.0 score-points, AND hedge-flag agreement κ ≥ 0.6, AND batched fallback rate < 10%.
H1: At least one of these fails.

## Design

### Phase 0: Pilot (cost-bounded variance estimation)
Run sub-exp A (score-only) on T1 alone, N=3 per mode = 6 calls per dim × 8 dims = 48 calls.
**Outputs of pilot:**
- σ̂_within_mode (variance of repeated scoring of identical evidence in the same mode)
- σ̂_between_mode_at_n=3 (preliminary signal)
- Per-call latency and (if observable) token cost

**Pilot decision rule:** if σ̂_within_mode > 1.5, the score-stage is too noisy to detect a 1.0-point effect at any feasible N. Abort or widen the equivalence margin and re-pre-register before main experiment.

### Phase 1: Power-justified main experiment

After pilot returns σ̂_within_mode, compute required N via:
```
N_per_mode = 2 * (z_{1-α/2} + z_{1-β})² * σ̂² / Δ²
```
with α=0.05, β=0.20 (80% power), Δ=1.0. For σ̂=0.7: N≈4 per cell. For σ̂=1.0: N≈8.
The main experiment uses `N = max(5, computed_N)`.

### Sub-experiment A: Score-stage isolation
- Per target: synthesize rubric ONCE → freeze. Collect evidence ONCE per-dim → freeze.
- Score N reps × 2 modes against frozen evidence.
- 5 targets × 2 modes × N reps × 1 batched call (or 8 per-dim calls) → call budget computed post-pilot.

### Sub-experiment B: End-to-end
- Same frozen rubric. Run full pipeline (evidence + score) at N_B = max(3, ceil(N/2)) per mode.
- Captures combined evidence + score variance.

### Targets (5)
| ID | Description | Clamp triggered |
|---|---|---|
| T1 | high-evidence Python repo (`agent-convergence-scorer/`) | none (baseline) |
| T2 | thin-evidence product blurb (~200 words) | hedge clamp [3,7] |
| T3 | all-README repo (no `src/`) | self-marketing cap 6 |
| T4 | research-corpus markdown report (formal claims, citations) | none expected |
| T5 | adversarial empty target (10-line file) | no-evidence cap 3 |

### Statistics
**Primary model (score-stage, sub-exp A):**
```python
mixedlm("score ~ mode", data, groups="target", re_formula="~1", vc_formula={"dim": "0 + C(dim_id)"})
```
Dims are **nested in target** (not crossed), since `synthesize` produces target-local dim_ids. The variance components form is the standard `statsmodels` pattern for nested factors.

**Endpoint:** 95% CI on the `mode[T.batched]` coefficient, in score-point units.

**Secondary endpoints:**
- Hedge-flag agreement: Cohen's κ on (per-dim, per-rep) hedge_applied flags, paired by (target, dim, rep_index).
- Clamp activation contingency: 3×2 χ² (clamp_type × mode) on counts across all (target, dim, rep) cells. Bonferroni correction across 3 clamps.
- Aggregate-score paired delta: bootstrap 95% CI per target, then meta-analytic combination.

**Stratified analyses (pre-registered):**
- Score deltas split by `evidence_found ∈ {true, false}`.
- Score deltas split by majority `source_class ∈ {code, readme/doc, other}`.
These check whether equivalence holds within each clamp regime.

### Confound controls
- **Model + version pinned per receipt.** Extend receipt to record `claude_cli_mode()` AND a `model_id` field captured from `/login` or response metadata. Reject runs that span a model-version change (re-run that target's batch).
- **Temperature pinned for ollama.** Set `temperature=0` and `seed=42` in ollama backend calls during the experiment.
- **claude-cli temperature unpinned (production conditions)** — this is intentional; the experiment measures real production variance, not idealized variance.
- **Prompt version pinned.** Hash `_BATCHED_EVIDENCE_PROMPT_TEMPLATE`, `_BATCHED_SCORE_PROMPT_TEMPLATE`, `_EVIDENCE_PROMPT_TEMPLATE`, `_SCORE_PROMPT_TEMPLATE` (sha256 of each). Record hashes in a manifest. Reject runs after any template edit.

### Determinism validation
Ollama `temperature=0, seed=42` validation: same 5 targets, sub-exp A only, N=3. Confirms code path is deterministic when LLM is — any non-zero variance under these conditions is a code bug, not LLM noise.

## Cost / budget

### Pre-pilot estimate
- Pilot: 48 calls, ~17s/call ≈ 14 min.
- Main exp (assuming σ̂≈0.7, N=5):
  - Sub-A: 5 targets × 2 modes × 5 reps × (1 batched call OR 8 per-dim calls) = 5×(5×1 + 5×8) = 225 calls
  - Sub-B: 5 targets × 2 modes × 3 reps × (2 batched calls OR 16 per-dim calls) = 5×(3×2 + 3×16) = 270 calls
  - Synthesize + freeze evidence (one-time): 5 × (1 + 8) = 45 calls
  - Total ≈ 540 calls.
- Validation (ollama): 5 × 2 × 3 × ~5 = 150 calls (free, local).

### Wall-clock
~540 × 17s ≈ 153 min ≈ 2.5 hours sequential on claude-cli. Acceptable.

### Mid-run cost cap
The runner emits a per-call latency line; aggregator script tails it and SIGTERMs the runner if cumulative wall-time exceeds 4 hours OR if any single call exceeds 60s twice consecutively (signal of backend trouble).

### Dollar cost (claude-cli)
claude-cli on a session OAuth token uses session quota, not metered API. Per cogito QA budget tracking (memory: $10 used of $50 monthly), 540 calls is well within the remaining envelope. No new dollar cost expected. If session quota is exceeded mid-run, fall through to ollama-local for the remainder; document which calls used which backend in the manifest.

## Failure-mode handling

### LLM JSON parse failure
- Per-dim mode: existing fallback at `score.py:174-181` returns `score=3, hedge_applied=true, score_rationale=<error>`. Fallback runs are **excluded** from the score-stage statistical analysis (treated as missing) but **included** in a separate "parse-failure rate per mode" metric.
- Batched mode: existing auto-fallback to per-dim at `evidence.py:_collect_batched` and `score.py:_score_batched`. Receipt records `batched_fallback_used: true`. Fallback events are **counted as a primary metric**, not excluded.
- Acceptance: parse-failure rate < 5% in either mode; fallback rate < 10% in batched mode. If exceeded, plan upgrades to add JSON-mode prompts (out-of-scope feature work) before continuing.

### Mid-run model drift
If `claude_cli_mode()` differs between any two consecutive calls within a target's run, abort that target's run, archive incomplete receipts, and re-run the entire target from scratch.

### Stratification rules
- All deltas reported overall AND stratified by:
  - `evidence_found` (boolean) — separates "no-evidence cap fired" cases.
  - `dominant_source_class` (most-frequent class across citations) — separates self-marketing cap cases.
  - Clamp triggered (hedge / no-evidence / self-marketing / none) — primary clinical strata.

## Implementation

### Bypass CLI; use Python API
The runner is `experiments/batch-equiv-2026-04-25/runner.py`, importing:
```python
from hermes_rubric.synthesize import synthesize
from hermes_rubric.evidence import collect_evidence, read_target, read_context
from hermes_rubric.score import score_dimensions, compute_aggregate
from hermes_rubric import __version__
```
This bypasses CLI synthesis-on-every-call, supporting frozen rubrics + frozen evidence.

### Output schema
```json
{
  "target_id": "T1",
  "mode": "batched"|"per_dim",
  "sub_exp": "A"|"B"|"pilot"|"validation_ollama",
  "rep": 0,
  "rubric_hash": "sha256:...",
  "evidence_hash": "sha256:..." | null,
  "prompt_template_hashes": {"evidence": "...", "score": "...", "evidence_batched": "...", "score_batched": "..."},
  "tool_version": "0.1.2",
  "backend": "claude-cli",
  "claude_cli_mode": "bare"|"contextual",
  "model_id": "<captured if available, else null>",
  "started_at": "<ISO>",
  "ended_at": "<ISO>",
  "latency_seconds": <float>,
  "scores": [...],
  "aggregate": <float>,
  "fallback_used": <bool>,
  "parse_failures": <int>
}
```

### Runner pseudocode (cited against shipped code)
```python
# Phase 0: pilot
rubric = synthesize(intent, context, target_type)              # synthesize.py:25-?
write(f"frozen/{tid}/rubric.json", rubric)
evidence = collect_evidence(rubric, target_content, target_path, backend, batch=False)
                                                                # evidence.py:100-114, default batch=False
write(f"frozen/{tid}/evidence.json", evidence)
for rep in range(N_pilot):
    for mode in ("per_dim", "batched"):
        scores = score_dimensions(rubric, evidence, backend, batch=(mode=="batched"))
                                                                # score.py:114-145
        write_run(...)
# Phase 1: main, sized after pilot
```

### Reproducibility artifacts
- `experiments/batch-equiv-2026-04-25/PLAN.md` (this file, committed).
- `frozen/{T1..T5}/rubric.json` — committed (small).
- `frozen/{T1..T5}/evidence.json` — committed (small, per-dim only).
- `runs/` — gitignored (large), but `RUNS-MANIFEST.csv` committed indexing every run file.
- `analyze.py` (script, not notebook — for unambiguous re-execution) — committed.
- `RESULTS.md` — committed after analysis.
- All numpy/random seeds set; ollama runs use seed=42.

## Decision tree (pre-registered)
```
                     Pilot σ̂ ≤ 1.5?
                    /              \
                  Yes               No → ABORT, re-pre-register margin
                   |
              Compute N via power formula
                   |
            Run main experiment
                   |
        ┌──────────┴───────────┐
   Sub-A passes?           Sub-A fails?
        |                       |
   Sub-B passes?         → bias is in score stage
   /         \           → ship `--batch-score-only` if sub-B-evidence isolation passes
 Yes          No
  |            |
Flip default  → bias is in evidence stage
to --batch     → keep opt-in, document
in 0.2.0       in CHANGELOG
(real minor    (which dim type biased)
bump)
```

## Cross-arm interference and cache effects
claude-cli routes through a session that may cache responses or accumulate context across calls. Mitigations:
- All runs **alternate modes per rep** (`per_dim`, `batched`, `per_dim`, `batched`, …) rather than running all per_dim then all batched. Monotonic session drift balances across arms.
- Per-target run order is randomized via `random.Random(42).shuffle(target_ids)` once per session.
- Frozen evidence ensures the same input bytes go to both modes — any cache hit benefits both arms.

## H0 decomposition
v1's compound H0 is split into:
- **Primary endpoint:** mixed-effects coefficient on `mode` has 95% CI within ±1.0.
- **Gating criteria (must also hold):** hedge-flag κ ≥ 0.6; batched fallback rate < 10%.
The primary is the directional/equivalence question; the gates prevent shipping a mode that's nominally equivalent on means but degenerate on hedge logic or fallback frequency.

## External validity (limitations)
- **Generalization beyond 5 targets:** targets span the four post-hoc clamps + one baseline. They don't span all possible target shapes (very long, multilingual, code-only). Results apply to "rubric-typical" targets; broader claims need more.
- **Single LLM family:** claude-cli + ollama validation. No GPT/Gemini/Mistral coverage.
- **Solo-rater:** one model is both rater and the thing being mode-compared. No human ground truth.
- **Novelty effect:** the `<DIM>` block prompt is new; transient adaptation behavior in older models is not tested at scale (>50 calls/session).
- **Attrition bias:** runs that fall back from batched to per-dim count in `fallback_used` but are **excluded** from primary score-stage analysis. This biases the primary toward "successfully batched" scenarios; the fallback rate gate guards against this becoming load-bearing.

## Out of scope (explicit)
- Per-backend tuning (max_tokens, JSON mode response_format).
- Alternative isolation prompts.
- Cost / latency optimization beyond 2N+1 → 3.
- Cross-LLM comparison (only claude-cli + ollama validation).
- Pinning claude-cli temperature (would require backend changes; production-conditions choice is intentional).

## Threats to validity (pre-declared)
- LLM drift mid-run → mid-run model-version detector (above).
- Target-leakage in claude-cli (session context bleed) → affects both modes equally; paired comparison cancels it. Unpaired absolute scores are NOT primary endpoints for this reason.
- Frozen-evidence ≠ realistic → sub-exp A is diagnostic; sub-exp B is the user-facing answer.
- N is small → pilot + power calc → either N is sufficient or the experiment doesn't run.
- Single LLM family → ollama validation establishes determinism floor; cross-LLM is future work, not claimed.

## Deliverables
`experiments/batch-equiv-2026-04-25/`:
- `PLAN.md` (this) — committed.
- `runner.py` — committed.
- `analyze.py` — committed.
- `frozen/{T1..T5}/{rubric,evidence}.json` — committed.
- `RUNS-MANIFEST.csv` — committed.
- `RESULTS.md` — committed post-analysis.
- `runs/*.json` — gitignored (size).
