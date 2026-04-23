# hermes-rubric — Intent

Forces evidence collection before producing structured scores. Three-stage pipeline: synthesize a domain rubric from (intent, context, target-type), collect per-dimension evidence with explicit hedging on thin data, score against the rubric — not from vibes. Every score is auditable.

## Accepts

- synthesizes a rubric from (intent, context, target-type) before any scoring begins
- collects per-dimension evidence citations pointing to file:line or named artifact before scoring
- marks dimensions as low-confidence when evidence is thin rather than silently averaging them in
- scores each dimension against the synthesized rubric, not against generic heuristics
- emits a reproducibility receipt containing the exact prompts used, data hashes, backend, and timestamp
- auto-detects the available backend in order: claude-cli, ollama-local, and raises if neither is present
- writes output as structured JSON with rubric, per_dim_scores, evidence_citations, aggregate, hedge_dims, and receipt fields
- accepts intent as a CLI string, context as a file or glob, and target as a file or directory
- runs in three discrete stages that are each independently inspectable
- exits non-zero if any stage fails and writes no partial output

## Does not

- produce a score before evidence is collected
- invent evidence citations when the source file cannot be found
- treat surface fluency as a proxy for substance
- silently drop low-confidence dimensions into the aggregate
- require an Anthropic API key or OpenAI API key
- push to any external service
- run as a daemon or schedule itself
- fabricate numeric scores not grounded in the rubric
- accept backend selection via environment variables that bypass the auto-detection priority order
