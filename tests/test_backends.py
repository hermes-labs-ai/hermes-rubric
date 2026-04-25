"""Tests for backend detection and invocation."""

import pytest
from unittest.mock import patch, MagicMock


def test_detect_prefers_claude_cli():
    """claude-cli is preferred when both are available."""
    from hermes_rubric import backends

    with patch("shutil.which", side_effect=lambda x: "/usr/bin/" + x):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="pong", stderr="")
            result = backends.detect()
    assert result == "claude-cli"


def test_detect_falls_back_to_ollama():
    """Falls back to ollama when claude-cli fails."""
    from hermes_rubric import backends

    def which_side(x):
        return "/usr/bin/ollama" if x == "ollama" else None

    with patch("shutil.which", side_effect=which_side):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = backends.detect()
    assert result == "ollama-local"


def test_detect_raises_when_nothing_available():
    """RuntimeError raised when no backend is found."""
    from hermes_rubric import backends

    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="No backend available"):
            backends.detect()


def test_call_routes_to_correct_backend():
    """call() routes to claude-cli when backend is specified."""
    from hermes_rubric import backends

    with patch.object(backends, "_call_claude_cli", return_value="response text") as mock_claude:
        result = backends.call("test prompt", backend="claude-cli")
    mock_claude.assert_called_once_with("test prompt", 2048)
    assert result == "response text"


def test_call_ollama_backend():
    """call() routes to ollama when specified."""
    from hermes_rubric import backends

    with patch.object(backends, "_call_ollama", return_value="ollama response") as mock_ollama:
        result = backends.call("test prompt", backend="ollama-local")
    mock_ollama.assert_called_once_with("test prompt", 2048)
    assert result == "ollama response"


def test_call_openai_basic(monkeypatch):
    """OpenAI backend posts JSON with model+temperature+seed and returns content."""
    import json as _json
    from unittest.mock import MagicMock
    from hermes_rubric import backends

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return _json.dumps({
                "choices": [{"message": {"content": '{"ok": true}'}}]
            }).encode()

    def fake_urlopen(req, timeout=300):
        captured["url"] = req.full_url
        captured["body"] = _json.loads(req.data)
        captured["auth"] = req.get_header("Authorization")
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = backends.call("ping", backend="openai")

    assert out == '{"ok": true}'
    assert "openai.com" in captured["url"]
    assert captured["body"]["temperature"] == 0
    assert captured["body"]["seed"] == 42
    assert captured["body"]["model"] == backends.openai_model()
    assert captured["auth"].startswith("Bearer ")


def test_call_openai_missing_key(monkeypatch):
    """OpenAI backend errors clearly when OPENAI_API_KEY is unset."""
    from hermes_rubric import backends

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
        backends.call("ping", backend="openai")


def test_openai_model_default_and_override(monkeypatch):
    """openai_model() respects HERMES_RUBRIC_OPENAI_MODEL env var."""
    from hermes_rubric import backends

    monkeypatch.delenv("HERMES_RUBRIC_OPENAI_MODEL", raising=False)
    assert backends.openai_model() == "gpt-4o-mini"

    monkeypatch.setenv("HERMES_RUBRIC_OPENAI_MODEL", "gpt-4o")
    assert backends.openai_model() == "gpt-4o"
