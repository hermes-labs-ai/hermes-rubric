# Hermes Rubric v1.2.3 — quickstart recipe hardening

Version 1.2.3 is a documentation/test-only patch: it hardens the published
quickstart recipe against a failed `mktemp -d`. It carries no adapter, API,
or scoring-behavior change.

## What is new

- The quickstart recipe now stops with `|| exit 1` when `mktemp -d` fails,
  instead of continuing with an empty `$workdir`. On a full or read-only
  temp filesystem that empty value made every quoted path in the recipe
  expand to `/post.md` and `/result.json` — the exact predictable-shared-path
  failure the workdir was introduced to remove.
- `_documented_argv()` now screens the published shell tokens for leftover
  variables *before* substitution, so a `pytest --basetemp` path containing
  `$` is not misread as an undocumented variable.
- `test_quickstart_recipe_stops_when_mktemp_fails` runs the published block
  with a failing `mktemp` shim and asserts the recipe aborts before reaching
  the CLI.

## Product boundary

No change to `hermes_rubric.assess`, `assess_path`, the CLI, the Inspect AI
scorer, or the OpenAI Agents SDK adapter. The PyPI long description already
matches this repository's README as of the 1.2.2 release, including both
adapters.

## Upgrade

```bash
pip install --upgrade hermes-rubric
```
