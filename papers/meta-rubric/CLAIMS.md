# Claims Verification — META-RUBRIC paper

Every numeric or sourced claim in `paper.md` is traced to a file:line or
arxiv abstract pointer below. Pointers are local repo paths; commits as of
hermes-rubric SHA `596ba3b6e972551df9717438915ca30d84fdceec` (2026-04-24).

## Numeric claims

| # | Claim (paper text) | Source pointer | Verified value |
|---|---|---|---|
| 1 | "1,892 controlled experiments" (corpus size for taxonomy) | `hermes-rubric/calibration/META-RUBRIC.md:12` | "1,892 experiment records (research-corpus/epistemic + ai-behavior + scaffold)" |
| 2 | "24 distinct modes" (failure-mode taxonomy size) | `hermes-rubric/calibration/failure-mode-taxonomy.md:211` | "Total: 24 failure modes across 4 categories" |
| 3 | "weights summing to 16" | `hermes-rubric/calibration/META-RUBRIC.md:136` | "**Total weight** | **16**" |
| 4 | "frozen at v1.0" / "built 2026-04-23" | `hermes-rubric/calibration/META-RUBRIC.md:5` | "Built: 2026-04-23. Frozen for hermes-rubric v0.1." |
| 5 | "aggregate floor 7.0/10 with no dimension below 5" | `hermes-rubric/calibration/META-RUBRIC.md:140` | "Rubric passes META-RUBRIC at 7.0/10 aggregate with no dimension below 5." |
| 6 | "Self-grading aggregate 6.8/10" | `hermes-rubric/applied/self-20260424.md:4` | "**Aggregate:** 6.8 / 10.0" |
| 7 | "fluency-bias resistance 10/10 (cited tests/test_adversarial.py)" | `hermes-rubric/applied/self-20260424.md:18` | "**10/10** Fluency-bias resistance — cited `tests/test_adversarial.py`" |
| 8 | "hedging discipline 9/10 (cited score.py:98 and cli.py:114-115)" | `hermes-rubric/applied/self-20260424.md:19` | "**9/10** Hedging discipline — cited `score.py:98` and `cli.py:114-115`" |
| 9 | "evidence-gate enforcement 8/10" | `hermes-rubric/applied/self-20260424.md:21` | "**8/10** Evidence-gate enforcement" |
| 10 | "reproducibility receipt 6/10" | `hermes-rubric/applied/self-20260424.md:25` | "**6/10** Reproducibility receipt" |
| 11 | "Asymmetric Burden of Proof 6.5/10 weighted aggregate" | `hermes-rubric/applied/papers-20260423.md:79` | "Aggregate (weighted): ... 85/13 = **6.5/10**" |
| 12 | "Taxonomy of Epistemic Failure Modes 6.9/10" | `hermes-rubric/applied/papers-20260423.md:138` | "Aggregate (weighted): ... 90/13 = **6.9/10**" |
| 13 | "23/24 pair-condition cells" / "19.6–56.7 percentage points" (paper 1 abstract claims) | `hermes-rubric/applied/papers-20260423.md:36-39` | direct quote from scored abstract |
| 14 | "calibration dataset currently contains seven cases" | `hermes-rubric/calibration/dataset.jsonl` (line count) | 7 records (cal-003, cal-004, cal-005, cal-007, cal-008, cal-009, cal-010) |
| 15 | "Three of seven cases carry human_score_provisional: true" | `hermes-rubric/calibration/dataset.jsonl` (grep) | grep `human_score_provisional.: true` returns 3 (cal-003, cal-004, cal-010) |
| 16 | "9b vs 0.8b ablation" (semantic constraint evasion finding) | `hermes-rubric/calibration/failure-mode-taxonomy.md:97` | "9b model used 1.1 synonyms vs 0.6 for 0.8b model" |
| 17 | "DeCE r=0.78 vs r=0.35" | `paper.bib` Yu 2025 + verification log [7] | abstract excerpt: "r=0.78 ... pointwise LLM scoring (r=0.35)" |
| 18 | "LLMBar 419 curated output pairs" | RELATED-WORK-VERIFICATION.md [9] | direct from fetched abstract |

## Citation pointers (12)

All twelve arxiv citations verified against fetched abstracts. See
`RELATED-WORK-VERIFICATION.md` for arxiv ID, posted date, and abstract
excerpt for each.

| BibTeX key | arXiv ID | Source of verification |
|---|---|---|
| zheng2023mtbench | 2306.05685 | reused from paper 2 log |
| liu2023geval | 2303.16634 | reused from paper 2 log |
| shankar2024validators | 2404.12272 | reused from paper 2 log |
| lee2024consistency | 2412.00543 | reused from paper 2 log |
| errica2024sensitivity | 2406.12334 | reused from paper 2 log |
| yu2025dece | 2509.16093 | reused from paper 2 log |
| choi2026irt | 2602.00521 | reused from paper 2 log |
| yeadon2026criterion | 2603.14732 | reused from paper 2 log |
| zeng2023llmbar | 2310.07641 | newly fetched 2026-04-24 |
| chern2024scaleeval | 2401.16788 | newly fetched 2026-04-24 |
| rao2026autorubric | 2603.00077 | newly fetched 2026-04-24 |
| tang2026rubric | 2604.12227 | newly fetched 2026-04-24 |

`batchequiv2026` is a non-arxiv companion citation; pointer is the local
hermes-content path and not subject to arxiv verification.

## Reproducibility anchor

- `hermes-rubric` commit SHA: `596ba3b6e972551df9717438915ca30d84fdceec`
- Date: 2026-04-24
- All file:line pointers above resolve under this commit.
