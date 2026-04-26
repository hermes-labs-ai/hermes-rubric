"""Backend auto-detection and invocation. Priority: claude-cli > ollama-local.

Pluggability: backends are registered into a module-level registry. Built-ins
(claude-cli, ollama-local, dashscope-qwen, google-gemini, openai, openai-sdk,
google-genai) register at import. Third-party packages can register additional
backends via either an explicit `register()` call or a Python entry-point in
the `hermes_rubric.backends` group:

    [project.entry-points."hermes_rubric.backends"]
    azure-openai = "hermes_rubric_azure:AzureBackend"

Auto-detection is unchanged: only built-ins participate in `detect()` priority,
which preserves INTENT.md's invariant that backend selection cannot be
overridden via env vars or third-party plugins.

Context-compensation: when the claude-cli backend is available and
ANTHROPIC_API_KEY is set, we invoke it in `--bare` mode to strip hooks, LSP,
plugin sync, auto-memory, CLAUDE.md discovery, and keychain reads, preventing
the scoring subprocess from inheriting session context that would bias its
judgment. If ANTHROPIC_API_KEY is not set, --bare cannot be used; we fall
back to non-bare --print and surface that in the receipt.
"""

import json
import os
import shutil
import subprocess
import time
import urllib.request
import urllib.error
import warnings
from typing import Literal, Protocol, runtime_checkable

# BackendName: the canonical identifier for a backend in CLI args, receipts,
# and tests. Kept as a Literal of the built-in names so type-checkers in
# call sites continue to validate. Third-party backends loaded via entry-points
# are addressed by string only.
BackendName = Literal[
    "claude-cli",
    "ollama-local",
    "dashscope-qwen",
    "google-gemini",
    "openai",
    "openai-sdk",
    "google-genai",
]
# Backwards-compat alias: pre-pluggability, the type was named `Backend`.
# External callers (and pre-existing tests) may still import this name.
Backend = BackendName

_DASHSCOPE_DEFAULT_MODEL = "qwen-plus"
_DASHSCOPE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

_GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
# Free-tier rate-limit throttle: ~15 RPM means >=4s between calls. Add slack.
_GEMINI_MIN_INTERVAL_S = 4.5
_gemini_last_call_t: list[float] = [0.0]

_OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"

_OPENAI_SDK_DEFAULT_MODEL = "gpt-4o-mini"
_GOOGLE_GENAI_DEFAULT_MODEL = "gemini-2.0-flash"

_OLLAMA_DEFAULT_MODEL = "qwen3.5:14b"
# Prefer non-reasoning models for structured JSON output. qwen3.5 reasoning
# models emit into `thinking` and often wrap the requested JSON in prose.
_OLLAMA_FALLBACK_MODELS = ["gemma3:12b", "gemma3:4b", "mistral:7b", "qwen3.5:9b", "qwen3.5:4b"]


# ---------------------------------------------------------------------------
# Protocol + registry
# ---------------------------------------------------------------------------


@runtime_checkable
class BackendProtocol(Protocol):
    """The plug-point. A backend must expose a stable name, a call() method
    that maps (prompt, max_tokens) -> str, a model_id() for receipts, and
    an availability() probe used by detect()-style priority lookups."""

    name: str

    def call(self, prompt: str, max_tokens: int) -> str: ...

    def model_id(self) -> str: ...

    def availability(self) -> bool: ...


_REGISTRY: dict[str, BackendProtocol] = {}
_ENTRY_POINTS_LOADED = False


def register(backend: BackendProtocol, *, replace: bool = False) -> None:
    """Register a backend instance.

    Validates Protocol shape (must have callable `call`, `model_id`,
    `availability`, and a `name` attribute). Raises TypeError on shape
    violations. Raises ValueError on duplicate name unless replace=True.
    """
    name = getattr(backend, "name", None)
    if not isinstance(name, str) or not name:
        raise TypeError(f"backend {backend!r} missing string `name` attribute")
    for method in ("call", "model_id", "availability"):
        fn = getattr(backend, method, None)
        if fn is None or not callable(fn):
            raise TypeError(f"backend {name!r} missing callable `{method}`")
    if name in _REGISTRY and not replace:
        raise ValueError(f"backend {name!r} already registered (use replace=True to override)")
    _REGISTRY[name] = backend


def _load_entry_points() -> None:
    """Scan the `hermes_rubric.backends` entry-point group once.

    Failures during plugin load become warnings, never crashes — a broken
    third-party plugin must not break the host CLI.
    """
    global _ENTRY_POINTS_LOADED
    if _ENTRY_POINTS_LOADED:
        return
    _ENTRY_POINTS_LOADED = True
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        return
    try:
        eps = entry_points(group="hermes_rubric.backends")
    except TypeError:
        # Python <3.10 compat fallback (we require 3.10+ anyway)
        eps = entry_points().get("hermes_rubric.backends", [])  # type: ignore[attr-defined]
    for ep in eps:
        try:
            obj = ep.load()
            # Accept either an already-constructed Backend instance or a
            # zero-arg class/factory. Heuristic: if `obj` is a `type`, call
            # it; otherwise assume it's an instance.
            instance = obj() if isinstance(obj, type) else obj
            register(instance, replace=False)
        except Exception as exc:
            warnings.warn(
                f"hermes-rubric: failed to load backend entry-point {ep.name!r}: {exc}"
            )


