"""Backend auto-detection and invocation. Priority: claude-cli > ollama-local.

Context-compensation: when the claude-cli backend is available and
ANTHROPIC_API_KEY is set, we invoke it in `--bare` mode. Bare mode strips
hooks, LSP, plugin sync, auto-memory, CLAUDE.md discovery, and keychain
reads, which prevents the scoring subprocess from inheriting session
context that would bias its judgment (e.g. knowledge that the scored
target was authored by the caller, or access to the caller's preferences
via CLAUDE.md / memory files). This upholds the rubric's evidence-first
invariant even when the scorer and the target share an owner.

If ANTHROPIC_API_KEY is not set, --bare cannot be used (OAuth and
keychain auth are blocked in bare mode); we fall back to non-bare
--print, accepting the context-contamination risk and surfacing it
in the receipt.
"""

import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error
from typing import Literal

Backend = Literal["claude-cli", "ollama-local", "dashscope-qwen"]

_DASHSCOPE_DEFAULT_MODEL = "qwen-plus"
_DASHSCOPE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

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
    elif backend == "dashscope-qwen":
        return _call_dashscope(prompt, max_tokens)
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _claude_cli_uses_bare() -> bool:
    """Return True if bare mode is available (ANTHROPIC_API_KEY set)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _call_claude_cli(prompt: str, max_tokens: int) -> str:
    """Invoke `claude --print` with context compensation when possible.

    Prefers --bare mode (requires ANTHROPIC_API_KEY) to isolate the
    subprocess from the caller's session context, hooks, memory, and
    CLAUDE.md. Falls back to non-bare mode if no API key is available,
    in which case the receipt will note 'claude-cli-contextual' instead
    of 'claude-cli-bare' so downstream consumers know the score may have
    been influenced by caller-side context.

    Timeout is set to 300s — bare mode is fast (no bootstrap), but
    non-bare mode can take 60-180s on first call due to hook + memory
    initialization.
    """
    cmd = ["claude", "--print"]
    if _claude_cli_uses_bare():
        cmd.append("--bare")
    else:
        # Even without --bare, strip per-machine sections to reduce
        # context bleed (cwd, env info, memory paths, git status).
        cmd.append("--exclude-dynamic-system-prompt-sections")
    cmd.append(prompt)

    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"claude --print failed (exit {r.returncode}): {r.stderr[:400]}"
        )
    return r.stdout.strip()


def claude_cli_mode() -> str:
    """Return 'claude-cli-bare' or 'claude-cli-contextual' for the receipt."""
    return "claude-cli-bare" if _claude_cli_uses_bare() else "claude-cli-contextual"


def _call_dashscope(prompt: str, max_tokens: int) -> str:
    """Invoke Alibaba DashScope (Qwen) via OpenAI-compatible endpoint.

    Uses temperature=0 and a fixed seed for determinism. Model is qwen-plus
    by default; override via HERMES_RUBRIC_QWEN_MODEL env var (e.g. qwen-max,
    qwen-turbo). Requires DASHSCOPE_API_KEY in env.
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY not set; cannot use dashscope-qwen backend")
    model = os.environ.get("HERMES_RUBRIC_QWEN_MODEL", _DASHSCOPE_DEFAULT_MODEL)

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "seed": 42,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        _DASHSCOPE_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"DashScope call failed (HTTP {e.code}): {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"DashScope call failed: {e}") from e


def dashscope_model() -> str:
    """Return the resolved Qwen model name for receipts."""
    return os.environ.get("HERMES_RUBRIC_QWEN_MODEL", _DASHSCOPE_DEFAULT_MODEL)


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
