# Coordination Roadmap — HAL state machine for Mission B + Mission C

**Coordinator:** HAL (this Claude Code session, main context).
**Spawned missions:** Mission B (paper hardening), Mission C (Hermes-native pilot).
**Watching gate:** Roli, monitoring logs.

---

## State machine

```
STATE_0: PRE-SPAWN
  - Pre-registration sealed locally
  - Spec + meta-prompts written
  - Both mission directories quarantined (per Constraint 4)
  - HAL action: spawn Mission B → wait 2 min → spawn Mission C

STATE_1: BOTH_RUNNING
  - Mission B running on hermes-content paper edits + adversarial verdict
  - Mission C running Phase 1 (V1 → V2 → V3 → V4)
  - HAL action: WAIT. No status updates to Roli unless halt-trigger or Phase 1 of C complete.
  - HAL re-reads output files before any communication, never reports from memory.

STATE_2: ONE_HALTED (mission halted on scratchpad / banned action / 90-min-no-commit)
  - HAL action: surface halt to Roli with halt-log path. Do NOT auto-restart. Wait for Roli direction.

STATE_3: BOTH_RUNNING_C_PHASE_1_COMPLETE
  - Mission C Phase 1 verdict in (success or failure).
  - HAL reads C's PHASE-1-SELF-RUBRIC.md.
  - HAL reports Roli: Phase 1 verdict + Mission B status (still running OR completed).

STATE_4: PHASE_1_PASS_DECISION_POINT
  - Roli decides: greenlight Phase 2, OR halt at Phase 1 (success), OR fold C findings into B.
  - HAL action: execute Roli's decision. Do not auto-decide.

STATE_5: PHASE_1_FAIL_FALLBACK
  - C halted at Phase 1 with documented R&D output for langquant.
  - HAL: report to Roli, await direction. Default: B proceeds with cuts (per pre-registration sync rule 3).

STATE_6: BOTH_COMPLETE
  - Mission B reports MISSION-B-REPORT.md with self-rubric and adversarial-after verdict.
  - Mission C reports PHASE-1-SELF-RUBRIC.md (and PHASE-2-RESULTS.md if applicable).
  - HAL synthesizes: ship recommendation per Roli's "B or C delivers" principle.

STATE_7: SHIP_DECISION
  - Roli's call. HAL does not auto-merge per Constraint 4.
  - If Roli says ship: HAL surfaces the final artifact path for upload.
  - If Roli says iterate: HAL spawns next iteration mission(s) per same framework.
```

---

## HAL non-actions (forbidden coordinator behaviors)

- HAL does not generate verification scratchpads on behalf of subagents.
- HAL does not modify any spec, pre-registration, or meta-prompt after spawn.
- HAL does not commit on behalf of subagents.
- HAL does not merge B and C output.
- HAL does not status-update Roli between framework-defined surfacing events.
- HAL does not retrofit pre-registration to outcomes.
- HAL does not auto-decide ship vs. iterate.

---

## HAL actions allowed during STATE_1

- Read mission output files (read-only) to refresh status memory.
- Respond to Roli's direct messages in main context (without cross-contaminating mission state).
- Write to applied/coordinator-log-20260429.md (HAL's own log, separate from missions).
- Halt either mission via TaskStop if Roli explicitly directs.

---

## Halt-and-escalate path

If HAL detects a banned-action attempt OR scratchpad failure in either mission's output:

1. HAL does NOT auto-halt the mission (subagent has its own halt logic; let it self-halt).
2. HAL reads the halt-log from the mission's directory.
3. HAL surfaces to Roli: mission name, halt reason, halt-log path, what was committed before halt, recovery options.
4. HAL waits for Roli direction. Default: do not restart without authorization.

---

## Final-state report template (for STATE_6 / STATE_7)

When both missions complete, HAL produces this report:

```
=== MISSION SUMMARY 2026-04-29 ===

MISSION B (Paper Hardening):
- Status: <COMPLETE / HALTED-AT-PHASE-X>
- Self-rubric: <X/19>
- Adversarial-after verdict: <X% FIX-BEFORE-SHIP / PUBLISH-AS-IS>
- Phantom-limb check: <PASS / FAIL — details>
- Citations added: <N of 5, verified>
- Artifact: <paper.pdf path, page count>

MISSION C (Hermes-Native Pilot):
- Phase 1 self-rubric: <X/10>
- V1 (--rubric-file): <PASS / FAIL>
- V2 (Hungarian cosine + null): <PASS / FAIL — threshold X derived from null-mean Y, std Z>
- V3 (hermeneutic Stage 1): <PASS / FAIL — N firings, M passing>
- V4 (hermes-seal): <PASS / FAIL — exit code>
- Phase 2: <RUN / DEFERRED — reason>

SHIP RECOMMENDATION (HAL synthesis, not decision):
- B-only path readiness: <READY / NEEDS-WORK — reason>
- C-augmented path readiness: <NOT-EVALUATED / READY-PENDING-PHASE-2 / R&D-OUTPUT-ONLY>
- HAL suggests: <one-paragraph framing for Roli's decision>

ROLI ACTION REQUIRED: <ship B-only / ship B+C-augmented / iterate / abandon-and-ship-16-page-version>
```

---

## Failure-recovery floor (per principle 6)

If BOTH missions fail (Mission B adversarial-after >40% FIX-BEFORE-SHIP AND Mission C Phase 1 <8/10):
- Fallback artifact: the existing 16-page paper.pdf with explicit "v1 preliminary" caveat in MORNING-REPORT.
- HAL does NOT auto-ship the fallback. HAL surfaces to Roli with explicit recommendation: "ship as v1-preliminary OR iterate".
- Worst-case outcome: zero ship today, R&D documentation gain (langquant gaps surfaced + paper structural gaps catalogued) — non-zero output day.
