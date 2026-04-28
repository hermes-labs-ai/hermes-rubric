# Backends

Seven built-in backends, auto-detected in priority order. Force one with `--backend <name>`.

## Built-in matrix

| Backend | Requires | Notes |
|---|---|---|
| `claude-cli` | Claude Code installed (`claude --print`) | Default. Highest consistency. |
| `ollama-local` | Ollama running locally (default `qwen3.5:14b`) | Zero cost, offline. Fallback chain: `gemma3:12b` → `gemma3:4b` → `mistral:7b` → `qwen3.5:9b` → `qwen3.5:4b`. |
| `dashscope-qwen` | `DASHSCOPE_API_KEY` | Alibaba Cloud Qwen. |
| `google-gemini` | `GOOGLE_GEMINI_API_KEY` | REST. |
| `openai` | `OPENAI_API_KEY` | REST, no SDK dep. |
| `openai-sdk` | `OPENAI_API_KEY` + `pip install hermes-rubric[openai]` | Uses official SDK. |
| `google-genai` | `GOOGLE_GEMINI_API_KEY` + `pip install hermes-rubric[google]` | Uses google-genai SDK. |

## Selection

If `--backend` is not specified, hermes-rubric auto-detects in priority order:

1. `claude-cli` (if `claude` is on `PATH`)
2. `ollama-local` (if `OLLAMA_BASE_URL` is reachable)
3. `dashscope-qwen` (if `DASHSCOPE_API_KEY` is set)
4. `google-gemini` (if `GOOGLE_GEMINI_API_KEY` is set)
5. `openai` or `openai-sdk` (if `OPENAI_API_KEY` is set)

Force one with `--backend claude-cli` (or any other name from the matrix above).

## Plugin protocol

Backends conform to a single `BackendProtocol`:

```python
from typing import Protocol

class BackendProtocol(Protocol):
    name: str
    def call(self, prompt: str, max_tokens: int = 2048) -> str: ...
    def detect_available(self) -> bool: ...
```

## Registering a backend at runtime

```python
from hermes_rubric.backends import register

class MyBackend:
    name = "my-backend"
    def call(self, prompt, max_tokens=2048):
        # invoke your model, return string
        ...
    def detect_available(self):
        # return True if your backend is configured
        ...

register(MyBackend())
```

After `register()`, hermes-rubric uses the new backend on the next call. `--backend my-backend` forces selection.

## Distributing as a plugin package

Ship a third-party package via the `hermes_rubric.backends` entry-point group:

```toml
# pyproject.toml of your plugin package
[project.entry-points."hermes_rubric.backends"]
my-backend = "my_pkg.backend:MyBackend"
```

Users `pip install` your package, and hermes-rubric discovers it on first call.

## Reference implementation

See `src/hermes_rubric/backends.py` for the source-of-truth implementations of all seven built-in backends. Each is ~30-60 lines.

## Cost / consistency tradeoff

| Backend | Cost / 1k runs | Per-run consistency |
|---|---|---|
| `claude-cli` | $0 (uses your Claude Code subscription) | High |
| `ollama-local` | $0 (local compute) | Medium |
| `dashscope-qwen` | ~$0.50 | High |
| `google-gemini` | ~$1-3 | High |
| `openai` / `openai-sdk` | ~$5-15 | High |

## Choosing for your use case

- **CI / local dev:** `claude-cli` if you have Claude Code; otherwise `ollama-local`
- **Cross-backend agreement check:** run with two backends, use `hermes-rubric kappa` to measure
- **Production scoring at volume:** `dashscope-qwen` (cheapest cloud) or `claude-cli` if you have a subscription with headroom
- **Highest cross-backend κ in our test set:** `claude-cli` paired with `dashscope-qwen` (κ = 0.642 on Gemini, 0.621 on Qwen, see [`BENCHMARKS.md`](BENCHMARKS.md))
