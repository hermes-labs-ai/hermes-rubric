# hermes-rubric — Multi-backend support spec (v0.2 candidate)

**Status:** spec only. No code. Estimated effort: 1 day for v0.2 with two new
backends + tests; longer if Bedrock / Vertex are required.

**Priority:** medium-high. Unblocks: harvester perf, /launch-microtool Phase
6.5 preflight, in-CI rubric runs, and any user who has an API key but doesn't
have Claude Code's CLI installed.

---

## Problem

`hermes-rubric` v0.1.x supports two backends:

1. `claude-cli` — invokes `claude --print` as a subprocess. Each rubric run
   spawns 3 separate subprocesses (synthesize → evidence → score), each with
   full Claude Code bootstrap (hooks, LSP, plugin sync, CLAUDE.md, memory
   ingestion). Wall-clock cost: 3-8 minutes per run.
2. `ollama-local` — local HTTP to `localhost:11434`. Fast, free, but quality
   is bounded by whichever local model is pulled (qwen3.5:9b in our test
   today returned uniform `dim_N: 6/10` with empty rationales — not usable
   for rubric synthesis on abstract targets).

**Gap:** users with an `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or OpenRouter
token cannot use them directly. The bare-mode patch in `backends.py` already
detects `ANTHROPIC_API_KEY` and switches `claude --print` to `--bare`, but
that still pays the subprocess + Claude Code init cost on every call. Direct
HTTP to Anthropic / OpenAI would eliminate the subprocess entirely (30 sec
per rubric run vs. 3-8 min).

## Goal

Pluggable backend system supporting (at minimum) the following targets, with
auto-detection by environment variable:

| Backend ID | Detection signal | Provider |
|---|---|---|
| `claude-cli` (existing) | `claude` on PATH + ping ok | Claude Code subprocess |
| `ollama-local` (existing) | `ollama` on PATH + `localhost:11434` healthy | Local Ollama |
| **`anthropic-api`** | `ANTHROPIC_API_KEY` env | Anthropic direct |
| **`openai-api`** | `OPENAI_API_KEY` env | OpenAI direct |
| **`openrouter`** | `OPENROUTER_API_KEY` env | OpenRouter (proxies to many) |
| **`bedrock`** | AWS creds + `AWS_REGION` | Amazon Bedrock (deferred to v0.3) |
| **`vertex`** | `GOOGLE_APPLICATION_CREDENTIALS` | Google Vertex (deferred to v0.3) |

Default detect order should prefer **API backends** over `claude-cli` when an
API key is present, because:

- API call latency is ~10x lower than subprocess+bootstrap
- API backends are isolated by construction (no CLAUDE.md, no memory, no
  hooks) — already context-compensated without needing `--bare` mode
- Receipt's `backend` field surfaces which one was used, preserving audit
  traceability

## Non-goals (v0.2)

- Streaming responses (rubric is single-shot completion)
- Function-calling / tool-use (rubric uses pure text completions)
- Multi-modal inputs (images, audio)
- Cost tracking (out of scope; let downstream tools track via the receipt)
- Model-specific quirks (per-provider system-prompt handling, output-format
  enforcement) beyond what's required for the JSON schemas the three stages
  emit

## Architecture

### Backend interface

A backend is a callable that returns `str` for a prompt. Add a thin Protocol:

```python
# src/hermes_rubric/backends/_interface.py
from typing import Protocol

class Backend(Protocol):
    name: str        # registry key, e.g. "anthropic-api"
    label: str       # receipt label, e.g. "anthropic-api/claude-haiku-4-5"

    def call(self, prompt: str, max_tokens: int = 2048) -> str: ...

    def healthy(self) -> bool: ...   # quick liveness check for detect()
```

Each concrete backend lives in its own module under
`src/hermes_rubric/backends/`:

```
backends/
  __init__.py          # detect(), call(), label registry
  _interface.py        # Backend Protocol
  claude_cli.py        # existing
  ollama_local.py      # existing
  anthropic_api.py     # NEW
  openai_api.py        # NEW
  openrouter.py        # NEW (thin variant of openai_api with base_url override)
```

### Detection priority

Update `detect()` in `backends/__init__.py` to:

```
1. Force-via-flag (--backend X) — bypass detection
2. Environment-variable backends (highest priority — present means user opted in)
   a. ANTHROPIC_API_KEY → anthropic-api
   b. OPENAI_API_KEY    → openai-api
   c. OPENROUTER_API_KEY → openrouter
3. Subprocess backends (only when no API key)
   a. claude-cli (if `claude` on PATH and ping returns 0)
4. Local backends (free fallback)
   a. ollama-local
