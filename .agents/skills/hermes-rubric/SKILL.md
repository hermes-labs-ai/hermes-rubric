---
name: hermes-rubric
description: Use when you need evidence-first LLM-as-judge scoring for an AI artifact — papers, PRs, prompts, cold emails — that synthesizes a rubric, collects quoted-evidence citations, scores only against that evidence, and hedges dimensions where evidence is thin. Every dimension ties to a file:line or quote, with reproducibility receipts. 7 backends.
license: MIT
compatibility: Requires Python 3.10+; installs via `pip install hermes-rubric` or runs standalone via `uvx hermes-rubric`. Needs a working LLM backend (`claude-cli`, `ollama-local`, `dashscope-qwen`, `google-gemini`, `openai`, `openai-sdk`, `google-genai`) — scoring itself is not zero-LLM.
---

# hermes-rubric

hermes-rubric is evidence-first LLM-as-judge scoring for AI artifacts —
papers, PRs, prompts, cold emails. It synthesizes a rubric (or loads a
deterministic class template), collects quoted-evidence citations, scores
only against that collected evidence, and hedges dimensions where evidence
is thin. Every dimension ties to a `file:line` or quote, with reproducibility
receipts, across 7 pluggable backends.

## Use it for

- Scoring a single artifact against a synthesized or pinned rubric with
  citation-backed evidence per dimension
- Using a deterministic class template (`--artifact-class`, e.g.
  `outreach-email`, `social-post`, `repo-*`) instead of LLM-synthesized rubric
  criteria
- Comparing artifact quality across model families with a reproducible,
  evidence-anchored scoring receipt
- Batch scoring (`--batch`) across a directory of targets

## Do not use it for

- A zero-LLM check — scoring always calls an LLM backend; use lintlang or
  hermeneutic instead for deterministic, LLM-free gates
- Ground-truth fact verification — it scores whether evidence was cited and
  quoted correctly, not whether the underlying claim is objectively true
- Real-time/low-latency gating — rubric synthesis plus evidence collection
  plus scoring is a multi-call pipeline, not a sub-second check

## Quickstart

```bash
pip install hermes-rubric
hermes-rubric --version
```

Or without installing, via [uv](https://docs.astral.sh/uv/):

```bash
uvx hermes-rubric --help
```

Score a target against a deterministic class template (needs a configured
backend, e.g. `--backend claude-cli` with the Claude CLI authenticated, or
`--backend ollama-local` with a local Ollama model):

```bash
uvx hermes-rubric --artifact-class outreach-email --target draft.txt --backend claude-cli
```

Real output confirmed in this environment (no `--context`/`--artifact-class`
supplied):

```
usage: hermes-rubric [-h] [--version] [--intent INTENT] [--context CONTEXT] --target TARGET ...
hermes-rubric: error: --context is required when --artifact-class/--pin-rubric is not set
```

## Commands

```
hermes-rubric --target <path> --artifact-class <name>   [--backend <backend>]
hermes-rubric --target <path> --intent "<goal>" --context <path>  [--backend <backend>]
hermes-rubric --target <path> --pin-rubric <path>        [--backend <backend>]
```

## Output shape

- Per-dimension score with quoted evidence and a `file:line` or exact-quote
  anchor for each citation
- Thin-evidence dimensions are hedged rather than scored with false
  confidence
- `--out` writes the structured result to a file for downstream tooling
- `--batch` processes multiple targets in one invocation

## Common gotchas

- `--context` is required unless `--artifact-class` or `--pin-rubric` is set
  — the CLI fails closed rather than guessing a rubric with no grounding.
- Scoring requires a working backend; `claude-cli` needs the Claude CLI
  authenticated in the environment, `ollama-local` needs a local Ollama
  server with a pulled model — an unconfigured backend will hang or fail
  rather than silently degrade.
- `--artifact-class` uses a deterministic template instead of LLM rubric
  synthesis — pick this when you want reproducible criteria across runs.

## More

Full docs, backend list, and artifact-class reference:
https://github.com/hermes-labs-ai/hermes-rubric
