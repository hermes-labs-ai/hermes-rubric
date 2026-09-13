---
name: hermes-rubric
description: Assess an agent output or application artifact with cited evidence, coverage facts, dimension scores, and caller-controlled feedback using the Hermes Rubric CLI or Python API.
---

# Hermes Rubric

Use Hermes Rubric when a user needs an evidence-first assessment of an agent output, document, repository artifact, or completed application run. Hermes Rubric measures and explains; the calling application decides what to do next.

## Install and choose an entry point

Install the package in the environment that will run the assessment:

```bash
pip install hermes-rubric
```

Use the CLI for a file or directory. `--intent` and `--context` describe the assessment unless a bundled deterministic `--artifact-class` is selected:

```bash
hermes-rubric \
  --intent "Evaluate publication readiness" \
  --context STYLE-GUIDE.md \
  --target paper.md \
  --out result.json
```

For repeated artifact types, use one of the bundled classes: `social-post`, `show-hn-post`, `linkedin-post`, `outreach-email`, or `repo-readme`.

```bash
hermes-rubric --artifact-class repo-readme --target README.md --out result.json
```

Use the Python API when the target is already in an application:

```python
from hermes_rubric import FeedbackPolicy, assess

result = assess(
    target=agent_output,
    intent="Answer accurately and support material claims with checkable evidence.",
    context=task_context,
    target_type="agent-output",
)

print(result.aggregate)
print(result.coverage.status)
print(result.feedback(FeedbackPolicy(minimum_score=7)).to_prompt())
```

Use `assess_path()` for a file or directory, and `assess_async()` when the surrounding application is asynchronous. Framework adapters are optional extras; the core package does not run an agent loop.

## Interpret the result

Inspect the returned `AssessmentResult` or JSON for:

- `schema_version`, so downstream consumers preserve the result contract.
- `evidence_citations`, `per_dim_scores`, and `receipt`, which connect scores to accepted evidence.
- `coverage.status` and `coverage.limitations`. `partial` means relevant material may not have been inspected; it is not proof that evidence is absent.
- Feedback type: `quality_gap`, `evidence_gap`, or `coverage_gap`. A coverage gap calls for wider inspection rather than an automatic rewrite.

The aggregate is a signal, not a verdict. Keep caller thresholds and runtime mutation policy outside Hermes Rubric. Do not turn an assessment into a compliance certification, factual-truth proof, or automatic release decision without an explicit caller policy.

## Backends and controlled runs

Automatic backend selection checks authenticated Claude Code first, then local Ollama. Cloud providers are explicit opt-ins. Pin a backend for controlled workflows, for example:

```bash
hermes-rubric \
  --intent "Evaluate publication readiness" \
  --context STYLE-GUIDE.md \
  --target paper.md \
  --backend claude-cli \
  --out result.json
```

For directly comparable completed runs, reuse the prior rubric with `--pin-rubric prior-result.json`. Use `hermes-rubric kappa --run1 result_a.json --run2 result_b.json` to compute Cohen's κ between two completed runs.

Read the installed package's CLI help and the Hermes Rubric documentation when a workflow needs flags or an optional adapter beyond these examples.
