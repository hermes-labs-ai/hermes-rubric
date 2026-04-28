# hermes-rubric

**Evidence-first structured scoring for LLM-judged artifacts. 62.9% chance-corrected agreement (Cohen's κ = 0.629, N=96 paired runs) across three model families on the batch-equivalence test set. 115 tests with two adversarial gates.** Forces a three-stage scaffold - synthesize a domain rubric, collect per-dimension citations, then score against the evidence - so the number at the end has an audit trail.

[![PyPI](https://img.shields.io/pypi/v/hermes-rubric.svg)](https://pypi.org/project/hermes-rubric/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-rubric.svg)](https://pypi.org/project/hermes-rubric/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml)
[![Hermes Seal](https://img.shields.io/badge/hermes--seal-verified-blue)](https://github.com/hermes-labs-ai/hermes-rubric)

**Cross-model Cohen's κ = 0.629 (62.9% chance-corrected agreement) across 96 paired runs** on the batch-equivalence test set - 5 fixture targets (T1–T5) spanning paper-quality, deploy-readiness, and email-quality scoring, full target list at [`experiments/batch-equiv-2026-04-25/RESULTS.md`](experiments/batch-equiv-2026-04-25/RESULTS.md). Per-backend: Gemini 2.5 Flash κ=0.642 (N=47), Qwen-Plus κ=0.621 (N=47); Claude κ=0.527 reported at N=2 - too few pairs for a stable estimate, included for transparency only. Passes the pre-registered ≥0.6 reproducibility floor. Raw runs and aggregation script in [`experiments/batch-equiv-2026-04-25/`](experiments/batch-equiv-2026-04-25/) - clone, run `compute_kappa.py`, get the same number. **115 tests** including two adversarial gates that fail the build if the scaffold breaks. Most LLM-as-judge tools score in one prompt and call it consistent; hermes-rubric forces three stages and capping rules that catch fluency-inflation in tests, every release.

```bash
echo "rate this paper" | hermes-rubric --target paper.md  # score with full audit trail
```

Without a scaffold, LLM scores reward fluency. Well-written garbage outscores substantive-but-rough work. Re-run the same input - the number shifts. There's no audit trail, and no way to argue with it.

hermes-rubric replaces that with three sequential stages: **(1)** synthesize a domain-specific rubric from your intent + context + target type, **(2)** collect per-dimension evidence citations (`file:line` or quoted passage), explicitly hedging dimensions where evidence is thin, **(3)** score against the rubric and citations only. Fabricated claims can't outscore evidenced ones - enforced by adversarial test. See [Examples](#examples) below and [`evals/`](evals/) for the worked-example reproducibility receipts.

## Install

```bash
pip install hermes-rubric
```

Python 3.10+. No API key required out-of-the-box - works with the Claude Code CLI (`claude`) or local Ollama. See [Backends](#backends) for the full plugin matrix (Anthropic, OpenAI, Google, Qwen).

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
| `--scope-class <name>` | none | `gate-plan` / `sweep-plan` / `results-bundle` - biases the synthesizer toward the right axes |
| `--intent-debias` | off | Prepend a debias preamble that neutralizes valence-loaded framing in the intent |
| `--artifact-class <name>` | none | Use a deterministic class template instead of LLM synthesis (see [Class-aware mode](#class-aware-mode-v02)) |
| `--batch` | off | Bundle evidence + scoring into one LLM call per stage; falls back to per-dim on parse failure |
| `--target-window-bytes <n>` | `8000` | Truncation cap for target/context content; oversize files emit a stderr warning |
| `--verbose` | off | Print stage progress to stderr |

Subcommand `kappa`: computes Cohen's κ between two completed runs. See `hermes-rubric kappa --help`.

## Class-aware mode

When you score the same kind of artifact repeatedly, Stage-1 LLM synthesis re-invents the dim set on every run - same target, three runs, three different rubric hashes. Class templates fix that:

```bash
hermes-rubric --artifact-class social-post --target post.md --out result.json
```

Each class is a YAML at `hermes_rubric/classes/<name>.yaml` defining a fixed dim set, weights, voice priors, and class-specific slop signatures. Same input + same class = same rubric across runs, so dim-by-dim diff actually means something. Bundled classes: `social-post`, `show-hn-post`, `linkedin-post`, `outreach-email`.

To add your own: in a development checkout (`pip install -e .`), drop a YAML next to the bundled ones. For installed distributions, fork the repo or maintain class YAMLs in your own package and load them via `hermes_rubric.classes.load_class()` - see `src/hermes_rubric/classes/__init__.py` for the loader.

## What changes for you immediately

After `pip install hermes-rubric`, the next time you ask a model to score something:

- Every score comes with a citation list - `file:line` or quoted passage per dimension. No more "8.4/10" with no audit trail.
- Dimensions where evidence was thin get clamped to [3, 7] and flagged as `hedge_dims`. The model can't bury weak evidence under a confident number.
- Re-running the same input + backend + rubric source produces the same score (within ±1) - receipts record the input hashes, so drift is detectable.
- Fluent-but-empty prose stops outscoring substantive-but-rough work - adversarial test in `tests/test_adversarial.py` fails the build if it does.
- Domain-specific rubrics auto-synthesize from your intent + context, instead of falling back to a generic "academic quality" template.

Most users notice the receipts more than the score. The score is the headline; the audit trail is the product.

## Known limitations (honest list)

- **The Stage-1 LLM rubric synthesis introduces a generic-rubric tail** when context is sparse. Mitigated by `--artifact-class <name>` for repeated artifact types; not yet auto-suggested.
- **κ measured on N=96 paired runs across 5 fixture targets (T1–T5)** - that's evidence for batch-vs-per-dim equivalence on this test set, not yet a generalization claim across all artifact domains. Cross-domain κ (paper-quality vs deploy-readiness vs lead-score) is on the roadmap (see `experiments/rubric-quality-PROPOSAL.md`).
- **Anthropic SDK backend exists but the cross-model κ figure includes only N=2 Claude pairs** - small sample, deferred Claude paper-grade run noted in ACTIONABLES.md.
- **Stage-2 evidence collection is deterministic given a synthesized rubric, but Stage 1 is not** - same intent + same context can produce slightly different rubric dim sets across runs. Use `--artifact-class` for full reproducibility.

## Examples

Three real worked examples ship in-repo:

- [`evals/wedge-variance/`](evals/wedge-variance/) - variance comparison: hermes-rubric `aggregate` vs raw 0–10 LLM rating, same target × same backend. Demonstrates the variance-reduction wedge with reproducible runner.
- [`applied/papers-20260423.md`](applied/papers-20260423.md) - two publicly published Zenodo papers scored on publication-readiness as worked examples (Asymmetric Burden of Proof, Taxonomy of Epistemic Failure Modes).
- [`calibration/dataset.jsonl`](calibration/dataset.jsonl) - 7 labeled cases with human scores, used for cross-backend κ measurement and as a regression fixture.

## Verify the cross-model κ claim yourself

The "Cohen's κ = 0.629" headline is the load-bearing public claim. Reproduce it from the raw artifacts in-repo:

```bash
git clone https://github.com/hermes-labs-ai/hermes-rubric && cd hermes-rubric
python experiments/batch-equiv-2026-04-25/compute_kappa.py
# Per-target κ table, per-backend mean, overall mean. Should match RESULTS.md.
```

If the script's output doesn't match the README number, file an issue - the chain is broken and we want to know.

## What the output means

- **`aggregate`** - weighted score (0–10). Signal, not verdict.
- **`hedge_dims`** - dimensions where evidence was thin. Scores in these dims are clamped to [3, 7]. The more hedged dimensions, the less you should trust the aggregate.
- **`evidence_citations`** - every score ties back to a quoted passage or `file:line`. This is the audit trail.
- **`receipt`** - same inputs + same backend + same rubric source produces scores within ±1 across runs. Receipt records backend, timestamp, input hashes, and rubric source (`synthesized` vs `class-template`).

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
- You need an audit trail - "the model said 8.7" isn't enough; you need to know *why*.
- You're calibrating against a specific style guide or rubric and generic "quality vibes" won't do.
- You want the same input to produce a score you can reproduce and defend.

## When not to use it

- Binary pass/fail gates - use a deterministic linter instead.
- Single-sentence inputs - there's no evidence surface for the rubric to cite.
- Scoring at high volume where cost matters more than fidelity - use a cheaper heuristic.
- Adversarial scoring where the author controls both the artifact and the rubric synthesis.

## Calibration

- **`calibration/dataset.jsonl`** - 7 labeled cases across paper-quality, tool-fit, and deploy-readiness domains. All targets are publicly available artifacts (Zenodo papers, public OSS tools).
- **`calibration/META-RUBRIC.md`** - the rubric for evaluating rubric generators. 7 dimensions, each motivated by a specific LLM failure mode from the taxonomy below.
- **`calibration/failure-mode-taxonomy.md`** - 24 failure modes mined from the Hermes Labs research corpus (1,892 experiment records + named post-mortem incidents). Each FM cites a source artifact.

## Evals

- **`evals/wedge-variance/`** - variance comparison: hermes-rubric `aggregate` vs raw 0–10 LLM rating, same target × same backend. Demonstrates the variance-reduction wedge.
- **`applied/papers-20260423.md`** - two publicly published research papers scored on publication-readiness as worked examples:

  | Paper                                  | Aggregate |
  |----------------------------------------|-----------|
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

**115 tests** (111 passing + 4 skipped) across 14 files, including two adversarial gates that fail the build if the scaffold breaks plus a mechanical doc-consistency gate (`tests/test_docs_consistency.py`) that fails CI if the README opener / `pytest --collect-only` count drift apart:

- `test_fluency_does_not_inflate_evidence_score` - a fluent rewrite of weak evidence must not outscore a substantive-but-rough version by more than 1 point.
- `test_fabricated_claim_does_not_outscore_evidenced_claim` - claims without supporting evidence are capped at ≤3.

CI status: see the [GitHub Actions badge](https://github.com/hermes-labs-ai/hermes-rubric/actions/workflows/ci.yml) at the top of this README.

## License

MIT - see [LICENSE](LICENSE).

---

## About Hermes Labs

Hermes Labs is building the reliability stack for the agent era. Memory, 
evaluation, observability, containment - the infrastructure layer that 
makes autonomous AI agents production-grade. Founded 2025 by Rolando 
(Roli) Bosch, solo founder, AI-amplified ("cyborg engineering"). Based 
in the San Francisco Bay Area.

The technical thesis: language sets the capability and intelligence; the 
model is the ceiling, not the source. Reliability is a question of 
linguistic infrastructure, not model tuning. Formalized as LPCI 
(Linguistically Persistent Cognitive Interface) - transfer entropy ≈ 0 
in embedding-space proxy, Markov property holds, the substrate is 
linguistic. The engineering follow-on: when language is the substrate, 
the engineering is interpretive - recovering meaning across the 
boundaries between model and user, session and session, training and 
runtime.

Public technical receipts. The flagship open-source release is fidelis 
- zero-LLM agent memory with integer-pointer fidelity. 73.0% end-to-end 
QA on LongMemEval-S, Wilson 95% CI [68.7%, 77.0%], at $0 per query, 
fully local. Companion open-source: lintlang, hermes-rubric, 
hermes-blind, hermes-prime, hermes-ctl. Published research at 
zenodo.org and the Hermes Labs paper line. The OSS surface is the 
proof; the commercial work is enterprise deployments.

For enterprise deployments and AI-reliability engagements: 
rbosch@lpci.ai · lpci.ai

On naming. Hermes Labs is named for Hermes, the Greek messenger god - 
patron of communication and interpretation, the herald who carries 
meaning between worlds. The thread to the work: hermeneutics, the 
theory of interpretation that takes its name from Hermes, is the 
philosophical anchor for an AI infrastructure company whose substrate 
is linguistic. Not affiliated with NousResearch's Hermes LLM line or 
their hermes-agent framework - different companies, different work.

Founder: Rolando (Roli) Bosch. 
Site: hermes-labs.ai
Citation: Bosch, R. (2026). Hermes Labs: AI reliability infrastructure 
for autonomous agents. https://hermes-labs.ai

Quantitative sources for claims above:
- fidelis 73.0% / Wilson 95% CI [68.7%, 77.0%]: see fidelis/README.md 
  "End-to-end QA accuracy" + experiments/zeroLLM-FLAGSHIP-evidence/, 
  470 questions, eval date 2026-04-24
- LPCI thesis (TE ≈ 0 embedding-space proxy): langquant repo, commit 
  dd918cc (2026-03-28) "LPCI PROVED" + lpci_rigorous.py:507-571
- 24-failure taxonomy: hermes-rubric/calibration/failure-mode-taxonomy.md

