# Backends

Seven built-in backends are available. Automatic selection checks only Claude Code, then local Ollama; cloud backends are explicit opt-ins through `--backend <name>`.

## Built-in matrix

| Backend | Requires | Notes |
|---|---|---|
| `claude-cli` | Claude Code installed (`claude --print`) | First automatic candidate. |
| `ollama-local` | Ollama running locally (default `qwen3.5:14b`) | Zero cost, offline. Fallback chain: `gemma3:12b` → `gemma3:4b` → `mistral:7b` → `qwen3.5:9b` → `qwen3.5:4b`. |
| `dashscope-qwen` | `DASHSCOPE_API_KEY` | Alibaba Cloud Qwen. |
| `google-gemini` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | REST. |
| `openai` | `OPENAI_API_KEY` | REST, no SDK dep. |
| `openai-sdk` | `OPENAI_API_KEY` + `pip install hermes-rubric[openai]` | Uses official SDK. |
| `google-genai` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` + `pip install hermes-rubric[google]` | Uses google-genai SDK. |

## Selection

If `--backend` is not specified, hermes-rubric auto-detects in priority order:

1. `claude-cli` when authenticated `claude --print ping` succeeds
2. `ollama-local` when `http://localhost:11434/api/tags` is reachable

Force one with `--backend claude-cli` (or any other name from the matrix above).

## Plugin protocol

Backends conform to a single `BackendProtocol`:

```python
from typing import Protocol

class BackendProtocol(Protocol):
    name: str
    def call(self, prompt: str, max_tokens: int = 2048) -> str: ...
    def model_id(self) -> str: ...
    def availability(self) -> bool: ...
```

## Registering a backend at runtime

```python
from hermes_rubric.backends import register

class MyBackend:
    name = "my-backend"
    def call(self, prompt, max_tokens=2048):
        # invoke your model, return string
        ...
    def model_id(self):
        return "my-provider/my-model"
    def availability(self):
        # return True if your backend is configured
        ...

register(MyBackend())
```

After `register()`, call it through the Python API:

```python
from hermes_rubric import backends

result = backends.call("Score this artifact", backend="my-backend")
```

Runtime-registered names do not extend the CLI's fixed `--backend` choices.

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

## Choosing for your use case

- **CI / local development:** use an explicitly configured backend available in that environment
- **Cross-backend agreement check:** run with two backends, use `hermes-rubric kappa` to measure
- **Production:** choose explicitly based on your own latency, privacy, availability, and provider-cost requirements
- **Historical comparison context:** see the bounded report linked from [`BENCHMARKS.md`](BENCHMARKS.md)
