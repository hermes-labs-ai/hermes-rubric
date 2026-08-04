# Install

## Requirements

- Python 3.10+
- One of: Claude Code installed (`claude` CLI) OR Ollama running locally with a capable model pulled

## Install from PyPI

```bash
pip install hermes-rubric
```

## Verify the install

```bash
hermes-rubric --version
# hermes-rubric 1.0.2
```

## Backends

hermes-rubric auto-detects a backend in priority order:

| Priority | Backend | Requirement |
|---|---|---|
| 1 | `claude-cli` | `claude` CLI installed + authenticated |
| 2 | `ollama-local` | Ollama running at `localhost:11434` with a model pulled |

Force a specific backend:

```bash
hermes-rubric --backend ollama-local ...
```

Recommended Ollama model: `qwen3.5:9b` or larger. Smaller models (0.8b/2b) produce less reliable evidence extraction.

## Install from source

```bash
git clone https://github.com/hermes-labs-ai/hermes-rubric
cd hermes-rubric
pip install -e ".[dev]"
pytest
```

## Upgrade

```bash
pip install --upgrade hermes-rubric
```

## What gets installed

The `hermes-rubric` CLI command and the `hermes_rubric` Python library. The default Claude Code and Ollama paths require no API key; optional cloud backends use their provider credentials. Hermes Rubric sends no telemetry of its own.
