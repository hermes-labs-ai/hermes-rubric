# Backend Pluggability — Design

## Function

`backends.py` dispatches via `if backend == "..."` branches against a `Literal` union. Each provider added another branch plus `_call_X` and `X_model` helpers. Adding more providers compounds conditional load and forces every SDK into one file. Non-Anthropic users cannot plug their own client without forking.

This design replaces conditional dispatch with a `Backend` Protocol + registry. Existing functions stay as canonical reference impls, wrapped in adapter classes. New backends register via `register()` or `importlib.metadata` entry-points. `call(prompt, backend, max_tokens)` keeps its exact signature; every call site (cli.py, score.py, synthesize.py, evidence.py, agreement.py, batch, tests) is untouched.

## Protocol

```python
class Backend(Protocol):
    name: str                              # "claude-cli", "openai-sdk", ...
    def call(self, prompt: str, max_tokens: int) -> str: ...
    def model_id(self) -> str: ...         # for receipts
    def availability(self) -> bool: ...    # used by detect()
```

`name` is a class attribute; the three methods are required. A class missing `call` is rejected at registration time via `hasattr` + `callable` checks. No metaclass magic.

## Registry

Module-level `_REGISTRY: dict[str, Backend] = {}` populated by:

1. **Built-ins** — claude-cli, ollama-local, dashscope-qwen, google-gemini, openai wrapped in adapter classes and registered at module import. Zero behavior change.
2. **`register(backend, replace=False) -> None`** — explicit programmatic registration. Validates Protocol shape; rejects duplicates unless `replace=True`.
3. **Entry-points** — on first registry access, `importlib.metadata.entry_points(group="hermes_rubric.backends")` is scanned. Load failures surface as warnings, not crashes.

`list_backends()` and `get_backend(name)` are public. `detect()` keeps priority (claude-cli > ollama-local); entry-point backends never auto-select — must be explicit via `--backend NAME`. Preserves INTENT.md auto-detection invariant.

## Migration path

Existing `_call_*` and `*_model()` helpers stay as private functions. Thin adapter classes (`_ClaudeCLIBackend` etc.) delegate to them. Top-level `call()` becomes:

```python
def call(prompt, backend=None, max_tokens=2048):
    if backend is None: backend = detect()
    return get_backend(backend).call(prompt, max_tokens)
```

Three lines replace the if-chain. `Backend = Literal[...]` is renamed `BackendName`; class `Backend` (Protocol) takes its place. Test surface preserved — `_call_X` patches in `test_backends.py` still work because adapters delegate.

## Plugin entry-point

In a third-party `pyproject.toml`:

```toml
[project.entry-points."hermes_rubric.backends"]
azure-openai = "hermes_rubric_azure:AzureBackend"
```

`pip install hermes-rubric-azure` makes `--backend azure-openai` work with no change to hermes-rubric. Standard Python pattern; no new dependencies.

## Backwards-compat

- `--backend claude-cli` works unchanged (registered built-in).
- `backends.call("prompt", backend="ollama-local")` works unchanged.
- `backends.detect()` returns the same string literals.
- `backends.openai_model()`, `backends.gemini_model()`, `backends.dashscope_model()` and `claude_cli_mode()` stay as module-level functions — receipt code in score.py uses these.
- The `BackendName` literal type still includes all legacy names; type-checking callers continue to pass.

## Non-goals

- HTTP API server (G5, separate 1wk task).
- Authentication / secret management — providers continue to read their own env vars (`OPENAI_API_KEY` etc.), the registry never mediates credentials.
- Streaming responses — post-1.0.
- Backend selection via env-var override — explicitly forbidden by INTENT.md ("accept backend selection via environment variables that bypass the auto-detection priority order"). Registry never reads env-vars to choose backends; per-backend env-vars (model overrides) are unchanged.

## New backends as proof

1. **`openai-sdk`** — `openai` SDK (Chat Completions). Lazy import inside `call()`; `RuntimeError("openai SDK not installed; pip install hermes-rubric[openai]")` on `ModuleNotFoundError`. Default `gpt-4o-mini`. Distinct from existing `openai` (raw urllib).
2. **`google-genai`** — `google-generativeai` SDK. Same lazy + graceful-fallback. Default `gemini-2.0-flash`. Distinct from existing `google-gemini` (OpenAI-compat HTTP).

## Verification contract

**Must keep passing (76 tests):** all `tests/test_backends.py` (detect priority, fallback, routing, OpenAI HTTP, missing-key, model override) plus rubric/score/synthesis tests using `backends.call`.

**Must add (`tests/test_backends_pluggability.py`):**
1. Protocol enforcement — class missing `call()` raises `TypeError` on `register()`.
2. Registry round-trip — `register()` then `get_backend()` round-trips.
3. `list_backends()` includes built-ins.
4. Lazy-import: `import hermes_rubric.backends` does not import `openai`/`google.generativeai` (asserted via `sys.modules`).
5. Mocked `openai-sdk` path with `openai.OpenAI` patched.
6. Mocked `google-genai` path with `google.generativeai.GenerativeModel` patched.
7. Backwards-compat: `call("p", backend="claude-cli")` still routes to `_call_claude_cli`.
8. Entry-point discovery via monkeypatched `importlib.metadata.entry_points`.

## Irreversible decisions

- **Entry-points + `register()`** over `register()`-only. Standard Python plugin pattern; zero-config install. `register()` stays for in-process use.
- **Adapter wrappers** over rewriting `_call_*`. Minimizes diff; keeps existing patches working.
- **Per-provider extras** (`[openai]`, `[google]`) over a single `[sdks]`. Users pick one.
