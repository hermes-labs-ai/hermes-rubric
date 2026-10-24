# Contributing

Bugs and feature requests: https://github.com/hermes-labs-ai/hermes-rubric/issues

## Before submitting a PR

1. Set up a Python 3.12 virtual environment: `python3.12 -m venv .venv && . .venv/bin/activate`.
2. Install the test and packaging dependencies: `python3 -m pip install -e ".[dev,inspect,openai-agents]" pytest-mock build twine`.
3. Run `bash scripts/local-ci.sh` for dependency resolution, required SDK imports, Ruff, and the full suite with provider keys unset. Missing tools or integration extras are failures. This is the same native test contract used by the CI Python matrix.
4. Run `hermes-gate fast`, `hermes-gate full`, and `hermes-gate review` before submitting. Full includes the native test contract and checks fresh wheel/source distributions in isolated environments; see [.hermes/README.md](.hermes/README.md).
5. Both adversarial tests in `test_adversarial.py` must pass, and no API key can be required for the suite.
6. Any new dimension in the rubric synthesizer must cite a failure mode from `calibration/failure-mode-taxonomy.md`.

## Adding calibration cases

Add to `calibration/dataset.jsonl`. Each case needs:
- `human_score` — your honest assessment, not a rounded number
- `notes` — why that score; what evidence drove it
- `human_score_provisional: true` if you're uncertain

## Adding failure modes

Update `calibration/failure-mode-taxonomy.md`. New failure mode format:
- ID (FM-NN)
- Name
- Description
- Tell (the observable signal)
- Example artifact (file path or incident name)
- Motivated dimension (which META-RUBRIC dimension this informs)

Then update `calibration/META-RUBRIC.md` if the failure mode motivates a new dimension or changes an existing one.