5. Raise — no backend available
```

### Default model per backend

Each backend has a default model (overridable via env or `--model` CLI flag):

| Backend | Default model | Override env |
|---|---|---|
| anthropic-api | `claude-haiku-4-5-20251001` (cost) | `HERMES_RUBRIC_MODEL` |
| openai-api | `gpt-4o-mini` (cost) | same |
| openrouter | `anthropic/claude-haiku-4-5` (cost) | same |
| ollama-local | `qwen3.5:14b` (existing) | `HERMES_RUBRIC_MODEL` |
| claude-cli | inherit from claude default | n/a |

Why Haiku/mini default: rubric synthesis + scoring on a paragraph-sized
target does not need Opus-level capability. Haiku is the floor; users can
upgrade via the env var.

### Receipt label

The receipt's `backend` field becomes more granular:

```json
"receipt": {
  "backend": "anthropic-api/claude-haiku-4-5-20251001",
  "context_isolation": "api-direct",   // NEW field
  ...
}
```

`context_isolation` values:

- `api-direct` — backend is a clean HTTP call, no inherited context
- `claude-cli-bare` — claude-cli with `--bare` (existing)
- `claude-cli-contextual` — claude-cli without `--bare` (caller context bleed)
- `ollama-local` — local model, no inherited context

## Implementation steps (for the agent picking this up)

1. **Create the Backend Protocol** at `src/hermes_rubric/backends/_interface.py`.
2. **Refactor existing `backends.py`** into `backends/__init__.py` +
   `backends/claude_cli.py` + `backends/ollama_local.py`. Keep public API
   identical (`call()`, `detect()`, `claude_cli_mode()`).
3. **Add `anthropic_api.py`** using `httpx` (or stdlib `urllib`) — POST to
   `https://api.anthropic.com/v1/messages`. Add `anthropic` to optional
   `[project.optional-dependencies.api]` if using the SDK; prefer raw HTTP
   to keep stdlib-only ethos.
4. **Add `openai_api.py`** — POST to `https://api.openai.com/v1/chat/completions`.
5. **Add `openrouter.py`** — same as openai_api but with `base_url=https://openrouter.ai/api/v1` and `HTTP-Referer` header.
6. **Update `cli.py`** to add `--model` flag and pass through.
7. **Update `receipt.py`** to include `context_isolation` field.
8. **Add tests** (`tests/test_backends_api.py`):
   - Mocked HTTP for each new backend (no real API calls in CI)
   - Detection priority test: when multiple env keys present, anthropic wins
   - Receipt label correctness per backend
9. **Document** in README + AGENTS.md + llms.txt — add backend table.
10. **Bump** `0.1.x → 0.2.0` (breaking config-shape change to receipt).

## Test plan (verifiable)

For each new backend:

- [ ] Unit test mocks the HTTP call; asserts the request body has the
      correct shape for that provider.
- [ ] Unit test asserts the response parser extracts the text correctly
      from that provider's response shape.
- [ ] Detection test: when only that backend's env var is set, `detect()`
      returns it.
- [ ] Detection test: when multiple env vars are set, the priority order
      above is honored.

End-to-end (manual, not CI — costs money):

- [ ] Live run against each backend with a fixture target (the hermes-blind
      README) — assert aggregate score within ±1.5 across backends.
- [ ] Live run latency: each new backend completes a full rubric pass in
      ≤45 seconds (vs. 3-8 min for claude-cli non-bare).

## Open questions (decide during implementation)

1. **SDK or raw HTTP?** Anthropic + OpenAI both ship Python SDKs. Pulling
   them in adds ~2MB to the install. Raw HTTP keeps stdlib-only. **Recommend:**
   raw HTTP via `urllib`, falling back to optional `[api]` extra if a user
   prefers the SDK ergonomics.
2. **Retry / backoff?** Each provider has its own rate-limit shape. Pick a
   single exponential-backoff policy that works for all (3 retries,
   2s/8s/30s) and let providers' own 429s drive it.
3. **Streaming?** Out of scope for v0.2 (rubric is single-shot). Reconsider
   if multi-turn rubric flows land in v0.3.
4. **Bedrock + Vertex?** Defer to v0.3. Bedrock has IAM auth complexity;
   Vertex has GCP credential file chain. Each is its own day of work.

## Compatibility

- v0.2 is **backwards compatible** for callers that use auto-detection: if
  no API keys are set, the existing `claude-cli > ollama-local` order still
  applies.
- v0.2 is **not** backwards compatible for callers that read `receipt.backend`
  expecting one of `{"claude-cli", "ollama-local"}`. New labels include
  provider+model. Document the change in CHANGELOG.

## Success criteria

After v0.2 lands:

- A user with `ANTHROPIC_API_KEY` set runs `hermes-rubric ...` and sees
  a rubric pass complete in <45 seconds instead of 3-8 minutes.
- The harvester's per-candidate rubric call no longer times out at the
  default 300s timeout.
- /launch-microtool's Phase 6.5 preflight can run a real `hermes-rubric`
  pass during repo polish without spending 5+ minutes per candidate.
- `receipt.backend` clearly labels which provider+model produced the score.
