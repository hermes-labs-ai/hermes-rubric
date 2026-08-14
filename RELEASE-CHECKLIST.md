# Release checklist — v1.1.0

Run from a clean release worktree at the exact candidate commit.

## Local gates

```bash
git diff --check
UV_CACHE_DIR=/tmp/hermes-rubric-uv-cache uv run --extra dev pytest -q
UV_CACHE_DIR=/tmp/hermes-rubric-uv-cache uv run --extra dev pytest -q tests/test_adversarial.py
UV_CACHE_DIR=/tmp/hermes-rubric-uv-cache uv run --extra dev ruff check \
  src/hermes_rubric/assessment.py src/hermes_rubric/errors.py \
  src/hermes_rubric/feedback.py src/hermes_rubric/inputs.py \
  src/hermes_rubric/models.py examples/portable_agent_assessment.py
UV_CACHE_DIR=/tmp/hermes-rubric-uv-cache uv build
```

The repository has known historical full-tree Ruff debt. New or modified v1.1 files must be clean; baseline debt must not be misreported as introduced by this release.

## Clean-wheel smoke

```bash
python -m venv /tmp/hermes-rubric-v110-smoke
/tmp/hermes-rubric-v110-smoke/bin/pip install dist/hermes_rubric-1.1.0-py3-none-any.whl
/tmp/hermes-rubric-v110-smoke/bin/python -c "from hermes_rubric import assess, assess_async, assess_path, assess_path_async, AssessmentResult, AssessmentError; print('imports-ok')"
/tmp/hermes-rubric-v110-smoke/bin/hermes-rubric --version
/tmp/hermes-rubric-v110-smoke/bin/hermes-rubric --help >/dev/null
```

Inspect the archives for the new modules and bundled class YAML files.

## Review

Perform one review against:

- backwards-compatible CLI behavior and legacy JSON keys;
- evidence, hedge, and source-authority invariants;
- truthful coverage and feedback semantics;
- public errors and exception chaining;
- version/docs/code consistency;
- absence of unsupported product or comparison claims.

After material fixes, run one re-review only.

## Publish

1. Merge the reviewed PR into `main`.
2. Build artifacts again from the exact merged commit if the merge changes the commit object.
3. Create annotated tag `v1.1.0` and push it.
4. Create the GitHub Release using `RELEASE-NOTES-v1.1.0.md` and attach wheel/sdist.
5. Let the repository's established trusted-publishing workflow publish PyPI, or use the established manual path only if that workflow is unavailable and current authorization covers it.

## Public verification

- Inspect the public tag and GitHub Release assets.
- Verify PyPI reports `1.1.0`.
- Install `hermes-rubric==1.1.0` in a fresh environment.
- Re-run imports and `hermes-rubric --version` from the public package.
