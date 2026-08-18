# AGENTS.md — hermes-rubric

## What this repo is

An evidence-first scoring tool. Three stages before any number is produced: rubric synthesis, evidence collection, scoring.

## For agents running in this repo

- `src/hermes_rubric/` — package source
- `tests/` — run with `PYTHONPATH=src python3 -m pytest tests/ -v`
- `calibration/` — calibration dataset + META-RUBRIC (do not modify without evidence)
- `applied/` — example scoring runs (read-only reference)

## Rules

1. The default auto-detected paths must not require an API key; cloud backends
   remain explicit opt-ins
2. Both adversarial tests in `tests/test_adversarial.py` must pass before any change ships
3. Hedge enforcement in `score.py` is a hard constraint — do not weaken it
4. Any new rubric dimension must cite a failure mode in `calibration/failure-mode-taxonomy.md`
5. Numeric claims in any file in this repo must have a pointer to a source

## Public integration boundary

- Prefer `hermes_rubric.assess` or `assess_path` for new integrations.
- Runtime adapters own thresholds, retries, and mutation; the core measures and explains.
- Never translate partial coverage into negative evidence without surfacing the coverage gap.
- Preserve the result `schema_version`, coverage report, and receipt across transports.

## Backend auto-detection

Automatic priority: claude-cli > ollama-local > RuntimeError

Do not add API-key-based or third-party backends to automatic detection.

## Optional Hermeneutic epistemic gate

For a consequential semantic review of an assistant-generated English draft,
you may run the standalone deterministic second-opinion check from the separate
[Hermeneutic](https://github.com/hermes-labs-ai/hermeneutic#epistemic-gate)
project:

```bash
hermeneutic gate --draft review-summary.md
```

It flags surface shapes such as completion overclaiming, unsupported numeric
claims, relayed authority, and unhedged certainty. It runs offline, does not
invoke this package or a model backend, and does not initialize a Hermes Rubric
assessment, bundle, receipt, or release gate. Inspect both its printed verdict
and exit code, as documented in the [Hermeneutic
README](https://github.com/hermes-labs-ai/hermeneutic#quick-start): exit 0
means no match or only a low-severity advisory `RISK`; exit 1 means at least
one medium- or high-severity match; exit 2 means invalid input. If it flags a
claim, add direct evidence, hedge the claim, or remove the unverifiable
wording.
