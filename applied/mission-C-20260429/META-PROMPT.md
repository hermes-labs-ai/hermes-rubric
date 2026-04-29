# Mission C — META-PROMPT for Opus subagent (Phase 1 only)

You are spawned as a HAL tentacle on a bounded pilot validation mission. Roli (Rolando Bosch, Hermes Labs / LPCI Innovations LLC) is watching the logs. You operate autonomously within Phase 1 scope. You do not commit on behalf of Mission B. You do not modify HAL coordinator state. Phase 2 is conditional on Phase 1 passing the floor.

---

## READ FIRST — verbatim, in order, no skipping

1. `~/Documents/projects/hermes-rubric/applied/METACOGNITIVE-FRAMEWORK-20260429.md` — your binding metacognitive constraints (Red-Team Scratchpad, Embedding & Math Justification, I/O Quarantine, Execution).
2. `~/Documents/projects/hermes-rubric/applied/PRE-REGISTRATION-20260429.md` — your hypothesis, Phase 1 rubric, halt triggers, banned actions.
3. `~/Documents/projects/hermes-rubric/meta_tool/hermes_meta_rubric.py` — the wrapper you'll modify in V1.
4. `~/Documents/projects/hermes-rubric/meta_tool/policy_schema.json` — the policy schema that V1's `--rubric-file` flag will reference.
5. `~/Documents/projects/hermes-rubric/src/hermes_rubric/synthesize.py` and `evidence.py` and `score.py` — the underlying pipeline you're working with.
6. `~/Documents/projects/hermes-rubric/tests/test_meta_tool.py` — existing 21 tests; V1 must not break any.
7. `~/Documents/projects/hermeneutic/` — the hermeneutic tool (Stage 1 regex layer) for V3.
8. `~/Documents/projects/hermes-seal/` — for V4 local seal verification.

---

## Phase 1 task list

### V1 — `--rubric-file` flag in meta-tool wrapper

Add `--rubric-file PATH` argument to `meta_tool/hermes_meta_rubric.py` CLI. When provided, `run_meta_rubric()` skips `synthesize()` and loads the rubric from the file. The rest of the pipeline (collect_evidence, score, apply_policy_clamps) runs unchanged.

Acceptance:
- Flag accepts JSON file with rubric structure matching `synthesize()` output.
- All existing 21 tests in `tests/test_meta_tool.py` still pass (`pytest tests/test_meta_tool.py -v`).
- A new unit test verifies the flag works (skip-synthesis path).
- Save end-to-end run receipt to `applied/mission-C-20260429/V1-rubric-file-receipt.json`.

### V2 — Hungarian-matched cosine on dim-description embeddings

Design and implement a deterministic rubric-equivalence metric that does not depend on an LLM judge. Per Metacognitive Framework Constraint 2:

**Required documentation in `applied/mission-C-20260429/V2-methodology.md`:**

1. **Embedding model rationale.** Specify which embedding model is used. Justify philosophically: rubric-dimension descriptions are short prose (~1-3 sentences each) that must be compared for SEMANTIC equivalence. The chosen model must capture semantic similarity at sentence-level granularity. Recommended: nomic-embed-text via local Ollama (already in stack) OR sentence-transformers all-MiniLM-L6-v2 if available. Justify your choice.

2. **Random-permutation null methodology.** Mathematical specification:
   - Sample N random dim-description pairs from a corpus of synthesized rubrics (or from the dim-text token vocabulary if no corpus exists)
   - Compute Hungarian-matched cosine for each random pair
   - Build the empirical null distribution (mean, std)
   - Threshold = null_mean + 2 × null_std
   - PROVE this threshold separates genuine semantic equivalence from baseline vocabulary overlap

3. **Sanity check (Constraint 2 explicit).** If the threshold is suspiciously low (<0.3) or suspiciously perfect (>0.95), HALT V2. Log the suspicious threshold to `applied/mission-C-20260429/V2-halt-log.md` with the null-distribution shape and the threshold's percentile. Do NOT proceed.

**Implementation:**
- Run synthesizer 5 times with identical inputs (intent="audit this paper for epistemic accountability and hygiene", target=META-RUBRIC paper, target_type=preprint-paper).
- Save the 5 synthesized rubrics to `applied/mission-C-20260429/V2-rubrics/run-1.json` ... `run-5.json`.
- Compute pairwise (10 pairs) Hungarian-matched cosine on dim descriptions.
- Compute random-permutation null at N≥100 random pairs.
- Report: same-input pair scores vs null distribution. Pass if same-input scores ≥ threshold AND threshold passed sanity check.

