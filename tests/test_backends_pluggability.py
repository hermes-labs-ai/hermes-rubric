"""Pluggability tests for the Backend Protocol + registry.

Covers Protocol enforcement, registry round-trip, lazy SDK imports,
mocked SDK call paths, backwards-compat, and entry-point discovery.
"""

import importlib
import sys
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_backends():
    """Reload backends module so registry state starts clean for the test."""
    if "hermes_rubric.backends" in sys.modules:
        del sys.modules["hermes_rubric.backends"]
    return importlib.import_module("hermes_rubric.backends")


# ---------------------------------------------------------------------------
# Protocol + registry
# ---------------------------------------------------------------------------


def test_register_rejects_class_missing_call():
    """A backend without callable `call` is rejected at register time."""
    from hermes_rubric import backends

    class Broken:
        name = "broken"
        def model_id(self): return "x"
        def availability(self): return True
        # no `call`

    with pytest.raises(TypeError, match="missing callable `call`"):
        backends.register(Broken())


def test_register_rejects_missing_name():
    from hermes_rubric import backends

    class Nameless:
        def call(self, p, m): return ""
        def model_id(self): return "x"
        def availability(self): return False

    with pytest.raises(TypeError, match="missing string `name`"):
        backends.register(Nameless())


def test_register_rejects_duplicate_unless_replace():
    from hermes_rubric import backends

    class Dummy:
        name = "dup-test-backend"
        def call(self, p, m): return "ok"
        def model_id(self): return "dummy"
        def availability(self): return True

    backends.register(Dummy())
    with pytest.raises(ValueError, match="already registered"):
        backends.register(Dummy())
    # replace=True allows override
    backends.register(Dummy(), replace=True)


def test_registry_round_trip_and_call():
    """register() -> get_backend() -> call() round-trip works."""
    from hermes_rubric import backends

    class Echo:
        name = "echo-test"
        def call(self, prompt, max_tokens): return f"echo:{prompt}"
        def model_id(self): return "echo-1"
        def availability(self): return True

    backends.register(Echo(), replace=True)
    assert "echo-test" in backends.list_backends()
    assert backends.get_backend("echo-test").model_id() == "echo-1"
    assert backends.call("hello", backend="echo-test") == "echo:hello"


def test_list_backends_includes_builtins():
    from hermes_rubric import backends

    names = backends.list_backends()
    for required in (
        "claude-cli", "ollama-local", "dashscope-qwen",
        "google-gemini", "openai", "openai-sdk", "google-genai",
    ):
        assert required in names


def test_get_backend_unknown_raises():
    from hermes_rubric import backends
    with pytest.raises(KeyError, match="not registered"):
        backends.get_backend("does-not-exist-xyz")


# ---------------------------------------------------------------------------
# Lazy SDK imports — critical invariant
# ---------------------------------------------------------------------------


def test_importing_backends_does_not_import_openai_sdk():
    """`import hermes_rubric.backends` must not transitively import openai."""
    # Drop any prior import so we test the cold-import case.
    for mod in list(sys.modules):
        if mod == "openai" or mod.startswith("openai."):
            del sys.modules[mod]
    if "hermes_rubric.backends" in sys.modules:
        del sys.modules["hermes_rubric.backends"]
    importlib.import_module("hermes_rubric.backends")
    assert "openai" not in sys.modules, "backends import leaked openai SDK"


def test_importing_backends_does_not_import_google_genai():
    for mod in list(sys.modules):
        if mod == "google.generativeai" or mod.startswith("google.generativeai."):
            del sys.modules[mod]
    if "hermes_rubric.backends" in sys.modules:
        del sys.modules["hermes_rubric.backends"]
    importlib.import_module("hermes_rubric.backends")
    assert "google.generativeai" not in sys.modules, (
        "backends import leaked google.generativeai SDK"
    )


