# Voice & style check — paper 1 (META-RUBRIC)

**Tool:** hermes-stylo (8-feature stylometric z-score detector)
**Run date:** 2026-04-26
**Reference corpus:** 4 prior Hermes Labs papers (lintlang, taxonomy, little-canary, quick-gate), 94 chunks

| feature | z-score | within ±2σ |
|---|---|---|
| typo_rate | -1.03 | ✓ |
| cap_start | -0.28 | ✓ |
| avg_sent_len | -0.09 | ✓ |
| fragment_ratio | -0.85 | ✓ |
| profanity_count | 0.00 | ✓ |
| punct_density | +0.03 | ✓ |
| lower_run_start | +0.38 | ✓ |
| lex_diversity | -7.39 | ⚠ outlier |

**7 of 8 features within ±2σ vs reference corpus.** Voice match on typing register, sentence length, fragment style, capitalization, punctuation rhythm. Outlier is `lex_diversity` (vocabulary repetition), explained by domain-term hammering ("rubric," "META-RUBRIC," "evidence," "dimension," "score") that the cross-domain reference corpus does not have.

Reproduce: `cd ~/Documents/projects/hermes-stylo && python3 -c "from src.stylo import featurize, Profile, score; ..."` (full snippet in repo).
