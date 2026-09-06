# Local quality gate

Use a **Python 3.12** environment for Gate commands, matching
`.github/workflows/hermes-quality.yml`. The canonical Hermes Gate tool and its
copied runner require Python 3.11 or newer (`tomllib`); this tooling requirement
does not change the package's Python 3.10 minimum, which the existing CI matrix
continues to test.

Install the project and full gate dependencies into that environment:

```sh
python3 -m pip install -e '.[dev,inspect,openai-agents]' pytest-mock build twine
hermes-gate fast
hermes-gate full
hermes-gate review
```

Keep that environment's `bin` directory on `PATH` when running `hermes-gate`.
CI uses `python3 .hermes/hermes_gate_runner.py full` directly. The full contract
requires both integration extras, runs tests without provider API keys, and
checks fresh wheel and source distributions in isolated install environments.

Fast whitespace validation checks complete selected files, including staged,
untracked, and committed paths. Its Ruff rule set explicitly preserves the
project's existing E4/E7/E9/F contract across Ruff default-rule changes.