def test_importing_top_level_package_does_not_import_sdks():
    """`import hermes_rubric` must also not transitively import either SDK."""
    for mod in list(sys.modules):
        if mod in ("openai", "google.generativeai") or \
           mod.startswith("openai.") or mod.startswith("google.generativeai."):
            del sys.modules[mod]
    for mod in list(sys.modules):
        if mod == "hermes_rubric" or mod.startswith("hermes_rubric."):
            del sys.modules[mod]
    importlib.import_module("hermes_rubric")
    assert "openai" not in sys.modules
    assert "google.generativeai" not in sys.modules


# ---------------------------------------------------------------------------
# Mocked SDK call paths
# ---------------------------------------------------------------------------


def test_openai_sdk_backend_invokes_sdk(monkeypatch):
    """openai-sdk backend uses openai.OpenAI client with temperature=0 and seed."""
    from hermes_rubric import backends

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    captured = {}

    class FakeMessage:
        content = "sdk-response"

    class FakeChoice:
        message = FakeMessage()

    class FakeResp:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResp()

    class FakeChat:
        def __init__(self): self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self, api_key=None):
            captured["api_key"] = api_key
            self.chat = FakeChat()

    fake_openai = MagicMock()
    fake_openai.OpenAI = FakeClient
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    out = backends.call("hi sdk", backend="openai-sdk")
    assert out == "sdk-response"
    assert captured["temperature"] == 0
    assert captured["seed"] == 42
    assert captured["model"] == backends.openai_sdk_model()
    assert captured["api_key"] == "test-key"
    assert captured["messages"][0]["content"] == "hi sdk"


def test_openai_sdk_backend_missing_sdk(monkeypatch):
    """When the openai SDK is not installed, raise an informative RuntimeError."""
    from hermes_rubric import backends

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    # Block the import: ensure `import openai` fails inside the call path.
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(RuntimeError, match="openai SDK not installed"):
        backends.call("hi", backend="openai-sdk")


def test_openai_sdk_backend_missing_key(monkeypatch):
    from hermes_rubric import backends

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Stub openai so we get past the import guard and into the key check.
    fake_openai = MagicMock()
    fake_openai.OpenAI = MagicMock()
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
        backends.call("hi", backend="openai-sdk")


def test_google_genai_backend_invokes_sdk(monkeypatch):
    """google-genai backend uses GenerativeModel.generate_content."""
    from hermes_rubric import backends

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured = {}

    class FakeResp:
        text = "gemini-sdk-response"

    class FakeModel:
        def __init__(self, name): captured["model_name"] = name
        def generate_content(self, prompt, generation_config=None):
            captured["prompt"] = prompt
            captured["generation_config"] = generation_config
            return FakeResp()

    fake_genai = MagicMock()
    def _configure(api_key=None): captured["api_key"] = api_key
    fake_genai.configure = _configure
    fake_genai.GenerativeModel = FakeModel
    fake_google = MagicMock()
    fake_google.generativeai = fake_genai
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake_genai)

    out = backends.call("hi gemini", backend="google-genai")
    assert out == "gemini-sdk-response"
    assert captured["api_key"] == "test-key"
    assert captured["prompt"] == "hi gemini"
    assert captured["generation_config"]["temperature"] == 0
    assert captured["model_name"] == backends.google_genai_model()


def test_google_genai_backend_missing_sdk(monkeypatch):
    from hermes_rubric import backends
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "google.generativeai", None)
    with pytest.raises(RuntimeError, match="google-generativeai SDK not installed"):
        backends.call("hi", backend="google-genai")


# ---------------------------------------------------------------------------
# Backwards-compat sentinel
# ---------------------------------------------------------------------------


def test_backwards_compat_claude_cli_call_routes_through_underscore_helper():
    """`call(..., backend="claude-cli")` still delegates to `_call_claude_cli`."""
    from hermes_rubric import backends

    with patch.object(backends, "_call_claude_cli", return_value="legacy-ok") as mock_claude:
        result = backends.call("test prompt", backend="claude-cli")
    mock_claude.assert_called_once_with("test prompt", 2048)
    assert result == "legacy-ok"