def list_backends() -> list[str]:
    """Return registered backend names (built-ins + entry-points)."""
    _load_entry_points()
    return sorted(_REGISTRY.keys())


def get_backend(name: str) -> BackendProtocol:
    """Look up a backend by name. Raises KeyError if not registered."""
    _load_entry_points()
    if name not in _REGISTRY:
        raise KeyError(f"backend {name!r} not registered; available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


# ---------------------------------------------------------------------------
# Detect (priority order, built-ins only)
# ---------------------------------------------------------------------------


def detect() -> BackendName:
    """Return the first available built-in backend.

    Only auto-detects claude-cli and ollama-local; this preserves the
    INTENT.md invariant that backend selection priority cannot be perturbed
    by env vars or third-party plugins.
    """
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


def call(prompt: str, backend: str | None = None, max_tokens: int = 2048) -> str:
    """Run a prompt against the selected backend and return the response text.

    Backwards-compat: signature unchanged. Dispatch is now via the registry
    rather than a chain of conditionals.
    """
    if backend is None:
        backend = detect()
    return get_backend(backend).call(prompt, max_tokens)


# ---------------------------------------------------------------------------
# Built-in backend implementations (private functions retained for test
# patching; adapter classes below delegate to them).
# ---------------------------------------------------------------------------


def _claude_cli_uses_bare() -> bool:
    """Return True if bare mode is available (ANTHROPIC_API_KEY set)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _call_claude_cli(prompt: str, max_tokens: int) -> str:
    """Invoke `claude --print` with context compensation when possible."""
    cmd = ["claude", "--print"]
    model = os.environ.get("HERMES_RUBRIC_CLAUDE_MODEL", "claude-haiku-4-5")
    cmd += ["--model", model]
    if _claude_cli_uses_bare():
        cmd.append("--bare")
    else:
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
    return os.environ.get("HERMES_RUBRIC_QWEN_MODEL", _DASHSCOPE_DEFAULT_MODEL)


def _call_gemini(prompt: str, max_tokens: int) -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY not set")
    model = os.environ.get("HERMES_RUBRIC_GEMINI_MODEL", _GEMINI_DEFAULT_MODEL)

    now = time.monotonic()
    elapsed = now - _gemini_last_call_t[0]
    if elapsed < _GEMINI_MIN_INTERVAL_S:
        time.sleep(_GEMINI_MIN_INTERVAL_S - elapsed)
    _gemini_last_call_t[0] = time.monotonic()

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        _GEMINI_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    last_err: Exception | None = None
    for attempt, backoff in enumerate([5, 15, 30, 60]):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:400]
            if e.code in (429, 502, 503, 504) and attempt < 3:
                last_err = e
                time.sleep(backoff)
                continue
            raise RuntimeError(f"Gemini call failed (HTTP {e.code}): {body}") from e
        except urllib.error.URLError as e:
            if attempt < 3:
                last_err = e
                time.sleep(backoff)
                continue
            raise RuntimeError(f"Gemini call failed: {e}") from e
    raise RuntimeError(f"Gemini call failed after retries: {last_err}")


def gemini_model() -> str:
    return os.environ.get("HERMES_RUBRIC_GEMINI_MODEL", _GEMINI_DEFAULT_MODEL)


def _call_openai(prompt: str, max_tokens: int) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set; cannot use openai backend")
    model = os.environ.get("HERMES_RUBRIC_OPENAI_MODEL", _OPENAI_DEFAULT_MODEL)

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "seed": 42,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        _OPENAI_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    last_err: Exception | None = None
    for attempt, backoff in enumerate([5, 15, 30, 60]):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:400]
            if e.code in (429, 502, 503, 504) and attempt < 3:
                last_err = e
                time.sleep(backoff)
                continue
            raise RuntimeError(f"OpenAI call failed (HTTP {e.code}): {body}") from e
        except urllib.error.URLError as e:
            if attempt < 3:
                last_err = e
                time.sleep(backoff)
                continue
            raise RuntimeError(f"OpenAI call failed: {e}") from e
    raise RuntimeError(f"OpenAI call failed after retries: {last_err}")


def openai_model() -> str:
    return os.environ.get("HERMES_RUBRIC_OPENAI_MODEL", _OPENAI_DEFAULT_MODEL)


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
            out = data.get("response", "") or data.get("thinking", "")
            return out.strip()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama call failed: {e}") from e


# ---------------------------------------------------------------------------
# SDK-based backends (lazy import — `import hermes_rubric.backends` must NOT
# transitively import openai or google.generativeai).
# ---------------------------------------------------------------------------


def openai_sdk_model() -> str:
    return os.environ.get("HERMES_RUBRIC_OPENAI_SDK_MODEL", _OPENAI_SDK_DEFAULT_MODEL)


def _call_openai_sdk(prompt: str, max_tokens: int) -> str:
    """Invoke OpenAI via the official `openai` Python SDK.

    Lazy-imports the SDK so `import hermes_rubric.backends` does not pull
    in `openai`. Raises an informative RuntimeError if the SDK is missing.
    """
    try:
        import openai  # noqa: F401
        from openai import OpenAI
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "openai SDK not installed; run `pip install hermes-rubric[openai]` "
            "or `pip install openai`."
        ) from e

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set; cannot use openai-sdk backend")
    model = openai_sdk_model()
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        seed=42,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def google_genai_model() -> str:
    return os.environ.get("HERMES_RUBRIC_GOOGLE_GENAI_MODEL", _GOOGLE_GENAI_DEFAULT_MODEL)


def _call_google_genai(prompt: str, max_tokens: int) -> str:
    """Invoke Google Gemini via the `google-generativeai` SDK.

    Lazy-imported. Distinct from the existing `google-gemini` backend
    (which uses the OpenAI-compatible HTTP endpoint) — this one exercises
    the SDK code path so users with `pip install google-generativeai`
    can plug in directly.
    """
    try:
        import google.generativeai as genai  # type: ignore[import-not-found]
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "google-generativeai SDK not installed; run "
            "`pip install hermes-rubric[google]` or "
            "`pip install google-generativeai`."
        ) from e

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY not set")
    genai.configure(api_key=api_key)
    model_name = google_genai_model()
    model = genai.GenerativeModel(model_name)
    resp = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0,
            "max_output_tokens": max_tokens,
        },
    )
    text = getattr(resp, "text", None)
    if text is None:
        # Fallback for response shapes without `.text` accessor.
        candidates = getattr(resp, "candidates", []) or []
        if candidates:
            parts = getattr(candidates[0].content, "parts", []) or []
            text = "".join(getattr(p, "text", "") for p in parts)
    return (text or "").strip()


# ---------------------------------------------------------------------------
# Adapter classes — thin wrappers that delegate to the private functions
# above. Kept thin so the existing test surface (which patches `_call_X`)
# continues to work unchanged.
# ---------------------------------------------------------------------------


class _ClaudeCLIBackend:
    name = "claude-cli"

    def call(self, prompt: str, max_tokens: int) -> str:
        return _call_claude_cli(prompt, max_tokens)

    def model_id(self) -> str:
        return os.environ.get("HERMES_RUBRIC_CLAUDE_MODEL", "claude-haiku-4-5")

    def availability(self) -> bool:
        if not shutil.which("claude"):
            return False
        try:
            r = subprocess.run(
                ["claude", "--print", "ping"],
                capture_output=True, text=True, timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False


class _OllamaBackend:
    name = "ollama-local"

    def call(self, prompt: str, max_tokens: int) -> str:
        return _call_ollama(prompt, max_tokens)

    def model_id(self) -> str:
        return _ollama_model()

    def availability(self) -> bool:
        if not shutil.which("ollama"):
            return False
        try:
            r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
            return r.status == 200
        except Exception:
            return False


class _DashScopeBackend:
    name = "dashscope-qwen"

    def call(self, prompt: str, max_tokens: int) -> str:
        return _call_dashscope(prompt, max_tokens)

    def model_id(self) -> str:
        return dashscope_model()

    def availability(self) -> bool:
        return bool(os.environ.get("DASHSCOPE_API_KEY"))


class _GeminiHTTPBackend:
    name = "google-gemini"

    def call(self, prompt: str, max_tokens: int) -> str:
        return _call_gemini(prompt, max_tokens)

    def model_id(self) -> str:
        return gemini_model()

    def availability(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


class _OpenAIHTTPBackend:
    name = "openai"

    def call(self, prompt: str, max_tokens: int) -> str:
        return _call_openai(prompt, max_tokens)

    def model_id(self) -> str:
        return openai_model()

    def availability(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))


class _OpenAISDKBackend:
    name = "openai-sdk"

    def call(self, prompt: str, max_tokens: int) -> str:
        return _call_openai_sdk(prompt, max_tokens)

    def model_id(self) -> str:
        return openai_sdk_model()

    def availability(self) -> bool:
        if not os.environ.get("OPENAI_API_KEY"):
            return False
        try:
            import openai  # noqa: F401
            return True
        except ModuleNotFoundError:
            return False


class _GoogleGenAIBackend:
    name = "google-genai"

    def call(self, prompt: str, max_tokens: int) -> str:
        return _call_google_genai(prompt, max_tokens)

    def model_id(self) -> str:
        return google_genai_model()

    def availability(self) -> bool:
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            return False
        try:
            import google.generativeai  # noqa: F401
            return True
        except ModuleNotFoundError:
            return False


# Register built-ins at import. Order is presentation-only; detect() has its
# own priority logic and does not consult registration order.
for _b in (
    _ClaudeCLIBackend(),
    _OllamaBackend(),
    _DashScopeBackend(),
    _GeminiHTTPBackend(),
    _OpenAIHTTPBackend(),
    _OpenAISDKBackend(),
    _GoogleGenAIBackend(),
):
    register(_b)
del _b
