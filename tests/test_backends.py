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