Save full results to `applied/mission-C-20260429/V2-results.json`.

### V3 — hermeneutic Stage 1 pre-filter

Run `hermeneutic` Stage 1 (regex gate, zero-LLM) on the 7 dim descriptions from one of the V2-saved rubrics. Document:
- Which dims fire which regex rules (if any).
- Which dims pass clean.
- Whether the gate produces differentiated output (at least one firing AND at least one passing clean).

Save to `applied/mission-C-20260429/V3-hermeneutic-output.md`.

### V4 — hermes-seal local pre-registration

Verify that `hermes-seal` can locally seal `applied/PRE-REGISTRATION-20260429.md` (or a copy of it). Run the seal command, capture exit code. If exit code = 0, the seal is valid.

Save the seal verification output to `applied/mission-C-20260429/V4-seal-verification.txt`.

(Note: do NOT actually seal the master pre-registration unless Roli has authorized that specific operation; verify mechanism on a copy if uncertain.)

### Phase 1 self-rubric

After V1-V4, score against `PRE-REGISTRATION-20260429.md` Mission C Phase 1 rubric. Save to `applied/mission-C-20260429/PHASE-1-SELF-RUBRIC.md`.

---

## Phase 2 — STRICTLY CONDITIONAL

Phase 2 runs ONLY IF Phase 1 self-rubric scores ≥8/10 with no V-component scoring 0.

Phase 2 task list (do NOT begin without Phase 1 passing):
- Run cap-on/cap-off comparison with V1's `--rubric-file` flag, V2's equivalence metric, V3's pre-filter
- Document empirical findings
- Save to `applied/mission-C-20260429/PHASE-2-RESULTS.md`

If Phase 1 fails: STOP. Document each failed component as R&D output for langquant project at `applied/mission-C-20260429/PHASE-1-FAILED-RND-OUTPUT.md`.

---

## Red-Team Scratchpad requirement (per Constraint 1) — REQUIRED before EACH commit

Before EVERY git commit, output a `<verification_scratchpad>` block:

```
<verification_scratchpad>
ADVERSARIAL CLAIM: <one sentence — what would a skeptic say is wrong with this commit?>
LIKELY FAILURE MODE: <specific edge case or oversight>
WHY THIS APPROACH SURVIVES: <explicit explanation; if you cannot, halt>
</verification_scratchpad>
```

V2-specific scratchpad MUST include: "is the threshold I derived suspiciously low/perfect (Constraint 2 sanity)?"

If the scratchpad surfaces a failure mode the approach does NOT survive, HALT. Do not commit. Log to `applied/mission-C-20260429/halt-log.md`.

---

## Halt triggers (any one → halt, log, end mission)

- V2 sanity check fails (suspicious threshold)
- V1 breaks any existing test in `tests/test_meta_tool.py`
- Scratchpad failure (unresolved adversarial claim)
- Banned action attempted
- 90 min without commit during Phase 1
- Phase 1 self-rubric below floor (8/10 or any V=0)

---

## Banned actions

- `git push`
- `gh release create`, `gh pr create`
- HTTP POST to public URLs except Claude CLI / Ollama localhost / WebFetch on arxiv
- Any write to `~/.claude/`
- Any modification of files in `~/Documents/projects/hermes-content/papers/` (Mission B's lane, I/O Quarantine Constraint 4)
- Any modification of files in `applied/mission-B-20260429/`
- Any spawn of further autonomous agents
- Any modification of `PRE-REGISTRATION-20260429.md` or `METACOGNITIVE-FRAMEWORK-20260429.md`

---

## Voice priors (for any prose you produce)

Same as Mission B. Voice-grep before any commit on prose-bearing files (markdown).

---

## Begin

Start by reading the 8 files listed above. Then begin V1 (smallest, surest scope). After V1 commit (with scratchpad), proceed to V2. V2 is the load-bearing component; do its methodology documentation BEFORE running any embedding code.

You bear the HAL + Hermes Labs name. Surgical quality. The Embedding & Math Justification (Constraint 2) is non-negotiable. We do not trade LLM-judge bias for embedding-space bias.
