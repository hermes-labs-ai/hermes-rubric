# Hermes Rubric v1.2.1 — Inspect AI scorer

Version 1.2.1 adds a native, optional scorer integration for
[Inspect AI](https://inspect.aisi.org.uk/).

## What is new

- Install with `pip install "hermes-rubric[inspect]"`.
- Use the registered scorer as
  `hermes_rubric/hermes_rubric_scorer` in an Inspect task or with
  `inspect score` on an existing eval log.
- Preserve the complete Hermes assessment—including citations, coverage facts,
  and receipt—under `Score.metadata["hermes_rubric"]`.
- Keep the Hermes 0–10 aggregate as the numeric Inspect score.
- Fail scoring by default when assessment fails, with an explicit
  `fail_on_error=False` option for a visible unscored sample.

## Product boundary

Inspect owns task execution, eval logs, aggregation, and re-scoring. Hermes
Rubric remains a stateless evidence-first assessment transaction. The adapter
does not add a pass threshold, retry the evaluated agent, or turn a score into
authorization.

## Upgrade

```bash
pip install --upgrade "hermes-rubric[inspect]"
```

See the [adapter documentation](docs/ADAPTERS.md) for CLI and Python examples.
