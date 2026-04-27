# Voice & style check — paper 2 (Batch Equivalence)

**Tool:** hermes-stylo (8-feature stylometric z-score detector)
**Run date:** 2026-04-26
**Reference corpus:** 4 prior Hermes Labs papers (lintlang, taxonomy, little-canary, quick-gate), 94 chunks

| feature | z-score | within ±2σ |
|---|---|---|
| typo_rate | -0.76 | ✓ |
| cap_start | -0.28 | ✓ |
| avg_sent_len | -1.58 | ✓ |
| fragment_ratio | +0.61 | ✓ |
| profanity_count | 0.00 | ✓ |
| punct_density | +0.31 | ✓ |
| lower_run_start | +0.38 | ✓ |
| lex_diversity | -7.46 | ⚠ outlier |

**7 of 8 features within ±2σ vs reference corpus.** Same outlier as paper 1: `lex_diversity` driven by domain-term repetition (further inflated by table density — paper 2 contains 5 tables hammering "backend / sub-A / sub-B / mean / Δ").
