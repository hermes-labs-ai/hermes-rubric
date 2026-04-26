# hermes-rubric

**Language scaffolds hold state. LLM scores don't — unless you force them to.**

The LPCI thesis (proved March 2026) showed that a stateless LLM can maintain coherent state through language scaffolding alone — the artifact is the memory, not the model. hermes-rubric applies that same principle to scoring: the rubric + evidence citations are the audit trail. The number at the end means something only because the scaffold forced the model to collect evidence before scoring.

Without a scaffold, LLMs reward fluency. hermes-rubric forces a three-stage path before any number is produced:

1. **Synthesize a rubric** from your intent and context. Domain-specific, not generic.
2. **Collect evidence** per dimension. Citation required — `file:line`, quoted passage, or named artifact. Dimensions without evidence are explicitly hedged.
3. **Score against the rubric and evidence only.** Fabricated claims can't outscore cited ones.

---

## The problem it solves

You asked a model to score a PR / paper / email and the number felt off. Later you read it and the score was right for the wrong reasons — fluent writing, not substance.

hermes-rubric breaks the fluency-bias loop. The scaffold compels the model to find evidence before scoring. No evidence → hedged dimension → score clamped to [3,7]. The aggregate reflects what the model actually found, not how well the target was written.

---

## Worked example (tonight's session log)

hermes-rubric was run on its own plan-criteria-rubric spec as a self-scoring exercise. The plan scored 6.0/10 — the hedge dimensions (discoverability, anti-recursion) had thin evidence. The score correctly flagged which dims needed work before the plan could clear the 7.0 execute threshold. A generic LLM prompt would have returned 8.5/10 and glossed over the gaps.

The same pipeline is used across the Hermes Labs research corpus (1,976 experiment records) to score papers, experiment results, and cold-email drafts.

---

## Install

```bash
pip install hermes-rubric
```

Python 3.10+. No API key required. Works with Claude Code (`claude` CLI) or local Ollama.

---

## The loop it enables

```
Synthesize rubric (from intent + context)
  ↓
Collect evidence per dim (citation required)
  ↓
Score against evidence only
  ↓
Hedge thin dims, clamp to [3,7]
  ↓
Aggregate → receipt
  ↓
Iterate: address hedged dims, re-run
```

This is the loop-compounding pattern from the Hermes Labs handbook: each run improves the artifact, and the improvement is measurable.

---

## Part of the Hermes Labs OSS audit stack

hermes-rubric is the **scoring and regression** layer. It sits above the static linters and below the evidence bundle:

| Layer | Tool |
|---|---|
| Static audit (pre-deploy) | lintlang · scaffold-lint · rule-audit |
| Runtime observability | little-canary · suy-sideguy |
| **Scoring + regression** | **hermes-rubric** (this tool) |
| Evidence bundle (audit deliverable) | hermes-bundle (proprietary) |

[Install →](install.md) | [Quickstart →](quickstart.md) | [Pricing →](pricing.md)
