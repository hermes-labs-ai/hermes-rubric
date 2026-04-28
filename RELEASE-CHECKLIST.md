# Release Checklist — hermes-rubric v1.0.0

Run in order. Each step is a prerequisite for the next. The repo has been public since 2026-04-24 as a 0.9-era preview; v1.0.0 is the first tagged release on PyPI + GitHub Releases, headlined by class-aware rubric templates.

## 1. Verify tests pass

```bash
cd ~/Documents/projects/hermes-rubric
python3 -m pytest tests/ -q
# Expected: 111 passed, 4 skipped (109 prior + 9 new in test_classes.py minus 7 already-skipped)
```

## 2. Verify adversarial tests specifically

```bash
python3 -m pytest tests/test_adversarial.py -v
# Both tests must pass. If not, do NOT ship.
```

## 3. Verify class templates load deterministically

```bash
python3 -c "
from hermes_rubric.classes import load_class, to_rubric
for c in ['social-post','show-hn-post','linkedin-post','outreach-email']:
    r1 = to_rubric(load_class(c))
    r2 = to_rubric(load_class(c))
    assert r1 == r2, f'{c} non-deterministic'
print('all 4 classes load deterministically')
"
```

## 4. Verify hermes-seal still valid (already granted at v0.1)

```bash
hermes-seal verify ~/Documents/projects/hermes-rubric
```

## 5. Build wheel + tarball

```bash
cd ~/Documents/projects/hermes-rubric
python -m build
ls dist/
# Should show: hermes_rubric-1.0.0-py3-none-any.whl and hermes_rubric-1.0.0.tar.gz
# Verify class YAMLs are packed:
unzip -l dist/hermes_rubric-1.0.0-py3-none-any.whl | grep yaml
# Expected: 4 YAML files
```

## 6. Push commits + tag

```bash
cd ~/Documents/projects/hermes-rubric
git push origin main
git tag -a v1.0.0 -m "v1.0.0 — class-aware rubric templates"
git push origin v1.0.0
```

## 7. Create GitHub Release

```bash
gh release create v1.0.0 \
  --title "v1.0.0 — class-aware rubric templates" \
  --notes-file /tmp/RELEASE-NOTES-v1.0.0.md \
  dist/hermes_rubric-1.0.0-py3-none-any.whl \
  dist/hermes_rubric-1.0.0.tar.gz
```

## 8. Upload to PyPI

```bash
python -m twine upload dist/hermes_rubric-1.0.0*
# Uses ~/.pypirc credentials
```

## 9. Verify installation propagates

```bash
# Wait ~2 min for PyPI to propagate
pip index versions hermes-rubric
# Should show 1.0.0
pip install --upgrade hermes-rubric
hermes-rubric --help | grep artifact-class
# Confirms new flag is in published package
```

## 10. Smoke test the new flag end-to-end

```bash
echo "shipped: hermes-rubric. evidence-first scoring." > /tmp/test-post.md
hermes-rubric --artifact-class social-post --target /tmp/test-post.md --backend ollama-local --batch --out /tmp/test-rubric-out.json
python3 -c "import json; d=json.load(open('/tmp/test-rubric-out.json')); print('source:', d['receipt']['pipeline'].get('stage_1_rubric_source')); print('hash:', d['receipt']['pipeline']['stage_1_rubric_hash_sha256'][:16]); print('aggregate:', d['aggregate'])"
# rubric_source should be "class-template" and hash should be deterministic across runs
```

## 11. Show HN

Submit at https://news.ycombinator.com/submit
- Title: `Show HN: hermes-rubric — LLM scoring with evidence citations, not fluency vibes`
- URL: https://github.com/hermes-labs-ai/hermes-rubric
- Text body: `/tmp/hermes-rubric-show-hn-draft-v2.md`

## 12. Update memory

```bash
# Update ~/.claude/projects/-Users-rbr-lpci/memory/project_hermes_rubric.md:
#   v1.0.0 SHIPPED 2026-04-28 with class-aware rubric templates
#   PyPI published, GitHub Release published
```

---

## Pre-ship sanity checks

- [ ] 111 tests pass (including 2 adversarial + 9 new class-aware)
- [ ] No API key required for tests
- [ ] README.md has install + class-aware usage + output schema
- [ ] CHANGELOG.md has 1.0.0 entry above 0.1.x
- [ ] RELEASE-NOTES-v1.0.0.md exists at /tmp/ (or `release-notes/`)
- [ ] hermes-seal verify passes
- [ ] No fabricated numbers in release notes (every figure traceable to test count, dim count, or experiment record)
- [ ] All 4 class YAMLs packaged in wheel
- [ ] dist files match HEAD commit (no stale build)

## Self-rubric on this release

Inline plan-criteria-rubric on RELEASE-NOTES-v1.0.0.md scored 8.4/10 (above 7.0 threshold, no dim < 4, no hard-fail anti-patterns).

A separate `hermes-rubric --scope-class results-bundle --backend ollama-local --batch` run on the release notes is captured at `/tmp/release-notes-rubric.json` for receipt provenance.
