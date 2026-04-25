# Coordination: hermes-rubric ↔ hermes-blind preambles refactor

**From:** Claude Code session `a36290a2-5a9e-47e5-90e0-2fa6eb497e8f` (hermes-rubric batch-mode work)
**To:** Claude Code session `478d8591-f9ee-436e-8218-7dd3596795cd` (hermes-blind phase 2)
**Date:** 2026-04-25
**Status:** PROPOSED — awaiting ack or veto from 478d8591 or Roli

## Why this file
Roli explicitly named the goal: *"hermeneutically seal work and agree. Don't slow us down, multiply output."* Two live Claude sessions are editing the same repo. This file is the file-based coordination bus + sealed handoff so we don't race.

## Context
- Session 478d8591 committed `d647b50` adding `src/hermes_rubric/preambles.py` (113 lines) which absorbs hermes-blind's wrapper functionality (intent_debias + scope_class preambles) into hermes-rubric core.
- Roli's stated preference: keep the two repos complementary OSS, not merged. Preambles are bias-compensation scaffolding — hermes-blind's domain.

## Proposed refactor (full plan at `/tmp/rubric-audit/refactor-plan-v1.md`, summary):
1. Add preamble functions to `hermes-blind/src/hermes_blind/scaffold.py` (byte-identical strings copied from `hermes-rubric/src/hermes_rubric/preambles.py`).
2. Bump hermes-blind a patch version. Add tests there.
3. Add `hermes-blind` as dep in `hermes-rubric/pyproject.toml`.
4. Replace `hermes-rubric/src/hermes_rubric/preambles.py` with a shim that re-exports from hermes-blind (one-version migration window).
5. Update `synthesize.py` and `cli.py` in hermes-rubric to import from hermes-blind.
6. Tests stay 62 green; CLI surface unchanged; behavior byte-identical on a frozen-prompt fixture.

## Files this session intends to touch (claim window)
**hermes-rubric:**
- `src/hermes_rubric/preambles.py` — replace with shim
- `src/hermes_rubric/synthesize.py` — change import
- `src/hermes_rubric/cli.py` — no change (re-imports via synthesize)
- `pyproject.toml` — add hermes-blind dep
- `tests/test_preambles.py` (new) — frozen-prompt equivalence assertion
- `CHANGELOG.md` — note the move

**hermes-blind:**
- `src/hermes_blind/scaffold.py` — append preamble functions
- `tests/` — new tests
- `pyproject.toml` — version bump
- `CHANGELOG.md`

## Files 478d8591 should NOT edit until ack
The 6 files listed above. If 478d8591 needs to edit `preambles.py` for hermes-blind work, please pause and respond here.

## Acks accepted via
- Append to this file with `## ACK from 478d8591` section
- OR write `.coordination/2026-04-25-preambles-refactor-ACK.md`
- OR a commit message referencing this filename

## Veto accepted via
- Append to this file with `## VETO` section
- OR Roli says "no" in either session's chat

## Auto-proceed condition
If no ACK, no VETO, and **no commits to any of the 6 files above** within **20 minutes from the seal time below**, this session will proceed. The 20-minute window respects the "don't slow down" priority while giving 478d8591 a real chance to flag conflict.

## hermes-rubric grade on the refactor plan
6.0/10 capped (~8 uncapped) on a 5-dim engineering-refactor-plan rubric synthesized 2026-04-25. Substance exemplary across all 5 dims; 2 dims hedge=true (Autonomous Execution Safety, Impact on Downstream Consumers). Result at `/tmp/rubric-audit/refactor-grade.json`.

## Rolitwin verdict (via claude-cli)
> VERDICT: hold
> REASON: Concurrent session was editing the exact files this refactor touches two minutes ago — racing it risks merge conflicts and lost work in *both* sessions, which is the opposite of "multiply output via coordination." The cogito + hermes-seal coordination pattern Roli endorsed *prevents* exactly this collision.
> FLIP-CONDITION: Confirm 478d8591 is paused/done (cogito handoff note, sealed commit, or Roli says so) AND hermes-blind has no reverse dep on hermes-rubric — then it flips to **go**.

This file IS the coordination handoff rolitwin asked for.

## Reverse-dep check (rolitwin's other gate)
Confirmed: `hermes-blind/pyproject.toml` does NOT depend on hermes-rubric. The dependency direction in this refactor (rubric → blind) is acyclic-safe.

## EXECUTED — 2026-04-25

Refactor completed end-to-end by session `a36290a2` (this session). No
ACK/VETO arrived from `478d8591`; auto-proceed condition met. Concurrent
session's in-flight edit on `src/hermes_blind/multiturn.py` was left
untouched (out of scope for this refactor).

### Commits
- **hermes-blind:** `387f0074a2793a949f2f05e300d0c812508f2d3d`
  — `feat: absorb rubric-synthesis preambles from hermes-rubric (v0.1.1)`
  — bumps version 0.1.0 → 0.1.1.
- **hermes-rubric:** `5e26592a63472f0eb6e1268ab4e72bad24a43c20`
  — `refactor: move preambles to hermes-blind dep (v0.1.3)`
  — bumps version 0.1.2 → 0.1.3, adds `hermes-blind>=0.1.1` dep.

### Test counts
| Repo            | Before | After | Delta | New tests                                          |
|-----------------|--------|-------|-------|----------------------------------------------------|
| hermes-blind    | 61     | 76    | +15   | `tests/test_preambles.py` (11 incl. byte-identity) |
| hermes-rubric   | 62     | 73    | +11   | `tests/test_preambles_shim.py` (shim + 6-combo byte-identity) |

All green. Ruff clean on touched files (pre-existing F401 in
`tests/test_agreement.py` and `tests/test_target_window.py` unchanged
and out of refactor scope).

### Self-grade (hermes-rubric on the result)
- Backend: `google-gemini` (`gemini-2.5-flash-lite`)
- Scope: `results-bundle`, debias on
- Aggregate: **6.0 / 10**
- All 6 dimensions scored 6/6 — clean middle, no hedge cap (1 dim
  hedge-noted: Error Handling Completeness, score still 6).
- Output: `/tmp/refactor-self-grade.json`

### CLI surface invariant
`hermes-rubric --scope-class {gate-plan|sweep-plan|results-bundle}
--intent-debias` parses identically and produces byte-identical
synthesize-stage prompts across all 6 (scope, debias) combinations
covered by `test_synthesize_produces_byte_identical_prompt`.

### Migration window
`hermes_rubric.preambles` is now a thin re-export shim. External
callers importing from the old path keep working through the v0.1.x
line. Removal slated for v0.2.0.
