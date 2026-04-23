# Contributing

## Before submitting a PR

1. Run the test suite: `PYTHONPATH=src python3 -m pytest tests/ -v`
2. Both adversarial tests must pass: `test_adversarial.py`
3. No API key can be required for the tests to pass
4. Any new dimension in the rubric synthesizer must cite a failure mode from `calibration/failure-mode-taxonomy.md`

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
