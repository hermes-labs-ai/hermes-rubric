"""Backend auto-detection and invocation. Priority: claude-cli > ollama-local."""

import json
import shutil
import subprocess
import urllib.request
import urllib.error
from typing import Literal

Backend = Literal["claude-cli", "ollama-local"]

_OLLAMA_DEFAULT_MODEL = "qwen3.5:14b"
# Prefer non-reasoning models for structured JSON output. qwen3.5 reasoning
# models emit into `thinking` and often wrap the requested JSON in prose.
_OLLAMA_FALLBACK_MODELS = ["gemma3:12b", "gemma3:4b", "mistral:7b", "qwen3.5:9b", "qwen3.5:4b"]


def detect() -> Backend:
    """Return the first available backend."""
    if shutil.which("claude"):
        try:
            r = subprocess.run(
                ["claude", "--print", "ping"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode == 0:
                return "claude-cli"
        except (subprocess.TimeoutExpired, FileNotFoundError):  # noqa: silent
            pass

    if shutil.which("ollama"):
        try:
            req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
            if req.status == 200:
                return "ollama-local"
        except (urllib.error.URLError, OSError):  # noqa: silent
            pass

    raise RuntimeError(
        "No backend available. Install Claude Code (claude CLI) or Ollama with a qwen3.5 model."
    )


def _ollama_model() -> str:
    """Return the best available Ollama model name."""
    try:
        req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        data = json.loads(req.read())
        available = {m["name"] for m in data.get("models", [])}
        for candidate in [_OLLAMA_DEFAULT_MODEL] + _OLLAMA_FALLBACK_MODELS:
            if candidate in available:
                return candidate
        # Return default; let Ollama error if missing
        return _OLLAMA_DEFAULT_MODEL
    except Exception:
        return _OLLAMA_DEFAULT_MODEL


def call(prompt: str, backend: Backend | None = None, max_tokens: int = 2048) -> str:
    """Run a prompt against the selected backend and return the response text."""
    if backend is None:
        backend = detect()

    if backend == "claude-cli":
        return _call_claude_cli(prompt, max_tokens)
    elif backend == "ollama-local":
        return _call_ollama(prompt, max_tokens)
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _call_claude_cli(prompt: str, max_tokens: int) -> str:
    r = subprocess.run(
        ["claude", "--print", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(f"claude --print failed (exit {r.returncode}): {r.stderr[:400]}")
    return r.stdout.strip()


def _call_ollama(prompt: str, max_tokens: int) -> str:
    model = _ollama_model()
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
            # Reasoning models (qwen3.5) emit into `thinking` and leave `response` empty.
            # Prefer response; fall back to thinking so the pipeline works with either.
            out = data.get("response", "") or data.get("thinking", "")
            return out.strip()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama call failed: {e}") from e
