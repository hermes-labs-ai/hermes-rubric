# auto-pilot fix summary — 2026-04-28

## Problem
`hal-auto-self-prompt.sh` fired off-mission classifier+compose prompts
("verify the recent file edits...", "run lintlang scan...") while main
Claude Code session was mid-bounded-mission. Root: transcript fallback
read 16k tail across turn boundaries, producing multiple `<hal:next-hint>`
tags → AMBIGUOUS rejection → fallback to generic classifier+compose.

## Fixes applied

### Fix A — transcript fallback: last-assistant-turn only
File: `~/.claude/hooks/hal-auto-self-prompt.sh`
Lines: fallback block after `LAST_OUTPUT` payload extraction.

Changed `tail -c 16000 "$TPATH"` to a Python JSONL parser that walks
the transcript in reverse and extracts only the last assistant turn
(truncated to 8000 chars). If JSONL parse yields nothing, falls back
to `tail -c 4000` (not 16000 — narrower window).

Effect: prior-turn `<hal:next-hint>` tags no longer contaminate the
hint search window. AMBIGUOUS false positives drop to near zero.

### Fix B — mission-marker suppresses classifier fallback
File: `~/.claude/hooks/hal-auto-self-prompt.sh`
Inserted between hint-extraction block and `hal-auto-classify` call.

Logic:
```
if LAST_OUTPUT contains <hal:mission-active> (case-insensitive)
   AND no usable hint was extracted:
     log "fire:N | reason:mission-active-no-hint"
     exit 0
```

Effect: bounded-mission sessions that emit `<hal:mission-active>` in
their last assistant turn prevent generic continuation prompts. If a
valid `<hal:next-hint>` is present, the hint fires normally; Fix B
does not block that path.

### Fix C — hint regex: last 2000 chars only
File: `~/.claude/hooks/hal-auto-self-prompt.sh`
Lines: `HINT_RAW` extraction block.

Changed: `re.findall` ran on full `text` → now runs on `text[-2000:]`.

Effect: hints quoted/embedded in message bodies (not at tail) are
ignored. Control-signal hints placed at message end are honoured.
Two hints in tail still → AMBIGUOUS (correct).

## Test fixture
`~/.claude/hooks/test-hal-auto-self-prompt.sh`
10 unit tests, all logic tested in-process (no Claude CLI invocations).
Results: 10/10 PASS.

Tests cover:
- A1/A2: JSONL last-turn extraction correctness + no cross-turn leak
- B1-B4: mission-active suppression (no-hint, with-hint, no-tag, uppercase)
- C1-C4: tail-restricted hint (tail-only, body-only ignored, AMBIGUOUS, body+tail)

## Git
Home directory is not a git repo. Changes saved in place.

## Constraints respected
- Only modified: `~/.claude/hooks/hal-auto-self-prompt.sh`
- Only created: `~/.claude/hooks/test-hal-auto-self-prompt.sh`
- Did NOT modify: `~/bin/rolitwin-self-prompt`, `~/bin/hal-auto-classify`,
  `~/bin/hal-auto-compose`, `settings.json`
- No GitHub push. No public-touch.

## Next-fire behavior
The next auto-pilot fire against a session that emits `<hal:mission-active>`
with no trailing `<hal:next-hint>` will log:
```
fire:N | reason:mission-active-no-hint
```
and exit without typing anything into the terminal.
