# Release Checklist — hermes-rubric v0.1.0

Run in order. Each step is a prerequisite for the next.

## 1. Verify tests pass

```bash
cd ~/Documents/projects/hermes-rubric
PYTHONPATH=src python3 -m pytest tests/ -v
# Expected: 14 passed
```

## 2. Verify adversarial tests specifically

```bash
PYTHONPATH=src python3 -m pytest tests/test_adversarial.py -v
# Both tests must pass. If not, do NOT ship.
```

## 3. Grant hermes-seal

```bash
sudo ~/Documents/projects/hermes-seal/.venv/bin/hermes-seal grant ~/Documents/projects/hermes-rubric
```

## 4. Create GitHub repo

```bash
cd ~/Documents/projects/hermes-rubric
gh repo create hermes-labs-ai/hermes-rubric --public --source=. --push
```

## 5. Build wheel

```bash
pip install build twine
python -m build
ls dist/
# Should show: hermes_rubric-0.1.0-py3-none-any.whl and hermes_rubric-0.1.0.tar.gz
```

## 6. Dry-run PyPI upload

```bash
python -m twine upload --repository testpypi dist/hermes_rubric-0.1.0*
# Verify at test.pypi.org
```

## 7. Upload to PyPI

```bash
python -m twine upload dist/hermes_rubric-0.1.0*
```

## 8. Verify installation

```bash
pip install hermes-rubric
hermes-rubric --help
```

## 9. Update memory

```bash
# Add to project_hermes_oss_branding_pass_20260422.md:
# hermes-rubric v0.1.0: PyPI published, public repo, product #22 dev-tools tier
```

## 10. Update MEMORY.md index

Add `project_hermes_rubric.md` entry.

---

## Pre-ship sanity checks

- [ ] 14 tests pass (including 2 adversarial)
- [ ] No ANTHROPIC_API_KEY or OPENAI_API_KEY required for tests
- [ ] README.md has install + usage + output schema
- [ ] CHANGELOG.md has 0.1.0 entry
- [ ] INTENT.md accepts/does-not clauses are accurate
- [ ] calibration/META-RUBRIC.md is frozen (do not edit after ship)
- [ ] applied/papers-20260423.md exists and is complete
- [ ] hermes-seal granted (sudo key required)
- [ ] No fabricated numbers in any file (verify with grep for ranges without source pointers)
