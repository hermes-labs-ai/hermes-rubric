# hermes-rubric

**Evidence-first structured scoring for LLM-judged artifacts.** Forces a three-stage scaffold — synthesize a domain rubric, collect per-dimension citations, then score against the evidence — so the number at the end has an audit trail.

[![PyPI](https://img.shields.io/pypi/v/hermes-rubric.svg)](https://pypi.org/project/hermes-rubric/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-rubric.svg)](https://pypi.org/project/hermes-rubric/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml)
[![Hermes Seal](https://img.shields.io/badge/hermes--seal-verified-blue)](https://github.com/hermes-labs-ai/hermes-rubric)

Without a scaffold, LLM scores reward fluency. Well-written garbage outscores substantive-but-rough work. Re-run the same input — the number shifts. There's no audit trail, and no way to argue with it.

hermes-rubric replaces that with three sequential stages: **(1)** synthesize a domain-specific rubric from your intent + context + target type, **(2)** collect per-dimension evidence citations (`file:line` or quoted passage), explicitly hedging dimensions where evidence is thin, **(3)** score against the rubric and citations only. Fabricated claims can't outscore evidenced ones — enforced by adversarial test.

## Install

```bash
pip install hermes-rubric
```

Python 3.10+. No API key required out-of-the-box — works with the Claude Code CLI (`claude`) or local Ollama. See [Backends](#backends) for the full plugin matrix (Anthropic, OpenAI, Google, Qwen).

## Quick start

```bash
hermes-rubric \
    --intent "rate this as a publication-ready research artifact" \
    --context STYLE-GUIDE.md \
    --target paper.md \
    --out result.json
```

Output (truncated):

```json
{
  "rubric": {"dimensions": [{"id": "claim_density", "weight": 3}, ...]},
  "evidence_citations": [
    {"dim_id": "claim_density", "citation": "paper.md:42", "quote": "..."}
  ],
  "per_dim_scores": [{"dim_id": "claim_density", "score": 8, "rationale": "..."}, ...],
  "aggregate": 8.7,
  "max_possible": 10.0,
  "hedge_dims": ["Reproducibility"],
  "hedge_note": "1 dimension had thin evidence — score less reliable: Reproducibility",
  "dim_summaries": [
    {"dim_id": "claim_density", "name": "Claim Density", "score": 8, "weight": 3, "hedged": false}
  ],
  "receipt": {"backend": "claude-cli", "timestamp_utc": "...", "input_hashes": {...}}
}
```

## CLI

```
hermes-rubric --target <path> [options]
hermes-rubric kappa <result_a.json> <result_b.json>     # cross-backend agreement
```

| Flag | Default | Purpose |
|---|---|---|
| `--target <path>` | required | File or directory to score |
| `--intent <text>` | required (unless `--artifact-class`) | One-sentence goal |
| `--context <path>` | required (unless `--artifact-class`) | Context for rubric synthesis |
| `--target-type <label>` | `document` | Tag for the target kind (e.g. `paper`, `tool`, `repo`) |
| `--out <path>` | stdout | Output JSON path |
| `--backend <name>` | auto-detect | One of: `claude-cli`, `ollama-local`, `dashscope-qwen`, `google-gemini`, `openai`, `openai-sdk`, `google-genai`, or any registered plugin |
| `--scope-class <name>` | none | `gate-plan` / `sweep-plan` / `results-bundle` — biases the synthesizer toward the right axes |
| `--intent-debias` | off | Prepend a debias preamble that neutralizes valence-loaded framing in the intent |
| `--artifact-class <name>` | none | Use a deterministic class template instead of LLM synthesis (see [Class-aware mode](#class-aware-mode-v02)) |
| `--batch` | off | Bundle evidence + scoring into one LLM call per stage; falls back to per-dim on parse failure |
| `--target-window-bytes <n>` | `8000` | Truncation cap for target/context content; oversize files emit a stderr warning |
| `--verbose` | off | Print stage progress to stderr |

Subcommand `kappa`: computes Cohen's κ between two completed runs. See `hermes-rubric kappa --help`.

## Class-aware mode (v0.2)

When you score the same kind of artifact repeatedly, Stage-1 LLM synthesis re-invents the dim set on every run — same target, three runs, three different rubric hashes. Class templates fix that:

```bash
hermes-rubric --artifact-class social-post --target post.md --out result.json
```

Each class is a YAML at `hermes_rubric/classes/<name>.yaml` defining a fixed dim set, weights, voice priors, and class-specific slop signatures. Same input + same class = same rubric across runs, so dim-by-dim diff actually means something. Bundled classes: `social-post`, `show-hn-post`, `linkedin-post`, `outreach-email`.

To add your own: in a development checkout (`pip install -e .`), drop a YAML next to the bundled ones. For installed distributions, fork the repo or maintain class YAMLs in your own package and load them via `hermes_rubric.classes.load_class()` — see `src/hermes_rubric/classes/__init__.py` for the loader.

## What the output means

- **`aggregate`** — weighted score (0–10). Signal, not verdict.
- **`hedge_dims`** — dimensions where evidence was thin. Scores in these dims are clamped to [3, 7]. The more hedged dimensions, the less you should trust the aggregate.
- **`evidence_citations`** — every score ties back to a quoted passage or `file:line`. This is the audit trail.
- **`receipt`** — same inputs + same backend + same rubric source produces scores within ±1 across runs. Receipt records backend, timestamp, input hashes, and rubric source (`synthesized` vs `class-template`).

## Backends

Seven built-in backends, auto-detected in priority order. Force one with `--backend <name>`:

| Backend         | Requires                                   | Notes                          |
|-----------------|--------------------------------------------|--------------------------------|
| `claude-cli`    | Claude Code installed (`claude --print`)   | Default. Highest consistency.  |
| `ollama-local`  | Ollama running locally (default `qwen3.5:14b`) | Zero cost, offline. Fallback chain: `gemma3:12b` → `gemma3:4b` → `mistral:7b` → `qwen3.5:9b` → `qwen3.5:4b`. |
| `dashscope-qwen`| `DASHSCOPE_API_KEY`                        | Alibaba Cloud Qwen.            |
| `google-gemini` | `GOOGLE_GEMINI_API_KEY`                    | REST.                          |
| `openai`        | `OPENAI_API_KEY`                           | REST, no SDK dep.              |
| `openai-sdk`    | `OPENAI_API_KEY` + `pip install hermes-rubric[openai]` | Uses official SDK.   |
| `google-genai`  | `GOOGLE_GEMINI_API_KEY` + `pip install hermes-rubric[google]` | Uses google-genai SDK. |

### Plugging in your own backend

Backends conform to a single `BackendProtocol`:

```python
class BackendProtocol(Protocol):
    name: str
    def call(self, prompt: str, max_tokens: int = 2048) -> str: ...
    def detect_available(self) -> bool: ...
```

Register at runtime:

```python
from hermes_rubric.backends import register

class MyBackend:
    name = "my-backend"
    def call(self, prompt, max_tokens=2048): ...
    def detect_available(self): ...

register(MyBackend())
```

Or ship as a third-party package via the `hermes_rubric.backends` entry-point group:

```toml
# pyproject.toml of your plugin package
[project.entry-points."hermes_rubric.backends"]
my-backend = "my_pkg.backend:MyBackend"
```

`hermes-rubric` discovers entry-point plugins on first call. See `src/hermes_rubric/backends.py` for the reference implementation.

## Library usage

```python
from hermes_rubric.synthesize import synthesize
from hermes_rubric.evidence import collect_evidence
from hermes_rubric.score import score_dimensions, compute_aggregate

rubric = synthesize(
    intent="...",
    context_summary="...",
    target_type="paper",
    target_excerpt="...",
)
evidence = collect_evidence(
    rubric=rubric,
    target_content="...",
    target_path="paper.md",
)
scores = score_dimensions(rubric=rubric, evidence_list=evidence)
result = compute_aggregate(rubric=rubric, scores=scores)
```

## When to use it

- Scoring artifacts where fluency-vs-substance divergence matters (papers, proposals, PRs, cold emails, lead dossiers).
- You need an audit trail — "the model said 8.7" isn't enough; you need to know *why*.
- You're calibrating against a specific style guide or rubric and generic "quality vibes" won't do.
- You want the same input to produce a score you can reproduce and defend.

## When not to use it

- Binary pass/fail gates — use a deterministic linter instead.
- Single-sentence inputs — there's no evidence surface for the rubric to cite.
- Scoring at high volume where cost matters more than fidelity — use a cheaper heuristic.
- Adversarial scoring where the author controls both the artifact and the rubric synthesis.

## Calibration

- **`calibration/dataset.jsonl`** — 15 labeled cases across 5 domains (paper-quality, tool-fit, deploy-readiness, email-quality, lead-score).
- **`calibration/META-RUBRIC.md`** — the rubric for evaluating rubric generators. 7 dimensions, each motivated by a specific LLM failure mode.
- **`calibration/failure-mode-taxonomy.md`** — 24 failure modes mined from the Hermes Labs research corpus.

## Evals

- **`evals/wedge-variance/`** — variance comparison: hermes-rubric `aggregate` vs raw 0–10 LLM rating, same target × same backend. Demonstrates the variance-reduction wedge.
- **`applied/papers-20260423.md`** — four research papers scored on publication-readiness:

  | Paper                                  | Aggregate |
  |----------------------------------------|-----------|
  | cogito-ergo LongMemEval                | 9.1       |
  | LangQuant LPCI                         | 8.7       |
  | Taxonomy of Epistemic Failure Modes    | 6.9       |
  | Asymmetric Burden of Proof             | 6.5       |

  Each score has a full rubric + citations + per-dimension rationale in the file.

## Running the tests

```bash
git clone https://github.com/hermes-labs-ai/hermes-rubric
cd hermes-rubric
pip install -e ".[dev]"
pytest
```

**111 tests** across 13 files, including two adversarial gates that fail the build if the scaffold breaks:

- `test_fluency_does_not_inflate_evidence_score` — a fluent rewrite of weak evidence must not outscore a substantive-but-rough version by more than 1 point.
- `test_fabricated_claim_does_not_outscore_evidenced_claim` — claims without supporting evidence are capped at ≤3.

CI status: see the [GitHub Actions badge](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml) at the top of this README.

## License

MIT — see [LICENSE](LICENSE).

---

## About Hermes Labs

[Hermes Labs](https://hermes-labs.ai) builds AI audit infrastructure for enterprise AI systems — EU AI Act readiness, ISO 42001 evidence bundles, continuous compliance monitoring, agent-level risk testing. We work with teams shipping AI into regulated environments.

**Our OSS philosophy — read this if you're deciding whether to depend on us:**

- **Everything we release is free, forever.** MIT or Apache-2.0. No "open core," no SaaS tier upsell, no paid version with the features you actually need. You can run this repo commercially, without talking to us.
- **We open-source our own infrastructure.** The tools we release are what Hermes Labs uses internally — we don't publish demo code, we publish production code.
- **We sell audit work, not licenses.** If you want an ANNEX-IV pack, an ISO 42001 evidence bundle, gap analysis against the EU AI Act, or agent-level red-teaming delivered as a report, that's at [hermes-labs.ai](https://hermes-labs.ai). If you just want the code to run it yourself, it's right here.

**The Hermes Labs OSS audit stack** (public, production-grade, no SaaS):

**Static audit** (before deployment)
- [**lintlang**](https://github.com/hermes-labs-ai/lintlang) — Static linter for AI agent configs, tool descriptions, system prompts. `pip install lintlang`
- [**scaffold-lint**](https://github.com/hermes-labs-ai/scaffold-lint) — Static linter for LLM prompt scaffolds. `pip install scaffold-lint`
- [**rule-audit**](https://github.com/hermes-labs-ai/rule-audit) — Static prompt audit — contradictions, coverage gaps, priority ambiguities
- [**intent-verify**](https://github.com/hermes-labs-ai/intent-verify) — Repo intent verification + spec-drift checks
- [**repo-audit**](https://github.com/hermes-labs-ai/repo-audit) — Multi-signal repo readiness check

**Runtime observability** (while the agent runs)
- [**little-canary**](https://github.com/hermes-labs-ai/little-canary) — Prompt injection detection via sacrificial canary-model probes
- [**suy-sideguy**](https://github.com/hermes-labs-ai/suy-sideguy) — Runtime policy guard — user-space enforcement + forensic reports
- [**colony-probe**](https://github.com/hermes-labs-ai/colony-probe) — Prompt confidentiality audit — detects system-prompt reconstruction

**Scoring & regression** (to prove what changed)
- [**hermes-rubric**](https://github.com/hermes-labs-ai/hermes-rubric) — Evidence-first structured scoring (this tool). `pip install hermes-rubric`
- [**hermes-jailbench**](https://github.com/hermes-labs-ai/hermes-jailbench) — Jailbreak regression benchmark. `pip install hermes-jailbench`
- [**agent-convergence-scorer**](https://github.com/hermes-labs-ai/agent-convergence-scorer) — Score how similar N agent outputs are. `pip install agent-convergence-scorer`

**Supporting infra**
- [**claude-router**](https://github.com/hermes-labs-ai/claude-router) · [**zer0dex**](https://github.com/hermes-labs-ai/zer0dex) · [**forgetted**](https://github.com/hermes-labs-ai/forgetted) · [**quick-gate-python**](https://github.com/hermes-labs-ai/quick-gate-python) · [**quick-gate-js**](https://github.com/hermes-labs-ai/quick-gate-js) · [**hermes-seal**](https://github.com/hermes-labs-ai/hermes-seal)

Natural pairing: `scaffold-lint` catches *how much* scaffolding you have. `lintlang` catches *how well-structured* it is. `rule-audit` catches *what the rules contradict*. `hermes-rubric` scores the thing the agent finally produced — with citations.

---

Built by [Hermes Labs](https://hermes-labs.ai) · [@roli-lpci](https://github.com/roli-lpci)
