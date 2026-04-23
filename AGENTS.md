# AGENTS.md — hermes-rubric

## What this repo is

An evidence-first scoring tool. Three stages before any number is produced: rubric synthesis, evidence collection, scoring.

## For agents running in this repo

- `src/hermes_rubric/` — package source
- `tests/` — run with `PYTHONPATH=src python3 -m pytest tests/ -v`
- `calibration/` — calibration dataset + META-RUBRIC (do not modify without evidence)
- `applied/` — example scoring runs (read-only reference)

## Rules

1. No API key may be required for the tool to run
2. Both adversarial tests in `tests/test_adversarial.py` must pass before any change ships
3. Hedge enforcement in `score.py` is a hard constraint — do not weaken it
4. Any new rubric dimension must cite a failure mode in `calibration/failure-mode-taxonomy.md`
5. Numeric claims in any file in this repo must have a pointer to a source

## Backend auto-detection

Priority: claude-cli > ollama-local > RuntimeError

Do not add API-key-based backends. Do not add OpenAI or Anthropic direct SDK calls.
