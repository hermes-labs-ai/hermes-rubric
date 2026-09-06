# hermes-rubric

Evidence-first assessment for agent outputs and applications.

[![PyPI](https://img.shields.io/pypi/v/hermes-rubric)](https://pypi.org/project/hermes-rubric/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-rubric)](https://pypi.org/project/hermes-rubric/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![CI](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml)

**Product page:** [hermes-labs.ai/hermes-rubric](https://hermes-labs.ai/hermes-rubric)

Hermes turns an artifact into cited evidence, dimension scores, honest coverage facts, and caller-controlled feedback. It measures and explains; your application decides what to do next.

```python
from hermes_rubric import FeedbackPolicy, assess

result = assess(
    target=agent_output,
    intent="Answer accurately and support material claims with checkable evidence.",
    context=task_context,
    target_type="agent-output",
    backend="openai-sdk",
)

print(result.aggregate)
print(result.coverage.status)
print(result.feedback(FeedbackPolicy(minimum_score=7)).to_prompt())
```

The same call can sit inside LangChain, the OpenAI Agents SDK, Semantic Kernel, PydanticAI, a bespoke loop, a notebook, CI, or a plain Python service. Those frameworks are not core dependencies, and Hermes does not run an agent loop for you.

## Install

The base package requires Python 3.10 or newer and PyYAML:

```bash
pip install hermes-rubric
```

For the example above, install the OpenAI extra and set `OPENAI_API_KEY`:

```bash
pip install "hermes-rubric[openai]"
```

Framework adapters are optional extras too: `hermes-rubric[inspect]` bundles an Inspect AI scorer and `hermes-rubric[openai-agents]` grades completed OpenAI Agents SDK runs. See [Adapters](docs/ADAPTERS.md).

You can instead use local Ollama, Claude Code, another built-in backend, or a backend plugin. Automatic selection checks authenticated Claude Code first, then local Ollama; cloud providers are always explicit opt-ins. See [Backends](docs/BACKENDS.md).

## One transaction, three evidence-first stages

Hermes keeps the measuring process separate from runtime policy:

1. Synthesize a task-specific rubric, load a bundled deterministic template, or accept a caller-provided frozen rubric.
2. Collect and validate citations for each dimension.
3. Score only against accepted evidence, applying the existing hedge, no-evidence, and source-authority clamps.

Provider failures and malformed scoring responses do not become fallback scores
or enter an aggregate. Batch mode retries a malformed or incomplete score
response per dimension; if a retry still fails, `assess` raises
`AssessmentError` with `stage == "score"`.

The returned `AssessmentResult` has attribute access plus `to_dict()` and `to_json()`. Its JSON preserves the established CLI keys and adds a versioned schema and coverage report.

```python
payload = result.to_dict()

assert payload["schema_version"] == "1.0"
print(payload["evidence_citations"])
print(payload["per_dim_scores"])
print(payload["receipt"])
```

The aggregate is a signal, not a verdict.

## Choose the measuring stick

Synthesize from intent and context when the criteria should be task-specific:

```python
result = assess(
    target=answer,
    intent="Evaluate whether this answer is accurate and well-supported.",
    context="The answer must distinguish observation from inference.",
    target_type="agent-output",
)
```

Reuse a frozen rubric when runs must share the same dimensions:

```python
import json
from hermes_rubric import assess

with open("rubric.json") as handle:
    frozen_rubric = json.load(handle)

result = assess(target=answer, rubric=frozen_rubric)
```

Use a bundled deterministic artifact class for common publishing surfaces:

```python
result = assess(target=readme_text, artifact_class="repo-readme")
```

Bundled classes are `social-post`, `show-hn-post`, `linkedin-post`, `outreach-email`, and `repo-readme`.

## Coverage is part of the result

Version 1.1 uses the existing UTF-8-safe prefix strategy for evidence collection. The default target window is 8,000 bytes. Hermes reports `coverage.status` as `complete` or `partial`, includes visible and total byte facts when they are knowable, discloses directory source limits, and lists plain-language limitations.

```python
if result.coverage.status == "partial":
    for limitation in result.coverage.limitations:
        print(limitation)
```

`partial` means relevant material may not have been inspected. It must not be translated into “the evidence is absent.” Full chunked retrieval is a later engine capability, not a v1.1 claim.

## Feedback without hidden policy

Hermes distinguishes three next-step types:

- `quality_gap`: inspected evidence supports a score below a threshold you supplied.
- `evidence_gap`: accepted evidence is absent or hedged.
- `coverage_gap`: the relevant material may not have been inspected.

No pass/fail threshold is built in. `FeedbackPolicy(minimum_score=...)` is caller policy, and `to_prompt()` only creates deterministic instructions—it never mutates a runtime or retries an agent. A coverage-only gap asks for wider inspection, not an automatic rewrite.

## File and CLI workflows

Use `assess_path()` for a file or directory:

```python
from hermes_rubric import assess_path

result = assess_path(
    "paper.md",
    intent="Evaluate publication readiness.",
    context_path="STYLE-GUIDE.md",
    target_type="paper",
)
```

The CLI is the equivalent file and automation surface:

```bash
hermes-rubric \
  --intent "Evaluate publication readiness" \
  --context STYLE-GUIDE.md \
  --target paper.md \
  --out result.json
```

Existing flags, output keys, and stage exit codes remain available. See the full [CLI reference](docs/CLI.md).

Async wrappers keep synchronous providers off the event loop:

```python
from hermes_rubric import assess_async

result = await assess_async(answer, rubric=frozen_rubric)
```

They use `asyncio.to_thread`; cancellation cannot interrupt a provider call already running in its worker thread.

## When to use Hermes

Use it when:

- an agent or application needs cited, inspectable assessment rather than a raw judge score;
- weak or missing evidence must remain visible;
- the same assessment contract should work across different runtimes;
- receipts and frozen rubrics matter for reviewing repeated runs.

Use a deterministic validator instead when the rule can be expressed exactly. Do not use Hermes as proof of factual truth, as a compliance certification, or as an automatic release decision. If the artifact is longer than the inspected window, review coverage before acting on missing evidence.

For directly comparable re-grades, pass `--pin-rubric prior-result.json` to
reuse the prior result's rubric without changing its hash.

## Documentation

- [Quickstart](docs/quickstart.md)
- [Python API](docs/API.md)
- [Architecture and product boundary](docs/ARCHITECTURE.md)
- [Adapter contract](docs/ADAPTERS.md)
- [Backends](docs/BACKENDS.md)
- [CLI](docs/CLI.md)
- [Benchmarks and evidence limits](docs/BENCHMARKS.md)
- [v1.2.1 release notes](RELEASE-NOTES-v1.2.1.md)
- [v1.1.1 release notes](RELEASE-NOTES-v1.1.1.md)
- [v1.1.0 release notes](RELEASE-NOTES-v1.1.0.md)

## Contributing

```bash
git clone https://github.com/hermes-labs-ai/hermes-rubric
cd hermes-rubric
pip install -e ".[dev]"
pytest
```

The adversarial tests in `tests/test_adversarial.py` are release gates. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Copyright 2026 Hermes Labs. Licensed under Apache-2.0. See [LICENSE](LICENSE).