def test_backwards_compat_call_signature_unchanged():
    """`call(prompt, backend, max_tokens)` keyword/positional invocations still work."""
    from hermes_rubric import backends
    with patch.object(backends, "_call_ollama", return_value="positional"):
        # Positional max_tokens still accepted (3rd positional arg).
        out = backends.call("p", "ollama-local", 1024)
    assert out == "positional"


def test_backwards_compat_backend_alias_still_exported():
    """The pre-pluggability `Backend` Literal alias is still importable."""
    from hermes_rubric import backends
    # Both names should exist; Backend is an alias of BackendName.
    assert hasattr(backends, "Backend")
    assert hasattr(backends, "BackendName")


# ---------------------------------------------------------------------------
# Entry-point discovery
# ---------------------------------------------------------------------------


def test_entry_point_discovery_registers_third_party_backend(monkeypatch):
    """A fake entry-point becomes a callable backend after lazy load."""
    backends = _fresh_backends()

    class FakePluginBackend:
        name = "fake-plugin"
        def call(self, prompt, max_tokens): return f"plugin:{prompt}"
        def model_id(self): return "fake-1"
        def availability(self): return True

    class FakeEP:
        name = "fake-plugin"
        def load(self): return FakePluginBackend  # class; registry will instantiate

    def fake_entry_points(*, group=None):
        if group == "hermes_rubric.backends":
            return [FakeEP()]
        return []

    monkeypatch.setattr("importlib.metadata.entry_points", fake_entry_points)
    # Force a fresh entry-point scan.
    backends._ENTRY_POINTS_LOADED = False

    assert "fake-plugin" in backends.list_backends()
    assert backends.call("hi", backend="fake-plugin") == "plugin:hi"


def test_entry_point_load_failure_warns_not_crashes(monkeypatch):
    """A broken third-party plugin must surface as a warning, not a crash."""
    backends = _fresh_backends()

    class BrokenEP:
        name = "broken-plugin"
        def load(self): raise ImportError("simulated broken plugin")

    def fake_entry_points(*, group=None):
        if group == "hermes_rubric.backends":
            return [BrokenEP()]
        return []

    monkeypatch.setattr("importlib.metadata.entry_points", fake_entry_points)
    backends._ENTRY_POINTS_LOADED = False

    with pytest.warns(UserWarning, match="failed to load backend entry-point"):
        names = backends.list_backends()

    # Built-ins still registered; broken plugin not present.
    assert "claude-cli" in names
    assert "broken-plugin" not in names


# ---------------------------------------------------------------------------
# Live SkipIf tests (only run when SDK installed AND opt-in env set)
# ---------------------------------------------------------------------------


def _has_openai_sdk() -> bool:
    try:
        import openai  # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


def _has_google_genai() -> bool:
    try:
        import google.generativeai  # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


@pytest.mark.skipif(
    not _has_openai_sdk() or not __import__("os").environ.get("HERMES_RUBRIC_OPENAI_LIVE"),
    reason="openai SDK + HERMES_RUBRIC_OPENAI_LIVE=1 required",
)
def test_openai_sdk_live():  # pragma: no cover
    from hermes_rubric import backends
    out = backends.call("ping", backend="openai-sdk", max_tokens=8)
    assert isinstance(out, str) and out


@pytest.mark.skipif(
    not _has_google_genai() or not __import__("os").environ.get("HERMES_RUBRIC_GEMINI_LIVE"),
    reason="google-generativeai SDK + HERMES_RUBRIC_GEMINI_LIVE=1 required",
)
def test_google_genai_live():  # pragma: no cover
    from hermes_rubric import backends
    out = backends.call("ping", backend="google-genai", max_tokens=8)
    assert isinstance(out, str) and out
